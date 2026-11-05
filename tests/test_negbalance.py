"""Negative-balance / near-zero-balance audit (follow-up 2026-11-03).

Every test names the boundary it pins. Money must never go negative,
exposure must never exceed balance, and a broke user must get a clean
rejection — never a free round, a partial bet, or a stuck state.
"""
import sys, os
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import app as appmod
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


def _player(app, admin, username, credit):
    p = _mk_player(admin, username, credit)
    c = wrap(app.test_client())
    _login(c, username, "password12")
    return c, p


def _me(c):
    return c.get("/api/me").get_json()["user"]


def _bookmaker(c):
    m = c.get("/api/matches/1").get_json()
    mk = next(x for x in m["markets"] if x["kind"] == "bookmaker")
    return mk, mk["selections"][0], mk["selections"][1]


def _fancy(c):
    m = c.get("/api/matches/1").get_json()
    mk = next(x for x in m["markets"] if x["kind"] == "fancy")
    yes = next(s for s in mk["selections"] if s["name"] == "Yes")
    no = next(s for s in mk["selections"] if s["name"] == "No")
    return mk, yes, no


def _bet(c, mk, sel, side, stake):
    return c.post("/api/bets", json={
        "match_id": 1, "market_id": mk["id"], "selection_id": sel["id"],
        "side": side, "stake": stake})


def _deduct(admin, pid, amount):
    return admin.post(f"/api/admin/players/{pid}/deduct-credit", json={"amount": amount})


def _add(admin, pid, amount):
    return admin.post(f"/api/admin/players/{pid}/add-credit", json={"amount": amount})


def _burst(app, logins, fn, n):
    """Run fn(client) on n threads, barrier-synced. logins: list of
    (username, password) per thread."""
    bar = threading.Barrier(n)
    results = [None] * n

    def go(i):
        c = wrap(app.test_client())
        _login(c, *logins[i])
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


def card(rank, suit="♠"):
    return {"rank": rank, "suit": suit}


def deck_factory(monkeypatch, decks):
    queue = [[dict(c) for c in d] for d in decks]

    def _factory():
        assert queue, "deck factory exhausted"
        return queue.pop(0)

    monkeypatch.setattr(appmod, "_cards_new_deck", _factory)


# ---------------- case 1: zero balance ----------------

def test_zero_balance_bet_rejected(app, client):
    a = _admin(client)
    p, _ = _player(app, client, "broke1", 100)
    assert _deduct(client, _["id"], 100).status_code == 200
    assert _me(p)["balance"] == 0.0
    mk, winner, _loser = _bookmaker(p)
    r = _bet(p, mk, winner, "back", 10)
    assert r.status_code == 400, r.get_json()
    assert _me(p)["balance"] == 0.0 and _me(p)["exposure"] == 0.0
    assert p.get("/api/bets?status=unsettled").get_json() == []


def test_zero_balance_casino_rejected(app, client):
    a = _admin(client)
    p, _ = _player(app, client, "broke2", 100)
    assert _deduct(client, _["id"], 100).status_code == 200
    for path, body in [
        ("/api/casino/limbo", {"stake": 10, "target": 2}),
        ("/api/casino/mines/start", {"stake": 10, "mines": 3}),
        ("/api/casino/blackjack/deal", {"stake": 10}),
        ("/api/casino/tower/start", {"stake": 10}),
    ]:
        r = p.post(path, json=body)
        assert r.status_code == 400, (path, r.get_json())
    assert _me(p)["balance"] == 0.0


def test_zero_balance_me_clean(app, client):
    a = _admin(client)
    p, _ = _player(app, client, "broke3", 100)
    assert _deduct(client, _["id"], 100).status_code == 200
    me = _me(p)
    assert me["balance"] == 0.0 and me["available"] == 0.0 and me["exposure"] == 0.0
    assert client.get("/").status_code == 200


# ---------------- case 2: exact boundaries ----------------

def test_back_stake_exact_balance(app, client):
    a = _admin(client)
    p, _ = _player(app, client, "edge1", 100)
    mk, winner, _ = _bookmaker(p)
    r = _bet(p, mk, winner, "back", 100)
    assert r.status_code == 200, r.get_json()
    assert _me(p)["exposure"] == 100.0 and _me(p)["available"] == 0.0
    assert _bet(p, mk, winner, "back", 0.01).status_code == 400


def test_back_stake_one_cent_over_balance(app, client):
    a = _admin(client)
    p, _ = _player(app, client, "edge2", 99.99)
    mk, winner, _ = _bookmaker(p)
    assert _bet(p, mk, winner, "back", 100).status_code == 400
    assert _me(p)["balance"] == 99.99 and _me(p)["exposure"] == 0.0


def test_lay_liability_exact_boundary(app, client):
    a = _admin(client)
    probe, _ = _player(app, client, "edgeprobe", 100)
    mk, winner, _ = _bookmaker(probe)
    r = _bet(probe, mk, winner, "lay", 10)
    assert r.status_code == 200
    liability = r.get_json()["liability"]
    assert liability > 0
    # A player whose whole balance equals the liability may lay exactly.
    p, _ = _player(app, client, "edge3", liability)
    r2 = _bet(p, mk, winner, "lay", 10)
    assert r2.status_code == 200, r2.get_json()
    assert _me(p)["available"] == 0.0
    # One cent less balance and the same lay must fail.
    q, _ = _player(app, client, "edge4", round(liability - 0.01, 2))
    assert _bet(q, mk, winner, "lay", 10).status_code == 400
    assert _me(q)["exposure"] == 0.0


def test_spendable_boundary_with_open_exposure(app, client):
    a = _admin(client)
    p, _ = _player(app, client, "edge5", 100)
    mk, winner, _ = _bookmaker(p)
    assert _bet(p, mk, winner, "back", 60).status_code == 200
    assert _me(p)["available"] == 40.0
    # Casino: exactly spendable ok, one cent over rejected.
    assert p.post("/api/casino/limbo", json={"stake": 40.01, "target": 2}).status_code == 400
    # Sportsbook: exactly spendable ok (back 40 -> exposure 100).
    assert _bet(p, mk, winner, "back", 40).status_code == 200
    assert _me(p)["available"] == 0.0
    assert _bet(p, mk, winner, "back", 0.01).status_code == 400
    assert p.post("/api/casino/limbo", json={"stake": 0.01, "target": 2}).status_code == 400


# ---------------- case 3: exposure stacking ----------------

def test_exposure_stacking_sequential(app, client):
    a = _admin(client)
    p, _ = _player(app, client, "stack1", 100)
    mk, winner, _ = _bookmaker(p)
    assert _bet(p, mk, winner, "back", 60).status_code == 200
    assert _bet(p, mk, winner, "back", 60).status_code == 400
    assert _me(p)["exposure"] == 60.0
    assert _bet(p, mk, winner, "back", 40).status_code == 200
    assert _me(p)["exposure"] == 100.0
    assert _bet(p, mk, winner, "back", 0.01).status_code == 400
    assert _me(p)["exposure"] == 100.0


def test_concurrent_bets_exact_boundary(app, client):
    a = _admin(client)
    p, _ = _player(app, client, "race1", 100)
    mk, winner, _ = _bookmaker(p)
    results = _burst(app, [("race1", "password12")] * 10,
                     lambda c: _bet(c, mk, winner, "back", 60), 10)
    oks = [r for r in results if not isinstance(r, Exception) and r.status_code == 200]
    assert len(oks) == 1, [getattr(r, "status_code", r) for r in results]
    # Fresh login to read final state (burst clients are thread-local).
    p2 = wrap(app.test_client())
    _login(p2, "race1", "password12")
    assert _me(p2)["exposure"] == 60.0 and _me(p2)["balance"] == 100.0
    # Two simultaneous full-balance bets: exactly one wins.
    q, _ = _player(app, client, "race2", 100)
    results = _burst(app, [("race2", "password12")] * 2,
                     lambda c: _bet(c, mk, winner, "back", 100), 2)
    oks = [r for r in results if not isinstance(r, Exception) and r.status_code == 200]
    assert len(oks) == 1
    q2 = wrap(app.test_client())
    _login(q2, "race2", "password12")
    assert _me(q2)["exposure"] == 100.0


# ---------------- case 4: settlement vs reduced balance ----------------

def test_settle_back_loss_after_max_deduct(app, client):
    a = _admin(client)
    p, pv = _player(app, client, "settle1", 100)
    mk, _winner, loser = _bookmaker(p)
    assert _bet(p, mk, loser, "back", 60).status_code == 200
    assert _deduct(client, pv["id"], 40).status_code == 200
    assert _me(p)["balance"] == 60.0 and _me(p)["exposure"] == 60.0
    s = p.post("/api/matches/1/settle")
    assert s.status_code == 200, s.get_json()
    assert _me(p)["balance"] == 0.0 and _me(p)["exposure"] == 0.0


def test_settle_lay_loss_after_max_deduct(app, client):
    a = _admin(client)
    probe, _ = _player(app, client, "settleprobe", 100)
    mk, winner, _ = _bookmaker(probe)
    r = _bet(probe, mk, winner, "lay", 10)
    liability = r.get_json()["liability"]
    p, pv = _player(app, client, "settle2", 100)
    assert _bet(p, mk, winner, "lay", 10).status_code == 200
    assert _deduct(client, pv["id"], round(100 - liability, 2)).status_code == 200
    assert _me(p)["balance"] == liability and _me(p)["exposure"] == liability
    s = p.post("/api/matches/1/settle")
    assert s.status_code == 200
    # Laying the winner loses the liability: balance lands exactly on 0.
    assert _me(p)["balance"] == 0.0 and _me(p)["exposure"] == 0.0


def test_settle_win_after_max_deduct(app, client):
    a = _admin(client)
    p, pv = _player(app, client, "settle3", 100)
    mk, winner, _ = _bookmaker(p)
    r = _bet(p, mk, winner, "back", 60)
    odds = r.get_json()["odds"]
    assert _deduct(client, pv["id"], 40).status_code == 200
    s = p.post("/api/matches/1/settle")
    assert s.status_code == 200
    assert _me(p)["balance"] == round(60 + 60 * (odds - 1), 2)
    assert _me(p)["exposure"] == 0.0


def test_casino_drain_then_settle_loss_never_negative(app, client):
    a = _admin(client)
    p, pv = _player(app, client, "settle4", 100)
    mk, _winner, loser = _bookmaker(p)
    assert _bet(p, mk, loser, "back", 60).status_code == 200
    # Casino may take at most the 40 spendable; win or lose, the
    # balance afterwards is >= exposure (60), so the losing settle
    # below can never push it below zero.
    assert p.post("/api/casino/limbo", json={"stake": 41, "target": 2}).status_code == 400
    r = p.post("/api/casino/limbo", json={"stake": 40, "target": 2})
    assert r.status_code == 200
    assert _me(p)["balance"] >= 60.0
    s = p.post("/api/matches/1/settle")
    assert s.status_code == 200
    assert _me(p)["balance"] >= 0.0 and _me(p)["exposure"] == 0.0


def test_admin_settle_market_loss_after_max_deduct(app, client):
    a = _admin(client)
    p, pv = _player(app, client, "settle5", 100)
    mk, _winner, loser = _bookmaker(p)
    assert _bet(p, mk, loser, "back", 60).status_code == 200
    assert _deduct(client, pv["id"], 40).status_code == 200
    r = client.post(f"/api/admin/markets/{mk['id']}/settle",
                    json={"winner": "Kirtipur Kings"})
    assert r.status_code == 200, r.get_json()
    assert _me(p)["balance"] == 0.0 and _me(p)["exposure"] == 0.0


def test_fancy_loss_after_max_deduct(app, client):
    a = _admin(client)
    p, pv = _player(app, client, "settle6", 100)
    mk, _yes, no = _fancy(p)
    assert _bet(p, mk, no, "back", 60).status_code == 200
    assert _deduct(client, pv["id"], 40).status_code == 200
    s = p.post("/api/matches/1/settle")
    assert s.status_code == 200
    assert _me(p)["balance"] == 0.0 and _me(p)["exposure"] == 0.0


def test_void_settlement_releases_exposure(app, client):
    a = _admin(client)
    p, pv = _player(app, client, "settle7", 100)
    mk, winner, _ = _bookmaker(p)
    assert _bet(p, mk, winner, "back", 60).status_code == 200
    r = client.post(f"/api/admin/markets/{mk['id']}/settle", json={"winner": "VOID"})
    assert r.status_code == 200, r.get_json()
    assert _me(p)["balance"] == 100.0 and _me(p)["exposure"] == 0.0


# ---------------- case 5: mid-round extra stake ----------------

def test_bj_double_boundary(app, client, monkeypatch):
    # Deterministic shoe: player 5+6=11, dealer 7+10=17, next card 2.
    # (A random deal could be an immediate blackjack, which settles
    # at deal time and leaves no hand to double -- that flaked this
    # test once in the full suite.)
    def bj_shoe():
        return [dict(c) for c in
                [card("5"), card("6"), card("7"), card("10"), card("2"), card("3")]
                + [card("4")] * 300]
    monkeypatch.setattr(appmod, "_bj_new_shoe", bj_shoe)
    a = _admin(client)
    p, _ = _player(app, client, "bj1", 10)
    d = p.post("/api/casino/blackjack/deal", json={"stake": 10}).get_json()
    assert d["settled"] is False
    assert _me(p)["balance"] == 0.0
    assert p.post("/api/casino/blackjack/double",
                  json={"game_id": d["game_id"]}).status_code == 400
    # Hand is still open and playable: standing closes it cleanly.
    assert p.post("/api/casino/blackjack/stand",
                  json={"game_id": d["game_id"]}).status_code == 200
    assert _me(p)["balance"] >= 0.0
    q, _ = _player(app, client, "bj2", 20)
    d = q.post("/api/casino/blackjack/deal", json={"stake": 10}).get_json()
    assert d["settled"] is False
    r = q.post("/api/casino/blackjack/double", json={"game_id": d["game_id"]}).get_json()
    # Double settles immediately: pre-double balance 10, extra 10
    # deducted, then the payout lands -- so balance == payout exactly.
    # (A free double would leave 10 + payout instead.)
    assert _me(q)["balance"] == r["payout"]


def test_war_raise_boundary(app, client, monkeypatch):
    a = _admin(client)
    p, _ = _player(app, client, "war1", 10)
    deck_factory(monkeypatch, [
        [card("K"), card("K", "♥")] + [card("5")] * 50])
    d = p.post("/api/casino/war/deal", json={"stake": 10}).get_json()
    assert d["tie"] is True
    assert p.post("/api/casino/war/go", json={"game_id": d["game_id"]}).status_code == 400
    assert _me(p)["balance"] == 0.0
    q, _ = _player(app, client, "war2", 20)
    deck_factory(monkeypatch, [
        [card("K"), card("K", "♥"), card("2", "♣"), card("3", "♣"), card("4", "♣"),
         card("A"), card("2")] + [card("5")] * 45])
    d = q.post("/api/casino/war/deal", json={"stake": 10}).get_json()
    assert d["tie"] is True
    r = q.post("/api/casino/war/go", json={"game_id": d["game_id"]}).get_json()
    assert _me(q)["balance"] == 0.0 + r["payout"]


def test_reddog_raise_boundary(app, client, monkeypatch):
    a = _admin(client)
    p, _ = _player(app, client, "rd1", 10)
    deck_factory(monkeypatch, [
        [card("5"), card("9"), card("7")] + [card("2")] * 49])
    d = p.post("/api/casino/reddog/deal", json={"stake": 10}).get_json()
    assert d["settled"] is False
    assert p.post("/api/casino/reddog/raise",
                  json={"game_id": d["game_id"]}).status_code == 400
    assert _me(p)["balance"] == 0.0
    q, _ = _player(app, client, "rd2", 20)
    deck_factory(monkeypatch, [
        [card("5"), card("9"), card("7")] + [card("2")] * 49])
    d = q.post("/api/casino/reddog/deal", json={"stake": 10}).get_json()
    r = q.post("/api/casino/reddog/raise", json={"game_id": d["game_id"]}).get_json()
    assert _me(q)["balance"] == 20 - 20 + r["payout"]


def test_tower_climb_costs_nothing_extra(app, client):
    a = _admin(client)
    p, _ = _player(app, client, "tower1", 10)
    d = p.post("/api/casino/tower/start", json={"stake": 10}).get_json()
    assert _me(p)["balance"] == 0.0
    r = p.post("/api/casino/tower/climb", json={"game_id": d["game_id"]})
    assert r.status_code == 200, r.get_json()
    assert _me(p)["balance"] == 0.0  # climb risks the original stake only


# ---------------- case 6: dust amounts ----------------

def test_dust_sportsbook_rejected(app, client):
    a = _admin(client)
    p, _ = _player(app, client, "dust1", 100)
    mk, winner, _ = _bookmaker(p)
    for stake in (0.001, 0.005, 0.009, 0, -5):
        assert _bet(p, mk, winner, "back", stake).status_code == 400, stake
    assert _me(p)["balance"] == 100.0 and _me(p)["exposure"] == 0.0
    assert p.get("/api/bets?status=unsettled").get_json() == []


def test_dust_casino_rejected(app, client):
    a = _admin(client)
    p, _ = _player(app, client, "dust2", 100)
    for stake in (0.001, 0.005, 0.009, 0, -5):
        r = p.post("/api/casino/limbo", json={"stake": stake, "target": 2})
        assert r.status_code == 400, (stake, r.get_json())
    assert _me(p)["balance"] == 100.0


def test_dust_admin_amounts_rejected(app, client):
    a = _admin(client)
    p, pv = _player(app, client, "dust3", 100)
    assert _add(client, pv["id"], 0.001).status_code == 400
    assert _deduct(client, pv["id"], 0.001).status_code == 400
    assert _add(client, pv["id"], 0).status_code == 400
    assert _add(client, pv["id"], -50).status_code == 400
    assert _me(p)["balance"] == 100.0


def test_cent_precision_ledger_over_many_rounds(app, client):
    a = _admin(client)
    p, _ = _player(app, client, "dust4", 100)
    for _ in range(30):
        r = p.post("/api/casino/limbo", json={"stake": 0.01, "target": 2})
        assert r.status_code == 200
    me = _me(p)
    stmt = p.get("/api/statement").get_json()
    assert stmt, "statement must record the rounds"
    assert round(stmt[0]["balance_after"], 2) == me["balance"]
    assert me["balance"] >= 0.0
    assert all(t["amount"] == round(t["amount"], 2) for t in stmt)


# ---------------- case 7: admin / sub-admin credit paths ----------------

def test_admin_deduct_guards(app, client):
    a = _admin(client)
    p, pv = _player(app, client, "adm1", 100)
    mk, winner, _ = _bookmaker(p)
    assert _bet(p, mk, winner, "back", 60).status_code == 200
    assert _deduct(client, pv["id"], 41).status_code == 400  # below exposure
    assert _deduct(client, pv["id"], 40).status_code == 200  # exactly to exposure
    assert _me(p)["balance"] == 60.0 and _me(p)["exposure"] == 60.0
    assert _deduct(client, pv["id"], 0.01).status_code == 400
    assert _deduct(client, pv["id"], 60).status_code == 400  # would go below exposure
    q, qv = _player(app, client, "adm2", 100)
    assert _deduct(client, qv["id"], 100.01).status_code == 400
    assert _deduct(client, qv["id"], 100).status_code == 200
    assert _me(q)["balance"] == 0.0


def test_concurrent_deduct_burst(app, client):
    a = _admin(client)
    p, pv = _player(app, client, "adm3", 100)
    pid = pv["id"]
    results = _burst(app, [("admin", "admin123")] * 10,
                     lambda c: c.post(f"/api/admin/players/{pid}/deduct-credit",
                                      json={"amount": 60}), 10)
    oks = [r for r in results if not isinstance(r, Exception) and r.status_code == 200]
    assert len(oks) == 1, [getattr(r, "status_code", r) for r in results]
    p2 = wrap(app.test_client())
    _login(p2, "adm3", "password12")
    assert _me(p2)["balance"] == 40.0


def test_concurrent_deduct_vs_bet_exactly_one_wins(app, client):
    a = _admin(client)
    p, pv = _player(app, client, "adm4", 100)
    mk, winner, _ = _bookmaker(p)
    pid = pv["id"]
    bar = threading.Barrier(2)
    out = [None, None]

    def admin_side():
        c = wrap(app.test_client())
        _login(c, "admin", "admin123")
        bar.wait(timeout=30)
        out[0] = c.post(f"/api/admin/players/{pid}/deduct-credit", json={"amount": 60})

    def bet_side():
        c = wrap(app.test_client())
        _login(c, "adm4", "password12")
        bar.wait(timeout=30)
        out[1] = _bet(c, mk, winner, "back", 60)

    ts = [threading.Thread(target=admin_side), threading.Thread(target=bet_side)]
    for t in ts:
        t.start()
    for t in ts:
        t.join(timeout=60)
    codes = sorted(r.status_code for r in out)
    assert codes == [200, 400], codes
    p2 = wrap(app.test_client())
    _login(p2, "adm4", "password12")
    me = _me(p2)
    # Either the deduct won (40/0) or the bet won (100/60) -- never both.
    assert (me["balance"], me["exposure"]) in [(40.0, 0.0), (100.0, 60.0)], me
    assert me["balance"] - me["exposure"] >= 0


def test_credit_suspended_user_cannot_play(app, client):
    a = _admin(client)
    p, pv = _player(app, client, "adm5", 100)
    assert client.post(f"/api/admin/players/{pv['id']}/suspend").status_code == 200
    # Crediting a suspended account is an admin action, not a user
    # exploit -- but the money must stay unusable while suspended.
    r = _add(client, pv["id"], 50)
    assert r.status_code == 200, r.get_json()
    mk, winner, _ = _bookmaker(p)
    assert _bet(p, mk, winner, "back", 10).status_code in (401, 403)
    assert p.post("/api/casino/limbo", json={"stake": 10, "target": 2}).status_code in (401, 403)


# ---------------- case 8: quick stakes / set-stake ----------------

def test_quick_stake_above_balance_rejected(app, client):
    a = _admin(client)
    p, _ = _player(app, client, "qs1", 50)
    r = p.post("/api/me/stakes", json={"quick_stakes": [100, 500, 1000, 5000, 10000, 50000]})
    assert r.status_code == 200
    mk, winner, _ = _bookmaker(p)
    assert _bet(p, mk, winner, "back", 100).status_code == 400
    assert _me(p)["balance"] == 50.0
    assert p.get("/api/bets?status=unsettled").get_json() == []


def test_set_stakes_dust_rejected(app, client):
    a = _admin(client)
    p, _ = _player(app, client, "qs2", 100)
    r = p.post("/api/me/stakes", json={"quick_stakes": [0.001, 100, 500, 1000, 5000, 10000]})
    assert r.status_code == 400
    assert p.get("/api/me").get_json()["user"]["quick_stakes"] == [100, 500, 1000, 5000, 10000, 50000]


# ---------------- case 9: free-entry value extraction ----------------

def test_zero_balance_free_entry_all_rejected(app, client):
    a = _admin(client)
    p, _ = _player(app, client, "free1", 100)
    assert _deduct(client, _["id"], 100).status_code == 200
    assert p.post("/api/casino/slots/free-spin", json={}).status_code == 400
    assert p.post("/api/casino/telefly/bet", json={"stake": 10}).status_code == 400
    assert p.post("/api/casino/pvp/bet", json={"stake": 10}).status_code == 400
    assert p.post("/api/casino/lottery/buy", json={"stake": 10}).status_code == 400
    assert _me(p)["balance"] == 0.0


def test_free_spin_without_pending_rejected(app, client):
    a = _admin(client)
    p, _ = _player(app, client, "free2", 100)
    assert p.post("/api/casino/slots/free-spin", json={}).status_code == 400
    assert _me(p)["balance"] == 100.0


def test_public_registration_removed(client):
    # Self-registration is gone (see test_security.py): the endpoint
    # must 404 and create nothing, however often it is hit.
    for i in range(5):
        assert client.post("/api/auth/register",
                           json={"username": f"gone{i}", "password": "password12"}).status_code == 404
    assert client.post("/api/auth/login",
                       json={"username": "gone0", "password": "password12"}).status_code == 401



def test_ledger_reconciliation_mixed_flows(app, client):
    a = _admin(client)
    p, pv = _player(app, client, "led1", 100)
    assert _add(client, pv["id"], 50).status_code == 200
    mk, winner, _ = _bookmaker(p)
    assert _bet(p, mk, winner, "back", 60).status_code == 200
    assert p.post("/api/casino/limbo", json={"stake": 10, "target": 2}).status_code == 200
    me = _me(p)
    assert me["balance"] >= 0.0 and me["exposure"] == 60.0
    s = p.post("/api/matches/1/settle")
    assert s.status_code == 200
    me = _me(p)
    assert me["exposure"] == 0.0 and me["balance"] >= 0.0
    stmt = p.get("/api/statement").get_json()
    assert stmt and round(stmt[0]["balance_after"], 2) == me["balance"]
    assert all(t["balance_after"] >= 0 for t in stmt)
    assert all(t["amount"] == round(t["amount"], 2) for t in stmt)
    unsettled = p.get("/api/bets?status=unsettled").get_json()
    assert unsettled == []
