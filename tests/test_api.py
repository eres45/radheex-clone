"""API tests for the demo exchange clone."""
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
    assert r.status_code == 200
    return r.get_json()


def first_bookmaker_selection(client, match_id):
    m = client.get(f"/api/matches/{match_id}").get_json()
    mk = next(x for x in m["markets"] if x["kind"] == "bookmaker")
    return m, mk, mk["selections"][0]


def test_public_registration_removed(client):
    # Self-registration is gone: accounts are admin-provisioned only.
    for i in range(3):
        assert client.post("/api/auth/register",
                           json={"username": f"gone{i}", "password": "secret12"}).status_code == 404
    assert client.post("/api/auth/login",
                       json={"username": "gone0", "password": "secret12"}).status_code == 401


def test_admin_created_player_login(client):
    # Admin provisions the account and hands over the login details.
    admin = wrap(client.application.test_client())
    r = admin.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert r.status_code == 200, r.get_json()
    r = admin.post("/api/admin/players",
                   json={"username": "alice", "password": "secret12", "credit": 100})
    assert r.status_code == 200, r.get_json()
    r = client.post("/api/auth/login", json={"username": "alice", "password": "secret12"})
    assert r.status_code == 200
    assert r.get_json()["username"] == "alice"
    me = client.get("/api/me").get_json()
    assert me["user"]["balance"] == 100.00
    client.post("/api/auth/logout")
    assert client.get("/api/me").get_json()["user"] is None
    bad = client.post("/api/auth/login", json={"username": "alice", "password": "wrong"})
    assert bad.status_code == 401




def test_demo_seed_account(client):
    user = login_demo(client)
    assert user["balance"] == 100.00
    assert user["exposure"] == 0.00
    assert user["available"] == 100.00
    assert user["quick_stakes"] == [100, 500, 1000, 5000, 10000, 50000]


def test_place_back_bet_and_exposure(client):
    login_demo(client)
    m, mk, sel = first_bookmaker_selection(client, 1)
    r = client.post("/api/bets", json={
        "match_id": 1, "market_id": mk["id"], "selection_id": sel["id"],
        "side": "back", "stake": 10})
    assert r.status_code == 200, r.get_json()
    user = r.get_json()["user"]
    assert user["exposure"] == 10.00
    assert user["available"] == 90.00
    unsettled = client.get("/api/bets?status=unsettled").get_json()
    assert len(unsettled) == 1
    assert unsettled[0]["side"] == "back"


def test_place_lay_bet_liability(client):
    login_demo(client)
    m, mk, sel = first_bookmaker_selection(client, 1)
    r = client.post("/api/bets", json={
        "match_id": 1, "market_id": mk["id"], "selection_id": sel["id"],
        "side": "lay", "stake": 10})
    assert r.status_code == 200
    odds = r.get_json()["odds"]
    user = r.get_json()["user"]
    assert user["exposure"] == round(10 * (odds - 1), 2)
    assert user["available"] == round(100 - user["exposure"], 2)


def test_bet_requires_login_and_valid_stake(client):
    r = client.post("/api/bets", json={
        "match_id": 1, "market_id": 1, "selection_id": 1, "side": "back", "stake": 10})
    assert r.status_code == 401
    login_demo(client)
    m, mk, sel = first_bookmaker_selection(client, 1)
    too_big = client.post("/api/bets", json={
        "match_id": 1, "market_id": mk["id"], "selection_id": sel["id"],
        "side": "back", "stake": 100000})
    assert too_big.status_code == 400  # exceeds available balance
    over_max = client.post("/api/bets", json={
        "match_id": 1, "market_id": mk["id"], "selection_id": sel["id"],
        "side": "back", "stake": 100001})
    assert over_max.status_code == 400  # exceeds market max


def test_suspended_match_rejects_bets(client):
    login_demo(client)
    m, mk, sel = first_bookmaker_selection(client, 3)  # seeded suspended
    r = client.post("/api/bets", json={
        "match_id": 3, "market_id": mk["id"], "selection_id": sel["id"],
        "side": "back", "stake": 10})
    assert r.status_code == 400


def test_settle_pnl_and_statement(client):
    login_demo(client)
    m, mk, sel = first_bookmaker_selection(client, 1)
    # First bookmaker selection is team_a, the seeded winner of match 1.
    r = client.post("/api/bets", json={
        "match_id": 1, "market_id": mk["id"], "selection_id": sel["id"],
        "side": "back", "stake": 10})
    odds = r.get_json()["odds"]
    s = client.post("/api/matches/1/settle")
    assert s.status_code == 200
    assert s.get_json()["settled_bets"] == 1
    user = s.get_json()["user"]
    assert user["exposure"] == 0.00
    assert user["balance"] == round(100 + 10 * (odds - 1), 2)
    pnl = client.get("/api/pnl").get_json()
    assert pnl["total_profit"] == round(10 * (odds - 1), 2)
    assert len(pnl["per_match"]) == 1
    stmt = client.get("/api/statement").get_json()
    assert any(t["kind"] == "BET_WON" for t in stmt)
    assert stmt[0]["balance_after"] == user["balance"]  # statement agrees with wallet
    hist = client.get("/api/bets?status=settled").get_json()
    assert hist[0]["profit"] == round(10 * (odds - 1), 2)
    results = client.get("/api/results").get_json()
    assert any(x["id"] == 1 and x["result"] == "Kirtipur Kings" for x in results)


def test_lay_losing_settlement(client):
    login_demo(client)
    m, mk, sel = first_bookmaker_selection(client, 1)
    r = client.post("/api/bets", json={
        "match_id": 1, "market_id": mk["id"], "selection_id": sel["id"],
        "side": "lay", "stake": 10})
    odds = r.get_json()["odds"]
    client.post("/api/matches/1/settle")
    user = client.get("/api/me").get_json()["user"]
    # Laying the eventual winner loses the liability.
    assert user["balance"] == round(100 - 10 * (odds - 1), 2)
    assert user["exposure"] == 0.00


def test_set_stake_persists(client):
    login_demo(client)
    r = client.post("/api/me/stakes", json={"quick_stakes": [50, 150, 250, 500, 750, 1000]})
    assert r.status_code == 200
    assert r.get_json()["quick_stakes"] == [50, 150, 250, 500, 750, 1000]
    assert client.get("/api/me/stakes").get_json()["quick_stakes"][0] == 50
    bad = client.post("/api/me/stakes", json={"quick_stakes": [50, 150]})
    assert bad.status_code == 400


def test_change_password(client):
    login_demo(client)
    r = client.post("/api/me/password", json={
        "current_password": "demo123", "new_password": "newpass9"})
    assert r.status_code == 200
    client.post("/api/auth/logout")
    assert client.post("/api/auth/login",
                        json={"username": "demo", "password": "demo123"}).status_code == 401
    assert client.post("/api/auth/login",
                        json={"username": "demo", "password": "newpass9"}).status_code == 200


def test_odds_shape_and_sports_counts(client):
    m = client.get("/api/matches/1").get_json()
    for mk in m["markets"]:
        for sel in mk["selections"]:
            assert sel["lay"] >= sel["back"] >= 1.01
    sports = client.get("/api/sports").get_json()
    live = client.get("/api/matches?live=1").get_json()
    for s in sports:
        assert s["live_count"] == sum(1 for x in live if x["sport"] == s["sport"])
