import asyncio
from playwright.async_api import async_playwright

async def check_live_stream_loading():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        print("Opening Wellington Firebirds v Northern Districts live match detail...")
        await page.goto("http://127.0.0.1:5005/#/live/36264203", wait_until="networkidle")
        await page.wait_for_timeout(2000)

        # Click Live Video button
        print("Clicking Live Video tab...")
        await page.click("#btnTvStream")
        await page.wait_for_timeout(3500)

        # Check iframe src
        iframe_src = await page.evaluate("""() => {
            const frame = document.querySelector('#tvFrame');
            return frame ? frame.getAttribute('src') : 'No iframe';
        }""")
        print(f"Loaded iframe src: {iframe_src}")

        # Screenshot
        await page.screenshot(path="C:/Users/Ronit/.gemini/antigravity/brain/2e978b79-8d26-4bd9-b12e-006d8c592855/live_tv_stream_actual_loading.png")
        print("Captured live_tv_stream_actual_loading.png")

        await browser.close()

asyncio.run(check_live_stream_loading())
