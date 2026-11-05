import sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open('static/app.js', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Clean duplicated block between list cache and liveListHtml
idx1 = text.find('function renderBox(boxId, events) {')
idx2 = text.find('function liveListHtml(events) {')

if idx1 != -1 and idx2 != -1 and idx1 < idx2:
    replacement_middle = """function renderPinnedBox() {
  const card = document.getElementById('pinnedCard');
  const box = document.getElementById('pinnedBox');
  if (!card || !box) return;
  const seen = {};
  const events = [];
  for (const key of ['liveNowBox', 'allEventsBox', 'liveBox']) {
    for (const ev of LIST_CACHE[key] || []) {
      if (PINNED.has(ev.event_id) && !seen[ev.event_id]) { seen[ev.event_id] = 1; events.push(ev); }
    }
  }
  card.style.display = events.length ? '' : 'none';
  box.innerHTML = events.length ? liveListHtml(events) : '';
  bindLiveRows();
  bindPinBtns();
}

function togglePin(eventId) {
  if (PINNED.has(eventId)) PINNED.delete(eventId); else PINNED.add(eventId);
  localStorage.setItem('pinnedEvents', JSON.stringify([...PINNED]));
}

function bindPinBtns() {
  document.querySelectorAll('.pin-btn').forEach(b => {
    b.onclick = e => {
      e.stopPropagation();
      togglePin(b.dataset.pin);
      for (const boxId of ['liveNowBox', 'allEventsBox', 'liveBox']) {
        if (LIST_CACHE[boxId]) renderBox(boxId, LIST_CACHE[boxId]);
      }
      renderPinnedBox();
    };
  });
}

function bindSearch() {
  document.querySelectorAll('.ev-search').forEach(inp => {
    inp.value = SEARCH_Q;
    inp.oninput = () => {
      SEARCH_Q = inp.value;
      document.querySelectorAll('.ev-search').forEach(o => { if (o !== inp) o.value = SEARCH_Q; });
      for (const boxId of ['liveNowBox', 'allEventsBox', 'liveBox']) {
        if (LIST_CACHE[boxId]) renderBox(boxId, LIST_CACHE[boxId]);
      }
      renderPinnedBox();
    };
  });
}

/* Left sport menu, matching real site's Popular menu with sprite sheet icons & official SVGs. */
function sidebarHtml(active) {
  const item = (label, href, key, icHtml) =>
    `<a href="${href}" class="${active === key ? 'on' : ''}"><span class="side-ic">${icHtml}</span> <span class="side-lbl">${label}</span></a>`;
  return `<aside class="sidebar"><div class="side-head">Popular</div>
    ${item('In-Play', '#/inplay', 'inplay', '<span class="sports-icon inplaytablet"></span>')}
    ${item('Multi Markets', '#/home', 'multimarkets', '<span class="sports-icon tennistablet"></span>')}
    ${item('WBBL 2026', '#/live/28045743', 'wbbl', '<span class="sports-icon iplwinnertablet"></span>')}
    ${item('Cricket', '#/sport/Cricket', 'Cricket', '<span class="sports-icon crickettablet"></span>')}
    ${item('Soccer', '#/sport/Soccer', 'Soccer', '<span class="sports-icon soccertablet"></span>')}
    ${item('Tennis', '#/sport/Tennis', 'Tennis', '<span class="sports-icon tennistablet"></span>')}
    ${item('Indian Poker', '#/casino/ezugi', 'poker', '<span class="sports-icon indianpokertablet"></span>')}
    ${item('Indian Poker II', '#/casino/ezugi', 'poker2', '<span class="sports-icon indianpokertablet"></span>')}
    ${item('RV Games', '#/casino/evolution', 'rv', '<span class="sports-icon casinoside-evotablet"></span>')}
    ${item('Aviator', '#/casino/telefly', 'aviator', '<img src="/static/images/aviator-icon.svg" class="side-plane-icon" alt="Aviator">')}
    ${item('Chicken Road', '#/casino/dino', 'chicken', '<img src="/static/images/inout-icon.svg" class="side-plane-icon" alt="Chicken Road">')}
    ${item('Live Casino', '#/casino/ezugi', 'casino', '<span class="sports-icon casinotablet"></span>')}
    ${item('Evolution', '#/casino/evolution', 'evolution', '<span class="sports-icon casinoside-evotablet"></span>')}
    ${item('Vivo', '#/casino/vivo', 'vivo', '<span class="sports-icon casinotablet"></span>')}
    ${item('Betgames', '#/casino/betgames', 'betgames', '<span class="sports-icon casinotablet"></span>')}
    ${item('Casino III', '#/casino/originals', 'casino3', '<span class="sports-icon casinotablet"></span>')}</aside>`;
}

/* Header clock + nav LIVE counts (presentation only; failures hide badges). */
function tickClock() {
  const el = document.getElementById('topClock');
  if (el) el.textContent = new Date().toLocaleString('en-GB', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  }).replace(/,/g, '');
}
async function updateNavCounts() {
  try {
    const data = await api('/api/live/markets?slim=1');
    const counts = {};
    for (const ev of data.events || []) {
      if (ev.in_play) counts[ev.sport] = (counts[ev.sport] || 0) + 1;
    }
    for (const [sport, id] of [['Cricket', 'navLiveCricket'], ['Soccer', 'navLiveSoccer'], ['Tennis', 'navLiveTennis']]) {
      const el = document.getElementById(id);
      if (!el) continue;
      const n = counts[sport] || 0;
      el.textContent = 'LIVE ' + n;
      el.style.display = n ? '' : 'none';
    }
  } catch (err) { /* badges stay hidden; nav still works */ }
}

function liveBanner(source, error) {
  if (source === 'live-delayed')
    return '<p class="live-note"><span class="live-dot-mini"></span> Live delayed feed — delayed guest data, not real-time.</p>';
  return `<p class="live-note">Simulated data — live feed unavailable${error ? ' (' + esc(error) + ')' : ''}.</p>`;
}

const LAST_ODDS = new Map();
function liveOddsCells(r) {
  if (!r || r.best_back == null || r.best_lay == null) {
    return '<button class="btn-back back btn-empty" disabled></button><button class="btn-lay lay btn-empty" disabled></button>';
  }
  const keyB = (r.id || r.name || '') + ':b';
  const keyL = (r.id || r.name || '') + ':l';
  const oldB = LAST_ODDS.get(keyB);
  const oldL = LAST_ODDS.get(keyL);
  LAST_ODDS.set(keyB, r.best_back);
  LAST_ODDS.set(keyL, r.best_lay);
  const flashB = oldB != null && oldB !== r.best_back ? (r.best_back > oldB ? 'odds-flash-up' : 'odds-flash-down') : '';
  const flashL = oldL != null && oldL !== r.best_lay ? (r.best_lay > oldL ? 'odds-flash-up' : 'odds-flash-down') : '';
  return `<button class="btn-back back ${flashB}" data-side="back" data-runner="${esc(r.name)}" data-price="${r.best_back}">${r.best_back}</button><button class="btn-lay lay ${flashL}" data-side="lay" data-runner="${esc(r.name)}" data-price="${r.best_lay}">${r.best_lay}</button>`;
}

function get1X2Runners(runners) {
  if (!runners || !runners.length) return [null, null, null];
  if (runners.length === 2) {
    return [runners[0], null, runners[1]];
  }
  if (runners.length === 3) {
    const draw = runners.find(r => /draw|tie/i.test(r.name || ''));
    if (draw) {
      const rest = runners.filter(r => r !== draw);
      return [rest[0] || null, draw, rest[1] || null];
    }
    return [runners[0], runners[1], runners[2]];
  }
  // For tournaments with >3 runners (e.g. WBBL):
  const priced = runners.filter(r => r.best_back != null && r.best_back > 0);
  const pool = priced.length ? priced : runners;
  return [pool[0] || null, pool[2] || pool[1] || null, pool[1] || pool[2] || null];
}

function liveEventRow(ev) {
  const m = ev.market || {};
  const liveBadge = ev.in_play ? '<span class="live-badge">Live Now</span>' : '';
  const dateStr = ev.open_date ? new Date(ev.open_date).toLocaleString('en-IN', {day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit'}) : '';
  const runners = (m.runners || []);
  const closed = m.status !== 'OPEN' || m.bet_lock;
  const [r1, rx, r2] = get1X2Runners(runners);

  const pair = (r) => {
    if (closed) return '<div class="suspended-full"><button class="btn-back back" disabled></button><button class="btn-lay lay" disabled></button></div>';
    if (!r) return '<div class="odds-cell-pair"><button class="btn-back back btn-empty" disabled></button><button class="btn-lay lay btn-empty" disabled></button></div>';
    return `<div class="odds-cell-pair">${liveOddsCells(r)}</div>`;
  };

  return `<tr class="match-row live-row ${closed ? 'suspended' : ''}" data-live="${esc(ev.event_id)}">
    <td class="td-event eventInfo">
      <div class="ev-row-top event-title">
        ${ev.in_play ? '<span class="live-dot" title="Live Now"></span>' : ''}
        <span class="ev-title-text"><b>${esc(ev.event_name)}</b></span>
        ${liveBadge}
        <span class="ev-badges float-right d-inline">
          ${ev.has_tv ? '<img src="/static/images/tv.svg" class="meta-icon l-tv" alt="TV">' : ''}
          <img src="/static/images/bm-icon1.svg" class="meta-icon bm1" alt="BM">
          <img src="/static/images/fancy-icon1.svg" class="meta-icon fancy1 mr-1" alt="F">
        </span>
      </div>
      <div class="ev-row-sub">
        <span class="ev-date-sub dtime">${dateStr ? esc(dateStr) : ''}</span>
        ${ev.competition ? ` | <span class="ev-comp-sub">${esc(ev.competition)}</span>` : ''}
        <button class="pin-btn" data-pin="${esc(ev.event_id)}" title="Pin event">${PINNED.has(ev.event_id) ? '★' : '☆'}</button>
      </div>
    </td>
    <td class="td-odds td-odds-1 col-home"><div class="odds">${pair(r1)}</div></td>
    <td class="td-odds td-odds-x col-draw"><div class="odds">${pair(rx)}</div></td>
    <td class="td-odds td-odds-2 col-visit"><div class="odds">${pair(r2)}</div></td>
  </tr>`;
}

"""
    text = text[:idx1] + replacement_middle + text[idx2:]
    print("Deduplicated middle section successfully")

with open('static/app.js', 'w', encoding='utf-8') as f:
    f.write(text)
