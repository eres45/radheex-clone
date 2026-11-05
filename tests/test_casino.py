"""Tests for batch-1 casino games: Limbo, Plinko, Keno, Mines, Dice.

Outcomes are server-side random, so win/lose paths are reached by
looping (a 1.01x Limbo target wins ~97% of rounds; a 100x target wins
~1%): 30 attempts make a missed path astronomically unlikely, and
every assertion checks exact wallet math, not luck.
"""
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from app import create_app
from csrf_helpers import wrap


@pytest.fixture
def client(tmp_path):
    app = create_app({"DATABASE": str(tmp_path / "test.db"), "TESTING": True})
    with app.test_client() as c:
        yield wrap(c)


def login_demo(client):
    r = client.post("/api/auth/login", json={"username": "demo", "password": "demo123"})
    assert r.status_code == 200, r.get_json()
    return r.get_json()


def balance(client):
    return client.get("/api/me").get_json()["user"]["balance"]


def casino_rows(client):
    # Admin activity view lists completed casino rounds for the player.
    pid = client.get("/api/me").get_json()["user"]["id"]
    client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    det = client.get(f"/api/admin/players/{pid}").get_json()
    assert "casino" in det, det
    client.post("/api/auth/logout")
    login_demo(client)
    return det["casino"]


def test_limbo_win_and_lose_wallet_math(client):
    login_demo(client)
    won = lost = None
    for _ in range(30):
        r = client.post("/api/casino/limbo", json={"stake": 10, "target": 1.01})
        assert r.status_code == 200, r.get_json()
        d = r.get_json()
        if d["win"] and won is None:
            won = d
            assert d["payout"] == round(10 * 1.01, 2) == 10.10
            assert d["crash_point"] >= 1.01
        if not d["win"] and lost is None:
            lost = d
        if won and lost:
            break
    # A 100x target loses ~99% of rounds; loop until a loss is seen.
    for _ in range(30):
        r = client.post("/api/casino/limbo", json={"stake": 5, "target": 100})
        d = r.get_json()
        if not d["win"]:
            lost100 = d
            assert lost100["payout"] == 0.0
            break
    else:
        pytest.fail("no Limbo loss in 30 rounds at 100x")
    assert won is not None, "no Limbo win in 30 rounds at 1.01x"
    # Exact balance math on a single round, whatever its outcome.
    before = balance(client)
    d = client.post("/api/casino/limbo", json={"stake": 7, "target": 2}).get_json()
    assert d["payout"] == (round(7 * 2, 2) if d["win"] else 0.0)
    assert balance(client) == round(before - 7 + d["payout"], 2)


def test_limbo_guards(client):
    r = client.post("/api/casino/limbo", json={"stake": 10, "target": 2})
    assert r.status_code == 401
    login_demo(client)
    assert client.post("/api/casino/limbo", json={"stake": 0, "target": 2}).status_code == 400
    assert client.post("/api/casino/limbo", json={"stake": 101, "target": 2}).status_code == 400
    assert client.post("/api/casino/limbo", json={"stake": 10, "target": 1.0}).status_code == 400
    assert client.post("/api/casino/limbo", json={"stake": 10, "target": 101}).status_code == 400
    assert client.post("/api/casino/limbo", json={"stake": 10}).status_code == 400


def test_plinko_path_bin_payout_math(client):
    login_demo(client)
    before = balance(client)
    r = client.post("/api/casino/plinko", json={"stake": 10, "risk": "medium", "rows": 8})
    assert r.status_code == 200, r.get_json()
    d = r.get_json()
    assert len(d["path"]) == 8 and all(p in (0, 1) for p in d["path"])
    assert d["bin"] == sum(d["path"])
    assert d["payout"] == round(10 * d["multiplier"], 2)
    assert balance(client) == round(before - 10 + d["payout"], 2)
    rows = casino_rows(client)
    assert any(g["game"] == "Plinko" and g["stake"] == 10 for g in rows)


def test_plinko_guards(client):
    login_demo(client)
    assert client.post("/api/casino/plinko", json={"stake": 10, "risk": "wild", "rows": 8}).status_code == 400
    assert client.post("/api/casino/plinko", json={"stake": 10, "risk": "low", "rows": 10}).status_code == 400
    assert client.post("/api/casino/plinko", json={"stake": 10, "risk": "low", "rows": 8}).status_code == 200
    assert client.post("/api/casino/plinko", json={"stake": 10, "risk": "high", "rows": 16}).status_code == 200
    assert client.post("/api/casino/plinko", json={"stake": 5000, "risk": "low", "rows": 8}).status_code == 400


def test_keno_draw_hits_payout_math(client):
    login_demo(client)
    before = balance(client)
    r = client.post("/api/casino/keno", json={"stake": 10, "picks": [3, 17, 42, 71]})
    assert r.status_code == 200, r.get_json()
    d = r.get_json()
    assert len(d["draw"]) == 20 and len(set(d["draw"])) == 20
    assert all(1 <= n <= 80 for n in d["draw"])
    assert d["hits"] == len(set([3, 17, 42, 71]) & set(d["draw"]))
    assert d["payout"] == round(10 * d["multiplier"], 2)
    assert balance(client) == round(before - 10 + d["payout"], 2)


def test_keno_guards(client):
    login_demo(client)
    assert client.post("/api/casino/keno", json={"stake": 10, "picks": []}).status_code == 400
    assert client.post("/api/casino/keno", json={"stake": 10, "picks": list(range(1, 12))}).status_code == 400
    assert client.post("/api/casino/keno", json={"stake": 10, "picks": [5, 5, 6]}).status_code == 400
    assert client.post("/api/casino/keno", json={"stake": 10, "picks": [0, 5]}).status_code == 400
    assert client.post("/api/casino/keno", json={"stake": 10, "picks": [81]}).status_code == 400
    assert client.post("/api/casino/keno", json={"stake": 10, "picks": [7]}).status_code == 200


def test_dice_win_lose_and_math(client):
    login_demo(client)
    # Under 95 wins ~95% of rounds; over 95 wins ~5%: loop for both sides.
    won = lost = None
    for _ in range(30):
        d = client.post("/api/casino/dice", json={"stake": 10, "target": 95, "direction": "under"}).get_json()
        if d["win"] and won is None:
            won = d
            assert won["payout"] == round(10 * won["multiplier"], 2)
            assert won["roll"] < 95
        if won:
            break
    for _ in range(40):
        d = client.post("/api/casino/dice", json={"stake": 10, "target": 95, "direction": "over"}).get_json()
        if not d["win"] and lost is None:
            lost = d
            assert lost["payout"] == 0.0
            assert lost["roll"] <= 95
        if lost:
            break
    assert won is not None and lost is not None


def test_dice_guards(client):
    r = client.post("/api/casino/dice", json={"stake": 10, "target": 50, "direction": "over"})
    assert r.status_code == 401
    login_demo(client)
    assert client.post("/api/casino/dice", json={"stake": 10, "target": 0, "direction": "over"}).status_code == 400
    assert client.post("/api/casino/dice", json={"stake": 10, "target": 96, "direction": "under"}).status_code == 400
    assert client.post("/api/casino/dice", json={"stake": 10, "target": 50, "direction": "sideways"}).status_code == 400
    assert client.post("/api/casino/dice", json={"stake": 200, "target": 50, "direction": "over"}).status_code == 400


def _start_mines(client, stake, mines):
    r = client.post("/api/casino/mines/start", json={"stake": stake, "mines": mines})
    assert r.status_code == 200, r.get_json()
    return r.get_json()["game_id"]


def test_mines_full_flow_cashout(client):
    login_demo(client)
    gid = _start_mines(client, 10, 3)
    # Stake leaves the wallet at start, before any history row exists.
    assert balance(client) == 90.00
    assert casino_rows(client) == []
    # Reveal until a safe tile is found; an unlucky bust just restarts
    # the round (balance baseline moves with it).
    safe = None
    while safe is None:
        for tile in range(25):
            d = client.post("/api/casino/mines/reveal", json={"game_id": gid, "tile": tile}).get_json()
            if d.get("safe"):
                safe = d
                break
            assert d.get("bust") is True
            gid = _start_mines(client, 10, 3)
            break
    assert safe["multiplier"] > 1.0
    assert safe["potential_payout"] == round(10 * safe["multiplier"], 2)
    # Mine positions are never sent while the game is open.
    assert "mines" not in safe
    base = balance(client)
    d = client.post("/api/casino/mines/cashout", json={"game_id": gid}).get_json()
    assert d["payout"] == round(10 * d["multiplier"], 2)
    assert balance(client) == round(base + d["payout"], 2)
    rows = casino_rows(client)
    assert rows[0]["game"] == "Mines"  # latest round first
    assert rows[0]["stake"] == 10 and rows[0]["payout"] == d["payout"]
    assert rows[0]["profit"] == round(d["payout"] - 10, 2)


def test_mines_bust_and_guards(client):
    login_demo(client)
    r = client.post("/api/casino/mines/start", json={"stake": 10, "mines": 10})
    gid = r.get_json()["game_id"]
    # Cashout with zero safe tiles is rejected.
    assert client.post("/api/casino/mines/cashout", json={"game_id": gid}).status_code == 400
    # Reveal every tile: a bust must happen (only 15 safe tiles exist).
    busted = None
    for tile in range(25):
        d = client.post("/api/casino/mines/reveal", json={"game_id": gid, "tile": tile}).get_json()
        if d.get("bust"):
            busted = d
            break
    assert busted is not None
    assert busted["payout"] == 0.0
    assert len(busted["mines"]) == 10
    # Closed games reject further play.
    assert client.post("/api/casino/mines/reveal", json={"game_id": gid, "tile": 0}).status_code == 400
    assert client.post("/api/casino/mines/cashout", json={"game_id": gid}).status_code == 400
    # History shows the bust with the original stake.
    rows = casino_rows(client)
    assert rows[0]["game"] == "Mines" and rows[0]["stake"] == 10
    assert rows[0]["payout"] == 0.0 and rows[0]["profit"] == -10.0
    # Bad params.
    assert client.post("/api/casino/mines/start", json={"stake": 10, "mines": 0}).status_code == 400
    assert client.post("/api/casino/mines/start", json={"stake": 10, "mines": 11}).status_code == 400
    assert client.post("/api/casino/mines/start", json={"stake": 500, "mines": 3}).status_code == 400
    assert client.post("/api/casino/mines/start", json={"stake": 10, "mines": 3}).status_code == 200


def test_mines_ownership(client):
    login_demo(client)
    gid = client.post("/api/casino/mines/start", json={"stake": 10, "mines": 3}).get_json()["game_id"]
    client.post("/api/auth/logout")
    # Accounts are admin-provisioned only: mallory is created by
    # the admin, then logs in on this client.
    admin = wrap(client.application.test_client())
    assert admin.post("/api/auth/login", json={"username": "admin", "password": "admin123"}).status_code == 200
    assert admin.post("/api/admin/players", json={"username": "mallory", "password": "secret12", "credit": 100}).status_code == 200
    assert client.post("/api/auth/login", json={"username": "mallory", "password": "secret12"}).status_code == 200
    assert client.post("/api/casino/mines/reveal", json={"game_id": gid, "tile": 0}).status_code == 403
    assert client.post("/api/casino/mines/cashout", json={"game_id": gid}).status_code == 403
    assert client.post("/api/casino/mines/reveal", json={"game_id": 99999, "tile": 0}).status_code == 404
