"""Residual-gap regression tests (sweep 2026-11-03).

Each test names the finding it pins. Helpers mirror test_security.py:
accounts are admin-provisioned only (public registration is removed).
"""
import sys, os
import sqlite3
import threading

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


@pytest.fixture
def raw(app):
    return app.test_client()


def _token(c):
    return c.get("/api/csrf-token").get_json()["token"]


def _login(c, username, password="password12"):
    t = _token(c)
    r = c.post("/api/auth/login", json={"username": username, "password": password},
               headers={"X-CSRF-Token": t})
    assert r.status_code == 200, r.get_json()
    return r.get_json()


def _admin(c):
    return _login(c, "admin", "admin123")


def _subadmin(c):
    return _login(c, "subadmin", "subadmin123")


def _mk_player(admin, username, credit, password="password12"):
    r = admin.post("/api/admin/players",
                   json={"username": username, "password": password, "credit": credit})
    assert r.status_code == 200, r.get_json()
    return r.get_json()


def _fund_subadmin(admin, sub, amount=1000000):
    # Transfer-model setup: main admin allots to the sub-admin so it
    # can fund its own players (creation opening credit + add-credit
    # both debit the sub-admin's balance).
    me = sub.get("/api/me").get_json()["user"]
    r = admin.post(f"/api/admin/subadmins/{me['id']}/add-credit", json={"amount": amount})
    assert r.status_code == 200, r.get_json()
    return r.get_json()


def _reg(c, username, credit=100):
    admin = wrap(c.application.test_client())
    _admin(admin)
    _mk_player(admin, username, credit)
    return _login(c, username)


def _bookmaker(client):
    m = client.get("/api/matches/1").get_json()
    mk = next(x for x in m["markets"] if x["kind"] == "bookmaker")
    return mk, mk["selections"][0]


# --- F-A: settle_match must not flip a match with zero caller bets ---

def test_settle_match_no_bets_refused(client):
    _reg(client, "nobets", 100)
    r = client.post("/api/matches/1/settle")
    assert r.status_code == 400
    assert "No unsettled bets" in r.get_json()["error"]
    # The match stays open and betting still works.
    assert client.get("/api/matches/1").get_json()["settled"] is False
    mk, sel = _bookmaker(client)
    r = client.post("/api/bets", json={"match_id": 1, "market_id": mk["id"],
                                       "selection_id": sel["id"], "side": "back",
                                       "stake": 10})
    assert r.status_code == 200, r.get_json()


def test_settle_match_with_bets_still_works(client):
    _reg(client, "withbets", 100)
    mk, sel = _bookmaker(client)
    r = client.post("/api/bets", json={"match_id": 1, "market_id": mk["id"],
                                       "selection_id": sel["id"], "side": "back",
                                       "stake": 10})
    assert r.status_code == 200, r.get_json()
    r = client.post("/api/matches/1/settle")
    assert r.status_code == 200, r.get_json()
    assert r.get_json()["settled_bets"] == 1


# --- F-B: sub-admin id-existence oracle -> uniform 404 ---

def test_subadmin_oracle_uniform_404(client):
    admin = wrap(client.application.test_client())
    _admin(admin)
    sub = wrap(client.application.test_client())
    _subadmin(sub)
    _fund_subadmin(admin, sub)
    own = _mk_player(sub, "ownp", 100)
    foreign = _mk_player(admin, "foreignp", 100)
    assert sub.get(f"/api/admin/players/{own['id']}").status_code == 200
    # Missing, foreign-downline, and admin ids must be indistinguishable.
    assert sub.get("/api/admin/players/99999").status_code == 404
    assert sub.get(f"/api/admin/players/{foreign['id']}").status_code == 404
    assert sub.get("/api/admin/players/1").status_code == 404
    assert sub.post(f"/api/admin/players/{foreign['id']}/add-credit",
                    json={"amount": 10}).status_code == 404


# --- F-C: sub-admin password reset floor is 8, like everything else ---

def test_subadmin_reset_password_min_8(client):
    admin = wrap(client.application.test_client())
    _admin(admin)
    sub = wrap(client.application.test_client())
    _subadmin(sub)
    # Sub-admin id 2 is the seeded one; reset via main admin.
    r = admin.post("/api/admin/subadmins/2/reset-password",
                   json={"new_password": "abcd"})
    assert r.status_code == 400
    r = admin.post("/api/admin/subadmins/2/reset-password",
                   json={"new_password": "abcdefgh"})
    assert r.status_code == 200, r.get_json()
    _login(sub, "subadmin", "abcdefgh")


# --- F-D: admin opening credit must be whole cents ---

def test_admin_create_player_whole_cents(client):
    admin = wrap(client.application.test_client())
    _admin(admin)
    for bad, msg in ((10.005, "whole cents"), (0.009, "whole cents"),
                     (100.555, "whole cents"), (True, "Invalid credit")):
        r = admin.post("/api/admin/players",
                       json={"username": f"frac{bad}", "password": "password12",
                             "credit": bad})
        assert r.status_code == 400, (bad, r.get_json())
        assert msg in r.get_json()["error"], (bad, r.get_json())
    r = admin.post("/api/admin/players",
                   json={"username": "whole", "password": "password12", "credit": 10.00})
    assert r.status_code == 200, r.get_json()
    assert r.get_json()["balance"] == 10.00


# --- F-E: non-dict JSON bodies -> 400, never 500 ---

def test_non_dict_json_bodies_400(raw):
    t = _token(raw)
    h = {"X-CSRF-Token": t}
    for path, body in (
            ("/api/bets", [1, 2, 3]),
            ("/api/bets", "hello"),
            ("/api/bets", 123),
            ("/api/casino/limbo", [10]),
            ("/api/me/stakes", [100]),
            ("/api/auth/login", [1, 2]),
    ):
        r = raw.post(path, json=body, headers=h)
        assert r.status_code == 400, (path, body, r.status_code)
        assert "JSON object" in r.get_json()["error"]


# --- F-F: malformed ids -> 400, never 500; digit strings still work ---

def test_malformed_ids_400(client):
    _reg(client, "badids", 100)
    mk, sel = _bookmaker(client)
    assert client.post("/api/bets", json={"match_id": [], "market_id": mk["id"],
                                          "selection_id": sel["id"], "side": "back",
                                          "stake": 10}).status_code == 400
    assert client.post("/api/bets", json={"match_id": 1, "market_id": {},
                                          "selection_id": sel["id"], "side": "back",
                                          "stake": 10}).status_code == 400
    assert client.post("/api/bets", json={"match_id": 1, "market_id": mk["id"],
                                          "selection_id": "abc", "side": "back",
                                          "stake": 10}).status_code == 400
    assert client.post("/api/casino/blackjack/hit",
                       json={"game_id": []}).status_code == 400
    assert client.post("/api/casino/videopoker/draw",
                       json={"game_id": {"x": 1}}).status_code == 400
    # Digit strings keep working (column-affinity behavior preserved).
    r = client.post("/api/bets", json={"match_id": "1", "market_id": str(mk["id"]),
                                       "selection_id": str(sel["id"]), "side": "back",
                                       "stake": 10})
    assert r.status_code == 200, r.get_json()


# --- F-G: roulette / mini-roulette amounts must be whole cents ---

def test_roulette_fractional_amounts_rejected(client):
    _reg(client, "roul", 1000)
    for path, value in (("/api/casino/roulette", 0), ("/api/casino/miniroulette", 0)):
        r = client.post(path, json={"bets": [{"type": "straight", "value": value,
                                              "amount": 10.015}]})
        assert r.status_code == 400, (path, r.get_json())
        r = client.post(path, json={"bets": [{"type": "straight", "value": value,
                                              "amount": 10.01}]})
        assert r.status_code == 200, (path, r.get_json())


# --- F-H: login rate limit survives XFF rotation ---

def test_login_rate_limit_xff_rotation(tmp_path):
    app = create_app({"DATABASE": str(tmp_path / "test.db"), "TESTING": True,
                      "RATE_LIMIT_LOGIN_USER": 3, "RATE_LIMIT_LOGIN_IP": 1000})
    c = wrap(app.test_client())
    t = _token(c)
    codes = []
    for i in range(5):
        # A fresh spoofed X-Forwarded-For on every attempt.
        r = c.post("/api/auth/login", json={"username": "nosuch", "password": "x"},
                   headers={"X-CSRF-Token": t, "X-Forwarded-For": f"10.0.0.{i}"})
        codes.append(r.status_code)
    assert codes == [401, 401, 401, 429, 429], codes
    # A correct login still works: the brake only blocks failures.
    assert c.post("/api/auth/login", json={"username": "demo", "password": "demo123"},
                  headers={"X-CSRF-Token": t}).status_code == 200


# --- F-I: bool stakes rejected ---

def test_bool_stakes_rejected(client):
    _reg(client, "boolstake", 100)
    mk, sel = _bookmaker(client)
    r = client.post("/api/bets", json={"match_id": 1, "market_id": mk["id"],
                                       "selection_id": sel["id"], "side": "back",
                                       "stake": True})
    assert r.status_code == 400
    r = client.post("/api/casino/limbo", json={"stake": True, "target": 2.0})
    assert r.status_code == 400
    admin = wrap(client.application.test_client())
    _admin(admin)
    p = _mk_player(admin, "booladmin", 100)
    r = admin.post(f"/api/admin/players/{p['id']}/add-credit", json={"amount": True})
    assert r.status_code == 400


# --- F-J: 7-day absolute session cap + pruning ---

def test_session_absolute_cap_and_prune(app, client, tmp_path):
    _reg(client, "oldie", 100)
    assert client.get("/api/me").get_json()["user"] is not None
    db = sqlite3.connect(str(tmp_path / "test.db"))
    db.execute("UPDATE sessions SET created_at = '2019-01-01T00:00:00+00:00'")
    db.commit()
    # The next request prunes the row (via _open) and the cap rejects it.
    assert client.get("/api/me").get_json()["user"] is None
    assert db.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 0
    db.close()


# --- F-K: authenticated JSON is private, never shared-cacheable ---

def test_cache_control_private_on_auth_json(client, raw):
    _reg(client, "cacheu", 100)
    r = client.get("/api/me")
    assert r.headers.get("Cache-Control") == "private, must-revalidate"
    r = raw.get("/api/matches")
    assert "private" not in (r.headers.get("Cache-Control") or "")


# --- F-N: /api/bets is capped at 200 rows like the statement ---

def test_bets_list_capped_at_200(app, client, tmp_path):
    _reg(client, "manybets", 100000)
    mk, sel = _bookmaker(client)
    db = sqlite3.connect(str(tmp_path / "test.db"))
    me = db.execute("SELECT id FROM users WHERE username = 'manybets'").fetchone()[0]
    for i in range(250):
        db.execute(
            "INSERT INTO bets (user_id, match_id, market_id, selection_id, side,"
            " odds, stake, placed_at) VALUES (?, 1, ?, ?, 'back', 1.85, 1, 'x')",
            (me, mk["id"], sel["id"]))
    db.commit()
    db.close()
    rows = client.get("/api/bets").get_json()
    assert len(rows) == 200
    assert rows[0]["id"] > rows[-1]["id"]  # most recent first


# --- F-L: gameResult escapes its text (defence in depth) ---

def test_gameresult_escapes():
    import pathlib
    js = pathlib.Path(__file__).parent.parent.joinpath("static", "app.js").read_text(encoding="utf-8")
    start = js.index("function gameResult")
    body = js[start:start + 400]
    assert "esc(text)" in body, body


# --- F-M: BEGIN IMMEDIATE closes the settle-placement window ---

def _db_count_unsettled_on_settled(tmp_path):
    db = sqlite3.connect(str(tmp_path / "test.db"))
    n = db.execute(
        "SELECT COUNT(*) FROM bets b JOIN matches m ON m.id = b.match_id"
        " WHERE b.status = 'unsettled' AND m.settled = 1").fetchone()[0]
    n2 = db.execute(
        "SELECT COUNT(*) FROM bets b JOIN markets mk ON mk.id = b.market_id"
        " WHERE b.status = 'unsettled' AND mk.settled = 1").fetchone()[0]
    db.close()
    return n, n2


def test_no_stranded_bets_under_settle_match_burst(app, tmp_path):
    admin = wrap(app.test_client())
    _admin(admin)
    _mk_player(admin, "settler", 100000)
    _mk_player(admin, "bettor", 100000)
    settler = wrap(app.test_client())
    _login(settler, "settler")
    bettor = wrap(app.test_client())
    _login(bettor, "bettor")
    mk, sel = _bookmaker(settler)
    # 100 settled-candidate bets make the settle transaction slow
    # enough (~10ms+) for the race window to bite without the fix.
    for _ in range(100):
        r = settler.post("/api/bets", json={"match_id": 1, "market_id": mk["id"],
                                            "selection_id": sel["id"], "side": "back",
                                            "stake": 1})
        assert r.status_code == 200, r.get_json()
    bar = threading.Barrier(2)
    results = {"settle": [], "bets": []}

    def do_settle():
        bar.wait(timeout=30)
        for _ in range(5):
            results["settle"].append(
                settler.post("/api/matches/1/settle").status_code)

    def do_bets():
        bar.wait(timeout=30)
        for _ in range(30):
            results["bets"].append(bettor.post(
                "/api/bets", json={"match_id": 1, "market_id": mk["id"],
                                   "selection_id": sel["id"], "side": "back",
                                   "stake": 1}).status_code)

    ts = [threading.Thread(target=do_settle), threading.Thread(target=do_bets)]
    for t in ts:
        t.start()
    for t in ts:
        t.join(timeout=120)
    assert all(c in (200, 400) for c in results["settle"]), results["settle"]
    assert all(c in (200, 400) for c in results["bets"]), results["bets"]
    assert 200 in results["settle"]
    n_match, _ = _db_count_unsettled_on_settled(tmp_path)
    assert n_match == 0, "stranded unsettled bets on a settled match"


def test_no_stranded_bets_under_admin_market_settle_burst(app, tmp_path):
    admin = wrap(app.test_client())
    _admin(admin)
    _mk_player(admin, "mbettor", 100000)
    bettor = wrap(app.test_client())
    _login(bettor, "mbettor")
    mk, sel = _bookmaker(bettor)
    bar = threading.Barrier(2)
    results = {"settle": [], "bets": []}

    def do_settle():
        bar.wait(timeout=30)
        results["settle"].append(admin.post(
            f"/api/admin/markets/{mk['id']}/settle",
            json={"winner": sel["name"]}).status_code)

    def do_bets():
        bar.wait(timeout=30)
        for _ in range(30):
            results["bets"].append(bettor.post(
                "/api/bets", json={"match_id": 1, "market_id": mk["id"],
                                   "selection_id": sel["id"], "side": "back",
                                   "stake": 1}).status_code)

    ts = [threading.Thread(target=do_settle), threading.Thread(target=do_bets)]
    for t in ts:
        t.start()
    for t in ts:
        t.join(timeout=120)
    assert results["settle"] == [200], results["settle"]
    assert all(c in (200, 400) for c in results["bets"]), results["bets"]
    _, n_market = _db_count_unsettled_on_settled(tmp_path)
    assert n_market == 0, "stranded unsettled bets on a settled market"
