"""Tests for the transfer model: sub-admin -> player credit is a TRANSFER
from the sub-admin's own spendable balance (balance minus own open
exposure), never minting. Applies to both opening credit at player
creation and later add-credit. Main admin -> sub-admin allotment is
the funding source at the top of the tree and MINTS (no debit); main
admin -> player funding is unchanged (also mints)."""
import sqlite3
import sys
import os
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

import live_feed
from app import create_app
from csrf_helpers import wrap


@pytest.fixture
def app(tmp_path):
    live_feed.clear_cache()
    return create_app({"DATABASE": str(tmp_path / "test.db"), "TESTING": True})


@pytest.fixture
def tmpdb(tmp_path):
    return str(tmp_path / "test.db")


def _login(c, username, password):
    r = c.post("/api/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.get_json()
    return r.get_json()


def _admin(c):
    return _login(c, "admin", "admin123")


def _subadmin(c):
    return _login(c, "subadmin", "subadmin123")


def _me(c):
    return c.get("/api/me").get_json()["user"]


def _mk_player(c, username, credit, password="password12"):
    r = c.post("/api/admin/players",
               json={"username": username, "password": password, "credit": credit})
    assert r.status_code == 200, r.get_json()
    return r.get_json()


def _mk_subadmin(admin, username, password="password12"):
    r = admin.post("/api/admin/subadmins", json={"username": username, "password": password})
    assert r.status_code == 200, r.get_json()
    return r.get_json()


def _allot(admin, sub_id, amount):
    r = admin.post(f"/api/admin/subadmins/{sub_id}/add-credit", json={"amount": amount})
    assert r.status_code == 200, r.get_json()
    return r.get_json()


def _player_balance(admin, pid):
    return admin.get(f"/api/admin/players/{pid}").get_json()["player"]["balance"]


def test_subadmin_add_credit_beyond_balance_rejected(app):
    admin, sub = wrap(app.test_client()), wrap(app.test_client())
    _admin(admin)
    me_sub = _subadmin(sub)
    _allot(admin, me_sub["id"], 100)
    p = _mk_player(sub, "overp", 0)
    r = sub.post(f"/api/admin/players/{p['id']}/add-credit", json={"amount": 101})
    assert r.status_code == 400, r.get_json()
    assert "Insufficient available balance" in r.get_json()["error"]
    # Both balances unchanged: no partial debit, no partial credit.
    assert _me(sub)["balance"] == 100.0
    assert _player_balance(admin, p["id"]) == 0.0


def test_subadmin_add_credit_within_balance_transfers_exactly(app):
    admin, sub = wrap(app.test_client()), wrap(app.test_client())
    _admin(admin)
    me_sub = _subadmin(sub)
    _allot(admin, me_sub["id"], 100)
    p = _mk_player(sub, "exactp", 0)
    r = sub.post(f"/api/admin/players/{p['id']}/add-credit", json={"amount": 40})
    assert r.status_code == 200, r.get_json()
    assert _me(sub)["balance"] == 60.0
    assert _player_balance(admin, p["id"]) == 40.0
    r = sub.post(f"/api/admin/players/{p['id']}/add-credit", json={"amount": 60})
    assert r.status_code == 200, r.get_json()
    assert _me(sub)["balance"] == 0.0
    assert _player_balance(admin, p["id"]) == 100.0


def test_subadmin_create_player_opening_credit_draws_from_balance(app):
    admin, sub = wrap(app.test_client()), wrap(app.test_client())
    _admin(admin)
    me_sub = _subadmin(sub)
    _allot(admin, me_sub["id"], 100)
    p = _mk_player(sub, "openp", 30)
    assert _me(sub)["balance"] == 70.0
    assert p["balance"] == 30.0
    # 71 exceeds the remaining 70: rejected, no debit, no player.
    r = sub.post("/api/admin/players",
                 json={"username": "openfail", "password": "password12", "credit": 71})
    assert r.status_code == 400, r.get_json()
    assert _me(sub)["balance"] == 70.0
    ghost = wrap(app.test_client())
    assert ghost.post("/api/auth/login",
                      json={"username": "openfail", "password": "password12"}).status_code == 401
    # Exactly the remainder still works.
    p2 = _mk_player(sub, "openp2", 70)
    assert _me(sub)["balance"] == 0.0
    assert p2["balance"] == 70.0


def test_concurrent_allots_cannot_exceed_balance(app):
    admin = wrap(app.test_client())
    _admin(admin)
    seed_sub = wrap(app.test_client())
    me_sub = _subadmin(seed_sub)
    _allot(admin, me_sub["id"], 100)
    # Ten zero-credit players (free to create), then ten concurrent
    # 60-pt allots against a 100-pt balance: exactly one may win.
    pids = [_mk_player(seed_sub, f"race{i}", 0)["id"] for i in range(10)]
    barrier = threading.Barrier(10)
    results = [None] * 10

    def _allot_one(i):
        c = wrap(app.test_client())
        _subadmin(c)
        barrier.wait(timeout=30)
        results[i] = c.post(f"/api/admin/players/{pids[i]}/add-credit",
                            json={"amount": 60}).status_code

    threads = [threading.Thread(target=_allot_one, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)
    assert all(t.is_alive() is False for t in threads)
    assert results.count(200) == 1, results
    assert results.count(400) == 9, results
    assert _me(seed_sub)["balance"] == 40.0
    assert sum(_player_balance(admin, pid) for pid in pids) == 60.0


def test_spent_subadmin_cannot_fund_new_players(app):
    admin, sub = wrap(app.test_client()), wrap(app.test_client())
    _admin(admin)
    me_sub = _subadmin(sub)
    _allot(admin, me_sub["id"], 50)
    p = _mk_player(sub, "spentp", 50)
    assert _me(sub)["balance"] == 0.0
    r = sub.post("/api/admin/players",
                 json={"username": "spentp2", "password": "password12", "credit": 0.01})
    assert r.status_code == 400, r.get_json()
    r = sub.post(f"/api/admin/players/{p['id']}/add-credit", json={"amount": 0.01})
    assert r.status_code == 400, r.get_json()
    assert _me(sub)["balance"] == 0.0
    assert _player_balance(admin, p["id"]) == 50.0
    # Zero-credit creation is not an allotment: still free.
    p0 = _mk_player(sub, "spentp0", 0)
    assert p0["balance"] == 0.0
    assert _me(sub)["balance"] == 0.0


def test_self_credit_cannot_mint(app):
    admin, sub = wrap(app.test_client()), wrap(app.test_client())
    me_admin = _admin(admin)
    me_sub = _subadmin(sub)
    _allot(admin, me_sub["id"], 100)
    # Sub-admin add-credit to its own id: not an own-downline player.
    r = sub.post(f"/api/admin/players/{me_sub['id']}/add-credit", json={"amount": 50})
    assert r.status_code == 404, r.get_json()
    assert _me(sub)["balance"] == 100.0
    # Main admin add-credit to its own id: not a player.
    r = admin.post(f"/api/admin/players/{me_admin['id']}/add-credit", json={"amount": 50})
    assert r.status_code == 400, r.get_json()
    assert _me(admin)["balance"] == 0.0
    # Allotment endpoint is main-admin-only and sub-admin-only targets.
    assert sub.post(f"/api/admin/subadmins/{me_sub['id']}/add-credit",
                    json={"amount": 50}).status_code == 403
    p = _mk_player(admin, "selfp", 10)
    assert admin.post(f"/api/admin/subadmins/{p['id']}/add-credit",
                      json={"amount": 50}).status_code == 400
    assert admin.post("/api/admin/subadmins/99999/add-credit",
                      json={"amount": 50}).status_code == 404
    assert admin.post(f"/api/admin/subadmins/{me_sub['id']}/add-credit",
                      json={"amount": 10.005}).status_code == 400
    assert _me(sub)["balance"] == 100.0


def test_main_admin_allotment_mints_at_top(app):
    admin, sub = wrap(app.test_client()), wrap(app.test_client())
    _admin(admin)
    me_sub = _subadmin(sub)
    assert _me(admin)["balance"] == 0.0
    got = _allot(admin, me_sub["id"], 500)
    assert got["balance"] == 500.0
    assert got["credit_limit"] == 500.0
    me = _me(sub)
    assert me["balance"] == 500.0
    # The main admin's balance is untouched: the root mints, it does
    # not spend. The sub-admin list view shows the allotment too.
    assert _me(admin)["balance"] == 0.0
    subs = admin.get("/api/admin/subadmins").get_json()
    row = next(s for s in subs if s["username"] == "subadmin")
    assert row["balance"] == 500.0 and row["available"] == 500.0
    # Main admin -> player funding is unchanged (still mints).
    p = _mk_player(admin, "rootp", 1000)
    assert p["balance"] == 1000.0
    assert _me(admin)["balance"] == 0.0
    r = admin.post(f"/api/admin/players/{p['id']}/add-credit", json={"amount": 500})
    assert r.status_code == 200
    assert _me(admin)["balance"] == 0.0


def test_transfer_respects_open_exposure(app, tmpdb):
    admin, sub = wrap(app.test_client()), wrap(app.test_client())
    _admin(admin)
    me_sub = _subadmin(sub)
    _allot(admin, me_sub["id"], 100)
    # Sub-admins cannot bet (manage-only), so their exposure column
    # is 0 in practice -- but the guard must still honor it if it is
    # ever nonzero. Set it directly, as the exposure guard requires.
    conn = sqlite3.connect(tmpdb)
    conn.execute("UPDATE users SET exposure = 30 WHERE id = ?", (me_sub["id"],))
    conn.commit()
    conn.close()
    p = _mk_player(sub, "expp", 0)
    # Available is 100 - 30 = 70: 71 fails, 70 succeeds.
    r = sub.post(f"/api/admin/players/{p['id']}/add-credit", json={"amount": 71})
    assert r.status_code == 400, r.get_json()
    r = sub.post(f"/api/admin/players/{p['id']}/add-credit", json={"amount": 70})
    assert r.status_code == 200, r.get_json()
    assert _me(sub)["balance"] == 30.0
    # Available is now 30 - 30 = 0: even 0.01 of creation credit fails.
    r = sub.post("/api/admin/players",
                 json={"username": "expfail", "password": "password12", "credit": 0.01})
    assert r.status_code == 400, r.get_json()


def test_deduct_does_not_refund_subadmin(app):
    """DOCUMENTED CURRENT BEHAVIOR, deliberately unchanged by the
    transfer task: deduct is a burn (player loses, sub-admin gains
    nothing back). If the client later wants deduct to return funds
    to the sub-admin, that is a separate decision -- this test will
    flag the change."""
    admin, sub = wrap(app.test_client()), wrap(app.test_client())
    _admin(admin)
    me_sub = _subadmin(sub)
    _allot(admin, me_sub["id"], 100)
    p = _mk_player(sub, "burnp", 100)
    assert _me(sub)["balance"] == 0.0
    r = sub.post(f"/api/admin/players/{p['id']}/deduct-credit", json={"amount": 40})
    assert r.status_code == 200, r.get_json()
    assert _player_balance(admin, p["id"]) == 60.0
    assert _me(sub)["balance"] == 0.0
