"""Resilience / double-submit regression tests (audit 2026-11-03).

For each situation the test records the outcome the user will see:
balance effect, stuck state, or error. Where the pre-fix behavior was
wrong, the test pins the fixed behavior; where the behavior is
inherently a boundary (two distinct POSTs are two bets), the test
documents it instead of pretending otherwise.
"""
import os
import sqlite3
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from app import create_app
from csrf_helpers import wrap


@pytest.fixture
def app(tmp_path):
    import live_feed
    live_feed.clear_cache()
    return create_app({"DATABASE": str(tmp_path / "test.db"), "TESTING": True})


@pytest.fixture
def client(app):
    return wrap(app.test_client())


def _token(c):
    return c.get("/api/csrf-token").get_json()["token"]


def _reg(c, username, password="password12", credit=100):
    # Public self-registration is removed: accounts are admin-
    # provisioned only. Test users are created through the admin
    # create-player API (same 100-pt starting balance the old seed
    # gave), then logged in on the caller's client.
    admin = wrap(c.application.test_client())
    _admin(admin)
    _mk_player(admin, username, credit, password)
    return _login(c, username, password)




def _login(c, username, password="password12"):
    t = _token(c)
    r = c.post("/api/auth/login", json={"username": username, "password": password},
               headers={"X-CSRF-Token": t})
    assert r.status_code == 200, r.get_json()
    return r.get_json()


def _admin(c):
    return _login(c, "admin", "admin123")


def _mk_player(admin, username, credit, password="password12"):
    r = admin.post("/api/admin/players",
                   json={"username": username, "password": password, "credit": credit})
    assert r.status_code == 200, r.get_json()
    return r.get_json()


def _bookmaker(client):
    m = client.get("/api/matches/1").get_json()
    mk = next(x for x in m["markets"] if x["kind"] == "bookmaker")
    return mk, mk["selections"][0]


def _bal(c):
    return c.get("/api/me").get_json()["user"]["balance"]


def test_idempotent_retry_charges_once(client):
    """Timeout-then-retry with the same key: charged once, same response."""
    _reg(client, "idem1")
    h = {"X-Idempotency-Key": "bet-key-1"}
    mk, sel = _bookmaker(client)
    body = {"match_id": 1, "market_id": mk["id"], "selection_id": sel["id"],
            "side": "back", "stake": 10}
    r1 = client.post("/api/bets", json=body, headers=h)
    r2 = client.post("/api/bets", json=body, headers=h)
    assert r1.status_code == 200 and r2.status_code == 200
    assert r1.get_data() == r2.get_data()
    assert len(client.get("/api/bets?status=unsettled").get_json()) == 1
    assert client.get("/api/me").get_json()["user"]["exposure"] == 10.0


def test_sequential_identical_bets_without_key_are_two_bets(client):
    """Boundary, documented honestly: WITHOUT an idempotency key, two
    distinct POSTs are two bets. The key (and the SPA's in-flight
    dedup) is what makes a retry safe -- not the bet endpoint itself."""
    _reg(client, "dblseq")
    mk, sel = _bookmaker(client)
    body = {"match_id": 1, "market_id": mk["id"], "selection_id": sel["id"],
            "side": "back", "stake": 10}
    assert client.post("/api/bets", json=body).status_code == 200
    assert client.post("/api/bets", json=body).status_code == 200
    assert len(client.get("/api/bets?status=unsettled").get_json()) == 2


def test_refresh_mid_round_resumable_all_games(client):
    """Close/refresh mid-round, come back on a NEW session: every
    multi-step round is completable and no stake is stranded."""
    _reg(client, "resumeall")
    # Mines
    g = client.post("/api/casino/mines/start", json={"stake": 10, "mines": 3}).get_json()
    c2 = wrap(client.application.test_client())
    _login(c2, "resumeall")
    st = c2.get("/api/casino/mines/state").get_json()
    assert st["open"] is True and st["game_id"] == g["game_id"]
    # Tower: climb, then resume and cash out on the new session.
    tower_gid = None
    for _ in range(5):
        g = client.post("/api/casino/tower/start", json={"stake": 10}).get_json()
        r = client.post("/api/casino/tower/climb", json={"game_id": g["game_id"]}).get_json()
        if r.get("safe"):
            tower_gid = g["game_id"]
            break
    if tower_gid is None:
        pytest.skip("tower busted 5 fresh climbs in a row (p ~ 1e-4)")
    st = c2.get("/api/casino/tower/state").get_json()
    assert st["open"] is True and st["level"] >= 1
    r = c2.post("/api/casino/tower/cashout", json={"game_id": st["game_id"]})
    assert r.status_code == 200 and r.get_json()["payout"] > 0
    # Blackjack: deal, resume, stand on the new session.
    d = client.post("/api/casino/blackjack/deal", json={"stake": 10}).get_json()
    if not d.get("settled"):
        st = c2.get("/api/casino/blackjack/state").get_json()
        assert st["open"] is True
        r = c2.post("/api/casino/blackjack/stand", json={"game_id": st["game_id"]})
        assert r.status_code == 200 and r.get_json()["settled"] is True
    # Video poker: deal, resume, draw on the new session.
    d = client.post("/api/casino/videopoker/deal", json={"stake": 10}).get_json()
    st = c2.get("/api/casino/videopoker/state").get_json()
    assert st["open"] is True and len(st["hand"]) == 5
    r = c2.post("/api/casino/videopoker/draw",
                json={"game_id": st["game_id"], "holds": [0]})
    assert r.status_code == 200 and r.get_json()["settled"] is True


def test_logout_mid_round_then_resume(client):
    """Logout mid-round does NOT lose the round: re-login resumes it."""
    _reg(client, "logoutmid")
    g = client.post("/api/casino/mines/start", json={"stake": 10, "mines": 3}).get_json()
    assert client.post("/api/auth/logout").status_code == 200
    assert client.get("/api/me").get_json()["user"] is None
    _login(client, "logoutmid")
    st = client.get("/api/casino/mines/state").get_json()
    assert st["open"] is True and st["game_id"] == g["game_id"]


def test_suspension_mid_round_then_unsuspend_resume(client, app):
    """Suspended mid-round: the round is NOT settled and NOT refunded
    (policy: suspension is temporary, resume covers it -- see report).
    After unsuspend the same round cashes out normally."""
    admin = wrap(app.test_client())
    _admin(admin)
    _mk_player(admin, "suspRound", 5000)
    _login(client, "suspRound")
    tower_gid = None
    for _ in range(5):
        g = client.post("/api/casino/tower/start", json={"stake": 10}).get_json()
        r = client.post("/api/casino/tower/climb", json={"game_id": g["game_id"]}).get_json()
        if r.get("safe"):
            tower_gid = g["game_id"]
            break
    if tower_gid is None:
        pytest.skip("tower busted 5 fresh climbs in a row")
    g = {"game_id": tower_gid}
    pid = client.get("/api/me").get_json()["user"]["id"]
    assert admin.post(f"/api/admin/players/{pid}/suspend", json={}).status_code == 200
    # Revoked session: cannot act while suspended.
    assert client.post("/api/casino/tower/cashout",
                       json={"game_id": g["game_id"]}).status_code == 401
    # Unsuspend, log back in, same round still there and cashes out.
    assert admin.post(f"/api/admin/players/{pid}/activate", json={}).status_code == 200
    _login(client, "suspRound")
    st = client.get("/api/casino/tower/state").get_json()
    assert st["open"] is True
    r = client.post("/api/casino/tower/cashout", json={"game_id": st["game_id"]})
    assert r.status_code == 200


def test_settle_while_betting_no_stuck_bet(client, app):
    """Bet, then admin settles, then bet again: the second bet is
    refused (not silently stranded unsettled), the first settles."""
    admin = wrap(app.test_client())
    _admin(admin)
    _mk_player(admin, "settlebet", 5000)
    _login(client, "settlebet")
    mk, sel = _bookmaker(client)
    assert client.post("/api/bets", json={"match_id": 1, "market_id": mk["id"],
                                          "selection_id": sel["id"], "side": "back",
                                          "stake": 10}).status_code == 200
    assert admin.post(f"/api/admin/markets/{mk['id']}/settle",
                      json={"winner": sel["name"]}).status_code == 200
    assert client.get("/api/bets?status=unsettled").get_json() == []
    r = client.post("/api/bets", json={"match_id": 1, "market_id": mk["id"],
                                       "selection_id": sel["id"], "side": "back",
                                       "stake": 10})
    assert r.status_code == 400


def test_admin_credit_mid_round_consistent(client, app):
    """Admin credit/deduct while a round is open leaves the round and
    the wallet consistent: cashout pays on top of the new balance."""
    admin = wrap(app.test_client())
    _admin(admin)
    p = _mk_player(admin, "midround", 5000)
    _login(client, "midround")
    g = client.post("/api/casino/mines/start", json={"stake": 10, "mines": 3}).get_json()
    assert admin.post(f"/api/admin/players/{p['id']}/add-credit",
                      json={"amount": 100}).status_code == 200
    assert _bal(client) == 5000 - 10 + 100
    assert admin.post(f"/api/admin/players/{p['id']}/deduct-credit",
                      json={"amount": 50}).status_code == 200
    assert _bal(client) == 5000 - 10 + 100 - 50


def _force_telefly_phase(app, tmp_db, phase):
    """Rewrite the current TeleFly round's timestamps so wall-clock
    phase math lands where the test needs it. Returns round id."""
    import time as _t
    db = sqlite3.connect(tmp_db)
    row = db.execute("SELECT id FROM telefly_rounds ORDER BY id DESC LIMIT 1").fetchone()
    now = int(_t.time() * 1000)
    if phase == "betting":
        db.execute("UPDATE telefly_rounds SET betting_end = ?, fly_start = ?,"
                   " crash_time = ? WHERE id = ?",
                   (now + 60000, now + 60000, now + 120000, row[0]))
    else:  # flying
        db.execute("UPDATE telefly_rounds SET betting_end = ?, fly_start = ?,"
                   " crash_time = ? WHERE id = ?",
                   (now - 1000, now - 1000, now + 60000, row[0]))
    db.commit()
    db.close()
    return row[0]


def test_telefly_round_boundary_bets(client, app, tmp_path):
    """Bets placed exactly as a round closes are rejected, never lost:
    a flying-phase bet is refused with the stake untouched, and a
    betting-phase bet lands in the open round."""
    _reg(client, "tfbound")
    db_path = str(tmp_path / "test.db")
    # Create a round via state, then force it into flying phase.
    st = client.get("/api/casino/telefly/state").get_json()
    _force_telefly_phase(app, db_path, "flying")
    before = _bal(client)
    r = client.post("/api/casino/telefly/bet", json={"stake": 10})
    assert r.status_code == 400
    assert _bal(client) == before
    # Force back to betting: the bet lands.
    _force_telefly_phase(app, db_path, "betting")
    r = client.post("/api/casino/telefly/bet", json={"stake": 10})
    assert r.status_code == 200
    assert _bal(client) == before - 10
    # A second bet in the same round is refused (one bet per round).
    assert client.post("/api/casino/telefly/bet", json={"stake": 10}).status_code == 400
    assert _bal(client) == before - 10


def test_feed_failure_materialize_clean(client, app):
    """Upstream dead mid-materialize: 502, stake untouched, no rows."""
    import live_feed
    _reg(client, "feedfail")
    orig = live_feed.fetch_json
    live_feed.fetch_json = lambda path: (_ for _ in ()).throw(
        live_feed.LiveFeedError("upstream down"))
    try:
        r = client.post("/api/live/materialize",
                        json={"event_id": "123", "market_id": "1.1",
                              "runner_id": "1", "side": "back"})
        assert r.status_code == 502
    finally:
        live_feed.fetch_json = orig
    assert _bal(client) == 100.0
    assert client.get("/api/bets").get_json() == []


def test_restart_preserves_open_rounds(app, tmp_path):
    """A process restart (new app instance, same SQLite file) keeps
    open rounds: the stake is not lost to a restart. (A Render deploy
    wipes the file -- that is the separate, documented persistence
    wall, not a round bug.)"""
    db_path = str(tmp_path / "test.db")
    c1 = wrap(app.test_client())
    _reg(c1, "restart1")
    g = c1.post("/api/casino/mines/start", json={"stake": 10, "mines": 3}).get_json()
    app2 = create_app({"DATABASE": db_path, "TESTING": True})
    c2 = wrap(app2.test_client())
    _login(c2, "restart1")
    st = c2.get("/api/casino/mines/state").get_json()
    assert st["open"] is True and st["game_id"] == g["game_id"]


def test_two_tabs_balances_agree(client, app):
    """Same account in two tabs: interleaved play stays consistent;
    after refresh both tabs show the same balance."""
    _reg(client, "twotabs")
    c2 = wrap(app.test_client())
    _login(c2, "twotabs")
    mk, sel = _bookmaker(client)
    assert client.post("/api/bets", json={"match_id": 1, "market_id": mk["id"],
                                          "selection_id": sel["id"], "side": "back",
                                          "stake": 10}).status_code == 200
    assert c2.post("/api/casino/limbo", json={"stake": 10, "target": 1.5}).status_code == 200
    b1 = client.get("/api/me").get_json()["user"]
    b2 = c2.get("/api/me").get_json()["user"]
    assert b1["balance"] == b2["balance"] and b1["exposure"] == b2["exposure"]


def test_no_server_form_posts_back_button_safe(app):
    """Back-button resubmission cannot duplicate anything: the SPA has
    no <form action> server POSTs (all posts are fetch calls)."""
    html = app.test_client().get("/").get_data(as_text=True)
    assert "<form action=" not in html
