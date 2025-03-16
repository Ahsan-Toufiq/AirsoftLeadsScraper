import time
import json
import csv
import os
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# Search terms for Airsoft Stores and Sites
SEARCH_TERMS = ["Airsoft store UK", "Airsoft shop UK", "Airsoft retailer UK",
                "Airsoft site UK", "Airsoft skirmish UK", "CQB Airsoft UK", "Outdoor Airsoft site UK"]

# Output file
OUTPUT_FILE = "airsoft_stores_sites.csv"

# Create screenshot folder
if not os.path.exists("screenshots"):
    os.makedirs("screenshots")

# Function to extract business details
def extract_business_details(page, index):
    try:
        # Wait for a visible name span as a signal that the detail view has loaded
        page.locator("h1 span").first.wait_for(timeout=15000)
        page.wait_for_timeout(1500)

        name = page.locator("h1 span").first.text_content() or ""

        phone = ""
        phone_el = page.locator("button[aria-label^='Call']")
        if phone_el.count():
            phone = phone_el.first.get_attribute("aria-label").replace("Call ", "")

        website = ""
        website_el = page.locator("a[aria-label^='Visit website']")
        if website_el.count():
            website = website_el.first.get_attribute("href")

        address = ""
        addr_el = page.locator("button[aria-label^='Copy address']")
        if addr_el.count():
            address = addr_el.first.get_attribute("aria-label").replace("Copy address", "")

        opening_hours = ""
        hours_block = page.locator("div[aria-label*='Opening hours'], div[aria-label*='Hours']")
        if hours_block.count():
            opening_hours = hours_block.first.text_content()

        details = {
            "Name": name.strip(),
            "Phone": phone.strip(),
            "Website": website.strip(),
            "Address": address.strip(),
            "Opening Hours": opening_hours.strip()
        }

        print("[SCRAPED]", json.dumps(details, indent=2))
        return details

    except Exception as e:
        print(f"Error extracting details for listing {index+1}: {e}")
        page.screenshot(path=f"screenshots/error_listing_{index+1}.png")
        return None

# Scroll until all listings are loaded
def scroll_until_all_loaded(page, max_scrolls=80):
    scrollable_div = page.locator("div[role='feed']")
    if scrollable_div.count() == 0:
        print("Scrollable container not found. Falling back to page scroll.")

    previous_count = -1
    same_count_repeats = 0
    scrolls = 0

    while scrolls < max_scrolls:
        business_cards = page.locator("div[class*='Nv2PK']")
        current_count = business_cards.count()

        if current_count == previous_count:
            same_count_repeats += 1
        else:
            same_count_repeats = 0

        if same_count_repeats >= 3:
            break  # no new listings in 3 tries

        previous_count = current_count

        try:
            if scrollable_div.count() > 0:
                scrollable_div.evaluate("el => el.scrollBy(0, el.scrollHeight)")
            else:
                page.mouse.wheel(0, 4000)
        except:
            pass

        time.sleep(2.0)
        scrolls += 1

    print(f"Scrolled {scrolls} times, found {previous_count} listings.")
    return previous_count

# Main scraping function
def scrape_google_maps():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=50)
        page = browser.new_page()

        all_results = []

        for search_term in SEARCH_TERMS:
            print(f"\n\n===== Searching for: {search_term} =====")
            search_url = f"https://www.google.com/maps/search/{search_term.replace(' ', '+')}"
            page.goto(search_url)
            time.sleep(6)

            try:
                page.locator("button:has-text('Accept all')").click(timeout=5000)
                print("Clicked cookie consent button.")
            except PlaywrightTimeoutError:
                pass

            try:
                print("Waiting for business listings to appear...")
                page.locator("div[class*='Nv2PK']").first.wait_for(timeout=15000)
            except PlaywrightTimeoutError:
                print("No business listings found after waiting. Moving to next search term.")
                continue

            total_count = scroll_until_all_loaded(page)
            business_cards = page.locator("div[class*='Nv2PK']")

            for index in range(total_count):
                try:
                    print(f"\nClicking listing {index+1}/{total_count}")
                    business_cards.nth(index).click()
                    page.wait_for_timeout(2000)
                    business_details = extract_business_details(page, index)
                    if business_details:
                        all_results.append(business_details)
                except Exception as e:
                    print(f"Error processing listing {index+1}: {e}")

        browser.close()

        with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["Name", "Phone", "Website", "Address", "Opening Hours"])
            writer.writeheader()
            writer.writerows(all_results)

        print(f"\nScraping complete. {len(all_results)} entries saved to {OUTPUT_FILE}")

# Run the scraper
scrape_google_maps()