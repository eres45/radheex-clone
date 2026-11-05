import urllib.request
import json

try:
    with urllib.request.urlopen('http://127.0.0.1:5005/api/live/markets') as resp:
        data = json.loads(resp.read().decode('utf-8'))
    print(f"Total events from clone: {len(data.get('events', []))}")
    for ev in data.get('events', []):
        if ev.get('has_tv') or ev.get('tv_url'):
            print(f"ID: {ev.get('event_id')} | {ev.get('event_name')}")
            print(f"  has_tv: {ev.get('has_tv')} | tv_url: {ev.get('tv_url')}")
except Exception as e:
    print('Error:', e)
