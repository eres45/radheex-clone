"""Tests for the admin activity view: full per-player activity (all bets
with live/simulated origin, casino history, credit activity,
settlements), scoping (main sees any player, sub-admin only its own
downline), and the seeder race fix. Casino history is recorded only
from completed rounds onward -- never backfilled."""
import json
import sqlite3
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from flask import g

import live_feed
from app import create_app, ensure_subadmin, get_db, SCHEMA
from csrf_helpers import wrap


@pytest.fixture
def clients3(tmp_path):
    """Independent sessions on one fresh DB: main admin, sub-admin
    (seeded demo), a player client, and a fourth client for a second
    sub-admin. Plain clients, NOT nested `with` blocks."""
    live_feed.clear_cache()
    app = create_app({"DATABASE": str(tmp_path / "test.db"), "TESTING": True})
    yield wrap(app.test_client()), wrap(app.test_client()), wrap(app.test_client()), wrap(app.test_client())


def login(client, username, password):
    r = client.post("/api/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.get_json()
    return r.get_json()


def login_admin(client):
    return login(client, "admin", "admin123")


def login_subadmin(client):
    return login(client, "subadmin", "subadmin123")


def match_market(client, match_id, kind):
    m = client.get(f"/api/matches/{match_id}").get_json()
    mk = next(x for x in m["markets"] if x["kind"] == kind)
    return m, mk


def create_player(client, username, password, credit):
    r = client.post("/api/admin/players", json={
        "username": username, "password": password, "credit": credit})
    assert r.status_code == 200, r.get_json()
    return r.get_json()


def fund_subadmin(admin, sub, amount=1000000):
    """Transfer-model setup: main admin allots to the sub-admin so it
    can fund its own players (creation opening credit + add-credit
    both debit the sub-admin's balance)."""
    me = sub.get("/api/me").get_json()["user"]
    r = admin.post(f"/api/admin/subadmins/{me['id']}/add-credit", json={"amount": amount})
    assert r.status_code == 200, r.get_json()
    return r.get_json()


def detail(client, pid):
    r = client.get(f"/api/admin/players/{pid}")
    assert r.status_code == 200, r.get_json()
    return r.get_json()


def test_seed_race_no_crash_on_username_clash(tmp_path):
    """Regression: the seeder runs on every request, so a pre-existing
    'subadmin' username (or two racing first requests) must not raise
    a UNIQUE violation and 500 the page."""
    app = create_app({"DATABASE": str(tmp_path / "test.db"), "TESTING": True})
    with app.app_context():
        g.app_config = app.config
        db = get_db()
        db.executescript(SCHEMA)
        db.execute(
            "INSERT INTO users (username, password_hash, balance, exposure, role, status,"
            " credit_limit, created_at) VALUES ('subadmin', 'x', 0, 0, 'player', 'active', 0, '2026-01-01')")
        db.commit()
        ensure_subadmin(db)  # must not raise despite the username clash
        ensure_subadmin(db)  # and must be idempotent
        row = db.execute("SELECT COUNT(*) FROM users WHERE role = 'subadmin'").fetchone()[0]
        assert row == 0


def test_activity_bets_credit_settlements(clients3):
    player, sub, admin, _ = clients3
    login_admin(admin)
    login_subadmin(sub)
    fund_subadmin(admin, sub)
    p = create_player(sub, "actp", "secret12", 3000)
    pid = p["id"]
    sub.post(f"/api/admin/players/{pid}/add-credit", json={"amount": 500})
    login(player, "actp", "secret12")
    _, mk = match_market(player, 1, "bookmaker")
    team_a = mk["selections"][0]
    bet = player.post("/api/bets", json={
        "match_id": 1, "market_id": mk["id"], "selection_id": team_a["id"],
        "side": "back", "stake": 25}).get_json()
    # Unsettled bet visible with full fields + simulated origin.
    det = detail(sub, pid)
    assert len(det["bets"]) == 1
    b = det["bets"][0]
    assert b["origin"] == "simulated" and b["status"] == "unsettled"
    assert b["side"] == "back" and b["stake"] == 25 and b["odds"] == bet["odds"]
    assert b["match_title"] and b["selection"] == team_a["name"] and b["placed_at"]
    # Credit activity: creation + top-up, with the acting manager named.
    acts = {(a["action"], a["admin"]) for a in det["credit_activity"]}
    assert ("CREATE_PLAYER", "subadmin") in acts
    assert ("ADD_CREDIT", "subadmin") in acts
    add_row = next(a for a in det["credit_activity"] if a["action"] == "ADD_CREDIT")
    assert add_row["amount"] == 500
    # Main settles; the settled bet, settlement row and P&L all show up.
    r = admin.post(f"/api/admin/markets/{mk['id']}/settle",
                   json={"winner": team_a["name"]})
    assert r.status_code == 200
    det = detail(admin, pid)
    assert det["bets"][0]["status"] == "settled"
    assert det["bets"][0]["profit"] == round(25 * (bet["odds"] - 1), 2)
    assert len(det["settlements"]) == 1
    s = det["settlements"][0]
    assert s["result"] == team_a["name"] and s["net"] == det["bets"][0]["profit"]
    assert any(t["kind"] == "BET_WON" for t in det["statement"])
    assert det["pnl"]["total_profit"] == det["bets"][0]["profit"]


def test_activity_live_origin(tmp_path):
    """A bet on a shadow match (live_event_id set) reports origin live."""
    live_feed.clear_cache()
    app = create_app({"DATABASE": str(tmp_path / "test.db"), "TESTING": True})
    admin_c, player_c = wrap(app.test_client()), wrap(app.test_client())
    login_admin(admin_c)
    p = create_player(admin_c, "livep", "secret12", 5000)
    pid = p["id"]
    with app.app_context():
        g.app_config = app.config
        db = get_db()
        db.executescript(SCHEMA)
        cur = db.execute(
            "INSERT INTO matches (sport, title, team_a, team_b, status, start_at, live_event_id)"
            " VALUES ('Cricket', 'Shadow XI v Test XI', 'Shadow XI', 'Test XI', 'live',"
            " '2026-11-03T00:00:00+00:00', '-99999')")
        match_id = cur.lastrowid
        cur = db.execute(
            "INSERT INTO markets (match_id, kind, name, max_stake, market_limit)"
            " VALUES (?, 'bookmaker', 'Match Odds', 100000, 1000000)", (match_id,))
        market_id = cur.lastrowid
        cur = db.execute(
            "INSERT INTO selections (market_id, name, base_back, base_lay, live_runner_id)"
            " VALUES (?, 'Shadow XI', 2.0, 2.02, '1')", (market_id,))
        sel_id = cur.lastrowid
        db.commit()
    login(player_c, "livep", "secret12")
    r = player_c.post("/api/bets", json={
        "match_id": match_id, "market_id": market_id, "selection_id": sel_id,
        "side": "back", "stake": 10, "odds": 2.0})
    assert r.status_code == 200, r.get_json()
    det = detail(admin_c, pid)
    assert len(det["bets"]) == 1
    assert det["bets"][0]["origin"] == "live"
    assert det["bets"][0]["odds"] == 2.0


def seed_history(tmp_path, pid, rows):
    """Insert game_history rows directly: the activity view must render
    past history (including rows from games since removed) with exactly
    the public columns and no hidden game state."""
    db = sqlite3.connect(str(tmp_path / "test.db"))
    for game, stake, payout, profit, outcome in rows:
        db.execute(
            "INSERT INTO game_history (user_id, game, stake, payout, profit, outcome, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, '2026-01-02T10:00:00+00:00')",
            (pid, game, stake, payout, profit, outcome))
    db.commit()
    db.close()


def test_activity_casino_history_and_no_leak(clients3, tmp_path):
    player, sub, admin, _ = clients3
    login_admin(admin)
    login_subadmin(sub)
    fund_subadmin(admin, sub)
    p = create_player(sub, "casinop", "secret12", 5000)
    pid = p["id"]
    # Legacy history rows (from games since removed) must still render.
    seed_history(tmp_path, pid, [
        ("crash", 10, 20.0, 10.0, "crashed at 3.45x, target 2.0x, won"),
        ("dice", 10, 0.0, -10.0, "roll 42.5, target 50 over, lost"),
        ("mines", 10, 0.0, -10.0, "hit a mine"),
    ])
    det = detail(sub, pid)
    games = {g["game"]: g for g in det["casino"]}
    assert "crash" in games and "dice" in games and "mines" in games
    assert games["crash"]["stake"] == 10
    assert games["crash"]["payout"] == 20.0
    assert games["crash"]["profit"] == 10.0
    assert "crashed at" in games["crash"]["outcome"]
    assert games["dice"]["payout"] == 0.0
    assert "roll" in games["dice"]["outcome"]
    bust_row = next(g for g in det["casino"]
                    if g["game"] == "mines" and g["payout"] == 0)
    assert bust_row["profit"] == -10.0 and bust_row["outcome"] == "hit a mine"
    # Rows carry only the public columns; no hidden game state leaks.
    for g in det["casino"]:
        assert set(g.keys()) == {"id", "game", "stake", "payout", "profit",
                                 "outcome", "created_at"}
        assert "revealed" not in g["outcome"] and "[" not in g["outcome"]
    # No backfill: a player with no game_history rows shows an empty list.
    p2 = create_player(sub, "oldp", "secret12", 100)
    det2 = detail(sub, p2["id"])
    assert det2["casino"] == []


def test_activity_scoping_other_subadmin(clients3, tmp_path):
    player, sub, admin, other = clients3
    login_admin(admin)
    login_subadmin(sub)
    agent = admin.post("/api/admin/subadmins",
                       json={"username": "otheragent", "password": "otherpass"}).get_json()
    login(other, "otheragent", "otherpass")
    fund_subadmin(admin, sub)
    p = create_player(sub, "scopep", "secret12", 1000)
    pid = p["id"]
    login(player, "scopep", "secret12")
    seed_history(tmp_path, pid, [("crash", 10, 20.0, 10.0, "crashed at 3.45x, target 2.0x, won")])
    # Owning sub-admin and main admin see the full activity...
    assert detail(sub, pid)["casino"]
    assert detail(admin, pid)["casino"]
    # ...another sub-admin sees nothing at all (404, not a redacted
    # view -- and not a 403, which would confirm the id exists).
    assert other.get(f"/api/admin/players/{pid}").status_code == 404
