"""Tests for batch-4a casino games: Baccarat, Video Poker, Three Card
Poker, Caribbean Stud, Let It Ride, Dragon Tiger, Casino War, Red Dog.

Random outcomes are never assumed: tests recompute the expected
payout from the server's public result, force round state by
rewriting the open row (batch-3 technique), or monkeypatch the deck
factory so the deal itself is deterministic. All eight games are
original implementations of their published rules.
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


def card(rank, suit="♠"):
    return {"rank": rank, "suit": suit}


def deck_factory(monkeypatch, decks):
    """Make _cards_new_deck return the given decks in order, one fresh
    copy per call (deals pop from the front)."""
    queue = [[dict(c) for c in d] for d in decks]

    def _factory():
        assert queue, "deck factory exhausted"
        return queue.pop(0)

    monkeypatch.setattr(appmod, "_cards_new_deck", _factory)


def open_row(db_path, pid, game):
    rows = sql(db_path, "SELECT id, state FROM casino_games WHERE user_id = ?"
                        " AND game = ? AND status = 'open'", (pid, game))
    assert len(rows) == 1, rows
    return rows[0]["id"], json.loads(rows[0]["state"])


def set_state(db_path, gid, state):
    sql(db_path, "UPDATE casino_games SET state = ? WHERE id = ?",
        (json.dumps(state), gid))


# ---------------- unit: poker ranks & baccarat tableau ----------------

def test_poker_rank_unit():
    r = appmod._poker_rank
    assert r([card("A"), card("K"), card("Q"), card("J"), card("10")])[0] == 8  # royal = SF
    assert r([card("9"), card("8"), card("7"), card("6"), card("5")])[0] == 8
    assert r([card("A"), card("2", "♥"), card("3", "♦"), card("4", "♣"), card("5")])[0] == 4  # wheel straight
    assert r([card("A"), card("A"), card("A"), card("A"), card("2")])[0] == 7
    assert r([card("K"), card("K"), card("K"), card("2"), card("2")])[0] == 6
    assert r([card("A"), card("K", "♥"), card("Q", "♦"), card("J", "♣"), card("9")])[0] == 0
    assert r([card("Q", "♠"), card("K", "♠"), card("A", "♠")])[0] == 5  # 3-card SF
    assert r([card("7"), card("7"), card("7")])[0] == 4
    assert r([card("A"), card("2", "♥"), card("3", "♦")])[0] == 3  # 3-card wheel
    assert r([card("K", "♠"), card("K", "♥"), card("2")])[0] == 1
    # Tiebreaks: pair of aces beats pair of kings; trips beat two pair.
    assert r([card("A"), card("A", "♥"), card("5", "♦"), card("4", "♣"), card("3")]) > \
        r([card("K"), card("K", "♥"), card("Q", "♦"), card("J", "♣"), card("9")])
    assert r([card("9"), card("9", "♥"), card("9", "♦"), card("2", "♣"), card("3")]) > \
        r([card("A"), card("A", "♥"), card("K", "♦"), card("K", "♣"), card("Q")])


def test_baccarat_tableau_unit():
    # Natural: no third cards.
    p, b = appmod._bac_play([card("A"), card("8"), card("K"), card("9")])
    assert len(p) == 2 and len(b) == 2
    # Player 5 draws; banker 2 always draws.
    p, b = appmod._bac_play([card("2"), card("3"), card("10"), card("2"), card("8"), card("5")])
    assert [c["rank"] for c in p] == ["2", "3", "8"]
    assert [c["rank"] for c in b] == ["10", "2", "5"]
    # Player stands on 7; banker 3 draws.
    p, b = appmod._bac_play([card("10"), card("7"), card("10"), card("3"), card("5")])
    assert len(p) == 2 and len(b) == 3
    # Banker 3 stands against a player third card of 8.
    p, b = appmod._bac_play([card("2"), card("3"), card("10"), card("3"), card("8")])
    assert len(p) == 3 and len(b) == 2


# ---------------- Baccarat ----------------

def test_baccarat_math_and_guards(env):
    c, _, _, _ = env
    r = c.post("/api/casino/baccarat", json={"stake": 10, "bet": "player"})
    assert r.status_code == 401
    login(c, "demo", "demo123")
    assert c.post("/api/casino/baccarat", json={"stake": 10, "bet": "bogus"}).status_code == 400
    assert c.post("/api/casino/baccarat", json={"stake": 10000, "bet": "player"}).status_code == 400
    before = balance(c)
    d = c.post("/api/casino/baccarat", json={"stake": 10, "bet": "player"}).get_json()
    assert d["ok"]
    assert d["player_value"] == appmod._bac_value(d["player"])
    assert d["banker_value"] == appmod._bac_value(d["banker"])
    winner = "player" if d["player_value"] > d["banker_value"] else \
        ("banker" if d["banker_value"] > d["player_value"] else "tie")
    assert d["winner"] == winner
    expected = {"player": 20.0, "banker": 19.5, "tie": 100.0}["player"] \
        if winner == "player" else (10.0 if winner == "tie" else 0.0)
    assert d["payout"] == expected
    assert balance(c) == round(before - 10 + expected, 2)


def test_baccarat_history_row(env):
    c, _, _, _ = env
    login(c, "demo", "demo123")
    pid = my_id(c)
    d = c.post("/api/casino/baccarat", json={"stake": 10, "bet": "banker"}).get_json()
    rows = casino_rows(c, pid)
    assert any(g["game"] == "Baccarat" and g["payout"] == d["payout"] for g in rows)


# ---------------- Video Poker ----------------

def test_videopoker_deal_draw_guards(env):
    c, c2, _, db_path = env
    r = c.post("/api/casino/videopoker/deal", json={"stake": 10})
    assert r.status_code == 401
    login(c, "demo", "demo123")
    pid = my_id(c)
    assert c.post("/api/casino/videopoker/deal", json={"stake": 10000}).status_code == 400
    d = c.post("/api/casino/videopoker/deal", json={"stake": 10}).get_json()
    assert d["ok"] and len(d["hand"]) == 5 and not d["settled"]
    assert balance(c) == 90
    assert c.post("/api/casino/videopoker/deal", json={"stake": 10}).status_code == 400
    # Another player cannot touch this hand.
    login(c2, "admin", "admin123")
    assert c2.post("/api/casino/videopoker/draw",
                   json={"game_id": d["game_id"], "holds": []}).status_code in (403, 404)
    # Bad holds rejected; forced quads pay 25x.
    assert c.post("/api/casino/videopoker/draw",
                  json={"game_id": d["game_id"], "holds": [0, 0]}).status_code == 400
    gid, state = open_row(db_path, pid, "VideoPoker")
    state["hand"] = [card("A"), card("A", "♥"), card("A", "♦"), card("A", "♣"), card("2")]
    state["deck"] = [card("3")] * 50
    set_state(db_path, gid, state)
    r = c.post("/api/casino/videopoker/draw",
               json={"game_id": gid, "holds": [0, 1, 2, 3]}).get_json()
    assert r["category"] == "Four of a kind" and r["payout"] == 250
    assert balance(c) == 90 + 250
    assert c.post("/api/casino/videopoker/draw",
                  json={"game_id": gid, "holds": []}).status_code == 400


def test_videopoker_royal_and_low_pair(env):
    c, _, _, db_path = env
    login(c, "demo", "demo123")
    pid = my_id(c)
    d = c.post("/api/casino/videopoker/deal", json={"stake": 10}).get_json()
    gid, state = open_row(db_path, pid, "VideoPoker")
    state["hand"] = [card("2")] * 5
    state["deck"] = [card("10", "♠"), card("J", "♠"), card("Q", "♠"),
                     card("K", "♠"), card("A", "♠")] + [card("3")] * 45
    set_state(db_path, gid, state)
    r = c.post("/api/casino/videopoker/draw",
               json={"game_id": gid, "holds": []}).get_json()
    assert r["category"] == "Royal flush" and r["payout"] == 2500
    # Low pair pays nothing.
    d = c.post("/api/casino/videopoker/deal", json={"stake": 10}).get_json()
    gid, state = open_row(db_path, pid, "VideoPoker")
    state["hand"] = [card("9"), card("9", "♥"), card("2"), card("3"), card("4")]
    state["deck"] = [card("5"), card("6"), card("7")] + [card("8")] * 47
    set_state(db_path, gid, state)
    r = c.post("/api/casino/videopoker/draw",
               json={"game_id": gid, "holds": [0, 1]}).get_json()
    assert r["category"] == "No win" and r["payout"] == 0


# ---------------- Three Card Poker ----------------

def test_threecard_deal_play_fold(env):
    c, _, _, db_path = env
    r = c.post("/api/casino/threecard/deal", json={"stake": 10})
    assert r.status_code == 401
    login(c, "demo", "demo123")
    pid = my_id(c)
    d = c.post("/api/casino/threecard/deal", json={"stake": 10}).get_json()
    assert d["ok"] and len(d["player"]) == 3 and d["dealer"] == [] and d["dealer_hidden"] is True
    assert balance(c) == 90
    assert c.post("/api/casino/threecard/deal", json={"stake": 10}).status_code == 400
    # Force: player straight flush vs dealer 5-high (no qualify).
    gid, state = open_row(db_path, pid, "ThreeCard")
    state["player"] = [card("Q", "♠"), card("K", "♠"), card("A", "♠")]
    state["dealer"] = [card("2"), card("3", "♥"), card("5", "♦")]
    set_state(db_path, gid, state)
    r = c.post("/api/casino/threecard/play", json={"game_id": gid}).get_json()
    assert r["qualifies"] is False and r["ante_bonus"] == 50
    # Ante wins 2x, play pushes, bonus 5x ante: 20 + 10 + 50 = 80.
    assert r["payout"] == 80
    assert balance(c) == 90 - 10 + 80
    # Fold loses only the ante.
    d = c.post("/api/casino/threecard/deal", json={"stake": 10}).get_json()
    r = c.post("/api/casino/threecard/fold", json={"game_id": d["game_id"]}).get_json()
    assert r["payout"] == 0 and len(r["dealer"]) == 3
    assert balance(c) == 160 - 10


def test_threecard_qualify_and_loss(env):
    c, _, _, db_path = env
    login(c, "demo", "demo123")
    pid = my_id(c)
    # Dealer queen-high qualifies; player high-card loses.
    d = c.post("/api/casino/threecard/deal", json={"stake": 10}).get_json()
    gid, state = open_row(db_path, pid, "ThreeCard")
    state["player"] = [card("2"), card("5", "♥"), card("9", "♦")]
    state["dealer"] = [card("Q"), card("5", "♥"), card("2", "♥")]
    set_state(db_path, gid, state)
    r = c.post("/api/casino/threecard/play", json={"game_id": gid}).get_json()
    assert r["qualifies"] is True and r["payout"] == 0
    # Dealer jack-high does not qualify.
    d = c.post("/api/casino/threecard/deal", json={"stake": 10}).get_json()
    gid, state = open_row(db_path, pid, "ThreeCard")
    state["player"] = [card("2"), card("5", "♥"), card("9", "♦")]
    state["dealer"] = [card("J"), card("5", "♥"), card("2", "♥")]
    set_state(db_path, gid, state)
    r = c.post("/api/casino/threecard/play", json={"game_id": gid}).get_json()
    assert r["qualifies"] is False and r["payout"] == 30  # ante 2x + play push


# ---------------- Caribbean Stud ----------------

def test_caribbean_deal_call_fold(env):
    c, _, _, db_path = env
    login(c, "demo", "demo123")
    pid = my_id(c)
    # Deal needs 3x ante available.
    assert c.post("/api/casino/caribbean/deal", json={"stake": 40}).status_code == 400
    d = c.post("/api/casino/caribbean/deal", json={"stake": 10}).get_json()
    assert d["ok"] and len(d["player"]) == 5 and d["call"] == 20
    assert balance(c) == 90
    assert c.post("/api/casino/caribbean/deal", json={"stake": 10}).status_code == 400
    # Force: player pair of aces vs dealer A-K high (qualifies) → win.
    gid, state = open_row(db_path, pid, "Caribbean")
    state["player"] = [card("A"), card("A", "♥"), card("2"), card("3"), card("4")]
    state["dealer"] = [card("A", "♦"), card("K"), card("2", "♥"), card("3", "♥"), card("5")]
    set_state(db_path, gid, state)
    r = c.post("/api/casino/caribbean/call", json={"game_id": gid}).get_json()
    assert r["qualifies"] is True
    # Ante 2x (20) + call 2x (40) = 60.
    assert r["payout"] == 60
    assert balance(c) == 90 - 20 + 60
    # Fold loses only the ante.
    d = c.post("/api/casino/caribbean/deal", json={"stake": 10}).get_json()
    r = c.post("/api/casino/caribbean/fold", json={"game_id": d["game_id"]}).get_json()
    assert r["payout"] == 0 and len(r["dealer"]) == 5
    assert balance(c) == 130 - 10


def test_caribbean_no_qualify(env):
    c, _, _, db_path = env
    login(c, "demo", "demo123")
    pid = my_id(c)
    d = c.post("/api/casino/caribbean/deal", json={"stake": 10}).get_json()
    gid, state = open_row(db_path, pid, "Caribbean")
    state["player"] = [card("2"), card("3"), card("4"), card("5"), card("7")]
    state["dealer"] = [card("2", "♥"), card("3", "♠"), card("4", "♦"), card("5", "♣"), card("7", "♥")]
    set_state(db_path, gid, state)
    r = c.post("/api/casino/caribbean/call", json={"game_id": gid}).get_json()
    assert r["qualifies"] is False
    # Ante 2x (20) + call pushed (20) = 40.
    assert r["payout"] == 40


# ---------------- Let It Ride ----------------

def test_letitride_ride_pull_and_guards(env):
    c, _, _, db_path = env
    login(c, "demo", "demo123")
    pid = my_id(c)
    assert c.post("/api/casino/letitride/deal", json={"stake": 10}).status_code == 400
    d = c.post("/api/casino/letitride/deal", json={"stake": 9}).get_json()
    assert d["ok"] and d["bet"] == 3 and len(d["player"]) == 3
    assert balance(c) == 91
    # Force trips on the board; ride both bets: 3 bets x3 x(1+3) = 36.
    gid, state = open_row(db_path, pid, "LetItRide")
    state["player"] = [card("10"), card("10", "♥"), card("10", "♦")]
    state["deck"] = [card("2", "♣"), card("3", "♣")] + [card("4")] * 45
    set_state(db_path, gid, state)
    r = c.post("/api/casino/letitride/action", json={"game_id": gid, "action": "ride"}).get_json()
    assert not r["settled"] and r["stage"] == 1 and len(r["community"]) == 1
    assert c.post("/api/casino/letitride/action", json={"game_id": gid, "action": "bogus"}).status_code == 400
    r = c.post("/api/casino/letitride/action", json={"game_id": gid, "action": "ride"}).get_json()
    assert r["settled"] and r["category"] == "Three of a kind" and r["payout"] == 36
    assert balance(c) == 91 + 36
    # Pull the first bet: 2 bets x3 x4 + 3 back = 27.
    d = c.post("/api/casino/letitride/deal", json={"stake": 9}).get_json()
    gid, state = open_row(db_path, pid, "LetItRide")
    state["player"] = [card("10"), card("10", "♥"), card("10", "♦")]
    state["deck"] = [card("2", "♣"), card("3", "♣")] + [card("4")] * 45
    set_state(db_path, gid, state)
    c.post("/api/casino/letitride/action", json={"game_id": gid, "action": "pull"})
    r = c.post("/api/casino/letitride/action", json={"game_id": gid, "action": "ride"}).get_json()
    assert r["payout"] == 27
    assert c.post("/api/casino/letitride/action", json={"game_id": gid, "action": "ride"}).status_code == 400


# ---------------- Dragon Tiger ----------------

def test_dragontiger_math_and_guards(env):
    c, _, _, _ = env
    r = c.post("/api/casino/dragontiger", json={"stake": 10, "bet": "dragon"})
    assert r.status_code == 401
    login(c, "demo", "demo123")
    assert c.post("/api/casino/dragontiger", json={"stake": 10, "bet": "bogus"}).status_code == 400
    before = balance(c)
    d = c.post("/api/casino/dragontiger", json={"stake": 10, "bet": "dragon"}).get_json()
    dv = 1 if d["dragon"]["rank"] == "A" else appmod._poker_val(d["dragon"])
    tv = 1 if d["tiger"]["rank"] == "A" else appmod._poker_val(d["tiger"])
    winner = "dragon" if dv > tv else ("tiger" if tv > dv else "tie")
    assert d["winner"] == winner
    expected = 20.0 if winner == "dragon" else (5.0 if winner == "tie" else 0.0)
    assert d["payout"] == expected
    assert balance(c) == round(before - 10 + expected, 2)


# ---------------- Casino War ----------------

def test_war_tie_surrender_and_go(env, monkeypatch):
    c, _, _, _ = env
    r = c.post("/api/casino/war/deal", json={"stake": 10})
    assert r.status_code == 401
    login(c, "demo", "demo123")
    # Forced tie: K vs K; burn 2,3,4; war A vs 2 → war won: 3x stake.
    deck_factory(monkeypatch, [
        [card("K"), card("K", "♥"), card("2", "♣"), card("3", "♣"), card("4", "♣"),
         card("A"), card("2")] + [card("5")] * 45])
    d = c.post("/api/casino/war/deal", json={"stake": 10}).get_json()
    assert d["tie"] is True and not d["settled"] and balance(c) == 90
    r = c.post("/api/casino/war/go", json={"game_id": d["game_id"]}).get_json()
    assert r["payout"] == 30
    assert balance(c) == 90 - 10 + 30
    # Forced tie again; surrender returns half.
    deck_factory(monkeypatch, [
        [card("Q"), card("Q", "♥")] + [card("5")] * 50])
    d = c.post("/api/casino/war/deal", json={"stake": 10}).get_json()
    assert d["tie"] is True
    r = c.post("/api/casino/war/surrender", json={"game_id": d["game_id"]}).get_json()
    assert r["payout"] == 5
    assert balance(c) == 110 - 10 + 5
    # Forced tie; war loss pays nothing.
    deck_factory(monkeypatch, [
        [card("J"), card("J", "♥"), card("2", "♣"), card("3", "♣"), card("4", "♣"),
         card("2"), card("A")] + [card("5")] * 45])
    d = c.post("/api/casino/war/deal", json={"stake": 10}).get_json()
    r = c.post("/api/casino/war/go", json={"game_id": d["game_id"]}).get_json()
    assert r["payout"] == 0
    # War without funds is refused.
    deck_factory(monkeypatch, [
        [card("9"), card("9", "♥")] + [card("5")] * 50])
    d = c.post("/api/casino/war/deal", json={"stake": 60}).get_json()
    assert d["tie"] is True
    assert c.post("/api/casino/war/go", json={"game_id": d["game_id"]}).status_code == 400


def test_war_straight_win_and_war_tie(env, monkeypatch):
    c, _, _, _ = env
    login(c, "demo", "demo123")
    deck_factory(monkeypatch, [[card("A"), card("K")] + [card("5")] * 50])
    d = c.post("/api/casino/war/deal", json={"stake": 10}).get_json()
    assert d["tie"] is False and d["payout"] == 20
    # War tie also pays the war bet: 3x stake.
    deck_factory(monkeypatch, [
        [card("8"), card("8", "♥"), card("2", "♣"), card("3", "♣"), card("4", "♣"),
         card("7"), card("7", "♥")] + [card("5")] * 45])
    d = c.post("/api/casino/war/deal", json={"stake": 10}).get_json()
    r = c.post("/api/casino/war/go", json={"game_id": d["game_id"]}).get_json()
    assert r["payout"] == 30


# ---------------- Red Dog ----------------

def test_reddog_spreads_raise_call(env, monkeypatch):
    c, _, _, _ = env
    r = c.post("/api/casino/reddog/deal", json={"stake": 10})
    assert r.status_code == 401
    login(c, "demo", "demo123")
    # Spread 3 (5,9), third 7 inside → call pays 3x.
    deck_factory(monkeypatch, [[card("5"), card("9"), card("7")] + [card("2")] * 49])
    d = c.post("/api/casino/reddog/deal", json={"stake": 10}).get_json()
    assert d["spread"] == 3 and not d["settled"]
    r = c.post("/api/casino/reddog/call", json={"game_id": d["game_id"]}).get_json()
    assert r["payout"] == 30
    assert balance(c) == 90 + 30
    # Same spread, raise doubles the stake → 6x.
    deck_factory(monkeypatch, [[card("5"), card("9"), card("7")] + [card("2")] * 49])
    d = c.post("/api/casino/reddog/deal", json={"stake": 10}).get_json()
    r = c.post("/api/casino/reddog/raise", json={"game_id": d["game_id"]}).get_json()
    assert r["payout"] == 60
    assert balance(c) == 120 - 20 + 60
    # Third card matching a spread card pushes.
    deck_factory(monkeypatch, [[card("5"), card("9"), card("5", "♥")] + [card("2")] * 49])
    d = c.post("/api/casino/reddog/deal", json={"stake": 10}).get_json()
    r = c.post("/api/casino/reddog/call", json={"game_id": d["game_id"]}).get_json()
    assert r["payout"] == 10
    # Third card outside loses.
    deck_factory(monkeypatch, [[card("5"), card("9"), card("2")] + [card("3")] * 49])
    d = c.post("/api/casino/reddog/deal", json={"stake": 10}).get_json()
    r = c.post("/api/casino/reddog/call", json={"game_id": d["game_id"]}).get_json()
    assert r["payout"] == 0
    # Raise without funds is refused (balance 150, deal 80 leaves 70 < 80).
    deck_factory(monkeypatch, [[card("5"), card("9"), card("7")] + [card("2")] * 49])
    d = c.post("/api/casino/reddog/deal", json={"stake": 80}).get_json()
    assert c.post("/api/casino/reddog/raise", json={"game_id": d["game_id"]}).status_code == 400


def test_reddog_pair_and_consecutive(env, monkeypatch):
    c, _, _, _ = env
    login(c, "demo", "demo123")
    # Pair + matching third → 11x.
    deck_factory(monkeypatch, [[card("K"), card("K", "♥"), card("K", "♦")] + [card("2")] * 49])
    d = c.post("/api/casino/reddog/deal", json={"stake": 10}).get_json()
    assert d["settled"] is True and d["pair"] is True and d["payout"] == 110
    # Pair + missed third → push.
    deck_factory(monkeypatch, [[card("K"), card("K", "♥"), card("2")] + [card("3")] * 49])
    d = c.post("/api/casino/reddog/deal", json={"stake": 10}).get_json()
    assert d["payout"] == 10
    # Consecutive ranks → push.
    deck_factory(monkeypatch, [[card("5"), card("6")] + [card("2")] * 50])
    d = c.post("/api/casino/reddog/deal", json={"stake": 10}).get_json()
    assert d["settled"] is True and d["payout"] == 10


# ---------------- regression: existing games untouched ----------------

def test_existing_games_still_work(env):
    c, _, _, _ = env
    login(c, "demo", "demo123")
    before = balance(c)
    d = c.post("/api/casino/limbo", json={"stake": 10, "target": 2}).get_json()
    assert d["ok"] and balance(c) == round(before - 10 + d["payout"], 2)
    assert c.get("/").status_code == 200
