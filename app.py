"""RadheEx-style demo clone (original code, points only).

A Flask + SQLite web app: sportsbook with back/lay and fancy markets,
a points wallet with exposure accounting, settlement, account reports,
and a casino lobby (provider slots are placeholders). No real money, no
provider integration. Odds come from the client's read-only guest
delayed feed (delayed, not real-time) for live events, plus simulated
fixtures for demo events -- see README.md for the feed seam.
"""
import hashlib
import json
import math
import os
import re
import secrets
import sqlite3
import threading
import time
import urllib.request
from datetime import datetime, timedelta, timezone

from flask import Flask, Response, g, jsonify, request, send_from_directory, session
from werkzeug.security import check_password_hash, generate_password_hash

import live_feed

DEFAULT_STAKES = [100, 500, 1000, 5000, 10000, 50000]


class InsufficientFunds(Exception):
    """Raised by _casino_wallet when the conditional deduction finds the
    user cannot cover the stake. Converted to a 400 by the app's
    error handler; any uncommitted writes in the request are discarded
    by teardown, so call sites need no cleanup."""


USERNAME_RE = re.compile(r"^[A-Za-z0-9_.\-]{3,32}$")
MIN_PASSWORD_LEN = 8

# ---- casino game tables (original numbers, tuned to ~1-3% house edge) ----
# Plinko: bin multipliers per risk level and row count. Rows are limited
# to 8/12/16 so every table is explicit and auditable; each table's
# binomial-weighted return sits between 0.97 and 1.00.
PLINKO_MULT = {
    "low": {
        8: [5.6, 2.1, 1.1, 1, 0.5, 1, 1.1, 2.1, 5.6],
        12: [10, 4, 2, 1.3, 1.1, 0.9, 0.6, 0.9, 1.1, 1.3, 2, 4, 10],
        16: [12, 6, 3, 2, 1.4, 1.3, 1, 0.9, 0.7, 0.9, 1, 1.3, 1.4, 2, 3, 6, 12],
    },
    "medium": {
        8: [13, 3, 1.3, 0.7, 0.4, 0.7, 1.3, 3, 13],
        12: [25, 8, 3, 1.4, 1, 0.8, 0.6, 0.8, 1, 1.4, 3, 8, 25],
        16: [100, 30, 12, 5, 2.2, 1.3, 1, 0.7, 0.4, 0.7, 1, 1.3, 2.2, 5, 12, 30, 100],
    },
    "high": {
        8: [29, 4, 1.5, 0.3, 0.2, 0.3, 1.5, 4, 29],
        12: [140, 20, 7, 1.8, 0.7, 0.45, 0.2, 0.45, 0.7, 1.8, 7, 20, 140],
        16: [1000, 130, 26, 9, 4, 1.9, 0.5, 0.2, 0.2, 0.2, 0.5, 1.9, 4, 9, 26, 130, 1000],
    },
}
# Keno: payout multiplier per (numbers picked, hits). Catch-0 pays only
# on a 10-pick (the classic catch-all). Weighted returns sit ~0.95-0.98.
KENO_PAYTABLE = {
    1: {1: 3.8},
    2: {2: 16},
    3: {3: 45, 2: 2.5},
    4: {4: 140, 3: 6, 2: 1.2},
    5: {5: 500, 4: 25, 3: 4},
    6: {6: 2000, 5: 80, 4: 8, 3: 1.5},
    7: {7: 7000, 6: 400, 5: 20, 4: 3, 3: 1},
    8: {8: 15000, 7: 1200, 6: 90, 5: 12, 4: 2, 3: 0.5},
    9: {9: 40000, 8: 4000, 7: 400, 6: 40, 5: 8, 4: 2},
    10: {10: 100000, 9: 5000, 8: 800, 7: 100, 6: 20, 5: 4, 4: 1, 0: 2},
}
# ---- batch-2 games (nekzabirov rules, reimplemented in Flask) ----
# TeleFly: bustabit-style crash, RTP 0.96, curve exp(0.07*t), 15s betting
# window (engine uses 10s; 15s plays better on a polling demo client),
# 4s crashed pause. Lucky Cups: fair odds 3.0x, paid 2.91x (3% edge --
# the engine's x2.0 payout is a 33% edge and is NOT copied). PvP Wheel:
# stake-weighted ticket, winner takes 95% of the pot (engine pays 100%;
# the task's edge rule overrides). Lottery: 10-minute rounds (engine
# uses 2h; 10 min keeps a demo round observable), pari-mutuel tiers
# from the pot, unclaimed shares + house 5% roll into the next round.
TELEFLY_RTP = 0.96
TELEFLY_GROWTH = 0.07
TELEFLY_BETTING_MS = 15000
TELEFLY_CRASH_PAUSE_MS = 4000
CUPS_PAYOUT = 2.91
PVP_EDGE = 0.05
PVP_COUNTDOWN_MS = 10000
PVP_SPIN_MS = 6000
LOTTERY_ROUND_MS = 600000
LOTTERY_TIERS = {6: 0.50, 5: 0.20, 4: 0.15, 3: 0.10}

# ---- batch-3 games (originals, TCS logic used as reference only) ----
# Roulette: European single-zero wheel. Payouts are TOTAL returns
# (stake back + profit): straight 36x, dozens/columns 3x, even-money
# 2x. The 2.70% edge falls out of the 37 pockets, not a fudge factor.
ROULETTE_RED = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}
ROULETTE_BET_TYPES = ("straight", "red", "black", "even", "odd", "low", "high",
                      "dozen", "column")


def _roulette_bet_win(bet, number):
    """Return the total-return multiplier for one bet, or 0 on loss."""
    t = bet["type"]
    if t == "straight":
        return 36 if number == bet["value"] else 0
    if number == 0:
        return 0
    if t == "red":
        return 2 if number in ROULETTE_RED else 0
    if t == "black":
        return 2 if number not in ROULETTE_RED else 0
    if t == "even":
        return 2 if number % 2 == 0 else 0
    if t == "odd":
        return 2 if number % 2 == 1 else 0
    if t == "low":
        return 2 if 1 <= number <= 18 else 0
    if t == "high":
        return 2 if 19 <= number <= 36 else 0
    if t == "dozen":
        return 3 if (bet["value"] - 1) * 12 < number <= bet["value"] * 12 else 0
    if t == "column":
        return 3 if number % 3 == bet["value"] % 3 else 0
    return 0


# Blackjack: 6-deck shoe, dealer stands on all 17s, blackjack pays 3:2.
BJ_RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
BJ_SUITS = ["♠", "♥", "♦", "♣"]
BJ_NUM_DECKS = 6
BJ_RESHUFFLE_AT = 52


def _bj_new_shoe():
    cards = [{"rank": r, "suit": s} for _ in range(BJ_NUM_DECKS)
             for s in BJ_SUITS for r in BJ_RANKS]
    secrets.SystemRandom().shuffle(cards)
    return cards


def _bj_value(cards):
    """Best blackjack total: highest <= 21, else the lowest bust total.
    Returns (total, soft) where soft means an ace counts as 11."""
    total = 0
    aces = 0
    for c in cards:
        if c["rank"] == "A":
            aces += 1
            total += 11
        elif c["rank"] in ("J", "Q", "K"):
            total += 10
        else:
            total += int(c["rank"])
    soft = aces > 0 and total <= 21
    while total > 21 and aces:
        total -= 10
        aces -= 1
    return total, soft


def _bj_is_blackjack(cards):
    return len(cards) == 2 and _bj_value(cards)[0] == 21


# Batch 4a card helpers (module level so tests can use them).
def _cards_new_deck():
    """One fresh 52-card deck, shuffled with secrets."""
    deck = [{"rank": r, "suit": s} for s in BJ_SUITS for r in BJ_RANKS]
    secrets.SystemRandom().shuffle(deck)
    return deck


def _dice_roll(n=1):
    """Roll n six-sided dice with secrets. Module-level so tests can
    force deterministic sequences by monkeypatching."""
    return [secrets.randbelow(6) + 1 for _ in range(n)]


def _dice_single_mult(matches):
    """Total-return multiplier for a single-number dice bet (sic bo /
    chuck-a-luck): 1 match 2x, 2 matches 3x, 3 matches 15x (14:1 profit).
    Edge 2.78%. The standard 3:1 profit on triples is a 7.87% edge, so
    the triple payout is raised here to bring the game in line."""
    return {0: 0.0, 1: 2.0, 2: 3.0, 3: 15.0}[matches]


def _tower_draw():
    """One Tower level draw: True = safe (78% survival). Module-level
    so tests can force deterministic climb/bust sequences."""
    return secrets.randbelow(100) < 78


# Big Six wheel: standard 54-segment layout (24/15/7/4/2/1/1) with
# standard payouts (total-return). Edges run 11.1-22.2% — documented
# as the published game, like Caribbean Stud in batch 4a: forcing
# 1-3% would need unrecognisable payouts ($1 at ~2.18x), so the
# authentic wheel is kept and the edges are stated, not hidden.
BIGSIX_SEGMENTS = (["1"] * 24 + ["2"] * 15 + ["5"] * 7 + ["10"] * 4
                    + ["20"] * 2 + ["joker", "logo"])
BIGSIX_PAY = {"1": 2.0, "2": 3.0, "5": 6.0, "10": 11.0, "20": 21.0,
              "joker": 46.0, "logo": 46.0}

# Mini roulette: 13 pockets (0-12), standard payouts. Edge 7.69% on
# every bet — again the published game, documented, not adjusted.
MINI_RED = {1, 3, 5, 7, 9, 11}
MINI_BET_TYPES = ("straight", "red", "black", "even", "odd",
                  "low", "high", "dozen")

_POKER_ORDER = {"A": 14, "K": 13, "Q": 12, "J": 11}

def _poker_val(card):
    r = card["rank"]
    if r in _POKER_ORDER:
        return _POKER_ORDER[r]
    return int(r)

def _poker_rank(cards):
    """Return (category, tiebreak) for 3- or 5-card poker hands.
    5-card categories: 8 straight flush, 7 quads, 6 full house,
    5 flush, 4 straight, 3 trips, 2 two pair, 1 pair, 0 high card.
    3-card categories: 5 straight flush, 4 trips, 3 straight,
    2 flush, 1 pair, 0 high card. Aces count high, and low in
    wheel straights (A-2-3, A-2-3-4-5). Tiebreak tuples compare
    lexicographically within a category."""
    vals = [_poker_val(c) for c in cards]
    n = len(cards)
    uniq = sorted(set(vals))
    straight_high = None
    if len(uniq) == n:
        if uniq[-1] - uniq[0] == n - 1:
            straight_high = uniq[-1]
        elif uniq == [2, 3, 14]:
            straight_high = 3
        elif uniq == [2, 3, 4, 5, 14]:
            straight_high = 5
    flush = len(set(c["suit"] for c in cards)) == 1
    counts = {}
    for v in vals:
        counts[v] = counts.get(v, 0) + 1
    groups = sorted(counts.items(), key=lambda kv: (kv[1], kv[0]), reverse=True)
    expanded = tuple(v for v, c in groups for _ in range(c))
    shape = sorted(counts.values(), reverse=True)
    if n == 5:
        if straight_high is not None and flush:
            return 8, (straight_high,)
        if shape == [4, 1]:
            return 7, expanded
        if shape == [3, 2]:
            return 6, expanded
        if flush:
            return 5, tuple(sorted(vals, reverse=True))
        if straight_high is not None:
            return 4, (straight_high,)
        if shape == [3, 1, 1]:
            return 3, expanded
        if shape == [2, 2, 1]:
            return 2, expanded
        if shape == [2, 1, 1, 1]:
            return 1, expanded
        return 0, tuple(sorted(vals, reverse=True))
    if straight_high is not None and flush:
        return 5, (straight_high,)
    if shape == [3]:
        return 4, expanded
    if straight_high is not None:
        return 3, (straight_high,)
    if flush:
        return 2, tuple(sorted(vals, reverse=True))
    if shape == [2, 1]:
        return 1, expanded
    return 0, tuple(sorted(vals, reverse=True))

def _bac_card_value(card):
    if card["rank"] == "A":
        return 1
    if card["rank"] in ("10", "J", "Q", "K"):
        return 0
    return int(card["rank"])

def _bac_value(cards):
    return sum(_bac_card_value(c) for c in cards) % 10

def _bac_play(deck):
    player = [deck.pop(0), deck.pop(0)]
    banker = [deck.pop(0), deck.pop(0)]
    if _bac_value(player) < 8 and _bac_value(banker) < 8:
        if _bac_value(player) <= 5:
            third = deck.pop(0)
            player.append(third)
            tv = _bac_card_value(third)
            bv = _bac_value(banker)
            draw = (bv <= 2 or (bv == 3 and tv != 8)
                    or (bv == 4 and tv in (2, 3, 4, 5, 6, 7))
                    or (bv == 5 and tv in (4, 5, 6, 7))
                    or (bv == 6 and tv in (6, 7)))
            if draw:
                banker.append(deck.pop(0))
        elif _bac_value(banker) <= 5:
            banker.append(deck.pop(0))
    return player, banker



# Slots: 5x3 video slot, 10 paylines, one weight table shared by all
# reels (auditable). Line wins pay paytable x (stake / 10): the stake
# is spread across the 10 lines. Scatter pays x total stake.
# Free spins: 3+ scatters award 10 free spins (retriggerable); all wins
# pay 2x during free spins. Weights/paytable below simulate to an RTP
# in the 94-97% band (see README; measured with /tmp/sim_slots.py).
SLOTS_SYMBOLS = ["9", "10", "J", "Q", "K", "A", "CH", "LE", "BE", "DI", "SEVEN", "SC"]
# Weights sum to 1000. Low symbols dominate the grid (as in real
# slots); the scatter sits at 2.3% per cell, giving a ~0.6% free-spin
# trigger rate. Line wins pay paytable x (stake / 10): the stake is
# spread across the 10 lines.
SLOTS_WEIGHTS = {"9": 200, "10": 180, "J": 160, "Q": 130, "K": 100, "A": 70,
                 "CH": 50, "LE": 40, "BE": 25, "DI": 15, "SEVEN": 7, "SC": 23}
SLOTS_LINES = [
    [1, 1, 1, 1, 1], [0, 0, 0, 0, 0], [2, 2, 2, 2, 2],
    [0, 1, 2, 1, 0], [2, 1, 0, 1, 2], [0, 1, 0, 1, 0],
    [2, 1, 2, 1, 2], [1, 0, 1, 0, 1], [1, 2, 1, 2, 1],
    [1, 0, 0, 0, 1],
]
# Line paytable: {symbol: {run_length: multiplier of per-line bet}}.
# A 3-of-a-kind on one line is rare (~0.1-0.6% per line per symbol),
# so the multipliers look large; against the TOTAL stake they pay
# 1/10th of the table value. Measured total RTP 96.3% over 300,000
# simulated spins (base 87.7% + free spins 8.6%); see README.
SLOTS_PAYTABLE = {
    "9": {3: 17, 4: 83, 5: 338}, "10": {3: 17, 4: 83, 5: 338},
    "J": {3: 21, 4: 104, 5: 416}, "Q": {3: 21, 4: 104, 5: 416},
    "K": {3: 27, 4: 135, 5: 520}, "A": {3: 33, 4: 166, 5: 676},
    "CH": {3: 52, 4: 260, 5: 1040}, "LE": {3: 68, 4: 338, 5: 1352},
    "BE": {3: 104, 4: 520, 5: 2080}, "DI": {3: 166, 4: 832, 5: 3380},
    "SEVEN": {3: 338, 4: 1664, 5: 6760},
}
# Scatter pays: {count: multiplier of TOTAL stake}.
SLOTS_SCATTER_PAY = {3: 2, 4: 10, 5: 50}
SLOTS_FREE_SPINS = 10
SLOTS_FREE_MULT = 2


def _slots_draw_grid():
    """One 5x3 grid: list of 5 reels, each a list of 3 symbols top-down."""
    symbols = []
    weights = []
    for s in SLOTS_SYMBOLS:
        symbols.append(s)
        weights.append(SLOTS_WEIGHTS[s])
    rng = secrets.SystemRandom()
    return [[rng.choices(symbols, weights=weights)[0] for _ in range(3)]
            for _ in range(5)]


def _slots_evaluate(grid):
    """Pure evaluator (unit-tested directly). Returns (line_wins, scatters)
    where line_wins is a list of {line, symbol, count} for 3+ matching
    symbols from the left on a payline (scatters never complete lines)."""
    line_wins = []
    for li, line in enumerate(SLOTS_LINES):
        sym = grid[0][line[0]]
        if sym == "SC":
            continue
        count = 1
        for col in range(1, 5):
            if grid[col][line[col]] == sym:
                count += 1
            else:
                break
        if count >= 3:
            line_wins.append({"line": li, "symbol": sym, "count": count})
    scatters = sum(1 for col in range(5) for row in range(3)
                   if grid[col][row] == "SC")
    return line_wins, scatters


def _slots_payouts(grid, stake, free=False):
    """Total payout for a grid. Line wins pay paytable x (stake/10);
    scatter pays x total stake. During free spins everything pays 2x."""
    line_wins, scatters = _slots_evaluate(grid)
    mult = SLOTS_FREE_MULT if free else 1
    per_line = stake / 10.0
    wins = []
    total = 0.0
    for w in line_wins:
        pay = round(SLOTS_PAYTABLE[w["symbol"]][w["count"]] * per_line * mult, 2)
        wins.append({**w, "payout": pay})
        total += pay
    scatter_pay = 0.0
    if scatters >= 3:
        scatter_pay = round(SLOTS_SCATTER_PAY[scatters] * stake * mult, 2)
        total += scatter_pay
    return wins, scatters, scatter_pay, round(total, 2)

DEMO_USERNAME = "demo"
DEMO_PASSWORD = "demo123"
DEMO_BALANCE = 100.00
# Generic demo admin for the agent-managed model. NOT a real account:
# change (or remove) these credentials before any real use.
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"
# Guards the per-request DB init in _open: schema creation, lazy column
# migration, and demo seeding all write, so two concurrent first
# requests on a fresh database used to race (duplicate-column ALTER
# failures, UNIQUE violations on the seeded demo/admin/sub-admin rows)
# and 500 the page. One process-wide lock serializes that short block;
# the dev server is single-process, so this is sufficient here.
_INIT_LOCK = threading.Lock()

# Generic demo sub-admin (manages only its own downline). Same warning:
# NOT a real account; change (or remove) before any real use.
SUBADMIN_USERNAME = "subadmin"
SUBADMIN_PASSWORD = "subadmin123"

# Official client demo account (Mataji060 / ronit123) with 2000.00 pts
MATAJI_USERNAME = "Mataji060"
MATAJI_PASSWORD = "ronit123"
MATAJI_BALANCE = 2000.00

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    balance REAL NOT NULL DEFAULT 0,
    exposure REAL NOT NULL DEFAULT 0,
    quick_stakes TEXT NOT NULL DEFAULT '[100,500,1000,5000,10000,50000]',
    role TEXT NOT NULL DEFAULT 'player',   -- player | admin | subadmin
    status TEXT NOT NULL DEFAULT 'active', -- active | suspended
    credit_limit REAL NOT NULL DEFAULT 0,  -- net credit assigned by an admin
    created_by INTEGER REFERENCES users(id),
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS idempotency_keys (
    user_id INTEGER NOT NULL REFERENCES users(id),
    key TEXT NOT NULL,
    path TEXT NOT NULL,
    status INTEGER NOT NULL,
    body TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(user_id, key)
);
CREATE TABLE IF NOT EXISTS matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sport TEXT NOT NULL,
    title TEXT NOT NULL,
    team_a TEXT NOT NULL,
    team_b TEXT NOT NULL,
    status TEXT NOT NULL,          -- live | upcoming | suspended
    start_at TEXT NOT NULL,
    result TEXT,                   -- seeded winner name; revealed on settle
    settled INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS markets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id INTEGER NOT NULL REFERENCES matches(id),
    kind TEXT NOT NULL,            -- bookmaker | fancy
    name TEXT NOT NULL,
    max_stake REAL NOT NULL,
    market_limit REAL NOT NULL,
    settled INTEGER NOT NULL DEFAULT 0,  -- admin settlement (market-level)
    settled_result TEXT,                 -- winning selection name, or 'VOID'
    settled_at TEXT
);
CREATE TABLE IF NOT EXISTS selections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    market_id INTEGER NOT NULL REFERENCES markets(id),
    name TEXT NOT NULL,
    base_back REAL NOT NULL,
    base_lay REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS bets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    match_id INTEGER NOT NULL REFERENCES matches(id),
    market_id INTEGER NOT NULL REFERENCES markets(id),
    selection_id INTEGER NOT NULL REFERENCES selections(id),
    side TEXT NOT NULL,            -- back | lay
    odds REAL NOT NULL,
    stake REAL NOT NULL,
    status TEXT NOT NULL DEFAULT 'unsettled',
    profit REAL,
    placed_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    kind TEXT NOT NULL,            -- BET_PLACED | BET_WON | BET_LOST | CASINO | SETTLEMENT
    amount REAL NOT NULL,
    balance_after REAL NOT NULL,
    note TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    text TEXT NOT NULL,
    is_read INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS casino_games (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    game TEXT NOT NULL,
    state TEXT NOT NULL,
    stake REAL NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    created_at TEXT NOT NULL
);
-- Batch-2 shared-round tables (TeleFly, PvP Wheel, Lottery). Round
-- state is derived from wall-clock timestamps and settled lazily on
-- the next state request, so no background thread is needed on the
-- single-worker demo service. Crash points / wheel winners are drawn
-- at round creation or spin time and are NEVER sent to clients early.
CREATE TABLE IF NOT EXISTS telefly_rounds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    crash_point REAL NOT NULL,
    betting_end INTEGER NOT NULL,
    fly_start INTEGER NOT NULL,
    crash_time INTEGER NOT NULL,
    settled INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS telefly_bets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    round_id INTEGER NOT NULL REFERENCES telefly_rounds(id),
    user_id INTEGER NOT NULL REFERENCES users(id),
    stake REAL NOT NULL,
    cashed INTEGER NOT NULL DEFAULT 0,
    cashout_mult REAL,
    payout REAL NOT NULL DEFAULT 0,
    UNIQUE(round_id, user_id)
);
CREATE TABLE IF NOT EXISTS pvp_rounds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    status TEXT NOT NULL DEFAULT 'waiting',
    pot REAL NOT NULL DEFAULT 0,
    winner_id INTEGER REFERENCES users(id),
    winning_number REAL,
    countdown_end INTEGER,
    spin_end INTEGER,
    settled INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS pvp_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    round_id INTEGER NOT NULL REFERENCES pvp_rounds(id),
    user_id INTEGER NOT NULL REFERENCES users(id),
    stake REAL NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS lottery_rounds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    draw_at INTEGER NOT NULL,
    numbers TEXT,
    pot REAL NOT NULL DEFAULT 0,
    rollover_in REAL NOT NULL DEFAULT 0,
    rollover_out REAL NOT NULL DEFAULT 0,
    settled INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS lottery_tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    round_id INTEGER NOT NULL REFERENCES lottery_rounds(id),
    user_id INTEGER NOT NULL REFERENCES users(id),
    numbers TEXT NOT NULL,
    stake REAL NOT NULL,
    payout REAL,
    UNIQUE(round_id, user_id)
);
-- Per-round casino history (completed rounds only): written whenever a
-- casino game settles a balance adjustment. Past play before this table
-- existed is NOT backfilled -- history starts when the table does.
CREATE TABLE IF NOT EXISTS game_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    game TEXT NOT NULL,            -- game name (history kept for future games)
    stake REAL NOT NULL,
    payout REAL NOT NULL,
    profit REAL NOT NULL,
    outcome TEXT NOT NULL,
    created_at TEXT NOT NULL
);
-- Admin audit trail: every credit change, suspension, password reset,
-- settlement and notice is recorded here. Password values are NEVER
-- written to this log (or anywhere else).
CREATE TABLE IF NOT EXISTS admin_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    admin_id INTEGER NOT NULL REFERENCES users(id),
    target_user_id INTEGER REFERENCES users(id),
    action TEXT NOT NULL,          -- CREATE_PLAYER | ADD_CREDIT | DEDUCT_CREDIT
                                   -- | SUSPEND | ACTIVATE | RESET_PASSWORD
                                   -- | SETTLE_MARKET | NOTICE
    detail TEXT NOT NULL,
    amount REAL,
    created_at TEXT NOT NULL
);
-- Site notices posted by an admin, shown on the home page. Only one is
-- active at a time; posting a new notice deactivates the old ones.
CREATE TABLE IF NOT EXISTS notices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT NOT NULL,
    created_by INTEGER NOT NULL REFERENCES users(id),
    created_at TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1
);
"""


def _split_teams(name):
    """Split an event name like 'Blackburn v Stoke' into two team names."""
    for sep in (" v ", " vs ", " V ", " VS "):
        if sep in name:
            a, b = name.split(sep, 1)
            return a.strip(), b.strip()
    return name, ""


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def ticked_odds(selection_id, base_back, base_lay):
    """Simulated odds engine: deterministic jitter per 10-second bucket.

    Odds move slightly over time so the board looks alive, but the value
    is a pure function of (selection, time bucket) -- no external feed.
    A real feed would replace this function with live prices.
    """
    bucket = int(time.time()) // 10
    digest = hashlib.md5(f"{selection_id}:{bucket}".encode()).hexdigest()
    jitter = (int(digest[:4], 16) % 21 - 10) / 100.0  # -0.10 .. +0.10
    back = max(1.01, round(base_back + jitter, 2))
    lay = max(back, round(base_lay + jitter, 2))
    return back, lay


def seed_data(db):
    """Seed matches, markets, selections and the generic demo account."""
    # Guard on matches, not users: ensure_admin() may already have
    # inserted the demo admin, and that must not skip the fixtures.
    if db.execute("SELECT COUNT(*) FROM matches").fetchone()[0] > 0:
        return
    db.execute(
        "INSERT INTO users (username, password_hash, balance, exposure, created_at)"
        " VALUES (?, ?, ?, 0, ?)",
        (DEMO_USERNAME, generate_password_hash(DEMO_PASSWORD), DEMO_BALANCE, now_iso()),
    )
    demo_id = db.execute(
        "SELECT id FROM users WHERE username = ?", (DEMO_USERNAME,)
    ).fetchone()[0]
    db.execute(
        "INSERT INTO notifications (user_id, text, created_at) VALUES (?, ?, ?)",
        (demo_id, "Welcome to the demo exchange. Simulated odds, points wallet only.", now_iso()),
    )
    now = datetime.now(timezone.utc)
    # (sport, title, team_a, team_b, status, start offset minutes, winner)
    fixtures = [
        ("Cricket", "NPL 2026: Match 12", "Kirtipur Kings", "Pokhara Stars",
         "live", -25, "Kirtipur Kings"),
        ("Cricket", "NPL 2026: Match 13", "Lalitpur Lions", "Chitwan Rhinos",
         "upcoming", 45, "Chitwan Rhinos"),
        ("Cricket", "WBBL 2026: Semi Final", "Sydney Stars", "Melbourne Blaze",
         "suspended", 120, "Sydney Stars"),
        ("Soccer", "Premier League: Matchday 14", "North United", "Harbour City",
         "live", -40, "North United"),
        ("Soccer", "La Liga: Matchday 15", "Real Costa", "Atletico Bay",
         "upcoming", 90, "Atletico Bay"),
        ("Tennis", "ATP Finals: Semi", "A. Sharma", "R. Novak",
         "upcoming", 30, "R. Novak"),
        ("Tennis", "WTA Tour: Quarter", "M. Lee", "S. Patel",
         "live", -15, "M. Lee"),
    ]
    for sport, title, a, b, status, offset, winner in fixtures:
        start_at = (now + timedelta(minutes=offset)).isoformat()
        cur = db.execute(
            "INSERT INTO matches (sport, title, team_a, team_b, status, start_at, result)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (sport, title, a, b, status, start_at, winner),
        )
        mid = cur.lastrowid
        # Bookmaker market (back/lay on each team)
        cur = db.execute(
            "INSERT INTO markets (match_id, kind, name, max_stake, market_limit)"
            " VALUES (?, 'bookmaker', 'Bookmaker 0 Commission', 100000, 1000000)",
            (mid,),
        )
        mk = cur.lastrowid
        db.execute(
            "INSERT INTO selections (market_id, name, base_back, base_lay) VALUES (?, ?, 1.85, 1.88)",
            (mk, a),
        )
        db.execute(
            "INSERT INTO selections (market_id, name, base_back, base_lay) VALUES (?, ?, 2.05, 2.08)",
            (mk, b),
        )
        # Fancy market (Yes/No session line)
        cur = db.execute(
            "INSERT INTO markets (match_id, kind, name, max_stake, market_limit)"
            " VALUES (?, 'fancy', 'Fancy: Total Score Over 160.5', 50000, 500000)",
            (mid,),
        )
        mk = cur.lastrowid
        db.execute(
            "INSERT INTO selections (market_id, name, base_back, base_lay) VALUES (?, ?, 1.90, 1.92)",
            (mk, "Yes"),
        )
        db.execute(
            "INSERT INTO selections (market_id, name, base_back, base_lay) VALUES (?, ?, 1.90, 1.92)",
            (mk, "No"),
        )
    db.commit()


def ensure_admin(db):
    """Guarantee the generic demo admin exists, including on databases
    created before the admin role existed. Idempotent: inserts only when
    no admin user is present. Demo credentials only -- see the bold
    warning in README.md."""
    row = db.execute("SELECT id FROM users WHERE role = 'admin' LIMIT 1").fetchone()
    if row:
        return
    # INSERT OR IGNORE: the seeder runs on every request, so two
    # concurrent first requests could both pass the check above; the
    # loser must silently insert nothing instead of raising a UNIQUE
    # violation (which used to 500 the home page on fresh databases).
    db.execute(
        "INSERT OR IGNORE INTO users (username, password_hash, balance, exposure, role, status,"
        " credit_limit, created_at) VALUES (?, ?, 0, 0, 'admin', 'active', 0, ?)",
        (ADMIN_USERNAME, generate_password_hash(ADMIN_PASSWORD), now_iso()),
    )
    db.commit()


def ensure_subadmin(db):
    """Guarantee the generic demo sub-admin exists, mirroring
    ensure_admin. Idempotent: inserts only when no sub-admin user is
    present. Demo credentials only -- see the bold warning in README.md."""
    row = db.execute("SELECT id FROM users WHERE role = 'subadmin' LIMIT 1").fetchone()
    if row:
        return
    # INSERT OR IGNORE: same first-request race as ensure_admin (see
    # there) -- the loser must not raise a UNIQUE violation.
    db.execute(
        "INSERT OR IGNORE INTO users (username, password_hash, balance, exposure, role, status,"
        " credit_limit, created_at) VALUES (?, ?, 0, 0, 'subadmin', 'active', 0, ?)",
        (SUBADMIN_USERNAME, generate_password_hash(SUBADMIN_PASSWORD), now_iso()),
    )
    db.commit()


def ensure_mataji(db):
    """Guarantee the official client demo account Mataji060 exists with 2000.00 balance."""
    row = db.execute("SELECT id FROM users WHERE username = ?", (MATAJI_USERNAME,)).fetchone()
    if row:
        return
    db.execute(
        "INSERT OR IGNORE INTO users (username, password_hash, balance, exposure, role, status,"
        " credit_limit, created_at) VALUES (?, ?, ?, 0, 'player', 'active', 0, ?)",
        (MATAJI_USERNAME, generate_password_hash(MATAJI_PASSWORD), MATAJI_BALANCE, now_iso()),
    )
    db.commit()


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(g.app_config["DATABASE"])
        g.db.row_factory = sqlite3.Row
    return g.db


def current_user():
    # Server-side sessions: the cookie holds only a random token id;
    # the row must exist. Logout, suspension and password changes delete
    # rows, so a pre-logout cookie stops authenticating immediately
    # (Flask's signed cookie alone would keep verifying forever).
    token = session.get("sid")
    if not token:
        return None
    row = get_db().execute(
        "SELECT user_id, created_at FROM sessions WHERE token = ?", (token,)).fetchone()
    if not row:
        return None
    # Absolute session cap: the Flask cookie enforces a 24h idle
    # window, but an actively-used stolen cookie would refresh forever
    # and server rows were never expiry-checked. A session older than
    # 7 days stops authenticating, whatever the cookie says; 7 days is
    # far beyond any demo walkthrough. Unparseable timestamps fail
    # open (rows are only ever written by _create_session, so this
    # should not happen).
    try:
        created = datetime.fromisoformat(row["created_at"])
    except (TypeError, ValueError):
        created = None
    if created is not None:
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) - created > timedelta(days=7):
            return None
    return get_db().execute("SELECT * FROM users WHERE id = ?",
                            (row["user_id"],)).fetchone()


def user_view(row):
    return {
        "id": row["id"],
        "username": row["username"],
        "balance": round(row["balance"], 2),
        "exposure": round(row["exposure"], 2),
        "available": round(row["balance"] - row["exposure"], 2),
        "quick_stakes": json.loads(row["quick_stakes"]),
        "role": row["role"] if "role" in row.keys() else "player",
        "status": row["status"] if "status" in row.keys() else "active",
    }


def admin_player_view(row, created_by_name=None):
    """Full admin-side player row (never includes any password data)."""
    view = user_view(row)
    view["credit_limit"] = round(row["credit_limit"], 2)
    view["created_by"] = created_by_name
    view["created_at"] = row["created_at"]
    return view


def add_transaction(db, user_id, kind, amount, balance_after, note):
    db.execute(
        "INSERT INTO transactions (user_id, kind, amount, balance_after, note, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, kind, amount, round(balance_after, 2), note, now_iso()),
    )


def effective_status(match):
    """Upcoming matches flip to live once their start time passes, so the
    In-Play count and the match list can never disagree (original bug)."""
    if match["status"] == "upcoming":
        start = datetime.fromisoformat(match["start_at"])
        if start <= datetime.now(timezone.utc):
            return "live"
    return match["status"]


def match_view(row, db):
    markets = []
    for m in db.execute("SELECT * FROM markets WHERE match_id = ?", (row["id"],)):
        sels = []
        for s in db.execute("SELECT * FROM selections WHERE market_id = ?", (m["id"],)):
            back, lay = ticked_odds(s["id"], s["base_back"], s["base_lay"])
            sels.append({"id": s["id"], "name": s["name"], "back": back, "lay": lay})
        markets.append({
            "id": m["id"], "kind": m["kind"], "name": m["name"],
            "max_stake": m["max_stake"], "market_limit": m["market_limit"],
            "selections": sels,
        })
    return {
        "id": row["id"], "sport": row["sport"], "title": row["title"],
        "team_a": row["team_a"], "team_b": row["team_b"],
        "status": effective_status(row), "start_at": row["start_at"],
        "settled": bool(row["settled"]),
        "result": row["result"] if row["settled"] else None,
        "live_event_id": row.get("live_event_id"),
        "markets": markets,
    }


def create_app(test_config=None):
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config["DATABASE"] = os.path.join(os.path.dirname(__file__), "app.db")
    if test_config:
        app.config.update(test_config)
    secret_key = os.environ.get("SECRET_KEY")
    if not secret_key:
        if app.config.get("TESTING") or os.environ.get("FLASK_ENV") == "development" or not os.environ.get("RENDER"):
            secret_key = "dev-secret-key-radheex-2026-local"
        else:
            raise RuntimeError("SECRET_KEY environment variable is not set")
    app.config["SECRET_KEY"] = secret_key
    # Security audit (2026-11-03): session cookies are locked down.
    # SECURE is off for local development (plain-http); production enables it.
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = os.environ.get("RENDER") is not None
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=24)

    # ---- security helpers (closure state, per app instance) ----
    # Rate-limit buckets: key -> list of event timestamps (monotonic).
    # In-memory is correct for the single-worker deployment; a future
    # multi-worker setup must move these to shared storage (Redis/DB).
    _RATE_BUCKETS = {}
    _RATE_LOCK = threading.Lock()

    def _rate_over(key, limit, window_s):
        """True if the bucket already holds `limit` events in the window
        (peek only -- a blocked attempt does not grow the bucket)."""
        now = time.monotonic()
        with _RATE_LOCK:
            stamps = [t for t in _RATE_BUCKETS.get(key, []) if now - t < window_s]
            _RATE_BUCKETS[key] = stamps
            return len(stamps) >= limit

    def _rate_record(key):
        now = time.monotonic()
        with _RATE_LOCK:
            if len(_RATE_BUCKETS) > 5000:
                for k in [k for k, v in _RATE_BUCKETS.items()
                          if not v or now - v[-1] > 3600]:
                    _RATE_BUCKETS.pop(k, None)
            _RATE_BUCKETS.setdefault(key, []).append(now)

    def _rate_clear(key):
        with _RATE_LOCK:
            _RATE_BUCKETS.pop(key, None)

    def _client_ip():
        # Deliberately NOT X-Forwarded-For: the leftmost entry is
        # client-controlled, so rotating it defeated the per-IP login
        # brake (15 spoofed fails, zero 429s). The direct peer address
        # is the only value the client cannot choose; there is no
        # trusted-proxy list to validate XFF against.
        return request.remote_addr or "unknown"

    def _create_session(db, user_id):
        token = secrets.token_urlsafe(32)
        db.execute("INSERT INTO sessions (token, user_id, created_at)"
                   " VALUES (?, ?, ?)", (token, user_id, now_iso()))
        return token

    def _revoke_user_sessions(db, user_id, except_token=None):
        if except_token:
            db.execute("DELETE FROM sessions WHERE user_id = ? AND token != ?",
                       (user_id, except_token))
        else:
            db.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))

    def _csrf_token():
        tok = session.get("csrf")
        if not tok:
            tok = secrets.token_urlsafe(32)
            session["csrf"] = tok
        return tok

    @app.get("/api/csrf-token")
    def csrf_token():
        # Anonymous-safe: login POSTs need a token too, so the
        # SPA fetches this on load, before any POST. The token lives in
        # the signed session cookie and is preserved across login so a
        # logged-in SPA never has to re-fetch mid-flow.
        return jsonify({"token": _csrf_token()})

    @app.after_request
    def _after_security(resp):
        # Security headers. No full Content-Security-Policy: the SPA
        # uses inline styles/handlers, so a strict CSP would break
        # pages -- recorded as a deliberate scope call, not an oversight.
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["X-XSS-Protection"] = "1; mode=block"
        resp.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if request.path.startswith("/api/") and session.get("sid") \
                and resp.mimetype == "application/json":
            # Authenticated JSON must not sit in a shared cache where
            # it could serve one user to another. `private` keeps it
            # out of shared caches while `must-revalidate` preserves
            # ETag revalidation (304s) for the feed poll.
            resp.headers["Cache-Control"] = "private, must-revalidate"
        elif request.path == "/" or request.path.startswith("/static/"):
            resp.headers["Cache-Control"] = "no-cache, must-revalidate"
        if request.method == "POST" and 200 <= resp.status_code < 300:
            key = request.headers.get("X-Idempotency-Key")
            if key:
                user = current_user()
                if user:
                    db = get_db()
                    try:
                        db.execute(
                            "INSERT OR REPLACE INTO idempotency_keys"
                            " (user_id, key, path, status, body, created_at)"
                            " VALUES (?, ?, ?, ?, ?, ?)",
                            (user["id"], key, request.path, resp.status_code,
                             resp.get_data(as_text=True), now_iso()))
                        db.execute(
                            "DELETE FROM idempotency_keys WHERE created_at < ?",
                            ((datetime.now(timezone.utc) - timedelta(hours=24))
                             .isoformat(),))
                        db.commit()
                    except Exception:
                        pass
        return resp

    @app.errorhandler(InsufficientFunds)
    def _insufficient_funds(err):
        return jsonify({"error": "Insufficient available balance."}), 400

    # Optimization pass: refresh the hot feed paths on a background thread
    # (never under TESTING, where tests stub the fetch and must stay
    # deterministic). The thread never touches the database.
    if not app.config.get("TESTING"):
        live_feed.start_background_refresh()

    @app.before_request
    def _open():
        g.app_config = app.config
        db = get_db()
        with _INIT_LOCK:
            db.executescript(SCHEMA)
            # Live-feed shadow rows: local copies of live events so the normal
            # bet flow can take live bets. Added lazily for existing DBs.
            for table, column in (
                ("matches", "live_event_id"),
                ("markets", "live_market_id"),
                ("selections", "live_runner_id"),
                ("users", "role"),
                ("users", "status"),
                ("users", "credit_limit"),
                ("users", "created_by"),
                ("markets", "settled"),
                ("markets", "settled_result"),
                ("markets", "settled_at"),
            ):
                cols = [r[1] for r in db.execute(f"PRAGMA table_info({table})")]
                if column not in cols:
                    default = {
                        ("users", "role"): "TEXT NOT NULL DEFAULT 'player'",
                        ("users", "status"): "TEXT NOT NULL DEFAULT 'active'",
                        ("users", "credit_limit"): "REAL NOT NULL DEFAULT 0",
                        ("users", "created_by"): "INTEGER",
                        ("markets", "settled"): "INTEGER NOT NULL DEFAULT 0",
                        ("markets", "settled_result"): "TEXT",
                        ("markets", "settled_at"): "TEXT",
                    }.get((table, column), "TEXT")
                    db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {default}")
            # Prune expired server-side sessions (see the 7-day cap in
            # current_user): keeps the table bounded. Committed by the
            # db.commit() below.
            cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
            db.execute("DELETE FROM sessions WHERE created_at < ?", (cutoff,))
            db.commit()
            ensure_admin(db)
            ensure_subadmin(db)
            if not app.config.get("TESTING"):
                ensure_mataji(db)
            seed_data(db)

    @app.before_request
    def _csrf_check():
        # Every state-changing API call needs the token. There are no
        # server-rendered <form action> POSTs (the SPA posts via fetch),
        # so a header check covers the whole surface.
        if request.method != "POST" or not request.path.startswith("/api/"):
            return None
        if request.path == "/api/csrf-token":
            return None
        want = session.get("csrf")
        got = request.headers.get("X-CSRF-Token")
        if not want or not got or not secrets.compare_digest(want, got):
            return jsonify({"error": "CSRF token missing or invalid."
                            " Refresh the page and retry."}), 403
        return None

    @app.before_request
    def _suspended_guard():
        # Defense in depth: a suspended player's live session must not
        # act, even on endpoints whose handler forgets the check.
        # Suspension also revokes sessions (see admin_suspend), so this
        # normally never fires -- it is the backstop, not the mechanism.
        if request.method != "POST":
            return None
        if not (request.path == "/api/bets"
                or request.path.startswith("/api/casino/")):
            return None
        user = current_user()
        if user and user["status"] == "suspended":
            return jsonify({"error": "Suspended accounts cannot play or bet."}), 403
        return None

    @app.before_request
    def _idem_replay():
        # Retry safety: a POST retried with the same idempotency key
        # returns the ORIGINAL response without re-executing. The key
        # is per-user and per-path; the SPA also dedups in-flight
        # identical POSTs, so this covers timeouts and manual retries.
        if request.method != "POST":
            return None
        key = request.headers.get("X-Idempotency-Key")
        if not key:
            return None
        user = current_user()
        if not user:
            return None
        row = get_db().execute(
            "SELECT status, body FROM idempotency_keys"
            " WHERE user_id = ? AND key = ? AND path = ?",
            (user["id"], key, request.path)).fetchone()
        if row:
            return Response(row["body"], status=row["status"],
                            content_type="application/json")
        return None

    @app.before_request
    def _json_body_guard():
        # Non-dict JSON bodies 500'd every POST handler (handlers call
        # .get() on the parsed body). Reject them centrally with a
        # clean 400 instead; no handler accepts a non-dict body.
        # (get_json caches, so handlers later read the same object.)
        if request.method != "POST" or not request.path.startswith("/api/"):
            return None
        data = request.get_json(force=True, silent=True)
        if data is not None and not isinstance(data, dict):
            return jsonify({"error": "Request body must be a JSON object."}), 400
        return None

    @app.teardown_appcontext
    def _close(exc=None):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    @app.route("/")
    def index():
        return send_from_directory(app.template_folder, "index.html")

    # ---------------- auth ----------------
    @app.post("/api/auth/login")
    def login():
        data = request.get_json(force=True, silent=True) or {}
        db = get_db()
        username = (data.get("username") or "").strip()
        ip = _client_ip()
        user = db.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
        if not user or not check_password_hash(user["password_hash"], data.get("password") or ""):
            # Brute-force brakes, generous by design: 10 failed tries
            # per username and 100 failed per direct-peer IP per 10
            # minutes. The username bucket is IP-independent so XFF
            # rotation cannot dodge it; the IP bucket uses the direct
            # peer (Render's proxy), not XFF. Demo use never trips
            # these; a password spray does. The 429 replaces the 401
            # (same response either way for a wrong password, so no
            # user enumeration is introduced). Only failures are
            # gated: a correct password always logs in, so the brakes
            # can never lock a legitimate user out.
            user_key = "login-user:" + username.lower()
            ip_key = "login-ip:" + ip
            if _rate_over(user_key, app.config.get("RATE_LIMIT_LOGIN_USER", 10), 600) or \
                    _rate_over(ip_key, app.config.get("RATE_LIMIT_LOGIN_IP", 100), 600):
                return jsonify({"error": "Too many failed logins. Try again"
                                " in a few minutes."}), 429
            _rate_record(user_key)
            _rate_record(ip_key)
            return jsonify({"error": "Invalid username or password."}), 401
        if user["status"] == "suspended":
            return jsonify({"error": "This account is suspended. Contact your admin."}), 401
        _rate_clear("login-user:" + username.lower())
        # Rotate the CSRF token at login: the pre-login token was
        # anonymous, and keeping it across the privilege change is
        # fixation-adjacent. The SPA and the test wrapper both re-fetch
        # + retry once on a CSRF 403, so the next POST picks the new
        # token up transparently.
        session.clear()
        session["csrf"] = secrets.token_urlsafe(32)
        session["sid"] = _create_session(db, user["id"])
        db.commit()
        session.permanent = True
        return jsonify(user_view(user))

    @app.post("/api/auth/logout")
    def logout():
        token = session.get("sid")
        if token:
            db = get_db()
            db.execute("DELETE FROM sessions WHERE token = ?", (token,))
            db.commit()
        session.clear()
        return jsonify({"ok": True})

    @app.get("/api/me")
    def me():
        user = current_user()
        if not user:
            return jsonify({"user": None})
        return jsonify({"user": user_view(user)})

    @app.post("/api/me/password")
    def change_password():
        user = current_user()
        if not user:
            return jsonify({"error": "Login required."}), 401
        data = request.get_json(force=True, silent=True) or {}
        if not check_password_hash(user["password_hash"], data.get("current_password") or ""):
            return jsonify({"error": "Current password is incorrect."}), 400
        if len(data.get("new_password") or "") < MIN_PASSWORD_LEN:
            return jsonify({"error": "New password needs 8+ chars."}), 400
        db = get_db()
        db.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (generate_password_hash(data["new_password"]), user["id"]),
        )
        # A password change kills every OTHER session (a stolen cookie
        # dies with the old password); the current session survives.
        _revoke_user_sessions(db, user["id"], except_token=session.get("sid"))
        db.commit()
        return jsonify({"ok": True})

    @app.get("/api/me/stakes")
    def get_stakes():
        user = current_user()
        if not user:
            return jsonify({"error": "Login required."}), 401
        return jsonify({"quick_stakes": json.loads(user["quick_stakes"])})

    @app.post("/api/me/stakes")
    def set_stakes():
        user = current_user()
        if not user:
            return jsonify({"error": "Login required."}), 401
        data = request.get_json(force=True, silent=True) or {}
        stakes = data.get("quick_stakes")
        if (not isinstance(stakes, list) or len(stakes) != 6
                or any(not isinstance(s, (int, float)) or isinstance(s, bool) for s in stakes)):
            return jsonify({"error": "Provide exactly 6 positive stake values."}), 400
        try:
            stakes = [float(s) for s in stakes]
        except (TypeError, ValueError, OverflowError):
            return jsonify({"error": "Provide exactly 6 positive stake values."}), 400
        # Whole cents only: a sub-cent quick stake is meaningless.
        if any(round(s, 2) != s for s in stakes):
            return jsonify({"error": "Provide exactly 6 positive stake values."}), 400
        if any(not math.isfinite(s) or s <= 0 for s in stakes):
            return jsonify({"error": "Provide exactly 6 positive stake values."}), 400
        db = get_db()
        db.execute(
            "UPDATE users SET quick_stakes = ? WHERE id = ?",
            (json.dumps(stakes), user["id"]),
        )
        db.commit()
        return jsonify({"quick_stakes": stakes})

    # ---------------- sportsbook ----------------
    @app.get("/api/sports")
    def sports():
        db = get_db()
        out = []
        for row in db.execute(
                "SELECT DISTINCT sport FROM matches WHERE live_event_id IS NULL ORDER BY sport"):
            ms = [dict(r) for r in db.execute(
                "SELECT * FROM matches WHERE sport = ? AND live_event_id IS NULL",
                (row["sport"],))]
            live = sum(1 for m in ms if effective_status(m) == "live")
            out.append({"sport": row["sport"], "live_count": live, "total": len(ms)})
        return jsonify(out)

    @app.get("/api/matches")
    def matches():
        db = get_db()
        sport = request.args.get("sport")
        live_only = request.args.get("live") == "1"
        rows = db.execute(
            "SELECT * FROM matches WHERE live_event_id IS NULL ORDER BY start_at").fetchall()
        out = []
        for r in rows:
            d = dict(r)
            if sport and d["sport"] != sport:
                continue
            status = effective_status(d)
            if live_only and status != "live":
                continue
            view = match_view(d, db)
            view["markets"] = []  # list view stays light; detail loads markets
            out.append(view)
        return jsonify(out)

    @app.get("/api/matches/<int:match_id>")
    def match_detail(match_id):
        db = get_db()
        row = db.execute("SELECT * FROM matches WHERE id = ?", (match_id,)).fetchone()
        if not row:
            return jsonify({"error": "Match not found."}), 404
        return jsonify(match_view(dict(row), db))

    # ---------------- live delayed feed ----------------
    # Optimization pass: serve pre-serialized snapshots with ETags, so a
    # poll whose payload did not change costs a 304 (headers only) instead
    # of the full body. If-None-Match: * matches any current representation.
    def _serve_cached(body, etag):
        inm = request.headers.get("If-None-Match") or ""
        if inm.strip() == "*" or (etag and etag in inm):
            resp = app.response_class(status=304)
            resp.headers["ETag"] = etag
            return resp
        resp = app.response_class(body, status=200, mimetype="application/json")
        resp.headers["ETag"] = etag
        return resp

    def _json_etag(data):
        body = json.dumps(data, separators=(",", ":")).encode("utf-8")
        return _serve_cached(body, '"' + hashlib.sha1(body).hexdigest() + '"')

    def _snapshot_response(path, slim):
        """Serve a background snapshot if one is fresh, else refresh it
        once (single-flight inside live_feed) and serve that. Returns None
        when no snapshot exists and the refresh failed, so callers fall
        back to the legacy fetch + simulated-fallback path."""
        live_feed.note_request(path)
        snap = live_feed.snapshot_get(path)
        if snap and time.time() - snap["updated"] < live_feed.SNAPSHOT_FRESH_S:
            if slim and snap["kind"] == "list":
                return _serve_cached(snap["slim_body"], snap["slim_etag"])
            return _serve_cached(snap["body"], snap["etag"])
        try:
            snap = live_feed.refresh_snapshot(path)
        except Exception:
            snap = None
        if snap:
            if slim and snap["kind"] == "list":
                return _serve_cached(snap["slim_body"], snap["slim_etag"])
            return _serve_cached(snap["body"], snap["etag"])
        return None

    # Server-side proxy to the public delayed guest feed (see live_feed.py).
    # Responses always carry "source": "live-delayed" for real feed data, or
    # "simulated-fallback" (plus "error") when upstream failed -- the app
    # never breaks because the feed is down. List routes catch ALL
    # exceptions from fetch/parse (not just LiveFeedError): urllib can
    # raise IncompleteRead/RemoteDisconnected mid-read, and those must
    # fall back, never escape as a 500.
    def _live_list(path, fallback_filter=None):
        slim = request.args.get("slim") == "1"
        resp = _snapshot_response(path, slim)
        if resp is not None:
            return resp
        try:
            raw = live_feed.fetch_json(path)
            events = [live_feed.parse_event_item(it) for it in raw]
            if slim:
                events = live_feed.slim_events(events)
            return _json_etag({"source": "live-delayed", "events": events})
        except Exception as exc:
            db = get_db()
            events = []
            for r in db.execute(
                    "SELECT * FROM matches WHERE live_event_id IS NULL ORDER BY start_at"):
                d = dict(r)
                if fallback_filter and not fallback_filter(d):
                    continue
                events.append(live_feed.simulated_to_live_event(match_view(d, db)))
            if slim:
                events = live_feed.slim_events(events)
            # Generic error only: the upstream exception text (paths,
            # status lines) must never reach clients.
            return jsonify({"source": "simulated-fallback",
                            "error": "Live feed unavailable.",
                            "events": events})

    @app.get("/api/live/current")
    def live_current():
        return _live_list("markets/current")

    @app.get("/api/live/markets")
    def live_markets():
        return _live_list("markets")

    @app.get("/api/live/markets/selected")
    def live_markets_selected():
        """Targeted single-market lookup (?marketids=<marketId>)."""
        marketids = request.args.get("marketids", "")
        if not marketids or not re.fullmatch(r"[0-9.,]+", marketids):
            return jsonify({"error": "Pass ?marketids=<marketId> (digits, dots, commas)."}), 400
        from urllib.parse import quote
        try:
            raw = live_feed.fetch_json(
                f"markets/selected?marketids={quote(marketids, safe='')}")
            events = [live_feed.parse_event_item(it) for it in raw]
            return jsonify({"source": "live-delayed", "events": events})
        except Exception:
            return jsonify({"source": "live-error",
                            "error": "Live feed unavailable."}), 502

    @app.get("/api/live/live")
    def live_live():
        return _live_list("markets/live",
                          lambda d: effective_status(d) == "live")

    @app.get("/api/live/eventtype/<sport_id>")
    def live_eventtype(sport_id):
        # Upstream accepts only 1, 2, 4, 7; anything else is a 400 there,
        # so validate here instead of falling back to simulated data.
        if str(sport_id) not in ("1", "2", "4", "7"):
            return jsonify({"error": "Unknown sport id (accepted: 1, 2, 4, 7)."}), 400
        sport_names = {"4": "Cricket", "1": "Soccer", "2": "Tennis"}
        name = sport_names.get(str(sport_id))
        if name is None:
            # Sport 7 is valid upstream but empty and unnamed -- never
            # present it as a sport; it simply has no events.
            return _live_list(f"markets/eventtype/{sport_id}",
                              lambda d: False)
        return _live_list(f"markets/eventtype/{sport_id}",
                          lambda d: d["sport"] == name)

    @app.get("/api/live/menu")
    def live_menu():
        resp = _snapshot_response("Markets/menu", False)
        if resp is not None:
            return resp
        try:
            raw = live_feed.fetch_json("Markets/menu")
            return _json_etag({"source": "live-delayed", "menu": raw})
        except Exception:
            return jsonify({"source": "simulated-fallback",
                            "error": "Live feed unavailable.",
                            "menu": []})

    @app.get("/api/live/event/<event_id>")
    def live_event(event_id):
        # Digits (with an optional leading minus -- the feed issues
        # negative ids) only: the id goes into an upstream path, so
        # anything else is rejected here rather than forwarded.
        if not re.fullmatch(r"-?[0-9]+", event_id):
            return jsonify({"error": "Event id must be numeric."}), 400
        try:
            raw = live_feed.fetch_json(f"events/detail/{event_id}")
            return _json_etag({"source": "live-delayed",
                               "event": live_feed.parse_event_detail(raw)})
        except Exception:
            return jsonify({"source": "live-error",
                            "error": "Live feed unavailable."}), 502

    @app.post("/api/live/materialize")
    def materialize_live():
        """Create (or reuse) local shadow rows for one live event so the
        normal bet flow can take a bet at the clicked live price. Login
        required. The event must be open and the runner priced. The price
        returned is ALWAYS the server-side feed price (fancy markets
        converted: decimal = 1 + rate/100) -- a client-supplied price is
        never trusted, since it would let anyone invent odds and get
        paid on them at admin settlement."""
        user = current_user()
        if not user:
            return jsonify({"error": "Login required."}), 401
        data = request.get_json(force=True, silent=True) or {}
        event_id = str(data.get("event_id") or "")
        market_id = str(data.get("market_id") or "")
        runner_id = str(data.get("runner_id") or "")
        side = data.get("side")
        if not re.fullmatch(r"-?[0-9]+", event_id) or not market_id \
                or not re.fullmatch(r"[0-9.]+", market_id) \
                or not re.fullmatch(r"[0-9.]+", runner_id) \
                or side not in ("back", "lay"):
            return jsonify({"error": "Invalid live bet selection."}), 400
        try:
            raw = live_feed.fetch_json(f"events/detail/{event_id}")
        except Exception:
            return jsonify({"error": "Live event unavailable."}), 502
        detail = live_feed.parse_event_detail(raw)
        market = next((m for m in detail["markets"]
                       if m["market_id"] == market_id), None)
        if not market:
            return jsonify({"error": "Market not found in live event."}), 404
        runner = next((r for r in market["runners"]
                       if r["id"] == runner_id), None)
        if not runner:
            return jsonify({"error": "Runner not found in live market."}), 404
        if (side == "back" and runner["best_back"] is None) \
                or (side == "lay" and runner["best_lay"] is None):
            # Detail books are often empty; refresh this market's prices
            # through the targeted single-market lookup before deciding.
            try:
                from urllib.parse import quote
                sel_raw = live_feed.fetch_json(
                    f"markets/selected?marketids={quote(market_id, safe='')}")
                sel_events = [live_feed.parse_event_item(it) for it in sel_raw]
                sel_market = next(
                    (e["market"] for e in sel_events
                     if e["market"]["market_id"] == market_id), None)
                if sel_market:
                    sel_runner = next(
                        (r for r in sel_market["runners"]
                         if r["id"] == runner_id), None)
                    if sel_runner and sel_runner["best_back"] is not None:
                        runner = sel_runner
                        market["status"] = sel_market["status"]
                        market["bet_lock"] = sel_market["bet_lock"]
            except Exception:
                pass  # keep detail values; validation below reports it
        if market["status"] != "OPEN" or market["bet_lock"] \
                or runner["status"] != "ACTIVE":
            return jsonify({"error": "This live market is not open for betting."}), 400
        best = runner["best_back"] if side == "back" else runner["best_lay"]
        if best is None:
            return jsonify({"error": "No live price for this selection."}), 400
        # Server-side price: percent-rate markets quote rates (100 = even
        # money), so convert to decimal exactly as the slip displays it.
        # That is the fancy markets (OVERS/BATSMAN) AND bookmaker markets
        # (rates like 78/82, toss 98, outright 500 -- only sensible as
        # percent rates). Standard markets already quote decimal odds.
        # The client-supplied odds value is ignored entirely (see the
        # docstring above).
        def _live_decimal(price):
            if price is None:
                return None
            if market["market_type"] in live_feed.RATE_MARKET_TYPES:
                # Percent rates (100 = even money) -> decimal odds,
                # rounded to cents: unrounded 1 + 82/100 is
                # 1.8199999999999998 in binary float, which would leak
                # into settlement math.
                return round(1 + price / 100, 2)
            return price
        dec_back = _live_decimal(runner["best_back"])
        dec_lay = _live_decimal(runner["best_lay"])
        server_odds = dec_back if side == "back" else dec_lay
        db = get_db()
        row = db.execute("SELECT * FROM matches WHERE live_event_id = ?",
                         (event_id,)).fetchone()
        if row:
            match_id = row["id"]
        else:
            name = detail["event_name"] or ""
            team_a, team_b = _split_teams(name)
            cur = db.execute(
                "INSERT INTO matches (sport, title, team_a, team_b, status, start_at, live_event_id)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (detail["sport"], name, team_a, team_b,
                 "live" if any(m["in_play"] for m in detail["markets"]) else "upcoming",
                 detail["open_date"] or now_iso(), event_id))
            match_id = cur.lastrowid
        mrow = db.execute(
            "SELECT * FROM markets WHERE live_market_id = ? AND match_id = ?",
            (market_id, match_id)).fetchone()
        if mrow:
            mk_id = mrow["id"]
        else:
            max_stake = market["max_bet"] or 100000
            cur = db.execute(
                "INSERT INTO markets (match_id, kind, name, max_stake, market_limit, live_market_id)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (match_id,
                 "bookmaker" if market["market_type"] == "MATCH_ODDS" else "live",
                 market["market_name"], max_stake, max_stake * 10, market_id))
            mk_id = cur.lastrowid
        srow = db.execute(
            "SELECT * FROM selections WHERE live_runner_id = ? AND market_id = ?",
            (runner_id, mk_id)).fetchone()
        if srow:
            sel_id = srow["id"]
            # Feed prices only: never store a client-supplied value, and
            # never overwrite a known side price with a missing one.
            db.execute("UPDATE selections SET base_back = ?, base_lay = ? WHERE id = ?",
                       (dec_back if dec_back is not None else srow["base_back"],
                        dec_lay if dec_lay is not None else srow["base_lay"], sel_id))
        else:
            fallback = dec_back if dec_back is not None else dec_lay
            cur = db.execute(
                "INSERT INTO selections (market_id, name, base_back, base_lay, live_runner_id)"
                " VALUES (?, ?, ?, ?, ?)",
                (mk_id, runner["name"],
                 dec_back if dec_back is not None else fallback,
                 dec_lay if dec_lay is not None else fallback, runner_id))
            sel_id = cur.lastrowid
        db.commit()
        return jsonify({"match_id": match_id, "market_id": mk_id,
                        "selection_id": sel_id, "odds": server_odds,
                        "runner": runner["name"], "market": market["market_name"]})

    @app.post("/api/bets")
    def place_bet():
        user = current_user()
        if not user:
            return jsonify({"error": "Login required."}), 401
        if user["role"] in ("admin", "subadmin"):
            return jsonify({"error": "Admin accounts manage players; they cannot place bets."}), 403
        if user["status"] == "suspended":
            return jsonify({"error": "Suspended accounts cannot place bets."}), 403
        data = request.get_json(force=True, silent=True) or {}
        db = get_db()
        # Serialize against settlement: the settled-check below must
        # not run against a pre-commit snapshot while a settler holds
        # the write lock, or the bet lands on a settled match and
        # strands (proven: 12/12 bursts with a 120-bet settler). With
        # BEGIN IMMEDIATE the check, reservation, and insert all see a
        # consistent state: either the settler committed first (then
        # the settled check below 400s) or this bet commits first
        # (then the settler's remaining-count sees it and reopens).
        db.execute("BEGIN IMMEDIATE")
        match_id = _as_int_id(data.get("match_id"))
        market_id = _as_int_id(data.get("market_id"))
        selection_id = _as_int_id(data.get("selection_id"))
        if match_id is None or market_id is None or selection_id is None:
            return jsonify({"error": "Unknown match, market or selection."}), 400
        match = db.execute("SELECT * FROM matches WHERE id = ?",
                           (match_id,)).fetchone()
        market = db.execute("SELECT * FROM markets WHERE id = ?",
                            (market_id,)).fetchone()
        sel = db.execute("SELECT * FROM selections WHERE id = ?",
                         (selection_id,)).fetchone()
        if not match or not market or not sel or market["match_id"] != match["id"] \
                or sel["market_id"] != market["id"]:
            return jsonify({"error": "Unknown match, market or selection."}), 400
        if market["settled"] or match["settled"]:
            # A bet placed after settlement would sit unsettled forever
            # (its exposure never released) -- reject it outright.
            return jsonify({"error": "This market is already settled; betting is closed."}), 400
        if effective_status(dict(match)) == "suspended":
            return jsonify({"error": "This match is suspended; betting is closed."}), 400
        side = data.get("side")
        if side not in ("back", "lay"):
            return jsonify({"error": "Side must be back or lay."}), 400
        if isinstance(data.get("stake"), bool):
            return jsonify({"error": "Invalid stake."}), 400
        try:
            stake = float(data.get("stake") or 0)
        except (TypeError, ValueError, OverflowError):
            return jsonify({"error": "Invalid stake."}), 400
        if not math.isfinite(stake):
            return jsonify({"error": "Invalid stake."}), 400
        # Whole cents only: a sub-cent stake would either play a free
        # zero-stake round (after rounding down) or silently charge
        # more than typed (after rounding up) -- both are wrong.
        if round(stake, 2) != stake or stake < 0.01:
            return jsonify({"error": "Stake must be 0.01 pts or more, in whole cents."}), 400
        if stake > market["max_stake"]:
            return jsonify({"error": f"Stake exceeds market max of {market['max_stake']:,.0f}."}), 400
        back, lay = ticked_odds(sel["id"], sel["base_back"], sel["base_lay"])
        if match["live_event_id"]:
            # Live shadow rows: the bet goes in at the server-side feed
            # price recorded by materialize, never a client-supplied
            # value -- a client-supplied price would let anyone invent
            # odds and get paid on them at admin settlement.
            odds = sel["base_back"] if side == "back" else sel["base_lay"]
            if odds is None or odds < 1.01:
                return jsonify({"error": "Live price unavailable — re-open the market from the live feed."}), 400
        else:
            odds = back if side == "back" else lay
        liability = stake if side == "back" else round(stake * (odds - 1), 2)
        # Atomic reservation: the availability check and the exposure
        # increase are ONE statement, so two simultaneous bets cannot
        # both reserve the same funds (proven pre-fix: exposure 120 on
        # a 100-pt balance from two concurrent stake-60 bets).
        cur = db.execute(
            "UPDATE users SET exposure = exposure + ? WHERE id = ?"
            " AND ROUND(balance - exposure, 2) >= ?",
            (liability, user["id"], liability))
        if cur.rowcount != 1:
            fresh = db.execute("SELECT * FROM users WHERE id = ?",
                               (user["id"],)).fetchone()
            available = round(fresh["balance"] - fresh["exposure"], 2)
            return jsonify({"error": f"Insufficient available balance ({available:.2f} pts)."}), 400
        db.execute(
            "INSERT INTO bets (user_id, match_id, market_id, selection_id, side, odds, stake, placed_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (user["id"], match["id"], market["id"], sel["id"], side, odds, stake, now_iso()),
        )
        db.commit()
        fresh = db.execute("SELECT * FROM users WHERE id = ?", (user["id"],)).fetchone()
        return jsonify({"ok": True, "odds": odds, "liability": liability,
                        "user": user_view(fresh)})

    @app.get("/api/bets")
    def list_bets():
        user = current_user()
        if not user:
            return jsonify({"error": "Login required."}), 401
        status = request.args.get("status")
        db = get_db()
        q = ("SELECT b.*, m.title AS match_title, mk.name AS market_name,"
             " s.name AS selection_name FROM bets b JOIN matches m ON m.id = b.match_id"
             " JOIN markets mk ON mk.id = b.market_id"
             " JOIN selections s ON s.id = b.selection_id WHERE b.user_id = ?")
        args = [user["id"]]
        if status in ("unsettled", "settled"):
            q += " AND b.status = ?"
            args.append(status)
        q += " ORDER BY b.id DESC LIMIT 200"
        rows = db.execute(q, args).fetchall()
        return jsonify([{
            "id": r["id"], "match_title": r["match_title"], "market_name": r["market_name"],
            "selection_name": r["selection_name"], "side": r["side"], "odds": r["odds"],
            "stake": r["stake"], "status": r["status"], "profit": r["profit"],
            "placed_at": r["placed_at"],
        } for r in rows])

    @app.post("/api/matches/<int:match_id>/settle")
    def settle_match(match_id):
        user = current_user()
        if not user:
            return jsonify({"error": "Login required."}), 401
        db = get_db()
        # Serialize against placement (see place_bet): the claim, the
        # caller's settlement, and the remaining-count must all see
        # one consistent state, or a bet landing mid-settle strands.
        db.execute("BEGIN IMMEDIATE")
        match = db.execute("SELECT * FROM matches WHERE id = ?", (match_id,)).fetchone()
        if not match:
            return jsonify({"error": "Match not found."}), 404
        if match["live_event_id"]:
            return jsonify({"error": "Live events cannot be settled without a results feed."}), 400
        # A caller with no unsettled bets must not flip the match to
        # settled: that closed betting for everyone and revealed the
        # seeded result without settling anything.
        own = db.execute(
            "SELECT COUNT(*) FROM bets WHERE user_id = ? AND match_id = ? AND status = 'unsettled'",
            (user["id"], match_id)).fetchone()[0]
        if not own:
            return jsonify({"error": "No unsettled bets on this match."}), 400
        # Conditional claim: two concurrent settles cannot both pay the
        # same bets. This settles only the CALLER's bets, so the match
        # stays open (settled=0) while ANY user still has unsettled
        # bets on it -- otherwise their exposure would strand forever.
        claim = db.execute(
            "UPDATE matches SET settled = 1 WHERE id = ? AND settled = 0",
            (match_id,))
        if claim.rowcount != 1:
            return jsonify({"error": "This match is already settled."}), 400
        winner = match["result"]
        bets = db.execute(
            "SELECT b.*, s.name AS selection_name FROM bets b"
            " JOIN selections s ON s.id = b.selection_id"
            " WHERE b.user_id = ? AND b.match_id = ? AND b.status = 'unsettled'",
            (user["id"], match_id)).fetchall()
        total_profit = 0.0
        for b in bets:
            market = db.execute("SELECT * FROM markets WHERE id = ?", (b["market_id"],)).fetchone()
            if market["kind"] == "fancy":
                # Seeded demo rule: the "Yes" line covers. Back follows the
                # outcome, lay takes the opposite side of it.
                outcome_yes = (b["selection_name"] == "Yes")
                won = outcome_yes if b["side"] == "back" else (not outcome_yes)
            else:
                won = (b["selection_name"] == winner) if b["side"] == "back" else \
                      (b["selection_name"] != winner)
            if b["side"] == "back":
                profit = round(b["stake"] * (b["odds"] - 1), 2) if won else -b["stake"]
                # Stake was never deducted from balance at placement -- only
                # reserved as exposure -- so a win credits just the profit,
                # and a loss now materialises the stake.
                balance_delta = profit if won else -b["stake"]
                exposure_delta = -b["stake"]
            else:
                liability = round(b["stake"] * (b["odds"] - 1), 2)
                profit = b["stake"] if won else -liability
                balance_delta = b["stake"] if won else -liability
                exposure_delta = -liability
            db.execute("UPDATE bets SET status = 'settled', profit = ? WHERE id = ?",
                       (profit, b["id"]))
            db.execute("UPDATE users SET balance = balance + ?, exposure = exposure + ?"
                       " WHERE id = ?", (balance_delta, exposure_delta, user["id"]))
            kind = "BET_WON" if profit >= 0 else "BET_LOST"
            fresh = db.execute("SELECT balance FROM users WHERE id = ?", (user["id"],)).fetchone()
            add_transaction(db, user["id"], kind, round(balance_delta, 2),
                            fresh["balance"],
                            f"{match['title']} — {b['selection_name']} {b['side']} @ {b['odds']}")
            total_profit += profit
        remaining = db.execute(
            "SELECT COUNT(*) AS c FROM bets WHERE match_id = ? AND status = 'unsettled'",
            (match_id,)).fetchone()["c"]
        if remaining:
            # Other users still hold unsettled bets: reopen the match
            # so their bets can still settle and new bets stay possible.
            db.execute("UPDATE matches SET settled = 0 WHERE id = ?", (match_id,))
        db.execute(
            "INSERT INTO notifications (user_id, text, created_at) VALUES (?, ?, ?)",
            (user["id"], f"{match['title']} settled. Net result: {total_profit:+.2f} pts.",
             now_iso()))
        db.commit()
        fresh = db.execute("SELECT * FROM users WHERE id = ?", (user["id"],)).fetchone()
        return jsonify({"ok": True, "settled_bets": len(bets),
                        "net_profit": round(total_profit, 2), "user": user_view(fresh)})

    @app.get("/api/statement")
    def statement():
        user = current_user()
        if not user:
            return jsonify({"error": "Login required."}), 401
        kind = request.args.get("type", "ALL")
        date_from = request.args.get("from")
        date_to = request.args.get("to")
        db = get_db()
        q = "SELECT * FROM transactions WHERE user_id = ?"
        args = [user["id"]]
        if kind == "BALANCE":
            q += " AND kind IN ('BET_WON','BET_LOST')"
        elif kind == "GAME":
            q += " AND kind = 'CASINO'"
        elif kind == "SETTLEMENT":
            q += " AND kind = 'SETTLEMENT'"
        if date_from:
            q += " AND date(created_at) >= date(?)"
            args.append(date_from)
        if date_to:
            q += " AND date(created_at) <= date(?)"
            args.append(date_to)
        q += " ORDER BY id DESC LIMIT 200"
        rows = db.execute(q, args).fetchall()
        return jsonify([{
            "id": r["id"], "kind": r["kind"], "amount": r["amount"],
            "balance_after": r["balance_after"], "note": r["note"],
            "created_at": r["created_at"],
        } for r in rows])

    @app.get("/api/pnl")
    def pnl():
        user = current_user()
        if not user:
            return jsonify({"error": "Login required."}), 401
        db = get_db()
        rows = db.execute(
            "SELECT m.title AS match_title, COUNT(*) AS bets, COALESCE(SUM(b.profit),0) AS profit"
            " FROM bets b JOIN matches m ON m.id = b.match_id"
            " WHERE b.user_id = ? AND b.status = 'settled' GROUP BY m.id ORDER BY m.id",
            (user["id"],)).fetchall()
        total = sum(r["profit"] for r in rows)
        return jsonify({
            "per_match": [{"match_title": r["match_title"], "bets": r["bets"],
                           "profit": round(r["profit"], 2)} for r in rows],
            "total_profit": round(total, 2),
        })

    @app.get("/api/results")
    def results():
        db = get_db()
        rows = db.execute(
            "SELECT * FROM matches WHERE settled = 1 ORDER BY start_at").fetchall()
        return jsonify([{
            "id": r["id"], "sport": r["sport"], "title": r["title"],
            "team_a": r["team_a"], "team_b": r["team_b"], "result": r["result"],
        } for r in rows])

    @app.get("/api/notifications")
    def notifications():
        user = current_user()
        if not user:
            return jsonify({"error": "Login required."}), 401
        db = get_db()
        rows = db.execute(
            "SELECT * FROM notifications WHERE user_id = ? ORDER BY id DESC LIMIT 50",
            (user["id"],)).fetchall()
        return jsonify([{"id": r["id"], "text": r["text"], "is_read": bool(r["is_read"]),
                         "created_at": r["created_at"]} for r in rows])

    @app.post("/api/notifications/read")
    def notifications_read():
        user = current_user()
        if not user:
            return jsonify({"error": "Login required."}), 401
        db = get_db()
        db.execute("UPDATE notifications SET is_read = 1 WHERE user_id = ?", (user["id"],))
        db.commit()
        return jsonify({"ok": True})

    # ---------------- admin / agent panel ----------------
    # Agent-managed model (same as the original site: no cashier, the
    # admin assigns credit). All rules here are enforced server-side;
    # the frontend only hides links. Password values are never written
    # to the audit log or returned by any endpoint.
    def require_admin():
        user = current_user()
        if not user:
            return None, (jsonify({"error": "Login required."}), 401)
        if user["role"] != "admin":
            return None, (jsonify({"error": "Admin access only."}), 403)
        return user, None

    def require_manager():
        """Main admin or sub-admin. Players get 403; logged-out get 401."""
        user = current_user()
        if not user:
            return None, (jsonify({"error": "Login required."}), 401)
        if user["role"] not in ("admin", "subadmin"):
            return None, (jsonify({"error": "Admin access only."}), 403)
        return user, None

    def manager_target(db, actor, player_id):
        """Resolve a manageable player for a manager. Main admin may
        manage ANY player; a sub-admin only players they created
        (created_by == their id). For a sub-admin, EVERY non-manageable
        target -- missing, non-player, or foreign downline -- returns
        the same 404: returning 403 for existing-but-foreign ids and
        404 for missing ones let a sub-admin enumerate which numeric
        user ids exist. Main admin keeps the old 400 for non-players."""
        target = db.execute("SELECT * FROM users WHERE id = ?", (player_id,)).fetchone()
        if actor["role"] == "subadmin":
            if not target or target["role"] != "player" \
                    or target["created_by"] != actor["id"]:
                return None, (jsonify({"error": "Player not found."}), 404)
            return target, None
        if not target:
            return None, (jsonify({"error": "Player not found."}), 404)
        if target["role"] != "player":
            return None, (jsonify({"error": "Only player accounts can be managed here."}), 400)
        return target, None

    def _transfer_from_manager(db, manager, amount):
        """Atomically debit a sub-admin's spendable balance.

        The spendable check (balance minus own open exposure) and the
        debit are ONE conditional UPDATE, so concurrent allots
        serialize on the write lock: each sees the post-debit balance
        of the last committer, and the total debited can never exceed
        the balance. Returns True if debited, False if the sub-admin
        lacks available balance. Main admin never calls this: the
        main admin is the funding source at the top of the tree and
        mints (creation and add-credit are unchanged for that role).
        The sub-admin's credit_limit is untouched: it records what
        the main admin allotted them, not what they still hold."""
        cur = db.execute(
            "UPDATE users SET balance = balance - ?"
            " WHERE id = ? AND ROUND(balance - exposure, 2) >= ?",
            (amount, manager["id"], amount))
        return cur.rowcount == 1

    def _manager_available(db, manager_id):
        row = db.execute("SELECT balance, exposure FROM users WHERE id = ?",
                         (manager_id,)).fetchone()
        return round(row["balance"] - row["exposure"], 2)

    def admin_log(db, admin_id, action, target_user_id, detail, amount=None):
        db.execute(
            "INSERT INTO admin_log (admin_id, target_user_id, action, detail, amount, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (admin_id, target_user_id, action, detail, amount, now_iso()),
        )

    def _as_int_id(value):
        """Coerce a client-supplied id to int, or None if malformed.
        Lists/dicts/bools must not reach SQLite (binding error ->
        500); digit strings and integral floats keep working as
        before via the column-affinity behavior they already had."""
        if isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, float) and value.is_integer():
            return int(value)
        if isinstance(value, str):
            s = value.strip()
            if s.lstrip("-").isdigit():
                return int(s)
        return None

    def parse_positive_amount(data):
        raw = data.get("amount", data.get("credit", 0))
        if isinstance(raw, bool):
            return None
        try:
            amount = float(raw or 0)
        except (TypeError, ValueError, OverflowError):
            return None
        # Whole cents only: an admin amount must never silently round
        # into a different amount of someone else's money.
        if round(amount, 2) != amount:
            return None
        return amount if (math.isfinite(amount) and amount > 0) else None

    @app.get("/api/admin/overview")
    def admin_overview():
        manager, err = require_manager()
        if err:
            return err
        db = get_db()
        if manager["role"] == "subadmin":
            rows = db.execute(
                "SELECT * FROM users WHERE role = 'player' AND created_by = ? ORDER BY id",
                (manager["id"],)).fetchall()
        else:
            rows = db.execute(
                "SELECT * FROM users WHERE role = 'player' ORDER BY id").fetchall()
        players = []
        for r in rows:
            creator = None
            if r["created_by"]:
                c = db.execute("SELECT username FROM users WHERE id = ?",
                               (r["created_by"],)).fetchone()
                creator = c["username"] if c else None
            players.append(admin_player_view(r, creator))
        downline = [p for p in players if p["created_by"] == manager["username"]]
        totals = {
            "players": len(players),
            "active": sum(1 for p in players if p["status"] == "active"),
            "total_credit": round(sum(p["credit_limit"] for p in players), 2),
            "total_exposure": round(sum(p["exposure"] for p in players), 2),
        }
        out = {"totals": totals, "players": players, "downline": downline,
               "scope": "own" if manager["role"] == "subadmin" else "all"}
        if manager["role"] == "admin":
            subs = []
            for s in db.execute(
                    "SELECT * FROM users WHERE role = 'subadmin' ORDER BY id").fetchall():
                n = db.execute(
                    "SELECT COUNT(*) FROM users WHERE role = 'player' AND created_by = ?",
                    (s["id"],)).fetchone()[0]
                creator = None
                if s["created_by"]:
                    c = db.execute("SELECT username FROM users WHERE id = ?",
                                   (s["created_by"],)).fetchone()
                    creator = c["username"] if c else None
                subs.append({"id": s["id"], "username": s["username"],
                             "status": s["status"], "created_by": creator,
                             "created_at": s["created_at"], "downline_players": n,
                             "balance": round(s["balance"], 2),
                             "available": round(s["balance"] - s["exposure"], 2),
                             "credit_limit": round(s["credit_limit"], 2)})
            out["subadmins"] = subs
        return jsonify(out)

    @app.post("/api/admin/players")
    def admin_create_player():
        manager, err = require_manager()
        if err:
            return err
        data = request.get_json(force=True, silent=True) or {}
        username = (data.get("username") or "").strip()
        password = data.get("password") or ""
        if isinstance(data.get("credit"), bool):
            return jsonify({"error": "Invalid credit amount."}), 400
        try:
            credit = float(data.get("credit", 0) or 0)
        except (TypeError, ValueError, OverflowError):
            return jsonify({"error": "Invalid credit amount."}), 400
        if not USERNAME_RE.match(username) or len(password) < MIN_PASSWORD_LEN:
            return jsonify({"error": "Username must be 3-32 letters, digits,"
                            " _ . or -, and password 8+ chars."}), 400
        if not math.isfinite(credit) or credit < 0:
            return jsonify({"error": "Credit cannot be negative."}), 400
        # Whole cents only, like every other money path: a fractional
        # opening credit (e.g. 0.009) stored sub-cent dust that could
        # never be spent or deducted, and even landed a balance at
        # stored -0.001 after a loss.
        if round(credit, 2) != credit:
            return jsonify({"error": "Credit must be in whole cents."}), 400
        db = get_db()
        # Usernames are unique case-insensitively (the DB UNIQUE index
        # alone is case-sensitive, so check explicitly).
        clash = db.execute("SELECT id FROM users WHERE lower(username) = lower(?)",
                           (username,)).fetchone()
        if clash:
            return jsonify({"error": "Username already exists."}), 400
        # TRANSFER MODEL: a sub-admin funds the opening credit from
        # their own spendable balance. The debit is conditional-atomic
        # and commits in the same transaction as the player INSERT
        # below, so a failed creation never leaves a debit behind.
        # Zero-credit creation needs no funds and stays free. Main
        # admin mints: the main admin is the funding source at the
        # top of the tree, so no debit applies to that role.
        if manager["role"] == "subadmin" and credit > 0:
            if not _transfer_from_manager(db, manager, credit):
                return jsonify({"error": "Insufficient available balance to allot "
                                f"{credit:.2f} pts (available: "
                                f"{_manager_available(db, manager['id']):.2f} pts). "
                                "Ask the main admin for an allotment first."}), 400
        cur = db.execute(
            "INSERT INTO users (username, password_hash, balance, exposure, role, status,"
            " credit_limit, created_by, created_at) VALUES (?, ?, ?, 0, 'player', 'active', ?, ?, ?)",
            (username, generate_password_hash(password), credit, credit,
             manager["id"], now_iso()),
        )
        pid = cur.lastrowid
        db.execute(
            "INSERT INTO notifications (user_id, text, created_at) VALUES (?, ?, ?)",
            (pid, f"Welcome! Your account was created with {credit:.2f} pts credit.",
             now_iso()))
        admin_log(db, manager["id"], "CREATE_PLAYER", pid,
                  f"Created player '{username}' with opening credit {credit:.2f}.", credit)
        db.commit()
        row = db.execute("SELECT * FROM users WHERE id = ?", (pid,)).fetchone()
        return jsonify(admin_player_view(row, manager["username"]))

    @app.post("/api/admin/players/<int:player_id>/add-credit")
    def admin_add_credit(player_id):
        manager, err = require_manager()
        if err:
            return err
        data = request.get_json(force=True, silent=True) or {}
        amount = parse_positive_amount(data)
        if amount is None:
            return jsonify({"error": "Provide a positive credit amount."}), 400
        db = get_db()
        target, terr = manager_target(db, manager, player_id)
        if terr:
            return terr
        # TRANSFER MODEL: a sub-admin's add-credit debits their own
        # spendable balance atomically; the player credit below
        # commits in the same transaction, so the two legs never
        # split. Main admin mints, unchanged.
        if manager["role"] == "subadmin":
            if not _transfer_from_manager(db, manager, amount):
                return jsonify({"error": "Insufficient available balance to allot "
                                f"{amount:.2f} pts (available: "
                                f"{_manager_available(db, manager['id']):.2f} pts). "
                                "Ask the main admin for an allotment first."}), 400
        db.execute("UPDATE users SET balance = balance + ?, credit_limit = credit_limit + ?"
                   " WHERE id = ?", (amount, amount, player_id))
        admin_log(db, manager["id"], "ADD_CREDIT", player_id,
                  f"Added {amount:.2f} pts credit to '{target['username']}'.", amount)
        db.commit()
        row = db.execute("SELECT * FROM users WHERE id = ?", (player_id,)).fetchone()
        return jsonify(admin_player_view(row))

    @app.post("/api/admin/players/<int:player_id>/deduct-credit")
    def admin_deduct_credit(player_id):
        manager, err = require_manager()
        if err:
            return err
        data = request.get_json(force=True, silent=True) or {}
        amount = parse_positive_amount(data)
        if amount is None:
            return jsonify({"error": "Provide a positive deduction amount."}), 400
        db = get_db()
        target, terr = manager_target(db, manager, player_id)
        if terr:
            return terr
        # Atomic deduction: the floor checks (never below zero, never
        # below open exposure) and the debit are ONE statement, so a
        # concurrent bet cannot slip exposure underneath the deduction.
        cur = db.execute(
            "UPDATE users SET balance = balance - ?,"
            " credit_limit = MAX(0, credit_limit - ?)"
            " WHERE id = ? AND ROUND(balance - ?, 2) >= ROUND(exposure, 2)"
            " AND ROUND(balance - ?, 2) >= 0",
            (amount, amount, player_id, amount, amount))
        if cur.rowcount != 1:
            fresh = db.execute("SELECT * FROM users WHERE id = ?",
                               (player_id,)).fetchone()
            if round(fresh["balance"] - amount, 2) < 0:
                return jsonify({"error": "Deduction exceeds the player's balance."}), 400
            return jsonify({"error": "Deduction would leave balance below open exposure"
                            f" ({fresh['exposure']:.2f} pts). Settle or wait for bets first."}), 400
        # credit_limit tracks net assigned credit; floor it at zero --
        # a player may hold winnings above what was ever assigned.
        admin_log(db, manager["id"], "DEDUCT_CREDIT", player_id,
                  f"Deducted {amount:.2f} pts credit from '{target['username']}'.", -amount)
        db.commit()
        row = db.execute("SELECT * FROM users WHERE id = ?", (player_id,)).fetchone()
        return jsonify(admin_player_view(row))

    @app.post("/api/admin/players/<int:player_id>/suspend")
    def admin_suspend(player_id):
        manager, err = require_manager()
        if err:
            return err
        db = get_db()
        target, terr = manager_target(db, manager, player_id)
        if terr:
            return terr
        db.execute("UPDATE users SET status = 'suspended' WHERE id = ?", (player_id,))
        # Suspension kills live sessions immediately: the suspended
        # player's in-flight rounds can no longer act (the suspended
        # guard also 403s any request that slips through).
        _revoke_user_sessions(db, player_id)
        admin_log(db, manager["id"], "SUSPEND", player_id,
                  f"Suspended player '{target['username']}'.")
        db.commit()
        row = db.execute("SELECT * FROM users WHERE id = ?", (player_id,)).fetchone()
        return jsonify(admin_player_view(row))

    @app.post("/api/admin/players/<int:player_id>/activate")
    def admin_activate(player_id):
        manager, err = require_manager()
        if err:
            return err
        db = get_db()
        target, terr = manager_target(db, manager, player_id)
        if terr:
            return terr
        db.execute("UPDATE users SET status = 'active' WHERE id = ?", (player_id,))
        admin_log(db, manager["id"], "ACTIVATE", player_id,
                  f"Reactivated player '{target['username']}'.")
        db.commit()
        row = db.execute("SELECT * FROM users WHERE id = ?", (player_id,)).fetchone()
        return jsonify(admin_player_view(row))

    @app.post("/api/admin/players/<int:player_id>/reset-password")
    def admin_reset_password(player_id):
        manager, err = require_manager()
        if err:
            return err
        data = request.get_json(force=True, silent=True) or {}
        new_password = data.get("new_password") or ""
        if len(new_password) < MIN_PASSWORD_LEN:
            return jsonify({"error": "New password needs 8+ chars."}), 400
        db = get_db()
        target, terr = manager_target(db, manager, player_id)
        if terr:
            return terr
        db.execute("UPDATE users SET password_hash = ? WHERE id = ?",
                   (generate_password_hash(new_password), player_id))
        _revoke_user_sessions(db, player_id)
        # Deliberately no password value in the log detail.
        admin_log(db, manager["id"], "RESET_PASSWORD", player_id,
                  f"Reset password for player '{target['username']}'.")
        db.commit()
        return jsonify({"ok": True})

    @app.get("/api/admin/markets")
    def admin_markets():
        admin, err = require_admin()
        if err:
            return err
        db = get_db()
        out = []
        for m in db.execute(
                "SELECT mk.*, mt.title AS match_title, mt.sport AS sport"
                " FROM markets mk JOIN matches mt ON mt.id = mk.match_id"
                " ORDER BY mk.settled ASC, mk.id DESC"):
            sels = [r["name"] for r in db.execute(
                "SELECT name FROM selections WHERE market_id = ?", (m["id"],))]
            open_bets = db.execute(
                "SELECT COUNT(*) FROM bets WHERE market_id = ? AND status = 'unsettled'",
                (m["id"],)).fetchone()[0]
            out.append({
                "id": m["id"], "match_id": m["match_id"], "match_title": m["match_title"],
                "sport": m["sport"], "kind": m["kind"], "name": m["name"],
                "settled": bool(m["settled"]), "settled_result": m["settled_result"],
                "selections": sels, "open_bets": open_bets,
            })
        return jsonify(out)

    def settle_market(db, market, winner_name):
        """Settle EVERY unsettled bet on one market (all users). Winner
        is a selection name, or None for VOID. Uses the bet's stored
        odds as-is -- fancy live bets already carry the converted
        decimal (1 + rate/100) from the materialize step, so no second
        conversion happens here. Returns (settled_count, per-user net).
        Idempotency is enforced by the caller via markets.settled."""
        match = db.execute("SELECT * FROM matches WHERE id = ?",
                           (market["match_id"],)).fetchone()
        bets = db.execute(
            "SELECT b.*, s.name AS selection_name FROM bets b"
            " JOIN selections s ON s.id = b.selection_id"
            " WHERE b.market_id = ? AND b.status = 'unsettled'",
            (market["id"],)).fetchall()
        net_by_user = {}
        for b in bets:
            if winner_name is None:
                # VOID: stakes were never deducted at placement, only
                # reserved as exposure -- so refund = release exposure.
                profit = 0.0
                balance_delta = 0.0
                exposure_delta = -(b["stake"] if b["side"] == "back"
                                   else round(b["stake"] * (b["odds"] - 1), 2))
                kind, note = "SETTLEMENT", "void — stake refunded (exposure released)"
            else:
                won = (b["selection_name"] == winner_name) if b["side"] == "back" else \
                      (b["selection_name"] != winner_name)
                if b["side"] == "back":
                    profit = round(b["stake"] * (b["odds"] - 1), 2) if won else -b["stake"]
                    balance_delta = profit if won else -b["stake"]
                    exposure_delta = -b["stake"]
                else:
                    liability = round(b["stake"] * (b["odds"] - 1), 2)
                    profit = b["stake"] if won else -liability
                    balance_delta = b["stake"] if won else -liability
                    exposure_delta = -liability
                kind = "BET_WON" if profit >= 0 else "BET_LOST"
                note = f"Admin settlement — {market['name']} — {b['selection_name']} {b['side']} @ {b['odds']}"
            db.execute("UPDATE bets SET status = 'settled', profit = ? WHERE id = ?",
                       (profit, b["id"]))
            db.execute("UPDATE users SET balance = balance + ?, exposure = exposure + ?"
                       " WHERE id = ?", (balance_delta, exposure_delta, b["user_id"]))
            fresh = db.execute("SELECT balance FROM users WHERE id = ?",
                               (b["user_id"],)).fetchone()
            add_transaction(db, b["user_id"], kind, round(balance_delta, 2),
                            fresh["balance"], note)
            net_by_user[b["user_id"]] = round(net_by_user.get(b["user_id"], 0.0) + profit, 2)
        for uid, net in net_by_user.items():
            db.execute(
                "INSERT INTO notifications (user_id, text, created_at) VALUES (?, ?, ?)",
                (uid, f"Admin settled {market['name']} ({match['title']}): "
                        f"{winner_name or 'VOID'}. Your net: {net:+.2f} pts.", now_iso()))
        return len(bets), net_by_user

    @app.post("/api/admin/markets/<int:market_id>/settle")
    def admin_settle_market(market_id):
        admin, err = require_admin()
        if err:
            return err
        data = request.get_json(force=True, silent=True) or {}
        winner = data.get("winner")
        db = get_db()
        # Serialize against placement (see place_bet): the claim, the
        # settlement, and the commit must all see one consistent
        # state, or a bet landing mid-settle strands on a settled
        # market with no re-settle path.
        db.execute("BEGIN IMMEDIATE")
        market = db.execute("SELECT * FROM markets WHERE id = ?", (market_id,)).fetchone()
        if not market:
            return jsonify({"error": "Market not found."}), 404
        if winner == "VOID":
            winner_name = None
        else:
            names = [r["name"] for r in db.execute(
                "SELECT name FROM selections WHERE market_id = ?", (market_id,))]
            if winner not in names:
                return jsonify({"error": "Winner must be one of the market's selections, or VOID."}), 400
            winner_name = winner
        # Claim the market FIRST, conditionally: a second concurrent
        # settle sees settled=1 and stops instead of paying every bet
        # twice. The claim is uncommitted until the final commit, so a
        # mid-settle failure rolls it back with everything else.
        claim = db.execute(
            "UPDATE markets SET settled = 1, settled_result = ?, settled_at = ?"
            " WHERE id = ? AND settled = 0",
            (winner_name or "VOID", now_iso(), market_id))
        if claim.rowcount != 1:
            return jsonify({"error": "This market is already settled and cannot be re-settled."}), 400
        count, net_by_user = settle_market(db, market, winner_name)
        admin_log(db, admin["id"], "SETTLE_MARKET", None,
                  f"Settled market '{market['name']}' (match id {market['match_id']}): "
                  f"{winner_name or 'VOID'} — {count} bet(s).")
        db.commit()
        return jsonify({"ok": True, "market_id": market_id,
                        "result": winner_name or "VOID", "settled_bets": count,
                        "net_by_user": {str(k): v for k, v in net_by_user.items()}})

    @app.get("/api/admin/ledger")
    def admin_ledger():
        manager, err = require_manager()
        if err:
            return err
        db = get_db()
        if manager["role"] == "subadmin":
            rows = db.execute(
                "SELECT l.*, a.username AS admin_name, t.username AS target_name"
                " FROM admin_log l JOIN users a ON a.id = l.admin_id"
                " LEFT JOIN users t ON t.id = l.target_user_id"
                " WHERE l.admin_id = ? ORDER BY l.id DESC LIMIT 100",
                (manager["id"],)).fetchall()
        else:
            rows = db.execute(
                "SELECT l.*, a.username AS admin_name, t.username AS target_name"
                " FROM admin_log l JOIN users a ON a.id = l.admin_id"
                " LEFT JOIN users t ON t.id = l.target_user_id"
                " ORDER BY l.id DESC LIMIT 100").fetchall()
        return jsonify([{
            "id": r["id"], "admin": r["admin_name"], "target": r["target_name"],
            "action": r["action"], "detail": r["detail"], "amount": r["amount"],
            "created_at": r["created_at"],
        } for r in rows])

    @app.get("/api/notices")
    def public_notice():
        db = get_db()
        row = db.execute("SELECT * FROM notices WHERE active = 1 ORDER BY id DESC LIMIT 1").fetchone()
        if not row:
            return jsonify({"notice": None})
        return jsonify({"notice": {"text": row["text"], "updated_at": row["created_at"]}})

    @app.post("/api/admin/notices")
    def admin_notice():
        admin, err = require_admin()
        if err:
            return err
        data = request.get_json(force=True, silent=True) or {}
        text = (data.get("text") or "").strip()
        db = get_db()
        db.execute("UPDATE notices SET active = 0 WHERE active = 1")
        if not text:
            admin_log(db, admin["id"], "NOTICE", None, "Cleared the home-page notice.")
            db.commit()
            return jsonify({"notice": None})
        cur = db.execute(
            "INSERT INTO notices (text, created_by, created_at, active) VALUES (?, ?, ?, 1)",
            (text, admin["id"], now_iso()))
        admin_log(db, admin["id"], "NOTICE", None, f"Posted home-page notice: {text[:120]}")
        db.commit()
        return jsonify({"notice": {"id": cur.lastrowid, "text": text}})

    # ---------------- sub-admins (main admin only) ----------------
    # A sub-admin manages ONLY its own downline (players it created).
    # Main admin sees and manages everything; settlement and global
    # notices stay main-admin-only (they cannot be downline-scoped).
    def subadmin_target(db, subadmin_id):
        target = db.execute("SELECT * FROM users WHERE id = ?", (subadmin_id,)).fetchone()
        if not target:
            return None, (jsonify({"error": "Sub-admin not found."}), 404)
        if target["role"] != "subadmin":
            return None, (jsonify({"error": "Only sub-admin accounts can be managed here."}), 400)
        return target, None

    def subadmin_view(db, row):
        n = db.execute(
            "SELECT COUNT(*) FROM users WHERE role = 'player' AND created_by = ?",
            (row["id"],)).fetchone()[0]
        creator = None
        if row["created_by"]:
            c = db.execute("SELECT username FROM users WHERE id = ?",
                           (row["created_by"],)).fetchone()
            creator = c["username"] if c else None
        return {"id": row["id"], "username": row["username"], "status": row["status"],
                "created_by": creator, "created_at": row["created_at"],
                "downline_players": n,
                "balance": round(row["balance"], 2),
                "available": round(row["balance"] - row["exposure"], 2),
                "credit_limit": round(row["credit_limit"], 2)}

    @app.post("/api/admin/subadmins")
    def admin_create_subadmin():
        admin, err = require_admin()
        if err:
            return err
        data = request.get_json(force=True, silent=True) or {}
        username = (data.get("username") or "").strip()
        password = data.get("password") or ""
        if not USERNAME_RE.match(username) or len(password) < MIN_PASSWORD_LEN:
            return jsonify({"error": "Username must be 3-32 letters, digits,"
                            " _ . or -, and password 8+ chars."}), 400
        db = get_db()
        clash = db.execute("SELECT id FROM users WHERE lower(username) = lower(?)",
                           (username,)).fetchone()
        if clash:
            return jsonify({"error": "Username already exists."}), 400
        cur = db.execute(
            "INSERT INTO users (username, password_hash, balance, exposure, role, status,"
            " credit_limit, created_by, created_at) VALUES (?, ?, 0, 0, 'subadmin', 'active', 0, ?, ?)",
            (username, generate_password_hash(password), admin["id"], now_iso()))
        sid = cur.lastrowid
        admin_log(db, admin["id"], "CREATE_SUBADMIN", sid,
                  f"Created sub-admin '{username}'.")
        db.commit()
        row = db.execute("SELECT * FROM users WHERE id = ?", (sid,)).fetchone()
        return jsonify(subadmin_view(db, row))

    @app.post("/api/admin/subadmins/<int:subadmin_id>/add-credit")
    def admin_allot_subadmin_credit(subadmin_id):
        """Main-admin-only allotment: the funding source at the top
        of the tree. This MINTS: it credits the sub-admin's balance
        and credit_limit with no debit anywhere -- the main admin's
        balance is untouched (it sits at 0.00) because the main admin
        is the root, not a holder. Sub-admins then fund their players
        from this balance via the transfer in _transfer_from_manager
        (creation opening credit and add-credit both debit it)."""
        admin, err = require_admin()
        if err:
            return err
        data = request.get_json(force=True, silent=True) or {}
        amount = parse_positive_amount(data)
        if amount is None:
            return jsonify({"error": "Provide a positive allotment amount."}), 400
        db = get_db()
        target, terr = subadmin_target(db, subadmin_id)
        if terr:
            return terr
        db.execute("UPDATE users SET balance = balance + ?, credit_limit = credit_limit + ?"
                   " WHERE id = ?", (amount, amount, subadmin_id))
        admin_log(db, admin["id"], "ALLOT_CREDIT", subadmin_id,
                  f"Allotted {amount:.2f} pts credit to sub-admin '{target['username']}'.",
                  amount)
        db.commit()
        row = db.execute("SELECT * FROM users WHERE id = ?", (subadmin_id,)).fetchone()
        return jsonify(subadmin_view(db, row))

    @app.get("/api/admin/subadmins")
    def admin_list_subadmins():
        admin, err = require_admin()
        if err:
            return err
        db = get_db()
        rows = db.execute("SELECT * FROM users WHERE role = 'subadmin' ORDER BY id").fetchall()
        return jsonify([subadmin_view(db, r) for r in rows])

    @app.post("/api/admin/subadmins/<int:subadmin_id>/suspend")
    def admin_suspend_subadmin(subadmin_id):
        admin, err = require_admin()
        if err:
            return err
        db = get_db()
        target, terr = subadmin_target(db, subadmin_id)
        if terr:
            return terr
        db.execute("UPDATE users SET status = 'suspended' WHERE id = ?", (subadmin_id,))
        _revoke_user_sessions(db, subadmin_id)
        admin_log(db, admin["id"], "SUSPEND_SUBADMIN", subadmin_id,
                  f"Suspended sub-admin '{target['username']}'.")
        db.commit()
        return jsonify(subadmin_view(db, db.execute(
            "SELECT * FROM users WHERE id = ?", (subadmin_id,)).fetchone()))

    @app.post("/api/admin/subadmins/<int:subadmin_id>/activate")
    def admin_activate_subadmin(subadmin_id):
        admin, err = require_admin()
        if err:
            return err
        db = get_db()
        target, terr = subadmin_target(db, subadmin_id)
        if terr:
            return terr
        db.execute("UPDATE users SET status = 'active' WHERE id = ?", (subadmin_id,))
        admin_log(db, admin["id"], "ACTIVATE_SUBADMIN", subadmin_id,
                  f"Reactivated sub-admin '{target['username']}'.")
        db.commit()
        return jsonify(subadmin_view(db, db.execute(
            "SELECT * FROM users WHERE id = ?", (subadmin_id,)).fetchone()))

    @app.post("/api/admin/subadmins/<int:subadmin_id>/reset-password")
    def admin_reset_subadmin_password(subadmin_id):
        admin, err = require_admin()
        if err:
            return err
        data = request.get_json(force=True, silent=True) or {}
        new_password = data.get("new_password") or ""
        if len(new_password) < MIN_PASSWORD_LEN:
            return jsonify({"error": "New password needs 8+ chars."}), 400
        db = get_db()
        target, terr = subadmin_target(db, subadmin_id)
        if terr:
            return terr
        db.execute("UPDATE users SET password_hash = ? WHERE id = ?",
                   (generate_password_hash(new_password), subadmin_id))
        # Deliberately no password value in the log detail.
        admin_log(db, admin["id"], "RESET_SUBADMIN_PASSWORD", subadmin_id,
                  f"Reset password for sub-admin '{target['username']}'.")
        db.commit()
        return jsonify({"ok": True})

    # ---------------- player detail (manager-scoped) ----------------
    @app.get("/api/admin/players/<int:player_id>")
    def admin_player_detail(player_id):
        manager, err = require_manager()
        if err:
            return err
        db = get_db()
        target, terr = manager_target(db, manager, player_id)
        if terr:
            return terr
        creator = None
        if target["created_by"]:
            c = db.execute("SELECT username FROM users WHERE id = ?",
                           (target["created_by"],)).fetchone()
            creator = c["username"] if c else None
        bets = db.execute(
            "SELECT b.*, m.title AS match_title, m.live_event_id AS match_live_event_id,"
            " mk.name AS market_name, s.name AS selection_name FROM bets b"
            " JOIN matches m ON m.id = b.match_id"
            " JOIN markets mk ON mk.id = b.market_id"
            " JOIN selections s ON s.id = b.selection_id"
            " WHERE b.user_id = ? ORDER BY b.id DESC LIMIT 200",
            (player_id,)).fetchall()
        txns = db.execute(
            "SELECT * FROM transactions WHERE user_id = ? ORDER BY id DESC LIMIT 200",
            (player_id,)).fetchall()
        per_match = db.execute(
            "SELECT m.title AS match_title, COUNT(*) AS bets, COALESCE(SUM(b.profit),0) AS profit"
            " FROM bets b JOIN matches m ON m.id = b.match_id"
            " WHERE b.user_id = ? AND b.status = 'settled' GROUP BY m.id ORDER BY m.id",
            (player_id,)).fetchall()
        casino = db.execute(
            "SELECT * FROM game_history WHERE user_id = ? ORDER BY id DESC LIMIT 200",
            (player_id,)).fetchall()
        credit_rows = db.execute(
            "SELECT l.*, a.username AS admin_name FROM admin_log l"
            " JOIN users a ON a.id = l.admin_id"
            " WHERE l.target_user_id = ? ORDER BY l.id DESC LIMIT 200",
            (player_id,)).fetchall()
        settlements = db.execute(
            "SELECT mk.id AS market_id, mk.name AS market_name, mk.settled_result,"
            " mk.settled_at, m.title AS match_title, COUNT(*) AS bets,"
            " COALESCE(SUM(b.profit),0) AS net FROM bets b"
            " JOIN markets mk ON mk.id = b.market_id"
            " JOIN matches m ON m.id = b.match_id"
            " WHERE b.user_id = ? AND b.status = 'settled' AND mk.settled = 1"
            " GROUP BY mk.id ORDER BY mk.id",
            (player_id,)).fetchall()
        return jsonify({
            "player": admin_player_view(target, creator),
            "bets": [{"id": b["id"], "match_title": b["match_title"],
                      # Live bets sit on shadow matches (live_event_id set);
                      # seeded matches have it NULL -- that is the origin.
                      "origin": "live" if b["match_live_event_id"] else "simulated",
                      "market_name": b["market_name"], "selection": b["selection_name"],
                      "side": b["side"], "odds": b["odds"], "stake": b["stake"],
                      "status": b["status"], "profit": b["profit"],
                      "placed_at": b["placed_at"]} for b in bets],
            "statement": [{"id": t["id"], "kind": t["kind"], "amount": t["amount"],
                           "balance_after": t["balance_after"], "note": t["note"],
                           "created_at": t["created_at"]} for t in txns],
            "pnl": {"per_match": [{"match_title": r["match_title"], "bets": r["bets"],
                                   "profit": round(r["profit"], 2)} for r in per_match],
                    "total_profit": round(sum(r["profit"] for r in per_match), 2)},
            "casino": [{"id": g["id"], "game": g["game"], "stake": g["stake"],
                        "payout": g["payout"], "profit": g["profit"],
                        "outcome": g["outcome"], "created_at": g["created_at"]} for g in casino],
            "credit_activity": [{"id": l["id"], "admin": l["admin_name"],
                                 "action": l["action"], "detail": l["detail"],
                                 "amount": l["amount"],
                                 "created_at": l["created_at"]} for l in credit_rows],
            "settlements": [{"market_id": s["market_id"], "market_name": s["market_name"],
                             "match_title": s["match_title"],
                             "result": s["settled_result"], "settled_at": s["settled_at"],
                             "bets": s["bets"], "net": round(s["net"], 2)} for s in settlements],
        })

    # ---------------- casino ----------------
    def _casino_wallet(user_id, stake, payout, note, game=None, outcome=None, hist_stake=None):
        # Atomic deduction: the balance check and the debit are ONE
        # statement, so two concurrent rounds cannot both pass the
        # guard on the same funds (proven overdraw pre-fix: balance
        # -20 from two simultaneous stake-60 limbo rounds on 100 pts).
        # A failed deduction raises before ANY write, so call sites
        # that insert a round record first must NOT commit before this
        # call -- teardown then discards the uncommitted record.
        db = get_db()
        # Cent precision backstop: every wallet movement is exactly
        # 2dp, so balances always reconcile to the cent in the ledger.
        stake = round(stake, 2)
        payout = round(payout, 2)
        if stake:
            cur = db.execute(
                "UPDATE users SET balance = balance - ? WHERE id = ?"
                " AND ROUND(balance - exposure, 2) >= ?",
                (stake, user_id, stake))
            if cur.rowcount != 1:
                raise InsufficientFunds()
        if payout > 0:
            db.execute("UPDATE users SET balance = balance + ? WHERE id = ?",
                       (payout, user_id))
        bal = db.execute("SELECT balance FROM users WHERE id = ?", (user_id,)).fetchone()["balance"]
        add_transaction(db, user_id, "CASINO", round(payout - stake, 2), bal, note)
        if game:
            # Completed-round record (see game_history schema note: no
            # backfill for play before this table existed). Multi-step
            # games (Mines) deduct the stake at start and settle at the
            # end: hist_stake lets the history row show the original
            # stake while the ledger rows stay exactly -stake / +payout.
            hs = stake if hist_stake is None else hist_stake
            db.execute(
                "INSERT INTO game_history (user_id, game, stake, payout, profit, outcome, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (user_id, game, hs, payout, round(payout - hs, 2), outcome or "", now_iso()))
        db.commit()
        return bal

    # ---------------- casino games (batch 1) ----------------
    # Every outcome is drawn server-side with the secrets module; the
    # browser only renders what the server returns. Every round settles
    # through _casino_wallet so header, statement and admin activity
    # always agree.
    def _casino_guard(data):
        """Shared guards: login, playable account, positive stake within
        available balance (balance minus sportsbook exposure). Returns
        (user, stake) or (None, error_response)."""
        user = current_user()
        if not user:
            return None, (jsonify({"error": "Login required."}), 401)
        if user["role"] in ("admin", "subadmin"):
            return None, (jsonify({"error": "Admin accounts manage players; they cannot play casino."}), 403)
        if user["status"] == "suspended":
            return None, (jsonify({"error": "Suspended accounts cannot play casino."}), 403)
        if isinstance(data.get("stake"), bool):
            return None, (jsonify({"error": "Invalid stake."}), 400)
        try:
            stake = float(data.get("stake") or 0)
        except (TypeError, ValueError, OverflowError):
            return None, (jsonify({"error": "Invalid stake."}), 400)
        if not math.isfinite(stake) or stake <= 0:
            return None, (jsonify({"error": "Stake must be positive."}), 400)
        # Whole cents only: a sub-cent stake would either play a free
        # zero-stake round (after rounding down) or silently charge
        # more than typed (after rounding up) -- both are wrong.
        if round(stake, 2) != stake or stake < 0.01:
            return None, (jsonify({"error": "Stake must be 0.01 pts or more, in whole cents."}), 400)
        available = round(user["balance"] - user["exposure"], 2)
        if stake > available:
            return None, (jsonify({"error": f"Stake exceeds available balance ({available:.2f} pts)."}), 400)
        return user, stake

    @app.post("/api/casino/limbo")
    def casino_limbo():
        data = request.get_json(force=True, silent=True) or {}
        user, res = _casino_guard(data)
        if res is not None and not isinstance(res, float):
            return res
        stake = res
        try:
            target = float(data.get("target") or 0)
        except (TypeError, ValueError, OverflowError):
            return jsonify({"error": "Invalid target multiplier."}), 400
        if not math.isfinite(target) or target < 1.01 or target > 100:
            return jsonify({"error": "Target multiplier must be between 1.01 and 100."}), 400
        # Crash point with a 2% house edge: 0.98 / (1 - r), floored at 1.00.
        r = secrets.randbelow(1_000_000) / 1_000_000
        crash = round(max(1.0, 0.98 / (1 - r)), 2) if r < 1 else 1.0
        win = crash >= target
        payout = round(stake * target, 2) if win else 0.0
        bal = _casino_wallet(user["id"], stake, payout,
                             f"Limbo target {target}x, crash {crash}x",
                             game="Limbo",
                             outcome=f"{'Won' if win else 'Lost'} at {crash}x (target {target}x)")
        return jsonify({"ok": True, "crash_point": crash, "target": target,
                        "win": win, "payout": payout, "balance": round(bal, 2)})

    @app.post("/api/casino/plinko")
    def casino_plinko():
        data = request.get_json(force=True, silent=True) or {}
        user, res = _casino_guard(data)
        if res is not None and not isinstance(res, float):
            return res
        stake = res
        risk = data.get("risk")
        try:
            rows = int(data.get("rows"))
        except (TypeError, ValueError, OverflowError):
            rows = None
        if not isinstance(risk, str) or risk not in PLINKO_MULT or rows not in PLINKO_MULT[risk]:
            return jsonify({"error": "Risk must be low/medium/high and rows must be 8, 12 or 16."}), 400
        path = [secrets.randbelow(2) for _ in range(rows)]
        bin_idx = sum(path)
        mult = PLINKO_MULT[risk][rows][bin_idx]
        payout = round(stake * mult, 2)
        bal = _casino_wallet(user["id"], stake, payout,
                             f"Plinko {risk} {rows} rows, bin {bin_idx} x{mult}",
                             game="Plinko",
                             outcome=f"Bin {bin_idx} x{mult}")
        return jsonify({"ok": True, "path": path, "bin": bin_idx,
                        "multiplier": mult, "payout": payout,
                        "balance": round(bal, 2)})

    @app.post("/api/casino/keno")
    def casino_keno():
        data = request.get_json(force=True, silent=True) or {}
        user, res = _casino_guard(data)
        if res is not None and not isinstance(res, float):
            return res
        stake = res
        picks = data.get("picks")
        if (not isinstance(picks, list) or not 1 <= len(picks) <= 10
                or any(not isinstance(p, int) or isinstance(p, bool) for p in picks)
                or len(set(picks)) != len(picks)
                or any(p < 1 or p > 80 for p in picks)):
            return jsonify({"error": "Pick 1-10 distinct numbers from 1 to 80."}), 400
        draw = sorted(secrets.SystemRandom().sample(range(1, 81), 20))
        hits = len(set(picks) & set(draw))
        mult = KENO_PAYTABLE[len(picks)].get(hits, 0)
        payout = round(stake * mult, 2)
        bal = _casino_wallet(user["id"], stake, payout,
                             f"Keno {len(picks)} picks, {hits} hits",
                             game="Keno",
                             outcome=f"{hits} hits x{mult}")
        return jsonify({"ok": True, "picks": picks, "draw": draw, "hits": hits,
                        "multiplier": mult, "payout": payout,
                        "balance": round(bal, 2)})

    @app.post("/api/casino/dice")
    def casino_dice():
        data = request.get_json(force=True, silent=True) or {}
        user, res = _casino_guard(data)
        if res is not None and not isinstance(res, float):
            return res
        stake = res
        target = data.get("target")
        if isinstance(target, bool) or not isinstance(target, int):
            return jsonify({"error": "Target must be a whole number from 1 to 95."}), 400
        direction = data.get("direction")
        if target < 1 or target > 95 or direction not in ("over", "under"):
            return jsonify({"error": "Target must be 1-95 with direction over/under."}), 400
        # Roll in 0.00-99.99; over wins on roll > target, under on roll <
        # target. Multiplier = 0.98 / win chance (2% edge).
        roll = secrets.randbelow(10000) / 100
        if direction == "over":
            win = roll > target
            chance = (9999 - target * 100) / 10000
        else:
            win = roll < target
            chance = (target * 100) / 10000
        mult = round(0.98 / chance, 4)
        payout = round(stake * mult, 2) if win else 0.0
        bal = _casino_wallet(user["id"], stake, payout,
                             f"Dice {direction} {target}, rolled {roll:.2f}",
                             game="Dice",
                             outcome=f"{'Won' if win else 'Lost'}: rolled {roll:.2f} ({direction} {target})")
        return jsonify({"ok": True, "roll": roll, "target": target,
                        "direction": direction, "win": win,
                        "multiplier": mult, "payout": payout,
                        "balance": round(bal, 2)})

    def _mines_multiplier(mines_count, revealed_count):
        # Combinatorial odds with a 3% edge; 0 picks pays nothing.
        if revealed_count == 0:
            return 0.0
        return round(math.comb(25, revealed_count) / math.comb(25 - mines_count, revealed_count) * 0.97, 4)

    @app.post("/api/casino/mines/start")
    def casino_mines_start():
        data = request.get_json(force=True, silent=True) or {}
        user, res = _casino_guard(data)
        if res is not None and not isinstance(res, float):
            return res
        stake = res
        mines_count = data.get("mines")
        if isinstance(mines_count, bool) or not isinstance(mines_count, int):
            return jsonify({"error": "Mines must be a whole number from 1 to 10."}), 400
        if mines_count < 1 or mines_count > 10:
            return jsonify({"error": "Mines must be between 1 and 10."}), 400
        mines = sorted(secrets.SystemRandom().sample(range(25), mines_count))
        db = get_db()
        cur = db.execute(
            "INSERT INTO casino_games (user_id, game, state, stake, status, created_at)"
            " VALUES (?, 'Mines', ?, ?, 'open', ?)",
            (user["id"], json.dumps({"mines": mines, "revealed": [], "mines_count": mines_count}),
             stake, now_iso()))
        game_id = cur.lastrowid
        # No commit here on purpose: _casino_wallet below commits
        # the record AND the deduction together. If the deduction
        # raises (funds drained concurrently), teardown discards
        # this record instead of leaving a free round.
        # Stake leaves the wallet now (ledger row, no history row yet --
        # the round completes on cashout or bust).
        _casino_wallet(user["id"], stake, 0, f"Mines stake ({mines_count} mines)")
        return jsonify({"ok": True, "game_id": game_id, "mines_count": mines_count,
                        "stake": stake})

    def _mines_game_or_error(user, game_id):
        db = get_db()
        row = db.execute("SELECT * FROM casino_games WHERE id = ?", (game_id,)).fetchone()
        if not row or row["game"] != "Mines":
            return None, (jsonify({"error": "Unknown Mines game."}), 404)
        if row["user_id"] != user["id"]:
            return None, (jsonify({"error": "This game belongs to another player."}), 403)
        if row["status"] != "open":
            return None, (jsonify({"error": "This game is already closed."}), 400)
        return row, None

    @app.post("/api/casino/mines/reveal")
    def casino_mines_reveal():
        user = current_user()
        if not user:
            return jsonify({"error": "Login required."}), 401
        data = request.get_json(force=True, silent=True) or {}
        try:
            game_id = int(data.get("game_id"))
            tile = int(data.get("tile"))
        except (TypeError, ValueError, OverflowError):
            return jsonify({"error": "game_id and tile are required."}), 400
        if tile < 0 or tile > 24:
            return jsonify({"error": "Tile must be 0-24."}), 400
        row, err = _mines_game_or_error(user, game_id)
        if err:
            return err
        state = json.loads(row["state"])
        if tile in state["revealed"]:
            return jsonify({"error": "Tile already revealed."}), 400
        db = get_db()
        stake = row["stake"]
        if tile in state["mines"]:
            # Bust: stake already left at start; history row closes the round.
            # Conditional close: a concurrent twin bust/cashout cannot
            # settle the same round twice.
            cur = db.execute("UPDATE casino_games SET status = 'closed' WHERE id = ? AND status = 'open'",
                             (game_id,))
            if cur.rowcount != 1:
                return jsonify({"error": "This game is already closed."}), 400
            db.commit()
            _casino_wallet(user["id"], 0, 0, "Mines bust", game="Mines",
                           outcome=f"Bust on tile {tile}", hist_stake=stake)
            return jsonify({"ok": True, "safe": False, "bust": True,
                            "mines": state["mines"], "revealed": state["revealed"],
                            "payout": 0.0})
        state["revealed"].append(tile)
        # Compare-and-swap on the exact prior state: a concurrent twin
        # reveal cannot silently overwrite (and double-count) tiles.
        cur = db.execute("UPDATE casino_games SET state = ? WHERE id = ? AND state = ?",
                         (json.dumps(state), game_id, row["state"]))
        if cur.rowcount != 1:
            return jsonify({"error": "Round changed — reveal again."}), 400
        db.commit()
        mult = _mines_multiplier(state["mines_count"], len(state["revealed"]))
        return jsonify({"ok": True, "safe": True, "bust": False,
                        "revealed": state["revealed"], "multiplier": mult,
                        "potential_payout": round(stake * mult, 2)})

    @app.post("/api/casino/mines/cashout")
    def casino_mines_cashout():
        user = current_user()
        if not user:
            return jsonify({"error": "Login required."}), 401
        data = request.get_json(force=True, silent=True) or {}
        try:
            game_id = int(data.get("game_id"))
        except (TypeError, ValueError, OverflowError):
            return jsonify({"error": "game_id is required."}), 400
        row, err = _mines_game_or_error(user, game_id)
        if err:
            return err
        state = json.loads(row["state"])
        if not state["revealed"]:
            return jsonify({"error": "Reveal at least one safe tile before cashing out."}), 400
        mult = _mines_multiplier(state["mines_count"], len(state["revealed"]))
        payout = round(row["stake"] * mult, 2)
        db = get_db()
        cur = db.execute("UPDATE casino_games SET status = 'closed' WHERE id = ? AND status = 'open'",
                         (game_id,))
        if cur.rowcount != 1:
            return jsonify({"error": "This game is already closed."}), 400
        db.commit()
        bal = _casino_wallet(user["id"], 0, payout,
                             f"Mines cashout x{mult} ({len(state['revealed'])} safe)",
                             game="Mines",
                             outcome=f"Cashed out x{mult} ({len(state['revealed'])} safe)",
                             hist_stake=row["stake"])
        return jsonify({"ok": True, "multiplier": mult, "payout": payout,
                        "mines": state["mines"], "revealed": state["revealed"],
                        "balance": round(bal, 2)})

    # ---------------- casino games (batch 2) ----------------
    # nekzabirov rules reimplemented in Flask (no Kotlin side-service:
    # a second service cannot run cleanly on the single Render free web
    # service). Shared rounds (TeleFly / PvP / Lottery) have no
    # background thread: phase is derived from wall-clock timestamps
    # and settlement runs lazily, idempotently, on the next state
    # request. Crash points and wheel winners are drawn server-side
    # and are NEVER sent to clients before they are public.
    def _ms_now():
        return int(time.time() * 1000)

    def _casino_player(user):
        """Role/suspension check for endpoints that do not take a stake
        (cashout, cancel): admins never hold a bet, so ownership alone
        would not block them."""
        if not user:
            return jsonify({"error": "Login required."}), 401
        if user["role"] in ("admin", "subadmin"):
            return jsonify({"error": "Admin accounts manage players; they cannot play casino."}), 403
        if user["status"] == "suspended":
            return jsonify({"error": "Suspended accounts cannot play casino."}), 403
        return None

    # ----- TeleFly (shared-round live crash) -----
    def _telefly_draw_crash():
        x = secrets.randbelow(2 ** 32) / float(2 ** 32)
        return max(1.0, TELEFLY_RTP / (1.0 - x))

    def _telefly_current(db, now):
        row = db.execute("SELECT * FROM telefly_rounds ORDER BY id DESC LIMIT 1").fetchone()
        if row and not (row["settled"] and now > row["crash_time"] + TELEFLY_CRASH_PAUSE_MS):
            return row
        crash = _telefly_draw_crash()
        betting_end = now + TELEFLY_BETTING_MS
        fly_start = betting_end
        crash_time = fly_start + int(math.log(crash) / TELEFLY_GROWTH * 1000)
        cur = db.execute(
            "INSERT INTO telefly_rounds (crash_point, betting_end, fly_start, crash_time, settled, created_at)"
            " VALUES (?, ?, ?, ?, 0, ?)",
            (crash, betting_end, fly_start, crash_time, now_iso()))
        db.commit()
        return db.execute("SELECT * FROM telefly_rounds WHERE id = ?", (cur.lastrowid,)).fetchone()

    def _telefly_phase(row, now):
        if now < row["betting_end"]:
            return "betting", 1.0
        if now < row["crash_time"]:
            return "flying", round(math.exp(TELEFLY_GROWTH * (now - row["fly_start"]) / 1000.0), 2)
        return "crashed", round(row["crash_point"], 2)

    def _telefly_settle(db, row):
        cur = db.execute("UPDATE telefly_rounds SET settled = 1 WHERE id = ? AND settled = 0",
                         (row["id"],))
        if cur.rowcount != 1:
            return
        db.commit()
        for bet in db.execute("SELECT * FROM telefly_bets WHERE round_id = ? AND cashed = 0",
                              (row["id"],)):
            _casino_wallet(bet["user_id"], 0, 0,
                           f"TeleFly crashed at {round(row['crash_point'], 2)}x",
                           game="TeleFly", hist_stake=bet["stake"])

    @app.get("/api/casino/telefly/state")
    def telefly_state():
        db = get_db()
        now = _ms_now()
        row = _telefly_current(db, now)
        phase, mult = _telefly_phase(row, now)
        if phase == "crashed":
            _telefly_settle(db, row)
        user = current_user()
        my_bet = None
        if user:
            b = db.execute("SELECT * FROM telefly_bets WHERE round_id = ? AND user_id = ?",
                           (row["id"], user["id"])).fetchone()
            if b:
                my_bet = {"stake": b["stake"], "cashed": bool(b["cashed"]),
                          "cashout_mult": b["cashout_mult"], "payout": b["payout"]}
        hist = db.execute("SELECT crash_point FROM telefly_rounds WHERE settled = 1"
                          " ORDER BY id DESC LIMIT 10").fetchall()
        return jsonify({"ok": True, "round_id": row["id"], "phase": phase,
                        "multiplier": mult,
                        "betting_ends_in_ms": max(0, row["betting_end"] - now),
                        "crash_point": round(row["crash_point"], 2) if phase == "crashed" else None,
                        "history": [round(r["crash_point"], 2) for r in hist],
                        "my_bet": my_bet})

    @app.post("/api/casino/telefly/bet")
    def telefly_bet():
        data = request.get_json(force=True, silent=True) or {}
        user, res = _casino_guard(data)
        if res is not None and not isinstance(res, float):
            return res
        stake = res
        db = get_db()
        now = _ms_now()
        row = _telefly_current(db, now)
        phase, _ = _telefly_phase(row, now)
        if phase != "betting":
            return jsonify({"error": "Betting is closed for this round."}), 400
        if db.execute("SELECT id FROM telefly_bets WHERE round_id = ? AND user_id = ?",
                      (row["id"], user["id"])).fetchone():
            return jsonify({"error": "You already have a bet in this round."}), 400
        try:
            db.execute("INSERT INTO telefly_bets (round_id, user_id, stake) VALUES (?, ?, ?)",
                       (row["id"], user["id"], stake))
        except sqlite3.IntegrityError:
            # The UNIQUE(round_id, user_id) backstop: a concurrent twin
            # bet lost the race. No wallet call has run, so no charge.
            return jsonify({"error": "You already have a bet in this round."}), 400
        # No commit before the wallet call: _casino_wallet commits the
        # bet row AND the deduction together. If the deduction raises,
        # teardown discards the bet row instead of leaving a free bet.
        _casino_wallet(user["id"], stake, 0, f"TeleFly bet (round {row['id']})")
        return jsonify({"ok": True, "round_id": row["id"], "stake": stake})

    @app.post("/api/casino/telefly/cashout")
    def telefly_cashout():
        err = _casino_player(current_user())
        if err:
            return err
        user = current_user()
        db = get_db()
        now = _ms_now()
        row = _telefly_current(db, now)
        phase, mult = _telefly_phase(row, now)
        if phase != "flying":
            return jsonify({"error": "Round is not flying — too early or already crashed."}), 400
        bet = db.execute("SELECT * FROM telefly_bets WHERE round_id = ? AND user_id = ?",
                         (row["id"], user["id"])).fetchone()
        if not bet:
            return jsonify({"error": "No bet in this round."}), 400
        if bet["cashed"]:
            return jsonify({"error": "Already cashed out."}), 400
        payout = round(bet["stake"] * mult, 2)
        cur = db.execute("UPDATE telefly_bets SET cashed = 1, cashout_mult = ?, payout = ?"
                         " WHERE id = ? AND cashed = 0",
                         (mult, payout, bet["id"]))
        if cur.rowcount != 1:
            return jsonify({"error": "Already cashed out."}), 400
        db.commit()
        bal = _casino_wallet(user["id"], 0, payout, f"TeleFly cashout x{mult}",
                             game="TeleFly", hist_stake=bet["stake"])
        return jsonify({"ok": True, "multiplier": mult, "payout": payout,
                        "balance": round(bal, 2)})

    # ----- Lucky Cups (shell game) -----
    @app.post("/api/casino/cups")
    def casino_cups():
        data = request.get_json(force=True, silent=True) or {}
        user, res = _casino_guard(data)
        if res is not None and not isinstance(res, float):
            return res
        stake = res
        cup = data.get("cup")
        if isinstance(cup, bool) or not isinstance(cup, int) or cup not in (0, 1, 2):
            return jsonify({"error": "Pick cup 0, 1 or 2."}), 400
        winning = secrets.randbelow(3)
        win = cup == winning
        payout = round(stake * CUPS_PAYOUT, 2) if win else 0.0
        bal = _casino_wallet(user["id"], stake, payout,
                             f"Lucky Cups picked {cup}, ball under {winning}",
                             game="Lucky Cups",
                             outcome=f"{'Won' if win else 'Lost'}: ball under cup {winning} (x{CUPS_PAYOUT})")
        return jsonify({"ok": True, "cup": cup, "winning_cup": winning, "win": win,
                        "multiplier": CUPS_PAYOUT, "payout": payout,
                        "balance": round(bal, 2)})

    # ----- PvP Wheel (jackpot wheel) -----
    def _pvp_current(db):
        row = db.execute("SELECT * FROM pvp_rounds WHERE status != 'done'"
                         " ORDER BY id DESC LIMIT 1").fetchone()
        if row:
            return row
        cur = db.execute("INSERT INTO pvp_rounds (status, created_at) VALUES ('waiting', ?)",
                         (now_iso(),))
        db.commit()
        return db.execute("SELECT * FROM pvp_rounds WHERE id = ?", (cur.lastrowid,)).fetchone()

    def _pvp_roster(db, round_id):
        rows = db.execute(
            "SELECT e.user_id, u.username, SUM(e.stake) AS stake, MIN(e.id) AS first_entry"
            " FROM pvp_entries e JOIN users u ON u.id = e.user_id"
            " WHERE e.round_id = ? GROUP BY e.user_id ORDER BY first_entry",
            (round_id,)).fetchall()
        return [{"user_id": r["user_id"], "username": r["username"],
                 "stake": round(r["stake"], 2)} for r in rows]

    def _pvp_advance(db, row, now):
        if row["status"] == "waiting":
            n = db.execute("SELECT COUNT(DISTINCT user_id) AS n FROM pvp_entries"
                           " WHERE round_id = ?", (row["id"],)).fetchone()["n"]
            if n >= 2:
                db.execute("UPDATE pvp_rounds SET status = 'countdown', countdown_end = ?"
                           " WHERE id = ?", (now + PVP_COUNTDOWN_MS, row["id"]))
                db.commit()
                row = db.execute("SELECT * FROM pvp_rounds WHERE id = ?", (row["id"],)).fetchone()
        if row["status"] == "countdown" and row["countdown_end"] and now >= row["countdown_end"]:
            roster = _pvp_roster(db, row["id"])
            pot_cents = sum(round(p["stake"] * 100) for p in roster)
            frac = secrets.randbelow(2 ** 32) / float(2 ** 32)
            ticket = min(int(frac * pot_cents), pot_cents - 1)
            cum = 0
            winner = roster[-1]
            for p in roster:
                cum += round(p["stake"] * 100)
                if ticket < cum:
                    winner = p
                    break
            db.execute("UPDATE pvp_rounds SET status = 'spinning', spin_end = ?,"
                       " winner_id = ?, winning_number = ?, pot = ? WHERE id = ?",
                       (now + PVP_SPIN_MS, winner["user_id"], round(frac * 100, 2),
                        round(pot_cents / 100, 2), row["id"]))
            db.commit()
            row = db.execute("SELECT * FROM pvp_rounds WHERE id = ?", (row["id"],)).fetchone()
        if row["status"] == "spinning" and row["spin_end"] and now >= row["spin_end"]:
            cur = db.execute("UPDATE pvp_rounds SET settled = 1 WHERE id = ? AND settled = 0",
                             (row["id"],))
            if cur.rowcount == 1:
                db.commit()
                roster = _pvp_roster(db, row["id"])
                payout = round(row["pot"] * (1 - PVP_EDGE), 2)
                for p in roster:
                    if p["user_id"] == row["winner_id"]:
                        _casino_wallet(p["user_id"], 0, payout,
                                       f"PvP Wheel win (round {row['id']})",
                                       game="PvP Wheel", hist_stake=p["stake"])
                    else:
                        _casino_wallet(p["user_id"], 0, 0,
                                       f"PvP Wheel round {row['id']}",
                                       game="PvP Wheel", hist_stake=p["stake"])
            db.execute("UPDATE pvp_rounds SET status = 'done' WHERE id = ?", (row["id"],))
            db.commit()
            row = db.execute("SELECT * FROM pvp_rounds WHERE id = ?", (row["id"],)).fetchone()
        return row

    def _pvp_state_payload(db, row, now):
        roster = _pvp_roster(db, row["id"])
        pot = round(sum(p["stake"] for p in roster), 2)
        winner_name = None
        if row["winner_id"]:
            w = db.execute("SELECT username FROM users WHERE id = ?", (row["winner_id"],)).fetchone()
            winner_name = w["username"] if w else None
        hist = db.execute("SELECT winning_number, pot FROM pvp_rounds WHERE status = 'done'"
                          " ORDER BY id DESC LIMIT 10").fetchall()
        user = current_user()
        my_stake = None
        if user:
            mine = db.execute("SELECT SUM(stake) AS s FROM pvp_entries WHERE round_id = ?"
                              " AND user_id = ?", (row["id"], user["id"])).fetchone()["s"]
            my_stake = round(mine, 2) if mine else None
        return {"ok": True, "round_id": row["id"], "status": row["status"],
                "pot": pot, "players": len(roster), "roster": roster,
                "countdown_ends_in_ms": max(0, (row["countdown_end"] or 0) - now)
                if row["status"] == "countdown" else None,
                "spin_ends_in_ms": max(0, (row["spin_end"] or 0) - now)
                if row["status"] == "spinning" else None,
                "winner": winner_name, "winning_number": row["winning_number"],
                "payout": round(row["pot"] * (1 - PVP_EDGE), 2)
                if row["status"] in ("spinning", "done") else None,
                "history": [{"number": r["winning_number"], "pot": r["pot"]} for r in hist],
                "my_stake": my_stake}

    @app.get("/api/casino/pvp/state")
    def pvp_state():
        db = get_db()
        now = _ms_now()
        row = _pvp_advance(db, _pvp_current(db), now)
        return jsonify(_pvp_state_payload(db, row, now))

    @app.post("/api/casino/pvp/bet")
    def pvp_bet():
        data = request.get_json(force=True, silent=True) or {}
        user, res = _casino_guard(data)
        if res is not None and not isinstance(res, float):
            return res
        stake = res
        db = get_db()
        now = _ms_now()
        row = _pvp_advance(db, _pvp_current(db), now)
        if row["status"] not in ("waiting", "countdown"):
            return jsonify({"error": "Round is spinning — wait for the next round."}), 400
        # Wallet first: the old order (insert + commit, then deduct)
        # left a free pot entry when the deduction failed. A failed
        # deduction now raises before anything is recorded.
        _casino_wallet(user["id"], stake, 0, f"PvP Wheel entry (round {row['id']})")
        db.execute("INSERT INTO pvp_entries (round_id, user_id, stake, created_at)"
                   " VALUES (?, ?, ?, ?)", (row["id"], user["id"], stake, now_iso()))
        pot = db.execute("SELECT SUM(stake) AS s FROM pvp_entries WHERE round_id = ?",
                         (row["id"],)).fetchone()["s"]
        db.execute("UPDATE pvp_rounds SET pot = ? WHERE id = ?", (round(pot, 2), row["id"]))
        db.commit()
        row = _pvp_advance(db, _pvp_current(db), _ms_now())
        return jsonify(_pvp_state_payload(db, row, _ms_now()))

    @app.post("/api/casino/pvp/cancel")
    def pvp_cancel():
        err = _casino_player(current_user())
        if err:
            return err
        user = current_user()
        db = get_db()
        now = _ms_now()
        row = _pvp_advance(db, _pvp_current(db), now)
        if row["status"] != "waiting":
            return jsonify({"error": "Round is counting down — entries are locked."}), 400
        total = db.execute("SELECT SUM(stake) AS s FROM pvp_entries WHERE round_id = ?"
                           " AND user_id = ?", (row["id"], user["id"])).fetchone()["s"]
        if not total:
            return jsonify({"error": "No entry in this round."}), 400
        db.execute("DELETE FROM pvp_entries WHERE round_id = ? AND user_id = ?",
                   (row["id"], user["id"]))
        pot = db.execute("SELECT SUM(stake) AS s FROM pvp_entries WHERE round_id = ?",
                         (row["id"],)).fetchone()["s"]
        db.execute("UPDATE pvp_rounds SET pot = ? WHERE id = ?",
                   (round(pot or 0, 2), row["id"]))
        db.commit()
        bal = _casino_wallet(user["id"], 0, round(total, 2), "PvP Wheel entry cancelled")
        return jsonify({"ok": True, "refunded": round(total, 2), "balance": round(bal, 2)})

    # ----- Lottery 6/49 -----
    def _lottery_settle(db, row):
        cur = db.execute("UPDATE lottery_rounds SET settled = 1 WHERE id = ? AND settled = 0",
                         (row["id"],))
        if cur.rowcount != 1:
            return
        numbers = sorted(secrets.SystemRandom().sample(range(1, 50), 6))
        tickets = db.execute("SELECT * FROM lottery_tickets WHERE round_id = ?",
                             (row["id"],)).fetchall()
        stakes = round(sum(t["stake"] for t in tickets), 2)
        pot_total = round(stakes + row["rollover_in"], 2)
        groups = {6: [], 5: [], 4: [], 3: []}
        for t in tickets:
            m = len(set(json.loads(t["numbers"])) & set(numbers))
            if m >= 3:
                groups[m].append(t)
        paid = 0.0
        for tier, pct in LOTTERY_TIERS.items():
            winners = groups[tier]
            if not winners:
                continue
            each = round(pot_total * pct / len(winners), 2)
            for t in winners:
                db.execute("UPDATE lottery_tickets SET payout = ? WHERE id = ?",
                           (each, t["id"]))
                paid += each
        db.execute("UPDATE lottery_rounds SET numbers = ?, pot = ?, rollover_out = ?"
                   " WHERE id = ?", (json.dumps(numbers), pot_total,
                                     round(pot_total - paid, 2), row["id"]))
        db.commit()
        for t in tickets:
            m = len(set(json.loads(t["numbers"])) & set(numbers))
            if m >= 3:
                payout = db.execute("SELECT payout FROM lottery_tickets WHERE id = ?",
                                    (t["id"],)).fetchone()["payout"]
                _casino_wallet(t["user_id"], 0, payout,
                               f"Lottery {m}/6 win (round {row['id']})",
                               game="Lottery", hist_stake=t["stake"])
            else:
                _casino_wallet(t["user_id"], 0, 0,
                               f"Lottery draw (round {row['id']}): {m}/6",
                               game="Lottery", hist_stake=t["stake"])

    def _lottery_current(db, now):
        row = db.execute("SELECT * FROM lottery_rounds ORDER BY id DESC LIMIT 1").fetchone()
        if row and not row["settled"]:
            if now < row["draw_at"]:
                return row
            _lottery_settle(db, row)
            row = db.execute("SELECT * FROM lottery_rounds WHERE id = ?", (row["id"],)).fetchone()
        rollover = row["rollover_out"] if row else 0.0
        cur = db.execute("INSERT INTO lottery_rounds (draw_at, rollover_in, created_at)"
                         " VALUES (?, ?, ?)", (now + LOTTERY_ROUND_MS, rollover, now_iso()))
        db.commit()
        return db.execute("SELECT * FROM lottery_rounds WHERE id = ?", (cur.lastrowid,)).fetchone()

    @app.get("/api/casino/lottery/state")
    def lottery_state():
        db = get_db()
        now = _ms_now()
        row = _lottery_current(db, now)
        pot = db.execute("SELECT SUM(stake) AS s FROM lottery_tickets WHERE round_id = ?",
                         (row["id"],)).fetchone()["s"]
        pot = round((pot or 0) + row["rollover_in"], 2)
        user = current_user()
        my_ticket = None
        if user:
            t = db.execute("SELECT * FROM lottery_tickets WHERE round_id = ? AND user_id = ?",
                           (row["id"], user["id"])).fetchone()
            if t:
                my_ticket = {"numbers": json.loads(t["numbers"]), "stake": t["stake"]}
        draws = db.execute("SELECT numbers, pot FROM lottery_rounds WHERE settled = 1"
                           " ORDER BY id DESC LIMIT 5").fetchall()
        return jsonify({"ok": True, "round_id": row["id"],
                        "draw_in_ms": max(0, row["draw_at"] - now),
                        "pot": pot, "rollover_in": row["rollover_in"],
                        "my_ticket": my_ticket,
                        "last_draws": [{"numbers": json.loads(d["numbers"]), "pot": d["pot"]}
                                       for d in draws if d["numbers"]]})

    @app.post("/api/casino/lottery/buy")
    def lottery_buy():
        data = request.get_json(force=True, silent=True) or {}
        user, res = _casino_guard(data)
        if res is not None and not isinstance(res, float):
            return res
        stake = res
        if data.get("quickpick"):
            numbers = sorted(secrets.SystemRandom().sample(range(1, 50), 6))
        else:
            numbers = data.get("numbers")
            if (not isinstance(numbers, list) or len(numbers) != 6
                    or any(not isinstance(n, int) or isinstance(n, bool) for n in numbers)
                    or len(set(numbers)) != 6
                    or any(n < 1 or n > 49 for n in numbers)):
                return jsonify({"error": "Pick 6 distinct numbers from 1 to 49, or use quick-pick."}), 400
            numbers = sorted(numbers)
        db = get_db()
        row = _lottery_current(db, _ms_now())
        if db.execute("SELECT id FROM lottery_tickets WHERE round_id = ? AND user_id = ?",
                      (row["id"], user["id"])).fetchone():
            return jsonify({"error": "One ticket per player per round."}), 400
        try:
            db.execute("INSERT INTO lottery_tickets (round_id, user_id, numbers, stake)"
                       " VALUES (?, ?, ?, ?)",
                       (row["id"], user["id"], json.dumps(numbers), stake))
        except sqlite3.IntegrityError:
            return jsonify({"error": "One ticket per player per round."}), 400
        # No commit before the wallet call (same free-ticket hazard as
        # TeleFly): the wallet commits ticket + deduction together.
        _casino_wallet(user["id"], stake, 0, f"Lottery ticket (round {row['id']})")
        return jsonify({"ok": True, "round_id": row["id"], "numbers": numbers,
                        "stake": stake})

    # ---------------- casino games (batch 3) ----------------
    # Roulette, Blackjack, Slots — originals in the batch-1/2 style:
    # server-side secrets draws, _casino_wallet settlement, no browser
    # input ever decides an outcome. Dealer hole cards and shoe contents
    # are never sent to the client before settlement.

    # ----- Roulette (European single-zero) -----
    @app.post("/api/casino/roulette")
    def casino_roulette():
        data = request.get_json(force=True, silent=True) or {}
        raw_bets = data.get("bets")
        if not isinstance(raw_bets, list) or not raw_bets or len(raw_bets) > 40:
            return jsonify({"error": "Place 1-40 bets."}), 400
        bets = []
        total = 0.0
        for b in raw_bets:
            if not isinstance(b, dict) or b.get("type") not in ROULETTE_BET_TYPES:
                return jsonify({"error": "Unknown bet type."}), 400
            try:
                amount = float(b.get("amount") or 0)
            except (TypeError, ValueError, OverflowError):
                return jsonify({"error": "Invalid bet amount."}), 400
            if not math.isfinite(amount) or amount <= 0:
                return jsonify({"error": "Bet amounts must be positive."}), 400
            # Whole cents only, like every other money path: the old
            # code rounded each amount for payouts but deducted the
            # rounded sum of raw amounts, so the deducted total could
            # differ from the sum payouts were computed on.
            if isinstance(b.get("amount"), bool) or round(amount, 2) != amount:
                return jsonify({"error": "Bet amounts must be in whole cents."}), 400
            value = b.get("value")
            if b["type"] == "straight":
                if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 36:
                    return jsonify({"error": "Straight bets need a number 0-36."}), 400
            elif b["type"] in ("dozen", "column"):
                if isinstance(value, bool) or not isinstance(value, int) or value not in (1, 2, 3):
                    return jsonify({"error": "Dozens and columns need a value 1-3."}), 400
                value = value
            else:
                value = None
            bets.append({"type": b["type"], "value": value, "amount": round(amount, 2)})
            total += amount
        total = round(total, 2)
        data = dict(data)
        data["stake"] = total
        user, res = _casino_guard(data)
        if res is not None and not isinstance(res, float):
            return res
        number = secrets.randbelow(37)
        color = "green" if number == 0 else ("red" if number in ROULETTE_RED else "black")
        results = []
        payout = 0.0
        for b in bets:
            mult = _roulette_bet_win(b, number)
            pay = round(b["amount"] * mult, 2)
            payout += pay
            results.append({**b, "won": mult > 0, "multiplier": mult, "payout": pay})
        payout = round(payout, 2)
        bal = _casino_wallet(user["id"], total, payout,
                             f"Roulette spin {number} {color}, {len(bets)} bets",
                             game="Roulette",
                             outcome=f"Ball {number} {color}: " +
                             (f"won {payout:.2f}" if payout > 0 else "no win"))
        return jsonify({"ok": True, "number": number, "color": color,
                        "results": results, "total_stake": total,
                        "payout": payout, "balance": round(bal, 2)})

    # ----- Blackjack (6-deck shoe, dealer stands on all 17s) -----
    def _bj_shoe_row(db, user_id):
        row = db.execute("SELECT * FROM casino_games WHERE user_id = ? AND game = 'BlackjackShoe'"
                         " AND status = 'open' ORDER BY id DESC LIMIT 1",
                         (user_id,)).fetchone()
        if row and len(json.loads(row["state"])) >= BJ_RESHUFFLE_AT:
            return row
        if row:
            db.execute("UPDATE casino_games SET status = 'closed' WHERE id = ?", (row["id"],))
        cur = db.execute("INSERT INTO casino_games (user_id, game, state, stake, status, created_at)"
                         " VALUES (?, 'BlackjackShoe', ?, 0, 'open', ?)",
                         (user_id, json.dumps(_bj_new_shoe()), now_iso()))
        db.commit()
        return db.execute("SELECT * FROM casino_games WHERE id = ?", (cur.lastrowid,)).fetchone()

    def _bj_draw(db, user_id):
        """Pop one card from the player's shoe, reshuffling if empty."""
        row = _bj_shoe_row(db, user_id)
        cards = json.loads(row["state"])
        if not cards:
            db.execute("UPDATE casino_games SET status = 'closed' WHERE id = ?", (row["id"],))
            db.commit()
            row = _bj_shoe_row(db, user_id)
            cards = json.loads(row["state"])
        card = cards.pop(0)
        db.execute("UPDATE casino_games SET state = ? WHERE id = ?",
                   (json.dumps(cards), row["id"]))
        db.commit()
        return card

    def _bj_hand_or_error(user, game_id):
        game_id = _as_int_id(game_id)
        if game_id is None:
            return None, (jsonify({"error": "Invalid game id."}), 400)
        db = get_db()
        row = db.execute("SELECT * FROM casino_games WHERE id = ?", (game_id,)).fetchone()
        if not row or row["game"] != "Blackjack":
            return None, (jsonify({"error": "Unknown Blackjack hand."}), 404)
        if row["user_id"] != user["id"]:
            return None, (jsonify({"error": "This hand belongs to another player."}), 403)
        if row["status"] != "open":
            return None, (jsonify({"error": "This hand is already finished."}), 400)
        return row, None

    def _bj_settle(db, hand_row, state, outcome, payout):
        """Close the hand exactly once (conditional update) then settle
        the wallet. Returns True if this call closed the hand."""
        cur = db.execute("UPDATE casino_games SET status = 'closed' WHERE id = ? AND status = 'open'",
                         (hand_row["id"],))
        if cur.rowcount != 1:
            return False
        db.commit()
        stake = state["stake"] * (2 if state.get("doubled") else 1)
        _casino_wallet(hand_row["user_id"], 0, payout,
                       f"Blackjack: {outcome}",
                       game="Blackjack", outcome=outcome, hist_stake=stake)
        return True

    def _bj_dealer_play(db, user_id, state):
        while _bj_value(state["dealer"])[0] < 17:
            state["dealer"].append(_bj_draw(db, user_id))
        return state

    def _bj_settle_showdown(db, hand_row, state):
        """Dealer plays, then the hand is settled. Returns the payload,
        or None if another request already closed the hand."""
        state = _bj_dealer_play(db, user_id=hand_row["user_id"], state=state)
        pv, _ = _bj_value(state["player"])
        dv, _ = _bj_value(state["dealer"])
        stake = state["stake"] * (2 if state.get("doubled") else 1)
        if _bj_is_blackjack(state["player"]) and _bj_is_blackjack(state["dealer"]):
            outcome, payout = "Both blackjack — push", round(stake, 2)
        elif _bj_is_blackjack(state["player"]):
            outcome, payout = "Blackjack pays 3:2", round(stake * 2.5, 2)
        elif dv > 21:
            outcome, payout = f"Dealer busts ({dv}) — you win", round(stake * 2, 2)
        elif pv > dv:
            outcome, payout = f"You {pv} beat dealer {dv}", round(stake * 2, 2)
        elif pv < dv:
            outcome, payout = f"Dealer {dv} beats you {pv}", 0.0
        else:
            outcome, payout = f"Push at {pv}", round(stake, 2)
        if not _bj_settle(db, hand_row, state, outcome, payout):
            return None
        return {"dealer": state["dealer"], "dealer_value": dv,
                "player_value": pv, "outcome": outcome, "payout": payout}

    def _bj_public_hand(state, reveal_dealer):
        return {"player": state["player"],
                "player_value": _bj_value(state["player"])[0],
                "dealer": state["dealer"] if reveal_dealer else [state["dealer"][0]],
                "dealer_upcard": state["dealer"][0],
                "dealer_value": _bj_value(state["dealer"])[0] if reveal_dealer else None,
                "dealer_hidden": not reveal_dealer}

    @app.post("/api/casino/blackjack/deal")
    def casino_bj_deal():
        data = request.get_json(force=True, silent=True) or {}
        user, res = _casino_guard(data)
        if res is not None and not isinstance(res, float):
            return res
        stake = res
        db = get_db()
        if db.execute("SELECT id FROM casino_games WHERE user_id = ? AND game = 'Blackjack'"
                      " AND status = 'open'", (user["id"],)).fetchone():
            return jsonify({"error": "Finish your open hand first."}), 400
        player = [_bj_draw(db, user["id"]), _bj_draw(db, user["id"])]
        dealer = [_bj_draw(db, user["id"]), _bj_draw(db, user["id"])]
        state = {"player": player, "dealer": dealer, "doubled": False, "stake": stake}
        cur = db.execute("INSERT INTO casino_games (user_id, game, state, stake, status, created_at)"
                         " VALUES (?, 'Blackjack', ?, ?, 'open', ?)",
                         (user["id"], json.dumps(state), stake, now_iso()))
        game_id = cur.lastrowid
        # No commit here on purpose: _casino_wallet below commits
        # the record AND the deduction together. If the deduction
        # raises (funds drained concurrently), teardown discards
        # this record instead of leaving a free round.
        _casino_wallet(user["id"], stake, 0, "Blackjack deal")
        hand_row = db.execute("SELECT * FROM casino_games WHERE id = ?", (game_id,)).fetchone()
        # Immediate blackjacks: dealer peeks only when an ace/ten shows.
        player_bj = _bj_is_blackjack(player)
        dealer_bj = _bj_is_blackjack(dealer)
        if player_bj or dealer_bj:
            if player_bj and dealer_bj:
                outcome, payout = "Both blackjack — push", round(stake, 2)
            elif player_bj:
                outcome, payout = "Blackjack pays 3:2", round(stake * 2.5, 2)
            else:
                outcome, payout = "Dealer blackjack", 0.0
            _bj_settle(db, hand_row, state, outcome, payout)
            payload = _bj_public_hand(state, True)
            payload.update({"ok": True, "game_id": game_id, "settled": True,
                            "outcome": outcome, "payout": payout})
            return jsonify(payload)
        payload = _bj_public_hand(state, False)
        payload.update({"ok": True, "game_id": game_id, "settled": False})
        return jsonify(payload)

    @app.post("/api/casino/blackjack/hit")
    def casino_bj_hit():
        err = _casino_player(current_user())
        if err:
            return err
        user = current_user()
        data = request.get_json(force=True, silent=True) or {}
        hand_row, err2 = _bj_hand_or_error(user, data.get("game_id"))
        if err2:
            return err2
        db = get_db()
        state = json.loads(hand_row["state"])
        state["player"].append(_bj_draw(db, user["id"]))
        pv, _ = _bj_value(state["player"])
        if pv > 21:
            if not _bj_settle(db, hand_row, state, f"Bust at {pv}", 0.0):
                return jsonify({"error": "Hand already settled."}), 400
            payload = _bj_public_hand(state, True)
            payload.update({"ok": True, "game_id": hand_row["id"], "settled": True,
                            "bust": True, "outcome": f"Bust at {pv}", "payout": 0.0})
            return jsonify(payload)
        cur = db.execute("UPDATE casino_games SET state = ? WHERE id = ? AND state = ?",
                         (json.dumps(state), hand_row["id"], hand_row["state"]))
        if cur.rowcount != 1:
            return jsonify({"error": "Hand changed — hit again."}), 400
        db.commit()
        payload = _bj_public_hand(state, False)
        payload.update({"ok": True, "game_id": hand_row["id"], "settled": False,
                        "bust": False})
        return jsonify(payload)

    @app.post("/api/casino/blackjack/stand")
    def casino_bj_stand():
        err = _casino_player(current_user())
        if err:
            return err
        user = current_user()
        data = request.get_json(force=True, silent=True) or {}
        hand_row, err2 = _bj_hand_or_error(user, data.get("game_id"))
        if err2:
            return err2
        db = get_db()
        state = json.loads(hand_row["state"])
        result = _bj_settle_showdown(db, hand_row, state)
        if result is None:
            return jsonify({"error": "Hand already settled."}), 400
        bal = db.execute("SELECT balance FROM users WHERE id = ?", (user["id"],)).fetchone()["balance"]
        result.update({"ok": True, "game_id": hand_row["id"], "settled": True,
                       "balance": round(bal, 2)})
        return jsonify(result)

    @app.post("/api/casino/blackjack/double")
    def casino_bj_double():
        data = request.get_json(force=True, silent=True) or {}
        user = current_user()
        err = _casino_player(user)
        if err:
            return err
        hand_row, err2 = _bj_hand_or_error(user, data.get("game_id"))
        if err2:
            return err2
        db = get_db()
        state = json.loads(hand_row["state"])
        if state.get("doubled") or len(state["player"]) != 2:
            return jsonify({"error": "Double down is only available on your first two cards."}), 400
        extra = state["stake"]
        available = round(user["balance"] - user["exposure"], 2)
        if extra > available:
            return jsonify({"error": f"Double needs {extra:.2f} pts, available {available:.2f} pts."}), 400
        # Claim the doubled state conditionally FIRST (uncommitted),
        # then let the wallet commit state + deduction together. The
        # old order (mark doubled + commit, then deduct) left a doubled
        # hand with the extra stake uncollected on deduction failure,
        # and an unconditional update let twin doubles both pay.
        state["doubled"] = True
        orig_state = hand_row["state"]
        cur = db.execute("UPDATE casino_games SET state = ? WHERE id = ?"
                         " AND status = 'open' AND state = ?",
                         (json.dumps(state), hand_row["id"], orig_state))
        if cur.rowcount != 1:
            return jsonify({"error": "Hand changed — try again."}), 400
        _casino_wallet(user["id"], extra, 0, "Blackjack double down")
        state["player"].append(_bj_draw(db, user["id"]))
        pv, _ = _bj_value(state["player"])
        if pv > 21:
            if not _bj_settle(db, hand_row, state, f"Bust at {pv} after double", 0.0):
                return jsonify({"error": "Hand already settled."}), 400
            payload = _bj_public_hand(state, True)
            payload.update({"ok": True, "game_id": hand_row["id"], "settled": True,
                            "bust": True, "outcome": f"Bust at {pv} after double",
                            "payout": 0.0})
            return jsonify(payload)
        result = _bj_settle_showdown(db, hand_row, state)
        if result is None:
            return jsonify({"error": "Hand already settled."}), 400
        bal = db.execute("SELECT balance FROM users WHERE id = ?", (user["id"],)).fetchone()["balance"]
        result.update({"ok": True, "game_id": hand_row["id"], "settled": True,
                       "doubled": True, "balance": round(bal, 2)})
        return jsonify(result)

    # ----- Slots (5x3, 10 paylines, free spins) -----
    def _slots_open_free(db, user_id):
        return db.execute("SELECT * FROM casino_games WHERE user_id = ? AND game = 'SlotsFree'"
                          " AND status = 'open' ORDER BY id DESC LIMIT 1",
                          (user_id,)).fetchone()

    @app.get("/api/casino/slots/state")
    def casino_slots_state():
        user = current_user()
        if not user:
            return jsonify({"ok": True, "free_spins_remaining": 0})
        row = _slots_open_free(get_db(), user["id"])
        remaining = json.loads(row["state"])["remaining"] if row else 0
        return jsonify({"ok": True, "free_spins_remaining": remaining})

    @app.post("/api/casino/slots/spin")
    def casino_slots_spin():
        data = request.get_json(force=True, silent=True) or {}
        user, res = _casino_guard(data)
        if res is not None and not isinstance(res, float):
            return res
        stake = res
        grid = _slots_draw_grid()
        wins, scatters, scatter_pay, payout = _slots_payouts(grid, stake)
        triggered = SLOTS_FREE_SPINS if scatters >= 3 else 0
        db = get_db()
        if triggered:
            cur = db.execute("INSERT INTO casino_games (user_id, game, state, stake, status, created_at)"
                             " VALUES (?, 'SlotsFree', ?, 0, 'open', ?)",
                             (user["id"], json.dumps({"remaining": triggered, "total_won": 0.0,
                                                      "base_stake": stake}),
                              now_iso()))
            db.commit()
        bal = _casino_wallet(user["id"], stake, payout,
                             f"Slots spin, {scatters} scatters" +
                             (f", {triggered} free spins triggered" if triggered else ""),
                             game="Slots",
                             outcome=f"{len(wins)} line wins, {scatters} scatters"
                             + (f", +{triggered} free spins" if triggered else ""))
        return jsonify({"ok": True, "grid": grid, "line_wins": wins,
                        "scatters": scatters, "scatter_payout": scatter_pay,
                        "payout": payout, "balance": round(bal, 2),
                        "free_spins_triggered": triggered,
                        "free_spins_remaining": triggered})

    @app.post("/api/casino/slots/free-spin")
    def casino_slots_free_spin():
        err = _casino_player(current_user())
        if err:
            return err
        user = current_user()
        db = get_db()
        row = _slots_open_free(db, user["id"])
        if not row:
            return jsonify({"error": "No free spins pending."}), 400
        state = json.loads(row["state"])
        grid = _slots_draw_grid()
        # Free spins reuse the paid-spin evaluator with the triggering
        # spin's stake as the base: line wins pay paytable x (base/10)
        # x 2, scatter pays x base x 2. A retrigger adds 10 more spins.
        base = state.get("base_stake", 0) or 0
        wins, scatters, scatter_pay, payout = _slots_payouts(grid, base, free=True)
        retrigger = SLOTS_FREE_SPINS if scatters >= 3 else 0
        state["remaining"] -= 1
        state["remaining"] += retrigger
        state["total_won"] = round(state.get("total_won", 0) + payout, 2)
        # Compare-and-swap on the exact prior state: a concurrent twin
        # claim cannot both decrement the same remaining spin and both
        # pay. The closing claim also carries the status change.
        if state["remaining"] <= 0:
            cur = db.execute("UPDATE casino_games SET state = ?, status = 'closed'"
                             " WHERE id = ? AND state = ?",
                             (json.dumps(state), row["id"], row["state"]))
        else:
            cur = db.execute("UPDATE casino_games SET state = ? WHERE id = ? AND state = ?",
                             (json.dumps(state), row["id"], row["state"]))
        if cur.rowcount != 1:
            return jsonify({"error": "Free spin already claimed — refresh."}), 400
        db.commit()
        bal = _casino_wallet(user["id"], 0, payout, "Slots free spin",
                             game="Slots", hist_stake=0,
                             outcome=f"Free spin: {len(wins)} line wins, {scatters} scatters")
        return jsonify({"ok": True, "grid": grid, "line_wins": wins,
                        "scatters": scatters, "scatter_payout": scatter_pay,
                        "payout": payout, "balance": round(bal, 2),
                        "free_spins_triggered": retrigger,
                        "free_spins_remaining": max(0, state["remaining"]),
                        "free_spins_total_won": state["total_won"]})

    # ----- Dino Run (original) -----
    # One settled round per play. The player picks a distance band;
    # the server draws the run distance with secrets and the dino
    # animation on screen only replays that distance. Bands and
    # total-return multipliers are tuned to ~97% RTP each
    # (probability x multiplier): short 0.50 x 1.94 = 0.970, steady
    # 0.30 x 3.23 = 0.969, long 0.15 x 6.47 = 0.9705, marathon
    # 0.05 x 19.40 = 0.970. Only the generic idea of a runner game
    # is borrowed; the mechanic, bands, payouts and art are original
    # and no code or art from any other game is used.
    DINO_BANDS = [
        {"id": "short", "label": "Short hop", "min": 0, "max": 99,
         "p": 0.50, "mult": 1.94},
        {"id": "steady", "label": "Steady run", "min": 100, "max": 249,
         "p": 0.30, "mult": 3.23},
        {"id": "long", "label": "Long run", "min": 250, "max": 499,
         "p": 0.15, "mult": 6.47},
        {"id": "marathon", "label": "Marathon", "min": 500, "max": 999,
         "p": 0.05, "mult": 19.40},
    ]

    @app.post("/api/casino/dino")
    def casino_dino():
        data = request.get_json(force=True, silent=True) or {}
        user, res = _casino_guard(data)
        if res is not None and not isinstance(res, float):
            return res
        stake = res
        band = next((b for b in DINO_BANDS if b["id"] == data.get("band")), None)
        if band is None:
            return jsonify({"error": "Pick a distance band: short, steady, long or marathon."}), 400
        # Server draw: pick a band by its probability, then a distance
        # uniformly inside it. The browser only animates this distance.
        u = secrets.randbelow(10000) / 10000
        acc = 0.0
        drawn = DINO_BANDS[-1]
        for b in DINO_BANDS:
            acc += b["p"]
            if u < acc:
                drawn = b
                break
        distance = drawn["min"] + secrets.randbelow(drawn["max"] - drawn["min"] + 1)
        win = drawn["id"] == band["id"]
        payout = round(stake * band["mult"], 2) if win else 0.0
        bal = _casino_wallet(user["id"], stake, payout,
                             f"Dino Run {distance}m ({drawn['label']}), bet {band['label']}",
                             game="Dino Run",
                             outcome=f"{'Won' if win else 'Lost'}: dino ran {distance}m"
                                     f" ({drawn['label']}), bet {band['label']} x{band['mult']}")
        return jsonify({"ok": True, "distance": distance, "band": drawn["id"],
                        "band_label": drawn["label"], "bet_band": band["id"],
                        "multiplier": band["mult"], "win": win,
                        "payout": payout, "balance": round(bal, 2)})

    # ----- Batch 4a: card & table games -----
    # Original implementations of the published rules for eight
    # card/table games. No code copied from any source (the Krush repo
    # has no licence and was used for its game list only, never its
    # code). Every outcome is drawn server-side with secrets; hidden
    # cards are never sent to the browser before settlement. Edge
    # policy: standard published paytables are kept where their edge
    # is near our 1-3% band, and adjusted or omitted where it is far
    # higher (baccarat tie, pair-plus, tie side bets) — each game's
    # edge is documented here and in the README.
    def _b4a_hand_or_error(user, game, game_id):
        """Open-round lookup for a multi-step game: unknown game 404,
        another player's round 403, finished round 400."""
        game_id = _as_int_id(game_id)
        if game_id is None:
            return None, (jsonify({"error": "Invalid game id."}), 400)
        db = get_db()
        row = db.execute("SELECT * FROM casino_games WHERE id = ?", (game_id,)).fetchone()
        if not row or row["game"] != game:
            return None, (jsonify({"error": f"Unknown {game} round."}), 404)
        if row["user_id"] != user["id"]:
            return None, (jsonify({"error": "This round belongs to another player."}), 403)
        if row["status"] != "open":
            return None, (jsonify({"error": "This round is already finished."}), 400)
        return row, None

    def _b4a_close(db, row, user_id, stake, payout, note, game, outcome):
        """Close the round exactly once (conditional update), then
        settle the wallet. Returns (closed, balance)."""
        cur = db.execute("UPDATE casino_games SET status = 'closed' WHERE id = ? AND status = 'open'",
                         (row["id"],))
        if cur.rowcount != 1:
            return False, None
        db.commit()
        bal = _casino_wallet(user_id, 0, payout, note, game=game,
                             outcome=outcome, hist_stake=stake)
        return True, bal

    def _b4a_open_round(db, user_id, game):
        return db.execute("SELECT id FROM casino_games WHERE user_id = ? AND game = ?"
                          " AND status = 'open'", (user_id, game)).fetchone()

    # ----- Baccarat -----
    # Standard drawing rules. Player 1:1 (2x total), banker 1:1 less 5%
    # commission (1.95x total), tie 10x total. Edges: player ~1.24%,
    # banker ~1.06%, tie ~4.8% — the tie payout is friendlier than the
    # standard 8:1 (~14.4% edge) but tie is still the worst bet.
    @app.post("/api/casino/baccarat")
    def casino_baccarat():
        data = request.get_json(force=True, silent=True) or {}
        user, res = _casino_guard(data)
        if res is not None and not isinstance(res, float):
            return res
        stake = res
        bet = data.get("bet")
        if bet not in ("player", "banker", "tie"):
            return jsonify({"error": "Bet must be player, banker or tie."}), 400
        player, banker = _bac_play(_cards_new_deck())
        pv, bv = _bac_value(player), _bac_value(banker)
        winner = "player" if pv > bv else ("banker" if bv > pv else "tie")
        if bet == winner:
            payout = round(stake * {"player": 2.0, "banker": 1.95, "tie": 10.0}[bet], 2)
        elif winner == "tie":
            payout = round(stake, 2)
        else:
            payout = 0.0
        bal = _casino_wallet(user["id"], stake, payout,
                             f"Baccarat {bet} bet, {winner} wins {pv}-{bv}",
                             game="Baccarat",
                             outcome=f"{winner} wins {pv}-{bv}, bet {bet}")
        return jsonify({"ok": True, "player": player, "banker": banker,
                        "player_value": pv, "banker_value": bv,
                        "winner": winner, "bet": bet,
                        "payout": payout, "balance": round(bal, 2)})

    # ----- Video Poker (Jacks or Better, 9/6 paytable) -----
    # Total-return multipliers: royal 250, straight flush 50, quads 25,
    # full house 9, flush 6, straight 4, trips 3, two pair 2, jacks or
    # better 1. Standard 9/6 table: 99.54% RTP, 0.46% edge. The deck
    # stays server-side; only the player's five cards are ever sent.
    @app.post("/api/casino/videopoker/deal")
    def casino_vp_deal():
        data = request.get_json(force=True, silent=True) or {}
        user, res = _casino_guard(data)
        if res is not None and not isinstance(res, float):
            return res
        stake = res
        db = get_db()
        if _b4a_open_round(db, user["id"], "VideoPoker"):
            return jsonify({"error": "Finish your open hand first."}), 400
        deck = _cards_new_deck()
        hand = [deck.pop(0) for _ in range(5)]
        state = {"hand": hand, "deck": deck, "stake": stake}
        cur = db.execute("INSERT INTO casino_games (user_id, game, state, stake, status, created_at)"
                         " VALUES (?, 'VideoPoker', ?, ?, 'open', ?)",
                         (user["id"], json.dumps(state), stake, now_iso()))
        game_id = cur.lastrowid
        # No commit here on purpose: _casino_wallet below commits
        # the record AND the deduction together. If the deduction
        # raises (funds drained concurrently), teardown discards
        # this record instead of leaving a free round.
        bal = _casino_wallet(user["id"], stake, 0, "Video Poker deal")
        return jsonify({"ok": True, "game_id": game_id, "hand": hand,
                        "settled": False, "balance": round(bal, 2)})

    @app.post("/api/casino/videopoker/draw")
    def casino_vp_draw():
        err = _casino_player(current_user())
        if err:
            return err
        user = current_user()
        data = request.get_json(force=True, silent=True) or {}
        row, err2 = _b4a_hand_or_error(user, "VideoPoker", data.get("game_id"))
        if err2:
            return err2
        holds = data.get("holds")
        if (not isinstance(holds, list)
                or any(not isinstance(h, int) or isinstance(h, bool) for h in holds)
                or any(h < 0 or h > 4 for h in holds)
                or len(set(holds)) != len(holds)):
            return jsonify({"error": "Holds must be distinct card positions 0-4."}), 400
        db = get_db()
        state = json.loads(row["state"])
        hand = state["hand"]
        deck = state["deck"]
        final = [hand[i] if i in holds else deck.pop(0) for i in range(5)]
        cat, key = _poker_rank(final)
        vals = set(_poker_val(c) for c in final)
        if cat == 8:
            mult = 250 if key[0] == 14 and vals == {10, 11, 12, 13, 14} else 50
            name = "Royal flush" if mult == 250 else "Straight flush"
        elif cat == 7:
            mult, name = 25, "Four of a kind"
        elif cat == 6:
            mult, name = 9, "Full house"
        elif cat == 5:
            mult, name = 6, "Flush"
        elif cat == 4:
            mult, name = 4, "Straight"
        elif cat == 3:
            mult, name = 3, "Three of a kind"
        elif cat == 2:
            mult, name = 2, "Two pair"
        elif cat == 1 and key[0] >= 11:
            mult, name = 1, "Jacks or Better"
        else:
            mult, name = 0, "No win"
        payout = round(state["stake"] * mult, 2)
        closed, bal = _b4a_close(db, row, user["id"], state["stake"], payout,
                            f"Video Poker {name}",
                            game="Video Poker", outcome=name)
        if not closed:
            return jsonify({"error": "Round already settled."}), 400
        return jsonify({"ok": True, "game_id": row["id"], "hand": final,
                        "category": name, "multiplier": mult,
                        "payout": payout, "settled": True,
                        "balance": round(bal, 2)})

    # ----- Three Card Poker (ante + play, ante bonus) -----
    # Dealer qualifies on queen-high or better. Ante bonus (profit on
    # the ante, paid whenever the player plays): straight flush 5:1,
    # trips 4:1, straight 1:1. Standard ante+play edge ~3.37%.
    # Pair-plus is deliberately omitted: its standard edge (~7.3%)
    # breaks the 1-3% house-edge policy; the ante bonus covers the
    # hand-quality payout instead. Dealer cards stay hidden until
    # the player plays or folds.
    def _threecard_qualifies(dealer):
        cat, _ = _poker_rank(dealer)
        if cat >= 1:
            return True
        return max(_poker_val(c) for c in dealer) >= 12

    @app.post("/api/casino/threecard/deal")
    def casino_3cp_deal():
        data = request.get_json(force=True, silent=True) or {}
        user, res = _casino_guard(data)
        if res is not None and not isinstance(res, float):
            return res
        stake = res
        db = get_db()
        if _b4a_open_round(db, user["id"], "ThreeCard"):
            return jsonify({"error": "Finish your open hand first."}), 400
        deck = _cards_new_deck()
        player = [deck.pop(0) for _ in range(3)]
        dealer = [deck.pop(0) for _ in range(3)]
        state = {"player": player, "dealer": dealer, "ante": stake}
        cur = db.execute("INSERT INTO casino_games (user_id, game, state, stake, status, created_at)"
                         " VALUES (?, 'ThreeCard', ?, ?, 'open', ?)",
                         (user["id"], json.dumps(state), stake, now_iso()))
        game_id = cur.lastrowid
        # No commit here on purpose: _casino_wallet below commits
        # the record AND the deduction together. If the deduction
        # raises (funds drained concurrently), teardown discards
        # this record instead of leaving a free round.
        bal = _casino_wallet(user["id"], stake, 0, "Three Card Poker ante")
        return jsonify({"ok": True, "game_id": game_id, "player": player,
                        "dealer": [], "dealer_hidden": True, "ante": stake,
                        "settled": False, "balance": round(bal, 2)})

    @app.post("/api/casino/threecard/play")
    def casino_3cp_play():
        err = _casino_player(current_user())
        if err:
            return err
        user = current_user()
        data = request.get_json(force=True, silent=True) or {}
        row, err2 = _b4a_hand_or_error(user, "ThreeCard", data.get("game_id"))
        if err2:
            return err2
        db = get_db()
        state = json.loads(row["state"])
        ante = state["ante"]
        available = round(user["balance"] - user["exposure"], 2)
        if ante > available:
            return jsonify({"error": f"Play needs {ante:.2f} pts, available {available:.2f} pts."}), 400
        db.commit()
        _casino_wallet(user["id"], ante, 0, "Three Card Poker play")
        player, dealer = state["player"], state["dealer"]
        pcat, pkey = _poker_rank(player)
        dcat, dkey = _poker_rank(dealer)
        qualifies = _threecard_qualifies(dealer)
        if not qualifies:
            ante_return, play_return = round(ante * 2, 2), round(ante, 2)
            result = "Dealer does not qualify — ante wins, play pushed"
        elif (pcat, pkey) > (dcat, dkey):
            ante_return, play_return = round(ante * 2, 2), round(ante * 2, 2)
            result = "Your hand beats the dealer"
        elif (pcat, pkey) < (dcat, dkey):
            ante_return, play_return = 0.0, 0.0
            result = "Dealer hand beats yours"
        else:
            ante_return, play_return = round(ante, 2), round(ante, 2)
            result = "Push"
        bonus = round(ante * {5: 5, 4: 4, 3: 1}.get(pcat, 0), 2)
        payout = round(ante_return + play_return + bonus, 2)
        closed, bal = _b4a_close(db, row, user["id"], ante * 2, payout,
                            f"Three Card Poker: {result}",
                            game="Three Card Poker", outcome=result)
        if not closed:
            return jsonify({"error": "Round already settled."}), 400
        return jsonify({"ok": True, "game_id": row["id"], "player": player,
                        "dealer": dealer, "qualifies": qualifies,
                        "result": result, "ante_bonus": bonus,
                        "payout": payout, "settled": True,
                        "balance": round(bal, 2)})

    @app.post("/api/casino/threecard/fold")
    def casino_3cp_fold():
        err = _casino_player(current_user())
        if err:
            return err
        user = current_user()
        data = request.get_json(force=True, silent=True) or {}
        row, err2 = _b4a_hand_or_error(user, "ThreeCard", data.get("game_id"))
        if err2:
            return err2
        db = get_db()
        state = json.loads(row["state"])
        closed, bal = _b4a_close(db, row, user["id"], state["ante"], 0.0,
                            "Three Card Poker fold",
                            game="Three Card Poker", outcome="Folded — ante lost")
        if not closed:
            return jsonify({"error": "Round already settled."}), 400
        return jsonify({"ok": True, "game_id": row["id"], "player": state["player"],
                        "dealer": state["dealer"], "payout": 0.0, "settled": True,
                        "balance": round(bal, 2)})

    # ----- Caribbean Stud -----
    # Ante + call (call = 2x ante; the deal requires 3x ante available
    # so a dealt hand can always afford its call). Dealer qualifies on
    # ace-king or better. Call pays (profit on the call): pair or less
    # 1:1, two pair 2:1, trips 3:1, straight 4:1, flush 5:1, full house
    # 7:1, quads 20:1, straight flush 50:1, royal 100:1. Standard edge
    # ~5.22% — kept as the published game; the standard paytable sets
    # it, so it is documented rather than tuned. Only the dealer's
    # upcard is shown before the call.
    @app.post("/api/casino/caribbean/deal")
    def casino_carib_deal():
        data = request.get_json(force=True, silent=True) or {}
        user, res = _casino_guard(data)
        if res is not None and not isinstance(res, float):
            return res
        ante = res
        available = round(user["balance"] - user["exposure"], 2)
        if ante * 3 > available:
            return jsonify({"error": f"Call costs 2x ante — keep {ante * 3:.2f} pts available."}), 400
        db = get_db()
        if _b4a_open_round(db, user["id"], "Caribbean"):
            return jsonify({"error": "Finish your open hand first."}), 400
        deck = _cards_new_deck()
        player = [deck.pop(0) for _ in range(5)]
        dealer = [deck.pop(0) for _ in range(5)]
        state = {"player": player, "dealer": dealer, "ante": ante}
        cur = db.execute("INSERT INTO casino_games (user_id, game, state, stake, status, created_at)"
                         " VALUES (?, 'Caribbean', ?, ?, 'open', ?)",
                         (user["id"], json.dumps(state), ante, now_iso()))
        game_id = cur.lastrowid
        # No commit here on purpose: _casino_wallet below commits
        # the record AND the deduction together. If the deduction
        # raises (funds drained concurrently), teardown discards
        # this record instead of leaving a free round.
        bal = _casino_wallet(user["id"], ante, 0, "Caribbean Stud ante")
        return jsonify({"ok": True, "game_id": game_id, "player": player,
                        "dealer_upcard": dealer[0], "dealer_hidden": True,
                        "ante": ante, "call": round(ante * 2, 2),
                        "settled": False, "balance": round(bal, 2)})

    def _carib_qualifies(dealer):
        cat, _ = _poker_rank(dealer)
        if cat >= 1:
            return True
        vals = [_poker_val(c) for c in dealer]
        return 14 in vals and 13 in vals

    @app.post("/api/casino/caribbean/call")
    def casino_carib_call():
        err = _casino_player(current_user())
        if err:
            return err
        user = current_user()
        data = request.get_json(force=True, silent=True) or {}
        row, err2 = _b4a_hand_or_error(user, "Caribbean", data.get("game_id"))
        if err2:
            return err2
        db = get_db()
        state = json.loads(row["state"])
        ante = state["ante"]
        call = round(ante * 2, 2)
        available = round(user["balance"] - user["exposure"], 2)
        if call > available:
            return jsonify({"error": f"Call needs {call:.2f} pts, available {available:.2f} pts."}), 400
        db.commit()
        _casino_wallet(user["id"], call, 0, "Caribbean Stud call")
        player, dealer = state["player"], state["dealer"]
        pcat, pkey = _poker_rank(player)
        dcat, dkey = _poker_rank(dealer)
        qualifies = _carib_qualifies(dealer)
        if not qualifies:
            ante_return, call_return = round(ante * 2, 2), call
            result = "Dealer does not qualify — ante wins, call pushed"
        elif (pcat, pkey) > (dcat, dkey):
            if pcat == 8:
                vals = set(_poker_val(c) for c in player)
                call_mult = 100 if pkey[0] == 14 and vals == {10, 11, 12, 13, 14} else 50
            else:
                call_mult = {0: 1, 1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 7, 7: 20}[pcat]
            ante_return = round(ante * 2, 2)
            call_return = round(call * (1 + call_mult), 2)
            result = "Your hand beats the dealer"
        elif (pcat, pkey) < (dcat, dkey):
            ante_return, call_return = 0.0, 0.0
            result = "Dealer hand beats yours"
        else:
            ante_return, call_return = round(ante, 2), call
            result = "Push"
        payout = round(ante_return + call_return, 2)
        closed, bal = _b4a_close(db, row, user["id"], ante * 3, payout,
                            f"Caribbean Stud: {result}",
                            game="Caribbean Stud", outcome=result)
        if not closed:
            return jsonify({"error": "Round already settled."}), 400
        return jsonify({"ok": True, "game_id": row["id"], "player": player,
                        "dealer": dealer, "qualifies": qualifies,
                        "result": result, "payout": payout, "settled": True,
                        "balance": round(bal, 2)})

    @app.post("/api/casino/caribbean/fold")
    def casino_carib_fold():
        err = _casino_player(current_user())
        if err:
            return err
        user = current_user()
        data = request.get_json(force=True, silent=True) or {}
        row, err2 = _b4a_hand_or_error(user, "Caribbean", data.get("game_id"))
        if err2:
            return err2
        db = get_db()
        state = json.loads(row["state"])
        closed, bal = _b4a_close(db, row, user["id"], state["ante"], 0.0,
                            "Caribbean Stud fold",
                            game="Caribbean Stud", outcome="Folded — ante lost")
        if not closed:
            return jsonify({"error": "Round already settled."}), 400
        return jsonify({"ok": True, "game_id": row["id"], "player": state["player"],
                        "dealer": state["dealer"], "payout": 0.0, "settled": True,
                        "balance": round(bal, 2)})

    # ----- Let It Ride -----
    # Three equal bets from one total stake (stake must be a multiple
    # of 3). After the first three cards the player pulls or rides bet
    # 1, then the first community card is revealed and bet 2 is pulled
    # or ridden; the second community card settles the 5-card hand.
    # Pulled bets are returned at settlement, not mid-round (same as
    # other multi-step games). Payouts are profit on each remaining
    # bet: pair of 10s+ 1:1, two pair 2:1, trips 3:1, straight 5:1,
    # flush 8:1, full house 11:1, quads 50:1, straight flush 200:1,
    # royal 1000:1. Standard edge ~3.51%.
    @app.post("/api/casino/letitride/deal")
    def casino_lir_deal():
        data = request.get_json(force=True, silent=True) or {}
        user, res = _casino_guard(data)
        if res is not None and not isinstance(res, float):
            return res
        stake = res
        cents = round(stake * 100)
        if cents < 300 or cents % 300 != 0:
            return jsonify({"error": "Stake must be a multiple of 3 (three equal bets)."}), 400
        bet = round(stake / 3, 2)
        db = get_db()
        if _b4a_open_round(db, user["id"], "LetItRide"):
            return jsonify({"error": "Finish your open round first."}), 400
        deck = _cards_new_deck()
        player = [deck.pop(0) for _ in range(3)]
        state = {"player": player, "deck": deck, "bet": bet, "total": stake,
                 "pulled": [False, False], "community": [], "stage": 0}
        cur = db.execute("INSERT INTO casino_games (user_id, game, state, stake, status, created_at)"
                         " VALUES (?, 'LetItRide', ?, ?, 'open', ?)",
                         (user["id"], json.dumps(state), stake, now_iso()))
        game_id = cur.lastrowid
        # No commit here on purpose: _casino_wallet below commits
        # the record AND the deduction together. If the deduction
        # raises (funds drained concurrently), teardown discards
        # this record instead of leaving a free round.
        bal = _casino_wallet(user["id"], stake, 0, "Let It Ride deal")
        return jsonify({"ok": True, "game_id": game_id, "player": player,
                        "bet": bet, "community": [], "stage": 0,
                        "settled": False, "balance": round(bal, 2)})

    @app.post("/api/casino/letitride/action")
    def casino_lir_action():
        err = _casino_player(current_user())
        if err:
            return err
        user = current_user()
        data = request.get_json(force=True, silent=True) or {}
        row, err2 = _b4a_hand_or_error(user, "LetItRide", data.get("game_id"))
        if err2:
            return err2
        action = data.get("action")
        if action not in ("ride", "pull"):
            return jsonify({"error": "Action must be ride or pull."}), 400
        db = get_db()
        state = json.loads(row["state"])
        stage = state["stage"]
        if stage > 1:
            return jsonify({"error": "This round is already finished."}), 400
        if action == "pull":
            state["pulled"][stage] = True
        state["community"].append(state["deck"].pop(0))
        state["stage"] = stage + 1
        if state["stage"] == 1:
            db.execute("UPDATE casino_games SET state = ? WHERE id = ?",
                       (json.dumps(state), row["id"]))
            db.commit()
            return jsonify({"ok": True, "game_id": row["id"],
                            "player": state["player"],
                            "community": state["community"],
                            "pulled": state["pulled"], "stage": 1,
                            "settled": False})
        hand = state["player"] + state["community"]
        cat, key = _poker_rank(hand)
        vals = set(_poker_val(c) for c in hand)
        if cat == 8:
            mult = 1000 if key[0] == 14 and vals == {10, 11, 12, 13, 14} else 200
            name = "Royal flush" if mult == 1000 else "Straight flush"
        elif cat == 7:
            mult, name = 50, "Four of a kind"
        elif cat == 6:
            mult, name = 11, "Full house"
        elif cat == 5:
            mult, name = 8, "Flush"
        elif cat == 4:
            mult, name = 5, "Straight"
        elif cat == 3:
            mult, name = 3, "Three of a kind"
        elif cat == 2:
            mult, name = 2, "Two pair"
        elif cat == 1 and key[0] >= 10:
            mult, name = 1, "Pair of 10s or better"
        else:
            mult, name = 0, "No win"
        bet = state["bet"]
        remaining = [bet, bet, bet]
        remaining[0] = 0 if state["pulled"][0] else bet
        remaining[1] = 0 if state["pulled"][1] else bet
        pulled_back = round((bet if state["pulled"][0] else 0)
                            + (bet if state["pulled"][1] else 0), 2)
        payout = round(sum(remaining) * (1 + mult) + pulled_back, 2)
        closed, bal = _b4a_close(db, row, user["id"], state["total"], payout,
                            f"Let It Ride {name}",
                            game="Let It Ride", outcome=name)
        if not closed:
            return jsonify({"error": "Round already settled."}), 400
        return jsonify({"ok": True, "game_id": row["id"],
                        "player": state["player"],
                        "community": state["community"],
                        "hand": hand, "category": name, "multiplier": mult,
                        "pulled": state["pulled"], "stage": 2,
                        "payout": payout, "settled": True,
                        "balance": round(bal, 2)})

    # ----- Dragon Tiger -----
    # One card each, ace low, king high; suits never matter. Win pays
    # 1:1 (2x total); a tie loses half the stake (0.5x). Edge ~3.73%.
    # Tie and suited-tie side bets are omitted: their standard edges
    # (~32% and ~13%) break the house-edge policy.
    @app.post("/api/casino/dragontiger")
    def casino_dt():
        data = request.get_json(force=True, silent=True) or {}
        user, res = _casino_guard(data)
        if res is not None and not isinstance(res, float):
            return res
        stake = res
        bet = data.get("bet")
        if bet not in ("dragon", "tiger"):
            return jsonify({"error": "Bet must be dragon or tiger."}), 400
        deck = _cards_new_deck()
        dragon, tiger = deck.pop(0), deck.pop(0)
        dv = 1 if dragon["rank"] == "A" else _poker_val(dragon)
        tv = 1 if tiger["rank"] == "A" else _poker_val(tiger)
        winner = "dragon" if dv > tv else ("tiger" if tv > dv else "tie")
        if bet == winner:
            payout = round(stake * 2, 2)
        elif winner == "tie":
            payout = round(stake / 2, 2)
        else:
            payout = 0.0
        bal = _casino_wallet(user["id"], stake, payout,
                             f"Dragon Tiger {bet} bet, {winner} wins",
                             game="Dragon Tiger",
                             outcome=f"{winner} wins, bet {bet}")
        return jsonify({"ok": True, "dragon": dragon, "tiger": tiger,
                        "winner": winner, "bet": bet,
                        "payout": payout, "balance": round(bal, 2)})

    # ----- Casino War -----
    # Ace high. Higher card wins 1:1 (2x total). On a tie the player
    # surrenders for half back, or goes to war with an equal second
    # bet: three cards burn, then new cards are dealt. A war win pays
    # the war bet 1:1 and returns the original bet; a war loss loses
    # both; a second tie also pays the war bet (tie on war favours
    # the player). Edge ~2.88% with surrender available.
    @app.post("/api/casino/war/deal")
    def casino_war_deal():
        data = request.get_json(force=True, silent=True) or {}
        user, res = _casino_guard(data)
        if res is not None and not isinstance(res, float):
            return res
        stake = res
        db = get_db()
        if _b4a_open_round(db, user["id"], "CasinoWar"):
            return jsonify({"error": "Finish your open round first."}), 400
        deck = _cards_new_deck()
        player, dealer = deck.pop(0), deck.pop(0)
        pv, dv = _poker_val(player), _poker_val(dealer)
        if pv != dv:
            payout = round(stake * 2, 2) if pv > dv else 0.0
            bal = _casino_wallet(user["id"], stake, payout,
                                 "Casino War deal",
                                 game="Casino War",
                                 outcome="You win" if pv > dv else "Dealer wins")
            return jsonify({"ok": True, "player": player, "dealer": dealer,
                            "tie": False, "settled": True, "payout": payout,
                            "balance": round(bal, 2)})
        state = {"player": player, "dealer": dealer, "deck": deck, "stake": stake}
        cur = db.execute("INSERT INTO casino_games (user_id, game, state, stake, status, created_at)"
                         " VALUES (?, 'CasinoWar', ?, ?, 'open', ?)",
                         (user["id"], json.dumps(state), stake, now_iso()))
        game_id = cur.lastrowid
        # No commit here on purpose: _casino_wallet below commits
        # the record AND the deduction together. If the deduction
        # raises (funds drained concurrently), teardown discards
        # this record instead of leaving a free round.
        bal = _casino_wallet(user["id"], stake, 0, "Casino War deal (tie)")
        return jsonify({"ok": True, "game_id": game_id, "player": player,
                        "dealer": dealer, "tie": True, "settled": False,
                        "balance": round(bal, 2)})

    @app.post("/api/casino/war/surrender")
    def casino_war_surrender():
        err = _casino_player(current_user())
        if err:
            return err
        user = current_user()
        data = request.get_json(force=True, silent=True) or {}
        row, err2 = _b4a_hand_or_error(user, "CasinoWar", data.get("game_id"))
        if err2:
            return err2
        db = get_db()
        state = json.loads(row["state"])
        payout = round(state["stake"] / 2, 2)
        closed, bal = _b4a_close(db, row, user["id"], state["stake"], payout,
                            "Casino War surrender",
                            game="Casino War", outcome="Surrendered — half back")
        if not closed:
            return jsonify({"error": "Round already settled."}), 400
        return jsonify({"ok": True, "game_id": row["id"],
                        "player": state["player"], "dealer": state["dealer"],
                        "payout": payout, "settled": True,
                        "balance": round(bal, 2)})

    @app.post("/api/casino/war/go")
    def casino_war_go():
        err = _casino_player(current_user())
        if err:
            return err
        user = current_user()
        data = request.get_json(force=True, silent=True) or {}
        row, err2 = _b4a_hand_or_error(user, "CasinoWar", data.get("game_id"))
        if err2:
            return err2
        db = get_db()
        state = json.loads(row["state"])
        stake = state["stake"]
        available = round(user["balance"] - user["exposure"], 2)
        if stake > available:
            return jsonify({"error": f"War needs {stake:.2f} pts, available {available:.2f} pts."}), 400
        db.commit()
        _casino_wallet(user["id"], stake, 0, "Casino War raise")
        deck = state["deck"]
        for _ in range(3):
            deck.pop(0)
        war_player, war_dealer = deck.pop(0), deck.pop(0)
        wp, wd = _poker_val(war_player), _poker_val(war_dealer)
        if wp >= wd:
            payout = round(stake * 3, 2)
            outcome = "War won — war bet pays, original returned"
            if wp == wd:
                outcome = "War tied — player wins the war bet"
        else:
            payout = 0.0
            outcome = "War lost"
        closed, bal = _b4a_close(db, row, user["id"], stake * 2, payout,
                            f"Casino War: {outcome}",
                            game="Casino War", outcome=outcome)
        if not closed:
            return jsonify({"error": "Round already settled."}), 400
        return jsonify({"ok": True, "game_id": row["id"],
                        "player": state["player"], "dealer": state["dealer"],
                        "war_player": war_player, "war_dealer": war_dealer,
                        "payout": payout, "settled": True,
                        "balance": round(bal, 2)})

    # ----- Red Dog -----
    # Ace high. Pair at deal: a third card of the same rank pays 11x
    # total, otherwise the stake pushes. Consecutive ranks push. Any
    # other pair leaves a spread (cards strictly between the two);
    # the player raises (equal second bet) or calls, then the third
    # card wins if it falls inside the spread, pushes if it matches
    # either card, and loses otherwise. Spread payouts (profit):
    # spread 1 → 5:1, 2 → 4:1, 3 → 2:1, 4+ → 1:1. Edge ~3.08%.
    @app.post("/api/casino/reddog/deal")
    def casino_rd_deal():
        data = request.get_json(force=True, silent=True) or {}
        user, res = _casino_guard(data)
        if res is not None and not isinstance(res, float):
            return res
        stake = res
        db = get_db()
        if _b4a_open_round(db, user["id"], "RedDog"):
            return jsonify({"error": "Finish your open round first."}), 400
        deck = _cards_new_deck()
        c1, c2 = deck.pop(0), deck.pop(0)
        v1, v2 = _poker_val(c1), _poker_val(c2)
        if v1 == v2:
            third = deck.pop(0)
            if _poker_val(third) == v1:
                payout, outcome = round(stake * 11, 2), "Three of a kind — pays 11x"
            else:
                payout, outcome = round(stake, 2), "Pair, third card missed — push"
            bal = _casino_wallet(user["id"], stake, payout, "Red Dog pair",
                                 game="Red Dog", outcome=outcome)
            return jsonify({"ok": True, "cards": [c1, c2], "third": third,
                            "pair": True, "settled": True, "payout": payout,
                            "outcome": outcome, "balance": round(bal, 2)})
        if abs(v1 - v2) == 1:
            bal = _casino_wallet(user["id"], stake, stake, "Red Dog consecutive",
                                 game="Red Dog", outcome="Consecutive — push")
            return jsonify({"ok": True, "cards": [c1, c2], "third": None,
                            "pair": False, "settled": True, "payout": round(stake, 2),
                            "outcome": "Consecutive — push",
                            "balance": round(bal, 2)})
        spread = abs(v1 - v2) - 1
        state = {"cards": [c1, c2], "deck": deck, "spread": spread, "stake": stake}
        cur = db.execute("INSERT INTO casino_games (user_id, game, state, stake, status, created_at)"
                         " VALUES (?, 'RedDog', ?, ?, 'open', ?)",
                         (user["id"], json.dumps(state), stake, now_iso()))
        game_id = cur.lastrowid
        # No commit here on purpose: _casino_wallet below commits
        # the record AND the deduction together. If the deduction
        # raises (funds drained concurrently), teardown discards
        # this record instead of leaving a free round.
        bal = _casino_wallet(user["id"], stake, 0, "Red Dog deal")
        return jsonify({"ok": True, "game_id": game_id, "cards": [c1, c2],
                        "spread": spread, "pair": False, "settled": False,
                        "balance": round(bal, 2)})

    def _reddog_settle(db, row, user, state, raised):
        """Draw the third card and settle. raised doubles the stake."""
        deck = state["deck"]
        third = deck.pop(0)
        stake = state["stake"] * (2 if raised else 1)
        v1, v2 = _poker_val(state["cards"][0]), _poker_val(state["cards"][1])
        vt = _poker_val(third)
        lo, hi = min(v1, v2), max(v1, v2)
        if vt == v1 or vt == v2:
            payout, outcome = round(stake, 2), "Third card matched — push"
        elif lo < vt < hi:
            mult = {1: 6, 2: 5, 3: 3}.get(state["spread"], 2)
            payout = round(stake * mult, 2)
            outcome = f"Third card inside the spread — pays {mult}x"
        else:
            payout, outcome = 0.0, "Third card outside the spread — lost"
        closed, bal = _b4a_close(db, row, user["id"], stake, payout,
                            f"Red Dog: {outcome}",
                            game="Red Dog", outcome=outcome)
        if not closed:
            return jsonify({"error": "Round already settled."}), 400
        return {"ok": True, "game_id": row["id"], "cards": state["cards"],
                "third": third, "spread": state["spread"],
                "payout": payout, "outcome": outcome, "settled": True,
                "balance": round(bal, 2)}

    @app.post("/api/casino/reddog/raise")
    def casino_rd_raise():
        err = _casino_player(current_user())
        if err:
            return err
        user = current_user()
        data = request.get_json(force=True, silent=True) or {}
        row, err2 = _b4a_hand_or_error(user, "RedDog", data.get("game_id"))
        if err2:
            return err2
        db = get_db()
        state = json.loads(row["state"])
        available = round(user["balance"] - user["exposure"], 2)
        if state["stake"] > available:
            return jsonify({"error": f"Raise needs {state['stake']:.2f} pts, available {available:.2f} pts."}), 400
        db.commit()
        _casino_wallet(user["id"], state["stake"], 0, "Red Dog raise")
        return jsonify(_reddog_settle(db, row, user, state, True))

    @app.post("/api/casino/reddog/call")
    def casino_rd_call():
        err = _casino_player(current_user())
        if err:
            return err
        user = current_user()
        data = request.get_json(force=True, silent=True) or {}
        row, err2 = _b4a_hand_or_error(user, "RedDog", data.get("game_id"))
        if err2:
            return err2
        db = get_db()
        state = json.loads(row["state"])
        return jsonify(_reddog_settle(db, row, user, state, False))

    # ----- Batch 4b: dice / wheel / table games -----
    # Original implementations of published rules (no copied code; the
    # Krush repo has no licence and supplied only the game list). Every
    # round settles in one POST through _casino_wallet; nothing that
    # affects the outcome is decided in the browser.

    # ----- Craps -----
    # Pass line 1.41%, don't pass 1.36%, field 2.78% (field: 12 pays
    # 2:1, 2 pays 3:1, 3/4/9/10/11 pay 1:1). The server rolls the whole
    # pass/don't-pass sequence (come-out + point rolls) and returns
    # every roll so the frontend can replay it.
    @app.post("/api/casino/craps")
    def casino_craps():
        data = request.get_json(force=True, silent=True) or {}
        user, res = _casino_guard(data)
        if res is not None and not isinstance(res, float):
            return res
        stake = res
        bet = data.get("bet")
        if bet not in ("pass", "dontpass", "field"):
            return jsonify({"error": "Bet must be pass, dontpass or field."}), 400
        if bet == "field":
            roll = _dice_roll(2)
            total = sum(roll)
            if total == 2:
                mult, outcome = 4.0, "Field: 2 pays 3:1"
            elif total == 12:
                mult, outcome = 3.0, "Field: 12 pays 2:1"
            elif total in (3, 4, 9, 10, 11):
                mult, outcome = 2.0, f"Field: {total} pays 1:1"
            else:
                mult, outcome = 0.0, f"Field: {total} loses"
            payout = round(stake * mult, 2)
            bal = _casino_wallet(user["id"], stake, payout, f"Craps field {total}",
                                 game="Craps", outcome=outcome)
            return jsonify({"ok": True, "bet": bet, "rolls": [roll],
                            "point": None, "outcome": outcome,
                            "payout": payout, "balance": round(bal, 2)})
        rolls = [_dice_roll(2)]
        total = sum(rolls[0])
        if total in (7, 11):
            win = bet == "pass"
            outcome = f"Come-out {total}: " + ("pass wins" if win else "don't pass loses")
            payout = round(stake * 2, 2) if win else 0.0
            point = None
        elif total in (2, 3):
            win = bet == "dontpass"
            outcome = f"Come-out {total}: " + ("don't pass wins" if win else "pass loses")
            payout = round(stake * 2, 2) if win else 0.0
            point = None
        elif total == 12:
            if bet == "dontpass":
                outcome, payout = "Come-out 12: don't pass pushes", round(stake, 2)
            else:
                outcome, payout = "Come-out 12: pass loses", 0.0
            point = None
        else:
            point = total
            outcome, payout = None, None
            while True:  # geometric termination: 7 or the point must come
                roll = _dice_roll(2)
                rolls.append(roll)
                t = sum(roll)
                if t == point:
                    win = bet == "pass"
                    outcome = f"Point {point} hit: " + ("pass wins" if win else "don't pass loses")
                    payout = round(stake * 2, 2) if win else 0.0
                    break
                if t == 7:
                    win = bet == "dontpass"
                    outcome = f"Seven-out: " + ("don't pass wins" if win else "pass loses")
                    payout = round(stake * 2, 2) if win else 0.0
                    break
        bal = _casino_wallet(user["id"], stake, payout, f"Craps {bet}: {outcome}",
                             game="Craps", outcome=outcome)
        return jsonify({"ok": True, "bet": bet, "rolls": rolls,
                        "point": point, "outcome": outcome,
                        "payout": payout, "balance": round(bal, 2)})

    # ----- Sic bo -----
    # Big/small pay 1:1 (2.78% edge; triples lose on big/small).
    # Single number uses _dice_single_mult (2.78% after the triple
    # adjustment). Combination (two distinct numbers both appear)
    # pays 6:1 (2.78%).
    @app.post("/api/casino/sicbo")
    def casino_sicbo():
        data = request.get_json(force=True, silent=True) or {}
        user, res = _casino_guard(data)
        if res is not None and not isinstance(res, float):
            return res
        stake = res
        bet = data.get("bet")
        if bet not in ("big", "small", "single", "combo"):
            return jsonify({"error": "Bet must be big, small, single or combo."}), 400
        number = None
        numbers = None
        if bet == "single":
            number = data.get("number")
            if isinstance(number, bool) or not isinstance(number, int) or not 1 <= number <= 6:
                return jsonify({"error": "Single bets need a number 1-6."}), 400
        if bet == "combo":
            numbers = data.get("numbers")
            if (not isinstance(numbers, list) or len(numbers) != 2
                    or any(isinstance(n, bool) or not isinstance(n, int)
                           or not 1 <= n <= 6 for n in numbers)
                    or numbers[0] == numbers[1]):
                return jsonify({"error": "Combo bets need two different numbers 1-6."}), 400
        dice = _dice_roll(3)
        total = sum(dice)
        triple = len(set(dice)) == 1
        if bet == "big":
            mult = 2.0 if (11 <= total <= 17 and not triple) else 0.0
            outcome = f"Big, total {total}" + (" (triple loses)" if triple else "")
        elif bet == "small":
            mult = 2.0 if (4 <= total <= 10 and not triple) else 0.0
            outcome = f"Small, total {total}" + (" (triple loses)" if triple else "")
        elif bet == "single":
            matches = dice.count(number)
            mult = _dice_single_mult(matches)
            outcome = f"Number {number} matched {matches} time(s)"
        else:
            mult = 7.0 if all(n in dice for n in numbers) else 0.0
            outcome = f"Combo {numbers[0]}-{numbers[1]}" + \
                (" hit" if mult else " missed")
        payout = round(stake * mult, 2)
        bal = _casino_wallet(user["id"], stake, payout, f"Sic bo {bet}: {outcome}",
                             game="Sic Bo", outcome=outcome)
        return jsonify({"ok": True, "bet": bet, "dice": dice, "total": total,
                        "triple": triple, "outcome": outcome,
                        "payout": payout, "balance": round(bal, 2)})

    # ----- Big Six wheel -----
    # Standard 54-segment wheel, standard payouts (see BIGSIX_PAY).
    @app.post("/api/casino/bigsix")
    def casino_bigsix():
        data = request.get_json(force=True, silent=True) or {}
        user, res = _casino_guard(data)
        if res is not None and not isinstance(res, float):
            return res
        stake = res
        bet = data.get("bet")
        if bet not in BIGSIX_PAY:
            return jsonify({"error": "Bet must be 1, 2, 5, 10, 20, joker or logo."}), 400
        idx = secrets.randbelow(len(BIGSIX_SEGMENTS))
        segment = BIGSIX_SEGMENTS[idx]
        mult = BIGSIX_PAY[segment] if bet == segment else 0.0
        payout = round(stake * mult, 2)
        outcome = f"Wheel stopped on {segment}" + (" — win" if mult else " — lose")
        bal = _casino_wallet(user["id"], stake, payout, f"Big Six bet {bet}: {outcome}",
                             game="Big Six", outcome=outcome)
        return jsonify({"ok": True, "bet": bet, "segment": segment,
                        "segment_index": idx, "outcome": outcome,
                        "payout": payout, "balance": round(bal, 2)})

    # ----- Chuck-a-Luck -----
    # Three dice, bet a number 1-6; pays by match count via
    # _dice_single_mult (2.78% after the triple adjustment; the
    # standard 3:1 triple payout is a 7.87% edge).
    @app.post("/api/casino/chuck")
    def casino_chuck():
        data = request.get_json(force=True, silent=True) or {}
        user, res = _casino_guard(data)
        if res is not None and not isinstance(res, float):
            return res
        stake = res
        number = data.get("number")
        if isinstance(number, bool) or not isinstance(number, int) or not 1 <= number <= 6:
            return jsonify({"error": "Chuck-a-Luck needs a number 1-6."}), 400
        dice = _dice_roll(3)
        matches = dice.count(number)
        mult = _dice_single_mult(matches)
        payout = round(stake * mult, 2)
        outcome = f"Number {number} matched {matches} time(s)"
        bal = _casino_wallet(user["id"], stake, payout, f"Chuck-a-Luck: {outcome}",
                             game="Chuck-a-Luck", outcome=outcome)
        return jsonify({"ok": True, "number": number, "dice": dice,
                        "matches": matches, "outcome": outcome,
                        "payout": payout, "balance": round(bal, 2)})

    # ----- Under / Over 7 -----
    # Two dice. Under (2-6) and over (8-12) pay 1:1; exactly 7 pays
    # 4:1. Standard payouts, 16.67% edge on every bet — documented
    # as the published game, like Big Six: no integer payout brings
    # this game to 1-3% (2x is 83.3%, 2.33x would be unrecognisable).
    @app.post("/api/casino/underover")
    def casino_underover():
        data = request.get_json(force=True, silent=True) or {}
        user, res = _casino_guard(data)
        if res is not None and not isinstance(res, float):
            return res
        stake = res
        bet = data.get("bet")
        if bet not in ("under", "over", "seven"):
            return jsonify({"error": "Bet must be under, over or seven."}), 400
        dice = _dice_roll(2)
        total = sum(dice)
        if bet == "under":
            mult = 2.0 if total < 7 else 0.0
        elif bet == "over":
            mult = 2.0 if total > 7 else 0.0
        else:
            mult = 5.0 if total == 7 else 0.0
        payout = round(stake * mult, 2)
        outcome = f"Total {total} — {'win' if mult else 'lose'} on {bet}"
        bal = _casino_wallet(user["id"], stake, payout, f"Under/Over 7 {bet}: {outcome}",
                             game="Under/Over 7", outcome=outcome)
        return jsonify({"ok": True, "bet": bet, "dice": dice, "total": total,
                        "outcome": outcome, "payout": payout,
                        "balance": round(bal, 2)})

    # ----- Mini roulette -----
    # 13 pockets (0-12), standard payouts: straight 11:1, dozens 2:1,
    # even-money 1:1. Edge 7.69% on every bet — the published mini
    # game, documented, not adjusted. Bets arrive as a list, mirroring
    # the European roulette endpoint.
    @app.post("/api/casino/miniroulette")
    def casino_miniroulette():
        data = request.get_json(force=True, silent=True) or {}
        raw_bets = data.get("bets")
        if not isinstance(raw_bets, list) or not raw_bets or len(raw_bets) > 20:
            return jsonify({"error": "Place 1-20 bets."}), 400
        bets = []
        total = 0.0
        for b in raw_bets:
            if not isinstance(b, dict) or b.get("type") not in MINI_BET_TYPES:
                return jsonify({"error": "Unknown bet type."}), 400
            try:
                amount = float(b.get("amount") or 0)
            except (TypeError, ValueError, OverflowError):
                return jsonify({"error": "Invalid bet amount."}), 400
            if not math.isfinite(amount) or amount <= 0:
                return jsonify({"error": "Bet amounts must be positive."}), 400
            # Whole cents only, like every other money path (see
            # roulette): payouts are computed on rounded amounts, so
            # the deducted total must match their sum exactly.
            if isinstance(b.get("amount"), bool) or round(amount, 2) != amount:
                return jsonify({"error": "Bet amounts must be in whole cents."}), 400
            value = b.get("value")
            if b["type"] == "straight":
                if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 12:
                    return jsonify({"error": "Straight bets need a number 0-12."}), 400
            elif b["type"] == "dozen":
                if isinstance(value, bool) or not isinstance(value, int) or value not in (1, 2, 3):
                    return jsonify({"error": "Dozens need a value 1-3."}), 400
            else:
                value = None
            bets.append({"type": b["type"], "value": value, "amount": round(amount, 2)})
            total += amount
        total = round(total, 2)
        data = dict(data)
        data["stake"] = total
        user, res = _casino_guard(data)
        if res is not None and not isinstance(res, float):
            return res
        number = secrets.randbelow(13)
        color = "green" if number == 0 else ("red" if number in MINI_RED else "black")
        results = []
        payout = 0.0
        for b in bets:
            t = b["type"]
            if t == "straight":
                mult = 12.0 if number == b["value"] else 0.0
            elif t == "red":
                mult = 2.0 if number in MINI_RED else 0.0
            elif t == "black":
                mult = 2.0 if number != 0 and number not in MINI_RED else 0.0
            elif t == "even":
                mult = 2.0 if number != 0 and number % 2 == 0 else 0.0
            elif t == "odd":
                mult = 2.0 if number % 2 == 1 else 0.0
            elif t == "low":
                mult = 2.0 if 1 <= number <= 6 else 0.0
            elif t == "high":
                mult = 2.0 if 7 <= number <= 12 else 0.0
            else:  # dozen: 1 -> 1-4, 2 -> 5-8, 3 -> 9-12
                lo = (b["value"] - 1) * 4 + 1
                mult = 3.0 if lo <= number <= lo + 3 else 0.0
            pay = round(b["amount"] * mult, 2)
            payout += pay
            results.append({**b, "won": mult > 0, "multiplier": mult, "payout": pay})
        payout = round(payout, 2)
        bal = _casino_wallet(user["id"], total, payout,
                             f"Mini roulette {number} {color}, {len(bets)} bets",
                             game="Mini Roulette",
                             outcome=f"Ball {number} {color}: " +
                             (f"won {payout:.2f}" if payout > 0 else "no win"))
        return jsonify({"ok": True, "number": number, "color": color,
                        "results": results, "total_stake": total,
                        "payout": payout, "balance": round(bal, 2)})

    # ----- Andar Bahar -----
    # A middle card is dealt, then cards alternate to Andar (first)
    # and Bahar until a card matches the middle rank. Andar pays 1:1,
    # Bahar pays 1:1, except an Andar win on the very first card pays
    # 25% (1.25x total) — the standard first-card reduction, which
    # keeps the edges at Andar ~1.41% / Bahar ~3.00% despite Andar's
    # dealing-order advantage (P(Andar) ~51.50%).
    @app.post("/api/casino/andarbahar")
    def casino_ab():
        data = request.get_json(force=True, silent=True) or {}
        user, res = _casino_guard(data)
        if res is not None and not isinstance(res, float):
            return res
        stake = res
        bet = data.get("bet")
        if bet not in ("andar", "bahar"):
            return jsonify({"error": "Bet must be andar or bahar."}), 400
        deck = _cards_new_deck()
        middle = deck.pop(0)
        rank = middle["rank"]
        andar_cards, bahar_cards = [], []
        winner, match_pos = None, None
        for i, card in enumerate(deck):  # 3 matching ranks remain, so a match is certain
            if i % 2 == 0:
                andar_cards.append(card)
                side = "andar"
            else:
                bahar_cards.append(card)
                side = "bahar"
            if card["rank"] == rank:
                winner, match_pos = side, i + 1
                break
        if winner == "andar" and match_pos == 1:
            if bet == "andar":
                payout = round(stake * 1.25, 2)
                outcome = "Andar wins on the first card — pays 25%"
            else:
                payout = 0.0
                outcome = "Andar wins on the first card, bet bahar loses"
        elif bet == winner:
            payout = round(stake * 2, 2)
            outcome = f"{winner.capitalize()} wins on card {match_pos}"
        else:
            payout = 0.0
            outcome = f"{winner.capitalize()} wins on card {match_pos}, bet {bet} loses"
        bal = _casino_wallet(user["id"], stake, payout, f"Andar Bahar {bet}: {outcome}",
                             game="Andar Bahar", outcome=outcome)
        return jsonify({"ok": True, "bet": bet, "middle": middle,
                        "andar_cards": andar_cards, "bahar_cards": bahar_cards,
                        "winner": winner, "match_position": match_pos,
                        "outcome": outcome, "payout": payout,
                        "balance": round(bal, 2)})

    # ----- Batch 4c: instant & arcade games -----
    # All original implementations of published rules (no copied code;
    # the Krush repo has no licence and supplied only the game list).
    # Every outcome is drawn server-side with secrets and settles
    # through _casino_wallet. Exact-edge games are verified with
    # Fraction arithmetic in tests; Bingo, Scratch and Darts carry
    # simulation-measured RTPs (Slots precedent) because their exact
    # edge needs enumeration/simulation over large outcome spaces.
    def _bingo_card():
        """A 5x5 card: columns B/I/N/G/O ranges, centre free (0)."""
        rng = secrets.SystemRandom()
        cols = [rng.sample(range(1, 16), 5), rng.sample(range(16, 31), 5),
                rng.sample(range(31, 46), 5), rng.sample(range(46, 61), 5),
                rng.sample(range(61, 76), 5)]
        card = [[cols[c][r] for c in range(5)] for r in range(5)]
        card[2][2] = 0
        return card

    def _bingo_lines(card, balls):
        """Count completed lines (5 rows, 5 cols, 2 diagonals)."""
        marked = set(balls) | {0}
        lines = 0
        for r in range(5):
            if all(card[r][c] in marked for c in range(5)):
                lines += 1
        for c in range(5):
            if all(card[r][c] in marked for r in range(5)):
                lines += 1
        if all(card[i][i] in marked for i in range(5)):
            lines += 1
        if all(card[i][4 - i] in marked for i in range(5)):
            lines += 1
        return lines

    BINGO_PAYOUT = {0: 0.0, 1: 5.0, 2: 21.0, 3: 100.0}
    SCRATCH_SYMBOLS = [("cherry", 30, 1.5), ("lemon", 25, 2.5),
                       ("bell", 20, 4.0), ("star", 12, 8.0),
                       ("seven", 8, 20.0), ("diamond", 5, 40.0)]
    SCRATCH_PAY = {name: mult for name, _w, mult in SCRATCH_SYMBOLS}
    FISH_TIERS = {"small": (600, 1.62), "medium": (400, 2.42),
                  "big": (250, 3.88), "golden": (100, 9.70)}
    TOWER_MULTS = [1.24, 1.59, 2.04, 2.62, 3.36, 4.31, 5.52, 7.08]
    CASE_TIERS = [(550, "common", 0.4), (250, "uncommon", 0.9),
                  (120, "rare", 1.7), (60, "epic", 3.4),
                  (20, "legendary", 6.0)]
    PENALTY_KEEPER = {"TL": 220, "TM": 60, "TR": 220,
                      "BL": 220, "BM": 60, "BR": 220}
    HORSES = [("Thunder Bolt", 300, 3.23), ("Desert Wind", 220, 4.41),
              ("Midnight Star", 180, 5.39), ("Golden Hoof", 140, 6.93),
              ("River Queen", 100, 9.70), ("Lucky Charm", 60, 16.17)]
    COLOR_WHEEL = [("red", 400, 2.42), ("blue", 300, 3.23),
                   ("green", 200, 4.85), ("gold", 100, 9.70)]

    @app.post("/api/casino/bingo")
    def casino_bingo():
        data = request.get_json(force=True, silent=True) or {}
        user, res = _casino_guard(data)
        if res is not None and not isinstance(res, float):
            return res
        stake = res
        card = _bingo_card()
        balls = sorted(secrets.SystemRandom().sample(range(1, 76), 30))
        numbers = {n for row in card for n in row if n != 0}
        full = numbers <= set(balls)
        lines = _bingo_lines(card, balls)
        if full:
            mult, outcome = 1000.0, f"Full house! All 24 numbers in 30 balls"
        elif lines >= 3:
            mult, outcome = 100.0, f"{lines} lines completed"
        elif lines:
            mult, outcome = BINGO_PAYOUT[lines], f"{lines} line{'s' if lines > 1 else ''} completed"
        else:
            mult, outcome = 0.0, "No line completed"
        payout = round(stake * mult, 2)
        bal = _casino_wallet(user["id"], stake, payout, f"Bingo: {outcome}",
                             game="Bingo", outcome=outcome)
        return jsonify({"ok": True, "card": card, "balls": balls,
                        "lines": lines, "full_house": full,
                        "multiplier": mult, "outcome": outcome,
                        "payout": payout, "balance": round(bal, 2)})

    @app.post("/api/casino/scratch")
    def casino_scratch():
        data = request.get_json(force=True, silent=True) or {}
        user, res = _casino_guard(data)
        if res is not None and not isinstance(res, float):
            return res
        stake = res
        bag = []
        for name, w, _m in SCRATCH_SYMBOLS:
            bag.extend([name] * w)
        rng = secrets.SystemRandom()
        grid = [rng.choice(bag) for _ in range(9)]
        lines_idx = [(0, 1, 2), (3, 4, 5), (6, 7, 8),
                     (0, 3, 6), (1, 4, 7), (2, 5, 8),
                     (0, 4, 8), (2, 4, 6)]
        best = None
        for a, b, c in lines_idx:
            if grid[a] == grid[b] == grid[c]:
                if best is None or SCRATCH_PAY[grid[a]] > SCRATCH_PAY[best]:
                    best = grid[a]
        mult = SCRATCH_PAY[best] if best else 0.0
        outcome = f"Three {best}s on a line" if best else "No matching line"
        payout = round(stake * mult, 2)
        bal = _casino_wallet(user["id"], stake, payout, f"Scratch: {outcome}",
                             game="Scratch", outcome=outcome)
        return jsonify({"ok": True, "grid": grid, "win_symbol": best,
                        "multiplier": mult, "outcome": outcome,
                        "payout": payout, "balance": round(bal, 2)})

    @app.post("/api/casino/fish")
    def casino_fish():
        data = request.get_json(force=True, silent=True) or {}
        user, res = _casino_guard(data)
        if res is not None and not isinstance(res, float):
            return res
        stake = res
        tier = data.get("tier")
        if tier not in FISH_TIERS:
            return jsonify({"error": "Tier must be small, medium, big or golden."}), 400
        prob, mult = FISH_TIERS[tier]
        caught = secrets.randbelow(1000) < prob
        payout = round(stake * mult, 2) if caught else 0.0
        outcome = f"Caught the {tier} fish (x{mult})" if caught else f"The {tier} fish got away"
        bal = _casino_wallet(user["id"], stake, payout, f"Fish table: {outcome}",
                             game="Fish Table", outcome=outcome)
        return jsonify({"ok": True, "tier": tier, "caught": caught,
                        "multiplier": mult if caught else 0.0,
                        "outcome": outcome, "payout": payout,
                        "balance": round(bal, 2)})

    def _tower_game_or_error(user, game_id):
        db = get_db()
        row = db.execute("SELECT * FROM casino_games WHERE id = ?", (game_id,)).fetchone()
        if not row or row["game"] != "Tower":
            return None, (jsonify({"error": "Unknown Tower game."}), 404)
        if row["user_id"] != user["id"]:
            return None, (jsonify({"error": "This game belongs to another player."}), 403)
        if row["status"] != "open":
            return None, (jsonify({"error": "This game is already closed."}), 400)
        return row, None

    @app.post("/api/casino/tower/start")
    def casino_tower_start():
        data = request.get_json(force=True, silent=True) or {}
        user, res = _casino_guard(data)
        if res is not None and not isinstance(res, float):
            return res
        stake = res
        db = get_db()
        cur = db.execute(
            "INSERT INTO casino_games (user_id, game, state, stake, status, created_at)"
            " VALUES (?, 'Tower', ?, ?, 'open', ?)",
            (user["id"], json.dumps({"level": 0}), stake, now_iso()))
        game_id = cur.lastrowid
        # No commit here on purpose: _casino_wallet below commits
        # the record AND the deduction together. If the deduction
        # raises (funds drained concurrently), teardown discards
        # this record instead of leaving a free round.
        # Stake leaves the wallet now (ledger row, no history row yet --
        # the round completes on cashout or bust, Mines pattern).
        _casino_wallet(user["id"], stake, 0, "Tower stake")
        return jsonify({"ok": True, "game_id": game_id, "level": 0,
                        "multipliers": TOWER_MULTS, "stake": stake})

    @app.post("/api/casino/tower/climb")
    def casino_tower_climb():
        user = current_user()
        if not user:
            return jsonify({"error": "Login required."}), 401
        data = request.get_json(force=True, silent=True) or {}
        try:
            game_id = int(data.get("game_id"))
        except (TypeError, ValueError, OverflowError):
            return jsonify({"error": "game_id is required."}), 400
        row, err = _tower_game_or_error(user, game_id)
        if err:
            return err
        state = json.loads(row["state"])
        level = state["level"]
        if level >= len(TOWER_MULTS):
            return jsonify({"error": "Already at the top — cash out."}), 400
        db = get_db()
        if not _tower_draw():
            cur = db.execute("UPDATE casino_games SET status = 'closed' WHERE id = ? AND status = 'open'",
                             (game_id,))
            if cur.rowcount != 1:
                return jsonify({"error": "This game is already closed."}), 400
            db.commit()
            _casino_wallet(user["id"], 0, 0, "Tower bust", game="Tower",
                           outcome=f"Bust on level {level + 1}",
                           hist_stake=row["stake"])
            return jsonify({"ok": True, "safe": False, "bust": True,
                            "level": level, "payout": 0.0})
        level += 1
        state["level"] = level
        cur = db.execute("UPDATE casino_games SET state = ? WHERE id = ? AND state = ?",
                         (json.dumps(state), game_id, row["state"]))
        if cur.rowcount != 1:
            return jsonify({"error": "Round changed — climb again."}), 400
        db.commit()
        mult = TOWER_MULTS[level - 1]
        return jsonify({"ok": True, "safe": True, "bust": False,
                        "level": level, "multiplier": mult,
                        "potential_payout": round(row["stake"] * mult, 2)})

    @app.post("/api/casino/tower/cashout")
    def casino_tower_cashout():
        user = current_user()
        if not user:
            return jsonify({"error": "Login required."}), 401
        data = request.get_json(force=True, silent=True) or {}
        try:
            game_id = int(data.get("game_id"))
        except (TypeError, ValueError, OverflowError):
            return jsonify({"error": "game_id is required."}), 400
        row, err = _tower_game_or_error(user, game_id)
        if err:
            return err
        state = json.loads(row["state"])
        level = state["level"]
        if level < 1:
            return jsonify({"error": "Climb at least one level before cashing out."}), 400
        mult = TOWER_MULTS[level - 1]
        payout = round(row["stake"] * mult, 2)
        db = get_db()
        cur = db.execute("UPDATE casino_games SET status = 'closed' WHERE id = ? AND status = 'open'",
                         (game_id,))
        if cur.rowcount != 1:
            return jsonify({"error": "This game is already closed."}), 400
        db.commit()
        bal = _casino_wallet(user["id"], 0, payout,
                             f"Tower cashout x{mult} (level {level})",
                             game="Tower",
                             outcome=f"Cashed out x{mult} at level {level}",
                             hist_stake=row["stake"])
        return jsonify({"ok": True, "level": level, "multiplier": mult,
                        "payout": payout, "balance": round(bal, 2)})

    # ---- resume endpoints (resilience audit) ----
    # A refresh/close/logout mid-round used to strand the stake
    # invisibly: the casino_games row stayed open but no UI path led
    # back to it. These endpoints return ONLY the public subset of an
    # open round (Mines bomb positions, the blackjack hole card, the
    # video-poker deck and hidden dealer cards are NEVER sent), so the
    # frontend can restore the round on page load. Shared rounds
    # (TeleFly, PvP, Lottery, Slots free spins) already had state
    # endpoints and are intentionally not duplicated here.
    def _open_round(user_id, game):
        db = get_db()
        return db.execute(
            "SELECT * FROM casino_games WHERE user_id = ? AND game = ?"
            " AND status = 'open' ORDER BY id DESC LIMIT 1",
            (user_id, game)).fetchone()

    def _resume_or_none(user, game):
        if not user:
            return jsonify({"error": "Login required."}), 401
        row = _open_round(user["id"], game)
        if not row:
            return jsonify({"open": False})
        return row

    @app.get("/api/casino/mines/state")
    def casino_mines_state():
        row = _resume_or_none(current_user(), "Mines")
        if not isinstance(row, sqlite3.Row):
            return row
        state = json.loads(row["state"])
        mult = _mines_multiplier(state["mines_count"], len(state["revealed"]))
        return jsonify({"open": True, "game_id": row["id"], "stake": row["stake"],
                        "mines_count": state["mines_count"],
                        "revealed": state["revealed"], "multiplier": mult,
                        "potential_payout": round(row["stake"] * mult, 2)})

    @app.get("/api/casino/tower/state")
    def casino_tower_state():
        row = _resume_or_none(current_user(), "Tower")
        if not isinstance(row, sqlite3.Row):
            return row
        state = json.loads(row["state"])
        level = state["level"]
        mult = TOWER_MULTS[level - 1] if level >= 1 else None
        return jsonify({"open": True, "game_id": row["id"], "stake": row["stake"],
                        "level": level, "multiplier": mult,
                        "potential_payout": round(row["stake"] * mult, 2)
                        if mult else 0.0})

    @app.get("/api/casino/blackjack/state")
    def casino_bj_state():
        row = _resume_or_none(current_user(), "Blackjack")
        if not isinstance(row, sqlite3.Row):
            return row
        state = json.loads(row["state"])
        payload = _bj_public_hand(state, False)
        payload.update({"open": True, "game_id": row["id"], "stake": row["stake"],
                        "doubled": bool(state.get("doubled"))})
        return jsonify(payload)

    @app.get("/api/casino/videopoker/state")
    def casino_vp_state():
        row = _resume_or_none(current_user(), "VideoPoker")
        if not isinstance(row, sqlite3.Row):
            return row
        state = json.loads(row["state"])
        return jsonify({"open": True, "game_id": row["id"], "stake": row["stake"],
                        "hand": state["hand"]})

    @app.get("/api/casino/threecard/state")
    def casino_3cp_state():
        row = _resume_or_none(current_user(), "ThreeCard")
        if not isinstance(row, sqlite3.Row):
            return row
        state = json.loads(row["state"])
        return jsonify({"open": True, "game_id": row["id"], "ante": state["ante"],
                        "player": state["player"]})

    @app.get("/api/casino/caribbean/state")
    def casino_carib_state():
        row = _resume_or_none(current_user(), "Caribbean")
        if not isinstance(row, sqlite3.Row):
            return row
        state = json.loads(row["state"])
        return jsonify({"open": True, "game_id": row["id"], "ante": state["ante"],
                        "call": round(state["ante"] * 2, 2),
                        "player": state["player"],
                        "dealer_upcard": state["dealer"][0]})

    @app.get("/api/casino/letitride/state")
    def casino_lir_state():
        row = _resume_or_none(current_user(), "LetItRide")
        if not isinstance(row, sqlite3.Row):
            return row
        state = json.loads(row["state"])
        return jsonify({"open": True, "game_id": row["id"], "stake": row["stake"],
                        "bet": state["bet"], "player": state["player"],
                        "community": state["community"],
                        "pulled": state["pulled"], "stage": state["stage"]})

    @app.get("/api/casino/war/state")
    def casino_war_state():
        row = _resume_or_none(current_user(), "CasinoWar")
        if not isinstance(row, sqlite3.Row):
            return row
        state = json.loads(row["state"])
        return jsonify({"open": True, "game_id": row["id"], "stake": row["stake"],
                        "player": state["player"], "dealer": state["dealer"]})

    @app.get("/api/casino/reddog/state")
    def casino_rd_state():
        row = _resume_or_none(current_user(), "RedDog")
        if not isinstance(row, sqlite3.Row):
            return row
        state = json.loads(row["state"])
        return jsonify({"open": True, "game_id": row["id"], "stake": row["stake"],
                        "cards": state["cards"], "spread": state["spread"]})

    @app.post("/api/casino/cases")
    def casino_cases():
        data = request.get_json(force=True, silent=True) or {}
        user, res = _casino_guard(data)
        if res is not None and not isinstance(res, float):
            return res
        stake = res
        roll = secrets.randbelow(1000)
        acc = 0
        tier, mult = CASE_TIERS[-1][1], CASE_TIERS[-1][2]
        for w, name, m in CASE_TIERS:
            acc += w
            if roll < acc:
                tier, mult = name, m
                break
        payout = round(stake * mult, 2)
        outcome = f"Opened a {tier} case (x{mult})"
        bal = _casino_wallet(user["id"], stake, payout, f"Cases: {outcome}",
                             game="Cases", outcome=outcome)
        return jsonify({"ok": True, "tier": tier, "multiplier": mult,
                        "outcome": outcome, "payout": payout,
                        "balance": round(bal, 2)})

    @app.post("/api/casino/penalty")
    def casino_penalty():
        data = request.get_json(force=True, silent=True) or {}
        user, res = _casino_guard(data)
        if res is not None and not isinstance(res, float):
            return res
        stake = res
        spot = data.get("spot")
        if spot not in PENALTY_KEEPER:
            return jsonify({"error": "Spot must be TL, TM, TR, BL, BM or BR."}), 400
        roll = secrets.randbelow(1000)
        acc = 0
        keeper = "BR"
        for name, w in PENALTY_KEEPER.items():
            acc += w
            if roll < acc:
                keeper = name
                break
        goal = keeper != spot
        mult = (1.24 if spot in ("TL", "TR", "BL", "BR") else 1.03) if goal else 0.0
        payout = round(stake * mult, 2)
        outcome = (f"GOAL! Keeper dived {keeper}, you shot {spot}"
                   if goal else f"Saved! Keeper dived {keeper}, you shot {spot}")
        bal = _casino_wallet(user["id"], stake, payout, f"Penalty: {outcome}",
                             game="Penalty", outcome=outcome)
        return jsonify({"ok": True, "spot": spot, "keeper": keeper,
                        "goal": goal, "multiplier": mult,
                        "outcome": outcome, "payout": payout,
                        "balance": round(bal, 2)})

    @app.post("/api/casino/darts")
    def casino_darts():
        data = request.get_json(force=True, silent=True) or {}
        user, res = _casino_guard(data)
        if res is not None and not isinstance(res, float):
            return res
        stake = res
        rng = secrets.SystemRandom()
        throws = []
        for _ in range(3):
            r = rng.randrange(100)
            if r < 15:
                throws.append({"label": "Miss", "score": 0})
            elif r < 65:
                v = rng.randrange(1, 21)
                throws.append({"label": f"Single {v}", "score": v})
            elif r < 85:
                v = rng.randrange(1, 21)
                throws.append({"label": f"Double {v}", "score": 2 * v})
            elif r < 95:
                v = rng.randrange(1, 21)
                throws.append({"label": f"Treble {v}", "score": 3 * v})
            else:
                throws.append({"label": "Bull", "score": 50})
        total = sum(t["score"] for t in throws)
        if total >= 120:
            mult = 12.0
        elif total >= 90:
            mult = 4.0
        elif total >= 60:
            mult = 2.0
        elif total >= 40:
            mult = 1.0
        else:
            mult = 0.0
        payout = round(stake * mult, 2)
        outcome = f"Total {total} ({', '.join(t['label'] for t in throws)})"
        bal = _casino_wallet(user["id"], stake, payout, f"Darts: {outcome}",
                             game="Darts", outcome=outcome)
        return jsonify({"ok": True, "throws": throws, "total": total,
                        "multiplier": mult, "outcome": outcome,
                        "payout": payout, "balance": round(bal, 2)})

    @app.post("/api/casino/horse")
    def casino_horse():
        data = request.get_json(force=True, silent=True) or {}
        user, res = _casino_guard(data)
        if res is not None and not isinstance(res, float):
            return res
        stake = res
        pick = data.get("horse")
        names = [h[0] for h in HORSES]
        if pick not in names:
            return jsonify({"error": "Pick one of the six horses."}), 400
        roll = secrets.randbelow(1000)
        acc = 0
        winner = HORSES[-1]
        for h in HORSES:
            acc += h[1]
            if roll < acc:
                winner = h
                break
        rest = [h[0] for h in HORSES if h[0] != winner[0]]
        secrets.SystemRandom().shuffle(rest)
        order = [winner[0]] + rest
        won = pick == winner[0]
        mult = winner[2] if won else 0.0
        payout = round(stake * mult, 2)
        outcome = (f"{winner[0]} wins (x{mult}) — your pick won"
                   if won else f"{winner[0]} wins — your pick {pick} lost")
        bal = _casino_wallet(user["id"], stake, payout, f"Horse race: {outcome}",
                             game="Horse Race", outcome=outcome)
        return jsonify({"ok": True, "pick": pick, "order": order,
                        "winner": winner[0], "multiplier": mult,
                        "outcome": outcome, "payout": payout,
                        "balance": round(bal, 2)})

    @app.post("/api/casino/colors")
    def casino_colors():
        data = request.get_json(force=True, silent=True) or {}
        user, res = _casino_guard(data)
        if res is not None and not isinstance(res, float):
            return res
        stake = res
        pick = data.get("color")
        names = [c[0] for c in COLOR_WHEEL]
        if pick not in names:
            return jsonify({"error": "Pick red, blue, green or gold."}), 400
        roll = secrets.randbelow(1000)
        acc = 0
        drawn = COLOR_WHEEL[-1]
        for c in COLOR_WHEEL:
            acc += c[1]
            if roll < acc:
                drawn = c
                break
        won = pick == drawn[0]
        mult = drawn[2] if won else 0.0
        payout = round(stake * mult, 2)
        outcome = (f"Wheel lands {drawn[0]} (x{mult}) — your pick won"
                   if won else f"Wheel lands {drawn[0]} — your pick {pick} lost")
        bal = _casino_wallet(user["id"], stake, payout, f"Colors: {outcome}",
                             game="Colors", outcome=outcome)
        return jsonify({"ok": True, "pick": pick, "color": drawn[0],
                        "multiplier": mult, "outcome": outcome,
                        "payout": payout, "balance": round(bal, 2)})

    @app.post("/api/casino/pick3")
    def casino_pick3():
        data = request.get_json(force=True, silent=True) or {}
        user, res = _casino_guard(data)
        if res is not None and not isinstance(res, float):
            return res
        stake = res
        bet = data.get("bet")
        raw = data.get("digits")
        digits = None
        if isinstance(raw, str) and len(raw) == 3 and raw.isdigit():
            digits = [int(ch) for ch in raw]
        elif (isinstance(raw, list) and len(raw) == 3
              and all(isinstance(d, int) and not isinstance(d, bool) and 0 <= d <= 9 for d in raw)):
            digits = list(raw)
        if bet not in ("straight", "box") or digits is None:
            return jsonify({"error": "Bet must be straight/box and digits must be 3 digits 0-9."}), 400
        draw = [secrets.randbelow(10) for _ in range(3)]
        if bet == "straight":
            mult = 970.0 if draw == digits else 0.0
            outcome = ("Straight hit!" if mult else "Straight missed")
        else:
            if sorted(draw) == sorted(digits):
                if digits[0] == digits[1] == digits[2]:
                    mult, outcome = 970.0, "Box hit on a triple — pays straight odds"
                elif len(set(digits)) == 2:
                    mult, outcome = 320.0, "Box hit on a pair"
                else:
                    mult, outcome = 160.0, "Box hit, any order"
            else:
                mult, outcome = 0.0, "Box missed"
        payout = round(stake * mult, 2)
        bal = _casino_wallet(user["id"], stake, payout, f"Pick 3 {bet}: {outcome}",
                             game="Pick 3", outcome=outcome)
        return jsonify({"ok": True, "bet": bet, "digits": digits,
                        "draw": draw, "multiplier": mult,
                        "outcome": outcome, "payout": payout,
                        "balance": round(bal, 2)})

    @app.get("/api/casino/launch/<provider>")
    def casino_live_launch(provider):
        token = live_feed.get_demo_token()
        if not token:
            return jsonify({"error": "Failed to acquire demo auth token"}), 502

        target_id = "EzugiLDLobby.201" if provider.lower() in ("ezugi", "live", "livecasino") else ("aviator" if provider.lower() == "aviator" else provider)
        upstream_url = f"https://api.clubcasinoz.com/casino/games/launch/{target_id}"
        req = urllib.request.Request(upstream_url, headers={
            "Authorization": f"Bearer {token}",
            "Origin": "https://www.radheex.com",
            "Referer": "https://www.radheex.com/",
            "x-op-key": "RDE",
            "User-Agent": "Mozilla/5.0"
        })
        try:
            with urllib.request.urlopen(req, timeout=6) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return jsonify({
                    "provider": provider,
                    "launch_url": data.get("url"),
                    "target": data.get("target", "_self")
                })
        except Exception as exc:
            return jsonify({"error": f"Upstream launch error: {exc}"}), 502

    return app


if __name__ == "__main__":
    import sys
    live_feed.USE_REALTIME = True
    port = int(os.environ.get("PORT", sys.argv[1] if len(sys.argv) > 1 else 5005))
    create_app().run(host="0.0.0.0", port=port, debug=False)
