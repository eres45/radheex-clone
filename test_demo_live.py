import asyncio
from playwright.async_api import async_playwright

async def test_demo():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        page.on("response", lambda res: print(f"Response: {res.url} -> {res.status}") if "api" in res.url or "sso" in res.url else None)

        await page.goto("https://www.radheex.com")
        await page.wait_for_timeout(2000)

        # Click LOG IN
        await page.click("button:has-text('LOG IN')")
        await page.wait_for_timeout(1000)

        # Click Demo ID button
        print("Clicking Demo ID button...")
        demo_btn = page.locator("button:has-text('Demo ID'), #demoId").first
        await demo_btn.click()
        await page.wait_for_timeout(4000)

        # Take screenshot
        await page.screenshot(path="C:/Users/Ronit/.gemini/antigravity/brain/2e978b79-8d26-4bd9-b12e-006d8c592855/live_demo_click.png")

        # Check URL and localStorage / cookies
        cookies = await page.context.cookies()
        auth_cookie = [c for c in cookies if 'token' in c['name'].lower() or 'auth' in c['name'].lower()]
        print("Auth cookies:", auth_cookie)

        # Check DOM for logged in user
        user_text = await page.evaluate("""() => {
            return document.body.innerText.slice(0, 1000);
        }""")
        print("Page preview:\n", user_text[:300])

        await browser.close()

asyncio.run(test_demo())
