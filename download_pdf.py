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

# Enable download capability in Headless Chrome
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
    
    # Broadened locator to catch the input box regardless of minor attribute variations
    input_box = wait.until(EC.presence_of_element_located(
        (By.XPATH, "//input[contains(translate(@placeholder, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'answer') or @type='number' or @type='text']")
    ))
    print("Math CAPTCHA input element located.")
    
    # Ensure element is visible before interacting
    wait.until(EC.visibility_of(input_box))
    
    # Extract page or modal text containing the math problem
    page_text = driver.find_element(By.TAG_NAME, "body").text

    # Match equation pattern (e.g. "2 * 10" or "5 + 3")
    match = re.search(r'(\d+)\s*([\+\-\*\/xX])\s*(\d+)', page_text)
    if match:
        num1, op, num2 = int(match.group(1)), match.group(2), int(match.group(3))
        if op in ('*', 'x', 'X'): result = num1 * num2
        elif op == '+': result = num1 + num2
        elif op == '-': result = num1 - num2
        elif op == '/': result = num1 // num2
        print(f"Detected and calculated equation: {num1} {op} {num2} = {result}")
    else:
        raise ValueError(f"Could not parse equation from text: {page_text[:200]}")
        
    # Enter answer and submit
    input_box.clear()
    input_box.send_keys(str(result))
    
    submit_btn = driver.find_element(
        By.XPATH, "//button[contains(translate(text(), 'SUBMIT', 'submit'), 'submit') or @type='submit']"
    )
    submit_btn.click()
    print("Math CAPTCHA answer submitted.")
    
    # Wait for the input box/modal to close
    wait.until(EC.staleness_of(input_box) if False else EC.invisibility_of_element(input_box))
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
    
    download_link = first_row.find_element(
        By.XPATH, ".//a[contains(translate(text(), 'DOWNLOAD', 'download'), 'download')] | .//button[contains(translate(text(), 'DOWNLOAD', 'download'), 'download')]"
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
