"""Tests for batch-4b casino games: Craps, Sic Bo, Big Six, Chuck-a-Luck,
Under/Over 7, Mini Roulette, Andar Bahar.

Random outcomes are never assumed: tests recompute the expected payout
from the server's public result, or force deterministic dice/deck
sequences by monkeypatching the module-level factories (batch-4a
technique). All seven games are original implementations of their
published rules; edges are verified exactly with Fraction arithmetic.
"""
import sqlite3
import sys
import os
from fractions import Fraction as F
from math import comb

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


def dice_queue(monkeypatch, rolls):
    """Make _dice_roll return the given rolls in order (each roll is a
    list of dice matching the requested count)."""
    q = [list(r) for r in rolls]

    def _roll(n):
        assert q, "dice queue exhausted"
        r = q.pop(0)
        assert len(r) == n, (r, n)
        return r

    monkeypatch.setattr(appmod, "_dice_roll", _roll)


def card(rank, suit="♠"):
    return {"rank": rank, "suit": suit}


# ---------------- unit: exact edges ----------------

def test_edges_unit():
    # Craps: enumerate the 36 come-out outcomes; a point resolves to a
    # win with P(point)/(P(point)+P(7)).
    dist = {}
    for a in range(1, 7):
        for b in range(1, 7):
            dist[a + b] = dist.get(a + b, 0) + 1
    P = {k: F(v, 36) for k, v in dist.items()}
    ev_pass = F(0)
    ev_dont = F(0)
    for total, p in P.items():
        if total in (7, 11):
            ev_pass += p * 2
        elif total in (2, 3):
            ev_dont += p * 2
        elif total == 12:
            ev_dont += p * 1  # push
        else:
            ev_pass += p * (P[total] / (P[total] + P[7])) * 2
            ev_dont += p * (P[7] / (P[total] + P[7])) * 2
    assert abs(float(ev_pass) - 0.9859) < 0.0001  # 1.41% edge
    assert abs(float(ev_dont) - 0.9864) < 0.0001  # 1.36% edge
    # Field: 2 pays 4x, 12 pays 3x, 3/4/9/10/11 pay 2x.
    ev_field = (F(1, 36) * 4 + F(1, 36) * 3
                + F(2 + 3 + 4 + 3 + 2, 36) * 2)
    assert abs(float(ev_field) - 0.9722) < 0.0001  # 2.78% edge
    # Sic bo big/small: totals 11-17 / 4-10 minus the two triples in
    # range (4-4-4, 5-5-5) = 105 winning combos of 216, paying 2x.
    assert abs(float(F(105, 216) * 2) - 0.9722) < 0.0001
    # Single number / chuck-a-luck: 75 one-match, 15 two-match, 1 triple.
    ev_single = F(75, 216) * 2 + F(15, 216) * 3 + F(1, 216) * 15
    assert abs(float(ev_single) - 0.9722) < 0.0001
    assert appmod._dice_single_mult(0) == 0.0
    assert appmod._dice_single_mult(1) == 2.0
    assert appmod._dice_single_mult(2) == 3.0
    assert appmod._dice_single_mult(3) == 15.0
    # Combo: 30 of 216 rolls contain both numbers, paying 7x.
    assert abs(float(F(30, 216) * 7) - 0.9722) < 0.0001
    # Under/over 7: 15 of 36 win at 2x; exactly 7: 6 of 36 win at 5x.
    assert abs(float(F(15, 36) * 2) - 0.8333) < 0.0001  # 16.67% edge
    assert abs(float(F(6, 36) * 5) - 0.8333) < 0.0001
    # Mini roulette: 1 of 13 straight at 12x; 6 of 13 even-money at 2x;
    # 4 of 13 dozen at 3x — all 12/13.
    assert abs(float(F(12, 13)) - 0.9231) < 0.0001  # 7.69% edge
    # Andar Bahar: earliest of 3 matching ranks among 51 positions is
    # odd (Andar deals first) with P ~51.50%; first-card Andar pays 1.25x.
    tot3 = comb(51, 3)
    p_andar = sum(F(comb(51 - m, 2), tot3) for m in range(1, 52, 2))
    p_first = F(3, 51)
    ev_andar = (p_andar - p_first) * 2 + p_first * F(5, 4)
    ev_bahar = (1 - p_andar) * 2
    assert abs(float(ev_andar) - 0.9859) < 0.0001  # 1.41% edge
    assert abs(float(ev_bahar) - 0.9700) < 0.0001  # 3.00% edge
    # Big Six: standard wheel counts x standard payouts / 54.
    segs = appmod.BIGSIX_SEGMENTS
    assert len(segs) == 54
    assert segs.count("1") == 24 and segs.count("2") == 15
    assert segs.count("5") == 7 and segs.count("10") == 4
    assert segs.count("20") == 2 and segs.count("joker") == 1
    assert segs.count("logo") == 1
    for seg, pay in appmod.BIGSIX_PAY.items():
        ev = segs.count(seg) * pay / 54
        assert 0.77 < ev < 0.90, (seg, ev)  # published 11.1-22.2% edges


# ---------------- Craps ----------------

def test_craps_sequences_and_guards(env, monkeypatch):
    c, _, _, _ = env
    assert c.post("/api/casino/craps", json={"stake": 10, "bet": "pass"}).status_code == 401
    login(c, "demo", "demo123")
    assert c.post("/api/casino/craps", json={"stake": 10, "bet": "bogus"}).status_code == 400
    assert c.post("/api/casino/craps", json={"stake": 10000, "bet": "pass"}).status_code == 400
    login(c, "admin", "admin123")
    assert c.post("/api/casino/craps", json={"stake": 10, "bet": "pass"}).status_code == 403
    login(c, "demo", "demo123")
    # Come-out 7: pass wins 2x.
    dice_queue(monkeypatch, [[4, 3]])
    d = c.post("/api/casino/craps", json={"stake": 10, "bet": "pass"}).get_json()
    assert d["ok"] and d["rolls"] == [[4, 3]] and d["point"] is None
    assert d["payout"] == 20.0 and balance(c) == 110.0
    # Come-out 2: pass loses.
    dice_queue(monkeypatch, [[1, 1]])
    d = c.post("/api/casino/craps", json={"stake": 10, "bet": "pass"}).get_json()
    assert d["payout"] == 0.0 and balance(c) == 100.0
    # Point 6, then 6: pass wins.
    dice_queue(monkeypatch, [[3, 3], [1, 5]])
    d = c.post("/api/casino/craps", json={"stake": 10, "bet": "pass"}).get_json()
    assert d["point"] == 6 and d["rolls"] == [[3, 3], [1, 5]]
    assert d["payout"] == 20.0 and balance(c) == 110.0
    # Point 6, then 7: don't pass wins, pass loses.
    dice_queue(monkeypatch, [[3, 3], [4, 3]])
    d = c.post("/api/casino/craps", json={"stake": 10, "bet": "dontpass"}).get_json()
    assert d["payout"] == 20.0 and balance(c) == 120.0
    # Come-out 12: don't pass pushes (stake back).
    dice_queue(monkeypatch, [[6, 6]])
    d = c.post("/api/casino/craps", json={"stake": 10, "bet": "dontpass"}).get_json()
    assert d["payout"] == 10.0 and balance(c) == 120.0
    # Field: 2 pays 4x, 12 pays 3x, 5 loses.
    dice_queue(monkeypatch, [[1, 1]])
    d = c.post("/api/casino/craps", json={"stake": 10, "bet": "field"}).get_json()
    assert d["payout"] == 40.0 and balance(c) == 150.0
    dice_queue(monkeypatch, [[6, 6]])
    d = c.post("/api/casino/craps", json={"stake": 10, "bet": "field"}).get_json()
    assert d["payout"] == 30.0 and balance(c) == 170.0
    dice_queue(monkeypatch, [[2, 3]])
    d = c.post("/api/casino/craps", json={"stake": 10, "bet": "field"}).get_json()
    assert d["payout"] == 0.0 and balance(c) == 160.0


# ---------------- Sic bo ----------------

def test_sicbo_rules_and_guards(env, monkeypatch):
    c, _, _, _ = env
    assert c.post("/api/casino/sicbo", json={"stake": 10, "bet": "big"}).status_code == 401
    login(c, "demo", "demo123")
    assert c.post("/api/casino/sicbo", json={"stake": 10, "bet": "bogus"}).status_code == 400
    assert c.post("/api/casino/sicbo", json={"stake": 10, "bet": "single", "number": 7}).status_code == 400
    assert c.post("/api/casino/sicbo", json={"stake": 10, "bet": "combo", "numbers": [3, 3]}).status_code == 400
    # Triple 4-4-4 (total 12) LOSES on big — triples are excluded.
    dice_queue(monkeypatch, [[4, 4, 4]])
    d = c.post("/api/casino/sicbo", json={"stake": 10, "bet": "big"}).get_json()
    assert d["triple"] is True and d["payout"] == 0.0 and balance(c) == 90.0
    # Small wins on 3-2-2 (total 7, no triple).
    dice_queue(monkeypatch, [[3, 2, 2]])
    d = c.post("/api/casino/sicbo", json={"stake": 10, "bet": "small"}).get_json()
    assert d["payout"] == 20.0 and balance(c) == 100.0
    # Single: two matches pay 3x.
    dice_queue(monkeypatch, [[5, 5, 2]])
    d = c.post("/api/casino/sicbo", json={"stake": 10, "bet": "single", "number": 5}).get_json()
    assert d["payout"] == 30.0 and balance(c) == 120.0
    # Combo hit pays 7x; combo miss pays 0.
    dice_queue(monkeypatch, [[1, 4, 6]])
    d = c.post("/api/casino/sicbo", json={"stake": 10, "bet": "combo", "numbers": [1, 6]}).get_json()
    assert d["payout"] == 70.0 and balance(c) == 180.0
    dice_queue(monkeypatch, [[1, 4, 6]])
    d = c.post("/api/casino/sicbo", json={"stake": 10, "bet": "combo", "numbers": [2, 6]}).get_json()
    assert d["payout"] == 0.0 and balance(c) == 170.0


# ---------------- Big Six ----------------

def test_bigsix_math_and_guards(env):
    c, _, _, _ = env
    assert c.post("/api/casino/bigsix", json={"stake": 10, "bet": "1"}).status_code == 401
    login(c, "demo", "demo123")
    assert c.post("/api/casino/bigsix", json={"stake": 10, "bet": "50"}).status_code == 400
    assert c.post("/api/casino/bigsix", json={"stake": 10000, "bet": "1"}).status_code == 400
    before = balance(c)
    d = c.post("/api/casino/bigsix", json={"stake": 10, "bet": "1"}).get_json()
    assert d["ok"] and d["segment"] in appmod.BIGSIX_PAY
    assert appmod.BIGSIX_SEGMENTS[d["segment_index"]] == d["segment"]
    expected = 10.0 * appmod.BIGSIX_PAY[d["segment"]] if d["segment"] == "1" else 0.0
    assert d["payout"] == expected
    assert balance(c) == round(before - 10 + expected, 2)


# ---------------- Chuck-a-Luck ----------------

def test_chuck_math_and_guards(env, monkeypatch):
    c, _, _, _ = env
    assert c.post("/api/casino/chuck", json={"stake": 10, "number": 3}).status_code == 401
    login(c, "demo", "demo123")
    assert c.post("/api/casino/chuck", json={"stake": 10, "number": 0}).status_code == 400
    # Triple match pays 15x.
    dice_queue(monkeypatch, [[3, 3, 3]])
    d = c.post("/api/casino/chuck", json={"stake": 10, "number": 3}).get_json()
    assert d["matches"] == 3 and d["payout"] == 150.0 and balance(c) == 240.0
    # No match pays 0.
    dice_queue(monkeypatch, [[1, 2, 4]])
    d = c.post("/api/casino/chuck", json={"stake": 10, "number": 3}).get_json()
    assert d["matches"] == 0 and d["payout"] == 0.0 and balance(c) == 230.0


# ---------------- Under / Over 7 ----------------

def test_underover_math_and_guards(env, monkeypatch):
    c, _, _, _ = env
    assert c.post("/api/casino/underover", json={"stake": 10, "bet": "under"}).status_code == 401
    login(c, "demo", "demo123")
    assert c.post("/api/casino/underover", json={"stake": 10, "bet": "sideways"}).status_code == 400
    dice_queue(monkeypatch, [[1, 1]])
    d = c.post("/api/casino/underover", json={"stake": 10, "bet": "under"}).get_json()
    assert d["total"] == 2 and d["payout"] == 20.0 and balance(c) == 110.0
    dice_queue(monkeypatch, [[6, 6]])
    d = c.post("/api/casino/underover", json={"stake": 10, "bet": "over"}).get_json()
    assert d["total"] == 12 and d["payout"] == 20.0 and balance(c) == 120.0
    dice_queue(monkeypatch, [[3, 4]])
    d = c.post("/api/casino/underover", json={"stake": 10, "bet": "seven"}).get_json()
    assert d["total"] == 7 and d["payout"] == 50.0 and balance(c) == 160.0
    dice_queue(monkeypatch, [[1, 2]])
    d = c.post("/api/casino/underover", json={"stake": 10, "bet": "seven"}).get_json()
    assert d["payout"] == 0.0 and balance(c) == 150.0


# ---------------- Mini roulette ----------------

def test_miniroulette_math_and_guards(env):
    c, _, _, _ = env
    assert c.post("/api/casino/miniroulette",
                  json={"bets": [{"type": "red", "amount": 10}]}).status_code == 401
    login(c, "demo", "demo123")
    assert c.post("/api/casino/miniroulette", json={"bets": []}).status_code == 400
    assert c.post("/api/casino/miniroulette",
                  json={"bets": [{"type": "bogus", "amount": 10}]}).status_code == 400
    assert c.post("/api/casino/miniroulette",
                  json={"bets": [{"type": "straight", "value": 13, "amount": 10}]}).status_code == 400
    assert c.post("/api/casino/miniroulette",
                  json={"bets": [{"type": "red", "amount": 10000}]}).status_code == 400
    before = balance(c)
    bets = [{"type": "straight", "value": 7, "amount": 10},
            {"type": "red", "amount": 10},
            {"type": "dozen", "value": 2, "amount": 10}]
    d = c.post("/api/casino/miniroulette", json={"bets": bets}).get_json()
    assert d["ok"] and d["total_stake"] == 30.0
    n = d["number"]
    exp = 0.0
    exp += 10 * 12.0 if n == 7 else 0.0
    exp += 10 * 2.0 if n in appmod.MINI_RED else 0.0
    exp += 10 * 3.0 if 5 <= n <= 8 else 0.0
    assert d["payout"] == exp
    assert balance(c) == round(before - 30 + exp, 2)


# ---------------- Andar Bahar ----------------

def test_andarbahar_forced_and_guards(env, monkeypatch):
    c, _, _, _ = env
    assert c.post("/api/casino/andarbahar", json={"stake": 10, "bet": "andar"}).status_code == 401
    login(c, "demo", "demo123")
    assert c.post("/api/casino/andarbahar", json={"stake": 10, "bet": "side"}).status_code == 400

    def ab_deck(cards):
        monkeypatch.setattr(appmod, "_cards_new_deck",
                            lambda: [dict(x) for x in cards])

    # Middle 7: first Andar card matches -> Andar pays 1.25x, Bahar loses.
    ab_deck([card("7"), card("7", "♥")])
    d = c.post("/api/casino/andarbahar", json={"stake": 10, "bet": "andar"}).get_json()
    assert d["winner"] == "andar" and d["match_position"] == 1
    assert d["payout"] == 12.5 and balance(c) == 102.5
    ab_deck([card("7"), card("7", "♥")])
    d = c.post("/api/casino/andarbahar", json={"stake": 10, "bet": "bahar"}).get_json()
    assert d["payout"] == 0.0 and balance(c) == 92.5
    # Middle K: Andar card, Bahar card, then Andar match on card 3 -> 2x.
    ab_deck([card("K"), card("A"), card("Q", "♥"), card("K", "♦")])
    d = c.post("/api/casino/andarbahar", json={"stake": 10, "bet": "andar"}).get_json()
    assert d["winner"] == "andar" and d["match_position"] == 3
    assert d["payout"] == 20.0 and balance(c) == 102.5
    # Middle Q: Bahar matches on card 2 -> Bahar wins 2x.
    ab_deck([card("Q"), card("2"), card("Q", "♥")])
    d = c.post("/api/casino/andarbahar", json={"stake": 10, "bet": "bahar"}).get_json()
    assert d["winner"] == "bahar" and d["match_position"] == 2
    assert d["payout"] == 20.0 and balance(c) == 112.5


# ---------------- history rows ----------------

def test_batch4b_history_rows(env):
    c, _, _, _ = env
    login(c, "demo", "demo123")
    pid = my_id(c)
    plays = [
        ("/api/casino/craps", {"stake": 10, "bet": "pass"}),
        ("/api/casino/sicbo", {"stake": 10, "bet": "big"}),
        ("/api/casino/bigsix", {"stake": 10, "bet": "1"}),
        ("/api/casino/chuck", {"stake": 10, "number": 3}),
        ("/api/casino/underover", {"stake": 10, "bet": "under"}),
        ("/api/casino/miniroulette", {"bets": [{"type": "red", "amount": 10}]}),
        ("/api/casino/andarbahar", {"stake": 10, "bet": "andar"}),
    ]
    for url, body in plays:
        r = c.post(url, json=body)
        assert r.status_code == 200, (url, r.get_json())
    rows = casino_rows(c, pid)
    names = {"Craps", "Sic Bo", "Big Six", "Chuck-a-Luck",
             "Under/Over 7", "Mini Roulette", "Andar Bahar"}
    assert names <= {g["game"] for g in rows}, rows
