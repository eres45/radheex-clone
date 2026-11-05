"""Security regression tests (audit 2026-11-03).

Each test names the exploit it pins. Raw (unwrapped) clients are used
where the test must prove CSRF/rate-limit/session behavior itself;
wrapped clients (csrf_helpers) everywhere else.
"""
import sys, os
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


def _fund_subadmin(admin, sub, amount=1000000):
    # Transfer-model setup: main admin allots to the sub-admin so it
    # can fund its own players (creation opening credit + add-credit
    # both debit the sub-admin's balance).
    me = sub.get("/api/me").get_json()["user"]
    r = admin.post(f"/api/admin/subadmins/{me['id']}/add-credit", json={"amount": amount})
    assert r.status_code == 200, r.get_json()
    return r.get_json()


def _bookmaker(client):
    m = client.get("/api/matches/1").get_json()
    mk = next(x for x in m["markets"] if x["kind"] == "bookmaker")
    return mk, mk["selections"][0]


def _burst(app, user, password, fn, n=10):
    """Run fn(client) on n threads sharing one user, barrier-synced."""
    bar = threading.Barrier(n)
    results = [None] * n

    def go(i):
        c = wrap(app.test_client())
        _login(c, user, password)
        bar.wait(timeout=30)
        try:
            results[i] = fn(c)
        except Exception as e:  # noqa: BLE001 -- recorded, asserted below
            results[i] = e

    threads = [threading.Thread(target=go, args=(i,)) for i in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)
    return results


def test_csrf_blocks_state_posts_without_token(raw):
    _reg(raw, "csrfvictim")
    r = raw.post("/api/casino/limbo", json={"stake": 10, "target": 1.5})
    assert r.status_code == 403
    r = raw.post("/api/casino/limbo", json={"stake": 10, "target": 1.5},
                 headers={"X-CSRF-Token": "bogus"})
    assert r.status_code == 403
    # Balance untouched by both refused attempts.
    assert raw.get("/api/me").get_json()["user"]["balance"] == 100.0


def test_csrf_token_rotates_at_login(raw):
    # The pre-login (anonymous) token must NOT survive login: keeping
    # it across the privilege change is fixation-adjacent. The SPA and
    # the wrapped test client re-fetch + retry once on a CSRF 403, so
    # rotation is transparent to them; raw callers must re-fetch.
    t = _token(raw)
    r = raw.post("/api/auth/login", json={"username": "demo", "password": "demo123"},
                 headers={"X-CSRF-Token": t})
    assert r.status_code == 200
    r = raw.post("/api/casino/limbo", json={"stake": 10, "target": 1.5},
                 headers={"X-CSRF-Token": t})
    assert r.status_code == 403
    t2 = _token(raw)
    assert t2 != t
    r = raw.post("/api/casino/limbo", json={"stake": 10, "target": 1.5},
                 headers={"X-CSRF-Token": t2})
    assert r.status_code == 200


def test_login_rate_limit_blocks_brute_force(tmp_path):
    app = create_app({"DATABASE": str(tmp_path / "test.db"), "TESTING": True,
                      "RATE_LIMIT_LOGIN_USER": 3, "RATE_LIMIT_LOGIN_IP": 100})
    c = wrap(app.test_client())
    t = _token(c)
    codes = [c.post("/api/auth/login", json={"username": "nosuch", "password": "x"},
                    headers={"X-CSRF-Token": t}).status_code for _ in range(5)]
    assert codes == [401, 401, 401, 429, 429]
    # A correct login still works: the brake only blocks failures.
    assert c.post("/api/auth/login", json={"username": "demo", "password": "demo123"},
                  headers={"X-CSRF-Token": t}).status_code == 200


def test_public_registration_removed(client):
    # Self-registration is gone: accounts are admin-provisioned only.
    # The endpoint must 404 (not 429, not 405) and create nothing, no
    # matter how many times it is hit.
    for i in range(5):
        assert client.post("/api/auth/register",
                           json={"username": f"gone{i}", "password": "password12"}).status_code == 404
    assert client.post("/api/auth/login",
                       json={"username": "gone0", "password": "password12"}).status_code == 401




def test_session_revoked_on_logout(client, raw):
    _reg(client, "logout1")
    old = client.get_cookie("session").value
    assert client.post("/api/auth/logout").status_code == 200
    assert client.get("/api/me").get_json()["user"] is None
    raw.set_cookie("session", old)
    assert raw.get("/api/me").get_json()["user"] is None


def test_session_fixation_login_rotates(raw):
    # Attacker plants a pre-login cookie; after the victim logs in,
    # the planted cookie must NOT authenticate (login mints a fresh
    # random server-side token instead of keeping the planted id).
    _token(raw)  # establishes an anonymous session cookie
    planted = raw.get_cookie("session").value
    _login(raw, "demo", "demo123")
    assert raw.get_cookie("session").value != planted
    # Fresh client carrying ONLY the planted cookie:
    spy = raw.application.test_client()
    spy.set_cookie("session", planted)
    assert spy.get("/api/me").get_json()["user"] is None


def test_password_minimum_new_only(client, app):
    admin = wrap(app.test_client())
    _admin(admin)
    assert admin.post("/api/admin/players",
                       json={"username": "shortpw", "password": "1234567", "credit": 100}).status_code == 400
    assert admin.post("/api/admin/players",
                       json={"username": "okpwuser", "password": "12345678", "credit": 100}).status_code == 200
    # Existing demo account (7-char password) still logs in: the rule
    # applies to NEW passwords only, never locks out seeded accounts.
    assert client.post("/api/auth/login",
                       json={"username": "demo", "password": "demo123"}).status_code == 200
    assert client.post("/api/me/password",
                       json={"current_password": "demo123", "new_password": "short"}).status_code == 400




def test_username_charset_blocks_xss_payload(client, app):
    admin = wrap(app.test_client())
    _admin(admin)
    evil = "<img src=x onerror=alert(1)>"
    assert admin.post("/api/admin/players",
                      json={"username": evil, "password": "password12", "credit": 100}).status_code == 400
    assert admin.post("/api/admin/players",
                      json={"username": "good.name-1_2", "password": "password12", "credit": 100}).status_code == 200




def test_concurrent_bets_cannot_overdraw(app, client):
    _reg(client, "racebet")
    mk, sel = _bookmaker(client)

    def bet(c):
        return c.post("/api/bets", json={"match_id": 1, "market_id": mk["id"],
                                         "selection_id": sel["id"], "side": "back", "stake": 60})

    res = _burst(app, "racebet", "password12", bet, n=10)
    ok = sum(1 for r in res if not isinstance(r, Exception) and r.status_code == 200)
    assert ok <= 1, [getattr(r, "status_code", repr(r)) for r in res]
    me = client.get("/api/me").get_json()["user"]
    assert me["exposure"] <= me["balance"] and me["available"] >= 0


def test_concurrent_casino_cannot_overdraw(app, client):
    _reg(client, "racecasino")

    def limbo(c):
        return c.post("/api/casino/limbo", json={"stake": 60, "target": 100})

    res = _burst(app, "racecasino", "password12", limbo, n=10)
    ok = sum(1 for r in res if not isinstance(r, Exception) and r.status_code == 200)
    assert ok >= 1
    me = client.get("/api/me").get_json()["user"]
    assert me["balance"] >= 0, me


def _open_mines_with_safe_reveal(c):
    """Start mines rounds until one reveals a safe tile; returns game_id."""
    for _ in range(10):
        g = c.post("/api/casino/mines/start", json={"stake": 10, "mines": 3}).get_json()
        r = c.post("/api/casino/mines/reveal", json={"game_id": g["game_id"], "tile": 0}).get_json()
        if r.get("safe"):
            return g["game_id"]
    raise AssertionError("no safe reveal in 10 rounds")


def test_double_cashout_pays_once_mines(app, client):
    admin = wrap(app.test_client())
    _admin(admin)
    p = _mk_player(admin, "dblmines", 5000)
    _login(client, "dblmines")
    gid = _open_mines_with_safe_reveal(client)
    # NB: the helper may have burned stakes on busted starts, so the
    # pre-cashout balance (not 5000 - 10) is the reference point.
    before = client.get("/api/me").get_json()["user"]["balance"]

    def cash(c):
        return c.post("/api/casino/mines/cashout", json={"game_id": gid})

    res = _burst(app, "dblmines", "password12", cash, n=6)
    ok = [r for r in res if not isinstance(r, Exception) and r.status_code == 200]
    assert len(ok) == 1, [getattr(r, "status_code", repr(r)) for r in res]
    payout = ok[0].get_json()["payout"]
    me = client.get("/api/me").get_json()["user"]
    assert me["balance"] == round(before + payout, 2), me


def test_double_draw_and_double_stand_pay_once(client):
    _reg(client, "dblvp")
    d = client.post("/api/casino/videopoker/deal", json={"stake": 10}).get_json()
    r1 = client.post("/api/casino/videopoker/draw",
                     json={"game_id": d["game_id"], "holds": [0, 1]})
    assert r1.status_code == 200
    r2 = client.post("/api/casino/videopoker/draw",
                     json={"game_id": d["game_id"], "holds": [0, 1]})
    assert r2.status_code == 400
    _reg(client, "dblbj")
    d = client.post("/api/casino/blackjack/deal", json={"stake": 10}).get_json()
    if not d.get("settled"):
        r1 = client.post("/api/casino/blackjack/stand", json={"game_id": d["game_id"]})
        assert r1.status_code == 200
        r2 = client.post("/api/casino/blackjack/stand", json={"game_id": d["game_id"]})
        assert r2.status_code == 400


def test_idor_matrix(client, app):
    admin = wrap(app.test_client())
    _admin(admin)
    sub = wrap(app.test_client())
    _login(sub, "subadmin", "subadmin123")
    _reg(client, "victim1")
    _fund_subadmin(admin, sub)
    own = _mk_player(sub, "ownp", 100)
    foreign = _mk_player(admin, "foreignp", 100)
    # Player cannot reach admin endpoints.
    for method, path in [("get", "/api/admin/overview"),
                         ("post", "/api/admin/players/1/add-credit"),
                         ("post", "/api/admin/markets/1/settle"),
                         ("post", "/api/admin/notices")]:
        r = getattr(client, method)(path, json={"amount": 9999, "winner": "VOID", "text": "x"})
        assert r.status_code == 403, (method, path, r.status_code)
    # Anonymous cannot reach admin endpoints.
    anon = wrap(app.test_client())
    assert anon.get("/api/admin/overview").status_code == 401
    # Sub-admin: own downline OK, foreign downline forbidden (404,
    # uniform with missing ids so existence cannot be probed).
    assert sub.post(f"/api/admin/players/{own['id']}/add-credit",
                    json={"amount": 10}).status_code == 200
    assert sub.post(f"/api/admin/players/{foreign['id']}/add-credit",
                    json={"amount": 10}).status_code == 404
    # Sub-admin cannot settle (main-admin-only).
    assert sub.post("/api/admin/markets/1/settle", json={"winner": "VOID"}).status_code == 403
    # A player sees only their own bets.
    assert client.get("/api/bets").get_json() == []
    # Another player's game round is not actionable.
    assert client.post("/api/casino/mines/cashout", json={"game_id": 1}).status_code in (403, 404)


def test_sqli_attempts_blocked(client):
    r = client.post("/api/auth/login", json={"username": "' OR '1'='1", "password": "x"})
    assert r.status_code == 401
    r = client.post("/api/auth/login", json={"username": "demo'--", "password": "x"})
    assert r.status_code == 401
    _reg(client, "sqli1")
    r = client.post("/api/bets", json={"match_id": "1 OR 1=1", "market_id": 1,
                                       "selection_id": 1, "side": "back", "stake": 10})
    assert r.status_code == 400


def test_feed_proxy_validation(client, app):
    import live_feed
    _reg(client, "feedp")
    assert client.get("/api/live/event/abc").status_code == 400
    assert client.get("/api/live/event/..%2F..%2Fmarkets").status_code in (400, 404)
    assert client.get("/api/live/markets/selected?marketids=1;DROP").status_code == 400
    r = client.post("/api/live/materialize",
                    json={"event_id": "1 OR 1=1", "market_id": "x",
                          "runner_id": "y", "side": "back"})
    assert r.status_code == 400
    # Upstream error text never leaks, even when the exception carries it.
    orig = live_feed.fetch_json
    live_feed.fetch_json = lambda path: (_ for _ in ()).throw(
        live_feed.LiveFeedError("GET https://internal-host/secret 500"))
    try:
        data = client.get("/api/live/current").get_json()
        assert "internal-host" not in data.get("error", "")
        assert data["error"] == "Live feed unavailable."
    finally:
        live_feed.fetch_json = orig


def test_security_headers(client):
    r = client.get("/")
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"
    assert r.headers["X-XSS-Protection"] == "1; mode=block"
    assert r.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"


def test_max_stake_enforced(client, app):
    admin = wrap(app.test_client())
    _admin(admin)
    _mk_player(admin, "maxp", 10_000_000)
    _login(client, "maxp")
    mk, sel = _bookmaker(client)
    r = client.post("/api/bets", json={"match_id": 1, "market_id": mk["id"],
                                       "selection_id": sel["id"], "side": "back",
                                       "stake": mk["max_stake"] + 1})
    assert r.status_code == 400
    assert "max" in r.get_json()["error"]


def test_bet_after_settle_rejected_and_settle_twice_pays_once(client, app):
    admin = wrap(app.test_client())
    _admin(admin)
    _mk_player(admin, "settp", 5000)
    _login(client, "settp")
    mk, sel = _bookmaker(client)
    r = client.post("/api/bets", json={"match_id": 1, "market_id": mk["id"],
                                       "selection_id": sel["id"], "side": "back", "stake": 10})
    assert r.status_code == 200
    winner = sel["name"]
    r = admin.post(f"/api/admin/markets/{mk['id']}/settle", json={"winner": winner})
    assert r.status_code == 200
    bal_after = client.get("/api/me").get_json()["user"]["balance"]
    # Second settle: refused, balances unchanged.
    assert admin.post(f"/api/admin/markets/{mk['id']}/settle",
                      json={"winner": winner}).status_code == 400
    assert client.get("/api/me").get_json()["user"]["balance"] == bal_after
    # A bet on the settled market: refused, exposure unchanged.
    me = client.get("/api/me").get_json()["user"]
    r = client.post("/api/bets", json={"match_id": 1, "market_id": mk["id"],
                                       "selection_id": sel["id"], "side": "back", "stake": 10})
    assert r.status_code == 400
    assert client.get("/api/me").get_json()["user"]["exposure"] == me["exposure"]


def test_concurrent_admin_deduct_bounded(app, client):
    admin = wrap(app.test_client())
    _admin(admin)
    _mk_player(admin, "dedp", 100)
    _login(client, "dedp")
    pid = client.get("/api/me").get_json()["user"]["id"]

    def deduct_pid(c):
        return c.post(f"/api/admin/players/{pid}/deduct-credit", json={"amount": 60})

    res = _burst_admin(app, deduct_pid, n=6)
    ok = sum(1 for r in res if not isinstance(r, Exception) and r.status_code == 200)
    assert ok == 1, [getattr(r, "status_code", repr(r)) for r in res]
    assert client.get("/api/me").get_json()["user"]["balance"] == 40.0


def _burst_admin(app, fn, n=6):
    bar = threading.Barrier(n)
    results = [None] * n

    def go(i):
        c = wrap(app.test_client())
        _login(c, "admin", "admin123")
        bar.wait(timeout=30)
        try:
            results[i] = fn(c)
        except Exception as e:  # noqa: BLE001
            results[i] = e

    threads = [threading.Thread(target=go, args=(i,)) for i in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)
    return results


def test_resume_endpoints_hide_secrets(client):
    _reg(client, "hideme")
    g = client.post("/api/casino/mines/start", json={"stake": 10, "mines": 3}).get_json()
    st = client.get("/api/casino/mines/state").get_json()
    assert st["open"] is True and "mines" not in st
    d = client.post("/api/casino/blackjack/deal", json={"stake": 10}).get_json()
    if not d.get("settled"):
        st = client.get("/api/casino/blackjack/state").get_json()
        assert st["open"] is True and len(st["dealer"]) == 1 and st["dealer_hidden"] is True
    d = client.post("/api/casino/videopoker/deal", json={"stake": 10}).get_json()
    st = client.get("/api/casino/videopoker/state").get_json()
    assert st["open"] is True and "deck" not in st
    assert client.get("/api/casino/tower/state").get_json() == {"open": False}
