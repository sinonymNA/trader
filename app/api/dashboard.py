from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["dashboard"])

_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
<title>OANDA Apex Bot</title>
<style>
  :root {
    --bg: #0d1117;
    --surface: #161b22;
    --surface2: #1c2128;
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
  html { -webkit-text-size-adjust: 100%; }
  body { background: var(--bg); color: var(--text); font-family: -apple-system, 'Segoe UI', system-ui, sans-serif; font-size: 14px; padding-bottom: 52px; }

  /* ── Header ── */
  header { background: var(--surface); border-bottom: 1px solid var(--border); padding: 12px 16px; display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
  header h1 { font-size: 17px; font-weight: 700; color: var(--green); letter-spacing: -0.3px; white-space: nowrap; }
  header .subtitle { color: var(--muted); font-size: 11px; }
  .header-badges { margin-left: auto; display: flex; gap: 6px; align-items: center; flex-wrap: wrap; justify-content: flex-end; }

  /* ── Badges ── */
  .badge { display: inline-flex; align-items: center; gap: 4px; padding: 2px 8px; border-radius: 10px; font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.4px; white-space: nowrap; }
  .badge.running { background: rgba(0,210,106,.15); color: var(--green); }
  .badge.paused  { background: rgba(210,153,34,.15); color: var(--yellow); }
  .badge.stopped { background: rgba(255,71,87,.15);  color: var(--red); }
  .badge.open    { background: rgba(0,210,106,.15); color: var(--green); }
  .badge.closed  { background: rgba(139,148,158,.15); color: var(--muted); }
  .badge.buy     { background: rgba(0,210,106,.15); color: var(--green); }
  .badge.sell    { background: rgba(255,71,87,.15);  color: var(--red); }
  .badge.dryrun  { background: rgba(88,166,255,.15); color: var(--blue); }

  /* ── Layout ── */
  main { padding: 16px; max-width: 1280px; margin: 0 auto; }

  /* ── Portfolio hero ── */
  .portfolio { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 20px; margin-bottom: 16px; }
  .portfolio-top { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
  .portfolio-label { color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 4px; }
  .portfolio-balance { font-size: clamp(28px, 8vw, 42px); font-weight: 800; color: var(--text); line-height: 1; }
  .portfolio-pnl { font-size: clamp(16px, 4vw, 22px); font-weight: 700; margin-top: 6px; }
  .portfolio-pnl.pos { color: var(--green); }
  .portfolio-pnl.neg { color: var(--red); }
  .portfolio-pnl.zero { color: var(--muted); }
  .portfolio-stats { display: flex; gap: 20px; margin-top: 16px; flex-wrap: wrap; }
  .pstat { }
  .pstat-label { color: var(--muted); font-size: 10px; text-transform: uppercase; letter-spacing: 0.6px; }
  .pstat-val { font-size: 15px; font-weight: 700; margin-top: 2px; }

  /* ── Summary grid ── */
  .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; margin-bottom: 16px; }
  .card { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 12px 14px; }
  .card-title { color: var(--muted); font-size: 10px; text-transform: uppercase; letter-spacing: 0.7px; margin-bottom: 6px; }
  .card-value { font-size: clamp(18px, 5vw, 24px); font-weight: 700; color: var(--text); }
  .card-value.green { color: var(--green); }
  .card-value.red   { color: var(--red); }
  .card-sub { color: var(--muted); font-size: 10px; margin-top: 3px; }

  /* ── Panel ── */
  .panel { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 14px; margin-bottom: 16px; }
  .section-title { font-size: 11px; font-weight: 700; color: var(--muted); text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 12px; }

  /* ── Controls ── */
  .controls { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 16px; }
  .controls button { padding: 12px 8px; border: none; border-radius: 8px; font-size: 13px; font-weight: 700; cursor: pointer; transition: opacity .15s; width: 100%; }
  .controls button:hover { opacity: .85; }
  .controls button:active { opacity: .65; }
  .btn-pause   { background: var(--yellow); color: #000; }
  .btn-resume  { background: var(--green);  color: #000; }
  .btn-flatten { background: var(--red);    color: #fff; }
  .btn-toggle  { background: var(--blue);   color: #000; }
  .btn-export  { background: var(--surface2); color: var(--muted); border: 1px solid var(--border) !important; grid-column: 1 / -1; }

  /* ── Apex panel ── */
  .apex-panel { border-color: var(--purple); }

  /* ── Signal cards ── */
  .signal-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 10px; }
  .signal-card { background: var(--bg); border: 1px solid var(--border); border-radius: 6px; padding: 12px; }
  .signal-card .instr { font-size: 14px; font-weight: 700; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center; }
  .signal-row { display: flex; justify-content: space-between; font-size: 12px; padding: 3px 0; border-bottom: 1px solid rgba(48,54,61,.4); }
  .signal-row:last-child { border-bottom: none; }
  .signal-row .label { color: var(--muted); }
  .signal-row .val { font-family: ui-monospace, monospace; font-size: 11px; }
  .hold-reason { font-size: 11px; color: var(--yellow); margin-top: 6px; font-style: italic; line-height: 1.4; }

  /* ── Trades table ── */
  .table-wrap { overflow-x: auto; -webkit-overflow-scrolling: touch; }
  table { width: 100%; border-collapse: collapse; min-width: 520px; }
  th { text-align: left; padding: 7px 10px; font-size: 10px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.4px; border-bottom: 1px solid var(--border); white-space: nowrap; }
  td { padding: 9px 10px; border-bottom: 1px solid rgba(48,54,61,.4); font-size: 12px; white-space: nowrap; }
  tr:last-child td { border-bottom: none; }
  tr:hover td { background: rgba(255,255,255,.02); }
  .pnl-pos { color: var(--green); font-weight: 700; }
  .pnl-neg { color: var(--red);   font-weight: 700; }
  .dim { color: var(--muted); }

  /* ── Status bar ── */
  .status-bar { display: flex; align-items: center; gap: 10px; padding: 8px 16px; background: var(--surface); border-top: 1px solid var(--border); position: fixed; bottom: 0; left: 0; right: 0; font-size: 10px; color: var(--muted); overflow: hidden; }
  .status-bar span { white-space: nowrap; }
  .status-bar .trading-on  { color: var(--green); font-weight: 700; }
  .status-bar .trading-off { color: var(--red); }

  /* ── Toast ── */
  #toast { position: fixed; top: 16px; right: 16px; left: 16px; max-width: 360px; margin: 0 auto; padding: 10px 18px; border-radius: 8px; font-size: 13px; font-weight: 600; display: none; z-index: 200; text-align: center; }
  #toast.success { background: var(--green); color: #000; }
  #toast.error   { background: var(--red);   color: #fff; }

  /* ── Desktop overrides ── */
  @media (min-width: 640px) {
    main { padding: 20px 24px; }
    header { padding: 14px 24px; }
    header h1 { font-size: 20px; }
    .controls { grid-template-columns: repeat(4, auto); width: auto; display: flex; flex-wrap: wrap; }
    .controls button { width: auto; padding: 9px 18px; }
    .btn-export { grid-column: auto; }
    .status-bar { padding: 8px 24px; font-size: 11px; gap: 14px; }
    #toast { left: auto; }
  }
</style>
</head>
<body>

<header>
  <div>
    <h1>⚡ OANDA Apex Bot</h1>
    <div class="subtitle">Autonomous Forex Practice Bot</div>
  </div>
  <div class="header-badges">
    <span id="market-badge" class="badge">–</span>
    <span id="worker-badge" class="badge">–</span>
    <span id="dry-run-badge" class="badge dryrun" style="display:none">DRY RUN</span>
  </div>
</header>

<main>

  <!-- Portfolio hero -->
  <div class="portfolio" id="portfolio-panel">
    <div class="portfolio-top">
      <div>
        <div class="portfolio-label">Account Balance</div>
        <div class="portfolio-balance" id="acct-balance">–</div>
        <div class="portfolio-pnl zero" id="acct-upnl">Unrealized P&amp;L: –</div>
      </div>
      <div style="text-align:right">
        <div class="portfolio-label">Today</div>
        <div id="today-realized" style="font-size:18px;font-weight:700;color:var(--muted)">–</div>
      </div>
    </div>
    <div class="portfolio-stats">
      <div class="pstat"><div class="pstat-label">NAV</div><div class="pstat-val" id="acct-nav">–</div></div>
      <div class="pstat"><div class="pstat-label">Open Trades</div><div class="pstat-val" id="acct-open">–</div></div>
      <div class="pstat"><div class="pstat-label">Trades Today</div><div class="pstat-val" id="trades-today">–</div></div>
      <div class="pstat"><div class="pstat-label">Losses Today</div><div class="pstat-val" id="losses-today">–</div></div>
    </div>
  </div>

  <!-- Summary cards (instrument + signal) -->
  <div class="grid">
    <div class="card">
      <div class="card-title">Current Instrument</div>
      <div class="card-value" id="current-instrument" style="font-size:clamp(16px,4vw,20px)">–</div>
    </div>
    <div class="card">
      <div class="card-title">Last Signal</div>
      <div class="card-value" id="last-signal" style="font-size:clamp(16px,4vw,20px)">–</div>
    </div>
    <div class="card">
      <div class="card-title">Uptime</div>
      <div class="card-value" id="uptime" style="font-size:clamp(16px,4vw,20px)">–</div>
    </div>
  </div>

  <!-- Apex panel (hidden unless apex_enabled) -->
  <div id="apex-panel" class="panel apex-panel" style="display:none">
    <div class="section-title">Apex Challenge</div>
    <div class="grid" style="margin-bottom:0">
      <div class="card" style="border:none;padding:4px 0"><div class="card-title">Realized PnL</div><div class="card-value" id="apex-pnl">–</div></div>
      <div class="card" style="border:none;padding:4px 0"><div class="card-title">Daily PnL</div><div class="card-value" id="apex-daily-pnl">–</div></div>
      <div class="card" style="border:none;padding:4px 0"><div class="card-title">Peak Balance</div><div class="card-value" id="apex-peak">–</div></div>
      <div class="card" style="border:none;padding:4px 0"><div class="card-title">Rule Status</div><div class="card-value" id="apex-status" style="font-size:14px">–</div></div>
    </div>
  </div>

  <!-- Controls -->
  <div class="controls">
    <button class="btn-pause"   onclick="sendControl('pause')">⏸ Pause</button>
    <button class="btn-resume"  onclick="sendControl('resume')">▶ Resume</button>
    <button class="btn-toggle"  onclick="sendControl('toggle-trading')">⚡ Toggle Trading</button>
    <button class="btn-flatten" onclick="confirmFlatten()">🔥 Flatten All</button>
    <button class="btn-export"  onclick="copyExport()">📋 Copy Export JSON</button>
  </div>

  <!-- Signal Analysis -->
  <div class="panel">
    <div class="section-title">Signal Analysis</div>
    <div class="signal-grid" id="signal-grid">
      <div style="color:var(--muted);font-size:13px">Waiting for first tick…</div>
    </div>
  </div>

  <!-- Trades -->
  <div class="panel">
    <div class="section-title">Recent Trades</div>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Instrument</th><th>Side</th><th>Units</th>
            <th>Open</th><th>Close</th><th>P&amp;L</th><th>Status</th><th>Time</th>
          </tr>
        </thead>
        <tbody id="trades-body">
          <tr><td colspan="8" style="color:var(--muted);text-align:center;padding:24px">Loading…</td></tr>
        </tbody>
      </table>
    </div>
  </div>

</main>

<div class="status-bar">
  <span id="last-tick">Last tick: –</span>
  <span>•</span>
  <span>Every 5s</span>
  <span>•</span>
  <span id="trading-status">Trading: –</span>
</div>

<div id="toast"></div>

<script>
const fmt = {
  usd:   v => v != null ? '$' + parseFloat(v).toLocaleString('en-US', {minimumFractionDigits:2, maximumFractionDigits:2}) : '–',
  pnl:   v => v != null ? (parseFloat(v) >= 0 ? '+' : '') + parseFloat(v).toFixed(2) : '–',
  price: v => v != null ? parseFloat(v).toFixed(5) : '–',
  uptime: s => { s = Math.round(s); const h = Math.floor(s/3600), m = Math.floor((s%3600)/60), sc = s%60; return [h,m,sc].map(x=>String(x).padStart(2,'0')).join(':'); },
  dt: s => s ? new Date(s).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit',second:'2-digit'}) : '–',
};

function toast(msg, type='success') {
  const el = document.getElementById('toast');
  el.textContent = msg; el.className = type; el.style.display = 'block';
  setTimeout(() => el.style.display = 'none', 2800);
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
  if (!confirm('Close ALL open trades?')) return;
  try {
    const r = await fetch('/control/flatten', {method:'POST'});
    const d = await r.json();
    toast('Flattened ' + d.closed_count + ' trade(s)');
    refresh();
  } catch(e) { toast('Flatten failed: ' + e.message, 'error'); }
}

async function refreshState() {
  try {
    const d = await (await fetch('/state')).json();

    // Header badges
    const wb = document.getElementById('worker-badge');
    wb.textContent = d.worker_status; wb.className = 'badge ' + d.worker_status.toLowerCase();
    const mb = document.getElementById('market-badge');
    mb.textContent = d.market_open ? '● OPEN' : '○ CLOSED';
    mb.className = 'badge ' + (d.market_open ? 'open' : 'closed');
    document.getElementById('dry-run-badge').style.display = d.dry_run ? '' : 'none';

    // Portfolio panel
    const a = d.account;
    if (a && a.balance != null) {
      document.getElementById('acct-balance').textContent = fmt.usd(a.balance);
      document.getElementById('acct-nav').textContent = fmt.usd(a.nav);
      document.getElementById('acct-open').textContent = a.open_trade_count ?? '–';
      const upnl = a.unrealized_pnl ?? 0;
      const upnlEl = document.getElementById('acct-upnl');
      upnlEl.textContent = 'Unrealized P&L: ' + (upnl >= 0 ? '+' : '') + upnl.toFixed(2);
      upnlEl.className = 'portfolio-pnl ' + (upnl > 0 ? 'pos' : upnl < 0 ? 'neg' : 'zero');
    }

    // Summary cards
    document.getElementById('trades-today').textContent = d.trades_today ?? '–';
    document.getElementById('losses-today').textContent = d.losses_today ?? '–';
    document.getElementById('current-instrument').textContent = d.current_instrument ?? '–';
    document.getElementById('uptime').textContent = fmt.uptime(d.uptime_seconds);
    const ls = document.getElementById('last-signal');
    ls.textContent = d.last_signal ?? '–';
    ls.className = 'card-value ' + (d.last_signal === 'BUY' ? 'green' : d.last_signal === 'SELL' ? 'red' : '');

    // Apex
    if (d.apex_state) {
      document.getElementById('apex-panel').style.display = '';
      const ax = d.apex_state;
      const setPnl = (id, v) => { const el = document.getElementById(id); el.textContent = fmt.pnl(v); el.className = 'card-value ' + (v >= 0 ? 'green' : 'red'); };
      setPnl('apex-pnl', ax.realized_pnl); setPnl('apex-daily-pnl', ax.daily_pnl);
      document.getElementById('apex-peak').textContent = fmt.usd(ax.peak_balance);
      const ss = document.getElementById('apex-status');
      ss.textContent = ax.can_trade ? '✓ ' + ax.rule_status : '✗ ' + ax.rule_status;
      ss.style.color = ax.can_trade ? 'var(--green)' : 'var(--red)';
    }

    // Status bar
    document.getElementById('last-tick').textContent = 'Tick: ' + fmt.dt(d.last_tick_at);
    const tsEl = document.getElementById('trading-status');
    tsEl.textContent = d.trading_enabled ? '✓ Trading ON' : '✗ Trading OFF';
    tsEl.className = d.trading_enabled ? 'trading-on' : 'trading-off';
  } catch(e) { console.error('State error', e); }
}

async function refreshTrades() {
  try {
    const d = await (await fetch('/trades')).json();
    const tbody = document.getElementById('trades-body');
    if (!d.trades || !d.trades.length) {
      tbody.innerHTML = '<tr><td colspan="8" style="color:var(--muted);text-align:center;padding:24px">No trades yet</td></tr>';
      return;
    }
    // Compute today's realized P&L from closed trades
    const today = new Date().toDateString();
    let todayPnl = 0;
    d.trades.forEach(t => {
      if (t.realized_pnl != null && t.closed_at && new Date(t.closed_at).toDateString() === today) todayPnl += parseFloat(t.realized_pnl);
    });
    const trEl = document.getElementById('today-realized');
    trEl.textContent = (todayPnl >= 0 ? '+' : '') + todayPnl.toFixed(2);
    trEl.style.color = todayPnl > 0 ? 'var(--green)' : todayPnl < 0 ? 'var(--red)' : 'var(--muted)';

    tbody.innerHTML = d.trades.map(t => {
      const pnl = t.realized_pnl;
      const pnlCls = pnl != null ? (pnl >= 0 ? 'pnl-pos' : 'pnl-neg') : '';
      return '<tr>' +
        '<td><strong>' + t.instrument + '</strong></td>' +
        '<td><span class="badge ' + t.side.toLowerCase() + '">' + t.side + '</span></td>' +
        '<td class="dim">' + t.units + '</td>' +
        '<td class="dim">' + fmt.price(t.open_price) + '</td>' +
        '<td class="dim">' + (t.close_price ? fmt.price(t.close_price) : '–') + '</td>' +
        '<td class="' + pnlCls + '">' + (pnl != null ? fmt.pnl(pnl) : '–') + '</td>' +
        '<td><span class="badge ' + t.status.toLowerCase() + '">' + t.status + '</span></td>' +
        '<td class="dim">' + fmt.dt(t.opened_at) + '</td>' +
        '</tr>';
    }).join('');
  } catch(e) { console.error('Trades error', e); }
}

async function refreshDebug() {
  try {
    const d = await (await fetch('/debug')).json();
    const grid = document.getElementById('signal-grid');
    const snaps = d.signal_snapshots || {};
    const instruments = Object.keys(snaps);
    if (!instruments.length) { grid.innerHTML = '<div style="color:var(--muted);font-size:13px">Waiting for first tick…</div>'; return; }
    grid.innerHTML = instruments.map(inst => {
      const s = snaps[inst];
      const sigColor = s.signal === 'BUY' ? 'var(--green)' : s.signal === 'SELL' ? 'var(--red)' : 'var(--muted)';
      const maColor = s.short_ma != null && s.long_ma != null ? (s.short_ma > s.long_ma ? 'var(--green)' : s.short_ma < s.long_ma ? 'var(--red)' : 'var(--muted)') : 'var(--muted)';
      const maArrow = s.short_ma != null && s.long_ma != null ? (s.short_ma > s.long_ma ? ' ↑' : s.short_ma < s.long_ma ? ' ↓' : ' =') : '';
      const p = v => v != null ? parseFloat(v).toFixed(5) : '–';
      return '<div class="signal-card">' +
        '<div class="instr"><span>' + inst + '</span><span style="color:' + sigColor + ';font-size:12px">' + (s.signal||'–') + '</span></div>' +
        '<div class="signal-row"><span class="label">Mid Price</span><span class="val">' + p(s.mid_price) + '</span></div>' +
        '<div class="signal-row"><span class="label">Spread</span><span class="val">' + (s.spread!=null?parseFloat(s.spread).toFixed(5):'–') + '</span></div>' +
        '<div class="signal-row"><span class="label">Short MA</span><span class="val" style="color:'+maColor+'">' + p(s.short_ma) + maArrow + '</span></div>' +
        '<div class="signal-row"><span class="label">Long MA</span><span class="val">' + p(s.long_ma) + '</span></div>' +
        '<div class="signal-row"><span class="label">Breakout High</span><span class="val">' + p(s.breakout_high) + '</span></div>' +
        '<div class="signal-row"><span class="label">Breakout Low</span><span class="val">' + p(s.breakout_low) + '</span></div>' +
        '<div class="signal-row"><span class="label">Candles</span><span class="val">' + (s.candle_count??'–') + (s.stale?' ⚠':'') + '</span></div>' +
        (s.hold_reason ? '<div class="hold-reason">⚠ ' + s.hold_reason + '</div>' : '') +
        '</div>';
    }).join('');
  } catch(e) { console.error('Debug error', e); }
}

async function copyExport() {
  try {
    const d = await (await fetch('/export')).json();
    await navigator.clipboard.writeText(JSON.stringify(d, null, 2));
    toast('Export JSON copied to clipboard!');
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
