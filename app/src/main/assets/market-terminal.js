/* Aster Market Terminal — adapted from Grok's market-terminal patterns.
 * Keeps Aster's binary-trading controls and API untouched while upgrading
 * the market-data surface: candlesticks + volume, live ticker, depth and
 * recent trades. Public market data only; this file never places orders.
 */
(function () {
  'use strict';
  const LC = window.LightweightCharts;
  if (!LC) return;

  const REST = 'https://api.binance.com';
  const WS = 'wss://stream.binance.com:9443/ws';
  const intervals = ['1m', '5m', '15m', '1h', '4h', '1d'];
  const state = { symbol: 'BTCUSDT', interval: '1m', chart: null, candles: null, volume: null, socket: null, depthTimer: null, tradesTimer: null, tickerTimer: null, generation: 0 };
  const $ = (id) => document.getElementById(id);
  const fmt = (n, max = 2) => Number(n || 0).toLocaleString(undefined, { maximumFractionDigits: max });
  const qty = (n) => Number(n || 0).toLocaleString(undefined, { maximumFractionDigits: 4 });
  const time = (ms) => new Date(ms).toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
  const text = (id, value) => { const el = $(id); if (el) el.textContent = value; };

  function label(symbol) { return window.__ASTER_SYMBOLS__?.[symbol] || symbol.replace('USDT', '/USDT'); }
  function destroyChart() { if (state.chart) { try { state.chart.remove(); } catch (_) {} } state.chart = state.candles = state.volume = null; }
  function createChart() {
    const host = $('chart'); if (!host) return;
    host.innerHTML = '';
    state.chart = LC.createChart(host, {
      autoSize: true,
      layout: { background: { type: LC.ColorType.Solid, color: '#070808' }, textColor: '#8e918e', fontFamily: 'IBM Plex Mono, ui-monospace, monospace' },
      grid: { vertLines: { color: '#171818' }, horzLines: { color: '#171818' } },
      rightPriceScale: { borderColor: '#282828', scaleMargins: { top: 0.08, bottom: 0.24 } },
      timeScale: { borderColor: '#282828', timeVisible: true, secondsVisible: false },
      crosshair: { mode: LC.CrosshairMode.Normal },
    });
    state.candles = state.chart.addSeries(LC.CandlestickSeries, { upColor: '#20c77a', downColor: '#ef5555', borderUpColor: '#20c77a', borderDownColor: '#ef5555', wickUpColor: '#20c77a', wickDownColor: '#ef5555' });
    state.volume = state.chart.addSeries(LC.HistogramSeries, { priceFormat: { type: 'volume' }, priceScaleId: 'volume' });
    state.chart.priceScale('volume').applyOptions({ scaleMargins: { top: 0.80, bottom: 0 } });
  }
  async function json(url) { const r = await fetch(url, { headers: { Accept: 'application/json' } }); if (!r.ok) throw new Error('Market data unavailable'); return r.json(); }
  async function klines(symbol, interval) {
    const rows = await json(`${REST}/api/v3/klines?symbol=${encodeURIComponent(symbol)}&interval=${encodeURIComponent(interval)}&limit=240`);
    return Array.isArray(rows) ? rows.map(k => ({ time: Math.floor(Number(k[0]) / 1000), open: Number(k[1]), high: Number(k[2]), low: Number(k[3]), close: Number(k[4]), volume: Number(k[5]) })) : [];
  }
  function renderBook(data) {
    const asksHost = $('askRows'), bidsHost = $('bidRows'); if (!asksHost || !bidsHost) return;
    const asks = (data.asks || []).slice(0, 10).reverse(), bids = (data.bids || []).slice(0, 10);
    const max = Math.max(1, ...asks.map(x => Number(x[1])), ...bids.map(x => Number(x[1])));
    const row = (x, side) => { const p = Number(x[0]), a = Number(x[1]), w = Math.max(4, Math.min(100, a / max * 100)); return `<div class="terminal-book-row ${side}"><i style="width:${w}%"></i><span>${fmt(p, 2)}</span><span>${qty(a)}</span><span>${fmt(p * a, 2)}</span></div>`; };
    asksHost.innerHTML = asks.map(x => row(x, 'ask')).join(''); bidsHost.innerHTML = bids.map(x => row(x, 'bid')).join('');
    const ask = Number(data.asks?.[0]?.[0] || 0), bid = Number(data.bids?.[0]?.[0] || 0), mid = ask && bid ? (ask + bid) / 2 : 0, spread = mid ? ((ask - bid) / mid) * 100 : 0;
    text('bookMid', mid ? fmt(mid, 2) : '—'); text('bookSpread', spread ? `Spread ${spread.toFixed(3)}%` : '—');
  }
  function renderTrades(data) {
    const host = $('recentTradesRows'); if (!host) return;
    host.innerHTML = (Array.isArray(data) ? data : []).slice().reverse().slice(0, 28).map(t => `<div class="terminal-trade-row ${t.isBuyerMaker ? 'down' : 'up'}"><span>${fmt(Number(t.price), 2)}</span><span>${qty(Number(t.qty))}</span><span>${time(Number(t.time))}</span></div>`).join('');
  }
  async function depth(symbol, generation) { if (generation !== state.generation || symbol === 'XAUUSDT') return; try { const d = await json(`${REST}/api/v3/depth?symbol=${encodeURIComponent(symbol)}&limit=20`); if (generation === state.generation) renderBook(d); } catch (_) {} }
  async function trades(symbol, generation) { if (generation !== state.generation || symbol === 'XAUUSDT') return; try { const d = await json(`${REST}/api/v3/trades?symbol=${encodeURIComponent(symbol)}&limit=40`); if (generation === state.generation) renderTrades(d); } catch (_) {} }
  async function ticker(symbol, generation) {
    if (generation !== state.generation || symbol === 'XAUUSDT') return;
    try {
      const t = await json(`${REST}/api/v3/ticker/24hr?symbol=${encodeURIComponent(symbol)}`); if (generation !== state.generation) return;
      text('price', fmt(Number(t.lastPrice), 2)); const c = Number(t.priceChangePercent); text('marketChange', `${c >= 0 ? '+' : ''}${c.toFixed(2)}%`);
      const el = $('marketChange'); if (el) el.className = `status ${c >= 0 ? 'terminal-up' : 'terminal-down'}`;
      text('feed', 'LIVE');
    } catch (_) {}
  }
  function socket(symbol, interval, generation) {
    if (symbol === 'XAUUSDT') return;
    try {
      state.socket = new WebSocket(`${WS}/${symbol.toLowerCase()}@kline_${interval}`);
      state.socket.onopen = () => { if (generation === state.generation) text('feed', 'LIVE'); };
      state.socket.onmessage = (ev) => { if (generation !== state.generation) return; try { const k = JSON.parse(ev.data).k, b = { time: Math.floor(Number(k.t) / 1000), open: Number(k.o), high: Number(k.h), low: Number(k.l), close: Number(k.c) }; state.candles?.update(b); state.volume?.update({ time: b.time, value: Number(k.v), color: b.close >= b.open ? 'rgba(32,199,122,.42)' : 'rgba(239,85,85,.42)' }); text('price', fmt(b.close, 2)); } catch (_) {} };
      state.socket.onclose = () => { if (generation === state.generation) text('feed', 'RECONNECTING'); };
    } catch (_) { text('feed', 'UNAVAILABLE'); }
  }
  async function start(symbol) {
    const selectedInterval = document.querySelector('#periods button[data-i].sel')?.dataset.i;
    if (intervals.includes(selectedInterval)) state.interval = selectedInterval;
    state.symbol = symbol || 'BTCUSDT'; state.generation += 1; const g = state.generation;
    if (state.socket) { try { state.socket.close(); } catch (_) {} state.socket = null; }
    [state.depthTimer, state.tradesTimer, state.tickerTimer].forEach(x => x && clearInterval(x));
    text('pair', label(state.symbol)); text('marketChange', '—');
    if (state.symbol === 'XAUUSDT') { destroyChart(); createChart(); text('feed', 'PROVIDER REQUIRED'); text('price', '—'); return; }
    destroyChart(); createChart(); text('feed', 'LOADING');
    try {
      const bars = await klines(state.symbol, state.interval); if (g !== state.generation) return;
      state.candles.setData(bars.map(k => ({ time: k.time, open: k.open, high: k.high, low: k.low, close: k.close })));
      state.volume.setData(bars.map(k => ({ time: k.time, value: k.volume, color: k.close >= k.open ? 'rgba(32,199,122,.42)' : 'rgba(239,85,85,.42)' })));
      state.chart.timeScale().fitContent(); if (bars.length) text('price', fmt(bars[bars.length - 1].close, 2)); text('feed', 'LIVE');
      socket(state.symbol, state.interval, g); void depth(state.symbol, g); void trades(state.symbol, g); void ticker(state.symbol, g);
      state.depthTimer = setInterval(() => void depth(state.symbol, g), 2500); state.tradesTimer = setInterval(() => void trades(state.symbol, g), 2000); state.tickerTimer = setInterval(() => void ticker(state.symbol, g), 3000);
    } catch (_) { text('feed', 'UNAVAILABLE'); }
  }
  function upgradeMarkup() {
    const trade = document.querySelector('#trade .trade'); if (!trade || $('asterMarketTerminalStyles')) return;
    const style = document.createElement('style'); style.id = 'asterMarketTerminalStyles'; style.textContent = `
      .terminal-meta{display:flex;align-items:center;justify-content:space-between;margin:4px 0 8px}.terminal-up{color:#20c77a!important}.terminal-down{color:#ef5555!important}
      .terminal-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:12px}.terminal-panel{border:1px solid #222;border-radius:10px;background:#0a0b0b;padding:10px}.terminal-head{display:grid;grid-template-columns:1fr 1fr 1fr;color:#666;font-size:9px;text-transform:uppercase;letter-spacing:.08em;padding:0 4px 5px}.terminal-book{font:10px ui-monospace,monospace;min-height:184px;overflow:hidden}.terminal-book-row{position:relative;display:grid;grid-template-columns:1fr 1fr 1fr;padding:2px 4px;line-height:1.35;overflow:hidden}.terminal-book-row i{position:absolute;right:0;top:0;bottom:0;z-index:0;opacity:.16}.terminal-book-row span{position:relative;z-index:1}.terminal-book-row.ask span:first-of-type{color:#ef5555}.terminal-book-row.ask i{background:#ef5555}.terminal-book-row.bid span:first-of-type{color:#20c77a}.terminal-book-row.bid i{background:#20c77a}.terminal-mid{display:flex;justify-content:space-between;background:#101111;border-radius:7px;padding:5px 7px;margin:5px 0;color:#e8bd50;font:10px ui-monospace,monospace}.terminal-trades{max-height:180px;overflow:auto;font:10px ui-monospace,monospace}.terminal-trade-row{display:grid;grid-template-columns:1fr 1fr 1fr;padding:2px 4px}.terminal-trade-row span:nth-child(2),.terminal-trade-row span:nth-child(3){text-align:right}.terminal-trade-row.up span:first-child{color:#20c77a}.terminal-trade-row.down span:first-child{color:#ef5555}@media(max-width:520px){.terminal-grid{grid-template-columns:1fr}.terminal-trades{max-height:150px}}
    `; document.head.appendChild(style);
    const pair = trade.querySelector('.pair'); if (pair) pair.insertAdjacentHTML('afterend', '<div class="terminal-meta"><span class="muted">24h change</span><span id="marketChange" class="status">—</span></div>');
    const oldBook = trade.querySelector('.book'); if (oldBook) oldBook.outerHTML = `<div class="terminal-grid"><div class="terminal-panel"><div class="terminal-head"><span>Price</span><span style="text-align:right">Size</span><span style="text-align:right">Total</span></div><div id="askRows" class="terminal-book"></div><div class="terminal-mid"><span id="bookMid">—</span><span id="bookSpread" style="color:#777">—</span></div><div id="bidRows" class="terminal-book"></div></div><div class="terminal-panel"><div class="terminal-head"><span>Price</span><span style="text-align:right">Qty</span><span style="text-align:right">Time</span></div><div id="recentTradesRows" class="terminal-trades"></div></div></div>`;
    const notice = trade.querySelector('.notice'); if (notice) notice.textContent = 'Market terminal powered by public Binance data. HIGHER / LOWER remain Aster sandbox binary-trade controls; no spot order is placed by the market terminal.';
  }
  function install() {
    window.__ASTER_MARKET_TERMINAL__ = { start, state }; upgradeMarkup(); window.startMarket = start;
    void start(state.symbol);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', install, { once: true }); else install();
})();
