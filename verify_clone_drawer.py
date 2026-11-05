import asyncio
from playwright.async_api import async_playwright

async def verify_clone_drawer():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1366, 'height': 800})
        page = await context.new_page()

        print("1. Opening clone and logging in...")
        await page.goto("http://127.0.0.1:5005/#/home", wait_until="networkidle")
        await page.wait_for_timeout(1000)

        # Open Login modal
        await page.click("#loginBtn")
        await page.wait_for_timeout(800)

        # Click Demo ID to log in
        await page.click("#demoIdBtn")
        await page.wait_for_timeout(2000)

        # Take screenshot of logged in header
        await page.screenshot(path="C:/Users/Ronit/.gemini/antigravity/brain/2e978b79-8d26-4bd9-b12e-006d8c592855/clone_logged_in_with_drawer_btn.png")
        print("Captured clone_logged_in_with_drawer_btn.png")

        # Click balance pill to open Right Account Drawer
        print("2. Opening Right Account Drawer...")
        await page.click("#openRightDrawerBtn")
        await page.wait_for_timeout(1000)
        await page.screenshot(path="C:/Users/Ronit/.gemini/antigravity/brain/2e978b79-8d26-4bd9-b12e-006d8c592855/clone_right_account_drawer.png")
        print("Captured clone_right_account_drawer.png")

        # Click Set Stake in drawer
        print("3. Opening Set Stake modal...")
        await page.click("#btnOpenSetStake")
        await page.wait_for_timeout(1000)
        await page.screenshot(path="C:/Users/Ronit/.gemini/antigravity/brain/2e978b79-8d26-4bd9-b12e-006d8c592855/clone_stake_modal.png")
        print("Captured clone_stake_modal.png")
        await page.click("#stakeClose")
        await page.wait_for_timeout(500)

        # Open drawer and click Rules
        print("4. Opening Rules modal...")
        await page.click("#userProfileBtn")
        await page.wait_for_timeout(800)
        await page.click("#btnOpenRules")
        await page.wait_for_timeout(1000)
        await page.screenshot(path="C:/Users/Ronit/.gemini/antigravity/brain/2e978b79-8d26-4bd9-b12e-006d8c592855/clone_rules_modal.png")
        print("Captured clone_rules_modal.png")

        await browser.close()
        print("All drawer & modal screenshots captured successfully!")

asyncio.run(verify_clone_drawer())
