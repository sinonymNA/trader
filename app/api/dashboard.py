from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["dashboard"])

_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>OANDA Apex Bot</title>
<style>
  :root {
    --bg: #0d1117;
    --surface: #161b22;
    --border: #30363d;
    --text: #e6edf3;
    --muted: #8b949e;
    --green: #00d26a;
    --yellow: #d29922;
    --red: #ff4757;
    --blue: #58a6ff;
    --purple: #bc8cff;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: var(--bg); color: var(--text); font-family: 'Segoe UI', system-ui, sans-serif; font-size: 14px; }
  header { background: var(--surface); border-bottom: 1px solid var(--border); padding: 16px 24px; display: flex; align-items: center; gap: 16px; }
  header h1 { font-size: 20px; font-weight: 700; color: var(--green); letter-spacing: -0.5px; }
  header .subtitle { color: var(--muted); font-size: 12px; }
  .badge { display: inline-flex; align-items: center; gap: 5px; padding: 3px 10px; border-radius: 12px; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }
  .badge.running { background: rgba(0, 210, 106, 0.15); color: var(--green); }
  .badge.paused  { background: rgba(210, 153, 34, 0.15); color: var(--yellow); }
  .badge.stopped { background: rgba(255, 71, 87, 0.15); color: var(--red); }
  .badge.open    { background: rgba(0, 210, 106, 0.15); color: var(--green); }
  .badge.closed  { background: rgba(139, 148, 158, 0.15); color: var(--muted); }
  .badge.buy     { background: rgba(0, 210, 106, 0.15); color: var(--green); }
  .badge.sell    { background: rgba(255, 71, 87, 0.15); color: var(--red); }
  .dot { width: 7px; height: 7px; border-radius: 50%; background: currentColor; }
  main { padding: 24px; max-width: 1280px; margin: 0 auto; }
  .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-bottom: 24px; }
  .card { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 16px; }
  .card-title { color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 8px; }
  .card-value { font-size: 26px; font-weight: 700; color: var(--text); }
  .card-value.green { color: var(--green); }
  .card-value.red   { color: var(--red); }
  .card-sub { color: var(--muted); font-size: 11px; margin-top: 4px; }
  .section-title { font-size: 13px; font-weight: 600; color: var(--muted); text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 12px; }
  .panel { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 16px; margin-bottom: 24px; }
  .controls { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 24px; }
  button { padding: 8px 20px; border: none; border-radius: 6px; font-size: 13px; font-weight: 600; cursor: pointer; transition: opacity 0.15s; }
  button:hover { opacity: 0.85; }
  button:active { opacity: 0.7; }
  .btn-pause  { background: var(--yellow); color: #000; }
  .btn-resume { background: var(--green);  color: #000; }
  .btn-flatten{ background: var(--red);    color: #fff; }
  .btn-toggle { background: var(--blue);   color: #000; }
  .btn-sm { padding: 5px 12px; font-size: 11px; }
  table { width: 100%; border-collapse: collapse; }
  th { text-align: left; padding: 8px 12px; font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid var(--border); }
  td { padding: 10px 12px; border-bottom: 1px solid rgba(48, 54, 61, 0.5); font-size: 13px; }
  tr:last-child td { border-bottom: none; }
  tr:hover td { background: rgba(255,255,255,0.02); }
  .pnl-pos { color: var(--green); }
  .pnl-neg { color: var(--red); }
  .timestamp { color: var(--muted); font-size: 11px; }
  .status-bar { display: flex; align-items: center; gap: 16px; padding: 8px 24px; background: var(--surface); border-top: 1px solid var(--border); position: fixed; bottom: 0; left: 0; right: 0; font-size: 11px; color: var(--muted); }
  .apex-panel { border-color: var(--purple); }
  .apex-panel .card-value { color: var(--purple); }
  #toast { position: fixed; top: 20px; right: 20px; padding: 10px 20px; border-radius: 6px; font-size: 13px; font-weight: 600; display: none; z-index: 100; }
  #toast.success { background: var(--green); color: #000; }
  #toast.error   { background: var(--red);   color: #fff; }
  .signal-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 12px; }
  .signal-card { background: var(--bg); border: 1px solid var(--border); border-radius: 6px; padding: 12px; }
  .signal-card .instr { font-size: 15px; font-weight: 700; margin-bottom: 8px; }
  .signal-row { display: flex; justify-content: space-between; font-size: 12px; padding: 3px 0; border-bottom: 1px solid rgba(48,54,61,0.4); }
  .signal-row:last-child { border-bottom: none; }
  .signal-row .label { color: var(--muted); }
  .signal-row .val { font-family: monospace; }
  .hold-reason { font-size: 11px; color: var(--yellow); margin-top: 6px; font-style: italic; }
  .btn-export { background: var(--surface); color: var(--muted); border: 1px solid var(--border); }
  .btn-export:hover { color: var(--text); }
</style>
</head>
<body>
<header>
  <div>
    <h1>⚡ OANDA Apex Bot</h1>
    <div class="subtitle">Autonomous Forex Practice Bot</div>
  </div>
  <div style="margin-left:auto; display:flex; gap:10px; align-items:center;">
    <span id="market-badge" class="badge">–</span>
    <span id="worker-badge" class="badge">–</span>
    <span id="dry-run-badge" class="badge" style="background:rgba(88,166,255,0.15);color:var(--blue)">DRY RUN</span>
  </div>
</header>

<main>
  <!-- Summary cards -->
  <div class="grid" id="summary-cards">
    <div class="card">
      <div class="card-title">Uptime</div>
      <div class="card-value" id="uptime">–</div>
    </div>
    <div class="card">
      <div class="card-title">Trades Today</div>
      <div class="card-value" id="trades-today">–</div>
      <div class="card-sub" id="losses-today">–</div>
    </div>
    <div class="card">
      <div class="card-title">Current Instrument</div>
      <div class="card-value" id="current-instrument" style="font-size:18px">–</div>
    </div>
    <div class="card">
      <div class="card-title">Last Signal</div>
      <div class="card-value" id="last-signal" style="font-size:18px">–</div>
    </div>
  </div>

  <!-- Apex panel (hidden unless apex_enabled) -->
  <div id="apex-panel" class="panel apex-panel" style="display:none; margin-bottom:24px;">
    <div class="section-title">Apex Challenge Status</div>
    <div class="grid" style="margin-bottom:0">
      <div class="card" style="border:none;padding:0">
        <div class="card-title">Realized PnL</div>
        <div class="card-value" id="apex-pnl">–</div>
      </div>
      <div class="card" style="border:none;padding:0">
        <div class="card-title">Daily PnL</div>
        <div class="card-value" id="apex-daily-pnl">–</div>
      </div>
      <div class="card" style="border:none;padding:0">
        <div class="card-title">Current Balance</div>
        <div class="card-value" id="apex-balance">–</div>
      </div>
      <div class="card" style="border:none;padding:0">
        <div class="card-title">Peak Balance</div>
        <div class="card-value" id="apex-peak">–</div>
      </div>
      <div class="card" style="border:none;padding:0">
        <div class="card-title">Rule Status</div>
        <div class="card-value" id="apex-status" style="font-size:14px">–</div>
      </div>
    </div>
  </div>

  <!-- Controls -->
  <div class="controls">
    <button class="btn-pause" onclick="sendControl('pause')">⏸ Pause</button>
    <button class="btn-resume" onclick="sendControl('resume')">▶ Resume</button>
    <button class="btn-toggle" onclick="sendControl('toggle-trading')">⚡ Toggle Trading</button>
    <button class="btn-flatten" onclick="confirmFlatten()">🔥 Flatten All</button>
    <button class="btn-export" onclick="copyExport()">📋 Copy Export</button>
  </div>

  <!-- Signal Analysis -->
  <div class="panel" style="margin-bottom:24px">
    <div class="section-title" style="margin-bottom:12px">Signal Analysis — Why HOLD?</div>
    <div class="signal-grid" id="signal-grid">
      <div style="color:var(--muted);font-size:13px">Waiting for first tick…</div>
    </div>
  </div>

  <!-- Trades table -->
  <div class="panel">
    <div class="section-title">Recent Trades</div>
    <table>
      <thead>
        <tr>
          <th>Instrument</th>
          <th>Side</th>
          <th>Units</th>
          <th>Open Price</th>
          <th>Close Price</th>
          <th>PnL</th>
          <th>Status</th>
          <th>Opened</th>
        </tr>
      </thead>
      <tbody id="trades-body">
        <tr><td colspan="8" style="color:var(--muted);text-align:center;padding:24px">Loading…</td></tr>
      </tbody>
    </table>
  </div>
</main>

<div class="status-bar">
  <span id="last-tick">Last tick: –</span>
  <span>•</span>
  <span id="refresh-status">Refreshing every 5s</span>
  <span>•</span>
  <span id="trading-enabled-status">Trading: –</span>
</div>

<div id="toast"></div>

<script>
const fmt = {
  price: v => v != null ? parseFloat(v).toFixed(5) : '–',
  pnl:   v => v != null ? (parseFloat(v) >= 0 ? '+' : '') + parseFloat(v).toFixed(2) : '–',
  uptime: s => {
    s = Math.round(s);
    const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), sec = s % 60;
    return [h,m,sec].map(x => String(x).padStart(2,'0')).join(':');
  },
  dt: s => s ? new Date(s).toLocaleTimeString() : '–',
};

function toast(msg, type='success') {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.className = type;
  el.style.display = 'block';
  setTimeout(() => el.style.display = 'none', 2500);
}

async function sendControl(action) {
  try {
    const r = await fetch('/control/' + action, {method:'POST'});
    const d = await r.json();
    toast(d.message || action + ' OK');
    refresh();
  } catch(e) { toast('Error: ' + e.message, 'error'); }
}

async function confirmFlatten() {
  if (!confirm('Close ALL open trades? This cannot be undone.')) return;
  try {
    const r = await fetch('/control/flatten', {method:'POST'});
    const d = await r.json();
    toast('Flattened ' + d.closed_count + ' trade(s)');
    refreshTrades();
  } catch(e) { toast('Flatten failed: ' + e.message, 'error'); }
}

async function refreshState() {
  try {
    const d = await (await fetch('/state')).json();
    // Worker badge
    const wb = document.getElementById('worker-badge');
    wb.textContent = d.worker_status;
    wb.className = 'badge ' + d.worker_status.toLowerCase();

    // Market badge
    const mb = document.getElementById('market-badge');
    mb.textContent = d.market_open ? '● MARKET OPEN' : '○ MARKET CLOSED';
    mb.className = 'badge ' + (d.market_open ? 'open' : 'closed');

    // Dry-run badge
    document.getElementById('dry-run-badge').style.display = d.dry_run ? '' : 'none';

    // Cards
    document.getElementById('uptime').textContent = fmt.uptime(d.uptime_seconds);
    document.getElementById('trades-today').textContent = d.trades_today ?? '–';
    document.getElementById('losses-today').textContent = 'Losses: ' + (d.losses_today ?? '–');
    document.getElementById('current-instrument').textContent = d.current_instrument ?? '–';

    const ls = document.getElementById('last-signal');
    ls.textContent = d.last_signal ?? '–';
    ls.className = 'card-value ' + (d.last_signal === 'BUY' ? 'green' : d.last_signal === 'SELL' ? 'red' : '');

    // Apex panel
    if (d.apex_state) {
      document.getElementById('apex-panel').style.display = '';
      const a = d.apex_state;
      const setPnl = (id, v) => {
        const el = document.getElementById(id);
        el.textContent = fmt.pnl(v);
        el.className = 'card-value ' + (v >= 0 ? 'green' : 'red');
      };
      setPnl('apex-pnl', a.realized_pnl);
      setPnl('apex-daily-pnl', a.daily_pnl);
      document.getElementById('apex-balance').textContent = '$' + parseFloat(a.current_balance).toLocaleString('en-US', {minimumFractionDigits:2});
      document.getElementById('apex-peak').textContent = '$' + parseFloat(a.peak_balance).toLocaleString('en-US', {minimumFractionDigits:2});
      const ss = document.getElementById('apex-status');
      ss.textContent = a.can_trade ? '✓ ' + a.rule_status : '✗ ' + a.rule_status;
      ss.style.color = a.can_trade ? 'var(--green)' : 'var(--red)';
    }

    // Status bar
    document.getElementById('last-tick').textContent = 'Last tick: ' + fmt.dt(d.last_tick_at);
    document.getElementById('trading-enabled-status').textContent = 'Trading: ' + (d.trading_enabled ? '✓ ON' : '✗ OFF');
  } catch(e) { console.error('State refresh error', e); }
}

async function refreshTrades() {
  try {
    const d = await (await fetch('/trades')).json();
    const tbody = document.getElementById('trades-body');
    if (!d.trades || d.trades.length === 0) {
      tbody.innerHTML = '<tr><td colspan="8" style="color:var(--muted);text-align:center;padding:24px">No trades yet</td></tr>';
      return;
    }
    tbody.innerHTML = d.trades.map(t => {
      const pnl = t.realized_pnl;
      const pnlCls = pnl != null ? (pnl >= 0 ? 'pnl-pos' : 'pnl-neg') : '';
      return '<tr>' +
        '<td><strong>' + t.instrument + '</strong></td>' +
        '<td><span class="badge ' + t.side.toLowerCase() + '">' + t.side + '</span></td>' +
        '<td>' + t.units + '</td>' +
        '<td class="timestamp">' + fmt.price(t.open_price) + '</td>' +
        '<td class="timestamp">' + (t.close_price ? fmt.price(t.close_price) : '–') + '</td>' +
        '<td class="' + pnlCls + '">' + (pnl != null ? fmt.pnl(pnl) : '–') + '</td>' +
        '<td><span class="badge ' + t.status.toLowerCase() + '">' + t.status + '</span></td>' +
        '<td class="timestamp">' + fmt.dt(t.opened_at) + '</td>' +
        '</tr>';
    }).join('');
  } catch(e) { console.error('Trades refresh error', e); }
}

async function refreshDebug() {
  try {
    const d = await (await fetch('/debug')).json();
    const grid = document.getElementById('signal-grid');
    const snaps = d.signal_snapshots || {};
    const instruments = Object.keys(snaps);
    if (instruments.length === 0) {
      grid.innerHTML = '<div style="color:var(--muted);font-size:13px">Waiting for first tick…</div>';
      return;
    }
    grid.innerHTML = instruments.map(inst => {
      const s = snaps[inst];
      const sigColor = s.signal === 'BUY' ? 'var(--green)' : s.signal === 'SELL' ? 'var(--red)' : 'var(--muted)';
      const maColor = s.short_ma != null && s.long_ma != null
        ? (s.short_ma > s.long_ma ? 'var(--green)' : s.short_ma < s.long_ma ? 'var(--red)' : 'var(--muted)')
        : 'var(--muted)';
      const maArrow = s.short_ma != null && s.long_ma != null
        ? (s.short_ma > s.long_ma ? ' ↑' : s.short_ma < s.long_ma ? ' ↓' : ' =')
        : '';
      const p = v => v != null ? parseFloat(v).toFixed(5) : '–';
      return '<div class="signal-card">' +
        '<div class="instr">' + inst + ' <span style="float:right;font-size:13px;color:' + sigColor + '">' + (s.signal || '–') + '</span></div>' +
        '<div class="signal-row"><span class="label">Mid Price</span><span class="val">' + p(s.mid_price) + '</span></div>' +
        '<div class="signal-row"><span class="label">Spread</span><span class="val">' + (s.spread != null ? parseFloat(s.spread).toFixed(5) : '–') + '</span></div>' +
        '<div class="signal-row"><span class="label">Short MA</span><span class="val" style="color:' + maColor + '">' + p(s.short_ma) + maArrow + '</span></div>' +
        '<div class="signal-row"><span class="label">Long MA</span><span class="val">' + p(s.long_ma) + '</span></div>' +
        '<div class="signal-row"><span class="label">Breakout High</span><span class="val">' + p(s.breakout_high) + '</span></div>' +
        '<div class="signal-row"><span class="label">Breakout Low</span><span class="val">' + p(s.breakout_low) + '</span></div>' +
        '<div class="signal-row"><span class="label">Candles</span><span class="val">' + (s.candle_count ?? '–') + (s.stale ? ' ⚠ stale' : '') + '</span></div>' +
        (s.hold_reason ? '<div class="hold-reason">⚠ ' + s.hold_reason + '</div>' : '') +
        '</div>';
    }).join('');
  } catch(e) { console.error('Debug refresh error', e); }
}

async function copyExport() {
  try {
    const d = await (await fetch('/export')).json();
    await navigator.clipboard.writeText(JSON.stringify(d, null, 2));
    toast('Copied export JSON to clipboard!');
  } catch(e) { toast('Copy failed: ' + e.message, 'error'); }
}

function refresh() { refreshState(); refreshTrades(); refreshDebug(); }

refresh();
setInterval(refresh, 5000);
</script>
</body>
</html>
"""


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard() -> str:
    return _HTML
