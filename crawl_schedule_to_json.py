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

# --- CẤU HÌNH ---
URL_LOGIN = "https://mydtu.duytan.edu.vn/Signin.aspx"
URL_SCHEDULE = "https://mydtu.duytan.edu.vn/Sites/index.aspx?p=home_schedule"
USERNAME = "trancongsang1"
PASSWORD = "Alice#1691"
OUTPUT_FILE = "lich_hoc_hom_nay_va_mai.json"
# ----------------

# Đặt locale
try:
    locale.setlocale(locale.LC_TIME, 'vi_VN.UTF-8')
except:
    try: locale.setlocale(locale.LC_TIME, 'vi_VN')
    except: pass

def save_json(data):
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def crawl_schedule_to_json():
    TODAY = date.today().strftime("%d/%m/%Y")
    TOMORROW = (date.today() + timedelta(days=1)).strftime("%d/%m/%Y")
    
    print(f"🚀 [CHROME] Đang lấy lịch cho {TODAY} và {TOMORROW}...")
    
    # --- CẤU HÌNH CHROME CHO GITHUB ACTIONS ---
    options = webdriver.ChromeOptions()
    options.add_argument("--headless") 
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    
    # Tự động cài đặt Driver Chrome phù hợp
    driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)
    
    data_output = {
        "status": "error", "message": "Chưa chạy xong.",
        "ngay_lay": date.today().strftime("%d-%m-%Y %H:%M:%S"),
        "hom_nay": TODAY, "ngay_mai": TOMORROW, "lich_hoc": []
    }

    try:
        driver.get(URL_LOGIN)
        wait = WebDriverWait(driver, 20)

        # --- ĐĂNG NHẬP ---
        print("[...] Đang đăng nhập...")
        for i in range(15):
            try:
                wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input[id$='txtUser']"))).clear()
                driver.find_element(By.CSS_SELECTOR, "input[id$='txtUser']").send_keys(USERNAME)
                
                driver.find_element(By.CSS_SELECTOR, "input[type='password']").clear()
                driver.find_element(By.CSS_SELECTOR, "input[type='password']").send_keys(PASSWORD)
                
                # Xử lý Captcha
                captcha_img = driver.find_element(By.CSS_SELECTOR, ".login-form img, img[src*='Captcha']")
                code = ddddocr.DdddOcr(show_ad=False).classification(captcha_img.screenshot_as_png)
                
                if len(code) != 4:
                    driver.find_element(By.CSS_SELECTOR, "img[src*='Captcha']").click()
                    time.sleep(1); continue
                
                driver.find_element(By.CSS_SELECTOR, "input[id$='txtCaptcha']").clear()
                driver.find_element(By.CSS_SELECTOR, "input[id$='txtCaptcha']").send_keys(code)
                driver.find_element(By.CSS_SELECTOR, "input[type='submit'], input[id$='btnLogin']").click()
                time.sleep(3)
                
                if "Signin.aspx" not in driver.current_url:
                    print("✅ Đăng nhập thành công!")
                    break
            except:
                driver.refresh()
        else:
            print("❌ Đăng nhập thất bại hết số lần thử."); return

        # --- LẤY LỊCH ---
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
                            "ngay_hoc": ngay,
                            "mon_hoc": cols[2].text.strip(),
                            "phong_hoc": cols[4].text.strip(),
                            "tiet": cols[5].text.strip(),
                            "giang_vien": cols[7].text.strip()
                        })
                except: continue

        data_output.update({"status": "success", "message": "Thành công", "lich_hoc": schedule_list})
        print(f"✅ Lấy được {len(schedule_list)} tiết học.")

    except Exception as e:
        print(f"❌ Lỗi: {e}")
    finally:
        save_json(data_output)
        try: driver.quit()
        except: pass

if __name__ == "__main__":
    crawl_schedule_to_json()
