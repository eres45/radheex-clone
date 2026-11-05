import json

with open('live_api_calls.json', 'r', encoding='utf-8') as f:
    calls = json.load(f)

print(f"Total API calls captured: {len(calls)}")
seen = set()
for c in calls:
    u = c['url'].split('?')[0]
    if u not in seen:
        seen.add(u)
        print(f"{c['method']} {u}")
