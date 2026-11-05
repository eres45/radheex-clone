"""Tests for batch-2 casino games: TeleFly, Lucky Cups, PvP Wheel,
Lottery 6/49.

Shared-round games (TeleFly / PvP / Lottery) derive phase from wall
clock and settle lazily on state requests, so tests force phase
transitions by moving the round's timestamps in the test DB, then
assert exact wallet math and history rows. Crash points and wheel
winners are server-side secrets: tests never assume a value, they
read the settled public result (or the DB row for crash timing) and
recompute the expected payout from it.
"""
import json
import sqlite3
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from app import create_app
from csrf_helpers import wrap


@pytest.fixture
def env(tmp_path):
    app = create_app({"DATABASE": str(tmp_path / "test.db"), "TESTING": True})
    db_path = str(tmp_path / "test.db")
    yield wrap(app.test_client()), wrap(app.test_client()), wrap(app.test_client()), db_path


def login(client, username, password):
    r = client.post("/api/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.get_json()
    return r.get_json()


def balance(client):
    return client.get("/api/me").get_json()["user"]["balance"]


def sql(db_path, stmt, params=()):
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    cur = con.execute(stmt, params)
    con.commit()
    rows = cur.fetchall()
    con.close()
    return rows


def casino_rows(client, pid):
    client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    det = client.get(f"/api/admin/players/{pid}").get_json()
    assert "casino" in det, det
    client.post("/api/auth/logout")
    return det["casino"]


def make_player(admin_c, player_c, db_path, username, credit):
    login(admin_c, "admin", "admin123")
    r = admin_c.post("/api/admin/players", json={
        "username": username, "password": "secret12", "credit": credit})
    assert r.status_code == 200, r.get_json()
    pid = r.get_json()["id"]
    login(player_c, username, "secret12")
    admin_c.post("/api/auth/logout")
    return pid


def demo_pid(client):
    return client.get("/api/me").get_json()["user"]["id"]


# ---------------- Lucky Cups ----------------

def test_cups_win_lose_and_guards(env):
    c, _, _, _ = env
    r = c.post("/api/casino/cups", json={"stake": 10, "cup": 1})
    assert r.status_code == 401
    login(c, "demo", "demo123")
    assert c.post("/api/casino/cups", json={"stake": 10, "cup": 3}).status_code == 400
    assert c.post("/api/casino/cups", json={"stake": 1000, "cup": 1}).status_code == 400
    won = lost = None
    for _ in range(40):
        d = c.post("/api/casino/cups", json={"stake": 10, "cup": 0}).get_json()
        assert d["winning_cup"] in (0, 1, 2)
        if d["win"] and won is None:
            won = d
            assert d["payout"] == round(10 * 2.91, 2) == 29.10
        if not d["win"] and lost is None:
            lost = d
            assert d["payout"] == 0.0
        if won and lost:
            break
    assert won is not None and lost is not None, "no win and loss in 40 cups rounds"
    before = balance(c)
    d = c.post("/api/casino/cups", json={"stake": 7, "cup": 2}).get_json()
    assert balance(c) == round(before - 7 + d["payout"], 2)
    assert d["payout"] == (round(7 * 2.91, 2) if d["win"] else 0.0)


def test_cups_admin_blocked(env):
    c, _, _, _ = env
    login(c, "admin", "admin123")
    assert c.post("/api/casino/cups", json={"stake": 10, "cup": 1}).status_code == 403


# ---------------- TeleFly ----------------

def test_telefly_bet_cashout_and_crash(env):
    c, _, _, db_path = env
    login(c, "demo", "demo123")
    pid = demo_pid(c)
    st = c.get("/api/casino/telefly/state").get_json()
    assert st["phase"] == "betting" and st["crash_point"] is None
    assert st["my_bet"] is None
    r = c.post("/api/casino/telefly/bet", json={"stake": 10})
    assert r.status_code == 200, r.get_json()
    assert balance(c) == 90.0
    assert c.post("/api/casino/telefly/bet", json={"stake": 5}).status_code == 400
    # Force FLYING 5s in: multiplier exp(0.07*5) = 1.419 -> 1.42x.
    now = int(time.time() * 1000)
    sql(db_path, "UPDATE telefly_rounds SET betting_end = ?, fly_start = ?,"
                 " crash_time = ? WHERE id = ?",
        (now - 60000, now - 5000, now + 600000, st["round_id"]))
    st = c.get("/api/casino/telefly/state").get_json()
    assert st["phase"] == "flying" and st["multiplier"] in (1.42, 1.43)
    assert c.post("/api/casino/telefly/bet", json={"stake": 5}).status_code == 400
    d = c.post("/api/casino/telefly/cashout", json={}).get_json()
    expected_mult = d["multiplier"]
    expected_payout = round(10 * expected_mult, 2)
    assert expected_mult in (1.42, 1.43) and d["payout"] == expected_payout
    assert balance(c) == 90.0 + expected_payout
    assert c.post("/api/casino/telefly/cashout", json={}).status_code == 400
    rows = [g for g in casino_rows(c, pid) if g["game"] == "TeleFly"]
    assert rows and rows[0]["stake"] == 10 and rows[0]["payout"] == expected_payout
    login(c, "demo", "demo123")  # casino_rows leaves the client logged out
    # Close the manipulated flying round (crash it, settle it), then the
    # next state call opens a fresh betting round.
    now = int(time.time() * 1000)
    sql(db_path, "UPDATE telefly_rounds SET crash_time = ? WHERE id = ?",
        (now - 5000, st["round_id"]))
    st = c.get("/api/casino/telefly/state").get_json()
    assert st["phase"] == "crashed"
    st = c.get("/api/casino/telefly/state").get_json()
    assert st["phase"] == "betting"
    # New round: bet, then force a crash at 2.5x and settle via state.
    assert c.post("/api/casino/telefly/bet", json={"stake": 10}).status_code == 200
    assert balance(c) == 94.20
    now = int(time.time() * 1000)
    sql(db_path, "UPDATE telefly_rounds SET betting_end = ?, fly_start = ?,"
                 " crash_time = ?, crash_point = ? WHERE id = ?",
        (now - 60000, now - 60000, now - 1000, 2.5, st["round_id"]))
    st = c.get("/api/casino/telefly/state").get_json()
    assert st["phase"] == "crashed" and st["crash_point"] == 2.5
    assert balance(c) == 94.20  # loser: stake already left, nothing back
    rows = [g for g in casino_rows(c, pid) if g["game"] == "TeleFly"]
    assert rows[0]["stake"] == 10 and rows[0]["payout"] == 0.0


def test_telefly_guards(env):
    c, _, _, _ = env
    assert c.post("/api/casino/telefly/bet", json={"stake": 10}).status_code == 401
    login(c, "admin", "admin123")
    assert c.post("/api/casino/telefly/bet", json={"stake": 10}).status_code == 403


# ---------------- PvP Wheel ----------------

def test_pvp_full_round_winner_math(env):
    admin_c, p1, p2, db_path = env
    login(p1, "demo", "demo123")
    p1_id = demo_pid(p1)
    p2_id = make_player(admin_c, p2, db_path, "pvp2", 100)
    assert p1.post("/api/casino/pvp/bet", json={"stake": 10}).status_code == 200
    st = p1.get("/api/casino/pvp/state").get_json()
    assert st["status"] == "waiting" and st["pot"] == 10.0 and st["players"] == 1
    assert p2.post("/api/casino/pvp/bet", json={"stake": 30}).status_code == 200
    st = p1.get("/api/casino/pvp/state").get_json()
    assert st["status"] == "countdown" and st["pot"] == 40.0 and st["players"] == 2
    assert p1.post("/api/casino/pvp/cancel", json={}).status_code == 400
    now = int(time.time() * 1000)
    sql(db_path, "UPDATE pvp_rounds SET countdown_end = ? WHERE id = ?",
        (now - 1000, st["round_id"]))
    st = p1.get("/api/casino/pvp/state").get_json()
    assert st["status"] == "spinning" and st["winner"] in ("demo", "pvp2")
    assert st["payout"] == 38.0  # pot 40 minus 5% edge
    assert p1.post("/api/casino/pvp/bet", json={"stake": 5}).status_code == 400
    now = int(time.time() * 1000)
    sql(db_path, "UPDATE pvp_rounds SET spin_end = ? WHERE id = ?",
        (now - 1000, st["round_id"]))
    b1_before = balance(p1)  # 90 after bet; p2 70 after bet
    b2_before = balance(p2)
    st = p1.get("/api/casino/pvp/state").get_json()
    assert st["status"] == "done"
    b1, b2 = balance(p1), balance(p2)
    gained = [(b1 - b1_before), (b2 - b2_before)]
    assert sorted(gained) == [0.0, 38.0]
    winner = p1 if gained[0] == 38.0 else p2
    loser = p2 if winner is p1 else p1
    winner_id = p1_id if winner is p1 else p2_id
    loser_id = p2_id if winner is p1 else p1_id
    wrows = [g for g in casino_rows(winner, winner_id) if g["game"] == "PvP Wheel"]
    lrows = [g for g in casino_rows(loser, loser_id) if g["game"] == "PvP Wheel"]
    assert wrows[-1]["payout"] == 38.0
    assert lrows[-1]["payout"] == 0.0
    # Next state call opens a fresh waiting round.
    st = p1.get("/api/casino/pvp/state").get_json()
    assert st["status"] == "waiting" and st["pot"] == 0.0


def test_pvp_cancel_refund_and_single_player_waits(env):
    admin_c, p1, _, db_path = env
    login(p1, "demo", "demo123")
    assert p1.post("/api/casino/pvp/bet", json={"stake": 10}).status_code == 200
    assert balance(p1) == 90.0
    d = p1.post("/api/casino/pvp/cancel", json={}).get_json()
    assert d["refunded"] == 10.0 and balance(p1) == 100.0
    assert p1.post("/api/casino/pvp/cancel", json={}).status_code == 400
    # A lone player never triggers a countdown.
    assert p1.post("/api/casino/pvp/bet", json={"stake": 5}).status_code == 200
    st = p1.get("/api/casino/pvp/state").get_json()
    assert st["status"] == "waiting"


# ---------------- Lottery ----------------

def test_lottery_buy_draw_and_tier_math(env):
    admin_c, p1, p2, db_path = env
    login(p1, "demo", "demo123")
    p1_id = demo_pid(p1)
    p2_id = make_player(admin_c, p2, db_path, "lotto2", 100)
    assert p1.post("/api/casino/lottery/buy",
                   json={"stake": 10, "numbers": [1, 2, 3, 4, 5]}).status_code == 400
    assert p1.post("/api/casino/lottery/buy",
                   json={"stake": 10, "numbers": [1, 2, 3, 4, 5, 5]}).status_code == 400
    assert p1.post("/api/casino/lottery/buy",
                   json={"stake": 10, "numbers": [1, 2, 3, 4, 5, 50]}).status_code == 400
    d = p1.post("/api/casino/lottery/buy",
                json={"stake": 10, "numbers": [1, 2, 3, 4, 5, 6]}).get_json()
    assert d["numbers"] == [1, 2, 3, 4, 5, 6]
    assert p1.post("/api/casino/lottery/buy",
                   json={"stake": 10, "numbers": [7, 8, 9, 10, 11, 12]}).status_code == 400
    q = p2.post("/api/casino/lottery/buy", json={"stake": 20, "quickpick": True}).get_json()
    assert len(q["numbers"]) == 6 and len(set(q["numbers"])) == 6
    assert all(1 <= n <= 49 for n in q["numbers"])
    assert balance(p1) == 90.0 and balance(p2) == 80.0
    st = p1.get("/api/casino/lottery/state").get_json()
    assert st["pot"] == 30.0 and st["my_ticket"]["numbers"] == [1, 2, 3, 4, 5, 6]
    now = int(time.time() * 1000)
    sql(db_path, "UPDATE lottery_rounds SET draw_at = ? WHERE id = ?",
        (now - 1000, st["round_id"]))
    st = p1.get("/api/casino/lottery/state").get_json()
    assert st["last_draws"], "draw did not settle"
    drawn = set(st["last_draws"][0]["numbers"])
    assert len(drawn) == 6
    pot_total = 30.0
    tiers = {6: 0.50, 5: 0.20, 4: 0.15, 3: 0.10}
    matches = {"p1": len({1, 2, 3, 4, 5, 6} & drawn),
               "p2": len(set(q["numbers"]) & drawn)}
    counts = {}
    for m in matches.values():
        if m >= 3:
            counts[m] = counts.get(m, 0) + 1
    expected = {}
    for key, m in matches.items():
        expected[key] = round(pot_total * tiers[m] / counts[m], 2) if m >= 3 else 0.0
    for client, pid, key in ((p1, p1_id, "p1"), (p2, p2_id, "p2")):
        rows = [g for g in casino_rows(client, pid) if g["game"] == "Lottery"]
        assert rows and rows[-1]["payout"] == expected[key]
    paid = sum(expected.values())
    # Next round inherits exactly the unclaimed + house remainder.
    assert st["rollover_in"] == round(pot_total - paid, 2)


def test_lottery_guards(env):
    c, _, _, _ = env
    assert c.post("/api/casino/lottery/buy",
                   json={"stake": 10, "quickpick": True}).status_code == 401
    login(c, "admin", "admin123")
    assert c.post("/api/casino/lottery/buy",
                   json={"stake": 10, "quickpick": True}).status_code == 403
