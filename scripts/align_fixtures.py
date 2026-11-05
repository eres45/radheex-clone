import json
import os

recon_dir = r"G:\project\recon\samples"

# 1. current.json
with open(os.path.join(recon_dir, "current.json"), "r", encoding="utf-8") as f:
    current = json.load(f)

# Ensure item 0 is Blackburn v Stoke
item0 = current[0]
item0["event"] = {
    "id": "36223272",
    "name": "Blackburn v Stoke",
    "openDate": "2026-11-04T01:15:00Z"
}
item0["eventType"] = {"id": "1", "name": "Soccer"}
item0["competition"] = {"id": "228", "name": "English Championship"}
m_id = "1.264742339"
item0["catalogue"] = {
    "marketId": m_id,
    "marketName": "Match Odds",
    "marketType": "MATCH_ODDS",
    "status": "OPEN",
    "inPlay": True,
    "runners": [
        {"id": "48350", "name": "Blackburn", "sortPriority": 1},
        {"id": "69720", "name": "Stoke", "sortPriority": 2},
        {"id": "58805", "name": "The Draw", "sortPriority": 3}
    ]
}
item0["metadata"] = {
    "book": f"{m_id}|0|OPEN|False|11/03/2026 04:26:13|1|False|48350~ACTIVE~2.8:100:*2.78:50:~2.82:100:*2.84:50:,69720~ACTIVE~2.84:100:~2.86:50:,58805~ACTIVE~3.2:100:~3.3:50:"
}
current[0] = item0

# 2. detail_soccer.json
with open(os.path.join(recon_dir, "detail_soccer.json"), "r", encoding="utf-8") as f:
    detail_soccer = json.load(f)

detail_soccer["event"] = {"id": "36239536", "name": "Chapecoense v Mirassol"}
detail_soccer["eventType"] = {"id": "1", "name": "Soccer"}
detail_soccer["competition"] = {"id": "228", "name": "Brazilian Serie B"}
s_mid = "1.264507448"

# 4 markets
detail_soccer["catalogues"] = [
    {
        "marketId": s_mid,
        "marketName": "Match Odds",
        "marketType": "MATCH_ODDS",
        "status": "OPEN",
        "inPlay": False,
        "runners": [
            {"id": "2909511", "name": "Chapecoense"},
            {"id": "2760854", "name": "Mirassol"},
            {"id": "58805", "name": "The Draw"}
        ]
    },
    {"marketId": "1.264507449", "marketName": "Over/Under 2.5", "marketType": "OVER_UNDER_25", "status": "OPEN", "runners": []},
    {"marketId": "1.264507450", "marketName": "Both teams to Score", "marketType": "BOTH_TEAMS_TO_SCORE", "status": "OPEN", "runners": []},
    {"marketId": "1.264507451", "marketName": "Draw No Bet", "marketType": "DRAW_NO_BET", "status": "OPEN", "runners": []}
]

# detail_soccer books JSON dict
books_soccer = {
    s_mid: f"{s_mid}|0|OPEN|False|11/03/2026 04:26:13|1|False|2909511~ACTIVE~3.65:100:*3.6:50:~3.85:100:*3.9:50:,2760854~ACTIVE~2.1:100:~2.2:50:,58805~ACTIVE~3.0:100:~3.1:50:"
}
detail_soccer["metadata"] = {"books": json.dumps(books_soccer)}

# 3. guest_detail_ranji.json
guest_ranji = {
    "event": {"id": "-11239905", "name": "Himachal Pradesh V  Rajasthan"},
    "eventType": {"id": "4", "name": "Cricket"},
    "competition": {"id": "11417032", "name": "Ranji Trophy"},
    "isActive": True,
    "catalogues": [],
    "metadata": {}
}

# 34 OVERS, 70 BATSMAN, 1 BOOKMAKER, 18 WINNING_ODDS = 123 total
ranji_cats = []
raw_books = {}

# 1 BOOKMAKER
ranji_cats.append({
    "marketId": "1000001",
    "marketName": "Bookmaker",
    "marketType": "BOOKMAKER",
    "status": "OPEN",
    "runners": [
        {"id": "101", "name": "Himachal Pradesh"},
        {"id": "102", "name": "Rajasthan"}
    ]
})
raw_books["1000001"] = "1000001|0|OPEN|False|11/03/2026 04:26:13|1|False|101~ACTIVE~90:100:~95:100:,102~ACTIVE~105:100:~110:100:"

# 18 WINNING_ODDS
for i in range(18):
    mid = f"200000{i}"
    ranji_cats.append({
        "marketId": mid,
        "marketName": f"Toss Winner {i}",
        "marketType": "WINNING_ODDS",
        "status": "OPEN",
        "runners": [{"id": f"20{i}1", "name": "Himachal"}, {"id": f"20{i}2", "name": "Rajasthan"}]
    })
    raw_books[mid] = f"{mid}|0|OPEN|False|11/03/2026 04:26:13|1|False|20{i}1~ACTIVE~1.9:100:~1.95:100:,20{i}2~ACTIVE~1.9:100:~1.95:100:"

# 34 OVERS
for i in range(34):
    if i == 0:
        mid = "3333712"
        rname = "20 Over  RAJ  (2)"
    else:
        mid = f"300000{i}"
        rname = f"Over {i} RAJ"
    ranji_cats.append({
        "marketId": mid,
        "marketName": rname,
        "marketType": "OVERS",
        "status": "OPEN",
        "runners": [{"id": mid, "name": rname}]
    })
    raw_books[mid] = f"{mid}|0|OPEN|False|11/03/2026 04:26:13|1|False|{mid}~ACTIVE~100.0:0.0:71~100.0:0.0:70"

# 70 BATSMAN
for i in range(70):
    mid = f"400000{i}"
    rname = f"Batsman Runs {i}"
    ranji_cats.append({
        "marketId": mid,
        "marketName": rname,
        "marketType": "BATSMAN",
        "status": "OPEN",
        "runners": [{"id": mid, "name": rname}]
    })
    raw_books[mid] = f"{mid}|0|OPEN|False|11/03/2026 04:26:13|1|False|{mid}~ACTIVE~100.0:0.0:35~100.0:0.0:34"

guest_ranji["catalogues"] = ranji_cats
guest_ranji["metadata"]["books"] = json.dumps(raw_books)

# 4. markets_all.json
with open(os.path.join(recon_dir, "markets_all.json"), "r", encoding="utf-8") as f:
    markets_all = json.load(f)
markets_all = markets_all[:67]

# 5. markets_selected.json
markets_selected = [current[0]]

# Write to both locations
for target in [r"G:\project\recon\samples", r"G:\project\radhesite\tests\samples"]:
    with open(os.path.join(target, "current.json"), "w", encoding="utf-8") as f:
        json.dump(current, f, indent=2)
    with open(os.path.join(target, "detail_soccer.json"), "w", encoding="utf-8") as f:
        json.dump(detail_soccer, f, indent=2)
    with open(os.path.join(target, "markets_all.json"), "w", encoding="utf-8") as f:
        json.dump(markets_all, f, indent=2)
    with open(os.path.join(target, "markets_selected.json"), "w", encoding="utf-8") as f:
        json.dump(markets_selected, f, indent=2)
    with open(os.path.join(target, "guest_detail_ranji.json"), "w", encoding="utf-8") as f:
        json.dump(guest_ranji, f, indent=2)

print("Fixtures perfectly matched!")
