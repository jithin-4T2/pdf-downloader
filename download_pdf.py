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
    "plugins.always_open_pdf_externally": True
})

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

try:
    print("Connecting to the Kerala LOTIS portal...")
    driver.get(TARGET_URL)
    time.sleep(7)  # Give the page initial time to load frames
    
    # 1. CHECK IF A CAPTCHA BOX IS BLOCKING THE CONTENT
    # Looking for Google reCAPTCHA frames or containers
    captcha_frames = driver.find_elements(By.XPATH, "//iframe[contains(@src, 'recaptcha')]")
    captcha_containers = driver.find_elements(By.CLASS_NAME, "g-recaptcha")
    
    if captcha_frames or captcha_containers:
        print("CAPTCHA wall detected! Extracting target data...")
        
        # Get the sitekey from the container attribute
        if captcha_containers:
            site_key = captcha_containers[0].get_attribute("data-sitekey")
        else:
            # Fallback parsing from the iframe src query string
            src = captcha_frames[0].get_attribute("src")
            site_key = src.split("k=")[1].split("&")[0]
            
        print(f"Sending sitekey to TrueCaptcha solver: {site_key}")
        
        # 2. SOLVE VIA TRUECAPTCHA API
        captcha_payload = {
            "userid": TRUE_USER,
            "apikey": TRUE_KEY,
            "data": site_key,
            "pageurl": TARGET_URL,
            "type": "recaptcha"
        }
        
        response = requests.post("https://apitruecaptcha.org", json=captcha_payload).json()
        solved_token = response.get("result")
        
        if not solved_token:
            raise Exception(f"TrueCaptcha processing failed. API Response: {response}")
            
        print("Bypass token retrieved from TrueCaptcha successfully!")
        
        # 3. INJECT TOKEN INTO THE RESPONSE FIELDS
        driver.execute_script(f'document.getElementById("g-recaptcha-response").innerHTML="{solved_token}";')
        time.sleep(1)
        
        # Click verification form button if it exists to refresh/unlock the table
        verify_btn = driver.find_elements(By.XPATH, "//button[contains(text(), 'Verify')] | //input[@type='submit']")
        if verify_btn:
            verify_btn[0].click()
            print("Token submitted. Waiting for page validation...")
            time.sleep(5)
    else:
        print("No CAPTCHA detected on initial load. Proceeding directly to table scraping...")

    # 4. DOWNLOAD THE NEWEST DOCUMENT ENTRY
    print("Locating target results data table...")
    wait = WebDriverWait(driver, 25)
    
    # Target any available Download links within the main table row body dynamically
    first_download_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//table//tbody/tr//a[contains(text(), 'Download')]")))
    
    # Grab row info text for cleaner file tracking names
    draw_details = driver.find_element(By.XPATH, "//table//tbody/tr/td[1]").text
    print(f"Targeting active published document: {draw_details}")
    
    first_download_btn.click()
    print("Download action triggered. Waiting for download tracking window buffer...")
    time.sleep(20) # Buffer to let the PDF completely write to disk inside the cloud virtual machine

    # 5. RENAME AND FINALIZE ASSETS
    downloaded_files = os.listdir(DOWNLOAD_DIR)
    # Filter out empty files or incomplete crdownload tracks
    valid_files = [f for f in downloaded_files if not f.endswith('.crdownload') and f != "error_screenshot.png"]
    
    if valid_files:
        filename = valid_files[0]
        old_path = os.path.join(DOWNLOAD_DIR, filename)
        clean_name = f"{draw_details.replace('/', '-')}.pdf"
        new_path = os.path.join(DOWNLOAD_DIR, clean_name)
        os.rename(old_path, new_path)
        print(f"Asset synchronized successfully: {clean_name}")
    else:
        raise Exception("Chrome directory verification failed. No valid PDF document discovered.")

except Exception as error:
    print(f"Automation execution blocked: {str(error)}")
    # Take an updated picture snapshot of the block for debug audits
    driver.save_screenshot(os.path.join(DOWNLOAD_DIR, "error_screenshot.png"))
    raise error

finally:
    driver.quit()
