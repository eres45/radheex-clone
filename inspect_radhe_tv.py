from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1400, 'height': 900})
    
    reqs = []
    page.on('request', lambda r: reqs.append((r.resource_type, r.url)))
    
    page.goto('https://www.radheex.com/', wait_until='domcontentloaded')
    page.wait_for_timeout(3000)
    
    first_match = page.locator('tr').filter(has_text='v').first
    if first_match.count() > 0:
        print('First match text:', first_match.inner_text().replace('\n', ' ')[:100])
        first_match.click()
        page.wait_for_timeout(4000)
        print('URL after match click:', page.url)
        page.screenshot(path='radheex_clicked_match.png')
        
        iframes = page.locator('iframe')
        print('Iframes count:', iframes.count())
        for i in range(iframes.count()):
            print(f'Iframe {i}:', iframes.nth(i).get_attribute('src'))
            
        # Check all buttons or links on this match page
        buttons = page.locator('button, a, .tv, .l-tv, [id*="tv"], [class*="tv"]').all()
        print('Total potential TV elements:', len(buttons))
        for b in buttons:
            txt = b.inner_text().strip()
            cls = b.get_attribute('class') or ''
            id_ = b.get_attribute('id') or ''
            if 'tv' in (txt + cls + id_).lower() or 'stream' in (txt + cls + id_).lower() or 'score' in (txt + cls + id_).lower():
                print(f'Match element: text="{txt}", class="{cls}", id="{id_}"')
                try:
                    b.click()
                    page.wait_for_timeout(2000)
                    print('Clicked it!')
                except Exception as e:
                    pass
                    
        page.screenshot(path='radheex_after_all_clicks.png')
        iframes_final = page.locator('iframe')
        print('Final iframes count:', iframes_final.count())
        for i in range(iframes_final.count()):
            print(f'Final Iframe {i}:', iframes_final.nth(i).get_attribute('src'))

    print('\n--- All Stream / Media Requests ---')
    for t, u in reqs:
        if any(k in u.lower() for k in ['oddsdata', 'stream', 'hls', 'm3u8', 'video', 'tv', 'score']):
            print(f'[{t}] {u}')
            
    browser.close()
