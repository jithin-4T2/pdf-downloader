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

# Enforce explicit configurations to capture PDF binary targets on headless servers
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
    time.sleep(12)  # Generous layout sleep for virtual instances
    
    # 1. OPTIONAL DEFENSTIVE CAPTCHA CHECKER
    captcha_frames = driver.find_elements(By.XPATH, "//iframe[contains(@src, 'recaptcha')]")
    captcha_containers = driver.find_elements(By.CLASS_NAME, "g-recaptcha")
    
    if captcha_frames or captcha_containers:
        print("CAPTCHA wall found! Communicating with TrueCaptcha bypass engine...")
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
        print("No dynamic CAPTCHA blocking present. Moving to core table parsing routine...")

    # 2. ISOLATE TARGET ROW ELEMENT STABLY
    print("Locating target data frames...")
    wait = WebDriverWait(driver, 35) # Expanded fallback tolerance window
    
    # Target the exact table body row structural layout element defensively
    first_row_xpath = "//table/tbody/tr["
    first_row = wait.until(EC.presence_of_element_located((By.XPATH, first_row_xpath)))
    
    # Extract structural lottery draw definition name data (2nd Column cell item)
    draw_name = first_row.find_element(By.XPATH, "./td").text
    print(f"Targeting active published document title: {draw_name}")
    
    # Specific click routine isolated onto the row action hyperlink item
    download_link = first_row.find_element(By.XPATH, ".//a[contains(text(), 'Download')]")
    
    # Native JS trigger prevents headless context rendering element collision errors
    driver.execute_script("arguments.click();", download_link)
    print("Download action deployed. Streaming PDF content directly onto server disk matrix...")
    time.sleep(25)

    # 3. VERIFY OUTPUT DIRECTORY FILES
    downloaded_files = os.listdir(DOWNLOAD_DIR)
    valid_files = [f for f in downloaded_files if not f.endswith('.crdownload') and f != "error_screenshot.png"]
    
    if valid_files:
        filename = valid_files
        old_path = os.path.join(DOWNLOAD_DIR, filename)
        
        # Format filename clean without slash dividers
        clean_name = f"{draw_name.replace('/', '-')}.pdf"
        new_path = os.path.join(DOWNLOAD_DIR, clean_name)
        
        os.rename(old_path, new_path)
        print(f"Asset synchronized completely: {clean_name}")
    else:
        raise Exception("Chrome directory verification step failure. Target write returned zero values.")

except Exception as error:
    print(f"Automation block event hit: {str(error)}")
    driver.save_screenshot(os.path.join(DOWNLOAD_DIR, "error_screenshot.png"))
    raise error

finally:
    driver.quit()
