(function(){
if(window.__asterV24)return;window.__asterV24=1;
const $=(s,r=document)=>r.querySelector(s);
function addCss(){const l=document.createElement('link');l.rel='stylesheet';l.href='https://appassets.androidplatform.net/assets/v24-upgrade.css';document.head.appendChild(l)}
function visual(id,title,text,img){const el=document.getElementById(id);if(!el||el.querySelector('.v24-section-visual'))return;const v=document.createElement('div');v.className='v24-section-visual';v.style.backgroundImage='url("'+img+'")';v.innerHTML='<div class="v24-copy"><b>'+title+'</b><span>'+text+'</span></div>';el.appendChild(v)}
function trust(){const home=$('#home');if(!home||home.querySelector('.v24-trust'))return;const t=document.createElement('div');t.className='v24-trust';t.innerHTML='<div><b>Live data</b><span>Market context</span></div><div><b>Transparent</b><span>Clear projections</span></div><div><b>Account-first</b><span>No fake balances</span></div>';home.querySelector('.grid2')?.after(t)}
function marketMeta(){const m=$('#markets');if(!m||m.querySelector('.v24-market-meta'))return;const x=document.createElement('div');x.className='v24-market-meta';x.innerHTML='<span class="v24-meta-pill live">● Live market data</span><span class="v24-meta-pill">Crypto</span><span class="v24-meta-pill">Forex</span><span class="v24-meta-pill">Informational only</span>';$('#marketTabs')?.before(x)}
function stamp(){const m=$('#markets');if(!m)return;let e=$('#v24MarketUpdated');if(!e){e=document.createElement('span');e.id='v24MarketUpdated';e.className='small muted';m.querySelector('.section-head')?.appendChild(e)}e.textContent='Updated '+new Date().toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'})}
async function forex(){try{const url='https://api.frankfurter.dev/v1/latest?base=USD&symbols=EUR,GBP,JPY,AUD,CAD,CHF';const raw=await new Promise((resolve,reject)=>{const id='fx'+Date.now()+Math.random();window.__asterCallbacks=window.__asterCallbacks||{};window.__asterCallbacks[id]={resolve,reject};if(window.AsterNative)AsterNative.fetch(url,id);else fetch(url).then(r=>r.text()).then(resolve).catch(reject)});const rates=(JSON.parse(raw).rates)||{};Object.entries(rates).forEach(([ccy,rate])=>quotes['USD/'+ccy]={symbol:'USD/'+ccy,type:'forex',price:+rate,open:+rate});renderMarkets();renderTicker();stamp();const list=$('#marketList');if(!list)return;$('#v24ForexCard')?.remove();const fx=document.createElement('div');fx.id='v24ForexCard';fx.className='card';fx.style.margin='12px 0 0';fx.innerHTML='<div class="row"><b>Global FX</b><span class="badge">Live spot</span></div>'+Object.entries(rates).map(([c,r])=>'<div class="v24-forex"><div class="v24-flag">'+c+'</div><div><b>USD/'+c+'</b><div class="small muted">1 USD</div></div><div class="price">'+Number(r).toFixed(c==='JPY'?2:4)+'<div class="change muted">spot</div></div></div>').join('');list.parentNode.insertBefore(fx,list.nextSibling)}catch(e){console.warn('Aster Forex feed unavailable',e)}}
function boot(){addCss();visual('home','Global markets, beautifully simple.','Aster combines live market context with automated investing in one focused experience.','https://images.unsplash.com/photo-1521295121783-8a321d551ad2?auto=format&fit=crop&w=1400&q=82');visual('invest','Choose your strategy.','Crypto and global FX, presented with transparent assumptions before you activate anything.','https://images.unsplash.com/photo-1559526324-593bc073d938?auto=format&fit=crop&w=1400&q=82');visual('markets','See the world behind the numbers.','Live crypto quotes plus global FX spot rates — informational, not execution.','https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?auto=format&fit=crop&w=1400&q=82');visual('wallet','Your treasury, clearly.','Network-specific USDT deposit rails with clear status and transaction history.','https://images.unsplash.com/photo-1526304640581-d334cdbbf45e?auto=format&fit=crop&w=1400&q=82');visual('profile','Everything about your Aster account.','Security, referrals, preferences and legal information in one place.','https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=1400&q=82');trust();marketMeta();const originalLoad=window.loadMarkets;if(typeof originalLoad==='function'&&!window.__asterV24Wrapped){window.__asterV24Wrapped=true;window.loadMarkets=async function(){const result=await originalLoad();await forex();return result}}setTimeout(()=>window.loadMarkets?.(),250)}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot);else boot();
})();
/* Aster V25 — command center upgrade */
(function(){
if(window.__asterV25)return;window.__asterV25=1;
const $=(s,r=document)=>r.querySelector(s);
function homePulse(){
 const home=$('#home'); if(!home||home.querySelector('.v25-pulse'))return;
 const card=document.createElement('div'); card.className='card v25-pulse';
 card.innerHTML='<div class="v25-pulse-head"><div><span class="eyebrow">Aster pulse</span><b>Markets are moving</b></div><span class="v25-live"><i></i> LIVE</span></div>'+
 '<div class="v25-pulse-grid"><div><span>Crypto</span><b>Live quotes</b><small>Updated continuously when available</small></div><div><span>Global FX</span><b>Spot context</b><small>Reference rates, not execution</small></div><div><span>Auto-Invest</span><b>Strategy first</b><small>Review assumptions before activation</small></div></div>';
 const target=home.querySelector('.v24-trust')||home.querySelector('.grid2')||home.lastElementChild;
 target?.after(card);
}
function investCommand(){
 const inv=$('#invest'); if(!inv||inv.querySelector('.v25-command'))return;
 const c=document.createElement('div'); c.className='card v25-command';
 c.innerHTML='<div class="v25-command-top"><div><span class="eyebrow">Auto-Invest command center</span><h3>Build the plan before you activate</h3><p>Choose an asset class, amount and duration. Projections are illustrative and returns are not guaranteed.</p></div><div class="v25-orb">AI</div></div>'+
 '<div class="v25-steps"><span class="on"><i>1</i>Strategy</span><span><i>2</i>Amount</span><span><i>3</i>Review</span></div>'+
 '<div class="v25-allocation"><div><span>Risk view</span><b>Transparent</b><small>Assumptions shown before confirmation</small></div><div><span>Execution</span><b>Account-first</b><small>Activation requires a connected backend</small></div></div>';
 const visual=inv.querySelector('.v24-section-visual'); (visual||inv.firstElementChild)?.after(c);
}
function activeStrip(){
 const inv=$('#invest'); if(!inv||inv.querySelector('.v25-active'))return;
 const a=document.createElement('div');a.className='card v25-active';
 a.innerHTML='<div class="row"><div><span class="eyebrow">Strategy status</span><b class="v25-status-title">Ready to review</b></div><span class="badge">NOT ACTIVE</span></div><div class="v25-status-track"><span></span></div><div class="v25-status-meta"><span>1&nbsp; Choose</span><span>2&nbsp; Review</span><span>3&nbsp; Activate</span></div>';
 inv.querySelector('.v25-command')?.after(a);
}
function walletStatus(){
 const w=$('#wallet'); if(!w||w.querySelector('.v25-wallet-status'))return;
 const a=document.createElement('div');a.className='card v25-wallet-status';
 a.innerHTML='<div class="row"><div><span class="eyebrow">Treasury rails</span><b>USDT deposit networks</b></div><span class="v25-secure">SECURE FLOW</span></div><div class="v25-network-row"><span>BNB Smart Chain</span><b>BEP20</b></div><div class="v25-network-row"><span>Tron</span><b>TRC20</b></div><p>Deposit addresses shown in-app are Aster treasury addresses. Always verify the network before sending.</p>';
 w.querySelector('.v24-section-visual')?.after(a);
}
function bindMotion(){
 document.querySelectorAll('.v25-command,.v25-pulse,.v25-active,.v25-wallet-status').forEach(el=>{
   el.addEventListener('pointerdown',()=>el.classList.add('pressed'),{passive:true});
   el.addEventListener('pointerup',()=>el.classList.remove('pressed'),{passive:true});
 });
}
function boot25(){homePulse();investCommand();activeStrip();walletStatus();bindMotion()}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',()=>setTimeout(boot25,120));else setTimeout(boot25,120);
})();
