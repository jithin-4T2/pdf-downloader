import os
import time
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# --- SECURE CREDENTIALS FROM GITHUB SECRETS ---
TRUE_USER = os.environ.get("4t2industries@gmail.com")
TRUE_KEY = os.environ.get("zNpEm0GDWNlWBhSxYDsZ")

TARGET_URL = "https://kerala.gov.in"
DOWNLOAD_DIR = os.path.join(os.getcwd(), "lottery_results")

if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument("--headless=new") 
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--window-size=1920,1080")

# Strict preferences to force background downloading of PDF links on cloud runners
chrome_options.add_experimental_option("prefs", {
    "download.default_directory": DOWNLOAD_DIR,
    "download.prompt_for_download": False,
    "download.directory_upgrade": True,
    "plugins.always_open_pdf_externally": True,
    "pdfjs.disabled": True
})

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

try:
    print("Connecting to the Kerala LOTIS portal...")
    driver.get(TARGET_URL)
    time.sleep(8)  # Give full frame rendering time
    
    # 1. CAPTCHA DETECTOR CHECK
    captcha_frames = driver.find_elements(By.XPATH, "//iframe[contains(@src, 'recaptcha')]")
    captcha_containers = driver.find_elements(By.CLASS_NAME, "g-recaptcha")
    
    if captcha_frames or captcha_containers:
        print("CAPTCHA detected! Bypassing via TrueCaptcha...")
        site_key = captcha_containers[0].get_attribute("data-sitekey") if captcha_containers else captcha_frames[0].get_attribute("src").split("k=")[1].split("&")[0]
        
        captcha_payload = {
            "userid": TRUE_USER, "apikey": TRUE_KEY, "data": site_key, "pageurl": TARGET_URL, "type": "recaptcha"
        }
        response = requests.post("https://apitruecaptcha.org", json=captcha_payload).json()
        solved_token = response.get("result")
        
        if solved_token:
            driver.execute_script(f'document.getElementById("g-recaptcha-response").innerHTML="{solved_token}";')
            time.sleep(1)
            verify_btn = driver.find_elements(By.XPATH, "//button[contains(text(), 'Verify')] | //input[@type='submit']")
            if verify_btn:
                verify_btn[0].click()
                time.sleep(5)
    else:
        print("No CAPTCHA blocking active. Proceeding straight to table extraction...")

    # 2. TARGET THE FIRST GENUINE DOWNLOAD LINK ACCURATELY
    print("Locating target results data table...")
    wait = WebDriverWait(driver, 25)
    
    # Target the row specifically to read the name column (2nd cell) instead of serial number
    first_row = wait.until(EC.presence_of_element_located((By.XPATH, "//table//tbody/tr[1]")))
    
    # Extract the descriptive name (e.g., KARUNYA PLUS (KN-644))
    draw_name = first_row.find_element(By.XPATH, "./td[2]").text
    print(f"Targeting active published document: {draw_name}")
    
    # Specific click to target only the 'Download' text link element inside the row
    download_link = first_row.find_element(By.XPATH, ".//a[contains(text(), 'Download')]")
    
    # Use JavaScript click execution to override headless background blocking bugs
    driver.execute_script("arguments[0].click();", download_link)
    print("Download action triggered via JS. Waiting for file write buffer...")
    time.sleep(20)

    # 3. VERIFY ARCHIVE AND FINALIZE
    downloaded_files = os.listdir(DOWNLOAD_DIR)
    valid_files = [f for f in downloaded_files if not f.endswith('.crdownload') and f != "error_screenshot.png"]
    
    if valid_files:
        filename = valid_files[0]
        old_path = os.path.join(DOWNLOAD_DIR, filename)
        
        # Formulate a clean filename using the parsed draw name
        clean_name = f"{draw_name.replace('/', '-')}.pdf"
        new_path = os.path.join(DOWNLOAD_DIR, clean_name)
        
        os.rename(old_path, new_path)
        print(f"Asset synchronized successfully: {clean_name}")
    else:
        raise Exception("Chrome directory verification failed. No valid PDF document discovered.")

except Exception as error:
    print(f"Automation execution blocked: {str(error)}")
    driver.save_screenshot(os.path.join(DOWNLOAD_DIR, "error_screenshot.png"))
    raise error

finally:
    driver.quit()
