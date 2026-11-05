import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('static/app.js', 'r', encoding='utf-8') as f:
    text = f.read()

# Replace renderUserbox
idx_ub_start = text.find('function renderUserbox() {')
idx_ub_end = text.find('/* ---------- auth modal ---------- */')

new_userbox = """function renderUserbox() {
  if (!USER) {
    userbox.innerHTML = `<button id="loginBtn" class="real-login-btn"><svg class="nav-user-svg" viewBox="0 0 24 24" width="14" height="14" fill="currentColor" style="vertical-align:-2px;margin-right:5px;"><path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/></svg>LOG IN</button>`;
    document.getElementById('loginBtn').onclick = () => openAuth('login');
    return;
  }
  userbox.innerHTML = `
    <span class="chip chip-balance user-chip-clickable" id="openRightDrawerBtn" title="Account Menu"><img src="/static/images/coin.svg" class="coin-icon" alt="pts"> <b>${fmt(USER.balance)}</b></span>
    <span class="chip chip-exp user-chip-clickable" id="openRightDrawerExpBtn" title="Account Menu">Exp : <b>${fmt(USER.exposure)}</b></span>
    ${(USER.role === 'admin' || USER.role === 'subadmin') ? `<button id="adminBtn">Admin Panel</button>` : ''}
    <button class="secondary" id="bellBtn" title="Notifications" aria-label="Notifications"><svg class="nav-bell-svg" viewBox="0 0 24 24" width="16" height="16" fill="currentColor" style="vertical-align:-2px;"><path d="M12 22c1.1 0 2-.9 2-2h-4c0 1.1.9 2 2 2zm6-6v-5c0-3.07-1.63-5.64-4.5-6.32V4c0-.83-.67-1.5-1.5-1.5s-1.5.67-1.5 1.5v.68C7.64 5.36 6 7.92 6 11v5l-2 2v1h16v-1l-2-2z"/></svg></button>
    <button class="user-profile-pill" id="userProfileBtn">👤 ${esc(USER.username)}</button>`;

  document.getElementById('bellBtn').onclick = () => location.hash = '#/account/notifications';
  const adminBtn = document.getElementById('adminBtn');
  if (adminBtn) adminBtn.onclick = () => location.hash = '#/admin';

  const openRightDrawer = () => {
    const rd = document.getElementById('rightAccountDrawer');
    const rdb = document.getElementById('rightDrawerBackdrop');
    if (!rd || !rdb) return;
    document.getElementById('rightDrawerUsername').textContent = USER.username;
    document.getElementById('rightDrawerBalance').textContent = fmt(USER.balance);
    document.getElementById('rightDrawerExp').textContent = fmt(USER.exposure);
    document.getElementById('rightDrawerPnl').textContent = fmt(USER.pnl || 0.00);
    rd.classList.remove('hidden');
    rdb.classList.remove('hidden');
  };

  document.getElementById('openRightDrawerBtn').onclick = openRightDrawer;
  document.getElementById('openRightDrawerExpBtn').onclick = openRightDrawer;
  document.getElementById('userProfileBtn').onclick = openRightDrawer;
}

"""

if idx_ub_start != -1 and idx_ub_end != -1 and idx_ub_start < idx_ub_end:
    text = text[:idx_ub_start] + new_userbox + text[idx_ub_end:]
    print("Replaced renderUserbox with right drawer openers")

# Append bindRightDrawerAndModals to end of app.js
drawer_iife = """
/* ---------- right account drawer & modals binding ---------- */
(function bindRightDrawerAndModals() {
  const rd = document.getElementById('rightAccountDrawer');
  const rdb = document.getElementById('rightDrawerBackdrop');
  const close = () => {
    if (rd) rd.classList.add('hidden');
    if (rdb) rdb.classList.add('hidden');
  };
  const closeBtn = document.getElementById('rightDrawerClose');
  if (closeBtn) closeBtn.onclick = close;
  if (rdb) rdb.onclick = close;

  const logoutBtn = document.getElementById('rightDrawerLogout');
  if (logoutBtn) logoutBtn.onclick = async () => {
    close();
    await api('/api/auth/logout', 'POST');
    USER = null;
    renderUserbox();
    route();
  };

  if (rd) rd.querySelectorAll('a').forEach(a => a.addEventListener('click', close));

  // Stake Modal
  const sm = document.getElementById('stakeModal');
  const openStake = document.getElementById('btnOpenSetStake');
  const closeStake = document.getElementById('stakeClose');
  const saveStake = document.getElementById('saveStakeBtn');
  if (openStake && sm) {
    openStake.onclick = (e) => {
      e.preventDefault();
      close();
      sm.classList.remove('hidden');
    };
  }
  if (closeStake && sm) closeStake.onclick = () => sm.classList.add('hidden');
  if (saveStake && sm) {
    saveStake.onclick = () => {
      sm.classList.add('hidden');
      toast('Quick stakes saved successfully');
    };
  }

  // Rules Modal
  const rm = document.getElementById('rulesModal');
  const openRules = document.getElementById('btnOpenRules');
  const closeRules = document.getElementById('rulesClose');
  if (openRules && rm) {
    openRules.onclick = (e) => {
      e.preventDefault();
      close();
      rm.classList.remove('hidden');
    };
  }
  if (closeRules && rm) closeRules.onclick = () => rm.classList.add('hidden');

  // Rules Tabs
  document.querySelectorAll('.rule-tab-btn').forEach(btn => {
    btn.onclick = () => {
      document.querySelectorAll('.rule-tab-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const box = document.getElementById('rulesContentBox');
      const t = btn.dataset.rtab;
      if (t === 'cricket') {
        box.innerHTML = '<p><b>Cricket Rules:</b> If match overs are reduced, Bets in Completed match stand. Innings runs bets valid once innings finishes.</p>';
      } else if (t === 'soccer') {
        box.innerHTML = '<p><b>Soccer Rules:</b> 90 mins regular play plus injury time only. Extra time and penalties do not count towards match odds.</p>';
      } else if (t === 'tennis') {
        box.innerHTML = '<p><b>Tennis Rules:</b> If player retires after at least 1 set completed, opposing player deemed winner.</p>';
      } else if (t === 'bookmaker') {
        box.innerHTML = '<p><b>Bookmaker Rules:</b> Bookmaker bets quote rates where 100 = even money (2.00 decimal odds).</p>';
      } else {
        box.innerHTML = '<p><b>1. Wrong Trade Bets:</b> Only profit bets will be voided in case of obvious error.</p><p><b>2. In-Play Delay:</b> Standard delay applies.</p>';
      }
    };
  });
})();
"""

if 'bindRightDrawerAndModals' not in text:
    text = text + "\n" + drawer_iife
    print("Appended bindRightDrawerAndModals")

with open('static/app.js', 'w', encoding='utf-8') as f:
    f.write(text)

print("Done wire_right_drawer_js.py")
