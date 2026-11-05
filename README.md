# RadheEx Demo Clone — full working web app

An original-code rebuild of the feature set mapped in `../SITE_MAP.md`:
sportsbook (back/lay + fancy markets), points wallet with exposure
accounting, settlement, account reports, and thirty-eight playable in-house
casino games (Limbo, Plinko, Keno, Mines, Dice, TeleFly, Lucky Cups,
PvP Wheel, Lottery, Roulette, Blackjack, Slots, Dino Run). **Demo only: points wallet, delayed guest odds feed + simulated demo fixtures, no real money,
no provider integration.**

## Run it

```bash
pip install -r requirements.txt
python app.py
```

Then open http://127.0.0.1:5000/

No Node build step: the frontend is vanilla HTML/CSS/JS served by Flask,
the database is SQLite (`app.db`, created on first run).

## Demo account

- Username: `demo`
- Password: `demo123`
- Starting balance: 100.00 pts, exposure 0.00

New accounts are created by an admin or sub-admin, who sets the opening credit and hands over the login details. A sub-admin funds that opening credit from its own allotted balance (see "Credit model" below) — it cannot create credit.

## Demo admin account (agent panel)

- Username: `admin`
- Password: `admin123`
- Role: admin — manages players, assigns credit, settles markets.

**⚠️ WARNING: these are generic demo credentials. Change the admin
password (or remove the seeded admin) before any real use — anyone
with this login can create players, move credit, and settle markets.**

## Demo sub-admin account

- Username: `subadmin`
- Password: `subadmin123`
- Role: sub-admin — creates player IDs and manages credit, suspension
  and passwords for ITS OWN downline only (players it created). It
  cannot create sub-admins, settle markets, post notices, or see any
  other downline's players.

**⚠️ WARNING: same as above — generic demo credentials. Change the
sub-admin password (or remove the seeded sub-admin) before any real
use.**

## Admin / agent panel (agent-managed model)

No cashier — the same model as the original site: the admin creates
player IDs and assigns credit; players bet against that credit. The
panel lives at `#/admin` and is visible to admins and sub-admins;
every admin route also enforces the role server-side (a player gets
403, a logged-out visitor gets 401), so hiding the link is never the
only protection. Admin and sub-admin accounts cannot place bets.

- **Roles**: the main admin sees and manages EVERYTHING — every
  player from every downline, every sub-admin, all totals, the full
  ledger, all settlements and notices — and can manage any player
  directly. A sub-admin sees and manages ONLY its own downline.
  Market settlement stays main-admin-only (a settlement affects all
  players on a market and cannot be downline-scoped cleanly), as do
  global notices and sub-admin management.
- **Sub-admins**: the main admin creates sub-admin accounts (username
  + password) and allots them credit (admin panel, "Allot credit");
  a sub-admin funds its players from that allotted balance (see
  "Credit model" below). The main admin can also suspend/activate
  and reset passwords for sub-admins. A suspended sub-admin
  cannot log in. Sub-admins cannot create sub-admins or admins.
- **Credit model (transfer)**: the main admin is the funding source
  at the top of the tree — allotments to sub-admins create credit,
  and the main admin's own balance is untouched by them; main-admin
  player funding likewise mints. Sub-admin → player credit is a
  TRANSFER, not minting: the opening credit at player creation and
  every later add-credit both atomically debit the sub-admin's
  spendable balance (balance minus its own open exposure) and credit
  the player. Allotting more than the available balance is rejected
  with both balances unchanged, and concurrent allots cannot exceed
  the balance in total. Self-credit cannot mint anything (a
  sub-admin targeting its own id gets 404; the main admin targeting
  its own id gets 400). Deduct is a burn: the player loses, the
  sub-admin gains nothing back.
- **Player detail**: clicking a player shows the full record —
  username, balance, exposure, available, credit limit, status,
  created-by, created-at — plus that player's bets, statement entries
  and P&L. Main admin sees any player; a sub-admin sees only its own
  players (anything else is 404 — the same response as a missing id,
  so user ids cannot be enumerated).
- **Player activity**: the detail panel also shows where each player
  is betting and what they are playing — all bets (unsettled +
  settled, with match/event, market, selection, side, odds, stake,
  profit/loss, status, time, and origin: `live` for bets on shadow
  matches from the delayed feed, `simulated` otherwise); casino play
  history (game, stake, payout, profit, outcome, time);
  credit activity (credit given/deducted, by whom, when); and
  settlements affecting that player. Same scoping: main sees any
  player, sub-admin only its own downline (cross-downline is 404).
  Casino history is recorded from completed rounds onward only —
  play from before the history table existed is NOT backfilled, and
  history rows expose only game/stake/payout/profit/outcome/time.

- **Dashboard**: players, active count, total credit assigned,
  total exposure, plus the downline (players created by this admin).
- **Create player ID**: username (unique, case-insensitively),
  password, opening credit (quick chips 1000 / 5000 / 10000 / 25000).
  The player's balance and credit limit both start at the opening
  credit; "total credit assigned" is the sum of credit limits.
- **Manage players**: click a player for the action panel — add
  credit, deduct credit, suspend/activate, reset password.
  Deduction is rejected if it would take the balance below zero or
  below open exposure (unlike a silent clamp, the admin gets an
  error). Suspended players cannot log in and cannot place bets;
  the block bites immediately, even for a live session. Passwords
  are hashed server-side and are never displayed or logged.
- **Settlement (the admin's job)**: pick any market — simulated or
  live shadow — and declare its winning selection, or VOID. Every
  open bet on that market settles at once: back on the winner wins
  (profit = stake × (odds − 1)), lay against the winner wins the
  stake, all other open bets lose, VOID refunds stakes (exposure
  released, balance untouched). Fancy bets settle at their stored
  converted decimal odds (1 + rate/100) — the conversion happens
  once at placement, never again at settlement. A market settles
  exactly once; re-settling is rejected. Balances, exposure,
  statement, P&L and per-player notifications all update from the
  same settlement.
- **Audit trail**: every credit change, suspension, activation,
  password reset, settlement and notice is written to the
  `admin_log` table (who, what, when, amounts) and shown on the
  dashboard. Password values are never written there.
- **Notices**: the admin posts a short notice that shows on the
  home page (the slot the original's session-only marquee would
  fill). Clearing the text removes the notice.

## What is built

- **Auth**: login, logout, change password (hashed passwords,
  session cookie).
- **Sportsbook**: Home, In-Play, Cricket, Soccer, Tennis; match lists with
  LIVE badges, countdowns and suspended states; event pages with a
  Bookmaker (back/lay) market and a Fancy (Yes/No) market, market max
  limits, and odds that refresh every 10 seconds.
- **Bet slip**: inline slip with stake spinner, six quick-stake buttons
  (100 / 500 / 1000 / 5000 / 10000 / 50000 by default), place and cancel.
  Set Stake page customises the six buttons per user.
- **Wallet + exposure**: placing a back bet reserves the stake as
  exposure; a lay bet reserves stake × (odds − 1). Available =
  balance − exposure, shown in the header and always consistent with the
  statement ledger.
- **Settlement**: open an event page and use "Settle demo event" — bets
  resolve against deterministic seeded results. Back win credits profit
  (stake × (odds − 1)); back loss deducts the stake; lay win credits the
  stake; lay loss deducts the liability. Results, Profit Loss Report,
  Bet History, Unsettled Bets and Account Statement all update from the
  same settlement.
- **Account pages**: Account Statement (type + date filters), Profit
  Loss Report, Bet History, Unsettled Bets, Results, Notifications,
  Rules (original text), Change Password.
- **Casino**: thirty-eight playable in-house games (Limbo, Plinko, Keno, Mines,
  Dice, TeleFly shared crash, Lucky Cups, PvP Wheel, Lottery 6/49,
  Roulette, Blackjack, Slots, Dino Run, Baccarat, Video Poker, Three Card
  Poker, Caribbean Stud, Let It Ride, Dragon Tiger, Casino War, Red Dog,
  Craps, Sic Bo, Big Six, Chuck-a-Luck, Under/Over 7, Mini Roulette,
  Andar Bahar, Bingo, Scratch Cards, Fish Table, Tower, Cases, Penalty
  Shootout, Darts, Horse Race, Colors, Pick 3)
  with server-side outcomes and wallet settlement, plus honestly
  labelled provider slots ("coming soon") for future provider games.
  Shared-round games (TeleFly, PvP Wheel, Lottery) settle lazily from
  wall-clock phases — no background thread on the demo service.
  Roulette is a European single-zero wheel (straight 35:1, dozens and
  columns 2:1, even-money 1:1; 2.70% edge). Blackjack uses a 6-deck
  shoe, dealer stands on all 17s, blackjack pays 3:2, with hit, stand
  and double down; the dealer hole card is never sent before
  settlement. Slots is a 5×3 video slot with 10 paylines, weighted
  symbols and 10 retriggerable free spins at 2× all wins; the
  paytable in `app.py` (weights + multipliers) measures 96.3% RTP over
  300,000 simulated spins (base 87.7% + free spins 8.6%). Dino Run is
  a single settled round: the player picks a distance band (Short hop
  0–99 m, Steady run 100–249 m, Long run 250–499 m, Marathon 500 m+),
  the server draws the run distance with `secrets`, and the canvas
  dino only replays that distance; payouts are 1.94× / 3.23× / 6.47× /
  19.40×, each tuned to ~97% RTP.
  Batch 4a adds eight card/table games, all original implementations
  of their published rules (no copied code; the Krush repo has no
  licence and supplied only the game list). Baccarat uses standard
  drawing rules (player 1:1, banker 1:1 less 5% commission, tie 10×
  total — friendlier than the standard 8:1; edges ~1.24% / ~1.06% /
  ~4.8%). Video Poker is Jacks or Better on the standard 9/6 table
  (royal 250×, straight flush 50×, quads 25×, full house 9×, flush 6×,
  straight 4×, trips 3×, two pair 2×, jacks or better 1×; 99.54% RTP).
  Three Card Poker is ante + play with the dealer qualifying on
  queen-high or better and an ante bonus (straight flush 5:1, trips
  4:1, straight 1:1; ~3.37% edge); pair-plus is omitted because its
  standard ~7.3% edge breaks the 1-3% policy. Caribbean Stud is ante
  + 2×-ante call with the dealer qualifying on ace-king or better
  and the standard call paytable (pair or less 1:1 up to royal 100:1;
  ~5.22% edge, documented as the published game). Let It Ride splits
  one stake into three equal bets with pull/ride decisions and the
  standard paytable (pair of 10s+ 1:1 up to royal 1000:1; ~3.51%).
  Dragon Tiger pays 1:1 with a tie losing half (~3.73%); tie side
  bets are omitted (~32% / ~13% edges). Casino War pays 1:1 with
  surrender for half back or a war raise on ties (~2.88%). Red Dog
  pays on the spread (1 → 5:1, 2 → 4:1, 3 → 2:1, 4+ → 1:1; ~3.08%).
  Multi-step games (Video Poker, Three Card, Caribbean, Let It Ride,
  War ties, Red Dog spreads) keep state server-side in `casino_games`;
  dealer/hole cards are never sent before settlement.
  Batch 4b adds seven dice/wheel/table games, all original
  implementations of their published rules (no copied code; the Krush
  repo has no licence and supplied only the game list). Craps offers
  pass (1.41%), don't pass (1.36%, 12 pushes) and field (2.78%; 12
  pays 2:1, 2 pays 3:1); the server rolls the whole come-out + point
  sequence and returns every roll. Sic Bo offers big/small at 1:1
  (2.78%, triples lose), single number at 1:1 / 2:1 / 14:1 by match
  count (2.78%; the standard 3:1 triple payout is a 7.87% edge, so the
  triple payout is raised) and combination at 6:1 (2.78%).
  Chuck-a-Luck uses the same single-number table (2.78% after the
  same adjustment). Andar Bahar deals a middle card, then alternates
  to Andar (first) and Bahar until a rank match; winners pay 1:1
  except an Andar win on the first card, which pays 25% (edges
  Andar ~1.41% / Bahar ~3.00%). Three games keep their standard
  payouts as documented published-game exceptions, because no integer
  payout brings them to 1-3% without making them unrecognisable:
  Big Six (54 segments, 1:1 / 2:1 / 5:1 / 10:1 / 20:1 / joker-logo
  45:1; edges 11.1-22.2%), Under/Over 7 (under/over 1:1, exactly 7
  4:1; 16.67% on every bet) and Mini Roulette (13 pockets 0-12,
  straight 11:1, dozens 2:1, even-money 1:1; 7.69% on every bet).
  All seven settle in one POST through the shared wallet; dice and
  wheel outcomes use `secrets`.
  Batch 4c adds ten instant/arcade games, all original
  implementations of their published rules (no copied code; the Krush
  repo has no licence and supplied only the game list). Bingo is a
  75-ball 5×5 card with 30 draws (1 line 5×, 2 lines 21×, 3+ lines
  100×, full house 1000×; ~97.8% RTP measured over 200,000 simulated
  rounds). Scratch Cards is a 3×3 grid where any matching row, column
  or diagonal pays (cherry 1.5×, lemon 2.5×, bell 4×, star 8×, seven
  20×, diamond 40×; ~96.5% measured). Fish Table is a single-round
  catch game (small 60% → 1.62×, medium 40% → 2.42×, big 25% → 3.88×,
  golden 10% → 9.70×; ~97% each). Tower is a multi-step climb-or-cashout
  ladder (8 levels, 78% survival per level, multipliers 1.24×–7.08×;
  ~97% at every cash-out level; stake leaves at start, Mines pattern).
  Cases opens a tiered case (common 55% → 0.4×, uncommon 25% → 0.9×,
  rare 12% → 1.7×, epic 6% → 3.4×, legendary 2% → 6.0×; 97.3% RTP).
  Penalty Shootout picks a spot against a keeper who favours corners
  (22% each) over the centre (6% each); corners pay 1.24× on a goal,
  centre spots 1.03× (~96.7–96.8%). Darts throws three darts (miss
  15%, single 50%, double 20%, treble 10%, bull 5%) with total tiers
  (40+ → 1×, 60+ → 2×, 90+ → 4×, 120+ → 12×; ~96.8% measured). Horse
  Race runs six weighted horses (3.23×–16.17×, ~97% per pick) with a
  full finish order. Colors spins a four-color wheel (red 40% → 2.42×,
  blue 30% → 3.23×, green 20% → 4.85×, gold 10% → 9.70×; ~97% per
  pick). Pick 3 draws three digits (straight exact order 970×, box
  distinct 160×, box pair 320×, box triple pays straight odds; ~97%
  straight, ~96% box). Exact-edge games are verified with Fraction
  arithmetic in tests; Bingo, Scratch and Darts carry the
  simulation-measured figures above.
- **Bug fixes from the original map**: no "Bet Histroy" typo (Bet
  History everywhere); In-Play counts are computed from the same match
  list, so they cannot disagree; header balance and statement come from
  one ledger; footer links (About, Terms, Privacy, Contact) exist;
  amounts display as points with Indian-style grouping (no HKD or other
  currency); the +18 notice and a "demo — simulated odds and in-house
  games" label are always visible.

## How the simulated odds engine works

`app.py::ticked_odds` takes each selection's base odds and adds a small
deterministic jitter derived from the selection id and the current
10-second time bucket (±0.10). Odds therefore move on the board, but the
value is a pure function of (selection, time) — no external data. When a
bet is placed, the odds at that moment are snapshotted onto the bet.
This engine still powers the seeded demo events, including their
Fancy market (labelled simulated in the UI). Live event pages use
the real delayed feed for Fancy instead (see below).

## Live delayed feed (real data, read-only guest feed)

Home, In-Play, sport pages and live event pages now use the real
delayed guest feed instead of simulated lists. The server proxies it so
the browser never calls the feed directly (and so page polls share one
cached fetch):

- Upstream: `https://api.radheex.com/delaymarkets/` with headers
  `Content-Type: application/json` and `X-OP-KEY: RDE` (a public brand
  code, not a secret). GETs only, no logins, no orders.
- Proxy routes (all under `/api/live/`): `current`, `markets` (full
  list), `markets/selected?marketids=<id>` (single-market refresh),
  `live`, `eventtype/<1|2|4|7>` (1=Soccer, 2=Tennis, 4=Cricket; 7 is
  valid upstream but empty and unnamed; anything else is a 400),
  `event/<eventId>`, `menu`. The proxy caches upstream responses for
  ~4 seconds and the frontend polls every 4 seconds.
- Performance (optimization pass): the hot list paths are refreshed by
  a background thread off the request path (single-flight, stale-while-
  revalidate, demand-gated so quiet periods make no upstream traffic),
  so no list poll ever blocks on the upstream fetch; list endpoints
  serve pre-serialized snapshots with ETags (`?slim=1` returns best-odds-
  only rows, which is all list views render) and answer 304 when the
  payload is unchanged; home polls live every 4 s and the full list
  every 30 s (slim); hidden tabs skip poll network entirely. Event
  detail and materialize still fetch on demand (materialize must be
  fresh for bet validation). Render/Cloudflare already gzips responses,
  so no in-app gzip is used. The single sync worker is kept on purpose:
  the per-request schema/init writes would contend on SQLite under
  threads, so a threaded worker is a separate change, not this pass.
- Prices live in `metadata.book`, a pipe-delimited string parsed by
  `live_feed.py` into back/lay ladders (price + stake pairs). Runners
  without a book entry show no prices; suspended runners show empty
- Event detail books: detail responses carry books as a JSON-encoded
  dict string (`{"<marketId>": "<book>", ...}`); the parser decodes
  that form. Fancy/session books carry a third field per level
  (`price:stake:line`) — the line is the runs line shown under the
  button, and the price is percent-scale (100 = even money). The live
  event page (and the materialize step) therefore refresh OPEN,
  still-unpriced markets' prices through the targeted
  `markets/selected?marketids=` lookup and merge them in, so odds
  buttons are priced whenever the market has prices at all.
- On upstream failure, list routes return the local simulated matches
  in the same shape with `"source": "simulated-fallback"` and an
  `"error"` field, so the app never breaks. The event route returns a
  502 error payload instead (no sensible simulated fallback exists for
  one live event). Upstream fetches retry transient failures
  (IncompleteRead, RemoteDisconnected, timeouts) up to 3 times, and
  list routes fall back on ANY upstream exception — never a 500.
- Honest labelling: the feed is the DELAYED guest feed
  (`delaymarkets`), so the UI says "live delayed feed", never
  "real-time". List endpoints carry no fancy markets, but guest event
  detail DOES: live cricket detail returns OVERS + BATSMAN catalogues
  (123 for Himachal Pradesh v Rajasthan: OVERS 34, BATSMAN 70), and
  the live event page's Fancy section shows them with real prices.
  Demo (simulated) events keep their simulated Fancy, labelled
  simulated; simulated odds are never presented as live data.
- Parity additions (completeness sweep): the proxy now passes through
  the feed's TV/scorecard/announcement/market-condition fields. Live
  event pages show a 📺 Live TV toggle (the feed's own `tvUrl`,
  embedded as an iframe, exactly as the real site embeds it) plus a
  📢 Announcements panel for active feed messages; odds refresh
  pauses while TV is open so the player is not reloaded every 4 s.
  There is deliberately NO scorecard iframe: the real site's
  scorecard is an operator-API widget URL (LMT for soccer/tennis,
  cricket widget for cricket), gated to logged-in non-demo accounts,
  and guest detail carries no live-score data — an oddsdata
  `/score/<hash>/<score_id>` iframe was verified in a real browser
  to render a stream placeholder, not a scorecard. `scoreUrl` is
  still passed through for when operator access exists. Market
  headers show Min as well as Max and bet delay; bookmaker markets
  are now converted from percent rates to decimal odds (78 -> 1.78)
  in both the slip and the materialize step — the same conversion
  fancy markets already had — while WINNING_ODDS books already quote
  decimal odds and pass through unchanged. Event lists have a search
  box and a ★ pin button (pinned events persist in localStorage and
  appear in a Pinned card on Home). Footer and drawer gained
  Responsible Gaming and Game Rules pages.
- Live bets: clicking live odds materializes the event into local
  shadow rows (`POST /api/live/materialize`) and the bet is placed at
  the clicked live price through the normal `/api/bets` flow. Live
  matches cannot be settled (no results feed) and stay out of the
  simulated lists.

## How a real-time feed would plug in later

Replace the delayed guest base with the operator's real-time endpoint
(and a session, when the client provides operator access):

1. A poller (background thread or scheduled job) fetches fixtures and
   prices from the agreed feed provider and upserts them into the
   `matches` / `markets` / `selections` tables (keeping `base_back` /
   `base_lay` as the live price instead of a seed).
2. `ticked_odds` becomes a pass-through that returns the stored live
   price, or is deleted and the API reads prices directly.
3. Suspended/live status comes from the feed's match state instead of
   the seeded `status` column.
4. Settlement switches from seeded results to the feed's official
   results (the `matches.result` column already holds the winner; only
   its writer changes).

Nothing else needs to change: bet placement, exposure, settlement and
reports all read from the same tables.

## Casino provider seam

Real provider games would be added as new lobby tiles that open a
provider iframe with a session token, the same way the current lobby
marks provider slots. Wallet settlement for provider games would post to
the existing `transactions` ledger via a provider callback endpoint
(not built — no provider agreement exists for this demo).

## Tests

```bash
python -m pytest tests/ -q
```

91 tests cover auth, wallet, bet placement, back/lay exposure math,
settlement, P&L, statement consistency, set-stake, suspended-match
rejection, the casino history view, plus the live feed: book parsing
(normal ladders, suspended/empty sides, malformed segments, missing
books), the proxy routes (current, full markets, single-market lookup,
eventtype validation, event detail, upstream-error fallback, 4-second
cache), and materialized live bets placed at the clicked live price
with live-settlement rejection. The admin panel adds 10 more: admin
gating (403/401), player creation + case-insensitive uniqueness,
add/deduct rules (below-zero and below-exposure rejection),
suspension blocking login and live-session betting, password reset,
market settlement math for back/lay/fancy (including the live fancy
decimal conversion), settlement idempotency, audit-ledger contents
(with no password values), and home-page notices. The sub-admin role
adds 9 more: sub-admin seeding and gating, main-admin creation and
management of sub-admins, sub-admin downline scoping (own players
only, cross-downline 403, cannot create sub-admins/settle/post
notices), credit guards and password reset by sub-admins, suspension
blocking login and live-session betting, full player-detail views
with scoping, ledger scoping, and the end-to-end main → sub-admin →
player → credit → bet → main settlement chain.
