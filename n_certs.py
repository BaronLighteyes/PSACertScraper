from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time
import csv
import os

import undetected_chromedriver as uc
from seleniumbase import Driver

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from tqdm import tqdm

# # Set up Chrome options to appear as a regular browser
# chrome_options = Options()
# # chrome_options.add_argument("--headless")  # Run in headless mode (remove to see the browser)
# chrome_options.add_argument("--no-sandbox")
# chrome_options.add_argument("--disable-dev-shm-usage")
# # chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
# #                             "(KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36")

# Automatically download and manage ChromeDriver
# driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

chrome_options = Options()
prefs = {
    "profile.managed_default_content_settings.images": 2,
    "profile.managed_default_content_settings.stylesheets": 2,
    "profile.managed_default_content_settings.fonts": 2,
    "profile.managed_default_content_settings.cookies": 2,
}
chrome_options.add_experimental_option("prefs", prefs)
driver = Driver(undetected=True, headless=True)

# Ask the user what they want to do
print("Put cert numbers in a text file called \"certs.txt\" in the same folder as this program.")

input("Press enter when ready...")

# Open the file containing the cert numbers (one per line)
with open('certs.txt', 'r') as file:
    cert_numbers = [int(line.strip()) for line in file if line.strip()]


csv_file = "psa_certs.csv"
fieldnames = ["Cert Number", "Item Grade", "Label Type", "Reverse Cert/Barcode", 
              "Year", "Brand/Title", "Subject", "Card Number", "Category", "Variety/Pedigree"]
file_exists = os.path.exists(csv_file)
with open(csv_file, "a", newline="") as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    if not file_exists:
        writer.writeheader()

    for cert_num in tqdm(cert_numbers):
        url = f"https://www.psacard.com/cert/{cert_num}/psa"
        try:
            driver.get(url)
            try:
                # Wait for the page to load and the element to be present
                WebDriverWait(driver, 4).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "h3.text-subtitle2 + dl"))
                )
            except Exception as e:
                print(f"Cert {cert_num}: Timed out waiting for item info - {e}")
                continue

            # Basic 404 check
            if "404" in driver.title or "not found" in driver.page_source.lower():
                print(f"Cert {cert_num}: Page not found (404)")
                continue

            # Scrape all dt/dd pairs in the Item Information section
            data = {"Cert Number": cert_num}
            try:
                info_dl = driver.find_element(By.CSS_SELECTOR, "h3.text-subtitle2 + dl")
                rows = info_dl.find_elements(By.CSS_SELECTOR, "div.flex.w-full")

                for row in rows:
                    label = row.find_element(By.TAG_NAME, "dt").text.strip()
                    dd = row.find_element(By.TAG_NAME, "dd")

                    # Some values live in <p> tags (e.g. Label Type with Fugitive Ink text)
                    ps = dd.find_elements(By.TAG_NAME, "p")
                    if ps:
                        value = " ".join(p.text.strip() for p in ps if p.text.strip())
                    else:
                        value = dd.text.strip()

                    #make sure all labels added exist in the CSV fieldnames
                    if label in fieldnames:
                        data[label] = value
                    else:
                        print(f"Warning: Label '{label}' not in fieldnames, skipping.")

                #TODO: Handle Missing FieldNames

                #Add the card to CSV
                writer.writerow(data)
                csvfile.flush()  # Push to OS buffer
                os.fsync(csvfile.fileno())  # Push from OS buffer to disk

            except Exception as e:
                print(f"Cert {cert_num}: Failed to scrape item info - {e}")
                writer.writerow()

            # Respect crawl-delay
            # time.sleep(1)

        except Exception as e:
            print(f"Cert {cert_num}: Error occurred - {e}")

print("Scraping Complete.")
print("Data Stored in \"psa_certs.csv\"")
print("You may safely close this window")
# Close the browser
driver.quit()
