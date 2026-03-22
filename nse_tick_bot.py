"""
╔══════════════════════════════════════════════════════════════════╗
║   NSE TICK BOT + LIVE DASHBOARD  —  Single File                 ║
║   Zero-delay 3-min signals from raw Upstox LTPC ticks           ║
║   Supertrend(10,3) · Heikin Ashi · ADX · VWAP                  ║
║                                                                  ║
║   Run:  python nse_tick_bot.py                                   ║
║   Open: http://localhost:8000                                    ║
║                                                                  ║
║   Env vars required:                                             ║
║     UPSTOX_ACCESS_TOKEN  — from developer.upstox.com            ║
║     TELEGRAM_BOT_TOKEN   — from @BotFather  (optional)          ║
║     CHAT_IDS             — comma-sep Telegram IDs  (optional)   ║
╚══════════════════════════════════════════════════════════════════╝

Install:
  pip install fastapi uvicorn upstox-python-sdk pandas numpy requests python-dotenv
"""

# ════════════════════════════════════════════════════════════════════
# EMBEDDED DASHBOARD HTML  (served at GET /)
# ════════════════════════════════════════════════════════════════════

DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>NSE Signal Dashboard</title>
<style>
  :root{
    --bg:#09090b;--card:#18181b;--border:#27272a;
    --up:#22c55e;--down:#ef4444;--muted:#71717a;
    --text:#fafafa;--indigo:#818cf8;
    --amber:#fbbf24;
  }
  *{margin:0;padding:0;box-sizing:border-box;}
  body{font-family:'Inter',system-ui,sans-serif;background:var(--bg);color:var(--text);height:100vh;display:flex;flex-direction:column;overflow:hidden;}

  /* ── Status Bar ── */
  #statusbar{display:flex;align-items:center;justify-content:space-between;padding:10px 20px;border-bottom:1px solid var(--border);background:rgba(0,0,0,.5);backdrop-filter:blur(12px);flex-shrink:0;z-index:30;gap:12px;flex-wrap:wrap;}
  .sb-logo{font-weight:800;font-size:1rem;letter-spacing:.04em;color:var(--text);}
  .sb-logo span{color:var(--indigo);}
  .sb-pills{display:flex;gap:8px;align-items:center;flex-wrap:wrap;}
  .pill{display:flex;align-items:center;gap:5px;padding:4px 10px;border-radius:999px;font-size:.7rem;font-weight:700;border:1px solid var(--border);background:rgba(255,255,255,.04);letter-spacing:.04em;}
  .pill.green{border-color:rgba(34,197,94,.3);background:rgba(34,197,94,.08);color:var(--up);}
  .pill.red{border-color:rgba(239,68,68,.3);background:rgba(239,68,68,.08);color:var(--down);}
  .pill.amber{border-color:rgba(251,191,36,.3);background:rgba(251,191,36,.08);color:var(--amber);}
  .dot{width:7px;height:7px;border-radius:50%;background:currentColor;}
  .dot.ping{animation:ping 1.2s ease-in-out infinite;}
  @keyframes ping{0%,100%{opacity:1;transform:scale(1);}50%{opacity:.5;transform:scale(1.4);}}
  #clock{font-size:.8rem;font-weight:600;font-family:monospace;color:var(--muted);}

  /* ── Main layout ── */
  #main{display:flex;flex:1;overflow:hidden;}
  #feed{flex:1;display:flex;flex-direction:column;min-width:0;}
  #feedhdr{padding:12px 20px;border-bottom:1px solid var(--border);background:rgba(0,0,0,.4);backdrop-filter:blur(12px);display:flex;align-items:center;justify-content:space-between;flex-shrink:0;}
  #feedhdr h2{font-size:.72rem;font-weight:800;letter-spacing:.1em;text-transform:uppercase;color:var(--text);display:flex;align-items:center;gap:8px;}
  #signals{flex:1;overflow-y:auto;padding:20px;display:flex;flex-direction:column;gap:14px;scrollbar-width:none;}
  #signals::-webkit-scrollbar{display:none;}

  /* ── Signal card ── */
  .card{border-radius:16px;padding:18px;background:var(--card);border:1px solid var(--border);position:relative;overflow:hidden;animation:slideIn .35s cubic-bezier(.4,0,.2,1);}
  @keyframes slideIn{from{opacity:0;transform:translateY(-16px) scale(.97);}to{opacity:1;transform:none;}}
  .card.call{border-color:rgba(34,197,94,.2);}
  .card.put{border-color:rgba(239,68,68,.2);}
  .card.flash-call{animation:slideIn .35s cubic-bezier(.4,0,.2,1),flashCall 2s ease-out;}
  .card.flash-put{animation:slideIn .35s cubic-bezier(.4,0,.2,1),flashPut 2s ease-out;}
  @keyframes flashCall{0%{box-shadow:0 0 0 0 rgba(34,197,94,.5);}50%{box-shadow:0 0 24px 6px rgba(34,197,94,.25);}100%{box-shadow:none;}}
  @keyframes flashPut{0%{box-shadow:0 0 0 0 rgba(239,68,68,.5);}50%{box-shadow:0 0 24px 6px rgba(239,68,68,.25);}100%{box-shadow:none;}}
  .card-glow{position:absolute;inset:-60px;border-radius:50%;opacity:.04;filter:blur(40px);pointer-events:none;}
  .call .card-glow{background:var(--up);}
  .put .card-glow{background:var(--down);}
  .card-top{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:14px;}
  .card-name{font-size:1.15rem;font-weight:800;color:var(--text);}
  .card-time{font-size:.7rem;color:var(--muted);font-weight:600;margin-top:4px;display:flex;align-items:center;gap:5px;}
  .badge{display:flex;align-items:center;gap:6px;padding:6px 14px;border-radius:10px;font-size:.8rem;font-weight:800;letter-spacing:.03em;}
  .badge.call{background:rgba(34,197,94,.1);color:var(--up);border:1px solid rgba(34,197,94,.3);}
  .badge.put{background:rgba(239,68,68,.1);color:var(--down);border:1px solid rgba(239,68,68,.3);}
  .metrics{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;}
  .metric{background:rgba(0,0,0,.35);border-radius:12px;padding:10px 12px;border:1px solid rgba(255,255,255,.05);}
  .metric-label{font-size:.6rem;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);font-weight:700;margin-bottom:5px;}
  .metric-val{font-size:.82rem;font-weight:800;}
  .c-up{color:var(--up);} .c-down{color:var(--down);} .c-amber{color:var(--amber);} .c-muted{color:var(--muted);}

  /* ── Empty state ── */
  #empty{display:flex;flex-direction:column;align-items:center;justify-content:center;flex:1;text-align:center;padding:40px;gap:14px;color:var(--muted);}
  #empty .icon{width:64px;height:64px;border-radius:50%;background:rgba(255,255,255,.05);display:flex;align-items:center;justify-content:center;font-size:1.8rem;}
  #empty h3{font-size:1rem;color:rgba(255,255,255,.5);}
  #empty p{font-size:.8rem;max-width:340px;line-height:1.6;}

  /* ── Sidebar ── */
  #sidebar{width:300px;flex-shrink:0;background:rgba(24,24,27,.5);border-left:1px solid var(--border);display:flex;flex-direction:column;backdrop-filter:blur(16px);}
  #sbhdr{padding:14px 16px;border-bottom:1px solid var(--border);background:rgba(0,0,0,.2);flex-shrink:0;}
  #sbhdr h2{font-size:.72rem;font-weight:800;letter-spacing:.1em;text-transform:uppercase;margin-bottom:10px;display:flex;align-items:center;justify-content:space-between;}
  #sbhdr h2 .closed-tag{font-size:.6rem;background:rgba(255,255,255,.08);color:rgba(255,255,255,.4);padding:2px 8px;border-radius:999px;}
  #search{width:100%;background:rgba(0,0,0,.4);border:1px solid var(--border);border-radius:10px;padding:8px 12px 8px 34px;color:var(--text);font-size:.8rem;outline:none;}
  #search::placeholder{color:var(--muted);}
  #search:focus{border-color:rgba(255,255,255,.2);}
  .search-wrap{position:relative;}
  .search-wrap::before{content:"⌕";position:absolute;left:10px;top:50%;transform:translateY(-50%);color:var(--muted);font-size:1rem;pointer-events:none;}
  #tickers{flex:1;overflow-y:auto;padding:8px;scrollbar-width:none;}
  #tickers::-webkit-scrollbar{display:none;}
  .ticker-row{display:flex;align-items:center;justify-content:space-between;padding:10px 12px;border-radius:12px;transition:background .15s,border-color .15s;border:1px solid transparent;cursor:default;}
  .ticker-row:hover{background:rgba(255,255,255,.03);}
  .ticker-row.flash-up{background:rgba(34,197,94,.1);border-color:rgba(34,197,94,.2);}
  .ticker-row.flash-down{background:rgba(239,68,68,.1);border-color:rgba(239,68,68,.2);}
  .ticker-name{font-size:.82rem;font-weight:700;color:rgba(255,255,255,.85);}
  .ticker-name.index{color:var(--indigo);}
  .ticker-price{font-size:.82rem;font-weight:700;font-family:monospace;color:var(--text);transition:color .2s;}
  .ticker-price.up{color:var(--up);}
  .ticker-price.down{color:var(--down);}

  /* ── Background decoration ── */
  body::before{content:"";position:fixed;top:-20%;left:-10%;width:50%;height:50%;border-radius:50%;background:radial-gradient(circle,rgba(99,102,241,.08),transparent 70%);pointer-events:none;z-index:0;}
  body::after{content:"";position:fixed;bottom:-20%;right:-10%;width:40%;height:50%;border-radius:50%;background:radial-gradient(circle,rgba(59,130,246,.06),transparent 70%);pointer-events:none;z-index:0;}

  @media(max-width:700px){#sidebar{display:none;}}
</style>
</head>
<body>

<!-- Status Bar -->
<div id="statusbar">
  <div class="sb-logo">NSE<span>⚡</span>Bot</div>
  <div class="sb-pills">
    <div class="pill" id="pill-sse">
      <span class="dot" id="dot-sse"></span>
      <span id="lbl-sse">SSE …</span>
    </div>
    <div class="pill" id="pill-ws">
      <span class="dot" id="dot-ws"></span>
      <span id="lbl-ws">Bot …</span>
    </div>
    <div class="pill" id="pill-inst">
      <span>📡</span><span id="lbl-inst">0 instr</span>
    </div>
    <div class="pill" id="pill-ticks">
      <span>🔢</span><span id="lbl-ticks">0 ticks</span>
    </div>
  </div>
  <div id="clock">--:--:--</div>
</div>

<!-- Main -->
<div id="main">

  <!-- Signal Feed -->
  <div id="feed">
    <div id="feedhdr">
      <h2>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
        Live Signals Feed
      </h2>
      <div style="font-size:.7rem;color:var(--muted);display:flex;align-items:center;gap:6px;">
        <span style="display:inline-block;width:7px;height:7px;border-radius:50%;background:var(--up);animation:ping 1.2s infinite;"></span>
        Zero-delay · 3-min bar close
      </div>
    </div>
    <div id="signals">
      <div id="empty">
        <div class="icon">📊</div>
        <h3>No signals yet</h3>
        <p>The bot is analyzing raw LTPC ticks and building 1-minute bars. Signals appear here at exact 3-minute bar close.</p>
      </div>
    </div>
  </div>

  <!-- Ticker Sidebar -->
  <div id="sidebar">
    <div id="sbhdr">
      <h2>Live Market <span class="closed-tag" id="market-tag">CLOSED</span></h2>
      <div class="search-wrap">
        <input id="search" type="text" placeholder="Search symbol…"/>
      </div>
    </div>
    <div id="tickers"></div>
  </div>

</div>

<script>
// ── State ──────────────────────────────────────────────────────────
const state = {
  signals: [],
  status: { connected: false, tick_count: 0, last_tick_ts: 0, instruments_ready: 0, started_at: null },
  ticks: {},
  sseOk: false,
  searchTerm: '',
};

let firstLoad = true;

// ── Clock ──────────────────────────────────────────────────────────
function updateClock() {
  const now = new Date();
  const ist = new Date(now.toLocaleString('en-US', { timeZone: 'Asia/Kolkata' }));
  document.getElementById('clock').textContent =
    ist.toTimeString().substring(0, 8) + ' IST';
}
setInterval(updateClock, 1000);
updateClock();

// ── Helpers ────────────────────────────────────────────────────────
function fmtPrice(n) {
  return Number(n).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function fmtTime(tsStr) {
  try {
    const d = new Date(tsStr);
    if (isNaN(d.getTime())) return tsStr.substring(11, 16);
    const ist = new Date(d.toLocaleString('en-US', { timeZone: 'Asia/Kolkata' }));
    return ist.toTimeString().substring(0, 5);
  } catch { return tsStr; }
}

function metricColor(label, val) {
  if (label === 'Trend Power') return val === 'Strong' ? 'c-up' : val === 'Moderate' ? 'c-amber' : 'c-muted';
  return val === 'Bullish' ? 'c-up' : val === 'Bearish' ? 'c-down' : 'c-muted';
}

// ── Signal Cards ───────────────────────────────────────────────────
function renderSignalCard(sig, isNew) {
  const isCall = sig.signal === 'BUY CALL';
  const cls    = isCall ? 'call' : 'put';
  const flash  = isNew ? (isCall ? ' flash-call' : ' flash-put') : '';
  return `
    <div class="card ${cls}${flash}" data-id="${sig.id}">
      <div class="card-glow"></div>
      <div class="card-top">
        <div>
          <div class="card-name">${sig.name}</div>
          <div class="card-time">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
            ${fmtTime(sig.bar_ts)} &nbsp;·&nbsp; 3m Bar Close
          </div>
        </div>
        <div class="badge ${cls}">
          ${isCall
            ? '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><line x1="7" y1="17" x2="17" y2="7"/><polyline points="7 7 17 7 17 17"/></svg>'
            : '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><line x1="7" y1="7" x2="17" y2="17"/><polyline points="17 7 17 17 7 17"/></svg>'
          }
          ${sig.signal}
        </div>
      </div>
      <div class="metrics">
        <div class="metric">
          <div class="metric-label">⚡ Trend Power</div>
          <div class="metric-val ${metricColor('Trend Power', sig.trend_power)}">${sig.trend_power}</div>
        </div>
        <div class="metric">
          <div class="metric-label">📈 Candle Trend</div>
          <div class="metric-val ${metricColor('Candle Trend', sig.candle_trend)}">${sig.candle_trend}</div>
        </div>
        <div class="metric">
          <div class="metric-label">🎯 Value Zone</div>
          <div class="metric-val ${metricColor('Value Zone', sig.value_zone)}">${sig.value_zone}</div>
        </div>
      </div>
    </div>`;
}

function renderSignals() {
  const container = document.getElementById('signals');
  if (state.signals.length === 0) {
    container.innerHTML = `<div id="empty">
      <div class="icon">📊</div>
      <h3>No signals yet</h3>
      <p>The bot is analyzing raw LTPC ticks and building 1-minute bars. Signals appear here at exact 3-minute bar close.</p>
    </div>`;
    return;
  }
  container.innerHTML = state.signals.map((s, i) => renderSignalCard(s, false)).join('');
}

function prependSignal(sig) {
  document.getElementById('empty')?.remove();
  const container = document.getElementById('signals');
  const div = document.createElement('div');
  div.innerHTML = renderSignalCard(sig, true);
  container.insertBefore(div.firstElementChild, container.firstChild);
  // trim to 200
  while (container.children.length > 200) container.removeChild(container.lastChild);
}

// ── Status Bar ─────────────────────────────────────────────────────
function updateStatusBar() {
  const { status, sseOk } = state;

  // SSE pill
  const pillSse = document.getElementById('pill-sse');
  const dotSse  = document.getElementById('dot-sse');
  const lblSse  = document.getElementById('lbl-sse');
  if (sseOk) {
    pillSse.className = 'pill green';
    dotSse.className  = 'dot ping';
    lblSse.textContent = 'SSE Live';
  } else {
    pillSse.className = 'pill red';
    dotSse.className  = 'dot';
    lblSse.textContent = 'SSE Off';
  }

  // Bot pill
  const pillWs = document.getElementById('pill-ws');
  const dotWs  = document.getElementById('dot-ws');
  const lblWs  = document.getElementById('lbl-ws');
  if (status.connected) {
    pillWs.className = 'pill green';
    dotWs.className  = 'dot ping';
    lblWs.textContent = 'Bot Live';
  } else {
    pillWs.className = 'pill red';
    dotWs.className  = 'dot';
    lblWs.textContent = 'Bot Off';
  }

  document.getElementById('lbl-inst').textContent  = `${status.instruments_ready || 0} instr`;
  document.getElementById('lbl-ticks').textContent = `${(status.tick_count || 0).toLocaleString()} ticks`;

  // Market tag
  const isOpen = status.connected && status.last_tick_ts && (Date.now()/1000 - status.last_tick_ts < 90);
  const tag = document.getElementById('market-tag');
  if (tag) { tag.style.display = isOpen ? 'none' : ''; }
}

// ── Tickers ────────────────────────────────────────────────────────
const prevPrices = {};
const flashTimers = {};

function renderTickers() {
  const term = state.searchTerm.toLowerCase();
  const all  = Object.values(state.ticks)
    .filter(t => t.name.toLowerCase().includes(term))
    .sort((a, b) => a.name.localeCompare(b.name));

  const container = document.getElementById('tickers');
  container.innerHTML = all.map(t => {
    const isIdx = t.key.includes('INDEX');
    return `
      <div class="ticker-row" id="tick-${t.key.replace(/[|.]/g,'-')}">
        <span class="ticker-name ${isIdx ? 'index' : ''}">${t.name}</span>
        <span class="ticker-price">${fmtPrice(t.ltp)}</span>
      </div>`;
  }).join('');
}

function updateTicker(tick) {
  const rowId = 'tick-' + tick.key.replace(/[|.]/g, '-');
  let row = document.getElementById(rowId);

  const prev = prevPrices[tick.key];
  const dir  = prev == null ? null : tick.ltp > prev ? 'up' : tick.ltp < prev ? 'down' : null;
  prevPrices[tick.key] = tick.ltp;

  if (!row) {
    renderTickers(); // new instrument → full re-render
    return;
  }

  const priceEl = row.querySelector('.ticker-price');
  priceEl.textContent = fmtPrice(tick.ltp);

  if (dir) {
    priceEl.className = `ticker-price ${dir}`;
    row.className = `ticker-row flash-${dir}`;
    clearTimeout(flashTimers[tick.key]);
    flashTimers[tick.key] = setTimeout(() => {
      if (row) { row.className = 'ticker-row'; priceEl.className = 'ticker-price'; }
    }, 900);
  }
}

document.getElementById('search').addEventListener('input', e => {
  state.searchTerm = e.target.value;
  renderTickers();
});

// ── SSE Connection ─────────────────────────────────────────────────
let es = null;
let retryTimer = null;

function connectSSE() {
  if (es) { es.close(); es = null; }

  es = new EventSource('/api/events');

  es.onopen = () => {
    state.sseOk = true;
    updateStatusBar();
  };

  es.addEventListener('init', e => {
    try {
      const data = JSON.parse(e.data);
      state.signals = (data.signals || []);
      state.status  = data.status || state.status;
      const ticksArr = data.ticks || [];
      ticksArr.forEach(t => { state.ticks[t.key] = t; prevPrices[t.key] = t.ltp; });
      firstLoad = false;
      renderSignals();
      renderTickers();
      updateStatusBar();
    } catch(err) { console.error('init parse error', err); }
  });

  es.addEventListener('signal', e => {
    try {
      const sig = JSON.parse(e.data);
      state.signals.unshift(sig);
      if (state.signals.length > 200) state.signals.pop();
      prependSignal(sig);
    } catch(err) { console.error('signal parse error', err); }
  });

  es.addEventListener('status', e => {
    try {
      state.status = JSON.parse(e.data);
      updateStatusBar();
    } catch(err) {}
  });

  es.addEventListener('tick', e => {
    try {
      const tick = JSON.parse(e.data);
      state.ticks[tick.key] = tick;
      updateTicker(tick);
    } catch(err) {}
  });

  es.onerror = () => {
    state.sseOk = false;
    updateStatusBar();
    es.close(); es = null;
    clearTimeout(retryTimer);
    retryTimer = setTimeout(connectSSE, 3000);
  };
}

connectSSE();
</script>
</body>
</html>
"""


# ════════════════════════════════════════════════════════════════════
# PYTHON IMPORTS
# ════════════════════════════════════════════════════════════════════

import sys, io, time, math, threading, logging, os, json, asyncio, uuid
import numpy as np
import pandas as pd
import requests
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
from typing import AsyncGenerator

try:
    from dotenv import load_dotenv; load_dotenv()
except ImportError:
    pass

try:
    from fastapi import FastAPI, Response
    from fastapi.responses import HTMLResponse, StreamingResponse
    import uvicorn
except ImportError:
    print("Missing: pip install fastapi uvicorn")
    sys.exit(1)

try:
    import upstox_client
except ImportError:
    print("Missing: pip install upstox-python-sdk"); sys.exit(1)


# ════════════════════════════════════════════════════════════════════
# GLOBALS — shared between bot thread and FastAPI
# ════════════════════════════════════════════════════════════════════

IST = timezone(timedelta(hours=5, minutes=30))

def now_ist() -> datetime:
    return datetime.now(IST).replace(tzinfo=None)

_log_handlers = [logging.StreamHandler(sys.stdout)]
try:
    _log_handlers.append(logging.FileHandler("nse_tick_bot.log", encoding="utf-8"))
except Exception:
    pass  # Railway filesystem may be read-only — stdout only is fine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=_log_handlers,
)
logger = logging.getLogger(__name__)
logging.getLogger("upstox_client").setLevel(logging.WARNING)

# In-memory store (thread-safe via lock)
_store_lock   = threading.Lock()
_signals_db   : list  = []          # list of signal dicts (newest first)
_ticks_db     : dict  = {}          # key → tick dict
_bot_status   : dict  = {"connected": False, "tick_count": 0,
                          "last_tick_ts": 0, "instruments_ready": 0,
                          "started_at": None}

# SSE subscriber queues  (asyncio.Queue, one per connected client)
_sse_queues : list = []
_sse_lock   = threading.Lock()


# ════════════════════════════════════════════════════════════════════
# SSE BROADCASTER  (called from bot thread → puts into asyncio queues)
# ════════════════════════════════════════════════════════════════════

def _sse_broadcast(event: str, data: dict):
    msg = f"event: {event}\ndata: {json.dumps(data)}\n\n"
    with _sse_lock:
        dead = []
        for q in _sse_queues:
            try:
                q.put_nowait(msg)
            except Exception:
                dead.append(q)
        for q in dead:
            _sse_queues.remove(q)


# ════════════════════════════════════════════════════════════════════
# DASHBOARD STORE WRITES  (bot → store + broadcast)
# ════════════════════════════════════════════════════════════════════

def store_status(**kwargs):
    with _store_lock:
        _bot_status.update(kwargs)
    _sse_broadcast("status", dict(_bot_status))

def store_signal(name, signal, bar_ts, trend_power, candle_trend, value_zone):
    entry = {
        "id":           str(uuid.uuid4()),
        "name":         name,
        "signal":       signal,
        "bar_ts":       str(bar_ts),
        "trend_power":  trend_power,
        "candle_trend": candle_trend,
        "value_zone":   value_zone,
    }
    with _store_lock:
        _signals_db.insert(0, entry)
        if len(_signals_db) > 500:
            del _signals_db[500:]
    _sse_broadcast("signal", entry)

def store_tick(key: str, name: str, ltp: float, ltt_ms: int):
    entry = {"key": key, "name": name, "ltp": ltp, "ltt": ltt_ms}
    with _store_lock:
        _ticks_db[key] = entry
    _sse_broadcast("tick", entry)


# Global bot instance (set once bot starts — used by token-update endpoint)
_bot_instance = None
_bot_lock = threading.Lock()


# ════════════════════════════════════════════════════════════════════
# FASTAPI APP
# ════════════════════════════════════════════════════════════════════

app = FastAPI(title="NSE Tick Bot Dashboard")


@app.get("/", response_class=HTMLResponse)
async def root():
    return DASHBOARD_HTML


@app.get("/api/signals")
async def get_signals():
    with _store_lock:
        return list(_signals_db)


@app.get("/api/ticks")
async def get_ticks():
    with _store_lock:
        return list(_ticks_db.values())


@app.get("/api/bot/status")
async def get_status():
    with _store_lock:
        return dict(_bot_status)


@app.post("/api/bot/signal")
async def post_signal_endpoint(payload: dict):
    store_signal(
        payload.get("name", ""),
        payload.get("signal", ""),
        payload.get("bar_ts", ""),
        payload.get("trend_power", ""),
        payload.get("candle_trend", ""),
        payload.get("value_zone", ""),
    )
    return {"ok": True}


@app.post("/api/bot/status")
async def post_status_endpoint(payload: dict):
    store_status(**payload)
    return {"ok": True}


@app.post("/api/bot/tick")
async def post_tick_endpoint(payload: dict):
    store_tick(
        payload.get("key", ""),
        payload.get("name", ""),
        float(payload.get("ltp", 0)),
        int(payload.get("ltt", 0)),
    )
    return {"ok": True}


@app.post("/api/update-token")
async def update_token(payload: dict):
    """
    Update Upstox access token without restarting the server.
    Protected by ADMIN_SECRET env var.

    Usage:
      curl -X POST https://your-app.railway.app/api/update-token \
           -H "Content-Type: application/json" \
           -d '{"admin_secret": "YOUR_ADMIN_SECRET", "token": "NEW_UPSTOX_TOKEN"}'
    """
    admin_secret = os.getenv("ADMIN_SECRET", "")
    if not admin_secret:
        return {"ok": False, "error": "ADMIN_SECRET not configured on server"}
    if payload.get("admin_secret") != admin_secret:
        return {"ok": False, "error": "Invalid admin secret"}

    new_token = (payload.get("token") or "").strip()
    if not new_token:
        return {"ok": False, "error": "token field is empty"}

    # Update env var in process memory
    os.environ["UPSTOX_ACCESS_TOKEN"] = new_token

    # Hot-reload the bot's token and reconnect WebSocket
    with _bot_lock:
        if _bot_instance is not None:
            _bot_instance.access_token = new_token
            logger.info("Token updated via API — reconnecting WebSocket...")
            try:
                if _bot_instance.streamer:
                    _bot_instance.streamer.disconnect()
            except Exception:
                pass
            # Reconnect in background so API returns immediately
            def _reconnect():
                import time as _time
                _time.sleep(2)
                _bot_instance.start_streamer()
            threading.Thread(target=_reconnect, daemon=True).start()
            return {"ok": True, "message": "Token updated and WebSocket reconnecting"}
        else:
            return {"ok": True, "message": "Token saved — bot not running yet"}


@app.get("/api/events")
async def sse_stream(response: Response):
    """Server-Sent Events stream: sends init snapshot, then live events."""

    queue: asyncio.Queue = asyncio.Queue(maxsize=500)
    with _sse_lock:
        _sse_queues.append(queue)

    async def generator() -> AsyncGenerator[str, None]:
        # ── Initial snapshot ──────────────────────────────────────
        with _store_lock:
            init_payload = {
                "signals": list(_signals_db),
                "status":  dict(_bot_status),
                "ticks":   list(_ticks_db.values()),
            }
        yield f"event: init\ndata: {json.dumps(init_payload)}\n\n"

        # ── Live events ───────────────────────────────────────────
        try:
            while True:
                try:
                    msg = await asyncio.wait_for(queue.get(), timeout=25)
                    yield msg
                except asyncio.TimeoutError:
                    yield ": heartbeat\n\n"   # keep-alive
        except asyncio.CancelledError:
            pass
        finally:
            with _sse_lock:
                if queue in _sse_queues:
                    _sse_queues.remove(queue)

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control":    "no-cache",
            "X-Accel-Buffering": "no",
            "Connection":       "keep-alive",
        },
    )


# ════════════════════════════════════════════════════════════════════
# TICK BOT
# ════════════════════════════════════════════════════════════════════

class UpstoxTickBot:
    """
    NSE Signal Bot — Upstox LTPC tick mode.
    Builds 1-min bars from raw ticks → 3-min bars → HA + Supertrend + ADX + VWAP.
    Zero candle delay: signals fire at exact 3-min bar close.
    """

    WATCHLIST = [
        {"name": "PAGEIND",       "key": "NSE_EQ|INE761H01022"},
        {"name": "SHREECEM",      "key": "NSE_EQ|INE070A01015"},
        {"name": "MARUTI",        "key": "NSE_EQ|INE585B01010"},
        {"name": "SOLARINDS",     "key": "NSE_EQ|INE343H01029"},
        {"name": "PAYTM",         "key": "NSE_EQ|INE982J01020"},
        {"name": "BOSCHLTD",      "key": "NSE_EQ|INE323A01026"},
        {"name": "DIXON",         "key": "NSE_EQ|INE935N01020"},
        {"name": "ULTRACEMCO",    "key": "NSE_EQ|INE481G01011"},
        {"name": "JIOFIN",        "key": "NSE_EQ|INE758T01015"},
        {"name": "OFSS",          "key": "NSE_EQ|INE881D01027"},
        {"name": "POLYCAB",       "key": "NSE_EQ|INE455K01017"},
        {"name": "ABB",           "key": "NSE_EQ|INE117A01022"},
        {"name": "DIVISLAB",      "key": "NSE_EQ|INE361B01024"},
        {"name": "NIFTY 50",      "key": "NSE_INDEX|Nifty 50"},
        {"name": "BANK NIFTY",    "key": "NSE_INDEX|Nifty Bank"},
        {"name": "SENSEX",        "key": "BSE_INDEX|SENSEX"},
        {"name": "FIN NIFTY",     "key": "NSE_INDEX|Nifty Fin Service"},
        {"name": "MIDCAP SELECT", "key": "NSE_INDEX|NIFTY MID SELECT"},
    ]

    def __init__(self):
        self.access_token      = os.getenv("UPSTOX_ACCESS_TOKEN", "")
        self.telegram_token    = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.chat_ids          = [c.strip() for c in os.getenv("CHAT_IDS", "").split(",") if c.strip()]

        self.atr_period  = int(os.getenv("ATR_PERIOD", 10))
        self.multiplier  = float(os.getenv("MULTIPLIER", 3.0))
        self.adx_len     = int(os.getenv("ADX_LEN",     14))
        self.ema_htf     = int(os.getenv("EMA_HTF",     20))
        self.n_bars      = int(os.getenv("N_BARS",    1000))

        self.key_to_info     = {s["key"]: s for s in self.WATCHLIST}
        self.market_open_min = 9 * 60 + 15

        # Per-instrument state
        self.history_3min = {}     # key → DataFrame
        self.last_fired   = {}     # key → Timestamp of last signal bar
        self.bar_buffer   = {}     # key → {3-min bar_open → agg dict}
        self.tick_bar     = {}     # key → current live 1-min bar dict | None
        self.locks        = {s["key"]: threading.Lock() for s in self.WATCHLIST}

        self.ws_state     = {"connected": False, "last_tick_ts": 0.0, "tick_count": 0}
        self.streamer     = None

        self._sig_exec    = ThreadPoolExecutor(max_workers=18, thread_name_prefix="sig")
        self._htf_cache   = {}
        self._htf_lock    = threading.Lock()

    # ── Market hours ─────────────────────────────────────────────

    def is_market_open(self) -> bool:
        n = now_ist()
        if n.weekday() >= 5: return False
        return (9, 15) <= (n.hour, n.minute) < (15, 30)

    def next_open_str(self) -> str:
        n = now_ist(); wd, hm = n.weekday(), (n.hour, n.minute)
        if wd >= 5 or (wd == 4 and hm >= (15, 30)):
            days = (7 - wd) % 7 or 7
            return f"Monday {(n + timedelta(days=days)).strftime('%d %b')} 09:15 IST"
        return "Tomorrow 09:15 IST" if hm >= (15, 30) else "soon"

    def get_3min_bar_open(self, ts: datetime):
        total = ts.hour * 60 + ts.minute
        since = total - self.market_open_min
        if since < 0: return None
        bm = self.market_open_min + (since // 3) * 3
        return ts.replace(hour=bm // 60, minute=bm % 60, second=0, microsecond=0)

    # ── Telegram ──────────────────────────────────────────────────

    def _send_telegram(self, msg: str):
        def _send():
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            for cid in self.chat_ids:
                try:
                    requests.post(url, data={"chat_id": cid, "text": msg,
                                             "parse_mode": "HTML"}, timeout=10)
                except Exception:
                    pass
        threading.Thread(target=_send, daemon=True).start()

    def _validate_telegram(self) -> bool:
        if not self.telegram_token:
            logger.info("  TELEGRAM_BOT_TOKEN not set — Telegram disabled")
            return False
        try:
            r = requests.get(f"https://api.telegram.org/bot{self.telegram_token}/getMe", timeout=10)
            if r.status_code == 200:
                bot = r.json().get("result", {})
                logger.info(f"  ✅ Telegram bot: @{bot.get('username','?')}")
                return True
            logger.warning(f"  ⚠️ Telegram token invalid ({r.status_code})")
            return False
        except Exception as e:
            logger.warning(f"  ⚠️ Telegram error: {e}")
            return False

    def send_signal(self, name, signal, bar_ts, trend_power, candle_trend, value_zone):
        # Store + broadcast via SSE
        store_signal(name, signal, bar_ts, trend_power, candle_trend, value_zone)

        # Telegram
        if signal == "BUY CALL":
            header = f"🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢\n📈  <b>{name}</b>\n⬆️  <b>BUY CALL</b>\n🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢"
        else:
            header = f"🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴\n📉  <b>{name}</b>\n⬇️  <b>BUY PUT</b>\n🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴"
        pi = "💪" if trend_power == "Strong" else "⚡" if trend_power == "Moderate" else "⚠️"
        ci = "🟢" if candle_trend == "Bullish" else "🔴" if candle_trend == "Bearish" else "⚪"
        zi = "🟢" if value_zone  == "Bullish" else "🔴" if value_zone  == "Bearish" else "⚪"
        try:   ts_str = pd.Timestamp(bar_ts).strftime("%H:%M  %d %b %Y")
        except: ts_str = str(bar_ts)[:16]

        fi = "🟢" if signal == "BUY CALL" else "🔴"
        self._send_telegram(
            f"{header}\n\n"
            f"{fi}  Trend Flip   : <b>{'Bullish' if signal=='BUY CALL' else 'Bearish'}</b>\n"
            f"{pi}  Trend Power  : <b>{trend_power}</b>\n"
            f"{ci}  Candle Trend : <b>{candle_trend}</b>\n"
            f"{zi}  Value Zone   : <b>{value_zone}</b>\n\n"
            f"🕒  <b>{ts_str}</b>\n"
            f"<i>Built from ticks — no candle delay</i>"
        )
        icon = "▲" if signal == "BUY CALL" else "▼"
        logger.info(f"  {icon} {name:15s} | {signal:8s} | {ts_str} | {trend_power} | {candle_trend} | {value_zone}")

    # ── Indicators ────────────────────────────────────────────────

    def to_heikin_ashi(self, df: pd.DataFrame) -> pd.DataFrame:
        o=df["open"].values.astype(float); h=df["high"].values.astype(float)
        l=df["low"].values.astype(float);  c=df["close"].values.astype(float)
        n = len(df)
        ha_o=np.empty(n); ha_c=np.empty(n); ha_h=np.empty(n); ha_l=np.empty(n)
        ha_o[0]=(o[0]+c[0])/2; ha_c[0]=(o[0]+h[0]+l[0]+c[0])/4
        ha_h[0]=max(h[0],ha_o[0],ha_c[0]); ha_l[0]=min(l[0],ha_o[0],ha_c[0])
        for i in range(1, n):
            ha_o[i]=(ha_o[i-1]+ha_c[i-1])/2; ha_c[i]=(o[i]+h[i]+l[i]+c[i])/4
            ha_h[i]=max(h[i],ha_o[i],ha_c[i]); ha_l[i]=min(l[i],ha_o[i],ha_c[i])
        out=df.copy(); out["open"]=ha_o; out["high"]=ha_h; out["low"]=ha_l; out["close"]=ha_c
        return out

    def wilder_rma(self, series: pd.Series, period: int) -> pd.Series:
        vals=series.values.astype(float); res=np.full(len(vals), np.nan)
        nz=np.where(~np.isnan(vals))[0]
        if len(nz)==0 or nz[0]+period>len(vals): return pd.Series(res, index=series.index)
        idx=nz[0]; res[idx+period-1]=np.nanmean(vals[idx:idx+period]); a=1.0/period
        for i in range(idx+period, len(vals)): res[i]=a*vals[i]+(1-a)*res[i-1]
        return pd.Series(res, index=series.index)

    def calc_supertrend(self, df: pd.DataFrame) -> np.ndarray:
        hl2=(df["high"]+df["low"])/2; pc=df["close"].shift(1)
        tr=pd.concat([df["high"]-df["low"],(df["high"]-pc).abs(),(df["low"]-pc).abs()],axis=1).max(axis=1)
        atr=self.wilder_rma(tr, self.atr_period)
        upper=(hl2+self.multiplier*atr).values; lower=(hl2-self.multiplier*atr).values
        cl=df["close"].values; n=len(df)
        up=np.full(n,np.nan); lo=np.full(n,np.nan); di=np.full(n,np.nan)
        for i in range(n):
            if np.isnan(atr.iloc[i]): continue
            if i==0 or np.isnan(di[i-1]):
                up[i]=upper[i]; lo[i]=lower[i]; di[i]=1; continue
            lo[i]=lower[i] if (lower[i]>lo[i-1] or cl[i-1]<lo[i-1]) else lo[i-1]
            up[i]=upper[i] if (upper[i]<up[i-1] or cl[i-1]>up[i-1]) else up[i-1]
            if di[i-1]==1:  di[i]=-1 if cl[i]>up[i-1] else 1
            else:           di[i]= 1 if cl[i]<lo[i-1] else -1
        return di

    def calc_adx(self, df_ha: pd.DataFrame) -> float:
        try:
            h=df_ha["high"].values.astype(float); l=df_ha["low"].values.astype(float)
            c=df_ha["close"].values.astype(float); n=len(df_ha)
            if n < self.adx_len*2+5: return 0.0
            dmp=np.zeros(n); dmm=np.zeros(n); tr=np.zeros(n)
            for i in range(1, n):
                up=h[i]-h[i-1]; dn=l[i-1]-l[i]
                dmp[i]=up if (up>dn and up>0) else 0
                dmm[i]=dn if (dn>up and dn>0) else 0
                tr[i]=max(h[i]-l[i], abs(h[i]-c[i-1]), abs(l[i]-c[i-1]))
            tr_s=self.wilder_rma(pd.Series(tr), self.adx_len)
            pdi=100*self.wilder_rma(pd.Series(dmp), self.adx_len)/tr_s.replace(0, np.nan)
            mdi=100*self.wilder_rma(pd.Series(dmm), self.adx_len)/tr_s.replace(0, np.nan)
            dx=100*(pdi-mdi).abs()/(pdi+mdi).replace(0, np.nan)
            adx=self.wilder_rma(dx, self.adx_len); val=float(adx.iloc[-1])
            return val if not np.isnan(val) else 0.0
        except Exception:
            return 0.0

    def calc_vwap(self, df: pd.DataFrame) -> float:
        try:
            if "volume" not in df.columns: return float("nan")
            td=df[df.index.date==df.index[-1].date()]
            if td.empty or td["volume"].sum()==0: return float("nan")
            tp=(td["high"]+td["low"]+td["close"])/3
            return float((tp*td["volume"]).sum()/td["volume"].sum())
        except Exception:
            return float("nan")

    # ── HTF bias (EMA-20 based, refreshed every 3 min) ───────────

    def _refresh_htf_all(self):
        for info in self.WATCHLIST:
            key = info["key"]
            hist = self.history_3min.get(key)
            if hist is None or len(hist) < self.ema_htf + 2: continue
            try:
                ema = hist["close"].ewm(span=self.ema_htf, adjust=False).mean()
                bias = "Bullish" if float(hist["close"].iloc[-1]) > float(ema.iloc[-1]) else "Bearish"
                with self._htf_lock:
                    self._htf_cache[key] = bias
            except Exception:
                pass

    def _htf_loop(self):
        while True:
            try: self._refresh_htf_all()
            except Exception as e: logger.warning(f"HTF: {e}")
            time.sleep(180)

    def get_htf_bias(self, key: str) -> str:
        with self._htf_lock:
            return self._htf_cache.get(key, "Unknown")

    # ── Tick processing ───────────────────────────────────────────

    def _on_tick(self, key: str, ltp: float, ltt_ms: int, ltq: float):
        if ltp <= 0: return
        info = self.key_to_info.get(key, {})
        lock = self.locks.get(key)
        if not lock or not lock.acquire(timeout=2): return

        released_early = False
        try:
            tick_dt = (
                datetime.fromtimestamp(ltt_ms / 1000.0, tz=timezone.utc)
                .astimezone(IST).replace(tzinfo=None, second=0, microsecond=0)
            )
            tb = self.tick_bar.get(key)

            if tb is None:
                self.tick_bar[key] = {"bar_open": tick_dt, "open": ltp, "high": ltp,
                                       "low": ltp, "close": ltp, "volume": ltq}
                return

            if tick_dt == tb["bar_open"]:
                tb["high"]    = max(tb["high"], ltp)
                tb["low"]     = min(tb["low"],  ltp)
                tb["close"]   = ltp
                tb["volume"] += ltq
                # throttled tick post every 5th tick
                if self.ws_state["tick_count"] % 5 == 0:
                    store_tick(key, info.get("name", key), ltp, ltt_ms)
            else:
                # 1-min bar just closed — release lock before spawning
                closed = dict(tb)
                self.tick_bar[key] = {"bar_open": tick_dt, "open": ltp, "high": ltp,
                                       "low": ltp, "close": ltp, "volume": ltq}
                lock.release()
                released_early = True

                store_tick(key, info.get("name", key), ltp, ltt_ms)
                bar = {"ts": closed["bar_open"], "open": closed["open"],
                       "high": closed["high"],   "low": closed["low"],
                       "close": closed["close"],  "volume": closed["volume"]}
                self._sig_exec.submit(self._process_1min_bar, key, bar)

        except Exception as e:
            logger.exception(f"Tick error [{key}]: {e}")
        finally:
            if not released_early:
                try: lock.release()
                except Exception: pass

    def _process_1min_bar(self, key: str, bar: dict):
        info = self.key_to_info.get(key)
        if not info or key not in self.history_3min: return

        lock = self.locks.get(key)
        if not lock or not lock.acquire(timeout=3): return

        signal = bar_ts = None
        entry = adx_val = vwap_val = 0.0
        name = ""

        try:
            ts = bar["ts"]
            bt = self.get_3min_bar_open(ts)
            if bt is None: return

            today = now_ist().date()
            buf   = self.bar_buffer.setdefault(key, {})
            for stale in [k for k in list(buf) if k.date() < today]:
                del buf[stale]

            if bt not in buf:
                buf[bt] = {"open": bar["open"], "high": bar["high"],
                           "low": bar["low"],   "close": bar["close"],
                           "volume": bar.get("volume", 0.0), "_cnt": 1}
            else:
                b = buf[bt]
                b["high"]    = max(b["high"], bar["high"])
                b["low"]     = min(b["low"],  bar["low"])
                b["close"]   = bar["close"]
                b["volume"] += bar.get("volume", 0.0)
                b["_cnt"]   += 1

            b = buf[bt]
            if b["_cnt"] < 3: return          # need all 3 × 1-min bars

            bar_ts = bt
            if self.last_fired.get(key) == bar_ts: return
            del buf[bt]

            new_row = pd.DataFrame(
                [{"open": b["open"], "high": b["high"],
                  "low": b["low"],   "close": b["close"], "volume": b["volume"]}],
                index=[pd.Timestamp(bar_ts)]
            )
            hist = self.history_3min[key]
            hist = pd.concat([hist, new_row])
            hist = hist[~hist.index.duplicated(keep="last")].sort_index()
            if len(hist) > self.n_bars: hist = hist.iloc[-self.n_bars:]
            self.history_3min[key] = hist

            df_ha    = self.to_heikin_ashi(hist)
            direction = self.calc_supertrend(df_ha)

            if len(direction) < 2:
                self.last_fired[key] = bar_ts; return
            curr = int(direction[-1]); prev = int(direction[-2])

            if   curr == -1 and prev ==  1: signal = "BUY CALL"
            elif curr ==  1 and prev == -1: signal = "BUY PUT"
            else:
                self.last_fired[key] = bar_ts; return

            self.last_fired[key] = bar_ts
            entry    = float(hist["close"].iloc[-1])
            adx_val  = self.calc_adx(df_ha)
            vwap_val = self.calc_vwap(hist)
            name     = info["name"]

        except Exception:
            logger.exception(f"Bar error [{info.get('name', key)}]"); return
        finally:
            lock.release()

        if not signal: return

        trend_power  = "Strong" if adx_val > 25 else "Moderate" if adx_val > 18 else "Weak"
        candle_trend = self.get_htf_bias(key)

        if math.isnan(vwap_val):
            hr = self.history_3min.get(key, pd.DataFrame())
            value_zone = ("Bullish" if entry > float(hr["close"].iloc[-2]) else "Bearish") \
                         if len(hr) >= 2 else "N/A"
        else:
            value_zone = "Bullish" if entry > vwap_val else "Bearish"

        self.send_signal(name, signal, bar_ts, trend_power, candle_trend, value_zone)

    # ── WebSocket ─────────────────────────────────────────────────

    def _parse_ltpc(self, message: dict):
        feeds = message.get("feeds", {})
        if not feeds: return
        for key, feed_data in feeds.items():
            ltpc = None
            for wrapper in (None, "ff", "fullFeed"):
                try:
                    if wrapper is None:
                        ltpc = feed_data.get("ltpc")
                    else:
                        for sub in ("marketFF", "indexFF"):
                            d = feed_data.get(wrapper, {}).get(sub, {}).get("ltpc")
                            if d: ltpc = d; break
                    if ltpc: break
                except Exception:
                    pass
            if not ltpc: continue
            try:
                ltp    = float(ltpc.get("ltp", 0) or 0)
                ltt_ms = int(ltpc.get("ltt", 0)   or 0)
                ltq    = float(ltpc.get("ltq", 0)  or 0)
            except Exception:
                continue
            if ltp <= 0 or ltt_ms == 0: continue
            if not self.is_market_open(): continue
            self.ws_state["last_tick_ts"] = time.time()
            self.ws_state["tick_count"] += 1
            self._sig_exec.submit(self._on_tick, key, ltp, ltt_ms, ltq)

    def start_streamer(self) -> bool:
        logger.info("Connecting Upstox V3 WebSocket (LTPC mode)…")

        def on_open(*_):
            self.ws_state["connected"] = True
            self.tick_bar.clear()
            keys = list(self.history_3min.keys())
            try:
                self.streamer.subscribe(keys, "ltpc")
                logger.info(f"  ✅ Subscribed {len(keys)} instruments [{now_ist():%H:%M:%S}]")
                store_status(connected=True, instruments_ready=len(keys),
                             tick_count=self.ws_state["tick_count"],
                             started_at=now_ist().isoformat())
            except Exception as e:
                logger.error(f"  ❌ Subscribe: {e}")

        def on_message(msg):
            try: self._parse_ltpc(msg)
            except Exception: pass

        def on_error(msg):
            logger.error(f"  WS error: {msg}")
            self.ws_state["connected"] = False
            store_status(connected=False, tick_count=self.ws_state["tick_count"])

        def on_close(*_):
            self.ws_state["connected"] = False
            logger.info(f"  WS closed [{now_ist():%H:%M:%S}] — reconnecting…")
            store_status(connected=False, tick_count=self.ws_state["tick_count"])

        try:
            cfg = upstox_client.Configuration()
            cfg.access_token = self.access_token
            self.streamer = upstox_client.MarketDataStreamerV3(upstox_client.ApiClient(cfg))
            self.streamer.on("open",    on_open)
            self.streamer.on("message", on_message)
            self.streamer.on("error",   on_error)
            self.streamer.on("close",   on_close)
            try: self.streamer.auto_reconnect(True, 5, 20)
            except Exception: pass
            self.streamer.connect()
            return True
        except Exception as e:
            logger.error(f"  Streamer failed: {e}"); return False

    # ── History (Upstox REST) ─────────────────────────────────────

    def load_all_history(self) -> bool:
        logger.info(f"Loading 3-min history for {len(self.WATCHLIST)} instruments…")
        headers  = {"Authorization": f"Bearer {self.access_token}", "Accept": "application/json"}
        today    = now_ist().date()

        # Find last real trading day — skip weekends AND market holidays (e.g. Holi).
        # Try up to 10 days back using NIFTY 50 as probe until we get HTTP 200.
        probe_key = requests.utils.quote("NSE_INDEX|Nifty 50", safe="")
        last_trading_day = today
        while last_trading_day.weekday() >= 5:       # skip Sat/Sun first
            last_trading_day -= timedelta(days=1)

        for _ in range(10):                          # then probe for holidays
            probe_to   = last_trading_day.strftime("%Y-%m-%d")
            probe_from = (last_trading_day - timedelta(days=5)).strftime("%Y-%m-%d")
            try:
                probe_url = (f"https://api.upstox.com/v2/historical-candle"
                             f"/{probe_key}/3minute/{probe_to}/{probe_from}")
                pr = requests.get(probe_url, headers=headers, timeout=10)
                if pr.status_code == 200 and pr.json().get("data", {}).get("candles"):
                    break   # found a real trading day
            except Exception:
                pass
            last_trading_day -= timedelta(days=1)
            while last_trading_day.weekday() >= 5:   # skip weekends while stepping back
                last_trading_day -= timedelta(days=1)

        to_date   = last_trading_day.strftime("%Y-%m-%d")
        from_date = (last_trading_day - timedelta(days=60)).strftime("%Y-%m-%d")
        logger.info(f"  Last trading day: {to_date}  |  history from: {from_date}")
        loaded   = 0

        for info in self.WATCHLIST:
            key = info["key"]
            enc = requests.utils.quote(key, safe="")
            url = (f"https://api.upstox.com/v2/historical-candle"
                   f"/{enc}/3minute/{to_date}/{from_date}")
            try:
                r = requests.get(url, headers=headers, timeout=15)
                if r.status_code == 200:
                    candles = r.json().get("data", {}).get("candles", [])
                    if candles:
                        df = pd.DataFrame(candles,
                                          columns=["ts","open","high","low","close","volume","oi"])
                        df["ts"] = pd.to_datetime(df["ts"])
                        df = df.set_index("ts").sort_index()
                        df = df[["open","high","low","close","volume"]].astype(float)
                        df = df[~df.index.duplicated(keep="last")]
                        self.history_3min[key] = df
                        logger.info(f"  ✅ [{info['name']:15s}] {len(df)} bars")
                    else:
                        logger.warning(f"  ⚠️  [{info['name']}] empty — using dummy")
                        self._seed_dummy(key)
                else:
                    logger.warning(f"  ⚠️  [{info['name']}] HTTP {r.status_code} — using dummy")
                    self._seed_dummy(key)
            except Exception as e:
                logger.warning(f"  ⚠️  [{info['name']}] {e} — using dummy")
                self._seed_dummy(key)

            self.bar_buffer[key] = {}
            self.tick_bar[key]   = None
            loaded += 1
            time.sleep(0.3)

        logger.info(f"\n✅ {loaded}/{len(self.WATCHLIST)} instruments ready.\n")
        return loaded > 0

    def _seed_dummy(self, key: str):
        now   = now_ist()
        dates = pd.date_range(end=now, periods=50, freq="3min")
        base  = 100.0
        opens = np.random.uniform(base*.99, base*1.01, 50)
        highs = opens + np.random.uniform(.1, 1., 50)
        lows  = opens - np.random.uniform(.1, 1., 50)
        closes= opens + np.random.uniform(-.5, .5, 50)
        self.history_3min[key] = pd.DataFrame(
            {"open": opens, "high": highs, "low": lows,
             "close": closes, "volume": np.ones(50)*1000}, index=dates)

    # ── Main bot loop ─────────────────────────────────────────────

    def start(self):
        logger.info("=" * 66)
        logger.info("  NSE TICK BOT — Zero Delay Signal System")
        logger.info(f"  Supertrend({self.atr_period},{self.multiplier}) · HA · 3-min from ticks")
        logger.info(f"  Dashboard → http://localhost:8000")
        logger.info("=" * 66)

        if not self.access_token:
            logger.error("UPSTOX_ACCESS_TOKEN env var not set."); return

        # Validate Upstox token
        logger.info("Validating Upstox token…")
        try:
            r = requests.get("https://api.upstox.com/v2/user/profile",
                             headers={"Authorization": f"Bearer {self.access_token}",
                                      "Accept": "application/json"}, timeout=10)
            if r.status_code == 200:
                u = r.json().get("data", {})
                logger.info(f"  ✅ {u.get('user_name','')} ({u.get('email','')})")
            elif r.status_code == 401:
                logger.error("  ❌ Token expired — get a fresh token from developer.upstox.com")
                return
            else:
                logger.warning(f"  ⚠️  Profile {r.status_code}, continuing")
        except Exception as e:
            logger.warning(f"  Token check error: {e}, continuing")

        self._validate_telegram()

        if not self.load_all_history():
            logger.error("No history loaded."); return

        # HTF bias background thread
        threading.Thread(target=self._htf_loop, daemon=True).start()
        logger.info("  ✅ HTF bias cache active\n")

        store_status(connected=False, instruments_ready=len(self.history_3min),
                     tick_count=0, started_at=now_ist().isoformat())

        if not self.is_market_open():
            logger.info(f"Market closed — opens {self.next_open_str()}")
            while not self.is_market_open():
                time.sleep(30)
            logger.info("🟢 Market open!\n")

        if not self.start_streamer():
            logger.error("WebSocket failed."); return
        time.sleep(4)

        logger.info(f"⚡ Bot live! {len(self.history_3min)} instruments")
        logger.info("   Signal fires at exact 3-min bar close ✅")
        logger.info("   Press Ctrl+C to stop.\n")

        WATCHDOG     = 90
        last_cleanup = now_ist().date()

        try:
            while True:
                time.sleep(8)
                now = now_ist()

                # Daily cleanup after market close
                if now.date() != last_cleanup and now.hour >= 15 and now.minute >= 35:
                    logger.info("  🧹 Daily cleanup")
                    for k in list(self.bar_buffer): self.bar_buffer[k] = {}
                    self.tick_bar.clear(); last_cleanup = now.date()

                # Periodic status log
                if now.second < 8 and now.minute % 5 == 0:
                    st    = "OPEN" if self.is_market_open() else "CLOSED"
                    since = int(time.time()-self.ws_state["last_tick_ts"]) \
                            if self.ws_state["last_tick_ts"] > 0 else -1
                    logger.info(f"  [{st}] {now:%H:%M:%S} "
                                f"ticks={self.ws_state['tick_count']} last={since}s")
                    store_status(connected=self.ws_state["connected"],
                                 tick_count=self.ws_state["tick_count"],
                                 last_tick_ts=int(self.ws_state["last_tick_ts"]),
                                 instruments_ready=len(self.history_3min))

                # Watchdog reconnect
                if (self.is_market_open()
                        and self.ws_state["last_tick_ts"] > 0
                        and (time.time()-self.ws_state["last_tick_ts"]) > WATCHDOG):
                    logger.warning(f"  No ticks for {WATCHDOG}s — reconnecting…")
                    try:
                        if self.streamer: self.streamer.disconnect()
                    except Exception: pass
                    time.sleep(3); self.start_streamer(); time.sleep(4)
                    self.ws_state["last_tick_ts"] = time.time()

        except KeyboardInterrupt:
            logger.info("\nStopping…")
            if self.streamer:
                try: self.streamer.disconnect()
                except Exception: pass
            store_status(connected=False, tick_count=self.ws_state["tick_count"])
            self._send_telegram(f"🔴 Bot Offline\n⏰ {now_ist():%H:%M  %d %b %Y}")
            self._sig_exec.shutdown(wait=False)
            logger.info("Done.")


# ════════════════════════════════════════════════════════════════════
# ENTRY POINT — starts FastAPI + bot concurrently
# ════════════════════════════════════════════════════════════════════

def run_bot():
    """Bot runs in a background daemon thread."""
    global _bot_instance
    bot = UpstoxTickBot()
    with _bot_lock:
        _bot_instance = bot
    bot.start()


if __name__ == "__main__":
    PORT = int(os.getenv("PORT", 8000))
    HOST = "0.0.0.0"   # Railway requires 0.0.0.0 — never 127.0.0.1

    print(f"\n{'='*60}")
    print(f"  PORT      : {PORT}")
    print(f"  Dashboard : http://0.0.0.0:{PORT}")
    print(f"{'='*60}\n")

    # Start bot in background — AFTER printing so Railway sees output immediately
    bot_thread = threading.Thread(target=run_bot, daemon=True, name="UpstoxBot")
    bot_thread.start()

    # uvicorn starts immediately — dashboard is reachable even while
    # bot is loading history (which can take 30-60 seconds)
    uvicorn.run(
        app,
        host=HOST,
        port=PORT,
        log_level="info",
    )
