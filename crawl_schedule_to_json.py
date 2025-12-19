import time
import json
import ddddocr
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import date, timedelta
import locale
import os
import sys 

# --- FIX LỖI UNICODE ---
sys.stdout.reconfigure(encoding='utf-8')

# --- CẤU HÌNH ---
URL_LOGIN = "https://mydtu.duytan.edu.vn/Signin.aspx"
URL_SCHEDULE = "https://mydtu.duytan.edu.vn/Sites/index.aspx?p=home_schedule"
USERNAME = "trancongsang1"
PASSWORD = "Alice#1691"
OUTPUT_FILE = "lich_hoc_hom_nay_va_mai.json"

# Đặt locale
try: locale.setlocale(locale.LC_TIME, 'vi_VN.UTF-8')
except:
    try: locale.setlocale(locale.LC_TIME, 'vi_VN')
    except: pass

def save_json(data):
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def crawl_schedule_to_json():
    TODAY = date.today().strftime("%d/%m/%Y")
    TOMORROW = (date.today() + timedelta(days=1)).strftime("%d/%m/%Y")
    
    print(f"🚀 [V3-Fix] Dang thu lay lich cho {TODAY} va {TOMORROW}...")
    
    options = webdriver.ChromeOptions()
    options.add_argument("--headless") 
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    # User-Agent xịn hơn để không bị chặn
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    try:
        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
    except Exception as e:
        print(f"❌ Lỗi Driver: {e}"); return
    
    # Khởi tạo OCR một lần cho nhanh
    ocr = ddddocr.DdddOcr(show_ad=False)
    
    data_output = {
        "status": "error", "message": "Chua chay xong.",
        "ngay_lay": date.today().strftime("%d-%m-%Y %H:%M:%S"),
        "hom_nay": TODAY, "ngay_mai": TOMORROW, "lich_hoc": []
    }

    try:
        driver.get(URL_LOGIN)
        wait = WebDriverWait(driver, 30) # Tăng thời gian chờ lên 30s
        print("[...] Dang vao trang dang nhap...")
        
        login_success = False
        for i in range(20): # Tăng số lần thử lên 20
            try:
                # Chờ các ô nhập liệu hiện ra
                wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input[id$='txtUser']"))).clear()
                driver.find_element(By.CSS_SELECTOR, "input[id$='txtUser']").send_keys(USERNAME)
                
                driver.find_element(By.CSS_SELECTOR, "input[type='password']").clear()
                driver.find_element(By.CSS_SELECTOR, "input[type='password']").send_keys(PASSWORD)
                
                # Chụp và giải mã Captcha
                time.sleep(1) # Chờ ảnh load kỹ
                captcha_img = driver.find_element(By.CSS_SELECTOR, ".login-form img, img[src*='Captcha']")
                code = ocr.classification(captcha_img.screenshot_as_png)
                print(f"   -> Thu lan {i+1}: Captcha doc duoc = '{code}'")
                
                if len(code) != 4:
                    print("      (Captcha sai dinh dang -> Refresh)")
                    driver.refresh(); time.sleep(2); continue
                
                driver.find_element(By.CSS_SELECTOR, "input[id$='txtCaptcha']").clear()
                driver.find_element(By.CSS_SELECTOR, "input[id$='txtCaptcha']").send_keys(code)
                
                # Bấm nút đăng nhập
                driver.find_element(By.CSS_SELECTOR, "input[type='submit'], input[id$='btnLogin']").click()
                
                # Chờ kết quả lâu hơn chút (5s)
                time.sleep(5)
                
                if "Signin.aspx" not in driver.current_url:
                    print("✅ Dang nhap THANH CONG!")
                    login_success = True
                    break
                else:
                    print("      (Dang nhap truot -> Thu lai)")
                    driver.refresh() # QUAN TRỌNG: F5 lại trang để lấy Captcha mới sạch sẽ
                    time.sleep(2)
            except Exception as e:
                print(f"   -> Loi kithuat: {e}")
                driver.refresh(); time.sleep(2)
        
        if not login_success:
            print("❌ That bai sau 20 lan thu. Bo tay!"); 
            data_output["message"] = "Loi: That bai 20 lan dang nhap (MyDTU chan hoac mang lag)."
            return

        # --- LẤY LỊCH ---
        print("[...] Dang lay du lieu lich...")
        driver.get(URL_SCHEDULE)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))
        rows = driver.find_elements(By.CSS_SELECTOR, "table tr")
        schedule_list = []
        
        for row in rows:
            cols = row.find_elements(By.TAG_NAME, "td")
            if len(cols) >= 5:
                try:
                    ngay = cols[1].text.strip()
                    if ngay == TODAY or ngay == TOMORROW:
                        schedule_list.append({
                            "ngay_hoc": ngay, "mon_hoc": cols[2].text.strip(),
                            "phong_hoc": cols[4].text.strip(), "tiet": cols[5].text.strip(),
                            "giang_vien": cols[7].text.strip()
                        })
                except: continue

        data_output.update({"status": "success", "message": "Thanh cong", "lich_hoc": schedule_list})
        print(f"✅ Lay duoc {len(schedule_list)} tiet hoc.")

    except Exception as e:
        print(f"❌ Loi He Thong: {e}")
        data_output["message"] = f"Loi Crash: {str(e)}"
    finally:
        save_json(data_output)
        try: driver.quit()
        except: pass

if __name__ == "__main__":
    crawl_schedule_to_json()
