import sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open('static/app.js', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Update bindToggle in liveEventView
old_bind_toggle = """  const bindToggle = (btnId, wrapId, frameId, showLabel, hideLabel) => {
    const btn = document.getElementById(btnId);
    if (!btn) return;
    btn.onclick = () => {
      const w = document.getElementById(wrapId), f = document.getElementById(frameId);
      const show = w.style.display === 'none';
      w.style.display = show ? '' : 'none';
      if (show && f && !f.getAttribute('src')) f.setAttribute('src', f.dataset.src);
      TV_MEDIA_OPEN = show;
      btn.textContent = show ? hideLabel : showLabel;
    };
  };
  bindToggle('tvToggle', 'tvWrap', 'tvFrame', 'Show Live TV', 'Hide Live TV');"""

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
      TV_MEDIA_OPEN = true;
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

if old_bind_toggle in text:
    text = text.replace(old_bind_toggle, new_tv_binding)
    print("Replaced bindToggle with new TV controls")
else:
    print("Warning: old_bind_toggle not found")

# 2. Clean pinned and notice emojis
text = text.replace('<div class="sec-head">★ Pinned</div>', '<div class="sec-head">Pinned Events</div>')
text = text.replace('d.notice ? `📢 <b>${esc(d.notice.text)}</b>`', 'd.notice ? `<span class="announcement-bullet">•</span> <b>${esc(d.notice.text)}</b>`')

# 3. Replace casinoLobby with CASINO_CATALOG & 6-column Visual Lobby
idx_c = text.find('function casinoLobby() {')
idx_s = text.find('const sleep = ms =>')

new_casino_lobby = """const CASINO_CATALOG = [
  // Ezugi
  { id: 'roulette', name: 'Automatic Roulette', provider: 'ezugi', img: '/static/images/ezugi1.webp', tag: 'Live Table' },
  { id: 'andarbahar', name: 'Andar Bahar', provider: 'ezugi', img: '/static/images/ezugi2.webp', tag: 'Live Table' },
  { id: 'roulette', name: 'Namaste Roulette', provider: 'ezugi', img: '/static/images/ezugi3.webp', tag: 'Live Table' },
  { id: 'dragontiger', name: 'Dragon Tiger Live', provider: 'ezugi', img: '/static/images/ezugi4.webp', tag: 'Speed Cards' },
  { id: 'miniroulette', name: 'Speed Auto Roulette', provider: 'ezugi', img: '/static/images/ezugi5.webp', tag: 'Fast Roulette' },
  { id: 'underover', name: 'Lucky 7', provider: 'ezugi', img: '/static/images/ezugi6.webp', tag: 'Hi-Lo Live' },
  { id: 'war', name: 'Cricket War', provider: 'ezugi', img: '/static/images/ezugi7.webp', tag: 'Fast War' },
  { id: 'craps', name: 'Xoc Dia Live', provider: 'ezugi', img: '/static/images/ezugi8.webp', tag: 'Dice Game' },
  { id: 'roulette', name: 'EZ Dealer Roulette', provider: 'ezugi', img: '/static/images/ezugi9.webp', tag: 'Live Dealer' },
  { id: 'bingo', name: 'EZ Bingo 90', provider: 'ezugi', img: '/static/images/ezugi10.webp', tag: 'Live Bingo' },
  { id: 'blackjack', name: 'Blackjack Gold 1', provider: 'ezugi', img: '/static/images/ezugi11.webp', tag: 'VIP Blackjack' },
  { id: 'roulette', name: 'Football Auto Roulette', provider: 'ezugi', img: '/static/images/ezugi12.webp', tag: 'Sports Live' },

  // Evolution
  { id: 'colors', name: 'Crazy Coin Flip', provider: 'evolution', img: '/static/images/evoluation1.webp', tag: 'Live Show' },
  { id: 'roulette', name: 'American Roulette', provider: 'evolution', img: '/static/images/evoluation2.webp', tag: 'Live Dealer' },
  { id: 'andarbahar', name: 'Super Andar Bahar', provider: 'evolution', img: '/static/images/evoluation3.webp', tag: 'Multiplier Live' },
  { id: 'dragontiger', name: 'Dragon Tiger Live', provider: 'evolution', img: '/static/images/evoluation4.webp', tag: 'Speed Cards' },
  { id: 'threecard', name: 'Teen Patti Live', provider: 'evolution', img: '/static/images/evoluation5.webp', tag: 'Indian Cards' },
  { id: 'blackjack', name: 'Blackjack VIP', provider: 'evolution', img: '/static/images/evoluation6.webp', tag: 'VIP Table' },
  { id: 'roulette', name: 'Lightning Roulette', provider: 'evolution', img: '/static/images/evoluation7.webp', tag: '500x Multiplier' },
  { id: 'baccarat', name: 'Salon Prive Baccarat', provider: 'evolution', img: '/static/images/evoluation8.webp', tag: 'VIP Baccarat' },
  { id: 'blackjack', name: 'Diamond VIP Blackjack', provider: 'evolution', img: '/static/images/evoluation9.webp', tag: 'High Stakes' },
  { id: 'baccarat', name: 'Speed Baccarat', provider: 'evolution', img: '/static/images/evoluation10.webp', tag: 'Fast Action' },
  { id: 'caribbean', name: 'Casino Hold\\'em', provider: 'evolution', img: '/static/images/evoluation11.webp', tag: 'Poker Live' },
  { id: 'roulette', name: 'Immersive Roulette', provider: 'evolution', img: '/static/images/evoluation12.webp', tag: 'Multi-Camera' },

  // Vivo Gaming
  { id: 'baccarat', name: 'Vivo Baccarat VIP', provider: 'vivo', img: '/static/images/vivo2.webp', tag: 'VIP Table' },
  { id: 'roulette', name: 'Vivo Roulette Lobby', provider: 'vivo', img: '/static/images/vivo3.webp', tag: 'Live Roulette' },
  { id: 'blackjack', name: 'Vivo Blackjack Live', provider: 'vivo', img: '/static/images/vivo4.webp', tag: 'Live Blackjack' },
  { id: 'roulette', name: 'Portomaso Roulette', provider: 'vivo', img: '/static/images/vivo5.webp', tag: 'Real Casino' },
  { id: 'baccarat', name: 'Sun Macau Baccarat', provider: 'vivo', img: '/static/images/vivo6.webp', tag: 'Asian VIP' },
  { id: 'miniroulette', name: 'Vivo Auto Roulette', provider: 'vivo', img: '/static/images/vivo7.webp', tag: 'Fast Spin' },

  // Betgames
  { id: 'andarbahar', name: 'Betgames Andar Bahar', provider: 'betgames', img: '/static/images/Andar-Bahar.webp', tag: 'Live Cards' },
  { id: 'underover', name: 'Classic Lucky 7', provider: 'betgames', img: '/static/images/Lucky-7.webp', tag: 'Live 7' },
  { id: 'bigsix', name: 'Wheel of Fortune', provider: 'betgames', img: '/static/images/Wheel-Of-Fortune.webp', tag: 'Live Wheel' },
  { id: 'dice', name: 'Dice Duel Live', provider: 'betgames', img: '/static/images/Dice-Duel.webp', tag: 'Red vs Blue' },
  { id: 'videopoker', name: 'Bet on Poker Live', provider: 'betgames', img: '/static/images/Bet-On-Poker.webp', tag: 'Poker Draw' },
  { id: 'reddog', name: 'Speedy 7 Live', provider: 'betgames', img: '/static/images/Speedy-7.webp', tag: '7 Cards' },
  { id: 'war', name: 'War of Bets Live', provider: 'betgames', img: '/static/images/War-Of-Bets.webp', tag: 'Dealer vs Player' },
  { id: 'lottery', name: 'Lucky 5 Live Draw', provider: 'betgames', img: '/static/images/Lucky-5.webp', tag: 'Live Lottery' },

  // In-House Originals
  { id: 'limbo', name: 'Limbo Crash', provider: 'originals', img: '/static/images/topgame1.webp', tag: 'Originals' },
  { id: 'mines', name: 'Mines Treasure', provider: 'originals', img: '/static/images/topgame2.webp', tag: 'Originals' },
  { id: 'plinko', name: 'Plinko Master', provider: 'originals', img: '/static/images/topgame3.webp', tag: 'Originals' },
  { id: 'telefly', name: 'Aviator TeleFly', provider: 'originals', img: '/static/images/topgame4.webp', tag: 'Crash Game' },
  { id: 'keno', name: 'Classic Keno 80', provider: 'originals', img: '/static/images/topgame5.webp', tag: 'Originals' },
  { id: 'dino', name: 'Dino Run Race', provider: 'originals', img: '/static/images/topgame6.webp', tag: 'Originals' },
  { id: 'penalty', name: 'Penalty Shootout', provider: 'originals', img: '/static/images/topgame7.webp', tag: 'Originals' },
  { id: 'tower', name: 'Tower Climber', provider: 'originals', img: '/static/images/topgame8.webp', tag: 'Originals' },
  { id: 'fish', name: 'Fish Hunter Arcade', provider: 'originals', img: '/static/images/topgame9.webp', tag: 'Originals' },
];

function casinoLobby(tab = 'all') {
  tab = (tab || 'all').toLowerCase();
  const filtered = (tab === 'all')
    ? CASINO_CATALOG
    : CASINO_CATALOG.filter(c => c.provider === tab);

  const cardsHtml = filtered.map(c => `
    <div class="casino-game-card" data-casino="${c.id}" title="${esc(c.name)}">
      <img src="${c.img}" alt="${esc(c.name)}" loading="lazy">
      <div class="casino-card-overlay">
        <span class="casino-play-btn">PLAY</span>
      </div>
      <div class="casino-card-footer">
        <span class="casino-card-title">${esc(c.name)}</span>
        <span class="casino-provider-badge badge-${c.provider}">${esc(c.provider.toUpperCase())}</span>
      </div>
    </div>
  `).join('');

  const all38Games = ['limbo', 'plinko', 'keno', 'mines', 'dice', 'telefly', 'cups', 'pvp', 'lottery', 'roulette', 'blackjack', 'slots', 'dino', 'baccarat', 'videopoker', 'threecard', 'caribbean', 'letitride', 'dragontiger', 'war', 'reddog', 'craps', 'sicbo', 'bigsix', 'chuck', 'underover', 'miniroulette', 'andarbahar', 'bingo', 'scratch', 'fish', 'tower', 'cases', 'penalty', 'darts', 'horse', 'colors', 'pick3'];
  const compatTilesHtml = all38Games.map(g => `<div class="tile" data-casino="${g}">${g}</div>`).join('');

  view.innerHTML = `
    <div class="layout">${sidebarHtml('casino')}<div class="content">
      <div class="casino-lobby-wrap">
        <div class="casino-tabs-bar">
          <button type="button" class="casino-tab-btn ${tab === 'all' ? 'active' : ''}" data-tab="all">All</button>
          <button type="button" class="casino-tab-btn ${tab === 'ezugi' ? 'active' : ''}" data-tab="ezugi">Live Casino (Ezugi)</button>
          <button type="button" class="casino-tab-btn ${tab === 'evolution' ? 'active' : ''}" data-tab="evolution">Evolution</button>
          <button type="button" class="casino-tab-btn ${tab === 'vivo' ? 'active' : ''}" data-tab="vivo">Vivo</button>
          <button type="button" class="casino-tab-btn ${tab === 'betgames' ? 'active' : ''}" data-tab="betgames">Betgames</button>
          <button type="button" class="casino-tab-btn ${tab === 'originals' ? 'active' : ''}" data-tab="originals">In-House Originals</button>
        </div>
        <div class="casino-cards-grid">
          ${cardsHtml}
        </div>
        <div style="display:none" class="tiles">${compatTilesHtml}</div>
      </div>
    </div></div>
  `;

  document.querySelectorAll('.casino-tab-btn').forEach(btn => {
    btn.onclick = () => {
      location.hash = '#/casino/' + btn.dataset.tab;
    };
  });
  document.querySelectorAll('.casino-game-card').forEach(card => {
    card.onclick = () => {
      location.hash = '#/casino/' + card.dataset.casino;
    };
  });
  document.querySelectorAll('.tiles [data-casino]').forEach(t => {
    t.onclick = () => { location.hash = '#/casino/' + t.dataset.casino; };
  });
}
"""

if idx_c != -1 and idx_s != -1 and idx_c < idx_s:
    text = text[:idx_c] + new_casino_lobby + "\n" + text[idx_s:]
    print("Replaced casinoLobby with 6-column Visual Grid")

# 4. Clean emojis from casinoGame titles
emoji_titles = {
  '<h2>🚀 Limbo</h2>': '<h2>Limbo</h2>',
  '<h2>🔴 Plinko</h2>': '<h2>Plinko</h2>',
  '<h2>🎱 Keno</h2>': '<h2>Keno</h2>',
  '<h2>💣 Mines</h2>': '<h2>Mines</h2>',
  '<h2>🎲 Dice</h2>': '<h2>Dice</h2>',
  '<h2>✈️ TeleFly</h2>': '<h2>TeleFly — Aviator Style</h2>',
  '<h2>🥤 Lucky Cups</h2>': '<h2>Lucky Cups</h2>',
  '<h2>🎡 PvP Wheel</h2>': '<h2>PvP Wheel</h2>',
  '<h2>🎟️ Lottery 6/49</h2>': '<h2>Lottery 6/49</h2>',
  '<h2>🎡 Roulette</h2>': '<h2>Roulette</h2>',
  '<h2>🃏 Blackjack</h2>': '<h2>Blackjack</h2>',
  '<h2>🎰 Slots</h2>': '<h2>Slots</h2>',
  '<h2>🦖 Dino Run</h2>': '<h2>Dino Run</h2>',
  '<h2>♠️ Baccarat</h2>': '<h2>Baccarat</h2>',
  '<h2>🃏 Video Poker — Jacks or Better</h2>': '<h2>Video Poker — Jacks or Better</h2>',
  '<h2>♣️ Three Card Poker</h2>': '<h2>Three Card Poker</h2>',
  '<h2>🌴 Caribbean Stud</h2>': '<h2>Caribbean Stud</h2>',
  '<h2>🎲 Let It Ride</h2>': '<h2>Let It Ride</h2>',
  '<h2>🐉 Dragon Tiger</h2>': '<h2>Dragon Tiger</h2>',
  '<h2>⚔️ Casino War</h2>': '<h2>Casino War</h2>',
  '<h2>🐕 Red Dog</h2>': '<h2>Red Dog</h2>',
  '<h2>🎲 Craps</h2>': '<h2>Craps</h2>',
  '<h2>🎲 Sic Bo</h2>': '<h2>Sic Bo</h2>',
  '<h2>🎡 Big Six</h2>': '<h2>Big Six</h2>',
  '<h2>🎲 Chuck-a-Luck</h2>': '<h2>Chuck-a-Luck</h2>',
  '<h2>🎲 Under/Over 7</h2>': '<h2>Under/Over 7</h2>',
  '<h2>🎡 Mini Roulette</h2>': '<h2>Mini Roulette</h2>',
  '<h2>🃏 Andar Bahar</h2>': '<h2>Andar Bahar</h2>',
  '<h2>🎱 Bingo</h2>': '<h2>Bingo</h2>',
  '<h2>🎫 Scratch Cards</h2>': '<h2>Scratch Cards</h2>',
  '<h2>🐟 Fish Table</h2>': '<h2>Fish Table</h2>',
  '<h2>🗼 Tower</h2>': '<h2>Tower</h2>',
  '<h2>📦 Cases</h2>': '<h2>Cases</h2>',
  '<h2>⚽ Penalty Shootout</h2>': '<h2>Penalty Shootout</h2>',
  '<h2>🎯 Darts</h2>': '<h2>Darts</h2>',
  '<h2>🏇 Horse Race</h2>': '<h2>Horse Race</h2>',
  '<h2>🎨 Colors</h2>': '<h2>Colors</h2>',
  '<h2>🔢 Pick 3</h2>': '<h2>Pick 3</h2>',
}

for k, v in emoji_titles.items():
    text = text.replace(k, v)

# 5. Update route() handler for casino
old_route = "else if (page === 'casino') { if (arg) await casinoGame(decodeURIComponent(arg)); else casinoLobby(); }"
new_route = """else if (page === 'casino') {
      const validTabs = ['all', 'ezugi', 'evolution', 'vivo', 'betgames', 'originals', 'poker', 'poker2', 'rv', 'casino', 'casino3'];
      if (!arg || validTabs.includes(arg.toLowerCase())) {
        let t = (arg || 'all').toLowerCase();
        if (t === 'poker' || t === 'poker2' || t === 'casino' || t === 'casino3') t = 'ezugi';
        if (t === 'rv') t = 'evolution';
        casinoLobby(t);
      } else {
        await casinoGame(decodeURIComponent(arg));
      }
    }"""

if old_route in text:
    text = text.replace(old_route, new_route)
    print("Updated casino route handler")
else:
    print("Warning: old_route not found")

with open('static/app.js', 'w', encoding='utf-8') as f:
    f.write(text)
print("Finished update_casino_and_route.py")
