import asyncio
import re
from playwright.async_api import async_playwright

async def deep_audit():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1366, 'height': 800}
        )
        page = await context.new_page()

        print("1. Opening radheex.com...")
        await page.goto("https://www.radheex.com", wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(2000)

        # Open Login Modal
        login_btn = page.locator("button:has-text('LOG IN')").first
        if await login_btn.count() > 0:
            await login_btn.click()
            await page.wait_for_timeout(1000)

        # Fill credentials
        print("2. Filling Mataji060...")
        user_input = page.locator("input[placeholder='User ID'], input[name='uid']").first
        pass_input = page.locator("input[placeholder='Password'], input[name='passcode']").first
        captcha_input = page.locator("input[placeholder='Solve captcha'], input[name='solution']").first
        
        await user_input.fill("Mataji060")
        await pass_input.fill("ronit123")

        # Solve captcha
        captcha_text = await page.evaluate("""() => {
            const divs = document.querySelectorAll('div');
            for (const d of divs) {
                if (/\\d+\\s*[\\+\\-]\\s*\\d+\\s*=/.test(d.innerText)) {
                    return d.innerText;
                }
            }
            return '';
        }""")
        print(f"Detected math challenge: '{captcha_text}'")
        m = re.search(r'(\d+)\s*([\+\-])\s*(\d+)', captcha_text)
        if m:
            n1, op, n2 = int(m.group(1)), m.group(2), int(m.group(3))
            ans = n1 + n2 if op == '+' else n1 - n2
            print(f"Solved math captcha: {n1} {op} {n2} = {ans}")
            await captcha_input.fill(str(ans))

        # Click Login
        login_submit = page.locator("button:has-text('Login')").first
        await login_submit.click()
        print("Submitted login form...")

        # Wait for post-login
        await page.wait_for_timeout(5000)

        # Screenshot post-login home
        await page.screenshot(path="C:/Users/Ronit/.gemini/antigravity/brain/2e978b79-8d26-4bd9-b12e-006d8c592855/live_radheex_logged_in.png")
        print("Captured live_radheex_logged_in.png")

        # Click user profile menu
        user_dropdown = page.locator(".dropdown, [class*='user'], [class*='profile'], [class*='balance']").first
        user_menu_items = await page.evaluate("""() => {
            return Array.from(document.querySelectorAll('a, button, li')).map(el => el.innerText.trim()).filter(t => t.length > 0 && t.length < 50);
        }""")
        print(f"Page text elements count: {len(user_menu_items)}")

        # Try navigating to In-Play
        print("3. Navigating to In-Play on live site...")
        inplay_link = page.locator("a:has-text('In-Play'), button:has-text('In-Play')").first
        if await inplay_link.count() > 0:
            await inplay_link.click()
            await page.wait_for_timeout(3000)
            await page.screenshot(path="C:/Users/Ronit/.gemini/antigravity/brain/2e978b79-8d26-4bd9-b12e-006d8c592855/live_radheex_inplay.png")
            print("Captured live_radheex_inplay.png")

        # Try clicking first match
        first_match = page.locator("tr.match-row, .match-table tr, .event-row, a[href*='game']").first
        if await first_match.count() > 0:
            print("Clicking first match...")
            await first_match.click()
            await page.wait_for_timeout(4000)
            await page.screenshot(path="C:/Users/Ronit/.gemini/antigravity/brain/2e978b79-8d26-4bd9-b12e-006d8c592855/live_radheex_match_detail.png")
            print("Captured live_radheex_match_detail.png")

        await browser.close()
        print("Deep audit complete!")

asyncio.run(deep_audit())
