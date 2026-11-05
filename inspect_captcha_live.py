import asyncio
from playwright.async_api import async_playwright

async def inspect_captcha():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("https://www.radheex.com")
        await page.wait_for_timeout(2000)

        # Click LOG IN
        await page.click("button:has-text('LOG IN')")
        await page.wait_for_timeout(1000)

        # Inspect captcha HTML
        captcha_html = await page.evaluate("""() => {
            const el = document.querySelector('#solution, input[name=\"solution\"]');
            if (!el) return 'No solution input';
            const parent = el.closest('div');
            return parent ? parent.parentElement.innerHTML : 'No parent';
        }""")
        print("Captcha container HTML:")
        print(captcha_html)

        await browser.close()

asyncio.run(inspect_captcha())
