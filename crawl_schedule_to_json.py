import time
import json
import ddddocr
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import date, timedelta
import locale
import os
import sys

# --- CẤU HÌNH ---
URL_LOGIN = "https://mydtu.duytan.edu.vn/Signin.aspx"
URL_SCHEDULE = "https://mydtu.duytan.edu.vn/Sites/index.aspx?p=home_schedule"
USERNAME = "trancongsang1"
PASSWORD = "Alice#1691"
OUTPUT_FILE = "lich_hoc_hom_nay_va_mai.json" 
# ----------------

# Đặt locale tiếng Việt
try:
    locale.setlocale(locale.LC_TIME, 'vi_VN.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_TIME, 'vi_VN')
    except locale.Error:
        pass

def save_json(data):
    """Lưu dữ liệu vào file JSON"""
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"💾 Dữ liệu lịch học đã được lưu vào: {OUTPUT_FILE}")

def crawl_schedule_to_json():
    TODAY = date.today().strftime("%d/%m/%Y")
    TOMORROW = (date.today() + timedelta(days=1)).strftime("%d/%m/%Y")
    
    print(f"🚀 [CLOUD] Đang chạy lấy lịch cho Hôm nay ({TODAY}) và Ngày mai ({TOMORROW})...")
    
    # --- CẤU HÌNH HEADLESS CHO GITHUB ACTIONS ---
    options = webdriver.EdgeOptions()
    options.add_argument("--headless")  # BẮT BUỘC BẬT KHI CHẠY TRÊN GITHUB ACTIONS
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--log-level=3")
    options.add_argument("--window-size=1920,1080") # Đặt kích thước giả lập để tránh lỗi giao diện
    
    driver = webdriver.Edge(options=options)
    
    data_output = {
        "status": "error",
        "message": "Không thể hoàn thành tác vụ.",
        "ngay_lay": date.today().strftime("%d-%m-%Y %H:%M:%S"),
        "hom_nay": TODAY,
        "ngay_mai": TOMORROW,
        "lich_hoc": []
    }

    try:
        driver.get(URL_LOGIN)
        wait = WebDriverWait(driver, 15) # Tăng thời gian chờ lên 15s cho mạng server

        # --- BƯỚC 1: ĐĂNG NHẬP ---
        print("[...] Đang đăng nhập...")
        login_success = False
        max_retries = 15
        
        for i in range(max_retries):
            # 1. Điền User & Pass
            try:
                user_input = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input[id$='txtUser']")))
                user_input.clear()
                user_input.send_keys(USERNAME)
                
                pass_input = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
                pass_input.clear()
                pass_input.send_keys(PASSWORD)
            except:
                driver.refresh(); time.sleep(2); continue
            
            # 2. Xử lý Captcha
            try:
                captcha_img = driver.find_element(By.CSS_SELECTOR, ".login-form img, img[src*='Captcha']")
                
                # Chụp ảnh màn hình captcha để xử lý
                captcha_png = captcha_img.screenshot_as_png
                ocr = ddddocr.DdddOcr(show_ad=False)
                code = ocr.classification(captcha_png)
                
                if len(code) != 4: 
                    driver.find_element(By.CSS_SELECTOR, "img[src*='Captcha']").click() # Click đổi captcha mới
                    time.sleep(1)
                    continue
                
                print(f"   -> Thử lần {i+1}: Captcha đoán là '{code}'")
                driver.find_element(By.CSS_SELECTOR, "input[id$='txtCaptcha']").clear()
                driver.find_element(By.CSS_SELECTOR, "input[id$='txtCaptcha']").send_keys(code)
                
                # 3. Click Login
                driver.find_element(By.CSS_SELECTOR, "input[type='submit'], input[id$='btnLogin']").click()
                time.sleep(3) # Chờ load trang
                
                if "Signin.aspx" not in driver.current_url:
                    print("✅ Đăng nhập thành công!")
                    login_success = True
                    break
                else:
                    # Nếu vẫn ở trang login -> Sai captcha hoặc pass -> Thử lại
                    pass
            except Exception as e:
                print(f"   -> Lỗi vòng lặp: {e}")
                driver.refresh()
        
        if not login_success:
            data_output["message"] = "❌ Đăng nhập thất bại sau nhiều lần thử."
            print("❌ Đăng nhập thất bại.")
            save_json(data_output)
            return

        # --- BƯỚC 2: CÀO VÀ PHÂN TÍCH LỊCH HỌC ---
        print("[...] Đang lấy dữ liệu lịch học...")
        driver.get(URL_SCHEDULE)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))
        
        rows = driver.find_elements(By.CSS_SELECTOR, "table.tbl-schedule tr") # Thêm class tbl-schedule cho chính xác
        if not rows:
             rows = driver.find_elements(By.CSS_SELECTOR, "table tr")

        schedule_list = []
        
        for row in rows:
            cols = row.find_elements(By.TAG_NAME, "td")
            
            if len(cols) >= 5: 
                try:
                    ngay_hoc = cols[1].text.strip()
                    # Chỉ lấy lịch của Hôm nay hoặc Ngày mai
                    if ngay_hoc == TODAY or ngay_hoc == TOMORROW:
                        lich_hoc = {
                            "ngay_hoc": ngay_hoc,                 
                            "thu_hoc": cols[0].text.strip(),
                            "mon_hoc": cols[2].text.strip(),
                            "phong_hoc": cols[4].text.strip(),
                            "tiet_bat_dau": cols[5].text.strip().split('-')[0].replace('Tiết ', ''), 
                            "tiet_ket_thuc": cols[5].text.strip().split('-')[-1],
                            "giang_vien": cols[7].text.strip()
                        }
                        if lich_hoc["mon_hoc"] != "":
                            schedule_list.append(lich_hoc)
                            
                except IndexError:
                    continue

        data_output["status"] = "success"
        data_output["message"] = f"Cập nhật thành công lúc {date.today().strftime('%H:%M')}"
        data_output["lich_hoc"] = schedule_list
        print(f"✅ Tìm thấy {len(schedule_list)} tiết học.")

    except Exception as e:
        print(f"❌ Lỗi hệ thống: {str(e)}")
        data_output["message"] = f"Lỗi Script: {str(e)}"
    finally:
        save_json(data_output)
        try:
             driver.quit()
        except:
             pass
        
        # --- QUAN TRỌNG: TẮT ĐẨY GIT TRONG PYTHON ---
        # Vì GitHub Actions sẽ tự thực hiện lệnh git push ở file YAML
        # Nên ta comment dòng này lại để tránh lỗi quyền truy cập.
        
        # print("\n[GIT] Đang đẩy dữ liệu...")
        # try:
        #     from deploy_git import push_to_github
        #     push_to_github()
        # except:
        #     print("⚠️ Bỏ qua bước Push trong Python (Đã có GitHub Actions lo).")

if __name__ == "__main__":
    crawl_schedule_to_json()