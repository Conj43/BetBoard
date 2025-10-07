from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    ElementClickInterceptedException,
    StaleElementReferenceException,
)
import csv
import time

URL = (
    "https://betiq.teamrankings.com/college-basketball/betting-trends/"
    "custom-trend-tool/?min_season=2021-2022&max_season=2021-2022"
)
OUTPUT_CSV = "2022BettingLinesCBB.csv"

# --- Config ---
HEADLESS = False        # set True if you want headless
PAGE_WAIT = 30          # seconds to wait for rows/changes
CLICK_DELAY = 0.4       # short polite pause after clicking next

# --- Setup driver ---
options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")
if HEADLESS:
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1920,1080")

driver = webdriver.Chrome(options=options)
wait = WebDriverWait(driver, PAGE_WAIT)

try:
    driver.get(URL)

    # wait for the table element and at least one data row to appear
    wait.until(EC.presence_of_element_located((By.ID, "custom-filter-table")))
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#custom-filter-table tbody tr")))

    table = driver.find_element(By.ID, "custom-filter-table")

    # --- Get headers once from the thead ---
    header_elems = table.find_elements(By.CSS_SELECTOR, "thead th")
    headers = [h.text.strip() for h in header_elems if h.text.strip()]
    if not headers:
        # fallback: infer column count from first visible data row
        first_data_row = driver.find_element(By.CSS_SELECTOR, "#custom-filter-table tbody tr")
        td_count = len(first_data_row.find_elements(By.TAG_NAME, "td"))
        headers = [f"col_{i+1}" for i in range(td_count)]

    # collect all rows (headers are stored separately)
    scraped_rows = []

    while True:
        # ensure rows present
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#custom-filter-table tbody tr")))

        # snapshot tbody html to detect change after navigation
        try:
            tbody = driver.find_element(By.CSS_SELECTOR, "#custom-filter-table tbody")
            old_html = tbody.get_attribute("innerHTML")
        except Exception:
            old_html = ""

        # collect current page rows
        row_elems = driver.find_elements(By.CSS_SELECTOR, "#custom-filter-table tbody tr")
        for tr in row_elems:
            try:
                cls = (tr.get_attribute("class") or "").lower()
                # skip DataTables "no data" placeholder row (class contains 'dataTables_empty')
                if "datatables_empty" in cls:
                    continue
                tds = tr.find_elements(By.TAG_NAME, "td")
                cells = [td.text.strip() for td in tds]
                if cells:
                    scraped_rows.append(cells)
            except StaleElementReferenceException:
                continue

        # try to click the DataTables "Next" control with id "<tableid>_next"
        next_clicked = False
        try:
            next_btn = driver.find_element(By.ID, "custom-filter-table_next")
            btn_class = (next_btn.get_attribute("class") or "").lower()
            aria_disabled = (next_btn.get_attribute("aria-disabled") or "").lower()
            if ("disabled" in btn_class) or (aria_disabled == "true"):
                # last page reached
                break

            # click (try normal click, fall back to JS)
            try:
                next_btn.click()
            except ElementClickInterceptedException:
                driver.execute_script("arguments[0].click();", next_btn)
            except Exception:
                driver.execute_script("arguments[0].click();", next_btn)

            next_clicked = True
        except NoSuchElementException:
            # fallback: try common DataTables next selector
            try:
                alt = driver.find_element(By.CSS_SELECTOR, ".dataTables_paginate .next, .paginate_button.next")
                alt_class = (alt.get_attribute("class") or "").lower()
                if "disabled" in alt_class:
                    break
                try:
                    alt.click()
                except ElementClickInterceptedException:
                    driver.execute_script("arguments[0].click();", alt)
                next_clicked = True
            except Exception:
                # no next control found -> stop
                next_clicked = False

        if not next_clicked:
            break

        # wait until the tbody content changes (new page)
        try:
            wait.until(lambda d: d.find_element(By.CSS_SELECTOR, "#custom-filter-table tbody").get_attribute("innerHTML") != old_html)
        except TimeoutException:
            # no change within timeout -> assume end
            break

        time.sleep(CLICK_DELAY)

    # --- After scraping all pages: delete every other row ---
    # scraped_rows is a list of data-rows (no header). 
    # Per request: remove every other row (keep the 1st of each adjacent duplicate pair).
    # We'll keep indices 0,2,4,... from scraped_rows (these correspond to overall CSV rows 1,3,5,...).
    cleaned_data_rows = [scraped_rows[i] for i in range(len(scraped_rows)) if i % 2 == 0]

    # prepare final output: headers + cleaned rows
    output_rows = [headers] + cleaned_data_rows

    # --- Save CSV ---
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(output_rows)

    print(f"Done — scraped {len(scraped_rows)} raw rows, kept {len(cleaned_data_rows)} after removing every other. Saved to: {OUTPUT_CSV}")

finally:
    driver.quit()