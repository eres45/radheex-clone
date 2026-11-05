import asyncio
import json
from playwright.async_api import async_playwright

async def explore():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1366, 'height': 800})
        page = await context.new_page()

        # Intercept and log all api calls
        api_calls = []
        page.on("request", lambda r: api_calls.append({"url": r.url, "method": r.method, "post_data": r.post_data}) if "api" in r.url or "manage" in r.url or "market" in r.url else None)

        print("1. Opening radheex.com and logging in with Demo ID...")
        await page.goto("https://www.radheex.com")
        await page.wait_for_timeout(2000)

        await page.click("button:has-text('LOG IN')")
        await page.wait_for_timeout(1000)

        demo_btn = page.locator("button:has-text('Demo ID'), #demoId").first
        await demo_btn.click()
        await page.wait_for_timeout(4000)

        # 1. Click user balance/account dropdown
        print("2. Inspecting Account dropdown menu...")
        # Check elements near top right
        user_area = page.locator(".dropdown-toggle, [id*='user'], [class*='coin'], [class*='balance']").first
        if await user_area.count() > 0:
            await user_area.click()
            await page.wait_for_timeout(1000)
            await page.screenshot(path="C:/Users/Ronit/.gemini/antigravity/brain/2e978b79-8d26-4bd9-b12e-006d8c592855/live_account_dropdown.png")

        # Extract account menu items
        menu_items = await page.evaluate("""() => {
            return Array.from(document.querySelectorAll('.dropdown-menu a, .dropdown-item, .user-menu a, [class*=\"menu\"] a')).map(a => ({
                text: a.innerText.trim(),
                href: a.getAttribute('href') || ''
            }));
        }""")
        print("Account menu items:", menu_items)

        # 2. Open an event detail page (e.g. WBBL or Wellington)
        print("3. Navigating to event detail page...")
        first_event = page.locator("tr.match-row, [data-event], .eventInfo").first
        if await first_event.count() > 0:
            await first_event.click()
            await page.wait_for_timeout(3500)
            await page.screenshot(path="C:/Users/Ronit/.gemini/antigravity/brain/2e978b79-8d26-4bd9-b12e-006d8c592855/live_event_detail_page.png")

            # Click a Back odds button to open betslip
            print("4. Clicking odds button to trigger betslip...")
            back_btn = page.locator(".btn-back, button.back, [class*='back']").first
            if await back_btn.count() > 0:
                await back_btn.click()
                await page.wait_for_timeout(1500)
                await page.screenshot(path="C:/Users/Ronit/.gemini/antigravity/brain/2e978b79-8d26-4bd9-b12e-006d8c592855/live_betslip_open.png")

        # Save all network calls captured
        with open("live_api_calls.json", "w", encoding="utf-8") as f:
            json.dump(api_calls, f, indent=2)

        await browser.close()
        print("Exploration finished successfully!")

asyncio.run(explore())
