"""Tests for Dino Run: single settled round, server-drawn distance.

Random outcomes are never assumed: tests read the server's public
result (drawn distance, drawn band, win flag) and recompute the
expected payout from it, exactly as batch-3 tests recompute roulette
and slots payouts from the returned result.
"""
import sqlite3
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import app as appmod
from app import create_app
from csrf_helpers import wrap


BANDS = {
    "short": (0, 99, 1.94),
    "steady": (100, 249, 3.23),
    "long": (250, 499, 6.47),
    "marathon": (500, 999, 19.40),
}


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


def play(client, stake, band):
    return client.post("/api/casino/dino", json={"stake": stake, "band": band})


def test_dino_guards(env):
    admin_c, player_c, anon_c, db_path = env
    pid = make_player(admin_c, player_c, db_path, "dinog", 100)
    # Unauthenticated -> 401.
    r = anon_c.post("/api/casino/dino", json={"stake": 10, "band": "short"})
    assert r.status_code == 401, r.get_json()
    # Admin accounts cannot play -> 403.
    login(admin_c, "admin", "admin123")
    r = admin_c.post("/api/casino/dino", json={"stake": 10, "band": "short"})
    assert r.status_code == 403, r.get_json()
    admin_c.post("/api/auth/logout")
    # Bad band -> 400, stake untouched.
    assert balance(player_c) == 100
    r = play(player_c, 10, "moon")
    assert r.status_code == 400, r.get_json()
    r = play(player_c, 10, None)
    assert r.status_code == 400, r.get_json()
    # Non-positive stake -> 400.
    assert play(player_c, 0, "short").status_code == 400
    assert play(player_c, -5, "short").status_code == 400
    # Stake above available balance -> 400, balance untouched.
    assert play(player_c, 101, "short").status_code == 400
    assert balance(player_c) == 100


def test_dino_payout_recompute(env):
    admin_c, player_c, anon_c, db_path = env
    pid = make_player(admin_c, player_c, db_path, "dinop", 1000)
    bal = 1000.0
    for band in ("short", "steady", "long", "marathon"):
        for _ in range(8):
            stake = 10.0
            r = play(player_c, stake, band)
            assert r.status_code == 200, r.get_json()
            d = r.get_json()
            lo, hi, _drawn_mult = BANDS[d["band"]]
            bet_mult = BANDS[band][2]
            # Drawn distance must sit inside its reported band.
            assert lo <= d["distance"] <= hi, d
            assert d["bet_band"] == band
            assert d["multiplier"] == bet_mult
            assert d["win"] == (d["band"] == band)
            expected = round(stake * bet_mult, 2) if d["win"] else 0.0
            assert d["payout"] == expected, d
            bal = round(bal - stake + expected, 2)
            assert d["balance"] == bal, d
            assert balance(player_c) == bal
    # History rows exist for this game with matching stake/payout.
    rows = casino_rows(admin_c, pid)
    dino = [row for row in rows if row["game"] == "Dino Run"]
    assert len(dino) == 32, len(dino)
    assert all(row["stake"] == 10.0 for row in dino)
    # Ledger: statement CASINO rows agree with the game history.
    login(player_c, "dinop", "secret12")
    st = player_c.get("/api/statement").get_json()
    cas = [row for row in st if row["kind"] == "CASINO"]
    assert len(cas) >= 32, len(cas)


def test_dino_loss_and_win_balance_steps(env):
    admin_c, player_c, anon_c, db_path = env
    pid = make_player(admin_c, player_c, db_path, "dinob", 100)
    # Play until we have seen at least one win and one loss across any
    # band choice; each step must move the balance by exactly the
    # settled amount (bounded loop, outcome is random).
    seen_win = seen_loss = False
    for _ in range(200):
        before = balance(player_c)
        d = play(player_c, 5, "short").get_json()
        assert d["ok"]
        after = balance(player_c)
        assert after == round(before - 5 + d["payout"], 2), d
        if d["win"]:
            seen_win = True
            assert d["payout"] == round(5 * 1.94, 2)
        else:
            seen_loss = True
            assert d["payout"] == 0.0
        if seen_win and seen_loss:
            break
    assert seen_win and seen_loss
