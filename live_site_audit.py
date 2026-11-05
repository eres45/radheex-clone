import asyncio
import json
from playwright.async_api import async_playwright

async def audit():
    results = {}
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1366, 'height': 800}
        )
        page = await context.new_page()

        network_requests = []
        page.on("request", lambda req: network_requests.append({
            "url": req.url,
            "method": req.method,
            "resource_type": req.resource_type
        }))

        print("1. Opening https://www.radheex.com...")
        try:
            resp = await page.goto("https://www.radheex.com", wait_until="networkidle", timeout=30000)
            print(f"Page loaded, status: {resp.status if resp else 'unknown'}")
        except Exception as e:
            print(f"Goto error: {e}")

        await page.wait_for_timeout(3000)

        # Extract top nav links
        nav_links = await page.evaluate("""() => {
            const items = [];
            document.querySelectorAll('a, button').forEach(el => {
                const text = el.innerText.trim();
                const href = el.getAttribute('href');
                if (text && (href || el.tagName === 'BUTTON')) {
                    items.push({ text: text.replace(/\\n/g, ' '), href: href || '', tag: el.tagName });
                }
            });
            return items;
        }""")

        # Extract all sports / categories in menu
        sidebar_items = await page.evaluate("""() => {
            const items = [];
            document.querySelectorAll('.sidebar a, .side-menu a, .menu a, ul.nav a, aside a').forEach(el => {
                items.push({ text: el.innerText.trim().replace(/\\n/g, ' '), href: el.getAttribute('href') || '' });
            });
            return items;
        }""")

        # Extract footer links
        footer_links = await page.evaluate("""() => {
            const items = [];
            document.querySelectorAll('footer a').forEach(el => {
                items.push({ text: el.innerText.trim().replace(/\\n/g, ' '), href: el.getAttribute('href') || '' });
            });
            return items;
        }""")

        # Check login modal structure
        login_btn = page.locator("text=/Log\\s*In/i").first
        login_modal_info = {}
        if await login_btn.count() > 0:
            try:
                await login_btn.click()
                await page.wait_for_timeout(1500)
                login_modal_info = await page.evaluate("""() => {
                    const inputs = Array.from(document.querySelectorAll('input')).map(i => ({
                        type: i.type, placeholder: i.placeholder, name: i.name, id: i.id
                    }));
                    const buttons = Array.from(document.querySelectorAll('button')).map(b => b.innerText.trim());
                    return { inputs, buttons };
                }""")
            except Exception as e:
                print(f"Login modal click error: {e}")

        # Try logging in with Mataji060 / ronit123
        print("2. Attempting login on live site...")
        logged_in = False
        user_info = {}
        try:
            user_input = page.locator("input[placeholder*='User'], input[name*='user'], input[type='text']").first
            pass_input = page.locator("input[type='password']").first
            
            # Check captcha on live site
            captcha_el = page.locator("input[placeholder*='Captcha'], input[name*='captcha']")
            captcha_val = ""
            if await captcha_el.count() > 0:
                captcha_text = await page.evaluate("""() => {
                    const el = document.querySelector('.captcha, [class*="captcha"], #captcha');
                    return el ? el.innerText : '';
                }""")
                print(f"Detected live captcha text: {captcha_text}")

            if await user_input.count() > 0 and await pass_input.count() > 0:
                await user_input.fill("Mataji060")
                await pass_input.fill("ronit123")
                
                # Check if captcha needs solving
                if await captcha_el.count() > 0:
                    try:
                        # eval math
                        import re
                        m = re.search(r'(\d+)\s*([\+\-\*])\s*(\d+)', captcha_text)
                        if m:
                            n1, op, n2 = int(m.group(1)), m.group(2), int(m.group(3))
                            ans = n1 + n2 if op == '+' else (n1 - n2 if op == '-' else n1 * n2)
                            await captcha_el.fill(str(ans))
                    except Exception:
                        pass
                
                # Click submit
                submit_btn = page.locator("button:has-text('Login'), button[type='submit']").first
                if await submit_btn.count() > 0:
                    await submit_btn.click()
                    await page.wait_for_timeout(4000)

                    # Check user info
                    user_info = await page.evaluate("""() => {
                        const balanceEl = document.querySelector('[class*="balance"], [class*="coin"], .user-balance, .pts');
                        const expEl = document.querySelector('[class*="exposure"], .user-exp');
                        const userMenu = Array.from(document.querySelectorAll('.dropdown-menu a, .user-menu a, .account-menu a, select option')).map(a => a.innerText.trim());
                        return {
                            balanceText: balanceEl ? balanceEl.innerText : '',
                            expText: expEl ? expEl.innerText : '',
                            menuItems: userMenu
                        };
                    }""")
                    print(f"Logged in user info: {user_info}")
        except Exception as e:
            print(f"Login attempt error: {e}")

        # Capture live screenshot
        await page.screenshot(path="C:/Users/Ronit/.gemini/antigravity/brain/2e978b79-8d26-4bd9-b12e-006d8c592855/live_site_audit_screen.png")

        # Save audit dump
        audit_dump = {
            "nav_links_count": len(nav_links),
            "nav_links_sample": nav_links[:30],
            "sidebar_items": sidebar_items,
            "footer_links": footer_links,
            "login_modal_info": login_modal_info,
            "user_info": user_info,
            "network_endpoints": list(set(r['url'].split('?')[0] for r in network_requests if 'api' in r['url'] or 'radhe' in r['url'] or 'market' in r['url']))
        }

        with open("live_audit_dump.json", "w", encoding="utf-8") as f:
            json.dump(audit_dump, f, indent=2)
        print("Saved live_audit_dump.json")

        await browser.close()

asyncio.run(audit())
