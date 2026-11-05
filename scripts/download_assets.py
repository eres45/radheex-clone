import os
import urllib.request
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

target_dir = r"g:\project\radhesite\static\images"
os.makedirs(target_dir, exist_ok=True)

assets = [
    ("brand_logo.svg", "https://images.staticcontents.net/rde/uimg/brand_logo.svg"),
    ("coin.svg", "https://images.staticcontents.net/rde/uimg/coin.svg"),
    ("aviator-icon.svg", "https://images.staticcontents.net/casino/banner/images/aviator-icon.svg"),
    ("evolution.png", "https://images.staticcontents.net/casino/banner/loginimages/evolution.png"),
    ("ezugi.png", "https://images.staticcontents.net/casino/banner/loginimages/ezugi.png"),
    ("pragmatic-live.png", "https://images.staticcontents.net/casino/banner/loginimages/pragmatic-live.png"),
    ("spribe.png", "https://images.staticcontents.net/casino/banner/loginimages/spribe.png"),
    ("betgames.png", "https://images.staticcontents.net/casino/banner/loginimages/betgames.png"),
    ("betsoft.png", "https://images.staticcontents.net/casino/banner/loginimages/betsoft.png"),
    ("evoplay.png", "https://images.staticcontents.net/casino/banner/loginimages/Evoplay.png"),
    ("logo-18plus.svg", "https://images.staticcontents.net/casino/banner/loginimages/logo-18plus.svg"),
    ("main-banner1.webp", "https://images.staticcontents.net/rde/login/main-banner1.webp"),
    ("main-banner2.webp", "https://images.staticcontents.net/rde/login/main-banner2.webp"),
    ("main-banner3.webp", "https://images.staticcontents.net/rde/login/main-banner3.webp"),
    ("main-banner4.webp", "https://images.staticcontents.net/rde/login/main-banner4.webp"),
    ("main-banner5.webp", "https://images.staticcontents.net/rde/login/main-banner5.webp"),
]

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Referer": "https://www.radheex.com/"
}

print("=== Downloading Assets to static/images ===")
for filename, url in assets:
    dest = os.path.join(target_dir, filename)
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, context=ctx) as resp:
            data = resp.read()
            with open(dest, "wb") as f:
                f.write(data)
            print(f" [OK] {filename} ({len(data)} bytes)")
    except Exception as e:
        print(f" [FAIL] {filename} from {url} -> {e}")
