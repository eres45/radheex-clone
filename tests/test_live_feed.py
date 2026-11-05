"""Tests for the live delayed feed: book parser, proxy routes, cache,
materialized live bets. Upstream responses are stubbed -- no test here
touches the network, except through the stubbed fetch function."""
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
def client(tmp_path):
    live_feed.clear_cache()
    app = create_app({"DATABASE": str(tmp_path / "test.db"), "TESTING": True})
    with app.test_client() as c:
        yield wrap(c)


def login_demo(client):
    r = client.post("/api/auth/login", json={"username": "demo", "password": "demo123"})
    assert r.status_code == 200


# ---------------- parser ----------------

def test_parse_ladder():
    assert live_feed.parse_ladder("2.8:15.43:*2.78:48.79:*2.76:52.13:") == [
        (2.8, 15.43), (2.78, 48.79), (2.76, 52.13)]
    assert live_feed.parse_ladder("") == []
    assert live_feed.parse_ladder("2.5:10:") == [(2.5, 10.0)]
    # Malformed pairs are skipped, never fatal.
    assert live_feed.parse_ladder("abc:10:*2.0:xx:*2.5:20:") == [(2.5, 20.0)]


def test_parse_book_active_runners():
    book = ("1.264742339|0|OPEN|False|11/03/2026 04:26:13|1793681599729|False|"
            "48350~ACTIVE~2.8:15.43:*2.78:48.79:*2.76:52.13:~2.82:41.56:*2.84:227.05:*2.86:602.03:,"
            "69720~ACTIVE~2.84:2.17:~2.86:42.68:")
    market_id, runners = live_feed.parse_book(book)
    assert market_id == "1.264742339"
    assert runners["48350"]["status"] == "ACTIVE"
    assert runners["48350"]["back"][0] == (2.8, 15.43)
    assert runners["48350"]["lay"][0] == (2.82, 41.56)
    assert len(runners["48350"]["back"]) == 3


def test_parse_book_suspended_runners_have_empty_ladders():
    book = ("43909778|0|OPEN|True|11/02/2026 04:21:13|1793593304807|True|"
            "47454453~SUSPENDED~~,47454454~SUSPENDED~~")
    market_id, runners = live_feed.parse_book(book)
    assert market_id == "43909778"
    assert runners["47454453"]["status"] == "SUSPENDED"
    assert runners["47454453"]["back"] == []
    assert runners["47454453"]["lay"] == []
    assert runners["47454453"]["line"] is None


def test_parse_book_missing_and_malformed():
    assert live_feed.parse_book(None) == (None, {})
    assert live_feed.parse_book("") == (None, {})
    assert live_feed.parse_book("garbage without pipes") == (None, {})
    # Entry without '~' is skipped; the good one still parses.
    _, runners = live_feed.parse_book("9|0|OPEN|F|t|1|F|nonsense,5~ACTIVE~2.0:10:~2.2:5:")
    assert list(runners) == ["5"]
    assert runners["5"]["back"] == [(2.0, 10.0)]


def test_parse_books_variants():
    book = "9|0|OPEN|F|t|1|F|5~ACTIVE~2.0:10:~2.2:5:"
    parsed = live_feed.parse_books(book)
    assert parsed["9"]["5"]["back"] == [(2.0, 10.0)]
    assert parsed["9"]["5"]["lay"] == [(2.2, 5.0)]
    assert parsed["9"]["5"]["line"] is None
    assert live_feed.parse_books({"9": book})["9"]["5"]["back"] == [(2.0, 10.0)]
    assert live_feed.parse_books([book])["9"]["5"]["lay"] == [(2.2, 5.0)]
    assert live_feed.parse_books("") == {}
    assert live_feed.parse_books(None) == {}


def test_parse_event_item_from_sample():
    items = load_sample("current.json")
    ev = live_feed.parse_event_item(items[0])
    assert ev["event_name"] == "Blackburn v Stoke"
    assert ev["sport"] == "Soccer"
    assert ev["competition"] == "English Championship"
    assert ev["market"]["market_name"] == "Match Odds"
    runners = {r["name"]: r for r in ev["market"]["runners"]}
    assert runners["Blackburn"]["best_back"] == 2.8
    assert runners["Blackburn"]["best_lay"] == 2.82
    assert runners["Stoke"]["best_back"] == 2.84


def test_parse_event_detail_from_sample_attaches_its_own_books():
    # The soccer sample's books were always a JSON-encoded dict string
    # with real prices; the old line-split parser just could not read
    # them (it produced a garbage market id and no prices).
    detail = live_feed.parse_event_detail(load_sample("detail_soccer.json"))
    assert detail["event_name"] == "Chapecoense v Mirassol"
    assert len(detail["markets"]) == 4
    assert detail["markets"][0]["market_type"] == "MATCH_ODDS"
    runners = {r["name"]: r for r in detail["markets"][0]["runners"]}
    assert runners["Chapecoense"]["best_back"] == 3.65
    assert runners["Chapecoense"]["best_lay"] == 3.85


def test_parse_event_detail_attaches_books_when_present():
    detail = load_sample("detail_soccer.json")
    detail["metadata"]["books"] = (
        "1.264507448|0|OPEN|False|11/03/2026 04:26:13|1|False|"
        "2909511~ACTIVE~2.5:100:*2.4:50:~2.6:80:*2.7:60:,"
        "2760854~ACTIVE~3.0:50:~3.2:40:,"
        "58805~ACTIVE~3.4:70:~3.5:60:")
    parsed = live_feed.parse_event_detail(detail)
    runners = {r["name"]: r for r in parsed["markets"][0]["runners"]}
    assert runners["Chapecoense"]["best_back"] == 2.5
    assert runners["Chapecoense"]["best_lay"] == 2.6
    assert runners["Mirassol"]["best_back"] == 3.0


# ---------------- proxy routes (stubbed upstream) ----------------

def _stub_fetch(monkeypatch, payload):
    monkeypatch.setattr(live_feed, "fetch_json", lambda path: payload)


def test_live_current_uses_parsed_feed(client, monkeypatch):
    _stub_fetch(monkeypatch, load_sample("current.json"))
    r = client.get("/api/live/current")
    assert r.status_code == 200
    data = r.get_json()
    assert data["source"] == "live-delayed"
    assert data["events"][0]["event_name"] == "Blackburn v Stoke"
    assert len(data["events"]) == 18


def test_live_markets_and_selected(client, monkeypatch):
    _stub_fetch(monkeypatch, load_sample("markets_all.json"))
    data = client.get("/api/live/markets").get_json()
    assert data["source"] == "live-delayed"
    assert len(data["events"]) == 67
    _stub_fetch(monkeypatch, load_sample("markets_selected.json"))
    data = client.get("/api/live/markets/selected?marketids=1.264742339").get_json()
    assert len(data["events"]) == 1
    assert data["events"][0]["event_name"] == "Blackburn v Stoke"
    assert client.get("/api/live/markets/selected").status_code == 400


def test_live_eventtype_validation_and_empty_seven(client, monkeypatch):
    assert client.get("/api/live/eventtype/9").status_code == 400
    assert client.get("/api/live/eventtype/3").status_code == 400
    _stub_fetch(monkeypatch, [])
    data = client.get("/api/live/eventtype/7").get_json()
    assert data["source"] == "live-delayed"
    assert data["events"] == []


def test_live_event_detail_and_upstream_error(client, monkeypatch):
    _stub_fetch(monkeypatch, load_sample("detail_soccer.json"))
    data = client.get("/api/live/event/36239536").get_json()
    assert data["source"] == "live-delayed"
    assert data["event"]["event_name"] == "Chapecoense v Mirassol"
    assert len(data["event"]["markets"]) == 4

    def boom(path):
        raise live_feed.LiveFeedError("boom")
    monkeypatch.setattr(live_feed, "fetch_json", boom)
    r = client.get("/api/live/event/36239536")
    assert r.status_code == 502
    assert r.get_json()["source"] == "live-error"


def test_live_list_falls_back_to_simulated_on_failure(client, monkeypatch):
    def boom(path):
        raise live_feed.LiveFeedError("boom")
    monkeypatch.setattr(live_feed, "fetch_json", boom)
    data = client.get("/api/live/current").get_json()
    assert data["source"] == "simulated-fallback"
    # Security audit: upstream error text must never reach clients --
    # the fallback carries a generic message even when the upstream
    # raised a detailed exception.
    assert data["error"] == "Live feed unavailable."
    assert "boom" not in data["error"]
    assert len(data["events"]) == 7  # seeded demo matches
    assert all(e["event_id"].startswith("sim-") for e in data["events"])


def test_live_cache_avoids_repeat_upstream_calls(client, monkeypatch):
    calls = []

    class FakeResp:
        def __init__(self, payload):
            self._payload = payload

        def read(self):
            return json.dumps(self._payload).encode()

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    def fake_urlopen(req, timeout=None):
        calls.append(req.full_url)
        return FakeResp(load_sample("current.json"))

    monkeypatch.setattr("live_feed.urllib.request.urlopen", fake_urlopen)
    live_feed.fetch_json("markets/current")
    live_feed.fetch_json("markets/current")
    assert len(calls) == 1
    live_feed.clear_cache()
    live_feed.fetch_json("markets/current")
    assert len(calls) == 2


# ---------------- materialized live bets ----------------

def _detail_with_books():
    detail = load_sample("detail_soccer.json")
    detail["metadata"]["books"] = (
        "1.264507448|0|OPEN|False|11/03/2026 04:26:13|1|False|"
        "2909511~ACTIVE~2.5:100:*2.4:50:~2.6:80:*2.7:60:,"
        "2760854~ACTIVE~3.0:50:~3.2:40:,"
        "58805~ACTIVE~3.4:70:~3.5:60:")
    return detail


def _selected_item_for_detail_market():
    """A selected-lookup payload for the detail sample's Match Odds
    market (1.264507448), carrying the prices the detail books lack."""
    return [{
        "eventType": {"id": "1", "name": "Soccer"},
        "competition": {"id": "13", "name": "Brazilian Serie A"},
        "event": {"id": "36239536", "name": "Chapecoense v Mirassol",
                 "openDate": "2026-11-03T22:30:00Z"},
        "catalogue": {
            "marketId": "1.264507448", "marketType": "MATCH_ODDS",
            "marketName": "Match Odds", "status": "OPEN", "inPlay": False,
            "marketCondition": {"minBet": 100, "maxBet": 10000,
                                "betDelay": 8, "betLock": False},
            "runners": [{"id": 2909511, "name": "Chapecoense"},
                        {"id": 2760854, "name": "Mirassol"},
                        {"id": 58805, "name": "The Draw"}]},
        "metadata": {"book":
            "1.264507448|0|OPEN|False|t|1|False|"
            "2909511~ACTIVE~3.7:100:*3.6:50:~3.85:80:*3.9:60:,"
            "2760854~ACTIVE~2.12:50:~2.18:40:,"
            "58805~ACTIVE~3.6:70:~3.75:60:"},
    }]


def test_materialize_merges_selected_prices_when_detail_books_empty(client, monkeypatch):
    # Detail books are empty in this variant of the live sample; the
    # targeted lookup carries the prices, so materialize must merge them
    # in. (The raw sample carries books, so strip them to exercise the
    # merge path for real.)

    def fake_fetch(path):
        if path.startswith("markets/selected"):
            return _selected_item_for_detail_market()
        detail = load_sample("detail_soccer.json")
        detail["metadata"]["books"] = ""
        return detail

    monkeypatch.setattr(live_feed, "fetch_json", fake_fetch)
    login_demo(client)
    mat = client.post("/api/live/materialize", json={
        "event_id": "36239536", "market_id": "1.264507448",
        "runner_id": "2909511", "side": "back", "odds": 3.7})
    assert mat.status_code == 200, mat.get_json()
    assert mat.get_json()["runner"] == "Chapecoense"
    r = client.post("/api/bets", json={
        "match_id": mat.get_json()["match_id"],
        "market_id": mat.get_json()["market_id"],
        "selection_id": mat.get_json()["selection_id"],
        "side": "back", "stake": 10, "odds": 3.7})
    assert r.status_code == 200
    assert r.get_json()["odds"] == 3.7


def test_materialize_and_live_bet_at_live_price(client, monkeypatch):
    monkeypatch.setattr(live_feed, "fetch_json", lambda path: _detail_with_books())
    login_demo(client)
    mat = client.post("/api/live/materialize", json={
        "event_id": "36239536", "market_id": "1.264507448",
        "runner_id": "2909511", "side": "back", "odds": 2.5}).get_json()
    assert mat["runner"] == "Chapecoense"
    # Idempotent: a second materialize reuses the same rows.
    mat2 = client.post("/api/live/materialize", json={
        "event_id": "36239536", "market_id": "1.264507448",
        "runner_id": "2909511", "side": "back", "odds": 2.5}).get_json()
    assert mat2["match_id"] == mat["match_id"]
    assert mat2["selection_id"] == mat["selection_id"]
    # The bet goes in at the clicked live price, not the simulated tick.
    r = client.post("/api/bets", json={
        "match_id": mat["match_id"], "market_id": mat["market_id"],
        "selection_id": mat["selection_id"], "side": "back",
        "stake": 10, "odds": 2.5})
    assert r.status_code == 200, r.get_json()
    assert r.get_json()["odds"] == 2.5
    assert r.get_json()["user"]["exposure"] == 10.00
    # Live matches cannot settle without a results feed.
    assert client.post(f"/api/matches/{mat['match_id']}/settle").status_code == 400
    # Live shadows stay out of the simulated lists.
    matches = client.get("/api/matches").get_json()
    assert len(matches) == 7
    assert all(m["live_event_id"] is None for m in matches)
    # ...and a live bet without a client-supplied price still books at
    # the server-side feed price (the price comes from the feed, never
    # from the client).
    good = client.post("/api/bets", json={
        "match_id": mat["match_id"], "market_id": mat["market_id"],
        "selection_id": mat["selection_id"], "side": "back", "stake": 10})
    assert good.status_code == 200, good.get_json()
    assert good.get_json()["odds"] == 2.5


# ---------------- real Fancy from guest event detail ----------------

def test_parse_ladder_fancy_format():
    # Fancy/session books carry a third field per level: price:stake:line.
    # The ladder keeps (price, stake); the line is exposed separately.
    assert live_feed.parse_ladder("100:0:71") == [(100.0, 0.0)]
    assert live_feed.parse_ladder("90:0:86") == [(90.0, 0.0)]
    assert live_feed.parse_line("100:0:71") == "71"
    assert live_feed.parse_line("2.8:15.43") is None
    # Standard format is unchanged.
    assert live_feed.parse_ladder("2.8:15.43:*2.78:48.79:") == [
        (2.8, 15.43), (2.78, 48.79)]


def test_parse_books_json_dict_string():
    # Live cricket detail carries books as a JSON-encoded dict string,
    # not newline-separated books.
    raw = load_sample("guest_detail_ranji.json")["metadata"]["books"]
    assert raw.strip().startswith("{")
    books = live_feed.parse_books(raw)
    assert len(books) >= 100
    runner = books["3333712"]["3333712"]
    assert runner["status"] == "ACTIVE"
    assert runner["back"] == [(100.0, 0.0)]
    assert runner["lay"] == [(100.0, 0.0)]
    assert runner["line"] == "71"
    assert runner["lay_line"] == "70"
    # Null book values are skipped, not fatal.
    assert live_feed.parse_books('{"1": null, "2": "2|0|OPEN|F|t|1|F|5~ACTIVE~2.0:10:~2.2:5:"}')["2"]


def test_parse_event_detail_ranji_fancy_grouping():
    detail = live_feed.parse_event_detail(load_sample("guest_detail_ranji.json"))
    assert detail["event_name"] == "Himachal Pradesh V  Rajasthan"
    assert len(detail["markets"]) == 123
    types = {}
    for m in detail["markets"]:
        types[m["market_type"]] = types.get(m["market_type"], 0) + 1
    assert types == {"OVERS": 34, "BATSMAN": 70, "BOOKMAKER": 1, "WINNING_ODDS": 18}
    fancy = live_feed.fancy_markets(detail)
    assert len(fancy) == 104
    assert all(m["market_type"] in ("OVERS", "BATSMAN") for m in fancy)
    assert len(detail["markets"]) - len(fancy) == 19
    # A real priced, bettable fancy market: 20 Over RAJ (2).
    mkt = next(m for m in fancy if m["market_id"] == "3333712")
    assert mkt["status"] == "OPEN" and not mkt["bet_lock"]
    runner = mkt["runners"][0]
    assert runner["status"] == "ACTIVE"
    assert runner["best_back"] == 100.0
    assert runner["best_lay"] == 100.0
    assert runner["line"] == "71"


def test_materialize_fancy_bet_at_converted_decimal_odds(client, monkeypatch):
    # Fancy rates are percent-scale (100 = even money); the clone's bet
    # flow is decimal-odds based, so the slip converts: 1 + rate / 100.
    # The materialize path itself is the same as other live odds.
    monkeypatch.setattr(live_feed, "fetch_json",
                        lambda path: load_sample("guest_detail_ranji.json"))
    login_demo(client)
    mat = client.post("/api/live/materialize", json={
        "event_id": "-11239905", "market_id": "3333712",
        "runner_id": "3333712", "side": "back", "odds": 2.0}).get_json()
    assert mat["runner"] == "20 Over  RAJ  (2)"
    r = client.post("/api/bets", json={
        "match_id": mat["match_id"], "market_id": mat["market_id"],
        "selection_id": mat["selection_id"], "side": "back",
        "stake": 10, "odds": 2.0})
    assert r.status_code == 200, r.get_json()
    assert r.get_json()["odds"] == 2.0
    assert r.get_json()["user"]["exposure"] == 10.00
    # Live matches still cannot settle (no results feed).
    assert client.post(f"/api/matches/{mat['match_id']}/settle").status_code == 400


# ---------------- proxy robustness: transient failures ----------------

def _fake_resp(payload):
    class FakeResp:
        def read(self):
            return json.dumps(payload).encode()

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    return FakeResp()


def test_fetch_json_retries_transient_errors_then_succeeds(monkeypatch):
    import http.client

    calls = []

    def flaky(req, timeout=None):
        calls.append(1)
        if len(calls) <= 2:
            raise http.client.RemoteDisconnected("dropped")
        return _fake_resp(load_sample("current.json"))

    monkeypatch.setattr("live_feed.urllib.request.urlopen", flaky)
    live_feed.clear_cache()
    data = live_feed.fetch_json("markets/current")
    assert len(calls) == 3
    assert data[0]["event"]["name"] == "Blackburn v Stoke"


def test_fetch_json_uses_partial_json_on_incomplete_read(monkeypatch):
    import http.client

    payload = json.dumps(load_sample("current.json")).encode()

    def partial(req, timeout=None):
        raise http.client.IncompleteRead(partial=payload, expected=len(payload) + 10)

    monkeypatch.setattr("live_feed.urllib.request.urlopen", partial)
    live_feed.clear_cache()
    data = live_feed.fetch_json("markets/current")
    assert data[0]["event"]["name"] == "Blackburn v Stoke"


def test_fetch_json_gives_up_after_retries(monkeypatch):
    import http.client

    def dead(req, timeout=None):
        raise http.client.RemoteDisconnected("dropped")

    monkeypatch.setattr("live_feed.urllib.request.urlopen", dead)
    live_feed.clear_cache()
    with pytest.raises(live_feed.LiveFeedError):
        live_feed.fetch_json("markets/current")


def test_live_list_falls_back_on_transient_error_not_500(client, monkeypatch):
    # Regression test for the 2026-11-03 bug: urllib mid-read failures
    # escaped as HTTP 500 instead of the documented simulated fallback.
    import http.client

    def dead(req, timeout=None):
        raise http.client.RemoteDisconnected("dropped")

    monkeypatch.setattr("live_feed.urllib.request.urlopen", dead)
    r = client.get("/api/live/current")
    assert r.status_code == 200
    data = r.get_json()
    assert data["source"] == "simulated-fallback"
    assert len(data["events"]) == 7
