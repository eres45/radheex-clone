import urllib.request
import json
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJtYXRhamkwNjAiLCJyb2xlIjoiQ2xpZW50IiwiaXNzIjoiUkRFIiwiZXhwIjoxNzkzNzY1NzAxMjkzLCJwd2RjaCI6ZmFsc2UsImlwIjoiNDkuMzYuNDMuMTc4In0.tYISzKComJOM6Ku5GzfAYk1gw4zreiWMU1UYqLL6xnk"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Content-Type": "application/json",
    "x-op-key": "RDE",
    "Authorization": f"Bearer {TOKEN}"
}

endpoints = [
    ("GET", "https://api.radheex.com/manage/profile", None),
    ("GET", "https://api.radheex.com/account/transaction/account", None),
    ("GET", "https://api.radheex.com/manage/profile/buttons", None),
    ("POST", "https://report.radheex.com/pnl/user", {"from":"2026-11-02T18:30:00.000Z","to":"2026-11-04T18:30:00.000Z"}),
    ("POST", "https://report.radheex.com/bets/user/history", {"filters":{"betStatus":["WON","LOST","VOID","DECLARED"],"eventTypeCategory":"SPORTS","marketId":""},"firstId":"","lastId":"","action":"","from":"2026-11-02T18:30:00.000Z","to":"2026-11-04T18:30:00.000Z","pageNo":1,"recordsPerPage":25,"countRecords":0}),
    ("POST", "https://report.radheex.com/transaction2/user", {"filters":{"types":"ALL"},"lastId":"","firstId":"","closingBalance":0,"openingBalance":0,"hstId":"","hstBalance":0,"action":"","from":"2026-11-02T18:30:00.000Z","to":"2026-11-04T18:30:00.000Z","countRecords":0,"pageNo":1,"recordsPerPage":25})
]

print("=== Testing Authenticated Endpoints for mataji060 ===")
for method, url, body in endpoints:
    try:
        data = json.dumps(body).encode("utf-8") if body else None
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        with urllib.request.urlopen(req, context=ctx) as resp:
            resp_data = resp.read().decode("utf-8")
            print(f"[{resp.status}] {method} {url}")
            try:
                parsed = json.loads(resp_data)
                print("  Response preview:", json.dumps(parsed)[:250])
            except Exception:
                print("  Text preview:", resp_data[:200])
    except Exception as e:
        print(f"[ERROR] {method} {url} -> {e}")
