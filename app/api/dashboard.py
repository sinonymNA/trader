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

  header { background: var(--surface); border-bottom: 1px solid var(--border); padding: 12px 16px; display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
  header h1 { font-size: 17px; font-weight: 700; color: var(--green); letter-spacing: -0.3px; white-space: nowrap; }
  header .subtitle { color: var(--muted); font-size: 11px; }
  .header-badges { margin-left: auto; display: flex; gap: 6px; align-items: center; flex-wrap: wrap; justify-content: flex-end; }

  .badge { display: inline-flex; align-items: center; gap: 4px; padding: 2px 8px; border-radius: 10px; font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.4px; white-space: nowrap; }
  .badge.running { background: rgba(0,210,106,.15); color: var(--green); }
  .badge.paused  { background: rgba(210,153,34,.15); color: var(--yellow); }
  .badge.stopped { background: rgba(255,71,87,.15);  color: var(--red); }
  .badge.open    { background: rgba(0,210,106,.15); color: var(--green); }
  .badge.closed  { background: rgba(139,148,158,.15); color: var(--muted); }
  .badge.buy     { background: rgba(0,210,106,.15); color: var(--green); }
  .badge.sell    { background: rgba(255,71,87,.15);  color: var(--red); }
  .badge.dryrun  { background: rgba(88,166,255,.15); color: var(--blue); }

  main { padding: 16px; max-width: 1280px; margin: 0 auto; }

  .portfolio { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 20px; margin-bottom: 16px; }
  .portfolio-top { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
  .portfolio-label { color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 4px; }
  .portfolio-balance { font-size: clamp(28px, 8vw, 42px); font-weight: 800; color: var(--text); line-height: 1; }
  .portfolio-pnl { font-size: clamp(15px, 4vw, 20px); font-weight: 700; margin-top: 6px; }
  .portfolio-pnl.pos { color: var(--green); }
  .portfolio-pnl.neg { color: var(--red); }
  .portfolio-pnl.zero { color: var(--muted); }
  .portfolio-stats { display: flex; gap: 20px; margin-top: 16px; flex-wrap: wrap; }
  .pstat-label { color: var(--muted); font-size: 10px; text-transform: uppercase; letter-spacing: 0.6px; }
  .pstat-val { font-size: 15px; font-weight: 700; margin-top: 2px; }

  .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; margin-bottom: 16px; }
  .card { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 12px 14px; }
  .card-title { color: var(--muted); font-size: 10px; text-transform: uppercase; letter-spacing: 0.7px; margin-bottom: 6px; }
  .card-value { font-size: clamp(18px, 5vw, 24px); font-weight: 700; color: var(--text); }
  .card-value.green { color: var(--green); }
  .card-value.red   { color: var(--red); }
  .card-sub { color: var(--muted); font-size: 10px; margin-top: 3px; }

  .panel { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 14px; margin-bottom: 16px; }
  .section-title { font-size: 11px; font-weight: 700; color: var(--muted); text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 12px; }

  .controls { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 16px; }
  .controls button { padding: 12px 8px; border: none; border-radius: 8px; font-size: 13px; font-weight: 700; cursor: pointer; transition: opacity .15s; width: 100%; }
  .controls button:active { opacity: .65; }
  .btn-pause   { background: var(--yellow); color: #000; }
  .btn-resume  { background: var(--green);  color: #000; }
  .btn-flatten { background: var(--red);    color: #fff; }
  .btn-toggle  { background: var(--blue);   color: #000; }
  .btn-export  { background: var(--surface2); color: var(--muted); border: 1px solid var(--border) !important; grid-column: 1 / -1; }

  .apex-panel { border-color: var(--purple); }

  /* ── Signal Visualizer ── */
  .vis-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 12px; }

  .vis-card {
    background: var(--surface2);
    border: 2px solid var(--border);
    border-radius: 10px;
    padding: 14px;
    transition: border-color .4s, background .4s;
    position: relative;
    overflow: hidden;
  }
  .vis-card.state-buy {
    border-color: var(--green);
    background: rgba(0, 210, 106, 0.06);
    animation: pulse-buy 1.8s ease-in-out infinite;
  }
  .vis-card.state-sell {
    border-color: var(--red);
    background: rgba(255, 71, 87, 0.06);
    animation: pulse-sell 1.8s ease-in-out infinite;
  }
  @keyframes pulse-buy {
    0%, 100% { box-shadow: 0 0 0 0 rgba(0,210,106,0); }
    50%       { box-shadow: 0 0 12px 3px rgba(0,210,106,0.25); }
  }
  @keyframes pulse-sell {
    0%, 100% { box-shadow: 0 0 0 0 rgba(255,71,87,0); }
    50%       { box-shadow: 0 0 12px 3px rgba(255,71,87,0.25); }
  }

  .vis-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
  .vis-instr { font-size: 15px; font-weight: 800; letter-spacing: 0.3px; }
  .vis-signal { font-size: 18px; font-weight: 900; letter-spacing: 1px; transition: color .3s; }
  .vis-signal.buy  { color: var(--green); }
  .vis-signal.sell { color: var(--red); }
  .vis-signal.hold { color: var(--muted); font-size: 12px; }

  /* sparkline */
  .vis-spark { width: 100%; height: 38px; margin-bottom: 12px; display: block; }

  /* condition bars */
  .cond-row { display: flex; align-items: center; gap: 8px; margin-bottom: 7px; }
  .cond-label { font-size: 10px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.5px; width: 70px; flex-shrink: 0; }
  .cond-track { flex: 1; height: 8px; background: rgba(255,255,255,0.06); border-radius: 4px; overflow: hidden; position: relative; }
  .cond-fill { height: 100%; border-radius: 4px; transition: width .6s cubic-bezier(.4,0,.2,1), background .4s; }
  .cond-val { font-size: 10px; font-family: ui-monospace, monospace; width: 46px; text-align: right; flex-shrink: 0; }

  /* alignment flash overlay */
  .vis-flash {
    position: absolute; inset: 0;
    display: flex; align-items: center; justify-content: center;
    font-size: 32px; font-weight: 900; letter-spacing: 2px;
    opacity: 0; pointer-events: none;
    transition: opacity .3s;
  }
  .vis-card.state-buy  .vis-flash { opacity: .08; color: var(--green); }
  .vis-card.state-sell .vis-flash { opacity: .06; color: var(--red); }

  .price-tag { font-size: 11px; color: var(--muted); margin-top: 8px; font-family: ui-monospace, monospace; }
  .price-tag .hl { color: var(--text); }

  /* trades */
  .table-wrap { overflow-x: auto; -webkit-overflow-scrolling: touch; }
  table { width: 100%; border-collapse: collapse; min-width: 520px; }
  th { text-align: left; padding: 7px 10px; font-size: 10px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.4px; border-bottom: 1px solid var(--border); white-space: nowrap; }
  td { padding: 9px 10px; border-bottom: 1px solid rgba(48,54,61,.4); font-size: 12px; white-space: nowrap; }
  tr:last-child td { border-bottom: none; }
  tr:hover td { background: rgba(255,255,255,.02); }
  .pnl-pos { color: var(--green); font-weight: 700; }
  .pnl-neg { color: var(--red);   font-weight: 700; }
  .dim { color: var(--muted); }

  .status-bar { display: flex; align-items: center; gap: 10px; padding: 8px 16px; background: var(--surface); border-top: 1px solid var(--border); position: fixed; bottom: 0; left: 0; right: 0; font-size: 10px; color: var(--muted); overflow: hidden; }
  .status-bar span { white-space: nowrap; }
  .trading-on  { color: var(--green); font-weight: 700; }
  .trading-off { color: var(--red); }

  #toast { position: fixed; top: 16px; right: 16px; left: 16px; max-width: 360px; margin: 0 auto; padding: 10px 18px; border-radius: 8px; font-size: 13px; font-weight: 600; display: none; z-index: 200; text-align: center; }
  #toast.success { background: var(--green); color: #000; }
  #toast.error   { background: var(--red);   color: #fff; }

  @media (min-width: 640px) {
    main { padding: 20px 24px; }
    header { padding: 14px 24px; }
    header h1 { font-size: 20px; }
    .controls { display: flex; flex-wrap: wrap; }
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
  <div class="portfolio">
    <div class="portfolio-top">
      <div>
        <div class="portfolio-label">Account Balance</div>
        <div class="portfolio-balance" id="acct-balance">–</div>
        <div class="portfolio-pnl zero" id="acct-upnl">Unrealized P&amp;L: –</div>
      </div>
      <div style="text-align:right">
        <div class="portfolio-label">Today Realized</div>
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

  <!-- Summary cards -->
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

  <!-- Apex panel -->
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

  <!-- Signal Visualizer -->
  <div class="panel">
    <div class="section-title">Live Signal Alignment</div>
    <div class="vis-grid" id="vis-grid">
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
// ── Price history (rolling 24 readings = ~2 min at 5s refresh) ──
const history = {};
const MAX_H = 24;

const fmt = {
  usd:   v => v != null ? '$' + parseFloat(v).toLocaleString('en-US', {minimumFractionDigits:2, maximumFractionDigits:2}) : '–',
  pnl:   v => v != null ? (parseFloat(v) >= 0 ? '+' : '') + parseFloat(v).toFixed(2) : '–',
  price: v => v != null ? parseFloat(v).toFixed(5) : '–',
  uptime: s => { s=Math.round(s); const h=Math.floor(s/3600),m=Math.floor((s%3600)/60),sc=s%60; return [h,m,sc].map(x=>String(x).padStart(2,'0')).join(':'); },
  dt: s => s ? new Date(s).toLocaleTimeString([],{hour:'2-digit',minute:'2-digit',second:'2-digit'}) : '–',
};

function toast(msg, type='success') {
  const el=document.getElementById('toast');
  el.textContent=msg; el.className=type; el.style.display='block';
  setTimeout(()=>el.style.display='none', 2800);
}

async function sendControl(action) {
  try {
    const r=await fetch('/control/'+action,{method:'POST'});
    const d=await r.json(); toast(d.message||action+' OK'); refresh();
  } catch(e){ toast('Error: '+e.message,'error'); }
}

async function confirmFlatten() {
  if(!confirm('Close ALL open trades?')) return;
  try {
    const r=await fetch('/control/flatten',{method:'POST'});
    const d=await r.json(); toast('Flattened '+d.closed_count+' trade(s)'); refresh();
  } catch(e){ toast('Flatten failed: '+e.message,'error'); }
}

// ── Sparkline ──
function sparkline(prices, w, h) {
  if (!prices || prices.length < 2) return '<line x1="0" y1="'+(h/2)+'" x2="'+w+'" y2="'+(h/2)+'" stroke="var(--border)" stroke-width="1"/>';
  const mn=Math.min(...prices), mx=Math.max(...prices), rng=mx-mn||0.000001;
  const pts=prices.map((p,i)=>{
    const x=(i/(prices.length-1))*w;
    const y=h-2-((p-mn)/rng)*(h-4);
    return x.toFixed(1)+','+y.toFixed(1);
  }).join(' ');
  const rising=prices[prices.length-1]>=prices[0];
  const col=rising?'var(--green)':'var(--red)';
  const lx=w, ly=h-2-((prices[prices.length-1]-mn)/rng)*(h-4);
  return '<polyline points="'+pts+'" fill="none" stroke="'+col+'" stroke-width="1.5" stroke-linejoin="round" stroke-linecap="round"/>'
       + '<circle cx="'+lx.toFixed(1)+'" cy="'+ly.toFixed(1)+'" r="2.5" fill="'+col+'"/>';
}

// ── Condition bar ──
function condBar(label, pct, col, valStr) {
  pct = Math.max(0, Math.min(100, pct));
  return '<div class="cond-row">'
    + '<span class="cond-label">'+label+'</span>'
    + '<div class="cond-track"><div class="cond-fill" style="width:'+pct+'%;background:'+col+'"></div></div>'
    + '<span class="cond-val" style="color:'+col+'">'+valStr+'</span>'
    + '</div>';
}

// ── Visualizer cards ──
function buildVisCard(inst, s, prices) {
  const isJPY = inst.includes('JPY');
  const maxSpread = isJPY ? 0.05 : 0.0005;
  const dec = isJPY ? 3 : 5;

  const bullMA = s.short_ma != null && s.long_ma != null && s.short_ma > s.long_ma;
  const bearMA = s.short_ma != null && s.long_ma != null && s.short_ma < s.long_ma;
  const spreadOK = s.spread != null && s.spread <= maxSpread;
  const isBuy  = s.signal === 'BUY';
  const isSell = s.signal === 'SELL';

  // MA bar: 0–100 based on (short-long)/long*factor
  let maPct=50, maCol='var(--muted)', maStr='FLAT';
  if (s.short_ma && s.long_ma) {
    const diff = (s.short_ma - s.long_ma) / s.long_ma;
    if (bullMA) { maPct=Math.min(100,50+diff*100000); maCol='var(--green)'; maStr='BULL ↑'; }
    else        { maPct=Math.max(0, 50+diff*100000);  maCol='var(--red)';   maStr='BEAR ↓'; }
  }

  // Breakout proximity bar
  let bkPct=0, bkCol='var(--muted)', bkStr='–';
  if (s.short_ma && s.long_ma && s.breakout_high && s.breakout_low && s.mid_price) {
    if (bullMA) {
      const range = s.breakout_high - s.long_ma;
      bkPct = range > 0 ? ((s.mid_price - s.long_ma) / range) * 100 : 0;
      bkCol = bkPct >= 100 ? 'var(--green)' : bkPct > 60 ? 'var(--yellow)' : 'var(--muted)';
      bkStr = bkPct.toFixed(0)+'%';
    } else if (bearMA) {
      const range = s.long_ma - s.breakout_low;
      bkPct = range > 0 ? ((s.long_ma - s.mid_price) / range) * 100 : 0;
      bkCol = bkPct >= 100 ? 'var(--red)' : bkPct > 60 ? 'var(--yellow)' : 'var(--muted)';
      bkStr = bkPct.toFixed(0)+'%';
    }
  }

  // Spread bar (inverted — full = tight spread = good)
  const spreadPct = spreadOK ? 100 : Math.max(0, (1 - s.spread/maxSpread)*100);
  const spreadCol = spreadOK ? 'var(--green)' : 'var(--red)';
  const spreadStr = spreadOK ? 'OK' : 'WIDE';

  // Card state
  const state = isBuy ? 'state-buy' : isSell ? 'state-sell' : '';
  const sigClass = isBuy ? 'buy' : isSell ? 'sell' : 'hold';
  const sigLabel = isBuy ? '▲ BUY' : isSell ? '▼ SELL' : 'HOLD';

  // Sparkline SVG
  const svgW=280, svgH=38;
  const spark=sparkline(prices, svgW, svgH);

  // Price tag
  const p = v => v != null ? parseFloat(v).toFixed(dec) : '–';
  const priceTag = bullMA
    ? '<div class="price-tag">Price <span class="hl">'+p(s.mid_price)+'</span> → need <span class="hl">'+p(s.breakout_high)+'</span></div>'
    : bearMA
    ? '<div class="price-tag">Price <span class="hl">'+p(s.mid_price)+'</span> → need <span class="hl">'+p(s.breakout_low)+'</span></div>'
    : '<div class="price-tag">Price <span class="hl">'+p(s.mid_price)+'</span></div>';

  return '<div class="vis-card '+state+'">'
    + '<div class="vis-flash">'+(isBuy?'BUY':isSell?'SELL':'')+'</div>'
    + '<div class="vis-header">'
    +   '<span class="vis-instr">'+inst+'</span>'
    +   '<span class="vis-signal '+sigClass+'">'+sigLabel+'</span>'
    + '</div>'
    + '<svg class="vis-spark" viewBox="0 0 '+svgW+' '+svgH+'" preserveAspectRatio="none">'+spark+'</svg>'
    + condBar('MA Trend', maPct, maCol, maStr)
    + condBar('Breakout', Math.min(bkPct,100), bullMA||bearMA?bkCol:'var(--muted)', bkStr)
    + condBar('Spread',   spreadPct,            spreadCol,                           spreadStr)
    + priceTag
    + '</div>';
}

async function refreshVisualizer() {
  try {
    const d = await (await fetch('/debug')).json();
    const snaps = d.signal_snapshots || {};
    const instruments = Object.keys(snaps);
    const grid = document.getElementById('vis-grid');
    if (!instruments.length) {
      grid.innerHTML='<div style="color:var(--muted);font-size:13px">Waiting for first tick…</div>';
      return;
    }
    instruments.forEach(inst => {
      if (!history[inst]) history[inst]=[];
      const mid=snaps[inst].mid_price;
      if (mid != null) { history[inst].push(mid); if(history[inst].length>MAX_H) history[inst].shift(); }
    });
    grid.innerHTML = instruments.map(inst => buildVisCard(inst, snaps[inst], history[inst]||[])).join('');
  } catch(e){ console.error('Vis error',e); }
}

async function refreshState() {
  try {
    const d=await (await fetch('/state')).json();
    const wb=document.getElementById('worker-badge');
    wb.textContent=d.worker_status; wb.className='badge '+d.worker_status.toLowerCase();
    const mb=document.getElementById('market-badge');
    mb.textContent=d.market_open?'● OPEN':'○ CLOSED';
    mb.className='badge '+(d.market_open?'open':'closed');
    document.getElementById('dry-run-badge').style.display=d.dry_run?'':'none';

    const a=d.account;
    if(a&&a.balance!=null){
      document.getElementById('acct-balance').textContent=fmt.usd(a.balance);
      document.getElementById('acct-nav').textContent=fmt.usd(a.nav);
      document.getElementById('acct-open').textContent=a.open_trade_count??'–';
      const upnl=a.unrealized_pnl??0;
      const upnlEl=document.getElementById('acct-upnl');
      upnlEl.textContent='Unrealized P&L: '+(upnl>=0?'+':'')+upnl.toFixed(2);
      upnlEl.className='portfolio-pnl '+(upnl>0?'pos':upnl<0?'neg':'zero');
    }
    document.getElementById('trades-today').textContent=d.trades_today??'–';
    document.getElementById('losses-today').textContent=d.losses_today??'–';
    document.getElementById('current-instrument').textContent=d.current_instrument??'–';
    document.getElementById('uptime').textContent=fmt.uptime(d.uptime_seconds);
    const ls=document.getElementById('last-signal');
    ls.textContent=d.last_signal??'–';
    ls.className='card-value '+(d.last_signal==='BUY'?'green':d.last_signal==='SELL'?'red':'');

    if(d.apex_state){
      document.getElementById('apex-panel').style.display='';
      const ax=d.apex_state;
      const setPnl=(id,v)=>{const el=document.getElementById(id);el.textContent=fmt.pnl(v);el.className='card-value '+(v>=0?'green':'red');};
      setPnl('apex-pnl',ax.realized_pnl); setPnl('apex-daily-pnl',ax.daily_pnl);
      document.getElementById('apex-peak').textContent=fmt.usd(ax.peak_balance);
      const ss=document.getElementById('apex-status');
      ss.textContent=ax.can_trade?'✓ '+ax.rule_status:'✗ '+ax.rule_status;
      ss.style.color=ax.can_trade?'var(--green)':'var(--red)';
    }
    document.getElementById('last-tick').textContent='Tick: '+fmt.dt(d.last_tick_at);
    const tsEl=document.getElementById('trading-status');
    tsEl.textContent=d.trading_enabled?'✓ Trading ON':'✗ Trading OFF';
    tsEl.className=d.trading_enabled?'trading-on':'trading-off';
  } catch(e){ console.error('State error',e); }
}

async function refreshTrades() {
  try {
    const d=await (await fetch('/trades')).json();
    const tbody=document.getElementById('trades-body');
    if(!d.trades||!d.trades.length){
      tbody.innerHTML='<tr><td colspan="8" style="color:var(--muted);text-align:center;padding:24px">No trades yet</td></tr>';
      return;
    }
    const today=new Date().toDateString();
    let todayPnl=0;
    d.trades.forEach(t=>{if(t.realized_pnl!=null&&t.closed_at&&new Date(t.closed_at).toDateString()===today)todayPnl+=parseFloat(t.realized_pnl);});
    const trEl=document.getElementById('today-realized');
    trEl.textContent=(todayPnl>=0?'+':'')+todayPnl.toFixed(2);
    trEl.style.color=todayPnl>0?'var(--green)':todayPnl<0?'var(--red)':'var(--muted)';

    tbody.innerHTML=d.trades.map(t=>{
      const pnl=t.realized_pnl;
      const pnlCls=pnl!=null?(pnl>=0?'pnl-pos':'pnl-neg'):'';
      return '<tr>'
        +'<td><strong>'+t.instrument+'</strong></td>'
        +'<td><span class="badge '+t.side.toLowerCase()+'">'+t.side+'</span></td>'
        +'<td class="dim">'+t.units+'</td>'
        +'<td class="dim">'+fmt.price(t.open_price)+'</td>'
        +'<td class="dim">'+(t.close_price?fmt.price(t.close_price):'–')+'</td>'
        +'<td class="'+pnlCls+'">'+(pnl!=null?fmt.pnl(pnl):'–')+'</td>'
        +'<td><span class="badge '+t.status.toLowerCase()+'">'+t.status+'</span></td>'
        +'<td class="dim">'+fmt.dt(t.opened_at)+'</td>'
        +'</tr>';
    }).join('');
  } catch(e){ console.error('Trades error',e); }
}

async function copyExport() {
  try {
    const d=await (await fetch('/export')).json();
    await navigator.clipboard.writeText(JSON.stringify(d,null,2));
    toast('Export JSON copied!');
  } catch(e){ toast('Copy failed: '+e.message,'error'); }
}

function refresh() { refreshState(); refreshTrades(); refreshVisualizer(); }
refresh();
setInterval(refresh, 5000);
</script>
</body>
</html>
"""


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard() -> str:
    return _HTML
