import os
import time
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

TARGET_URL = "https://www.lotteryagent.kerala.gov.in/result/public/"
DOWNLOAD_DIR = os.path.join(os.getcwd(), "lottery_results")

if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

# Configure Headless Chrome options
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
    
    # -------------------------------------------------------------
    # 1. SOLVE MATH CAPTCHA POP-UP
    # -------------------------------------------------------------
    print("Waiting for math equation verification pop-up...")
    try:
        # Wait for the input box inside the modal
        input_box = wait.until(EC.visibility_of_element_located(
            (By.XPATH, "//input[@placeholder='Enter your answer' or @type='number']")
        ))
        print("Math CAPTCHA detected.")
        
        # Locate the math equation text node
        equation_element = driver.find_element(
            By.XPATH, "//input[@placeholder='Enter your answer']/preceding-sibling::*[1] | //*[contains(text(), '*') or contains(text(), '+') or contains(text(), '-')]"
        )
        equation_text = equation_element.text.strip()
        print(f"Extracted puzzle text: {equation_text}")

        # Extract numbers and operator cleanly using regex
        match = re.search(r'(\d+)\s*([\+\-\*\/])\s*(\d+)', equation_text)
        if match:
            num1, op, num2 = int(match.group(1)), match.group(2), int(match.group(3))
            if op == '*': result = num1 * num2
            elif op == '+': result = num1 + num2
            elif op == '-': result = num1 - num2
            elif op == '/': result = num1 // num2
        else:
            # Fallback evaluation
            clean_eq = equation_text.replace('x', '*').replace(' ', '')
            result = eval(clean_eq)
            
        print(f"Calculated answer: {result}")
        
        # Enter answer and submit
        input_box.clear()
        input_box.send_keys(str(result))
        
        submit_btn = driver.find_element(
            By.XPATH, "//button[contains(text(), 'Submit')] | //button[@type='submit']"
        )
        submit_btn.click()
        print("Math response submitted.")
        
        # Wait briefly for modal overlay to disappear
        time.sleep(2)
        
    except Exception as modal_error:
        print(f"Modal check bypassed/skipped: {str(modal_error)}")

    # -------------------------------------------------------------
    # 2. ISOLATE DOWNLOAD MECHANICS & TRIGGER DOWNLOAD
    # -------------------------------------------------------------
    print("Locating target results data table rows...")
    
    # Wait for the table row to be interactive
    first_row = wait.until(EC.presence_of_element_located((By.XPATH, "//table/tbody/tr[1]")))
    
    # Get Draw Name from the 2nd column
    draw_name = first_row.find_element(By.XPATH, "./td[2]").text.strip()
    print(f"Targeting published document: {draw_name}")
    
    # Click download link
    download_link = first_row.find_element(By.XPATH, ".//a[contains(text(), 'Download')] | .//button[contains(text(), 'Download')]")
    driver.execute_script("arguments[0].click();", download_link)
    
    print("Download action deployed. Waiting for file transfer...")
    
    # -------------------------------------------------------------
    # 3. VERIFY AND RENAME DOWNLOADED FILE
    # -------------------------------------------------------------
    # Wait dynamically for download completion (up to 30 seconds)
    download_timeout = 30
    downloaded_file = None
    
    start_time = time.time()
    while time.time() - start_time < download_timeout:
        files = os.listdir(DOWNLOAD_DIR)
        # Filter out incomplete downloads and screenshot files
        completed_files = [
            f for f in files 
            if not f.endswith('.crdownload') 
            and not f.endswith('.tmp') 
            and f != "error_screenshot.png"
        ]
        if completed_files:
            downloaded_file = completed_files[0]
            break
        time.sleep(1)

    if downloaded_file:
        old_path = os.path.join(DOWNLOAD_DIR, downloaded_file)
        
        # Sanitize filename for operating system compatibility
        safe_draw_name = re.sub(r'[\\/*?:"<>|]', '-', draw_name)
        clean_name = f"{safe_draw_name}.pdf"
        new_path = os.path.join(DOWNLOAD_DIR, clean_name)
        
        os.rename(old_path, new_path)
        print(f"Asset synchronized successfully: {clean_name}")
    else:
        raise Exception("Download failed: No valid file found in download directory after waiting.")

except Exception as error:
    print(f"Automation error encountered: {str(error)}")
    driver.save_screenshot(os.path.join(DOWNLOAD_DIR, "error_screenshot.png"))
    raise error

finally:
    driver.quit()
