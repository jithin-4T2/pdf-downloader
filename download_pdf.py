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

# Enable CDP download behavior for headless Chrome
driver.execute_cdp_cmd(
    "Page.setDownloadBehavior",
    {"behavior": "allow", "downloadPath": DOWNLOAD_DIR}
)

wait = WebDriverWait(driver, 20)

try:
    print("Connecting to the Kerala LOTIS portal...")
    driver.get(TARGET_URL)
    
    # -------------------------------------------------------------
    # 1. TRIGGER DOWNLOAD TO OPEN MATH CAPTCHA MODAL
    # -------------------------------------------------------------
    print("Locating latest results row (Row 1)...")
    first_row = wait.until(EC.presence_of_element_located((By.XPATH, "//table/tbody/tr[1]")))
    
    draw_name = first_row.find_element(By.XPATH, "./td[2]").text.strip()
    print(f"Targeting latest result: {draw_name}")
    
    download_btn = first_row.find_element(
        By.XPATH, ".//a[contains(translate(text(), 'DOWNLOAD', 'download'), 'download')] | .//button[contains(translate(text(), 'DOWNLOAD', 'download'), 'download')]"
    )
    driver.execute_script("arguments[0].click();", download_btn)
    print("Download button clicked. Waiting for math CAPTCHA modal...")

    # -------------------------------------------------------------
    # 2. ISOLATE MODAL & SOLVE CAPTCHA EXCLUSIVELY
    # -------------------------------------------------------------
    # Wait for the modal dialog to be visible
    modal_dialog = wait.until(EC.visibility_of_element_located(
        (By.XPATH, "//div[contains(@class, 'modal-content') or contains(@class, 'modal-dialog') or @role='dialog']")
    ))
    
    input_box = modal_dialog.find_element(
        By.XPATH, ".//input[contains(translate(@placeholder, 'ANSWER', 'answer'), 'answer') or @type='number' or @type='text']"
    )

    # Extract text exclusively from the modal element
    modal_text = modal_dialog.text
    print(f"Modal content isolated: {repr(modal_text)}")

    # Extract numbers and operator specifically from the equation line (e.g., '2 * 10' or '15 + 4')
    # Reject dates or draw number patterns by enforcing a strict math equation regex
    match = re.search(r'(\d+)\s*([\+\-\*\/xX])\s*(\d+)', modal_text)
    if match:
        num1, op, num2 = int(match.group(1)), match.group(2), int(match.group(3))
        if op in ('*', 'x', 'X'): result = num1 * num2
        elif op == '+': result = num1 + num2
        elif op == '-': result = num1 - num2
        elif op == '/': result = num1 // num2
        print(f"Correctly extracted equation: {num1} {op} {num2} = {result}")
    else:
        raise ValueError(f"Could not parse valid math equation from modal content: {modal_text}")

    # Enter answer and submit inside modal context
    input_box.clear()
    input_box.send_keys(str(result))
    
    submit_btn = modal_dialog.find_element(
        By.XPATH, ".//button[contains(translate(text(), 'SUBMIT', 'submit'), 'submit') or @type='submit']"
    )
    submit_btn.click()
    print("Correct Captcha answer submitted. Awaiting PDF stream...")

    # -------------------------------------------------------------
    # 3. VERIFY AND SAVE VALID PDF
    # -------------------------------------------------------------
    download_timeout = 30
    valid_pdf_path = None
    start_time = time.time()
    
    while time.time() - start_time < download_timeout:
        files = os.listdir(DOWNLOAD_DIR)
        completed_files = [
            f for f in files 
            if not f.endswith('.crdownload') 
            and not f.endswith('.tmp') 
            and f != "error_screenshot.png"
        ]
        
        for candidate in completed_files:
            file_path = os.path.join(DOWNLOAD_DIR, candidate)
            # Verify valid PDF signature (%PDF header) and non-trivial size (> 10KB)
            if os.path.getsize(file_path) > 10240:
                with open(file_path, "rb") as f:
                    if f.read(4) == b"%PDF":
                        valid_pdf_path = file_path
                        break
        if valid_pdf_path:
            break
        time.sleep(1)

    if valid_pdf_path:
        safe_draw_name = re.sub(r'[\\/*?:"<>|]', '-', draw_name)
        clean_name = f"{safe_draw_name}.pdf"
        new_path = os.path.join(DOWNLOAD_DIR, clean_name)
        
        if valid_pdf_path != new_path:
            os.rename(valid_pdf_path, new_path)
            
        print(f"PDF verified and successfully saved to: {new_path}")
    else:
        raise Exception("Download failed: PDF was not received or corrupted.")

except Exception as error:
    print(f"Automation error: {str(error)}")
    driver.save_screenshot(os.path.join(DOWNLOAD_DIR, "error_screenshot.png"))
    raise error

finally:
    time.sleep(2)
    driver.quit()
