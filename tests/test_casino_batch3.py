"""Tests for batch-3 casino games: Roulette, Blackjack, Slots.

Random outcomes are never assumed: tests read the server's public
result (winning number, grid, settled hands) and recompute the
expected payout from it. Deterministic paths (bust, push, double,
dealer bust, blackjack 3:2, free-spin accounting) force game state by
rewriting the hand/shoe rows in the test DB, exactly as batch-2 tests
move round timestamps.
"""
import json
import sqlite3
import sys
import os

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


def sql(db_path, stmt, params=()):
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    cur = con.execute(stmt, params)
    con.commit()
    rows = cur.fetchall()
    con.close()
    return rows


def my_id(client):
    return client.get("/api/me").get_json()["user"]["id"]


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


def card(rank, suit="♠"):
    return {"rank": rank, "suit": suit}


def bj_hand(db_path, pid):
    rows = sql(db_path, "SELECT id, state FROM casino_games WHERE user_id = ?"
                        " AND game = 'Blackjack' AND status = 'open'", (pid,))
    assert len(rows) == 1, rows
    return rows[0]["id"], json.loads(rows[0]["state"])


def set_bj_state(db_path, pid, player, dealer, shoe, doubled=False, stake=10):
    gid, _ = bj_hand(db_path, pid)
    state = {"player": player, "dealer": dealer, "doubled": doubled, "stake": stake}
    sql(db_path, "UPDATE casino_games SET state = ? WHERE id = ?",
        (json.dumps(state), gid))
    # The app reshuffles any shoe under 52 cards, so pad the forced
    # draws past that line (draws pop from the front, in order).
    shoe = list(shoe) + [card("2")] * 60
    sql(db_path, "UPDATE casino_games SET state = ? WHERE user_id = ?"
                 " AND game = 'BlackjackShoe' AND status = 'open'",
        (json.dumps(shoe), pid))
    return gid


def seed_safe_shoe(db_path, pid):
    """Insert an open shoe whose first four draws (10,7,10,7) can never
    be a blackjack, so the opening deal is always an open hand. Without
    this, a randomly dealt immediate blackjack leaves no open hand for
    set_bj_state to rewrite and the test flakes."""
    shoe = [card("10"), card("7"), card("10"), card("7")] + [card("2")] * 60
    sql(db_path, "INSERT INTO casino_games (user_id, game, state, stake, status, created_at)"
                 " VALUES (?, 'BlackjackShoe', ?, 0, 'open', 'test')",
        (pid, json.dumps(shoe)))


# ---------------- Roulette ----------------

def test_roulette_math_and_guards(env):
    c, _, _, _ = env
    r = c.post("/api/casino/roulette", json={"bets": [{"type": "red", "amount": 10}]})
    assert r.status_code == 401
    login(c, "demo", "demo123")
    assert c.post("/api/casino/roulette", json={"bets": []}).status_code == 400
    assert c.post("/api/casino/roulette",
                  json={"bets": [{"type": "bogus", "amount": 10}]}).status_code == 400
    assert c.post("/api/casino/roulette",
                  json={"bets": [{"type": "straight", "value": 37, "amount": 10}]}).status_code == 400
    assert c.post("/api/casino/roulette",
                  json={"bets": [{"type": "dozen", "value": 4, "amount": 10}]}).status_code == 400
    assert c.post("/api/casino/roulette",
                  json={"bets": [{"type": "red", "amount": 0}]}).status_code == 400
    assert c.post("/api/casino/roulette",
                  json={"bets": [{"type": "red", "amount": 1000}]}).status_code == 400
    before = balance(c)
    bets = [{"type": "straight", "value": 7, "amount": 10},
            {"type": "red", "amount": 10},
            {"type": "dozen", "value": 1, "amount": 10}]
    d = c.post("/api/casino/roulette", json={"bets": bets}).get_json()
    assert d["ok"] and 0 <= d["number"] <= 36
    expected = sum(round(b["amount"] * appmod._roulette_bet_win(b, d["number"]), 2)
                   for b in bets)
    assert d["payout"] == expected
    assert d["total_stake"] == 30
    assert balance(c) == round(before - 30 + expected, 2)
    assert d["color"] == ("green" if d["number"] == 0 else
                          ("red" if d["number"] in appmod.ROULETTE_RED else "black"))


def test_roulette_admin_blocked(env):
    c, _, _, _ = env
    login(c, "admin", "admin123")
    r = c.post("/api/casino/roulette", json={"bets": [{"type": "red", "amount": 10}]})
    assert r.status_code == 403


def test_roulette_bet_table_unit():
    # Straight pays 36x total return; even-money loses on zero; columns
    # follow n % 3 (column 3 = multiples of 3).
    assert appmod._roulette_bet_win({"type": "straight", "value": 0}, 0) == 36
    assert appmod._roulette_bet_win({"type": "red"}, 0) == 0
    assert appmod._roulette_bet_win({"type": "black"}, 0) == 0
    assert appmod._roulette_bet_win({"type": "column", "value": 3}, 36) == 3
    assert appmod._roulette_bet_win({"type": "column", "value": 1}, 36) == 0
    assert appmod._roulette_bet_win({"type": "dozen", "value": 2}, 24) == 3
    assert appmod._roulette_bet_win({"type": "high"}, 19) == 2
    assert appmod._roulette_bet_win({"type": "even"}, 18) == 2
    assert appmod._roulette_bet_win({"type": "odd"}, 18) == 0


# ---------------- Blackjack ----------------

def test_blackjack_deal_hides_hole_card_and_guards(env):
    c, _, _, _ = env
    r = c.post("/api/casino/blackjack/deal", json={"stake": 10})
    assert r.status_code == 401
    login(c, "demo", "demo123")
    assert c.post("/api/casino/blackjack/deal", json={"stake": 0}).status_code == 400
    assert c.post("/api/casino/blackjack/deal", json={"stake": 10000}).status_code == 400
    d = c.post("/api/casino/blackjack/deal", json={"stake": 10}).get_json()
    if d.get("settled"):
        pytest.skip("dealt an immediate blackjack; hole-card check not applicable")
    assert d["ok"] and len(d["player"]) == 2 and len(d["dealer"]) == 1
    assert d["dealer_hidden"] is True and d["dealer_value"] is None
    assert balance(c) == 90
    assert c.post("/api/casino/blackjack/deal", json={"stake": 10}).status_code == 400


def test_blackjack_hit_bust_and_double_settle_guard(env):
    c, _, _, db_path = env
    login(c, "demo", "demo123")
    pid = my_id(c)
    seed_safe_shoe(db_path, pid)
    d = c.post("/api/casino/blackjack/deal", json={"stake": 10}).get_json()
    assert not d.get("settled")
    gid = set_bj_state(db_path, pid, [card("10"), card("6")], [card("9"), card("7")],
                       [card("K")] * 5)
    r = c.post("/api/casino/blackjack/hit", json={"game_id": gid}).get_json()
    assert r["settled"] and r["bust"] and r["payout"] == 0.0
    assert balance(c) == 90
    assert c.post("/api/casino/blackjack/hit", json={"game_id": gid}).status_code == 400
    assert c.post("/api/casino/blackjack/stand", json={"game_id": gid}).status_code == 400
    rows = casino_rows(c, pid)
    assert any(g["game"] == "Blackjack" and g["payout"] == 0 for g in rows)


def test_blackjack_push_win_dealer_bust(env):
    c, _, _, db_path = env
    login(c, "demo", "demo123")
    pid = my_id(c)
    seed_safe_shoe(db_path, pid)
    # Push: 17 vs 17, dealer stands, no draw needed.
    d = c.post("/api/casino/blackjack/deal", json={"stake": 10}).get_json()
    gid = set_bj_state(db_path, pid, [card("10"), card("7")], [card("10"), card("7")], [])
    r = c.post("/api/casino/blackjack/stand", json={"game_id": gid}).get_json()
    assert r["payout"] == 10 and "Push" in r["outcome"]
    assert balance(c) == 100
    # Player win: 19 vs dealer 16 -> dealer draws 2 -> 18, player wins 2x.
    d = c.post("/api/casino/blackjack/deal", json={"stake": 10}).get_json()
    gid = set_bj_state(db_path, pid, [card("10"), card("9")], [card("10"), card("6")],
                       [card("2")])
    r = c.post("/api/casino/blackjack/stand", json={"game_id": gid}).get_json()
    assert r["payout"] == 20 and r["dealer_value"] == 18
    assert balance(c) == 110
    # Dealer bust: 18 vs 16 -> dealer draws K -> 26 bust, player wins 2x.
    d = c.post("/api/casino/blackjack/deal", json={"stake": 10}).get_json()
    gid = set_bj_state(db_path, pid, [card("10"), card("8")], [card("10"), card("6")],
                       [card("K")])
    r = c.post("/api/casino/blackjack/stand", json={"game_id": gid}).get_json()
    assert r["payout"] == 20 and r["dealer_value"] == 26
    assert balance(c) == 120


def test_blackjack_three_two_and_double(env):
    c, _, _, db_path = env
    login(c, "demo", "demo123")
    pid = my_id(c)
    seed_safe_shoe(db_path, pid)
    # Blackjack 3:2 on the showdown path: player A+K, dealer 16 draws to 18.
    d = c.post("/api/casino/blackjack/deal", json={"stake": 10}).get_json()
    gid = set_bj_state(db_path, pid, [card("A"), card("K")], [card("9"), card("7")],
                       [card("2")])
    r = c.post("/api/casino/blackjack/stand", json={"game_id": gid}).get_json()
    assert r["payout"] == 25.0
    assert balance(c) == 115
    # Double: 11 doubles, draws 10 -> 21, dealer 16 draws 2 -> 18, win
    # pays 2x the doubled stake (40 total return on 20 staked).
    d = c.post("/api/casino/blackjack/deal", json={"stake": 10}).get_json()
    gid = set_bj_state(db_path, pid, [card("5"), card("6")], [card("10"), card("6")],
                       [card("10"), card("2")])
    r = c.post("/api/casino/blackjack/double", json={"game_id": gid}).get_json()
    assert r["settled"] and r["doubled"] and r["payout"] == 40
    assert balance(c) == 135  # 115 -10 deal -10 double +40
    # Double only on the first two cards.
    d = c.post("/api/casino/blackjack/deal", json={"stake": 10}).get_json()
    gid = set_bj_state(db_path, pid, [card("5"), card("6")], [card("10"), card("6")],
                       [card("2"), card("2")])
    c.post("/api/casino/blackjack/hit", json={"game_id": gid})
    assert c.post("/api/casino/blackjack/double", json={"game_id": gid}).status_code == 400


def test_blackjack_double_needs_funds_and_ownership(env):
    c, c2, _, db_path = env
    login(c, "demo", "demo123")
    pid = my_id(c)
    d = c.post("/api/casino/blackjack/deal", json={"stake": 60}).get_json()
    # Available is now 40; doubling needs 60 more.
    assert c.post("/api/casino/blackjack/double",
                  json={"game_id": d["game_id"]}).status_code == 400
    # Another player cannot touch this hand.
    login(c2, "admin", "admin123")
    assert c2.post("/api/casino/blackjack/hit",
                   json={"game_id": d["game_id"]}).status_code in (403, 404)


def test_blackjack_value_unit():
    assert appmod._bj_value([card("A"), card("K")]) == (21, True)
    assert appmod._bj_value([card("A"), card("6")]) == (17, True)
    assert appmod._bj_value([card("A"), card("K"), card("5")]) == (16, False)
    assert appmod._bj_value([card("10"), card("6")]) == (16, False)
    assert appmod._bj_is_blackjack([card("A"), card("Q")])
    assert not appmod._bj_is_blackjack([card("A"), card("Q"), card("2")])


# ---------------- Slots ----------------

def test_slots_spin_math_and_guards(env):
    c, _, _, _ = env
    r = c.post("/api/casino/slots/spin", json={"stake": 10})
    assert r.status_code == 401
    login(c, "demo", "demo123")
    assert c.post("/api/casino/slots/spin", json={"stake": 0}).status_code == 400
    assert c.post("/api/casino/slots/spin", json={"stake": 10000}).status_code == 400
    before = balance(c)
    d = c.post("/api/casino/slots/spin", json={"stake": 10}).get_json()
    assert d["ok"] and len(d["grid"]) == 5 and all(len(r) == 3 for r in d["grid"])
    wins, sc, sc_pay, expected = appmod._slots_payouts(d["grid"], 10)
    assert d["line_wins"] == wins and d["scatters"] == sc
    assert d["scatter_payout"] == sc_pay and d["payout"] == expected
    assert d["free_spins_triggered"] == (10 if sc >= 3 else 0)
    assert balance(c) == round(before - 10 + expected, 2)


def test_slots_evaluator_unit():
    # Reel-major grids: grid[col][row]. Middle row 9/9/9 wins line 0 only.
    grid = [["J", "9", "Q"], ["K", "9", "A"], ["CH", "9", "LE"],
            ["BE", "A", "DI"], ["SEVEN", "BE", "Q"]]
    wins, sc = appmod._slots_evaluate(grid)
    assert wins == [{"line": 0, "symbol": "9", "count": 3}] and sc == 0
    grid2 = [["SC", "9", "9"], ["9", "SC", "9"], ["9", "9", "SC"],
             ["A", "CH", "LE"], ["BE", "DI", "SEVEN"]]
    wins2, sc2 = appmod._slots_evaluate(grid2)
    assert sc2 == 3
    assert not any(w["symbol"] == "SC" for w in wins2)  # scatters never line-win
    grid3 = [["9", "10", "J"], ["Q", "K", "A"], ["CH", "LE", "BE"],
             ["DI", "SEVEN", "9"], ["10", "J", "Q"]]
    wins3, sc3 = appmod._slots_evaluate(grid3)
    assert wins3 == [] and sc3 == 0


def test_slots_free_spin_accounting(env):
    c, _, _, db_path = env
    login(c, "demo", "demo123")
    pid = my_id(c)
    assert c.post("/api/casino/slots/free-spin", json={}).status_code == 400
    sql(db_path, "INSERT INTO casino_games (user_id, game, state, stake, status, created_at)"
                 " VALUES (?, 'SlotsFree', ?, 0, 'open', 'now')",
        (pid, json.dumps({"remaining": 2, "total_won": 0.0, "base_stake": 10})))
    before = balance(c)
    d1 = c.post("/api/casino/slots/free-spin", json={}).get_json()
    assert d1["ok"] and d1["free_spins_remaining"] == 1
    assert balance(c) == round(before + d1["payout"], 2)
    d2 = c.post("/api/casino/slots/free-spin", json={}).get_json()
    assert d2["ok"] and d2["free_spins_remaining"] == 0
    assert d2["free_spins_total_won"] == round(d1["payout"] + d2["payout"], 2)
    assert c.post("/api/casino/slots/free-spin", json={}).status_code == 400


def test_slots_admin_blocked(env):
    c, _, _, _ = env
    login(c, "admin", "admin123")
    assert c.post("/api/casino/slots/spin", json={"stake": 10}).status_code == 403
    assert c.post("/api/casino/slots/free-spin", json={}).status_code == 403
