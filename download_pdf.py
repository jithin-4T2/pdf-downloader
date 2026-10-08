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

# Enable headless download capability using Chrome DevTools Protocol
driver.execute_cdp_cmd(
    "Page.setDownloadBehavior",
    {"behavior": "allow", "downloadPath": DOWNLOAD_DIR}
)

wait = WebDriverWait(driver, 20)

try:
    print("Connecting to the Kerala LOTIS portal...")
    driver.get(TARGET_URL)
    
    # -------------------------------------------------------------
    # 1. SOLVE MATH CAPTCHA POP-UP
    # -------------------------------------------------------------
    print("Waiting for math equation verification pop-up...")
    
    # Locate answer input field inside the modal overlay
    input_box = wait.until(EC.visibility_of_element_located(
        (By.XPATH, "//input[@placeholder='Enter your answer']")
    ))
    print("Math CAPTCHA input located.")
    
    # Extract modal text containing the math expression (e.g., '2 * 10')
    modal_element = driver.find_element(
        By.XPATH, "//div[contains(@class, 'modal')] | //body"
    )
    modal_text = modal_element.text
    print(f"Modal text extracted: {modal_text}")

    # Extract two numbers and math operator using regex
    match = re.search(r'(\d+)\s*([\+\-\*\/xX])\s*(\d+)', modal_text)
    if match:
        num1, op, num2 = int(match.group(1)), match.group(2), int(match.group(3))
        if op in ('*', 'x', 'X'):
            result = num1 * num2
        elif op == '+':
            result = num1 + num2
        elif op == '-':
            result = num1 - num2
        elif op == '/':
            result = num1 // num2
        print(f"Parsed equation: {num1} {op} {num2} = {result}")
    else:
        raise ValueError("Failed to extract valid math equation from modal text.")
        
    # Input answer and submit
    input_box.clear()
    input_box.send_keys(str(result))
    
    submit_btn = driver.find_element(
        By.XPATH, "//button[contains(text(), 'Submit') or @type='submit']"
    )
    submit_btn.click()
    print("Math CAPTCHA answer submitted.")
    
    # Wait for the modal backdrop overlay to completely close
    wait.until(EC.invisibility_of_element_located(
        (By.XPATH, "//input[@placeholder='Enter your answer']")
    ))
    print("Modal successfully closed.")

    # -------------------------------------------------------------
    # 2. TRIGGER LATEST FILE DOWNLOAD
    # -------------------------------------------------------------
    print("Locating latest results row (Row 1)...")
    
    first_row = wait.until(EC.presence_of_element_located(
        (By.XPATH, "//table/tbody/tr[1]")
    ))
    
    draw_name = first_row.find_element(By.XPATH, "./td[2]").text.strip()
    print(f"Targeting latest result file: {draw_name}")
    
    # Click download link for row 1
    download_link = first_row.find_element(
        By.XPATH, ".//a[contains(text(), 'Download')] | .//button[contains(text(), 'Download')]"
    )
    driver.execute_script("arguments[0].click();", download_link)
    
    print("Download action triggered. Waiting for PDF file write...")
    
    # -------------------------------------------------------------
    # 3. VERIFY AND RENAME PDF
    # -------------------------------------------------------------
    download_timeout = 30
    downloaded_file = None
    start_time = time.time()
    
    while time.time() - start_time < download_timeout:
        files = os.listdir(DOWNLOAD_DIR)
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
        safe_draw_name = re.sub(r'[\\/*?:"<>|]', '-', draw_name)
        clean_name = f"{safe_draw_name}.pdf"
        new_path = os.path.join(DOWNLOAD_DIR, clean_name)
        
        os.rename(old_path, new_path)
        print(f"Latest PDF downloaded and saved to: {new_path}")
    else:
        raise Exception("Download failed: No completed PDF found in download directory.")

except Exception as error:
    print(f"Automation error: {str(error)}")
    driver.save_screenshot(os.path.join(DOWNLOAD_DIR, "error_screenshot.png"))
    raise error

finally:
    driver.quit()
