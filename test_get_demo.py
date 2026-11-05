import urllib.request
import json

headers = {
    'Content-Type': 'application/json',
    'X-OP-KEY': 'RDE',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Origin': 'https://www.radheex.com',
    'Referer': 'https://www.radheex.com/'
}

print("Testing GET /sso/auth/demo...")
req_demo = urllib.request.Request(
    'https://api.radheex.com/sso/auth/demo',
    headers=headers,
    method='GET'
)

try:
    with urllib.request.urlopen(req_demo, timeout=10) as resp:
        demo_resp = json.loads(resp.read().decode('utf-8'))
    print("Demo GET auth response:", demo_resp)
except Exception as e:
    print("Demo GET error:", e)
