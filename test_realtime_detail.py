import urllib.request
import json

headers = {
    'Content-Type': 'application/json',
    'X-OP-KEY': 'RDE',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Origin': 'https://www.radheex.com',
    'Referer': 'https://www.radheex.com/'
}

# Fetch token
req_demo = urllib.request.Request('https://api.radheex.com/sso/auth/demo', headers=headers, method='GET')
with urllib.request.urlopen(req_demo, timeout=10) as resp:
    token = json.loads(resp.read().decode('utf-8'))['token']

headers['Authorization'] = f"Bearer {token}"

# Fetch detail for Wellington v Northern Districts (ID: 36264203)
print("Testing /marketprovider/events/detail/36264203 with Bearer token...")
req_det = urllib.request.Request('https://api.radheex.com/marketprovider/events/detail/36264203', headers=headers)
try:
    with urllib.request.urlopen(req_det, timeout=10) as resp:
        det = json.loads(resp.read().decode('utf-8'))
    print("SUCCESS!")
    print("Event Name:", det.get('event', {}).get('name'))
    print("Catalogues (markets count):", len(det.get('catalogues', [])))
    print("Metadata hasTv:", det.get('metadata', {}).get('hasTv'))
    print("Metadata tvUrl:", det.get('metadata', {}).get('tvUrl'))
    print("Books length:", len(det.get('metadata', {}).get('books', '')))
except Exception as e:
    print("Detail error:", e)
