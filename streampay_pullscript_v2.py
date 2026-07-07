import asyncio
import gspread
import os
from datetime import datetime
from playwright.async_api import async_playwright

# --- CONFIG ---
PHONE_NUM = os.environ["PHONE_NUM"]
STATIC_OTP = os.environ["STATIC_OTP"]
SHEET_NAME = os.environ["SHEET_NAME"]
URL = os.environ["LOGIN_URL"]

async def run_tracker():
    async with async_playwright() as p:
        # Using a real-looking user agent to avoid bot detection
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Starting run...")
        await page.goto(URL)

        # STEP 1: Phone Number
        try:
            phone_selector = "input.creo-input" 
            await page.wait_for_selector(phone_selector, timeout=15000)
            
            # Click and "Type" instead of "Fill" to trigger the site's logic
            await page.click(phone_selector)
            await page.type(phone_selector, PHONE_NUM, delay=100)
            
            # Find the button more broadly - looking for anything clickable that isn't the input
            # Often these buttons don't have text, just an arrow or icon
            login_btn = page.locator('button, [role="button"], .login-phone-row + button').first
            await login_btn.click()
            
            print("Phone number submitted.")
        except Exception as e:
            print(f"Failed at Phone step: {e}")
            await page.screenshot(path="error_phone.png")
            await browser.close()
            return

 # STEP 2: Segmented OTP
        try:
            print("Waiting for OTP boxes...")
            await page.wait_for_selector(".login-otp-cell", timeout=20000)
            otp_cells = page.locator(".login-otp-cell")

            for i in range(len(STATIC_OTP)):
                await otp_cells.nth(i).fill(STATIC_OTP[i])
            
            # --- THE FIX: Click the 'Verify code' button specifically ---
            print("Clicking Verify Button...")
            verify_btn = page.get_by_role("button", name="Verify code")
            await verify_btn.click()
            
            # Wait for the URL to change to the dashboard
            await page.wait_for_load_state("networkidle")
            print("OTP submitted. Dashboard should be loading.")
        except Exception as e:
            print(f"Failed at OTP step: {e}")
            await page.screenshot(path="error_otp.png")
            await browser.close()
            return

        # STEP 3: Scrape
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(10000) 

        try:
            # Grab the text
            raw_w1 = await page.locator(".kobox-creator-balance-value").first.inner_text()
            raw_w2 = await page.locator(".home-balance-amount").first.inner_text()
            
            # CLEANING LOGIC: Remove ₦, commas, and spaces
            def clean_to_float(val):
                # Remove symbols and commas, then convert to a float (number)
                clean_val = val.replace("₦", "").replace(",", "").strip()
                try:
                    return float(clean_val)
                except:
                    return val # Return raw if it fails
            
            wallet1 = clean_to_float(raw_w1)
            wallet2 = clean_to_float(raw_w2)
            
            print(f"Cleaned Values: {wallet1} | {wallet2}")
        except Exception as e:
            print(f"Scrape failed: {e}")
            wallet1, wallet2 = 0, 0
            

        # STEP 4: Google Sheets
        try:
            gc = gspread.service_account(filename='service_account.json')
            sh = gc.open(SHEET_NAME).sheet1
            new_row = [datetime.now().strftime("%Y-%m-%d %H:%M"), wallet1, wallet2]
            sh.append_row(new_row)
            print("✅ Data successfully sent to Sheets.")
        except Exception as e:
            print(f"Sheets Error: {e}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_tracker())
