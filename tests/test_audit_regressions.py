"""Regression tests from the final end-to-end audit (2026-11-03).

Covers: live odds must come from the server-side feed (never a
client-supplied price), and non-finite / overflowing numbers must be
rejected with 400, never a 500 or a corrupted balance.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

import live_feed
from app import create_app
from csrf_helpers import wrap

SAMPLES = os.path.normpath(os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "..", "recon", "samples"))


def load_sample(name):
    with open(os.path.join(SAMPLES, name)) as f:
        return json.load(f)


@pytest.fixture
def client(tmp_path):
    live_feed.clear_cache()
    app = create_app({"DATABASE": str(tmp_path / "test.db"), "TESTING": True})
    with app.test_client() as c:
        yield wrap(c)


def login_demo(client):
    r = client.post("/api/auth/login", json={"username": "demo", "password": "demo123"})
    assert r.status_code == 200
    return r.get_json()


def detail_with_books():
    detail = load_sample("detail_soccer.json")
    detail["metadata"]["books"] = (
        "1.264507448|0|OPEN|False|11/03/2026 04:26:13|1|False|"
        "2909511~ACTIVE~2.5:100:*2.4:50:~2.6:80:*2.7:60:,"
        "2760854~ACTIVE~3.0:50:~3.2:40:,"
        "58805~ACTIVE~3.4:70:~3.5:60:")
    return detail


def test_live_bet_ignores_inflated_client_odds(client, monkeypatch):
    """Audit BUG-1: a client claiming odds 1000 on a 2.5 feed price must
    still book and settle at the feed price (2.5), never at 1000."""
    monkeypatch.setattr(live_feed, "fetch_json", lambda path: detail_with_books())
    login_demo(client)
    mat = client.post("/api/live/materialize", json={
        "event_id": "36239536", "market_id": "1.264507448",
        "runner_id": "2909511", "side": "back", "odds": 1000})
    assert mat.status_code == 200
    assert mat.get_json()["odds"] == 2.5
    mj = mat.get_json()
    r = client.post("/api/bets", json={
        "match_id": mj["match_id"], "market_id": mj["market_id"],
        "selection_id": mj["selection_id"], "side": "back",
        "stake": 10, "odds": 1000})
    assert r.status_code == 200
    assert r.get_json()["odds"] == 2.5
    client.post("/api/auth/logout")
    admin = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert admin.status_code == 200
    s = client.post(f"/api/admin/markets/{mj['market_id']}/settle",
                    json={"winner": "Chapecoense"})
    assert s.status_code == 200
    assert s.get_json()["settled_bets"] == 1
    # demo started at 100, won 10*(2.5-1) = 15 -> 115, never 10090.
    me = client.post("/api/auth/login", json={"username": "demo", "password": "demo123"})
    assert me.get_json()["balance"] == 115.0


def test_live_fancy_bet_uses_server_converted_decimal(client, monkeypatch):
    """Fancy rates convert server-side: rate 100 -> decimal 2.0, even if
    the client claims a different price."""
    monkeypatch.setattr(live_feed, "fetch_json",
                        lambda path: load_sample("guest_detail_ranji.json"))
    login_demo(client)
    mat = client.post("/api/live/materialize", json={
        "event_id": "-11239905", "market_id": "3333712",
        "runner_id": "3333712", "side": "back", "odds": 999})
    assert mat.status_code == 200
    assert mat.get_json()["odds"] == 2.0
    mj = mat.get_json()
    r = client.post("/api/bets", json={
        "match_id": mj["match_id"], "market_id": mj["market_id"],
        "selection_id": mj["selection_id"], "side": "back",
        "stake": 10, "odds": 999})
    assert r.status_code == 200
    assert r.get_json()["odds"] == 2.0


def test_nan_and_huge_stakes_rejected(client):
    """Audit BUG-2: NaN / overflowing stakes must be 400, never 500,
    and must leave balance and exposure untouched."""
    login_demo(client)
    m = client.get("/api/matches/1").get_json()
    mk = next(x for x in m["markets"] if x["kind"] == "bookmaker")
    sel = mk["selections"][0]
    for stake in (float("nan"), float("inf"), 10 ** 400):
        r = client.post("/api/bets", json={
            "match_id": 1, "market_id": mk["id"], "selection_id": sel["id"],
            "side": "back", "stake": stake})
        assert r.status_code == 400, (stake, r.status_code, r.get_json())
    me = client.get("/api/me").get_json()["user"]
    assert me["balance"] == 100.0 and me["exposure"] == 0.0


def test_nan_casino_stake_rejected(client):
    login_demo(client)
    r = client.post("/api/casino/limbo", json={"stake": float("nan"), "target": 2})
    assert r.status_code == 400
    me = client.get("/api/me").get_json()["user"]
    assert me["balance"] == 100.0


def test_admin_amounts_must_be_finite(client):
    login_demo(client)
    pid = client.get("/api/me").get_json()["user"]["id"]
    client.post("/api/auth/logout")
    client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    for amount in (float("nan"), float("inf")):
        r = client.post(f"/api/admin/players/{pid}/add-credit", json={"amount": amount})
        assert r.status_code == 400, (amount, r.status_code)
    r = client.post("/api/admin/players", json={
        "username": "badcredit", "password": "secret12", "credit": float("nan")})
    assert r.status_code == 400


def test_quick_stakes_must_be_finite(client):
    login_demo(client)
    r = client.post("/api/me/stakes", json={"quick_stakes": [float("nan")] + [10] * 5})
    assert r.status_code == 400
    r = client.post("/api/me/stakes", json={"quick_stakes": [float("inf")] + [10] * 5})
    assert r.status_code == 400
    r = client.post("/api/me/stakes", json={"quick_stakes": [10, 20, 30, 40, 50, 60]})
    assert r.status_code == 200
