"""Tests for the admin / agent panel: roles, player management, credit
rules, suspension, password reset, admin market settlement, audit
ledger and home-page notices. Server-side rules only -- the frontend
merely hides links."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

import live_feed
from app import create_app
from csrf_helpers import wrap

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLES = os.path.normpath(os.path.join(APP_DIR, "..", "recon", "samples"))


def load_sample(name):
    with open(os.path.join(SAMPLES, name)) as f:
        return json.load(f)


@pytest.fixture
def clients(tmp_path):
    """Two independent sessions (separate cookie jars) on one fresh DB:
    c_player acts as a player, c_admin as the admin. Plain clients, NOT
    nested `with` blocks: nesting two test-client context managers pops
    the wrong request context (Flask) and breaks every other request."""
    live_feed.clear_cache()
    app = create_app({"DATABASE": str(tmp_path / "test.db"), "TESTING": True})
    yield wrap(app.test_client()), wrap(app.test_client())


def login(client, username, password):
    r = client.post("/api/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.get_json()
    return r.get_json()


def login_admin(client):
    return login(client, "admin", "admin123")


def login_demo(client):
    return login(client, "demo", "demo123")


def match_market(client, match_id, kind):
    m = client.get(f"/api/matches/{match_id}").get_json()
    mk = next(x for x in m["markets"] if x["kind"] == kind)
    return m, mk


def admin_create(client, username, password, credit):
    r = client.post("/api/admin/players", json={
        "username": username, "password": password, "credit": credit})
    assert r.status_code == 200, r.get_json()
    return r.get_json()


# ---------------- gating ----------------

def test_admin_seed_and_gating(clients):
    player, admin = clients
    assert player.get("/api/admin/overview").status_code == 401  # logged out
    login_demo(player)
    assert player.get("/api/admin/overview").status_code == 403  # player
    assert player.get("/api/admin/markets").status_code == 403
    assert player.get("/api/admin/ledger").status_code == 403
    me = login_admin(admin)
    assert me["role"] == "admin"
    ov = admin.get("/api/admin/overview").get_json()
    assert ov["totals"]["players"] == 1  # the seeded demo player
    assert ov["totals"]["active"] == 1
    assert ov["totals"]["total_credit"] == 0  # demo was not admin-assigned
    assert len(admin.get("/api/admin/markets").get_json()) > 0
    assert admin.get("/api/admin/ledger").get_json() == []


def test_admin_cannot_bet_and_cannot_be_managed(clients):
    player, admin = clients
    me = login_admin(admin)
    m, mk = match_market(admin, 1, "bookmaker")
    r = admin.post("/api/bets", json={
        "match_id": 1, "market_id": mk["id"], "selection_id": mk["selections"][0]["id"],
        "side": "back", "stake": 10})
    assert r.status_code == 403
    assert admin.post(f"/api/admin/players/{me['id']}/suspend").status_code == 400
    assert admin.post(f"/api/admin/players/{me['id']}/add-credit",
                      json={"amount": 100}).status_code == 400
    assert admin.post("/api/admin/players/9999/suspend").status_code == 404


# ---------------- create / credit ----------------

def test_create_player_and_credit(clients):
    player, admin = clients
    login_admin(admin)
    p = admin_create(admin, "player1", "secret12", 5000)
    assert p["balance"] == 5000 and p["credit_limit"] == 5000
    assert p["created_by"] == "admin" and p["status"] == "active"
    ov = admin.get("/api/admin/overview").get_json()
    assert ov["totals"]["players"] == 2
    assert ov["totals"]["total_credit"] == 5000
    assert len(ov["downline"]) == 1  # created by this admin
    assert admin.post("/api/admin/players", json={
        "username": "player1", "password": "otherpass", "credit": 100}).status_code == 400
    # Usernames are unique case-insensitively.
    assert admin.post("/api/admin/players", json={
        "username": "PLAYER1", "password": "otherpass", "credit": 100}).status_code == 400
    assert admin.post("/api/admin/players", json={
        "username": "p2", "password": "secret12", "credit": -5}).status_code == 400
    assert admin.post("/api/admin/players", json={
        "username": "p2", "password": "x", "credit": 100}).status_code == 400
    me = login(player, "player1", "secret12")
    assert me["balance"] == 5000


def test_add_deduct_credit_rules(clients):
    player, admin = clients
    login_admin(admin)
    p = admin_create(admin, "pcredit", "secret12", 5000)
    pid = p["id"]
    r = admin.post(f"/api/admin/players/{pid}/add-credit", json={"amount": 1000}).get_json()
    assert r["balance"] == 6000 and r["credit_limit"] == 6000
    r = admin.post(f"/api/admin/players/{pid}/deduct-credit", json={"amount": 2000}).get_json()
    assert r["balance"] == 4000 and r["credit_limit"] == 4000
    assert admin.post(f"/api/admin/players/{pid}/deduct-credit",
                      json={"amount": 5000}).status_code == 400  # exceeds balance
    assert admin.post(f"/api/admin/players/{pid}/deduct-credit",
                      json={"amount": 0}).status_code == 400
    assert admin.post(f"/api/admin/players/{pid}/add-credit",
                      json={"amount": -100}).status_code == 400
    # Deduction below open exposure is rejected, at exposure is allowed.
    login(player, "pcredit", "secret12")
    m, mk = match_market(player, 1, "bookmaker")
    bet = player.post("/api/bets", json={
        "match_id": 1, "market_id": mk["id"], "selection_id": mk["selections"][0]["id"],
        "side": "back", "stake": 100})
    assert bet.status_code == 200  # exposure now 100, balance 4000
    assert admin.post(f"/api/admin/players/{pid}/deduct-credit",
                      json={"amount": 3950}).status_code == 400  # 50 left < 100 exposure
    r = admin.post(f"/api/admin/players/{pid}/deduct-credit",
                   json={"amount": 3900}).get_json()
    assert r["balance"] == 100 and r["credit_limit"] == 100  # available exactly 0


# ---------------- suspend / password ----------------

def test_suspend_blocks_login_and_betting(clients):
    player, admin = clients
    login_admin(admin)
    p = admin_create(admin, "psusp", "secret12", 5000)
    pid = p["id"]
    login(player, "psusp", "secret12")
    m, mk = match_market(player, 1, "bookmaker")
    assert player.post("/api/bets", json={
        "match_id": 1, "market_id": mk["id"], "selection_id": mk["selections"][0]["id"],
        "side": "back", "stake": 10}).status_code == 200
    assert admin.post(f"/api/admin/players/{pid}/suspend").status_code == 200
    # Suspension revokes the live session outright (401), which is
    # stricter than the old 403-on-a-live-session: the session is dead
    # the moment the admin suspends, not just blocked from betting.
    assert player.post("/api/bets", json={
        "match_id": 1, "market_id": mk["id"], "selection_id": mk["selections"][0]["id"],
        "side": "back", "stake": 10}).status_code == 401
    player.post("/api/auth/logout")
    assert player.post("/api/auth/login",
                        json={"username": "psusp", "password": "secret12"}).status_code == 401
    assert admin.post(f"/api/admin/players/{pid}/activate").status_code == 200
    assert player.post("/api/auth/login",
                        json={"username": "psusp", "password": "secret12"}).status_code == 200


def test_admin_password_reset(clients):
    player, admin = clients
    login_admin(admin)
    p = admin_create(admin, "preset", "oldpass1", 1000)
    assert admin.post(f"/api/admin/players/{p['id']}/reset-password",
                      json={"new_password": "newpass9"}).status_code == 200
    assert player.post("/api/auth/login",
                        json={"username": "preset", "password": "oldpass1"}).status_code == 401
    assert player.post("/api/auth/login",
                        json={"username": "preset", "password": "newpass9"}).status_code == 200
    assert admin.post(f"/api/admin/players/{p['id']}/reset-password",
                      json={"new_password": "x"}).status_code == 400


# ---------------- settlement ----------------

def test_admin_settlement_bookmaker_and_idempotency(clients):
    player, admin = clients
    login_demo(player)
    login_admin(admin)
    m, mk = match_market(player, 1, "bookmaker")
    team_a, team_b = mk["selections"][0], mk["selections"][1]
    assert team_a["name"] == "Kirtipur Kings"
    back = player.post("/api/bets", json={
        "match_id": 1, "market_id": mk["id"], "selection_id": team_a["id"],
        "side": "back", "stake": 10}).get_json()
    lay = player.post("/api/bets", json={
        "match_id": 1, "market_id": mk["id"], "selection_id": team_b["id"],
        "side": "lay", "stake": 10}).get_json()
    o_back, o_lay = back["odds"], lay["odds"]
    assert player.get("/api/me").get_json()["user"]["exposure"] == round(
        10 + 10 * (o_lay - 1), 2)
    r = admin.post(f"/api/admin/markets/{mk['id']}/settle",
                   json={"winner": "Kirtipur Kings"})
    assert r.status_code == 200, r.get_json()
    assert r.get_json()["settled_bets"] == 2
    # Back on the winner wins; lay on the loser wins (selection != winner).
    user = player.get("/api/me").get_json()["user"]
    assert user["exposure"] == 0
    assert user["balance"] == round(100 + 10 * (o_back - 1) + 10, 2)
    pnl = player.get("/api/pnl").get_json()
    assert pnl["total_profit"] == round(10 * (o_back - 1) + 10, 2)
    settled = player.get("/api/bets?status=settled").get_json()
    assert len(settled) == 2
    # Idempotency: re-settling is rejected and changes nothing.
    assert admin.post(f"/api/admin/markets/{mk['id']}/settle",
                      json={"winner": "Kirtipur Kings"}).status_code == 400
    assert player.get("/api/me").get_json()["user"]["balance"] == user["balance"]
    # A winner that is not a selection is rejected (fresh market).
    _, mk2 = match_market(player, 2, "bookmaker")
    assert admin.post(f"/api/admin/markets/{mk2['id']}/settle",
                      json={"winner": "Nobody"}).status_code == 400


def test_admin_settlement_fancy_and_void(clients):
    player, admin = clients
    login_demo(player)
    login_admin(admin)
    # VOID first: stakes are refunded (exposure released, balance untouched).
    m2, mk2 = match_market(player, 2, "bookmaker")
    for sel in mk2["selections"]:
        assert player.post("/api/bets", json={
            "match_id": 2, "market_id": mk2["id"], "selection_id": sel["id"],
            "side": "back", "stake": 10}).status_code == 200
    r = admin.post(f"/api/admin/markets/{mk2['id']}/settle", json={"winner": "VOID"})
    assert r.status_code == 200 and r.get_json()["settled_bets"] == 2
    user = player.get("/api/me").get_json()["user"]
    assert user["balance"] == 100 and user["exposure"] == 0
    voided = player.get("/api/bets?status=settled").get_json()
    assert all(b["profit"] == 0 for b in voided)
    stmt = player.get("/api/statement?type=SETTLEMENT").get_json()
    assert any(t["kind"] == "SETTLEMENT" and t["amount"] == 0 for t in stmt)
    # Fancy: admin declares "Yes" the winner of the seeded Yes/No market.
    _, mkf = match_market(player, 1, "fancy")
    yes = next(s for s in mkf["selections"] if s["name"] == "Yes")
    back = player.post("/api/bets", json={
        "match_id": 1, "market_id": mkf["id"], "selection_id": yes["id"],
        "side": "back", "stake": 10}).get_json()
    lay = player.post("/api/bets", json={
        "match_id": 1, "market_id": mkf["id"], "selection_id": yes["id"],
        "side": "lay", "stake": 10}).get_json()
    o_back, o_lay = back["odds"], lay["odds"]
    r = admin.post(f"/api/admin/markets/{mkf['id']}/settle", json={"winner": "Yes"})
    assert r.status_code == 200 and r.get_json()["settled_bets"] == 2
    user = player.get("/api/me").get_json()["user"]
    # Back Yes wins (profit stake*(odds-1)); lay Yes loses the liability.
    assert user["balance"] == round(100 + 10 * (o_back - 1) - 10 * (o_lay - 1), 2)
    assert user["exposure"] == 0


def test_admin_settlement_live_fancy_conversion(clients, monkeypatch):
    """A live fancy bet stores the converted decimal (1 + rate/100) at
    placement; admin settlement must use that stored decimal as-is --
    no second conversion. Upstream is stubbed with the real Ranji
    detail sample; the fancy market/runner is picked from the live
    event response itself, not hardcoded."""
    player, admin = clients
    login_demo(player)
    login_admin(admin)
    sample = load_sample("guest_detail_ranji.json")
    monkeypatch.setattr(live_feed, "fetch_json", lambda path: sample)
    ev = player.get("/api/live/event/-11239905").get_json()["event"]
    target = None
    for mk in ev["markets"]:
        if mk["market_type"] not in ("OVERS", "BATSMAN"):
            continue
        if mk["status"] != "OPEN" or mk["bet_lock"]:
            continue
        for r in mk["runners"]:
            if r["status"] == "ACTIVE" and r["best_back"] is not None:
                target = (mk, r)
                break
        if target:
            break
    assert target, "no priced fancy runner in the sample"
    mk, r = target
    rate = r["best_back"]
    decimal = 1 + rate / 100
    mat = player.post("/api/live/materialize", json={
        "event_id": "-11239905", "market_id": mk["market_id"], "runner_id": r["id"],
        "side": "back", "odds": decimal})
    assert mat.status_code == 200, mat.get_json()
    bet = player.post("/api/bets", json={
        "match_id": mat.get_json()["match_id"], "market_id": mat.get_json()["market_id"],
        "selection_id": mat.get_json()["selection_id"], "side": "back",
        "stake": 10, "odds": decimal})
    assert bet.status_code == 200, bet.get_json()
    assert bet.get_json()["odds"] == decimal
    assert player.get("/api/me").get_json()["user"]["exposure"] == 10
    admin_markets = admin.get("/api/admin/markets").get_json()
    shadow = next(m for m in admin_markets if m["match_id"] == mat.get_json()["match_id"])
    assert shadow["open_bets"] == 1
    s = admin.post(f"/api/admin/markets/{shadow['id']}/settle",
                   json={"winner": r["name"]})
    assert s.status_code == 200, s.get_json()
    user = player.get("/api/me").get_json()["user"]
    # Back win at the converted decimal, once -- not converted twice.
    assert user["balance"] == round(100 + 10 * (decimal - 1), 2)
    assert user["exposure"] == 0


# ---------------- ledger / notices ----------------

def test_admin_ledger_and_notices(clients):
    player, admin = clients
    login_admin(admin)
    p = admin_create(admin, "pledger", "secret12", 1000)
    pid = p["id"]
    admin.post(f"/api/admin/players/{pid}/add-credit", json={"amount": 500})
    admin.post(f"/api/admin/players/{pid}/suspend")
    admin.post(f"/api/admin/players/{pid}/activate")
    admin.post(f"/api/admin/players/{pid}/reset-password", json={"new_password": "ledgerpass9"})
    _, mk = match_market(admin, 1, "bookmaker")
    admin.post(f"/api/admin/markets/{mk['id']}/settle", json={"winner": "Kirtipur Kings"})
    admin.post("/api/admin/notices", json={"text": "Maintenance on Sunday"})
    ledger = admin.get("/api/admin/ledger").get_json()
    actions = [row["action"] for row in ledger]
    for expected in ("CREATE_PLAYER", "ADD_CREDIT", "SUSPEND", "ACTIVATE",
                     "RESET_PASSWORD", "SETTLE_MARKET", "NOTICE"):
        assert expected in actions
    create_row = next(row for row in ledger if row["action"] == "CREATE_PLAYER")
    assert create_row["admin"] == "admin" and create_row["target"] == "pledger"
    assert create_row["amount"] == 1000
    # No password value anywhere in the ledger output.
    assert "ledgerpass9" not in json.dumps(ledger)
    assert "secret12" not in json.dumps(ledger)
    # Notices: public read, admin-only write, empty text clears.
    assert player.get("/api/notices").get_json()["notice"]["text"] == "Maintenance on Sunday"
    login_demo(player)
    assert player.post("/api/admin/notices", json={"text": "x"}).status_code == 403
    admin.post("/api/admin/notices", json={"text": ""})
    assert admin.get("/api/notices").get_json()["notice"] is None
