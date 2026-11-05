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

# 1. Fetch Demo Token
print("1. Fetching Demo Token...")
req_demo = urllib.request.Request('https://api.radheex.com/sso/auth/demo', headers=headers, method='GET')
with urllib.request.urlopen(req_demo, timeout=10) as resp:
    demo_auth = json.loads(resp.read().decode('utf-8'))
token = demo_auth['token']
print(f"Token acquired: {token[:25]}... (Expires: {demo_auth['expiration']})")

headers['Authorization'] = f"Bearer {token}"

# 2. Fetch from marketprovider (Real-Time)
print("\n2. Fetching from /marketprovider/markets/current (REAL TIME)...")
t0 = time.time()
req_rt = urllib.request.Request('https://api.radheex.com/marketprovider/markets/current', headers=headers)
with urllib.request.urlopen(req_rt, timeout=10) as resp:
    rt_markets = json.loads(resp.read().decode('utf-8'))
t_rt = time.time() - t0
print(f"Real-time markets returned: {len(rt_markets)} items in {t_rt:.2f}s")

# 3. Fetch from delaymarkets (Delayed)
print("\n3. Fetching from /delaymarkets/markets/current (DELAYED)...")
t0 = time.time()
req_delay = urllib.request.Request('https://api.radheex.com/delaymarkets/markets/current', headers={'Content-Type': 'application/json', 'X-OP-KEY': 'RDE'})
with urllib.request.urlopen(req_delay, timeout=10) as resp:
    delay_markets = json.loads(resp.read().decode('utf-8'))
t_delay = time.time() - t0
print(f"Delayed markets returned: {len(delay_markets)} items in {t_delay:.2f}s")

# 4. Compare timestamps and seconds difference on matching events
print("\n4. Analyzing time difference between Real-Time and Delayed feeds...")
rt_by_id = {x.get('event', {}).get('id'): x for x in rt_markets if x.get('event', {}).get('id')}
delay_by_id = {x.get('event', {}).get('id'): x for x in delay_markets if x.get('event', {}).get('id')}

common_ids = set(rt_by_id.keys()) & set(delay_by_id.keys())
print(f"Matching events in both feeds: {len(common_ids)}")

for eid in list(common_ids)[:5]:
    ev_rt = rt_by_id[eid]
    ev_del = delay_by_id[eid]
    name = ev_rt.get('event', {}).get('name')
    
    # Check timestamps in metadata
    md_rt = ev_rt.get('metadata', {})
    md_del = ev_del.get('metadata', {})
    
    # Book string timestamp
    # Format: marketId|..|status|..|timestamp|..|..|runnerId~...
    book_rt = md_rt.get('book', '')
    book_del = md_del.get('book', '')
    
    ts_rt = book_rt.split('|')[4] if len(book_rt.split('|')) > 4 else 'N/A'
    ts_del = book_del.split('|')[4] if len(book_del.split('|')) > 4 else 'N/A'
    
    print(f"\nEvent: {name} (ID: {eid})")
    print(f"  Real-time book timestamp: {ts_rt}")
    print(f"  Delayed book timestamp:   {ts_del}")
    
    try:
        t_diff = int(ts_rt) - int(ts_del)
        print(f"  --> EXACT DIFFERENCE: {t_diff / 1000.0:.1f} seconds! ({t_diff} ms)")
    except Exception:
        pass
