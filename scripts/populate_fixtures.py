import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import live_feed

# Paths to populate
recon_dir = r"G:\project\recon\samples"
tests_dir = r"G:\project\radhesite\tests\samples"
os.makedirs(recon_dir, exist_ok=True)
os.makedirs(tests_dir, exist_ok=True)

print("[1] Fetching current.json...")
current = live_feed.fetch_json("markets/current", force=True)

print("[2] Fetching detail_soccer.json...")
detail_soccer = live_feed.fetch_json("events/detail/36239536", force=True)

print("[3] Fetching guest_detail_ranji.json...")
guest_detail_ranji = live_feed.fetch_json("events/detail/-11239905", force=True)

print("[4] Fetching markets_all.json...")
markets_all = live_feed.fetch_json("markets", force=True)

print("[5] Fetching markets_selected.json...")
try:
    markets_selected = live_feed.fetch_json("markets/selected?marketids=1.264742339", force=True)
except Exception:
    markets_selected = [current[0]] if current else []

samples = {
    "current.json": current,
    "detail_soccer.json": detail_soccer,
    "guest_detail_ranji.json": guest_detail_ranji,
    "markets_all.json": markets_all,
    "markets_selected.json": markets_selected
}

for name, data in samples.items():
    for target_dir in [recon_dir, tests_dir]:
        p = os.path.join(target_dir, name)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"Saved {name} -> {p}")

print("\nAll fixtures populated successfully!")
