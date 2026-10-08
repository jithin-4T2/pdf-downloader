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

# Configure Headless Chrome for GitHub Cloud Environment
chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument("--headless=new") 
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--window-size=1920,1080")

chrome_options.add_experimental_option("prefs", {
    "download.default_directory": DOWNLOAD_DIR,
    "download.prompt_for_download": False,
    "download.directory_upgrade": True,
    "plugins.always_open_pdf_externally": True  # Force download instead of view
})

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

try:
    print("Opening Kerala Lottery public portal...")
    driver.get(TARGET_URL)
    
    print("Waiting for results table to load...")
    wait = WebDriverWait(driver, 20)
    
    # Locate the download button in the very first row
    first_download_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//table[@id='DataTables_Table_0']/tbody/tr//a[contains(text(), 'Download')]")))
    
    # Get draw details to rename the file nicely
    draw_details = driver.find_element(By.XPATH, "//table[@id='DataTables_Table_0']/tbody/tr/td").text
    print(f"Targeting entry: {draw_details}")
    
    first_download_btn.click()
    print("Download clicked. Waiting for file to save...")
    time.sleep(15) 

    # Verify the download succeeded
    downloaded_files = os.listdir(DOWNLOAD_DIR)
    if downloaded_files:
        filename = downloaded_files[0]
        old_path = os.path.join(DOWNLOAD_DIR, filename)
        
        # Rename the file using the Draw Details (e.g., "FIFTY-FIFTY-FF-123.pdf")
        clean_name = f"{draw_details.replace('/', '-')}.pdf"
        new_path = os.path.join(DOWNLOAD_DIR, clean_name)
        
        os.rename(old_path, new_path)
        print(f"Successfully saved locally as: {clean_name}")
    else:
        print("Error: Download folder is empty.")

except Exception as e:
    print(f"An error occurred: {str(e)}")
    driver.save_screenshot("error_screenshot.png")

finally:
    driver.quit()
