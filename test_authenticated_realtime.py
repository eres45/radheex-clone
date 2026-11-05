import urllib.request
import json
import time

headers = {
    'Content-Type': 'application/json',
    'X-OP-KEY': 'RDE',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Origin': 'https://www.radheex.com',
    'Referer': 'https://www.radheex.com/'
}

# 1. Call demo auth endpoint
print("1. Calling /sso/auth/demo...")
req_demo = urllib.request.Request(
    'https://api.radheex.com/sso/auth/demo',
    data=json.dumps({}).encode('utf-8'),
    headers=headers,
    method='POST'
)

token = None
try:
    with urllib.request.urlopen(req_demo, timeout=10) as resp:
        demo_resp = json.loads(resp.read().decode('utf-8'))
    print("Demo auth response:", demo_resp)
    token = demo_resp.get('token') or demo_resp.get('data', {}).get('token')
except Exception as e:
    print("Demo auth error:", e)

# If demo gave credentials, let's see what it returned
if token:
    print(f"Got Bearer Token: {token[:30]}...")
    headers['Authorization'] = f"Bearer {token}"

    # 2. Test marketprovider with token
    print("2. Calling /marketprovider/markets/current with Bearer token...")
    req_mp = urllib.request.Request(
        'https://api.radheex.com/marketprovider/markets/current',
        headers=headers
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req_mp, timeout=10) as resp:
            mp_data = json.loads(resp.read().decode('utf-8'))
        t_mp = time.time() - t0
        print(f"SUCCESS! Fetched {len(mp_data)} REAL-TIME markets in {t_mp:.2f}s!")
        if mp_data:
            first = mp_data[0]
            print(f"Sample Event: {first.get('event', {}).get('name')}")
            print(f"Timestamp: {first.get('metadata', {}).get('timestamp')}")
    except Exception as e:
        print("Marketprovider error with token:", e)
