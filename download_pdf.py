import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

TARGET_URL = "https://kerala.gov.in"
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
    time.sleep(10)  # Wait for page elements to load
    
    # 1. DETECT AND AUTOMATICALLY SOLVE THE MATH CAPTCHA POP-UP
    print("Checking for math equation verification pop-up...")
    
    # Search for text elements containing typical equation indicator structures
    equation_elements = driver.find_elements(By.XPATH, "//*[contains(text(), '*') or contains(text(), '+') or contains(text(), '-')]")
    
    # Target the modal specific elements visible in your screenshot
    modal_present = driver.find_elements(By.XPATH, "//*[contains(text(), 'solve the equation')]")
    
    if modal_present:
        print("Math CAPTCHA pop-up confirmed active.")
        
        # Isolate the exact equation text string element dynamically
        # Finds the text node sitting right above the text input field box
        equation_text = driver.find_element(By.XPATH, "//input[@placeholder='Enter your answer']/preceding-sibling::* | //input/parent::div/preceding-sibling::*").text
        
        # Cleanup string formatting spaces or cross symbols if present
        clean_equation = equation_text.replace(' ', '').replace('x', '*').strip()
        print(f"Extracted equation text from page layout: {clean_equation}")
        
        # Safely evaluate the arithmetic math problem mathematically
        if '*' in clean_equation:
            num1, num2 = clean_equation.split('*')
            result = int(num1) * int(num2)
        elif '+' in clean_equation:
            num1, num2 = clean_equation.split('+')
            result = int(num1) + int(num2)
        elif '-' in clean_equation:
            num1, num2 = clean_equation.split('-')
            result = int(num1) - int(num2)
        else:
            raise Exception(f"Unable to parse custom math structure format: {clean_equation}")
            
        print(f"Calculated arithmetic verification response: {result}")
        
        # Enter target evaluation numeric string into the input elements box
        input_box = driver.find_element(By.XPATH, "//input[@placeholder='Enter your answer'] | //input[@type='number']")
        input_box.send_keys(str(result))
        time.sleep(1)
        
        # Locate the action trigger Submit element button and click it to unlock layout rows
        submit_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Submit')] | //input[@value='Submit']")
        submit_btn.click()
        print("Math solution successfully provided. Waiting for page validation refresh...")
        time.sleep(5)

    # 2. ISOLATE DOWNLOAD MECHANICS TARGETS
    print("Locating target results data table rows...")
    wait = WebDriverWait(driver, 35)
    
    first_row = wait.until(EC.presence_of_element_located((By.XPATH, "//table/tbody/tr")))
    
    # Safely pull description string from the second data cell column location
    draw_name = first_row.find_element(By.XPATH, "./td").text
    print(f"Targeting active published document title: {draw_name}")
    
    download_link = first_row.find_element(By.XPATH, ".//a[contains(text(), 'Download')]")
    
    driver.execute_script("arguments.click();", download_link)
    print("Download action deployed. Streaming PDF onto background workspace layout folder...")
    time.sleep(25)

    # 3. VERIFY DISK DIRECTORY ASSETS
    downloaded_files = os.listdir(DOWNLOAD_DIR)
    valid_files = [f for f in downloaded_files if not f.endswith('.crdownload') and f != "error_screenshot.png"]
    
    if valid_files:
        filename = valid_files
        old_path = os.path.join(DOWNLOAD_DIR, filename)
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
