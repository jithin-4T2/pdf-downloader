import os
import time
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# --- SECURE CREDENTIALS LOADED FROM ENV ---
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
    print("Connecting to the portal...")
    driver.get(TARGET_URL)
    time.sleep(5)
    
    # 1. CHECK IF A CAPTCHA BOX EXISTS ON THE PAGE
    captcha_elements = driver.find_elements(By.CLASS_NAME, "g-recaptcha")
    
    if captcha_elements:
        print("CAPTCHA wall detected! Extracting sitekey parameter...")
        # Automatically pull the 'data-sitekey' element embedded in the form
        site_key = captcha_elements[0].get_attribute("data-sitekey")
        
        # 2. SOLVE CAPTCHA VIA TRUECAPTCHA API
        print(f"Sending sitekey to TrueCaptcha solver: {site_key}")
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
            raise Exception(f"TrueCaptcha failed to solve. API Response: {response}")
            
        print("TrueCaptcha bypass token retrieved successfully!")
        
        # 3. INJECT THE CAPTCHA RESPONSE
        driver.execute_script(f'document.getElementById("g-recaptcha-response").innerHTML="{solved_token}";')
        time.sleep(1)
        
        # Click the page verify or form submit button to unlock the page contents
        # Adjusting specifically for standard LOTIS layout forms
        submit_btn = driver.find_elements(By.XPATH, "//button[@type='submit'] | //input[@type='submit']")
        if submit_btn:
            submit_btn[0].click()
            print("Submitted verification token. Waiting for table access...")
            time.sleep(5)

    # 4. DOWNLOAD THE NEWEST DOCUMENT ENTRY
    print("Locating target results data table...")
    wait = WebDriverWait(driver, 20)
    first_download_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//table[@id='DataTables_Table_0']/tbody/tr//a[contains(text(), 'Download')]")))
    
    draw_details = driver.find_element(By.XPATH, "//table[@id='DataTables_Table_0']/tbody/tr/td").text
    print(f"Downloading current published entry: {draw_details}")
    
    first_download_btn.click()
    time.sleep(15) # Allow downloading window buffer stream

    # 5. RENAME AND SYNC FILE
    downloaded_files = os.listdir(DOWNLOAD_DIR)
    if downloaded_files:
        filename = downloaded_files[0]
        old_path = os.path.join(DOWNLOAD_DIR, filename)
        clean_name = f"{draw_details.replace('/', '-')}.pdf"
        new_path = os.path.join(DOWNLOAD_DIR, clean_name)
        os.rename(old_path, new_path)
        print(f"File verified and ready for commit: {clean_name}")
    else:
        raise Exception("Chrome workspace directory is empty. Download trigger failed.")

except Exception as error:
    print(f"Automation execution blocked: {str(error)}")
    driver.save_screenshot("lottery_results/error_screenshot.png")
    raise error

finally:
    driver.quit()
