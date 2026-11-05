import sys
sys.stdout.reconfigure(encoding='utf-8')

# 1. Update templates/index.html
with open('templates/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

drawer_markup = """
  <!-- Right Account Menu Drawer (matching live radheex.com #RightMenu) -->
  <div class="right-drawer-backdrop hidden" id="rightDrawerBackdrop"></div>
  <aside class="right-account-drawer hidden" id="rightAccountDrawer" aria-label="Account Menu">
    <div class="right-drawer-header">
      <div class="right-drawer-user-title">
        <svg viewBox="0 0 24 24" width="16" height="16" fill="#ffc107"><path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/></svg>
        <span id="rightDrawerUsername">Demo</span> - (<span id="rightDrawerBalance">2000.00</span>)
      </div>
      <button class="right-drawer-close" id="rightDrawerClose" type="button" aria-label="Close">&times;</button>
    </div>
    <div class="right-drawer-stats">
      <div class="stat-box">
        <div class="stat-lbl">Exposure</div>
        <div class="stat-val" id="rightDrawerExp">0.00</div>
      </div>
      <div class="stat-box">
        <div class="stat-lbl">P&amp;L</div>
        <div class="stat-val" id="rightDrawerPnl">0.00</div>
      </div>
    </div>
    <div class="right-drawer-links">
      <a href="#/account/statement" class="right-menu-item">
        <span class="rm-ic">📄</span>
        <span>Account Statement</span>
      </a>
      <a href="#/account/pnl" class="right-menu-item">
        <span class="rm-ic">📊</span>
        <span>Profit Loss Report</span>
      </a>
      <a href="#/account/history" class="right-menu-item">
        <span class="rm-ic">📜</span>
        <span>Bet History</span>
      </a>
      <a href="#/account/unsettled" class="right-menu-item">
        <span class="rm-ic">⏳</span>
        <span>Unsettled Bet</span>
      </a>
      <button type="button" class="right-menu-item" id="btnOpenSetStake">
        <span class="rm-ic">⚙️</span>
        <span>Set Stake</span>
      </button>
      <button type="button" class="right-menu-item" id="btnOpenRules">
        <span class="rm-ic">📋</span>
        <span>Rules</span>
      </button>
      <a href="#/account/password" class="right-menu-item">
        <span class="rm-ic">🔒</span>
        <span>Change Password</span>
      </a>
      <button type="button" class="right-menu-item btn-drawer-logout" id="rightDrawerLogout">
        <span class="rm-ic">➔</span>
        <span>Logout</span>
      </button>
    </div>
  </aside>

  <!-- Stake Settings Modal -->
  <div class="modal hidden" id="stakeModal">
    <div class="modal-card">
      <div class="modal-header-teal">
        <h3 class="modal-title-main">Stake Setting</h3>
        <button class="modal-x" id="stakeClose" type="button">&times;</button>
      </div>
      <div class="stake-modal-body">
        <div class="stake-inputs-grid" id="stakeInputsGrid">
          <label>Stake 1 <input type="number" class="field-inp stake-val" value="100"></label>
          <label>Stake 2 <input type="number" class="field-inp stake-val" value="500"></label>
          <label>Stake 3 <input type="number" class="field-inp stake-val" value="1000"></label>
          <label>Stake 4 <input type="number" class="field-inp stake-val" value="2000"></label>
          <label>Stake 5 <input type="number" class="field-inp stake-val" value="5000"></label>
          <label>Stake 6 <input type="number" class="field-inp stake-val" value="10000"></label>
          <label>Stake 7 <input type="number" class="field-inp stake-val" value="25000"></label>
          <label>Stake 8 <input type="number" class="field-inp stake-val" value="50000"></label>
        </div>
        <button type="button" class="btn-login-teal" id="saveStakeBtn" style="margin-top:14px;">Save Stakes</button>
      </div>
    </div>
  </div>

  <!-- Exchange Rules Modal -->
  <div class="modal hidden" id="rulesModal">
    <div class="modal-card modal-large">
      <div class="modal-header-teal">
        <h3 class="modal-title-main">Exchange Rules</h3>
        <button class="modal-x" id="rulesClose" type="button">&times;</button>
      </div>
      <div class="rules-modal-body">
        <div class="rules-tabs">
          <button type="button" class="rule-tab-btn active" data-rtab="general">General</button>
          <button type="button" class="rule-tab-btn" data-rtab="cricket">Cricket</button>
          <button type="button" class="rule-tab-btn" data-rtab="soccer">Soccer</button>
          <button type="button" class="rule-tab-btn" data-rtab="tennis">Tennis</button>
          <button type="button" class="rule-tab-btn" data-rtab="bookmaker">Bookmaker</button>
        </div>
        <div class="rules-content" id="rulesContentBox">
          <p><b>1. Wrong Trade Bets:</b> Only profit bets will be voided in case of obvious error.</p>
          <p><b>2. In-Play Delay:</b> Standard bet placement delay applies (0.5s - 5s) during live events.</p>
          <p><b>3. Abandoned / Postponed:</b> If a match is abandoned, uncompleted bets are settled void (payout = stake returned) per exchange standards.</p>
          <p><b>4. Dead Heat:</b> In case of dead heat, stakes are split equally among winning selections.</p>
        </div>
      </div>
    </div>
  </div>
"""

if 'id="rightAccountDrawer"' not in html:
    insert_pos = html.find('<div id="toast"></div>')
    html = html[:insert_pos] + drawer_markup + "\n" + html[insert_pos:]
    with open('templates/index.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("Added right drawer and modals to templates/index.html")

# 2. Update static/style.css
with open('static/style.css', 'r', encoding='utf-8') as f:
    css = f.read()

css_drawer = """
/* Right Account Drawer (RadheEx Parity) */
.right-drawer-backdrop {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  z-index: 1040;
}
.right-account-drawer {
  position: fixed;
  top: 0; right: 0; bottom: 0;
  width: 280px;
  max-width: 85vw;
  background: #054d5d;
  color: #fff;
  z-index: 1050;
  display: flex;
  flex-direction: column;
  box-shadow: -4px 0 20px rgba(0, 0, 0, 0.4);
  transition: transform 0.3s ease;
}
.right-account-drawer.hidden {
  transform: translateX(100%);
  display: block !important;
  pointer-events: none;
}
.right-drawer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 16px;
  background: #043d4a;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}
.right-drawer-user-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 700;
  font-size: 14px;
  color: #ffc107;
}
.right-drawer-close {
  background: none;
  border: none;
  color: #fff;
  font-size: 22px;
  cursor: pointer;
  line-height: 1;
}
.right-drawer-stats {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  padding: 12px 16px;
}
.stat-box {
  background: #17a2b8;
  color: #fff;
  padding: 8px 10px;
  border-radius: 4px;
}
.stat-lbl {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
}
.stat-val {
  font-size: 14px;
  font-weight: 800;
  margin-top: 2px;
}
.right-drawer-links {
  display: flex;
  flex-direction: column;
  padding: 8px 0;
  overflow-y: auto;
  flex: 1;
}
.right-menu-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 18px;
  color: #fff;
  text-decoration: none;
  font-size: 13px;
  font-weight: 600;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  background: none;
  border-top: none;
  border-left: none;
  border-right: none;
  width: 100%;
  text-align: left;
  cursor: pointer;
  transition: background 0.15s;
}
.right-menu-item:hover {
  background: rgba(255, 255, 255, 0.1);
  color: #20b8cd;
}
.btn-drawer-logout {
  color: #ff6b6b;
  margin-top: auto;
}
.btn-drawer-logout:hover {
  background: rgba(255, 107, 107, 0.15);
  color: #ff4757;
}
.user-chip-clickable {
  cursor: pointer;
  transition: opacity 0.2s;
}
.user-chip-clickable:hover {
  opacity: 0.85;
}
.user-profile-pill {
  background: #17a2b8;
  color: #fff;
  border: none;
  border-radius: 4px;
  padding: 6px 12px;
  font-weight: 700;
  font-size: 13px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 5px;
}
.user-profile-pill:hover {
  background: #138496;
}

/* Stake & Rules Modal */
.modal-large {
  max-width: 650px;
}
.stake-modal-body, .rules-modal-body {
  padding: 16px 20px;
}
.stake-inputs-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.stake-inputs-grid label {
  font-size: 12px;
  font-weight: 700;
  color: #555;
}
.rules-tabs {
  display: flex;
  gap: 6px;
  margin-bottom: 14px;
  border-bottom: 1px solid #dee2e6;
  padding-bottom: 8px;
}
.rule-tab-btn {
  background: #e9ecef;
  border: none;
  padding: 6px 12px;
  border-radius: 4px;
  font-weight: 600;
  font-size: 12px;
  cursor: pointer;
}
.rule-tab-btn.active {
  background: #17a2b8;
  color: #fff;
}
.rules-content {
  font-size: 13px;
  line-height: 1.6;
  color: #333;
  max-height: 300px;
  overflow-y: auto;
}
"""

if '.right-account-drawer' not in css:
    with open('static/style.css', 'a', encoding='utf-8') as f:
        f.write(css_drawer)
    print("Added right drawer and modal CSS to static/style.css")

print("Done add_right_drawer_and_modals.py")
