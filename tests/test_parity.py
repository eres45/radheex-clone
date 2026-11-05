"""Parity tests for the real-site completeness sweep: guest-feed fields the
clone used to drop (TV, scorecard, announcements, market-condition fields)
and the bookmaker percent-rate conversion. Upstream responses are stubbed;
no test here touches the network."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

import live_feed
from app import create_app
from csrf_helpers import wrap


@pytest.fixture
def client(tmp_path):
    live_feed.clear_cache()
    app = create_app({"DATABASE": str(tmp_path / "test.db"), "TESTING": True})
    with app.test_client() as c:
        yield wrap(c)


def login_demo(client):
    r = client.post("/api/auth/login", json={"username": "demo", "password": "demo123"})
    assert r.status_code == 200


def _list_item():
    return {
        "eventType": {"id": 1, "name": "Soccer"},
        "competition": {"id": 10, "name": "Test League"},
        "event": {"id": 36223235, "name": "A v B", "openDate": "2026-11-04T10:00:00.000Z"},
        "catalogue": {
            "marketId": "1.1", "marketName": "Match Odds", "marketType": "MATCH_ODDS",
            "status": "OPEN", "inPlay": True, "marketTime": "2026-11-04T10:00:00.000Z",
            "marketCondition": {"betLock": False, "minBet": 100, "maxBet": 100000,
                                "maxProfit": 50000, "betDelay": 5, "mtp": 0,
                                "allowUnmatchBet": True, "potLimit": 0, "volume": 1234},
            "runners": [{"id": 1, "name": "A", "sortPriority": 0},
                        {"id": 2, "name": "B", "sortPriority": 1}],
        },
        "metadata": {
            "book": "1.1|0|OPEN|True||1|False|1~ACTIVE~2.0:10:~2.2:5:,2~ACTIVE~3.0:10:~3.2:5:",
            "hasTv": "True",
            "tvUrl": "https://oddsdata.org/score/a9a34ab526857ed732b4cc0aa5802be39fca6e47/36223235",
            "scoreUrl": "76256436",
            "hasSession": "True",
            "hasBookMaker": "True",
        },
    }


def _bookmaker_detail():
    return {
        "eventType": {"id": 4, "name": "Cricket"},
        "competition": {"id": 20, "name": "Test Cup"},
        "event": {"id": 36271322, "name": "X v Y", "openDate": "2026-11-04T10:00:00.000Z"},
        "catalogues": [{
            "marketId": "43909941", "marketName": "Bookmaker 0 Commission",
            "marketType": "BOOKMAKER", "status": "OPEN", "inPlay": True,
            "marketCondition": {"betLock": False, "minBet": 100, "maxBet": 100000,
                                "betDelay": 0},
            "runners": [{"id": 47455045, "name": "X", "sortPriority": 0},
                        {"id": 47455046, "name": "Y", "sortPriority": 1}],
        }, {
            "marketId": "43909942", "marketName": "Winner",
            "marketType": "WINNING_ODDS", "status": "OPEN", "inPlay": False,
            "marketCondition": {"betLock": False, "minBet": 100, "maxBet": 100000,
                                "betDelay": 0},
            "runners": [{"id": 47455047, "name": "X", "sortPriority": 0}],
        }],
        "metadata": {
            # Bookmaker books quote PERCENT rates (78 = 1.78 decimal);
            # winning-odds books quote decimal odds (1.98 stays 1.98).
            "books": {
                "43909941": ("43909941|0|OPEN|True||1|False|"
                             "47455045~ACTIVE~78:0:*77:0:*76:0:~82:0:*83:0:*84:0:,"
                             "47455046~ACTIVE~98:0:~99:0:"),
                "43909942": ("43909942|0|OPEN|False||1|False|"
                             "47455047~ACTIVE~1.98:0:0~2.0:0:0"),
            },
            "tvUrl": "https://oddsdata.org/score/hash/36271322",
            "hasSession": "True",
            "hasBookMaker": "True",
            "messages": {
                "43909941": [
                    {"time": 100, "message": "old active", "isActive": True},
                    {"time": 200, "message": "new active", "isActive": True},
                    {"time": 300, "message": "inactive one", "isActive": False},
                ],
            },
        },
    }


def test_parse_event_item_passes_tv_score_and_flags():
    ev = live_feed.parse_event_item(_list_item())
    assert ev["has_tv"] is True
    assert ev["tv_url"].endswith("/36223235")
    assert ev["score_url"] == "76256436"
    assert ev["has_session"] is True
    assert ev["has_bookmaker"] is True
    assert ev["market"]["market_name"] == "Match Odds"


def test_parse_event_item_tv_url_alone_implies_tv():
    item = _list_item()
    item["metadata"] = {"tvUrl": "https://oddsdata.org/score/h/1"}
    ev = live_feed.parse_event_item(item)
    assert ev["has_tv"] is True
    assert ev["tv_url"] == "https://oddsdata.org/score/h/1"
    assert ev["score_url"] is None


def test_parse_catalogue_passes_market_condition_fields():
    cat = live_feed.parse_catalogue(_list_item()["catalogue"])
    assert cat["max_profit"] == 50000
    assert cat["allow_unmatch"] is True
    assert cat["mtp"] == 0
    assert cat["pot_limit"] == 0
    assert cat["volume"] == 1234
    assert cat["min_bet"] == 100
    assert cat["max_bet"] == 100000
    assert cat["bet_delay"] == 5


def test_parse_event_detail_passes_tv_messages_and_flags():
    d = live_feed.parse_event_detail(_bookmaker_detail())
    assert d["tv_url"] == "https://oddsdata.org/score/hash/36271322"
    assert d["score_url"] is None  # detail never carries it; list items do
    assert d["has_session"] is True
    assert d["has_bookmaker"] is True
    msgs = d["messages"]
    assert [m["message"] for m in msgs] == ["new active", "old active"]
    assert msgs[0]["market_id"] == "43909941"


def test_parse_event_detail_messages_capped_at_twenty():
    detail = _bookmaker_detail()
    detail["metadata"]["messages"] = {
        "43909941": [{"time": t, "message": f"m{t}", "isActive": True}
                     for t in range(25)]
    }
    d = live_feed.parse_event_detail(detail)
    assert len(d["messages"]) == 20
    assert d["messages"][0]["message"] == "m24"


def test_slim_events_keep_tv_and_score():
    ev = live_feed.parse_event_item(_list_item())
    slim = live_feed.slim_event(ev)
    assert slim["has_tv"] is True
    assert slim["score_url"] == "76256436"


def test_live_list_route_passes_new_fields(client, monkeypatch):
    monkeypatch.setattr(live_feed, "fetch_json", lambda path: [_list_item()])
    r = client.get("/api/live/live")
    assert r.status_code == 200
    ev = r.get_json()["events"][0]
    assert ev["has_tv"] is True
    assert ev["score_url"] == "76256436"
    r = client.get("/api/live/live?slim=1")
    ev = r.get_json()["events"][0]
    assert ev["has_tv"] is True
    assert ev["score_url"] == "76256436"


def test_live_event_route_passes_tv_and_messages(client, monkeypatch):
    monkeypatch.setattr(live_feed, "fetch_json", lambda path: _bookmaker_detail())
    r = client.get("/api/live/event/36271322")
    assert r.status_code == 200
    ev = r.get_json()["event"]
    assert ev["tv_url"] == "https://oddsdata.org/score/hash/36271322"
    assert [m["message"] for m in ev["messages"]] == ["new active", "old active"]


def test_materialize_converts_bookmaker_percent_to_decimal(client, monkeypatch):
    monkeypatch.setattr(live_feed, "fetch_json", lambda path: _bookmaker_detail())
    login_demo(client)
    # Client-supplied odds are ignored: the server-side feed price wins.
    r = client.post("/api/live/materialize", json={
        "event_id": "36271322", "market_id": "43909941",
        "runner_id": "47455045", "side": "back", "odds": 999})
    assert r.status_code == 200, r.get_json()
    assert r.get_json()["odds"] == 1.78
    r = client.post("/api/live/materialize", json={
        "event_id": "36271322", "market_id": "43909941",
        "runner_id": "47455045", "side": "lay", "odds": 999})
    assert r.get_json()["odds"] == 1.82


def test_materialize_keeps_winning_odds_decimal(client, monkeypatch):
    monkeypatch.setattr(live_feed, "fetch_json", lambda path: _bookmaker_detail())
    login_demo(client)
    r = client.post("/api/live/materialize", json={
        "event_id": "36271322", "market_id": "43909942",
        "runner_id": "47455047", "side": "back", "odds": 999})
    assert r.status_code == 200, r.get_json()
    assert r.get_json()["odds"] == 1.98
