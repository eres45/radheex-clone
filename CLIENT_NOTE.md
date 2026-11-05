# Radhe Exchange — Prototype Demo (for the client)

A working prototype of the rebuilt exchange. Demo only — points/credits only, no real money anywhere.

## Run it
```bash
pip install -r requirements.txt
python app.py
```
Then open http://127.0.0.1:5000/

## Try it with these demo logins (generic demos — change before any real use)
- Player: demo / demo123 (100 points)
- Main admin: admin / admin123
- Sub-admin: subadmin / subadmin123

## What is live
- Real odds and markets for Cricket, Soccer, Tennis, including Fancy (OVERS + BATSMAN), from the live delayed feed — refreshes every few seconds.
- Betting works: back/lay + fancy, bet slip, wallet, exposure, unsettled bets, statement, P&L.

## What the admin side does
- Main admin: creates sub-admins, sees every player ID and everything (all downlines, all credit, all activity).
- Sub-admin: creates player IDs, assigns and manages credit, suspends, resets passwords — only for their own players.
- Player activity: admins see where each player is betting, what they are playing (bets + casino), credit changes, and settlements.
- Settlement: the admin settles markets (no results feed needed) — this is how live bets settle here.

## What is simulated or placeholder (honest labels inside the app)
- Casino provider games (live-dealer tables) are "coming soon" placeholders — 38 in-house games are playable instead (full lobby).
- Live TV plays on event pages where the feed carries it. No live scorecard widget: the real scorecard needs operator access (see README).
- The odds feed is delayed, not real-time push.
- Demo accounts and demo points only. No cashier — credit is assigned by admins, exactly like the original site.

## What is NOT in this package
- No real user data, no real credentials, nothing from the original site's accounts.
