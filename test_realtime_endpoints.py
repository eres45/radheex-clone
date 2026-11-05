import urllib.request
import json
import time

# 1. Test delaymarkets
req_delay = urllib.request.Request(
    'https://api.radheex.com/delaymarkets/markets/current',
    headers={'Content-Type': 'application/json', 'X-OP-KEY': 'RDE', 'User-Agent': 'Mozilla/5.0'}
)

t0 = time.time()
try:
    with urllib.request.urlopen(req_delay, timeout=10) as resp:
        d_delay = json.loads(resp.read().decode('utf-8'))
    t_delay = time.time() - t0
    print(f"delaymarkets: {len(d_delay)} events fetched in {t_delay:.2f}s")
except Exception as e:
    print("delaymarkets error:", e)

# 2. Test marketprovider without token
req_mp = urllib.request.Request(
    'https://api.radheex.com/marketprovider/markets/current',
    headers={'Content-Type': 'application/json', 'X-OP-KEY': 'RDE', 'User-Agent': 'Mozilla/5.0'}
)

try:
    with urllib.request.urlopen(req_mp, timeout=10) as resp:
        d_mp = json.loads(resp.read().decode('utf-8'))
    print(f"marketprovider (no auth): status 200, {len(d_mp)} events")
except urllib.error.HTTPError as e:
    print(f"marketprovider (no auth): HTTP {e.code} - {e.read().decode('utf-8', errors='ignore')[:200]}")
except Exception as e:
    print("marketprovider error:", e)
