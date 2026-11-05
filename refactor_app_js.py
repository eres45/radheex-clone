import sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open('static/app.js', 'r', encoding='utf-8') as f:
    code = f.read()

# 1. Update renderUserbox
old_userbox = """function renderUserbox() {
  if (!USER) {
    userbox.innerHTML = `<button id="loginBtn" class="real-login-btn">👤 LOG IN</button>`;
    document.getElementById('loginBtn').onclick = () => openAuth('login');
    return;
  }
  userbox.innerHTML = `
    <span class="chip chip-balance"><img src="/static/images/coin.svg" class="coin-icon" alt="pts"> <b>${fmt(USER.balance)}</b></span>
    <span class="chip chip-exp">Exp : <b>${fmt(USER.exposure)}</b></span>
    ${(USER.role === 'admin' || USER.role === 'subadmin') ? `<button id="adminBtn">🛠 Admin panel</button>` : ''}
    <button class="secondary" id="bellBtn">🔔</button>
    <select id="acctMenu">
      <option value="">${esc(USER.username)} — Account</option>
      <option value="statement">Account Statement</option>
      <option value="pnl">Profit Loss Report</option>
      <option value="history">Bet History</option>
      <option value="unsettled">Unsettled Bets</option>
      <option value="stakes">Set Stake</option>
      <option value="results">Results</option>
      <option value="rules">Rules</option>
      <option value="password">Change Password</option>
    </select>
    <button class="secondary" id="logoutBtn">Logout</button>`;
  document.getElementById('bellBtn').onclick = () => location.hash = '#/account/notifications';
  const adminBtn = document.getElementById('adminBtn');
  if (adminBtn) adminBtn.onclick = () => location.hash = '#/admin';
  document.getElementById('acctMenu').onchange = e => {
    if (e.target.value) location.hash = '#/account/' + e.target.value;
  };
  document.getElementById('logoutBtn').onclick = async () => {
    await api('/api/auth/logout', 'POST'); USER = null; renderUserbox(); route();
  };
}"""

new_userbox = """function renderUserbox() {
  if (!USER) {
    userbox.innerHTML = `<button id="loginBtn" class="real-login-btn"><svg class="nav-user-svg" viewBox="0 0 24 24" width="14" height="14" fill="currentColor" style="vertical-align:-2px;margin-right:5px;"><path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/></svg>LOG IN</button>`;
    document.getElementById('loginBtn').onclick = () => openAuth('login');
    return;
  }
  userbox.innerHTML = `
    <span class="chip chip-balance"><img src="/static/images/coin.svg" class="coin-icon" alt="pts"> <b>${fmt(USER.balance)}</b></span>
    <span class="chip chip-exp">Exp : <b>${fmt(USER.exposure)}</b></span>
    ${(USER.role === 'admin' || USER.role === 'subadmin') ? `<button id="adminBtn">Admin Panel</button>` : ''}
    <button class="secondary" id="bellBtn" title="Notifications" aria-label="Notifications"><svg class="nav-bell-svg" viewBox="0 0 24 24" width="16" height="16" fill="currentColor" style="vertical-align:-2px;"><path d="M12 22c1.1 0 2-.9 2-2h-4c0 1.1.9 2 2 2zm6-6v-5c0-3.07-1.63-5.64-4.5-6.32V4c0-.83-.67-1.5-1.5-1.5s-1.5.67-1.5 1.5v.68C7.64 5.36 6 7.92 6 11v5l-2 2v1h16v-1l-2-2z"/></svg></button>
    <select id="acctMenu">
      <option value="">${esc(USER.username)} — Account</option>
      <option value="statement">Account Statement</option>
      <option value="pnl">Profit Loss Report</option>
      <option value="history">Bet History</option>
      <option value="unsettled">Unsettled Bets</option>
      <option value="stakes">Set Stake</option>
      <option value="results">Results</option>
      <option value="rules">Rules</option>
      <option value="password">Change Password</option>
    </select>
    <button class="secondary" id="logoutBtn">Logout</button>`;
  document.getElementById('bellBtn').onclick = () => location.hash = '#/account/notifications';
  const adminBtn = document.getElementById('adminBtn');
  if (adminBtn) adminBtn.onclick = () => location.hash = '#/admin';
  document.getElementById('acctMenu').onchange = e => {
    if (e.target.value) location.hash = '#/account/' + e.target.value;
  };
  document.getElementById('logoutBtn').onclick = async () => {
    await api('/api/auth/logout', 'POST'); USER = null; renderUserbox(); route();
  };
}"""

if old_userbox in code:
    code = code.replace(old_userbox, new_userbox)
    print("Userbox updated")
else:
    print("Warning: old_userbox not found exactly, will check")

# Save and verify
with open('static/app.js', 'w', encoding='utf-8') as f:
    f.write(code)
