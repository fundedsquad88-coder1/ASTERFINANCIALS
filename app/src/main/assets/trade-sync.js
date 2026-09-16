(function(){
  function base(){return String(localStorage.getItem('aster_api_base')||'').replace(/\/$/,'')}
  function token(){return localStorage.getItem('aster_token')||''}
  async function call(path,options){const b=base();if(!b)throw Error('Set your backend URL in Profile first.');const o=Object.assign({},options||{});o.headers=Object.assign({'Content-Type':'application/json'},o.headers||{});if(token())o.headers.Authorization='Bearer '+token();const r=await fetch(b+path,o);const d=await r.json().catch(()=>({}));if(!r.ok)throw Error(d.error||'Request failed');return d}
  const oldPreview=window.previewTrade;
  window.previewTrade=async function(side){
    if(!token())return window.openAuth&&window.openAuth();
    const amount=Number(document.getElementById('amount')?.value), expiry=Number(document.getElementById('expiry')?.value);
    if(!(amount>0))return window.toast&&window.toast('Enter a valid amount.');
    const market=window.__asterActiveMarket||'BTCUSDT';
    try{
      let preview={};
      if(typeof oldPreview==='function'){
        // The existing preview performs the backend sandbox validation.
        await oldPreview(side);
      }
      preview=await call('/api/v1/trades/record',{method:'POST',body:JSON.stringify({market,direction:side,amount,expiry})});
      if(window.toast)window.toast(preview.message||'Sandbox trade recorded.');
      await sync();
    }catch(e){if(window.toast)window.toast(e.message)}
  };
  function fmt(ms){return new Date(ms).toLocaleString(undefined,{month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'})}
  function countdown(ms){if(ms<=0)return 'EXPIRED';const s=Math.ceil(ms/1000),m=Math.floor(s/60),r=s%60;return m?m+'m '+String(r).padStart(2,'0')+'s':r+'s'}
  function label(sym){const names={BTCUSDT:'BTC/USDT',ETHUSDT:'ETH/USDT',BNBUSDT:'BNB/USDT',XRPUSDT:'XRP/USDT',SOLUSDT:'SOL/USDT',TRXUSDT:'TRX/USDT',DOGEUSDT:'DOGE/USDT',LINKUSDT:'LINK/USDT',ADAUSDT:'ADA/USDT',LTCUSDT:'LTC/USDT',BCHUSDT:'BCH/USDT',AVAXUSDT:'AVAX/USDT',DOTUSDT:'DOT/USDT',UNIUSDT:'UNI/USDT',NEARUSDT:'NEAR/USDT',SUIUSDT:'SUI/USDT',SHIBUSDT:'SHIB/USDT',HBARUSDT:'HBAR/USDT',APTUSDT:'APT/USDT',ATOMUSDT:'ATOM/USDT',XAUUSDT:'XAU/USDT',XAGUSDT:'XAG/USDT',WTIUSDT:'WTI/USDT',BRENTUSDT:'BRENT/USDT'};return names[sym]||sym}
  function render(rows){const box=document.getElementById('tradeActivity');if(!box)return;const now=Date.now();const open=rows.filter(x=>x.status==='OPEN'&&Date.parse(x.expiresAt)>now);const history=rows.filter(x=>!(x.status==='OPEN'&&Date.parse(x.expiresAt)>now));box.innerHTML='<div class="head"><b>Trade activity</b><span class="muted">SERVER SYNC · SANDBOX</span></div><div class="tabs"><button id="openTradesTab" class="sel" onclick="window.tradeTab=\'open\';window.renderServerTrades()">Open ('+open.length+')</button><button id="tradeHistoryTab" onclick="window.tradeTab=\'history\';window.renderServerTrades()">History ('+history.length+')</button></div><div id="tradeActivityList"></div><p class="notice">Open trades and history are now read from the Aster backend database. They remain sandbox previews: no funds move and no real-money profit/loss is settled.</p>';window.__serverTrades=rows;window.renderServerTrades()}
  window.tradeTab='open';window.__serverTrades=[];
  window.renderServerTrades=function(){const list=document.getElementById('tradeActivityList');if(!list)return;const rows=window.__serverTrades||[],now=Date.now();const open=rows.filter(x=>x.status==='OPEN'&&Date.parse(x.expiresAt)>now),history=rows.filter(x=>!(x.status==='OPEN'&&Date.parse(x.expiresAt)>now));const data=window.tradeTab==='history'?history.slice(0,20):open;document.getElementById('openTradesTab')?.classList.toggle('sel',window.tradeTab==='open');document.getElementById('tradeHistoryTab')?.classList.toggle('sel',window.tradeTab==='history');if(!data.length){list.innerHTML='<div class="empty">No server-side sandbox trades here yet.</div>';return}list.innerHTML=data.map(x=>{const exp=Date.parse(x.expiresAt),isOpen=x.status==='OPEN'&&exp>now;return '<div class="listitem"><div><b>'+label(x.market)+'</b><br><span class="muted">'+x.direction+' · '+Number(x.amount).toFixed(2)+' USDT</span><br><span class="muted">'+fmt(Date.parse(x.openedAt))+'</span></div><div style="text-align:right"><b class="'+(x.direction==='HIGHER'?'status':'')+'">'+(isOpen?countdown(exp-now):(x.status==='OPEN'?'EXPIRED':x.status))+'</b><br><span class="muted">'+(isOpen?'OPEN':'HISTORY')+'</span></div></div>'}).join('')}
  async function sync(){if(!token())return;try{const d=await call('/api/v1/trades?status=ALL');render(d.trades||[])}catch(e){}}
  window.syncTradeActivity=sync;
  setInterval(()=>{if(document.getElementById('tradeActivity'))window.renderServerTrades()},1000);
  const oldShow=window.show;window.show=function(id){if(typeof oldShow==='function')oldShow(id);if(id==='trade')setTimeout(sync,250);};
  const oldStart=window.startMarket;if(typeof oldStart==='function')window.startMarket=function(sym){window.__asterActiveMarket=sym;return oldStart(sym)};
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',sync);else setTimeout(sync,400);
})();
