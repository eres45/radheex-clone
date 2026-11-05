import live_feed
import json
import urllib.request

# Get demo token
req = urllib.request.Request(
    'https://api.radheex.com/sso/auth/demo',
    headers={'Content-Type': 'application/json', 'X-OP-KEY': 'RDE', 'User-Agent': 'Mozilla/5.0', 'Origin': 'https://www.radheex.com'}
)
resp = urllib.request.urlopen(req)
token = json.loads(resp.read().decode('utf-8'))['token']

# Fetch real-time markets/current
req_rt = urllib.request.Request(
    'https://api.radheex.com/marketprovider/markets/current',
    headers={'Content-Type': 'application/json', 'X-OP-KEY': 'RDE', 'Authorization': f'Bearer {token}', 'User-Agent': 'Mozilla/5.0', 'Origin': 'https://www.radheex.com'}
)
data_rt = json.loads(urllib.request.urlopen(req_rt).read().decode('utf-8'))

print(f"Fetched {len(data_rt)} real-time market items.")
# Test parsing with live_feed parser
parsed = live_feed._parse_list_payload(data_rt)
print(f"Successfully parsed {len(parsed)} events with 0-second real-time odds!")

for ev in parsed[:3]:
    print(f"Event: {ev['event_name']} ({ev['sport']}) | in_play: {ev['in_play']} | has_tv: {ev['has_tv']}")
    runners = ev.get('market', {}).get('runners', [])
    for r in runners[:2]:
        print(f"   Runner: {r['name']} -> Back: {r['best_back']} / Lay: {r['best_lay']}")
