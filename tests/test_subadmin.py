"""Tests for the sub-admin role: main admin creates sub-admins, sub-admins
manage ONLY their own downline (create players, allot credit, suspend,
reset passwords), full player-detail views with scoping, and the
main-admin-only gates (settlement, notices, sub-admin management).
Server-side rules only -- the frontend merely hides links."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

import live_feed
from app import create_app
from csrf_helpers import wrap


@pytest.fixture
def clients3(tmp_path):
    """Three independent sessions on one fresh DB: main admin, sub-admin
    (the seeded demo), and a player client. Plain clients, NOT nested
    `with` blocks (see test_admin.py fixture note)."""
    live_feed.clear_cache()
    app = create_app({"DATABASE": str(tmp_path / "test.db"), "TESTING": True})
    yield wrap(app.test_client()), wrap(app.test_client()), wrap(app.test_client())


def login(client, username, password):
    r = client.post("/api/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.get_json()
    return r.get_json()


def login_admin(client):
    return login(client, "admin", "admin123")


def login_subadmin(client):
    return login(client, "subadmin", "subadmin123")


def login_demo(client):
    return login(client, "demo", "demo123")


def match_market(client, match_id, kind):
    m = client.get(f"/api/matches/{match_id}").get_json()
    mk = next(x for x in m["markets"] if x["kind"] == kind)
    return m, mk


def create_player(client, username, password, credit):
    r = client.post("/api/admin/players", json={
        "username": username, "password": password, "credit": credit})
    assert r.status_code == 200, r.get_json()
    return r.get_json()


def fund_subadmin(admin, sub, amount=1000000):
    """Transfer-model setup: main admin allots to the sub-admin so it
    can fund its own players (creation opening credit + add-credit
    both debit the sub-admin's balance)."""
    me = sub.get("/api/me").get_json()["user"]
    r = admin.post(f"/api/admin/subadmins/{me['id']}/add-credit", json={"amount": amount})
    assert r.status_code == 200, r.get_json()
    return r.get_json()


def test_subadmin_seed_and_gating(clients3):
    player, sub, admin = clients3
    me = login_subadmin(sub)
    assert me["role"] == "subadmin"
    # Sub-admin cannot bet (manage-only, like the main admin).
    _, mk = match_market(sub, 1, "bookmaker")
    r = sub.post("/api/bets", json={
        "match_id": 1, "market_id": mk["id"], "selection_id": mk["selections"][0]["id"],
        "side": "back", "stake": 10})
    assert r.status_code == 403
    # Logged-out and plain players get 401/403 on manager routes.
    assert player.get("/api/admin/overview").status_code == 401
    login_demo(player)
    assert player.get("/api/admin/overview").status_code == 403
    assert player.get("/api/admin/players/1").status_code == 403


def test_main_creates_subadmin_and_manages(clients3):
    player, sub, admin = clients3
    login_admin(admin)
    r = admin.post("/api/admin/subadmins", json={"username": "agent1", "password": "agentpass"})
    assert r.status_code == 200, r.get_json()
    assert r.get_json()["username"] == "agent1"
    assert r.get_json()["status"] == "active"
    # Case-insensitive uniqueness, like players.
    assert admin.post("/api/admin/subadmins",
                      json={"username": "AGENT1", "password": "otherpass"}).status_code == 400
    assert admin.post("/api/admin/subadmins",
                      json={"username": "ag2", "password": "x"}).status_code == 400
    subs = admin.get("/api/admin/subadmins").get_json()
    names = [s["username"] for s in subs]
    assert "agent1" in names and "subadmin" in names
    agent = next(s for s in subs if s["username"] == "agent1")
    # Suspend blocks login; reactivate restores it.
    assert admin.post(f"/api/admin/subadmins/{agent['id']}/suspend").status_code == 200
    bad = sub.post("/api/auth/login", json={"username": "agent1", "password": "agentpass"})
    assert bad.status_code == 401
    assert admin.post(f"/api/admin/subadmins/{agent['id']}/activate").status_code == 200
    me = login(sub, "agent1", "agentpass")
    assert me["role"] == "subadmin"
    # Password reset by main admin.
    assert admin.post(f"/api/admin/subadmins/{agent['id']}/reset-password",
                      json={"new_password": "agentpass2"}).status_code == 200
    assert sub.post("/api/auth/login",
                    json={"username": "agent1", "password": "agentpass"}).status_code == 401
    assert login(sub, "agent1", "agentpass2")["role"] == "subadmin"
    # Managing a non-subadmin through the subadmin routes is rejected.
    me_admin = admin.get("/api/me").get_json()["user"]
    assert admin.post(f"/api/admin/subadmins/{me_admin['id']}/suspend").status_code == 400
    assert admin.post("/api/admin/subadmins/9999/suspend").status_code == 404


def test_subadmin_cannot_create_subadmin_or_settle_or_notice(clients3):
    player, sub, admin = clients3
    login_subadmin(sub)
    # Creating sub-admins/admins is main-admin-only.
    assert sub.post("/api/admin/subadmins",
                    json={"username": "rogue", "password": "roguepass"}).status_code == 403
    assert sub.get("/api/admin/subadmins").status_code == 403
    # Settlement is main-admin-only.
    _, mk = match_market(sub, 1, "bookmaker")
    assert sub.post(f"/api/admin/markets/{mk['id']}/settle",
                    json={"winner": "Kirtipur Kings"}).status_code == 403
    assert sub.get("/api/admin/markets").status_code == 403
    assert sub.post("/api/admin/notices", json={"text": "x"}).status_code == 403


def test_subadmin_downline_scoping(clients3):
    player, sub, admin = clients3
    login_admin(admin)
    login_subadmin(sub)
    fund_subadmin(admin, sub)
    # Main admin's own player vs sub-admin's own player.
    main_player = create_player(admin, "mainp", "secret12", 1000)
    sub_player = create_player(sub, "subp", "secret12", 2000)
    assert sub_player["created_by"] == "subadmin"
    # Sub-admin overview sees ONLY its own downline.
    ov = sub.get("/api/admin/overview").get_json()
    assert ov["scope"] == "own"
    assert ov["totals"]["players"] == 1
    assert ov["totals"]["total_credit"] == 2000
    assert [p["username"] for p in ov["players"]] == ["subp"]
    assert "subadmins" not in ov
    # Main admin overview sees everything, including the sub-admin list.
    ov = admin.get("/api/admin/overview").get_json()
    assert ov["scope"] == "all"
    assert ov["totals"]["players"] == 3  # demo + mainp + subp
    assert any(s["username"] == "subadmin" for s in ov["subadmins"])
    sub_row = next(s for s in ov["subadmins"] if s["username"] == "subadmin")
    assert sub_row["downline_players"] == 1
    # Cross-downline actions are 404 (uniform with missing ids, so a
    # sub-admin cannot enumerate which user ids exist).
    assert sub.post(f"/api/admin/players/{main_player['id']}/suspend").status_code == 404
    assert sub.post(f"/api/admin/players/{main_player['id']}/add-credit",
                    json={"amount": 100}).status_code == 404
    assert sub.get(f"/api/admin/players/{main_player['id']}").status_code == 404
    # Managing admins / other sub-admins is 404 for a sub-admin.
    me_admin = admin.get("/api/me").get_json()["user"]
    assert sub.post(f"/api/admin/players/{me_admin['id']}/suspend").status_code == 404
    me_sub = sub.get("/api/me").get_json()["user"]
    assert sub.post(f"/api/admin/players/{me_sub['id']}/suspend").status_code == 404
    # Own player is fully manageable.
    assert sub.post(f"/api/admin/players/{sub_player['id']}/add-credit",
                    json={"amount": 500}).status_code == 200
    assert sub.post(f"/api/admin/players/{sub_player['id']}/suspend").status_code == 200
    assert sub.post(f"/api/admin/players/{sub_player['id']}/activate").status_code == 200


def test_subadmin_credit_guards_and_password_reset(clients3):
    player, sub, admin = clients3
    login_admin(admin)
    login_subadmin(sub)
    fund_subadmin(admin, sub)
    p = create_player(sub, "guardp", "secret12", 1000)
    pid = p["id"]
    # Deduct below zero and below open exposure are rejected.
    assert sub.post(f"/api/admin/players/{pid}/deduct-credit",
                    json={"amount": 1001}).status_code == 400
    login(player, "guardp", "secret12")
    _, mk = match_market(player, 1, "bookmaker")
    r = player.post("/api/bets", json={
        "match_id": 1, "market_id": mk["id"], "selection_id": mk["selections"][0]["id"],
        "side": "back", "stake": 100})
    assert r.status_code == 200
    # Balance 1000, exposure 100: deducting 950 would leave 50 < 100.
    assert sub.post(f"/api/admin/players/{pid}/deduct-credit",
                    json={"amount": 950}).status_code == 400
    # Deducting exactly down to exposure is allowed.
    assert sub.post(f"/api/admin/players/{pid}/deduct-credit",
                    json={"amount": 900}).status_code == 200
    # Password reset by the sub-admin works; old password dies.
    assert sub.post(f"/api/admin/players/{pid}/reset-password",
                    json={"new_password": "guardpass9"}).status_code == 200
    assert player.post("/api/auth/login",
                       json={"username": "guardp", "password": "secret12"}).status_code == 401
    assert login(player, "guardp", "guardpass9")["balance"] == 100.0


def test_subadmin_suspension_blocks_login_and_live_bets(clients3):
    player, sub, admin = clients3
    login_admin(admin)
    login_subadmin(sub)
    fund_subadmin(admin, sub)
    p = create_player(sub, "suspp", "secret12", 500)
    pid = p["id"]
    login(player, "suspp", "secret12")
    assert sub.post(f"/api/admin/players/{pid}/suspend").status_code == 200
    # Suspension revokes the live session outright (401): the session
    # is dead the moment the admin suspends, not just blocked.
    _, mk = match_market(player, 1, "bookmaker")
    r = player.post("/api/bets", json={
        "match_id": 1, "market_id": mk["id"], "selection_id": mk["selections"][0]["id"],
        "side": "back", "stake": 10})
    assert r.status_code == 401
    # Fresh login is refused too.
    assert player.post("/api/auth/login",
                       json={"username": "suspp", "password": "secret12"}).status_code == 401
    assert sub.post(f"/api/admin/players/{pid}/activate").status_code == 200
    assert login(player, "suspp", "secret12")["balance"] == 500.0


def test_player_detail_full_view_and_scoping(clients3):
    player, sub, admin = clients3
    login_admin(admin)
    login_subadmin(sub)
    fund_subadmin(admin, sub)
    p = create_player(sub, "detailp", "secret12", 3000)
    pid = p["id"]
    login(player, "detailp", "secret12")
    _, mk = match_market(player, 1, "bookmaker")
    team_a, team_b = mk["selections"][0], mk["selections"][1]
    back = player.post("/api/bets", json={
        "match_id": 1, "market_id": mk["id"], "selection_id": team_a["id"],
        "side": "back", "stake": 10}).get_json()
    assert back["odds"] > 0
    # Main admin settles (settlement is main-only, and it settles every
    # player's bets on the market, including this sub-admin downline bet).
    r = admin.post(f"/api/admin/markets/{mk['id']}/settle",
                   json={"winner": team_a["name"]})
    assert r.status_code == 200 and r.get_json()["settled_bets"] == 1
    # Sub-admin sees the full detail for its own player.
    det = sub.get(f"/api/admin/players/{pid}").get_json()
    assert det["player"]["username"] == "detailp"
    assert det["player"]["balance"] == round(3000 + 10 * (back["odds"] - 1), 2)
    assert det["player"]["exposure"] == 0
    assert det["player"]["credit_limit"] == 3000
    assert det["player"]["status"] == "active"
    assert det["player"]["created_by"] == "subadmin"
    assert det["player"]["created_at"]
    assert len(det["bets"]) == 1
    assert det["bets"][0]["status"] == "settled"
    assert det["bets"][0]["match_title"] and det["bets"][0]["selection"] == team_a["name"]
    assert any(t["kind"] in ("BET_WON", "BET_LOST") for t in det["statement"])
    assert det["pnl"]["total_profit"] == round(10 * (back["odds"] - 1), 2)
    # Main admin sees the same full detail for any player.
    det2 = admin.get(f"/api/admin/players/{pid}").get_json()
    assert det2["player"]["username"] == "detailp"
    assert det2["pnl"]["total_profit"] == det["pnl"]["total_profit"]
    # No password data anywhere in the detail output.
    assert "secret12" not in str(det)
    # Detail of a nonexistent player is 404.
    assert admin.get("/api/admin/players/9999").status_code == 404


def test_ledger_scoping(clients3):
    player, sub, admin = clients3
    login_admin(admin)
    login_subadmin(sub)
    fund_subadmin(admin, sub)
    create_player(admin, "ledmain", "secret12", 100)
    create_player(sub, "ledsub", "secret12", 100)
    main_ledger = admin.get("/api/admin/ledger").get_json()
    main_actions = [(row["admin"], row["action"]) for row in main_ledger]
    assert ("admin", "CREATE_PLAYER") in main_actions
    assert ("subadmin", "CREATE_PLAYER") in main_actions
    sub_ledger = sub.get("/api/admin/ledger").get_json()
    assert all(row["admin"] == "subadmin" for row in sub_ledger)
    assert any(row["action"] == "CREATE_PLAYER" and row["target"] == "ledsub"
               for row in sub_ledger)
    assert not any(row["target"] == "ledmain" for row in sub_ledger)


def test_end_to_end_main_subadmin_player_settle(clients3):
    """Full agent chain: main -> sub-admin -> player -> credit -> bet ->
    main settlement -> statement/P&L agree."""
    player, sub, admin = clients3
    login_admin(admin)
    agent = admin.post("/api/admin/subadmins",
                       json={"username": "e2eagent", "password": "e2epass1"}).get_json()
    assert agent["username"] == "e2eagent"
    login(sub, "e2eagent", "e2epass1")
    r = admin.post(f"/api/admin/subadmins/{agent['id']}/add-credit",
                   json={"amount": 1000000})
    assert r.status_code == 200, r.get_json()
    p = create_player(sub, "e2eplayer", "secret12", 4000)
    pid = p["id"]
    r = sub.post(f"/api/admin/players/{pid}/add-credit", json={"amount": 1000})
    assert r.status_code == 200 and r.get_json()["balance"] == 5000
    login(player, "e2eplayer", "secret12")
    _, mk = match_market(player, 1, "bookmaker")
    team_a = mk["selections"][0]
    bet = player.post("/api/bets", json={
        "match_id": 1, "market_id": mk["id"], "selection_id": team_a["id"],
        "side": "back", "stake": 50}).get_json()
    me = player.get("/api/me").get_json()["user"]
    assert me["exposure"] == 50.0 and me["available"] == 4950.0
    # Main admin sees the player in all-IDs; sub-admin sees only its own.
    ov = admin.get("/api/admin/overview").get_json()
    assert any(x["username"] == "e2eplayer" for x in ov["players"])
    ov = sub.get("/api/admin/overview").get_json()
    assert [x["username"] for x in ov["players"]] == ["e2eplayer"]
    # Main settles; the downline player's P&L and statement update.
    r = admin.post(f"/api/admin/markets/{mk['id']}/settle",
                   json={"winner": team_a["name"]})
    assert r.status_code == 200
    det = sub.get(f"/api/admin/players/{pid}").get_json()
    assert det["player"]["exposure"] == 0
    assert det["player"]["balance"] == round(5000 + 50 * (bet["odds"] - 1), 2)
    assert det["pnl"]["total_profit"] == round(50 * (bet["odds"] - 1), 2)
