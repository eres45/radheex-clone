"""Live delayed sportsbook feed (public guest data, read-only).

Upstream: https://api.radheex.com/delaymarkets/ with the public brand
header X-OP-KEY: RDE. This is the DELAYED guest feed (delaymarkets), not
real-time and not operator access -- the app labels it as such.

Payload shape (from saved samples in ../recon/samples/):
- List endpoints (markets/current, markets/live, markets/eventtype/{id})
  return a list of items, each with eventType/competition/event, a single
  `catalogue` market, and metadata.book -- a pipe-delimited string whose
  runner entries carry back/lay ladders.
- Detail (events/detail/{id}) returns one event with `catalogues` (a list
  of markets) and metadata.books (a string, possibly empty).
- Menu (Markets/menu) returns a flat list of menu rows.

Book string format (one market):
    marketId|..|status|..|timestamp|..|..|runnerId~STATUS~back~lay,runnerId~...
  where each side is price:stake pairs joined by ':*' with a trailing ':',
  e.g. "2.8:15.43:*2.78:48.79:*2.76:52.13:" -> [(2.8, 15.43), ...].
  Suspended runners look like "47454453~SUSPENDED~~" (empty sides).
  Runners with no book entry simply have no prices.

Only GETs, no logins, no credentials beyond the public brand header.
"""
import http.client
import json
import hashlib
import os
import threading
import time
import urllib.error
import urllib.request

LIVE_BASE = "https://api.radheex.com/delaymarkets/"
REALTIME_BASE = "https://api.radheex.com/marketprovider/"
DEMO_AUTH_URL = "https://api.radheex.com/sso/auth/demo"
USE_REALTIME = os.environ.get("USE_REALTIME", "0") == "1"

LIVE_HEADERS = {"Content-Type": "application/json", "X-OP-KEY": "RDE"}
LIVE_TIMEOUT = 5
CACHE_TTL = 4

_CACHE = {}

_TOKEN_LOCK = threading.Lock()
_DEMO_TOKEN = None
_DEMO_TOKEN_EXP = 0


def get_demo_token():
    """Acquire or return cached JWT token from RadheEx demo auth endpoint."""
    global _DEMO_TOKEN, _DEMO_TOKEN_EXP
    now = time.time()
    if _DEMO_TOKEN and _DEMO_TOKEN_EXP > now + 60:
        return _DEMO_TOKEN
    with _TOKEN_LOCK:
        if _DEMO_TOKEN and _DEMO_TOKEN_EXP > now + 60:
            return _DEMO_TOKEN
        req = urllib.request.Request(
            DEMO_AUTH_URL,
            headers={
                "X-OP-KEY": "RDE",
                "Origin": "https://www.radheex.com",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            },
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=LIVE_TIMEOUT) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                tok = data.get("token")
                if tok:
                    _DEMO_TOKEN = tok
                    _DEMO_TOKEN_EXP = now + 900
                    return _DEMO_TOKEN
        except Exception:
            pass
    return None


class LiveFeedError(Exception):
    """Upstream fetch failed (network, timeout, HTTP error, bad JSON)."""


def clear_cache():
    _CACHE.clear()
    with _SNAP_LOCK:
        _SNAPSHOTS.clear()
    with _SNAP_LOCK:
        _LAST_REQUEST.clear()


FETCH_ATTEMPTS = 3
FETCH_BACKOFF = (0.25, 0.5)  # seconds before attempts 2 and 3


def fetch_json(path, force=False):
    """GET one upstream path (relative to LIVE_BASE or REALTIME_BASE), cached ~4 seconds.

    With force=True the cache is bypassed for reading (still written), so
    a background refresher always fetches fresh data. Returns the decoded
    JSON. Transient fetch failures (IncompleteRead, RemoteDisconnected,
    timeouts, other connection errors) are retried up to FETCH_ATTEMPTS
    times with a short backoff; an IncompleteRead whose partial payload
    is still valid JSON is used as-is. Raises LiveFeedError on any
    failure (HTTP errors are not retried).
    """
    now = time.time()
    hit = _CACHE.get(path)
    if not force and hit and hit[0] > now:
        return hit[1]

    # Try 0-second real-time authenticated endpoint first if enabled
    if USE_REALTIME:
        tok = get_demo_token()
        if tok:
            rt_headers = dict(LIVE_HEADERS)
            rt_headers["Authorization"] = f"Bearer {tok}"
            rt_headers["Origin"] = "https://www.radheex.com"
            rt_headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            rt_req = urllib.request.Request(REALTIME_BASE + path, headers=rt_headers, method="GET")
            try:
                with urllib.request.urlopen(rt_req, timeout=LIVE_TIMEOUT) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                _CACHE[path] = (now + CACHE_TTL, data)
                return data
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ConnectionError,
                    http.client.HTTPException, OSError, ValueError):
                pass  # Fall through to delayed guest feed on any real-time failure

    req = urllib.request.Request(LIVE_BASE + path, headers=LIVE_HEADERS, method="GET")
    last_exc = None
    for attempt in range(FETCH_ATTEMPTS):
        try:
            with urllib.request.urlopen(req, timeout=LIVE_TIMEOUT) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as exc:
            raise LiveFeedError(f"upstream HTTP {exc.code} for {path}") from exc
        except http.client.IncompleteRead as exc:
            # The connection dropped mid-body, but the bytes received may
            # still be a complete, parseable payload -- use them.
            try:
                data = json.loads(exc.partial.decode("utf-8"))
                break
            except (ValueError, UnicodeDecodeError, AttributeError):
                last_exc = exc
        except ValueError as exc:
            # Complete read, unparseable body: retrying cannot help.
            raise LiveFeedError(f"upstream bad JSON for {path}: {exc}") from exc
        except (urllib.error.URLError, TimeoutError, ConnectionError,
                http.client.HTTPException, OSError) as exc:
            last_exc = exc
        if attempt < FETCH_ATTEMPTS - 1:
            time.sleep(FETCH_BACKOFF[attempt])
    else:
        raise LiveFeedError(f"upstream fetch failed for {path}: {last_exc}")
    _CACHE[path] = (now + CACHE_TTL, data)
    return data


def parse_ladder(side):
    """Parse one side of a book runner entry into [(price, stake), ...].

    Side format: "price:stake:*price:stake:*..." with an optional trailing
    ':'. Fancy/session books carry a third field per level
    ("price:stake:line", e.g. "100:0:71") -- the line is the runs line
    (see parse_book); the ladder keeps (price, stake) only.
    Malformed pairs are skipped, never fatal.
    """
    out = []
    if not side:
        return out
    side = side.strip().rstrip(":")
    if not side:
        return out
    for piece in side.split(":*"):
        piece = piece.strip().rstrip(":")
        if not piece:
            continue
        fields = piece.split(":")
        if len(fields) < 2:
            continue
        try:
            out.append((float(fields[0]), float(fields[1])))
        except ValueError:
            continue
    return out


def parse_line(side):
    """First level's line field of a book side, if present ("100:0:71" -> "71").

    Standard match/bookmaker books have no line -> None.
    """
    if not side:
        return None
    first = side.strip().rstrip(":").split(":*")[0]
    fields = first.split(":")
    return fields[2] if len(fields) > 2 and fields[2] != "" else None


def parse_book(book):
    """Parse one market book string -> (market_id, {runner_id: runner}).

    Runner dict: {"status": str, "back": [(price, stake)], "lay": [...]}.
    Returns (None, {}) for empty/malformed input.
    """
    if not book or not isinstance(book, str):
        return None, {}
    parts = book.split("|")
    if len(parts) < 8:
        return None, {}
    market_id = parts[0]
    runners = {}
    runner_section = parts[7]
    if not runner_section.strip():
        return market_id, runners
    for entry in runner_section.split(","):
        entry = entry.strip()
        if not entry:
            continue
        fields = entry.split("~")
        if len(fields) < 2:
            continue
        runner_id, status = fields[0], fields[1]
        back_side = fields[2] if len(fields) > 2 else ""
        lay_side = fields[3] if len(fields) > 3 else ""
        runners[runner_id] = {
            "status": status,
            "back": parse_ladder(back_side),
            "lay": parse_ladder(lay_side),
            # Fancy/session line (runs line), e.g. "71"; None for
            # standard books, which carry no third field.
            "line": parse_line(back_side),
            "lay_line": parse_line(lay_side),
        }
    return market_id, runners


def parse_books(books):
    """Parse a detail endpoint's `books` value -> {market_id: runners}.

    Accepts a string (single book, or newline-separated books), a list of
    strings, a dict of market_id -> book string, or a JSON-encoded dict
    string (the form live cricket detail uses:
    '{"<marketId>": "<book>", ...}'). Unknown shapes -> {}.
    """
    out = {}
    if not books:
        return out
    if isinstance(books, str):
        stripped = books.strip()
        if stripped.startswith("{"):
            try:
                decoded = json.loads(stripped)
            except ValueError:
                return out
            return parse_books(decoded)
        candidates = books.splitlines()
    elif isinstance(books, dict):
        candidates = books.values()
    elif isinstance(books, list):
        candidates = books
    else:
        return out
    for candidate in candidates:
        market_id, runners = parse_book(candidate)
        if market_id:
            out[market_id] = runners
    return out


FANCY_MARKET_TYPES = ("OVERS", "BATSMAN")


# Markets whose book prices are percent rates, not decimal odds: the slip
# converts rate -> decimal as 1 + rate/100. OVERS/BATSMAN fancy books quote
# rates (100 = even money); BOOKMAKER books quote rates too, verified
# against live guest books (back 78 / lay 82, toss 98, outright 500/170/200
# -- only sensible as percent rates, never as decimal odds). WINNING_ODDS
# books quote decimal odds (e.g. 1.98) and are NOT in this set.
# SPECIAL_MAKER books were never observed with prices, so they stay decimal
# until a priced book proves otherwise.
RATE_MARKET_TYPES = ("OVERS", "BATSMAN", "BOOKMAKER")


def fancy_markets(event_detail):
    """The Fancy section of a parsed event detail: its OVERS + BATSMAN
    catalogues (the site's Fancy tab content)."""
    return [m for m in event_detail.get("markets", [])
            if m.get("market_type") in FANCY_MARKET_TYPES]


def parse_catalogue(cat, book_runners=None):
    """Normalize one catalogue market + its runners' live prices."""
    cond = cat.get("marketCondition") or {}
    runners = []
    for r in cat.get("runners") or []:
        rid = str(r.get("id"))
        book = (book_runners or {}).get(rid)
        if book:
            status = book["status"]
            back, lay = book["back"], book["lay"]
            line, lay_line = book.get("line"), book.get("lay_line")
        else:
            status, back, lay, line, lay_line = None, [], [], None, None
        runners.append({
            "id": rid,
            "name": r.get("name"),
            "status": status,
            "back": [[p, s] for p, s in back],
            "lay": [[p, s] for p, s in lay],
            "best_back": back[0][0] if back else None,
            "best_lay": lay[0][0] if lay else None,
            "line": line,
            "lay_line": lay_line,
        })
    return {
        "market_id": str(cat.get("marketId")),
        "market_name": cat.get("marketName"),
        "market_type": cat.get("marketType"),
        "status": cat.get("status"),
        "in_play": bool(cat.get("inPlay")),
        "bet_lock": bool(cond.get("betLock")),
        "min_bet": cond.get("minBet"),
        "max_bet": cond.get("maxBet"),
        "bet_delay": cond.get("betDelay"),
        # Further marketCondition fields, passed through for display and
        # API completeness (mtp's purpose is undocumented upstream).
        "max_profit": cond.get("maxProfit"),
        "allow_unmatch": cond.get("allowUnmatchBet"),
        "mtp": cond.get("mtp"),
        "pot_limit": cond.get("potLimit"),
        "volume": cond.get("volume"),
        "runners": runners,
    }


def parse_event_item(item):
    """Normalize one list-endpoint item (singular `catalogue`)."""
    event = item.get("event") or {}
    et = item.get("eventType") or {}
    comp = item.get("competition") or {}
    cat = item.get("catalogue") or {}
    md = item.get("metadata") or {}
    book = md.get("book")
    _, runners = parse_book(book)
    tv_url = md.get("tvUrl")
    return {
        "event_id": str(event.get("id")),
        "sport": (et.get("name") or ""),
        "sport_id": str(et.get("id")),
        "competition": comp.get("name"),
        "competition_id": str(comp.get("id")) if comp.get("id") is not None else None,
        "event_name": event.get("name"),
        "open_date": event.get("openDate"),
        "in_play": bool(cat.get("inPlay")),
        "status": cat.get("status"),
        "market": parse_catalogue(cat, runners),
        # Guest-visible TV/score/summary flags. hasTv arrives as "True"
        # or True (or is absent while tvUrl is present), so tvUrl
        # presence is the reliable TV signal. scoreUrl arrives as a bare
        # score id (the real site feeds it to its scorecard widget).
        "has_tv": md.get("hasTv") in ("True", True) or bool(tv_url),
        "tv_url": tv_url,
        "score_url": str(md["scoreUrl"]) if md.get("scoreUrl") is not None else None,
        "has_session": md.get("hasSession") in ("True", True),
        "has_bookmaker": md.get("hasBookMaker") in ("True", True),
    }


def parse_event_detail(data):
    """Normalize one detail-endpoint response (plural `catalogues`)."""
    event = data.get("event") or {}
    et = data.get("eventType") or {}
    comp = data.get("competition") or {}
    md = data.get("metadata") or {}
    books = parse_books(md.get("books"))
    markets = []
    for cat in data.get("catalogues") or []:
        markets.append(parse_catalogue(cat, books.get(str(cat.get("marketId")), {})))
    # Market announcements (commentary): metadata.messages maps marketId
    # to [{time, message, isActive}]. Only active messages are surfaced,
    # newest first, capped so one chatty market cannot bloat the page.
    messages = []
    raw_messages = md.get("messages") or {}
    if isinstance(raw_messages, dict):
        for market_id, msgs in raw_messages.items():
            for m in msgs or []:
                if isinstance(m, dict) and m.get("isActive") and m.get("message"):
                    messages.append({"market_id": str(market_id),
                                     "time": m.get("time"),
                                     "message": m["message"]})
    messages.sort(key=lambda m: m.get("time") or 0, reverse=True)
    messages = messages[:20]
    return {
        "event_id": str(event.get("id")),
        "sport": (et.get("name") or ""),
        "sport_id": str(et.get("id")),
        "competition": comp.get("name"),
        "competition_id": str(comp.get("id")) if comp.get("id") is not None else None,
        "event_name": event.get("name"),
        "open_date": event.get("openDate"),
        "markets": markets,
        "tv_url": md.get("tvUrl"),
        "has_tv": md.get("hasTv") in ("True", True) or bool(md.get("tvUrl")),
        # Detail payloads carry no scoreUrl; it arrives via list items
        # (see parse_event_item) and the SPA resolves it from its list
        # cache. None here is honest, not a missing field.
        "score_url": None,
        "messages": messages,
        "has_session": md.get("hasSession") in ("True", True),
        "has_bookmaker": md.get("hasBookMaker") in ("True", True),
    }


def simulated_to_live_event(match_view):
    """Shape one local (simulated) match view like a live list event, so
    list endpoints can fall back to it without the frontend changing
    shape. The first bookmaker market becomes the event's market."""
    bookmaker = next(
        (m for m in match_view.get("markets", []) if m["kind"] == "bookmaker"),
        None,
    )
    runners = []
    if bookmaker:
        for sel in bookmaker["selections"]:
            runners.append({
                "id": str(sel["id"]),
                "name": sel["name"],
                "status": "ACTIVE",
                "back": [[sel["back"], 0]],
                "lay": [[sel["lay"], 0]],
                "best_back": sel["back"],
                "best_lay": sel["lay"],
            })
    return {
        "event_id": f"sim-{match_view['id']}",
        "sport": match_view["sport"],
        "sport_id": None,
        "competition": None,
        "competition_id": None,
        "event_name": match_view["title"],
        "open_date": match_view["start_at"],
        "in_play": match_view["status"] == "live",
        "status": "OPEN" if match_view["status"] != "suspended" else "SUSPENDED",
        "has_tv": False,
        "tv_url": None,
        "score_url": None,
        "has_session": False,
        "has_bookmaker": False,
        "market": {
            "market_id": str(bookmaker["id"]) if bookmaker else None,
            "market_name": bookmaker["name"] if bookmaker else None,
            "market_type": "MATCH_ODDS",
            "status": "OPEN" if match_view["status"] != "suspended" else "SUSPENDED",
            "in_play": match_view["status"] == "live",
            "bet_lock": False,
            "min_bet": None,
            "max_bet": bookmaker["max_stake"] if bookmaker else None,
            "bet_delay": None,
            "runners": runners,
        },
    }


# ---------------------------------------------------------------------------
# Background refresh + snapshots (optimization pass).
#
# Problem: fetch_json's 4 s cache is refreshed synchronously inside the
# request that first finds it expired, so the single gunicorn worker blocks
# ~1 s on the upstream fetch every cache cycle and stalls every concurrent
# poll. Fix: a daemon thread refreshes the hot list paths off the request
# path; requests serve a pre-serialized snapshot (stale-while-revalidate).
# The thread NEVER touches the database or Flask state -- it only fetches
# and parses the public guest feed, so SQLite threading rules are unaffected.
# Snapshots also carry pre-computed slim bodies and ETags (see slim_event).
#
# Demand-gating: the thread only refreshes paths a visitor actually asked
# for in the last 120 s, so a quiet site makes no upstream traffic. The
# first request after quiet triggers one synchronous single-flight refresh
# and the thread takes over from there. If the thread ever dies, requests
# fall back to a synchronous refresh once a snapshot is older than
# SNAPSHOT_FRESH_S, then serve the fresh snapshot -- never a stale-forever
# page, never a 500 for a feed hiccup (the legacy simulated fallback below
# still applies when upstream is down entirely).
# ---------------------------------------------------------------------------

SNAPSHOT_FRESH_S = 15
BACKGROUND_PATHS = ("markets/live", "markets", "markets/current",
                    "Markets/menu",
                    "markets/eventtype/1", "markets/eventtype/2",
                    "markets/eventtype/4", "markets/eventtype/7")
_DEMAND_WINDOW_S = 120

_SNAPSHOTS = {}
_LAST_REQUEST = {}
_SNAP_LOCK = threading.Lock()
_REFRESH_LOCKS = {}
_REFRESH_LOCKS_GUARD = threading.Lock()
_REFRESH_STARTED = False


def note_request(path):
    """Record that a visitor asked for a path (drives demand-gating)."""
    with _SNAP_LOCK:
        _LAST_REQUEST[path] = time.time()


def slim_event(ev):
    """Slim list-view shape: what the list rows render (names, best odds,
    status) without the full back/lay ladders. Event detail views still
    use the full shape via /api/live/event."""
    m = ev.get("market") or {}
    return {
        "event_id": ev.get("event_id"),
        "sport": ev.get("sport"),
        "sport_id": ev.get("sport_id"),
        "competition": ev.get("competition"),
        "event_name": ev.get("event_name"),
        "open_date": ev.get("open_date"),
        "in_play": ev.get("in_play"),
        "status": ev.get("status"),
        "has_tv": ev.get("has_tv"),
        "score_url": ev.get("score_url"),
        "market": {
            "market_id": m.get("market_id"),
            "market_name": m.get("market_name"),
            "market_type": m.get("market_type"),
            "status": m.get("status"),
            "in_play": m.get("in_play"),
            "bet_lock": m.get("bet_lock"),
            "runners": [{
                "id": r.get("id"),
                "name": r.get("name"),
                "status": r.get("status"),
                "best_back": r.get("best_back"),
                "best_lay": r.get("best_lay"),
            } for r in m.get("runners", [])],
        },
    }


def slim_events(events):
    return [slim_event(e) for e in events]


def _dump(payload):
    return json.dumps(payload, separators=(",", ":")).encode("utf-8")


def _etag(body):
    return '"' + hashlib.sha1(body).hexdigest() + '"'


def snapshot_get(path):
    with _SNAP_LOCK:
        snap = _SNAPSHOTS.get(path)
        return dict(snap) if snap else None


def _refresh_lock(path):
    with _REFRESH_LOCKS_GUARD:
        return _REFRESH_LOCKS.setdefault(path, threading.Lock())


def refresh_snapshot(path, force=False):
    """Refresh one path's snapshot (single-flight via a per-path lock).

    With force=False, a snapshot younger than SNAPSHOT_FRESH_S is returned
    as-is (double-checked locking: concurrent requests serialize on the
    lock, the first refreshes, the rest reuse). With force=True (the
    background thread) the upstream fetch always runs. On fetch failure
    the old snapshot is kept and the exception propagates, so callers can
    fall back to the legacy path. Returns the snapshot dict, or None if
    there is none and the fetch failed (callers must handle None).
    """
    lock = _refresh_lock(path)
    with lock:
        snap = snapshot_get(path)
        if snap and not force and \
                time.time() - snap["updated"] < SNAPSHOT_FRESH_S:
            return snap
        raw = fetch_json(path, force=True)
        src = "live-realtime" if USE_REALTIME else "live-delayed"
        if path == "Markets/menu":
            body = _dump({"source": src, "menu": raw})
            new = {"kind": "menu", "body": body, "etag": _etag(body),
                   "updated": time.time()}
        else:
            events = [parse_event_item(it) for it in raw]
            full = _dump({"source": src, "events": events})
            slim = _dump({"source": src,
                          "events": slim_events(events)})
            new = {"kind": "list", "body": full, "etag": _etag(full),
                   "slim_body": slim, "slim_etag": _etag(slim),
                   "updated": time.time()}
        with _SNAP_LOCK:
            _SNAPSHOTS[path] = new
        return dict(new)


def _background_loop():
    while True:
        for path in BACKGROUND_PATHS:
            with _SNAP_LOCK:
                last = _LAST_REQUEST.get(path, 0)
            if time.time() - last > _DEMAND_WINDOW_S:
                continue  # nobody asked lately: make no upstream traffic
            try:
                refresh_snapshot(path, force=True)
            except Exception:
                pass  # keep last-good snapshot; next pass retries
        time.sleep(4)


def start_background_refresh():
    """Start the daemon refresher once per process. Idempotent; never
    started under TESTING (create_app guards that) and never touches the
    database, so it is safe alongside the single sync gunicorn worker."""
    global _REFRESH_STARTED
    if _REFRESH_STARTED:
        return
    _REFRESH_STARTED = True
    threading.Thread(target=_background_loop, name="live-feed-refresh",
                     daemon=True).start()
