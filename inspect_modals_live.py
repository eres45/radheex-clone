import asyncio
from playwright.async_api import async_playwright

async def inspect_modals():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        await page.goto("https://www.radheex.com")
        await page.wait_for_timeout(2000)

        # Login with Demo ID
        await page.click("button:has-text('LOG IN')")
        await page.wait_for_timeout(1000)
        await page.click("button:has-text('Demo ID'), #demoId")
        await page.wait_for_timeout(3000)

        # Click user profile to open right drawer
        await page.click("[class*='coin'], [class*='balance'], .dropdown-toggle")
        await page.wait_for_timeout(1000)

        # Check if Rules button exists in drawer
        rules_btn = page.locator("a:has-text('Rules'), button:has-text('Rules')").first
        if await rules_btn.count() > 0:
            print("Clicking Rules button...")
            await rules_btn.click()
            await page.wait_for_timeout(1500)
            await page.screenshot(path="C:/Users/Ronit/.gemini/antigravity/brain/2e978b79-8d26-4bd9-b12e-006d8c592855/live_rules_modal.png")

        await browser.close()
        print("Modal inspection complete!")

asyncio.run(inspect_modals())
