import urllib.request
import json

req = urllib.request.Request(
    'https://api.radheex.com/delaymarkets/markets/current',
    headers={'Content-Type': 'application/json', 'X-OP-KEY': 'RDE', 'User-Agent': 'Mozilla/5.0'}
)
try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode('utf-8'))
    print(f"Total items returned: {len(data)}")
    tv_items = [x for x in data if x.get('metadata', {}).get('tvUrl') or x.get('metadata', {}).get('hasTv')]
    print(f"Items with tvUrl or hasTv: {len(tv_items)}")
    for item in tv_items[:10]:
        ev = item.get('event', {})
        md = item.get('metadata', {})
        print(f"Event: {ev.get('name')} (ID: {ev.get('id')})")
        print(f"  hasTv: {md.get('hasTv')}")
        print(f"  tvUrl: {md.get('tvUrl')}")
        print(f"  scoreUrl: {md.get('scoreUrl')}")
except Exception as e:
    print('Error:', e)
