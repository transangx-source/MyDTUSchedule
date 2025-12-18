import time
import json
import ddddocr
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime, timedelta
import sys 
import os

# --- FIX LỖI UNICODE TRÊN GITHUB ACTIONS ---
sys.stdout.reconfigure(encoding='utf-8')

# --- CẤU HÌNH ---
URL_LOGIN = "https://mydtu.duytan.edu.vn/Signin.aspx"
URL_SCHEDULE = "https://mydtu.duytan.edu.vn/Sites/index.aspx?p=home_schedule"
USERNAME = "trancongsang1"
PASSWORD = "Alice#1691"
OUTPUT_FILE = "lich_hoc_hom_nay_va_mai.json"

def get_vietnam_time():
    # GitHub Server chạy UTC, cần cộng 7h để ra giờ VN
    return datetime.utcnow() + timedelta(hours=7)

def save_json(data):
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def crawl_schedule_to_json():
    # Lấy ngày giờ VN chuẩn
    now_vn = get_vietnam_time()
    TODAY = now_vn.strftime("%d/%m/%Y")
    TOMORROW = (now_vn + timedelta(days=1)).strftime("%d/%m/%Y")
    
    print(f"🚀 [CHROME] Bat dau chay luc {now_vn.strftime('%H:%M %d/%m/%Y')}")
    print(f"📅 Muc tieu: {TODAY} va {TOMORROW}")
    
    options = webdriver.ChromeOptions()
    # Sử dụng chế độ headless mới (ổn định hơn)
    options.add_argument("--headless=new") 
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # Khởi tạo biến data_output mặc định
    data_output = {
        "status": "error", 
        "message": "Khoi tao - Chua co du lieu.",
        "ngay_lay": now_vn.strftime("%d-%m-%Y %H:%M:%S"),
        "hom_nay": TODAY, 
        "ngay_mai": TOMORROW, 
        "lich_hoc": []
    }

    driver = None
    try:
        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        
        driver.get(URL_LOGIN)
        wait = WebDriverWait(driver, 15) # Giảm timeout xuống 15s cho nhanh
        print("[...] Dang dang nhap...")
        
        login_success = False
        
        # Vòng lặp đăng nhập
        for i in range(15):
            try:
                # Tìm và điền user/pass
                user_input = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input[id$='txtUser']")))
                user_input.clear()
                user_input.send_keys(USERNAME)
                
                pass_input = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
                pass_input.clear()
                pass_input.send_keys(PASSWORD)
                
                # Xử lý Captcha
                captcha_img = driver.find_element(By.CSS_SELECTOR, ".login-form img, img[src*='Captcha']")
                # Chụp ảnh captcha để OCR
                captcha_screenshot = captcha_img.screenshot_as_png
                ocr = ddddocr.DdddOcr(show_ad=False)
                code = ocr.classification(captcha_screenshot)
                
                print(f"   -> Lan {i+1}: Captcha = {code}")
                
                if len(code) != 4:
                    print("   -> Captcha khong du 4 ky tu, thu lai...")
                    driver.find_element(By.CSS_SELECTOR, "img[src*='Captcha']").click()
                    time.sleep(1)
                    continue
                
                driver.find_element(By.CSS_SELECTOR, "input[id$='txtCaptcha']").clear()
                driver.find_element(By.CSS_SELECTOR, "input[id$='txtCaptcha']").send_keys(code)
                
                # Click đăng nhập
                driver.find_element(By.CSS_SELECTOR, "input[type='submit'], input[id$='btnLogin']").click()
                time.sleep(3)
                
                # Kiểm tra url sau khi login
                if "Signin.aspx" not in driver.current_url:
                    print("✅ Dang nhap thanh cong!")
                    login_success = True
                    break
                else:
                    # Nếu vẫn ở trang login, có thể sai captcha, refresh thử lại
                    error_msg = driver.page_source
                    if "Sai mã xác nhận" in error_msg:
                        print("   -> Web bao sai captcha.")
                    else:
                        print("   -> Dang nhap that bai (ly do khac).")
                        
            except Exception as e:
                print(f"   ⚠️ Loi vatra trong vong lap login: {e}")
                driver.refresh()
                time.sleep(2)

        if not login_success:
            raise Exception("That bai qua 15 lan dang nhap (Sai Captcha hoac loi Web)")

        # Bắt đầu lấy lịch
        print("[...] Dang lay du lieu lich hoc...")
        driver.get(URL_SCHEDULE)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))
        
        rows = driver.find_elements(By.CSS_SELECTOR, "table tr")
        schedule_list = []
        
        for row in rows:
            cols = row.find_elements(By.TAG_NAME, "td")
            if len(cols) >= 5:
                try:
                    ngay_text = cols[1].text.strip()
                    # So sánh chuỗi ngày
                    if ngay_text == TODAY or ngay_text == TOMORROW:
                        schedule_list.append({
                            "ngay_hoc": ngay_text, 
                            "mon_hoc": cols[2].text.strip(),
                            "phong_hoc": cols[4].text.strip(), 
                            "tiet": cols[5].text.strip(),
                            "giang_vien": cols[7].text.strip()
                        })
                except: 
                    continue

        # Cập nhật thành công
        data_output["status"] = "success"
        data_output["message"] = "Thanh cong"
        data_output["lich_hoc"] = schedule_list
        print(f"✅ Da lay duoc {len(schedule_list)} tiet hoc.")

    except Exception as e:
        error_message = str(e)
        print(f"❌ LOI NGHIEM TRONG: {error_message}")
        # Cập nhật thông báo lỗi vào JSON để người dùng biết tại sao
        data_output["status"] = "error"
        data_output["message"] = f"Loi he thong: {error_message}"

    finally:
        # Luôn luôn lưu file dù thành công hay thất bại
        save_json(data_output)
        print("💾 Da luu file JSON.")
        if driver:
            try: driver.quit()
            except: pass

if __name__ == "__main__":
    crawl_schedule_to_json()
