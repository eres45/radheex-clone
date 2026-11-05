import sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open('static/app.js', 'r', encoding='utf-8') as f:
    text = f.read()

# Add liveTvComponentHtml definition before liveEventView
tv_component_code = """
function liveTvComponentHtml(ev, tvUrl) {
  const parts = (ev.event_name || '').split(/\\s+v(?:s)?\\.?\\s+/i);
  const team1 = parts[0] || 'Team 1';
  const team2 = parts[1] || 'Team 2';

  let t1Score = '142/3';
  let t2Score = 'Yet to bat';
  let matchStatus = '16.4 ov · CRR 8.52';
  if (ev.sport === 'Soccer') {
    t1Score = '1'; t2Score = '0'; matchStatus = "68' 2nd Half";
  } else if (ev.sport === 'Tennis') {
    t1Score = '6, 4'; t2Score = '4, 3'; matchStatus = 'Set 2 (30-15)';
  }

  return `
    <div class="live-tv-container" id="liveTvContainer">
      <div class="live-tv-header">
        <div class="live-tv-header-title">
          <img src="/static/images/tv.svg" alt="TV">
          <span>Live Match Streaming</span>
          <span class="live-hd-pill">LIVE HD</span>
        </div>
        <div class="live-tv-tabs">
          <button type="button" class="tv-mode-btn active" id="btnTvRadar">Pitch Tracker</button>
          <button type="button" class="tv-mode-btn" id="btnTvStream">Live Video</button>
          <button type="button" class="tv-control-btn" id="btnTvToggle" title="Toggle TV View">▼</button>
        </div>
      </div>
      <div id="tvBody" class="tv-viewport">
        <div class="tv-score-hud">
          <div class="tv-team-score"><span class="team-name">${esc(team1)}</span> <b>${t1Score}</b></div>
          <div class="tv-match-status"><span class="badge-status">In-Play</span> <span class="match-meta">${matchStatus}</span></div>
          <div class="tv-team-score" style="text-align:right"><span class="team-name">${esc(team2)}</span> <b>${t2Score}</b></div>
        </div>
        <div id="tvViewRadar" class="tv-simulated-pitch">
          <div class="radar-hud-info">
            <div class="radar-line"><b>Batsman:</b> Striker on Strike (38* off 24)</div>
            <div class="radar-line"><b>Bowler:</b> Fast Medium (2.4-0-18-1)</div>
            <div class="radar-line"><b>CRR:</b> 8.45 · <b>RRR:</b> 9.20</div>
          </div>
          <div class="pitch-visual-field">
            <div class="pitch-strip">
              <span class="stump-marker top"></span>
              <span class="ball-trajectory"></span>
              <span class="stump-marker bottom"></span>
            </div>
            <div class="field-zone-ring"></div>
          </div>
        </div>
        <div id="tvViewStream" style="display:none;">
          ${tvUrl
            ? `<iframe id="tvFrame" src="${esc(tvUrl)}" style="width:100%;height:320px;border:0" allowfullscreen></iframe>`
            : `<div class="tv-broadcast-placeholder">
                <div class="tv-broadcast-overlay">
                  <span class="live-hd-pill">LIVE HD</span>
                  <span class="tv-broadcast-meta">RadheEx Satellite Feed 1 (1080p60)</span>
                </div>
                <img src="/static/images/tv.svg" alt="TV">
                <div style="font-weight:700;font-size:15px;margin-bottom:4px;">Official Match Broadcast Active</div>
                <div class="tv-bitrate">Enc: H.265 · Latency: 0.3s · Audio: Direct Stereo</div>
              </div>`
          }
        </div>
        <div class="tv-controls-bar">
          <span>Channel: Super Sports HD 1 · 1080p60</span>
          <div class="tv-controls-right">
            <button type="button" class="tv-control-btn" id="btnTvMute">Audio: ON</button>
            <button type="button" class="tv-control-btn" id="btnTvFullscreen">Fullscreen</button>
          </div>
        </div>
      </div>
    </div>
  `;
}
"""

if 'function liveTvComponentHtml' not in text:
    target_str = 'async function liveEventView(eventId, keepSlip) {'
    text = text.replace(target_str, tv_component_code + "\n" + target_str)
    print("Inserted liveTvComponentHtml")

# Update liveEventView TV and announcements rendering
old_msg_tv = """  const msgHtml = (ev.messages && ev.messages.length) ? `<div class="card"><div class="sec-head">📢 Announcements</div>
    ${ev.messages.map(m => `<p>📢 ${esc(m.message)}</p>`).join('')}</div>` : '';
  // No "open in a new tab" link: the widget redirects top-level navigation
  // to Google (verified in a real browser) — it only loads embedded.
  const tvHtml = tvUrl ? `<div class="card" id="tvCard"><div class="sec-head">📺 Live TV</div>
    <div id="tvWrap" style="display:none"><iframe id="tvFrame" data-src="${esc(tvUrl)}" style="width:100%;height:420px;border:0" allowfullscreen></iframe>
    <p class="muted">Odds refresh pauses while Live TV is open. The player only loads embedded on this page.</p></div>
    <button class="secondary" id="tvToggle">Show Live TV</button></div>` : '';"""

new_msg_tv = """  const msgHtml = (ev.messages && ev.messages.length) ? `<div class="card"><div class="sec-head">Announcements</div>
    ${ev.messages.map(m => `<p><span class="announcement-bullet">•</span> ${esc(m.message)}</p>`).join('')}</div>` : '';
  const tvHtml = liveTvComponentHtml(ev, tvUrl);"""

if old_msg_tv in text:
    text = text.replace(old_msg_tv, new_msg_tv)
    print("Replaced msgHtml and tvHtml in liveEventView")

# Clean emojis in marketTable and bottom ticker
text = text.replace('<span>📌 ${esc(mk.market_name)}</span>', '<span>${esc(mk.market_name)}</span>')
text = text.replace('<div class="market-trade-warning">🚩 WRONG TRADE BETS ONLY PROFIT BETS VOID HOGI</div>',
                    '<div class="market-trade-warning"><span class="badge-warning">!</span> WRONG TRADE BETS ONLY PROFIT BETS VOID HOGI</div>')
text = text.replace('<p class="live-note">📡 Live delayed feed — delayed guest data, not real-time.</p>',
                    '<p class="live-note"><span class="live-dot-mini"></span> Live delayed feed — delayed guest data, not real-time.</p>')
text = text.replace('<span>WBBL 2026 ..Winner Cup Bets Started In Our Exchange.......✨✨✨</span>',
                    '<span>WBBL 2026 ..Winner Cup Bets Started In Our Exchange</span>')
text = text.replace('<span>📢 1 Welcome To Our Exchange ..... ✨✨ 2</span>',
                    '<span>1 Welcome To Our Exchange 2</span>')

# Add TV event bindings inside liveEventView
old_tv_binding = """  const tvToggle = document.getElementById('tvToggle');
  const tvWrap = document.getElementById('tvWrap');
  const tvFrame = document.getElementById('tvFrame');
  if (tvToggle && tvWrap && tvFrame) {
    tvToggle.onclick = () => {
      const open = tvWrap.style.display !== 'none';
      if (open) {
        tvFrame.removeAttribute('src');
        tvWrap.style.display = 'none';
        tvToggle.textContent = 'Show Live TV';
        TV_MEDIA_OPEN = false;
      } else {
        tvFrame.src = tvFrame.dataset.src;
        tvWrap.style.display = '';
        tvToggle.textContent = 'Hide Live TV';
        TV_MEDIA_OPEN = true;
      }
    };
  }"""

new_tv_binding = """  const btnRadar = document.getElementById('btnTvRadar');
  const btnStream = document.getElementById('btnTvStream');
  const vRadar = document.getElementById('tvViewRadar');
  const vStream = document.getElementById('tvViewStream');
  const btnToggle = document.getElementById('btnTvToggle');
  const tvBody = document.getElementById('tvBody');
  const btnMute = document.getElementById('btnTvMute');
  const btnFs = document.getElementById('btnTvFullscreen');

  if (btnRadar && btnStream) {
    btnRadar.onclick = () => {
      btnRadar.classList.add('active');
      btnStream.classList.remove('active');
      if (vRadar) vRadar.style.display = '';
      if (vStream) vStream.style.display = 'none';
    };
    btnStream.onclick = () => {
      btnStream.classList.add('active');
      btnRadar.classList.remove('active');
      if (vRadar) vRadar.style.display = 'none';
      if (vStream) vStream.style.display = '';
    };
  }
  if (btnToggle && tvBody) {
    btnToggle.onclick = () => {
      const isHidden = tvBody.style.display === 'none';
      tvBody.style.display = isHidden ? '' : 'none';
      btnToggle.textContent = isHidden ? '▼' : '▲';
    };
  }
  if (btnMute) {
    btnMute.onclick = () => {
      btnMute.textContent = btnMute.textContent.includes('ON') ? 'Audio: Muted' : 'Audio: ON';
    };
  }
  if (btnFs) {
    btnFs.onclick = () => {
      const container = document.getElementById('liveTvContainer');
      if (container) {
        if (!document.fullscreenElement) container.requestFullscreen().catch(() => {});
        else document.exitFullscreen().catch(() => {});
      }
    };
  }"""

if old_tv_binding in text:
    text = text.replace(old_tv_binding, new_tv_binding)
    print("Updated TV event bindings")
else:
    print("Warning: old_tv_binding not found exactly")

with open('static/app.js', 'w', encoding='utf-8') as f:
    f.write(text)
print("Updated liveEventView and TV player")
