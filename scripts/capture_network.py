import os
import sys
import json
import time
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "network-reverse"))
RESPONSES_DIR = os.path.join(OUTPUT_DIR, "responses")
os.makedirs(RESPONSES_DIR, exist_ok=True)

captured_requests = []
captured_responses = {}
websocket_messages = []
captured_assets = {
    "images": set(),
    "svgs": set(),
    "fonts": set(),
    "scripts": set(),
    "stylesheets": set(),
    "api_endpoints": set(),
}

def on_request(request):
    url = request.url
    method = request.method
    resource_type = request.resource_type
    
    parsed = urlparse(url)
    ext = os.path.splitext(parsed.path)[1].lower()
    
    if resource_type == "image" or ext in [".png", ".jpg", ".jpeg", ".webp", ".gif", ".ico"]:
        captured_assets["images"].add(url)
    elif ext == ".svg" or "svg" in url:
        captured_assets["svgs"].add(url)
    elif resource_type == "font" or ext in [".woff", ".woff2", ".ttf"]:
        captured_assets["fonts"].add(url)
    elif resource_type == "script" or ext == ".js":
        captured_assets["scripts"].add(url)
    elif resource_type == "stylesheet" or ext == ".css":
        captured_assets["stylesheets"].add(url)
    elif resource_type in ["fetch", "xhr"] or "api" in parsed.netloc or "json" in parsed.path:
        captured_assets["api_endpoints"].add(url)

    post_data = None
    try:
        post_data = request.post_data
    except Exception:
        pass

    captured_requests.append({
        "url": url,
        "method": method,
        "resource_type": resource_type,
        "headers": dict(request.headers),
        "post_data": post_data,
        "timestamp": time.time()
    })

def on_response(response):
    url = response.url
    status = response.status
    headers = dict(response.headers)
    content_type = headers.get("content-type", "")

    # Save all XHR/Fetch or JSON or API responses
    if any(k in content_type.lower() for k in ["application/json", "text/plain", "application/javascript", "text/javascript"]) or \
       any(k in url.lower() for k in ["api", "json", "market", "maintenance", "banner", "event", "user", "auth", "token"]):
        try:
            body = response.body()
            body_text = body.decode("utf-8", errors="ignore")
            
            # Try to parse as JSON if possible
            try:
                body_json = json.loads(body_text)
                is_json = True
            except Exception:
                body_json = None
                is_json = False

            # Generate a safe filename
            parsed = urlparse(url)
            safe_name = (parsed.netloc + "_" + parsed.path).replace("/", "_").replace(":", "_").replace("?", "_").replace("&", "_")
            if len(safe_name) > 80:
                safe_name = safe_name[:80]
            filename = f"{response.request.method}_{safe_name}.json" if is_json else f"{response.request.method}_{safe_name}.txt"
            filepath = os.path.join(RESPONSES_DIR, filename)

            with open(filepath, "w", encoding="utf-8") as f:
                if is_json:
                    json.dump(body_json, f, indent=2)
                else:
                    f.write(body_text[:100000])

            captured_responses[url] = {
                "status": status,
                "headers": headers,
                "is_json": is_json,
                "file": filename,
                "data_preview": body_json if is_json else body_text[:500]
            }
        except Exception as e:
            pass

def on_websocket(ws):
    ws_url = ws.url
    print(f"[WS OPEN] {ws_url}")
    
    def on_frame_sent(payload):
        websocket_messages.append({
            "ws_url": ws_url,
            "direction": "sent",
            "payload": payload,
            "timestamp": time.time()
        })
    def on_frame_received(payload):
        websocket_messages.append({
            "ws_url": ws_url,
            "direction": "received",
            "payload": payload,
            "timestamp": time.time()
        })

    ws.on("framesent", on_frame_sent)
    ws.on("framereceived", on_frame_received)

def run():
    print("[1/6] Launching Playwright Chromium...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        page.on("request", on_request)
        page.on("response", on_response)
        page.on("websocket", on_websocket)

        print("[2/6] Navigating to https://www.radheex.com/ ...")
        try:
            page.goto("https://www.radheex.com/", wait_until="networkidle", timeout=30000)
        except Exception as e:
            print("Navigation note:", e)
        time.sleep(3)

        print("[3/6] Interacting with Login & Demo ID...")
        try:
            login_btn = page.locator('button:has-text("Log in"), button:has-text("LOG IN")').first
            if login_btn.is_visible(timeout=5000):
                login_btn.click()
                time.sleep(1.5)
                demo_btn = page.locator('button:has-text("Demo ID")').first
                if demo_btn.is_visible(timeout=5000):
                    demo_btn.click()
                    print("  -> Clicked Demo ID, waiting for session to initialize...")
                    time.sleep(4)
        except Exception as e:
            print("Login error:", e)

        print("[4/6] Navigating Sports Categories (In-Play, Cricket, Soccer, Tennis)...")
        for tab_name in ["In-Play", "Cricket", "Soccer", "Tennis"]:
            try:
                tab = page.locator(f'a:has-text("{tab_name}"), button:has-text("{tab_name}"), li:has-text("{tab_name}")').first
                if tab.is_visible(timeout=3000):
                    print(f"  -> Clicking tab: {tab_name}")
                    tab.click()
                    time.sleep(2)
            except Exception as e:
                pass

        print("[5/6] Navigating to an active Match Details page...")
        try:
            match_links = page.locator('div.event-title, a[href*="/event/"]').all()
            if match_links:
                print(f"  -> Found {len(match_links)} match items, clicking first match...")
                match_links[0].click()
                time.sleep(4)

                # Try clicking an odds button to observe betslip API / reaction
                odds_btns = page.locator('.back, .lay, [class*="back"], [class*="lay"]').all()
                if odds_btns:
                    print(f"  -> Found {len(odds_btns)} odds cells, clicking first odds button...")
                    odds_btns[0].click()
                    time.sleep(2)
        except Exception as e:
            print("Match page note:", e)

        print("[6/6] Checking User Statement & History Modals...")
        try:
            # Look for user menu or links
            for item in ["Account Statement", "Bet History", "Profit Loss", "Live Casino", "Aviator"]:
                try:
                    el = page.locator(f'text="{item}"').first
                    if el.is_visible(timeout=2000):
                        print(f"  -> Interacting with: {item}")
                        el.click()
                        time.sleep(2)
                except Exception:
                    pass
        except Exception as e:
            pass

        print("Final network settling (wait 5s)...")
        time.sleep(5)
        browser.close()

    # Save all summary files
    print("\nSaving summary files...")
    
    # 1. Assets catalog
    assets_clean = {k: sorted(list(v)) for k, v in captured_assets.items()}
    with open(os.path.join(OUTPUT_DIR, "assets_catalog.json"), "w", encoding="utf-8") as f:
        json.dump(assets_clean, f, indent=2)

    # 2. Endpoints and responses
    with open(os.path.join(OUTPUT_DIR, "responses_index.json"), "w", encoding="utf-8") as f:
        json.dump(captured_responses, f, indent=2)

    # 3. All captured requests
    with open(os.path.join(OUTPUT_DIR, "all_requests.json"), "w", encoding="utf-8") as f:
        json.dump(captured_requests, f, indent=2)

    # 4. WebSockets log
    with open(os.path.join(OUTPUT_DIR, "websocket_messages.json"), "w", encoding="utf-8") as f:
        json.dump(websocket_messages, f, indent=2)

    # 5. Generate API Spec Markdown
    markdown_lines = [
        "# RadheEx Reverse-Engineered Network & API Specification",
        "",
        f"**Generated**: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Total Requests Captured**: {len(captured_requests)}",
        f"**Unique API/Data Endpoints**: {len(captured_responses)}",
        f"**WebSocket Messages Logged**: {len(websocket_messages)}",
        "",
        "## 1. Discovered API Endpoints & Data Contracts",
        ""
    ]

    for url, info in sorted(captured_responses.items()):
        parsed = urlparse(url)
        method = "GET"
        for req in captured_requests:
            if req["url"] == url:
                method = req["method"]
                break
        
        markdown_lines.extend([
            f"### `{method} {parsed.path}`",
            f"- **Full URL**: `{url}`",
            f"- **Status**: `{info['status']}`",
            f"- **Content-Type**: `{info['headers'].get('content-type', 'N/A')}`",
            f"- **Saved Payload**: [`{info['file']}`](./responses/{info['file']})",
            "",
            "```json",
            json.dumps(info['data_preview'], indent=2)[:800] if info['is_json'] else str(info['data_preview'])[:500],
            "```",
            ""
        ])

    markdown_lines.extend([
        "## 2. WebSocket Connections & Streaming",
        ""
    ])
    if websocket_messages:
        for msg in websocket_messages[:15]:
            markdown_lines.append(f"- **{msg['direction'].upper()}** (`{msg['ws_url']}`): `{str(msg['payload'])[:200]}`")
    else:
        markdown_lines.append("No active persistent WebSocket frames detected during session. Markets update via high-frequency REST polling (`/delaymarkets/markets/current`).")

    markdown_lines.extend([
        "",
        "## 3. Discovered Assets Summary",
        f"- **Images**: {len(assets_clean['images'])} URLs",
        f"- **SVGs**: {len(assets_clean['svgs'])} URLs",
        f"- **Fonts**: {len(assets_clean['fonts'])} URLs",
        f"- **Scripts**: {len(assets_clean['scripts'])} URLs",
        f"- **Stylesheets**: {len(assets_clean['stylesheets'])} URLs",
        ""
    ])

    with open(os.path.join(OUTPUT_DIR, "API_SPEC.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(markdown_lines))

    print(f"[DONE] Successfully mapped network! Output stored in: {OUTPUT_DIR}")

if __name__ == "__main__":
    run()
