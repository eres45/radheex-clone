import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1366, 'height': 800})
        page = await context.new_page()

        # 1. Check Home & Sidebar
        print("Navigating to Home...")
        await page.goto("http://127.0.0.1:5005/#/home", wait_until="networkidle")
        await page.wait_for_timeout(2000)
        await page.screenshot(path="C:/Users/Ronit/.gemini/antigravity/brain/2e978b79-8d26-4bd9-b12e-006d8c592855/clone_final_no_emojis_home.png")
        print("Captured clone_final_no_emojis_home.png")

        # 2. Check Casino Lobby & 6-column Visual Grid
        print("Navigating to Casino Lobby...")
        await page.goto("http://127.0.0.1:5005/#/casino", wait_until="networkidle")
        await page.wait_for_timeout(2000)
        await page.screenshot(path="C:/Users/Ronit/.gemini/antigravity/brain/2e978b79-8d26-4bd9-b12e-006d8c592855/clone_final_casino_all.png")
        print("Captured clone_final_casino_all.png")

        # Click Evolution tab
        evo_tab = page.locator('button[data-tab="evolution"]')
        if await evo_tab.count() > 0:
            await evo_tab.click()
            await page.wait_for_timeout(1000)
            await page.screenshot(path="C:/Users/Ronit/.gemini/antigravity/brain/2e978b79-8d26-4bd9-b12e-006d8c592855/clone_final_casino_evolution.png")
            print("Captured clone_final_casino_evolution.png")

        # Click Ezugi tab
        ezugi_tab = page.locator('button[data-tab="ezugi"]')
        if await ezugi_tab.count() > 0:
            await ezugi_tab.click()
            await page.wait_for_timeout(1000)
            await page.screenshot(path="C:/Users/Ronit/.gemini/antigravity/brain/2e978b79-8d26-4bd9-b12e-006d8c592855/clone_final_casino_ezugi.png")
            print("Captured clone_final_casino_ezugi.png")

        # 3. Check Live Event Detail & Live TV
        print("Navigating to Live Event Detail...")
        await page.goto("http://127.0.0.1:5005/#/live/28045743", wait_until="networkidle")
        await page.wait_for_timeout(2500)
        await page.screenshot(path="C:/Users/Ronit/.gemini/antigravity/brain/2e978b79-8d26-4bd9-b12e-006d8c592855/clone_final_live_tv_radar.png")
        print("Captured clone_final_live_tv_radar.png")

        # Switch to Live Video
        stream_btn = page.locator('#btnTvStream')
        if await stream_btn.count() > 0:
            await stream_btn.click()
            await page.wait_for_timeout(1000)
            await page.screenshot(path="C:/Users/Ronit/.gemini/antigravity/brain/2e978b79-8d26-4bd9-b12e-006d8c592855/clone_final_live_tv_video.png")
            print("Captured clone_final_live_tv_video.png")

        await browser.close()
        print("All screenshots successfully captured!")

asyncio.run(main())
