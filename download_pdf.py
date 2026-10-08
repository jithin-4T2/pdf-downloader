python
import os
import time
import requests
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
wait = WebDriverWait(driver, 20)

try:
    print("Connecting to the Kerala LOTIS portal...")
    driver.get(TARGET_URL)
    
    # 1. WAIT FOR AND SOLVE THE MATH CAPTCHA POP-UP
    print("Waiting for math equation verification pop-up to render...")
    try:
        # Wait up to 10 seconds for the input field to become visible
        input_box = wait.until(EC.visibility_of_element_located((By.XPATH, "//input[contains(@placeholder, 'answer')] | //input[@type='number']")))
        print("Math CAPTCHA pop-up detected successfully.")
        
        # Locate the math equation text node relative to the input field box
        # Using a reliable relative path to grab the mathematical expression text block
        equation_element = driver.find_element(By.XPATH, "//input[contains(@placeholder, 'answer')]/parent::div/preceding-sibling::div | //*[contains(text(), '* ') or contains(text(), ' + ') or contains(text(), ' - ')]")
        equation_text = equation_element.text.strip()
        
        # Clean string formatting characters
        clean_equation = equation_text.replace(' ', '').replace('x', '*').strip()
        print(f"Extracted math puzzle text: {clean_equation}")
        
        # Dynamically evaluate the math operations
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
            # Fallback evaluation parser if equation formatting changes slightly
            result = eval(clean_equation)
            
        print(f"Calculated arithmetic target solution response: {result}")
        
        # Type answer token string value directly into the input target box
        input_box.send_keys(str(result))
        time.sleep(1)
        
        # Locate the action trigger Submit element button and click it to dismiss the modal
        submit_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Submit')] | //input[@value='Submit'] | //*[contains(@class, 'submit') or contains(@type, 'submit')]")
        submit_btn.click()
        print("Math response submitted. Waiting for validation verification...")
        time.sleep(5)
        
    except Exception as modal_error:
        print(f"Modal validation bypass check pass or skipped: {str(modal_error)}")

    # 2. ISOLATE DOWNLOAD MECHANICS TARGETS
    print("Locating target results data table rows...")
    
    # Target the first structural table row element item cleanly
    first_row = wait.until(EC.presence_of_element_located((By.XPATH, "//table/tbody/tr")))
    
    # Safely pull description string from the second data cell column location to rename cleanly
    # (Extracting text column cell context to avoid blank index strings)
    cells = first_row.find_elements(By.XPATH, "./td")
    draw_name = cells[1].text if len(cells) > 1 else cells[0].text
    print(f"Targeting active published document title: {draw_name}")
    
    download_link = first_row.find_element(By.XPATH, ".//a[contains(text(), 'Download')]")
    
    driver.execute_script("arguments.click();", download_link)
    print("Download action deployed. Streaming PDF content...")
    time.sleep(25)

    # 3. VERIFY OUTPUT DIRECTORY FILES
    downloaded_files = os.listdir(DOWNLOAD_DIR)
    valid_files = [f for f in downloaded_files if not f.endswith('.crdownload') and f != "error_screenshot.png"]
    
    if valid_files:
        filename = valid_files[0]
        old_path = os.path.join(DOWNLOAD_DIR, filename)
        clean_name = f"{draw_name.replace('/', '-')}.pdf"
        new_path = os.path.join(DOWNLOAD_DIR, clean_name)
        
        os.rename(old_path, new_path)
        print(f"Asset synchronized completely: {clean_name}")
    else:
        raise Exception("Directory validation step failure. Chrome workspace returned zero values.")

except Exception as error:
    print(f"Automation block event hit: {str(error)}")
    driver.save_screenshot(os.path.join(DOWNLOAD_DIR, "error_screenshot.png"))
    raise error

finally:
    driver.quit()
