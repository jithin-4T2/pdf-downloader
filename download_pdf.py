import os
import time
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# --- SECURE API TOKENS FROM SECRETS ENV ---
TRUE_USER = os.environ.get("4t2industries@gmail.com")
TRUE_KEY = os.environ.get("zNpEm0GDWNlWBhSxYDsZ")

TARGET_URL = "https://www.lotteryagent.kerala.gov.in/result/public/"
DOWNLOAD_DIR = os.path.join(os.getcwd(), "lottery_results")

if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument("--headless=new") 
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--window-size=1920,1080")

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
    time.sleep(12)
    
    # 1. DYNAMIC CAPTCHA INTERACTION LAYER
    captcha_frames = driver.find_elements(By.XPATH, "//iframe[contains(@src, 'recaptcha')]")
    captcha_containers = driver.find_elements(By.CLASS_NAME, "g-recaptcha")
    
    if captcha_frames or captcha_containers:
        print("CAPTCHA grid layout detected. Querying TrueCaptcha API credentials...")
        site_key = captcha_containers.get_attribute("data-sitekey") if captcha_containers else captcha_frames.get_attribute("src").split("k=").split("&")
        
        captcha_payload = {
            "userid": TRUE_USER, "apikey": TRUE_KEY, "data": site_key, "pageurl": TARGET_URL, "type": "recaptcha"
        }
        response = requests.post("https://apitruecaptcha.org", json=captcha_payload).json()
        solved_token = response.get("result")
        
        if solved_token:
            driver.execute_script(f'document.getElementById("g-recaptcha-response").innerHTML="{solved_token}";')
            time.sleep(2)
            verify_btn = driver.find_elements(By.XPATH, "//button[contains(text(), 'Verify')] | //input[@type='submit']")
            if verify_btn:
                verify_btn.click()
                time.sleep(6)
    else:
        print("No dynamic verification screen found. Accessing dynamic table rows directly...")

    # 2. RUN EXTRACTION AGAINST TARGET DATA COLUMNS DEFINED BY TARGET XPATH
    print("Parsing table entries...")
    wait = WebDriverWait(driver, 35)
    
    # Secure the explicit first data entry row element block container safely
    first_row = wait.until(EC.presence_of_element_located((By.XPATH, "//table/tbody/tr[1]")))
    
    # FIX: Point explicitly to the SECOND column cell (td[2]) to capture the Draw details string name
    draw_name = first_row.find_element(By.XPATH, "./td[2]").text
    print(f"Targeting active published document title: {draw_name}")
    
    # Target the download interactive link item safely relative inside this row block
    download_link = first_row.find_element(By.XPATH, ".//a[contains(text(), 'Download')]")
    
    # Trigger interaction sequence via native JavaScript execute commands
    driver.execute_script("arguments.click();", download_link)
    print("Download action deployed. Streaming PDF onto background storage directory...")
    time.sleep(25)

    # 3. LOCATE TARGET AND RENAME
    downloaded_files = os.listdir(DOWNLOAD_DIR)
    valid_files = [f for f in downloaded_files if not f.endswith('.crdownload') and f != "error_screenshot.png"]
    
    if valid_files:
        filename = valid_files
        old_path = os.path.join(DOWNLOAD_DIR, filename)
        
        # Clean formatting expression to remove unsafe file special separator symbols
        clean_name = f"{draw_name.replace('/', '-')}.pdf"
        new_path = os.path.join(DOWNLOAD_DIR, clean_name)
        
        os.rename(old_path, new_path)
        print(f"Asset synchronized completely: {clean_name}")
    else:
        raise Exception("Directory validation step failure. Chrome returned blank output fields.")

except Exception as error:
    print(f"Automation block event hit: {str(error)}")
    driver.save_screenshot(os.path.join(DOWNLOAD_DIR, "error_screenshot.png"))
    raise error

finally:
    driver.quit()
