(function(){
if(window.__asterV24)return;window.__asterV24=1;
const $=(s,r=document)=>r.querySelector(s);
function addCss(){
 const l=document.createElement('link');l.rel='stylesheet';l.href='https://appassets.androidplatform.net/assets/v24-upgrade.css';document.head.appendChild(l);
}
function visual(id,title,text,img){
 const el=document.getElementById(id);if(!el)return;
 if(el.querySelector('.v24-section-visual'))return;
 const v=document.createElement('div');v.className='v24-section-visual';v.style.backgroundImage='url("'+img+'")';
 v.innerHTML='<div class="v24-copy"><b>'+title+'</b><span>'+text+'</span></div>';
 el.appendChild(v);
}
function trust(){
 const home=$('#home');if(!home||home.querySelector('.v24-trust'))return;
 const t=document.createElement('div');t.className='v24-trust';
 t.innerHTML='<div><b>Live data</b><span>Market context</span></div><div><b>Transparent</b><span>Clear projections</span></div><div><b>Account-first</b><span>No fake balances</span></div>';
 const ref=home.querySelector('.grid2');ref?.after(t);
}
function marketMeta(){
 const m=$('#markets');if(!m||m.querySelector('.v24-market-meta'))return;
 const x=document.createElement('div');x.className='v24-market-meta';
 x.innerHTML='<span class="v24-meta-pill live">● Live market data</span><span class="v24-meta-pill">Crypto</span><span class="v24-meta-pill">Forex</span><span class="v24-meta-pill">Informational only</span>';
 const tabs=$('#marketTabs');tabs?.before(x);
}
function stampMarketUpdate(){
 const m=$('#markets');if(!m)return;
 let el=$('#v24MarketUpdated');
 if(!el){
  el=document.createElement('span');el.id='v24MarketUpdated';el.className='small muted';
  const head=m.querySelector('.section-head');head?.appendChild(el);
 }
 el.textContent='Updated '+new Date().toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'});
}
async function forex(){
 try{
  const url='https://api.frankfurter.dev/v1/latest?base=USD&symbols=EUR,GBP,JPY,AUD,CAD,CHF';
  const raw=await new Promise((resolve,reject)=>{
   const id='fx'+Date.now()+Math.random();window.__asterCallbacks=window.__asterCallbacks||{};
   window.__asterCallbacks[id]={resolve,reject};
   if(window.AsterNative)AsterNative.fetch(url,id);
   else fetch(url).then(r=>r.text()).then(resolve).catch(reject)
  });
  const d=JSON.parse(raw), rates=d.rates||{};
  Object.entries(rates).forEach(([ccy,rate])=>{
   quotes['USD/'+ccy]={symbol:'USD/'+ccy,type:'forex',price:+rate,open:+rate};
  });
  renderMarkets();renderTicker();stampMarketUpdate();
  const list=$('#marketList');if(!list)return;
  const old=$('#v24ForexCard');if(old)old.remove();
  const fx=document.createElement('div');fx.id='v24ForexCard';fx.className='card';fx.style.margin='12px 0 0';
  fx.innerHTML='<div class="row"><b>Global FX</b><span class="badge">Live spot</span></div>'+
   Object.entries(rates).map(([c,r])=>'<div class="v24-forex"><div class="v24-flag">'+c+'</div><div><b>USD/'+c+'</b><div class="small muted">1 USD</div></div><div class="price">'+Number(r).toFixed(c==='JPY'?2:4)+'<div class="change muted">spot</div></div></div>').join('');
  list.parentNode.insertBefore(fx,list.nextSibling);
 }catch(e){console.warn('Aster Forex feed unavailable',e)}
}
function boot(){
 addCss();
 visual('home','Global markets, beautifully simple.','Aster combines live market context with automated investing in one focused experience.','https://images.unsplash.com/photo-1521295121783-8a321d551ad2?auto=format&fit=crop&w=1400&q=82');
 visual('invest','Choose your strategy.','Crypto and global FX, presented with transparent assumptions before you activate anything.','https://images.unsplash.com/photo-1559526324-593bc073d938?auto=format&fit=crop&w=1400&q=82');
 visual('markets','See the world behind the numbers.','Live crypto quotes plus global FX spot rates — informational, not execution.','https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?auto=format&fit=crop&w=1400&q=82');
 visual('wallet','Your treasury, clearly.','Network-specific USDT deposit rails with clear status and transaction history.','https://images.unsplash.com/photo-1526304640581-d334cdbbf45e?auto=format&fit=crop&w=1400&q=82');
 visual('profile','Everything about your Aster account.','Security, referrals, preferences and legal information in one place.','https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=1400&q=82');
 trust();marketMeta();
 const originalLoad=window.loadMarkets;
 if(typeof originalLoad==='function'&&!window.__asterV24Wrapped){
  window.__asterV24Wrapped=true;
  window.loadMarkets=async function(){
   const result=await originalLoad();
   await forex();
   return result;
  };
 }
 setTimeout(()=>window.loadMarkets?.(),250);
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot);else boot();
})();