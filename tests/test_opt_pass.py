"""Tests for the Render optimization pass: slim payloads, ETags/304,
background snapshots (single-flight + stale-while-revalidate).

Upstream responses are stubbed -- no test here touches the network. The
background thread itself is NOT started in tests (create_app only starts
it when TESTING is unset); refresh_snapshot is exercised directly.
"""
import json
import os
import sys
import time

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


def test_slim_drops_ladders_keeps_best_prices():
    events = live_feed.parse_event_item(load_sample("current.json")[0])
    # parse_event_item returns one event dict; slim a list of one.
    slim = live_feed.slim_events([events])[0]
    assert slim["event_id"] == events["event_id"]
    assert slim["event_name"] == events["event_name"]
    assert slim["market"]["status"] == events["market"]["status"]
    assert slim["market"]["bet_lock"] == events["market"]["bet_lock"]
    for rs, ro in zip(slim["market"]["runners"], events["market"]["runners"]):
        assert rs["best_back"] == ro["best_back"]
        assert rs["best_lay"] == ro["best_lay"]
        assert "back" not in rs and "lay" not in rs


def test_list_slim_param_returns_slim_shape(client, monkeypatch):
    monkeypatch.setattr(live_feed, "fetch_json",
                        lambda path, force=False: load_sample("current.json"))
    r = client.get("/api/live/current?slim=1")
    assert r.status_code == 200
    data = r.get_json()
    assert data["source"] == "live-delayed"
    assert data["events"]
    assert all("back" not in run and "lay" not in run
               for ev in data["events"] for run in ev["market"]["runners"])
    r2 = client.get("/api/live/current")
    assert r2.status_code == 200
    full = r2.get_json()
    assert full["events"]
    assert any("back" in run
               for ev in full["events"] for run in ev["market"]["runners"])


def test_etag_304_on_unchanged_list(client, monkeypatch):
    monkeypatch.setattr(live_feed, "fetch_json",
                        lambda path, force=False: load_sample("current.json"))
    r1 = client.get("/api/live/current")
    assert r1.status_code == 200
    etag = r1.headers.get("ETag")
    assert etag
    r2 = client.get("/api/live/current", headers={"If-None-Match": etag})
    assert r2.status_code == 304
    assert r2.data == b""
    r3 = client.get("/api/live/current", headers={"If-None-Match": '"nope"'})
    assert r3.status_code == 200


def test_etag_304_on_event_detail(client, monkeypatch):
    monkeypatch.setattr(live_feed, "fetch_json",
                        lambda path, force=False: load_sample("detail_soccer.json"))
    r1 = client.get("/api/live/event/36239536")
    assert r1.status_code == 200
    etag = r1.headers.get("ETag")
    assert etag
    r2 = client.get("/api/live/event/36239536",
                    headers={"If-None-Match": etag})
    assert r2.status_code == 304


def test_refresh_snapshot_single_flight_and_slim(client, monkeypatch):
    calls = []
    payload = load_sample("current.json")

    def stub(path, force=False):
        calls.append(path)
        return payload

    monkeypatch.setattr(live_feed, "fetch_json", stub)
    snap = live_feed.refresh_snapshot("markets/current")
    assert snap["kind"] == "list"
    assert snap["etag"] and snap["slim_etag"]
    assert snap["etag"] != snap["slim_etag"]
    assert len(calls) == 1
    # Second refresh inside the fresh window reuses the snapshot.
    snap2 = live_feed.refresh_snapshot("markets/current")
    assert snap2["etag"] == snap["etag"]
    assert len(calls) == 1
    # Served through the route from the snapshot (no extra fetch).
    r = client.get("/api/live/current?slim=1")
    assert r.status_code == 200
    assert len(calls) == 1
    assert r.headers.get("ETag") == snap["slim_etag"]


def test_refresh_snapshot_failure_keeps_old_snapshot(monkeypatch):
    monkeypatch.setattr(live_feed, "fetch_json",
                        lambda path, force=False: load_sample("current.json"))
    snap = live_feed.refresh_snapshot("markets/current")
    assert snap is not None

    def boom(path, force=False):
        raise live_feed.LiveFeedError("down")

    monkeypatch.setattr(live_feed, "fetch_json", boom)
    with pytest.raises(live_feed.LiveFeedError):
        live_feed.refresh_snapshot("markets/current", force=True)
    kept = live_feed.snapshot_get("markets/current")
    assert kept is not None and kept["etag"] == snap["etag"]


def test_snapshot_stale_triggers_refresh_via_route(client, monkeypatch):
    calls = []
    payload = load_sample("current.json")

    def stub(path, force=False):
        calls.append(path)
        return payload

    monkeypatch.setattr(live_feed, "fetch_json", stub)
    live_feed.refresh_snapshot("markets/current")
    assert len(calls) == 1
    # Age the snapshot past the fresh window: the next route request must
    # refresh synchronously (single-flight) rather than serve it stale.
    with live_feed._SNAP_LOCK:
        live_feed._SNAPSHOTS["markets/current"]["updated"] = time.time() - 60
    r = client.get("/api/live/current")
    assert r.status_code == 200
    assert len(calls) == 2
