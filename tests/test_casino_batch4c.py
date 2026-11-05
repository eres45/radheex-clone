"""Tests for batch-4c casino games: Bingo, Scratch, Fish Table, Tower,
Cases, Penalty, Darts, Horse Race, Colors, Pick 3.

Random outcomes are never assumed: tests recompute the expected payout
from the server's public result (card/balls, grid, draw, finish order),
or force deterministic sequences by monkeypatching module-level
factories (tower draws, pick-3 digits). All ten games are original
implementations of their published rules; exact edges are verified
with Fraction arithmetic, and Bingo/Scratch/Darts carry
simulation-measured RTPs (see README) because their exact edge needs
enumeration over a large outcome space.
"""
import sqlite3
import sys
import os
from fractions import Fraction as F

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import app as appmod
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


def my_id(client):
    return client.get("/api/me").get_json()["user"]["id"]


def casino_rows(client, pid):
    client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    det = client.get(f"/api/admin/players/{pid}").get_json()
    assert "casino" in det, det
    client.post("/api/auth/logout")
    return det["casino"]


def bingo_lines(card, balls):
    marked = set(balls) | {0}
    n = 0
    for r in range(5):
        if all(card[r][c] in marked for c in range(5)):
            n += 1
    for c in range(5):
        if all(card[r][c] in marked for r in range(5)):
            n += 1
    if all(card[i][i] in marked for i in range(5)):
        n += 1
    if all(card[i][4 - i] in marked for i in range(5)):
        n += 1
    return n


# ---------------- unit: exact edges ----------------

def test_edges_unit():
    # Fish: catch probability x multiplier per tier.
    assert abs(float(F(600, 1000) * F(162, 100)) - 0.972) < 0.0001
    assert abs(float(F(400, 1000) * F(242, 100)) - 0.968) < 0.0001
    assert abs(float(F(250, 1000) * F(388, 100)) - 0.970) < 0.0001
    assert abs(float(F(100, 1000) * F(970, 100)) - 0.970) < 0.0001
    # Cases: weighted tier sum.
    ev = (F(550, 1000) * F(4, 10) + F(250, 1000) * F(9, 10)
          + F(120, 1000) * F(17, 10) + F(60, 1000) * F(34, 10)
          + F(20, 1000) * 6)
    assert abs(float(ev) - 0.973) < 0.0001
    # Penalty: keeper dives corners 22% each, centre 6% each.
    assert abs(float(F(78, 100) * F(124, 100)) - 0.9672) < 0.0001
    assert abs(float(F(94, 100) * F(103, 100)) - 0.9682) < 0.0001
    # Horse race: per-pick win probability x payout.
    for p, m in [(300, 323), (220, 441), (180, 539),
                 (140, 693), (100, 970), (60, 1617)]:
        ev = float(F(p, 1000) * F(m, 100))
        assert 0.969 <= ev <= 0.971, (p, m, ev)
    # Colors: per-pick win probability x payout.
    for p, m in [(400, 242), (300, 323), (200, 485), (100, 970)]:
        ev = float(F(p, 1000) * F(m, 100))
        assert 0.968 <= ev <= 0.971, (p, m, ev)
    # Pick 3: straight 1/1000 x 970; box distinct 6/1000 x 160;
    # box pair 3/1000 x 320.
    assert abs(float(F(1, 1000) * 970) - 0.970) < 0.0001
    assert abs(float(F(6, 1000) * 160) - 0.960) < 0.0001
    assert abs(float(F(3, 1000) * 320) - 0.960) < 0.0001
    # Tower: survival 78% per level x cash-out multiplier.
    mults = [1.24, 1.59, 2.04, 2.62, 3.36, 4.31, 5.52, 7.08]
    for k, m in enumerate(mults, start=1):
        ev = float(F(78, 100) ** k * F(int(m * 100), 100))
        assert 0.967 <= ev <= 0.971, (k, ev)


# ---------------- guards ----------------

def test_guards(env):
    c, _c2, _c3, _db = env
    posts = [
        ("/api/casino/bingo", {"stake": 10}),
        ("/api/casino/scratch", {"stake": 10}),
        ("/api/casino/fish", {"stake": 10, "tier": "small"}),
        ("/api/casino/tower/start", {"stake": 10}),
        ("/api/casino/cases", {"stake": 10}),
        ("/api/casino/penalty", {"stake": 10, "spot": "TL"}),
        ("/api/casino/darts", {"stake": 10}),
        ("/api/casino/horse", {"stake": 10, "horse": "Thunder Bolt"}),
        ("/api/casino/colors", {"stake": 10, "color": "red"}),
        ("/api/casino/pick3", {"stake": 10, "bet": "straight", "digits": "123"}),
        ("/api/casino/tower/climb", {"game_id": 1}),
        ("/api/casino/tower/cashout", {"game_id": 1}),
    ]
    for path, body in posts:
        assert c.post(path, json=body).status_code == 401, path
    login(c, "admin", "admin123")
    for path, body in posts:
        # Single-round endpoints refuse admins with 403; tower
        # climb/cashout on an unknown game correctly report 404.
        want = 404 if path.startswith("/api/casino/tower/") and path != "/api/casino/tower/start" else 403
        assert c.post(path, json=body).status_code == want, path
    c.post("/api/auth/logout")
    login(c, "demo", "demo123")
    # Over-balance and bad params.
    assert c.post("/api/casino/bingo", json={"stake": 100000}).status_code == 400
    assert c.post("/api/casino/fish", json={"stake": 10, "tier": "whale"}).status_code == 400
    assert c.post("/api/casino/penalty", json={"stake": 10, "spot": "XX"}).status_code == 400
    assert c.post("/api/casino/horse", json={"stake": 10, "horse": "Nope"}).status_code == 400
    assert c.post("/api/casino/colors", json={"stake": 10, "color": "pink"}).status_code == 400
    assert c.post("/api/casino/pick3", json={"stake": 10, "bet": "straight", "digits": "12"}).status_code == 400
    assert c.post("/api/casino/pick3", json={"stake": 10, "bet": "weird", "digits": "123"}).status_code == 400


# ---------------- payout recomputation ----------------

def test_bingo_recompute(env):
    c, _c2, _c3, _db = env
    login(c, "demo", "demo123")
    for _ in range(5):
        before = balance(c)
        d = c.post("/api/casino/bingo", json={"stake": 10}).get_json()
        assert d["ok"] and len(d["balls"]) == 30 and len(set(d["balls"])) == 30
        assert len(d["card"]) == 5 and all(len(r) == 5 for r in d["card"])
        nums = {n for row in d["card"] for n in row if n != 0}
        assert len(nums) == 24 and all(1 <= n <= 75 for n in nums)
        lines = bingo_lines(d["card"], d["balls"])
        assert d["lines"] == lines
        if nums <= set(d["balls"]):
            assert d["full_house"] and d["multiplier"] == 1000.0
        elif lines >= 3:
            assert d["multiplier"] == 100.0
        elif lines:
            assert d["multiplier"] == {1: 5.0, 2: 21.0}[lines]
        else:
            assert d["multiplier"] == 0.0
        assert d["payout"] == round(10 * d["multiplier"], 2)
        assert balance(c) == round(before - 10 + d["payout"], 2)


def test_scratch_recompute(env):
    c, _c2, _c3, _db = env
    login(c, "demo", "demo123")
    pay = {"cherry": 1.5, "lemon": 2.5, "bell": 4.0,
           "star": 8.0, "seven": 20.0, "diamond": 40.0}
    lines_idx = [(0, 1, 2), (3, 4, 5), (6, 7, 8),
                 (0, 3, 6), (1, 4, 7), (2, 5, 8), (0, 4, 8), (2, 4, 6)]
    for _ in range(10):
        before = balance(c)
        d = c.post("/api/casino/scratch", json={"stake": 10}).get_json()
        assert d["ok"] and len(d["grid"]) == 9
        best = 0.0
        for a, b, cc in lines_idx:
            if d["grid"][a] == d["grid"][b] == d["grid"][cc]:
                best = max(best, pay[d["grid"][a]])
        assert d["multiplier"] == best
        assert d["payout"] == round(10 * best, 2)
        assert balance(c) == round(before - 10 + d["payout"], 2)


def test_fish_cases_penalty(env):
    c, _c2, _c3, _db = env
    login(c, "demo", "demo123")
    fish = {"small": 1.62, "medium": 2.42, "big": 3.88, "golden": 9.70}
    for tier, mult in fish.items():
        before = balance(c)
        d = c.post("/api/casino/fish", json={"stake": 10, "tier": tier}).get_json()
        assert d["ok"] and d["tier"] == tier
        assert d["payout"] == (round(10 * mult, 2) if d["caught"] else 0.0)
        assert balance(c) == round(before - 10 + d["payout"], 2)
    case_pay = {"common": 0.4, "uncommon": 0.9, "rare": 1.7,
                "epic": 3.4, "legendary": 6.0}
    for _ in range(5):
        before = balance(c)
        d = c.post("/api/casino/cases", json={"stake": 10}).get_json()
        assert d["ok"] and d["multiplier"] == case_pay[d["tier"]]
        assert d["payout"] == round(10 * d["multiplier"], 2)
        assert balance(c) == round(before - 10 + d["payout"], 2)
    for spot in ("TL", "TM", "TR", "BL", "BM", "BR"):
        before = balance(c)
        d = c.post("/api/casino/penalty", json={"stake": 10, "spot": spot}).get_json()
        assert d["ok"] and d["goal"] == (d["keeper"] != spot)
        want = (1.24 if spot in ("TL", "TR", "BL", "BR") else 1.03) if d["goal"] else 0.0
        assert d["multiplier"] == want
        assert d["payout"] == round(10 * want, 2)
        assert balance(c) == round(before - 10 + d["payout"], 2)


def test_darts_horse_colors(env):
    c, _c2, _c3, _db = env
    # Funded player, not demo: 15 x 10-pt plays on a 100-pt demo
    # balance can drain below the stake on a losing streak and 400
    # mid-test (pre-existing probabilistic flake, ~1/15 runs). A 5000-pt
    # bankroll cannot drain in 15 plays, so the test measures payouts,
    # not bankroll luck.
    _c2.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert _c2.post("/api/admin/players", json={
        "username": "dartfund", "password": "password12", "credit": 5000}).status_code == 200
    login(c, "dartfund", "password12")
    for _ in range(5):
        before = balance(c)
        d = c.post("/api/casino/darts", json={"stake": 10}).get_json()
        assert d["ok"] and len(d["throws"]) == 3
        assert d["total"] == sum(t["score"] for t in d["throws"])
        want = 12.0 if d["total"] >= 120 else 4.0 if d["total"] >= 90 else \
            2.0 if d["total"] >= 60 else 1.0 if d["total"] >= 40 else 0.0
        assert d["multiplier"] == want
        assert d["payout"] == round(10 * want, 2)
        assert balance(c) == round(before - 10 + d["payout"], 2)
    horse_pay = {"Thunder Bolt": 3.23, "Desert Wind": 4.41,
                 "Midnight Star": 5.39, "Golden Hoof": 6.93,
                 "River Queen": 9.70, "Lucky Charm": 16.17}
    for pick in horse_pay:
        before = balance(c)
        d = c.post("/api/casino/horse", json={"stake": 10, "horse": pick}).get_json()
        assert d["ok"] and d["order"][0] == d["winner"] and len(d["order"]) == 6
        assert sorted(d["order"]) == sorted(horse_pay)
        want = horse_pay[d["winner"]] if d["winner"] == pick else 0.0
        assert d["multiplier"] == want
        assert d["payout"] == round(10 * want, 2)
        assert balance(c) == round(before - 10 + d["payout"], 2)
    color_pay = {"red": 2.42, "blue": 3.23, "green": 4.85, "gold": 9.70}
    for pick in color_pay:
        before = balance(c)
        d = c.post("/api/casino/colors", json={"stake": 10, "color": pick}).get_json()
        assert d["ok"]
        want = color_pay[d["color"]] if d["color"] == pick else 0.0
        assert d["multiplier"] == want
        assert d["payout"] == round(10 * want, 2)
        assert balance(c) == round(before - 10 + d["payout"], 2)


def test_pick3_forced(env, monkeypatch):
    c, _c2, _c3, _db = env
    login(c, "demo", "demo123")
    # secrets.randbelow is shared: queue one draw (3 values) per play.
    seq = [[1, 2, 3], [1, 1, 2], [5, 5, 5], [3, 2, 1]]
    state = {"i": 0, "j": 0}

    def _randbelow(n):
        assert n == 10
        v = seq[state["i"]][state["j"]]
        state["j"] += 1
        if state["j"] == 3:
            state["i"] += 1
            state["j"] = 0
        return v
    monkeypatch.setattr(appmod.secrets, "randbelow", _randbelow)
    cases = [("straight", "123", 970.0), ("box", "112", 320.0),
             ("box", "555", 970.0), ("box", "123", 160.0)]
    for bet, digits, mult in cases:
        before = balance(c)
        d = c.post("/api/casino/pick3",
                   json={"stake": 10, "bet": bet, "digits": digits}).get_json()
        assert d["ok"] and d["multiplier"] == mult, d
        assert d["payout"] == round(10 * mult, 2)
        assert balance(c) == round(before - 10 + d["payout"], 2)


# ---------------- tower multi-step ----------------

def test_tower_flow(env, monkeypatch):
    c, _c2, _c3, _db = env
    login(c, "demo", "demo123")
    pid = my_id(c)
    # Cashout before any climb is rejected.
    d = c.post("/api/casino/tower/start", json={"stake": 10}).get_json()
    assert d["ok"] and d["level"] == 0
    gid = d["game_id"]
    assert balance(c) == 90.0  # stake left at start, no history row yet
    assert c.post("/api/casino/tower/cashout", json={"game_id": gid}).status_code == 400
    # Forced safe climbs then cashout at level 3.
    monkeypatch.setattr(appmod, "_tower_draw", lambda: True)
    for level, mult in ((1, 1.24), (2, 1.59), (3, 2.04)):
        r = c.post("/api/casino/tower/climb", json={"game_id": gid}).get_json()
        assert r["ok"] and r["safe"] and r["level"] == level
        assert r["multiplier"] == mult and r["potential_payout"] == round(10 * mult, 2)
    r = c.post("/api/casino/tower/cashout", json={"game_id": gid}).get_json()
    assert r["ok"] and r["level"] == 3 and r["payout"] == 20.40
    assert balance(c) == 110.40
    assert c.post("/api/casino/tower/climb", json={"game_id": gid}).status_code == 400
    rows = [row for row in casino_rows(c, pid) if row["game"] == "Tower"]
    assert rows and rows[-1]["stake"] == 10 and rows[-1]["payout"] == 20.40
    login(c, "demo", "demo123")
    # Bust path: forced unsafe climb.
    monkeypatch.setattr(appmod, "_tower_draw", lambda: False)
    d = c.post("/api/casino/tower/start", json={"stake": 10}).get_json()
    gid = d["game_id"]
    r = c.post("/api/casino/tower/climb", json={"game_id": gid}).get_json()
    assert r["ok"] and r["bust"] and r["payout"] == 0.0
    assert balance(c) == 100.40
    rows = [row for row in casino_rows(c, pid) if row["game"] == "Tower"]
    assert any(r["stake"] == 10 and r["payout"] == 0.0 and "Bust" in r["outcome"]
               for r in rows)
    # Another player's game is forbidden.
    login(c, "admin", "admin123")
    assert c.post("/api/casino/tower/climb", json={"game_id": gid}).status_code == 403


# ---------------- history agreement ----------------

def test_history_agreement(env):
    c, _c2, _c3, _db = env
    login(c, "demo", "demo123")
    pid = my_id(c)
    c.post("/api/casino/bingo", json={"stake": 10})
    c.post("/api/casino/scratch", json={"stake": 10})
    c.post("/api/casino/cases", json={"stake": 10})
    c.post("/api/casino/darts", json={"stake": 10})
    rows = casino_rows(c, pid)
    games = {row["game"] for row in rows}
    assert {"Bingo", "Scratch", "Cases", "Darts"} <= games
    for row in rows:
        if row["game"] in ("Bingo", "Scratch", "Cases", "Darts"):
            assert row["stake"] == 10
            assert row["profit"] == round(row["payout"] - 10, 2)
