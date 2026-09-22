/* Aster V25 MAX — product UX layer */
(()=>{const $=(s,r=document)=>r.querySelector(s),$$=(s,r=document)=>[...r.querySelectorAll(s)];
const photo={
 home:'https://images.unsplash.com/photo-1521295121783-8a321d551ad2?auto=format&fit=crop&w=1400&q=86',
 crypto:'https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?auto=format&fit=crop&w=900&q=86',
 forex:'https://images.unsplash.com/photo-1526304640581-d334cdbbf45e?auto=format&fit=crop&w=900&q=86'
};
function toast(t){let x=$('.v25-toast');if(!x){x=document.createElement('div');x.className='v25-toast';document.body.appendChild(x)}x.textContent=t;x.classList.add('on');clearTimeout(x._t);x._t=setTimeout(()=>x.classList.remove('on'),1900)}
function chart(){return '<svg viewBox="0 0 500 120" preserveAspectRatio="none"><defs><linearGradient id="v25g" x1="0" x2="1"><stop offset="0" stop-color="#e9b84e"/><stop offset="1" stop-color="#8d72ff"/></linearGradient></defs><path d="M0 96 C45 92 48 70 88 77 S128 51 166 63 S202 42 241 51 S282 20 320 39 S359 30 398 43 S440 17 500 10" fill="none" stroke="url(#v25g)" stroke-width="4" stroke-linecap="round"/><path d="M0 96 C45 92 48 70 88 77 S128 51 166 63 S202 42 241 51 S282 20 320 39 S359 30 398 43 S440 17 500 10 L500 120 L0 120Z" fill="url(#v25g)" opacity=".10"/></svg>'}
function home(){
 const h=$('#home');if(!h||h.dataset.v25)return;h.dataset.v25=1;
 const oldHero=h.querySelector('.hero'); if(oldHero) oldHero.style.display='none';
 const wrap=document.createElement('div');wrap.className='v25-shell';
 wrap.innerHTML='<div class="v25-hero" style="background-image:url('+photo.home+')"><div class="v25-hero-copy"><div class="v25-kicker">ASTER FINANCIALS · 2026</div><h1>Build wealth.<br>Automatically.</h1><p>A focused financial workspace for Auto-Invest, live market context and transparent treasury rails.</p><div class="v25-pills"><span class="v25-pill">LIVE MARKETS</span><span class="v25-pill">AUTO-INVEST</span><span class="v25-pill">24/7 ACCESS</span></div></div></div><div class="v25-actionbar"><button data-v25-go="wallet">＋ Deposit</button><button data-v25-go="invest">✦ Auto-Invest</button><button data-v25-go="markets">↗ Markets</button></div><div class="v25-balance-row"><div class="v25-stat"><span class="label">Portfolio balance</span><strong id="v25Bal">$0</strong><small>Account value</small></div><div class="v25-stat"><span class="label">Market status</span><strong style="font-size:20px">Live</strong><small>Quotes updating</small></div></div><div class="v25-section-title"><h2>Performance</h2><span>Illustrative UI view</span></div><div class="v25-chart-card"><div class="v25-chart-head"><b>Portfolio trend</b><span>LIVE CONTEXT</span></div><div class="v25-chart">'+chart()+'</div></div><div class="v25-section-title"><h2>Choose your path</h2><span>Auto-Invest</span></div><div class="v25-strategy"><div class="v25-strategy-card" style="background-image:url('+photo.crypto+')"><span class="v25-badge">CRYPTO</span><b>Digital assets</b><span>Automated strategy flow with transparent assumptions.</span></div><div class="v25-strategy-card" style="background-image:url('+photo.forex+')"><span class="v25-badge">FOREX</span><b>Global FX</b><span>Currency-market exposure presented without execution controls.</span></div></div>';
 h.prepend(wrap);
 const bal=$('.balance .amount');if(bal)$('#v25Bal').textContent='$'+(bal.textContent.replace(/[^0-9.]/g,'')||'0');
}
function invest(){
 const s=$('#invest');if(!s||s.dataset.v25)return;s.dataset.v25=1;
 const art=document.createElement('div');art.className='v25-chart-card';art.innerHTML='<div class="v25-chart-head"><b>How Auto-Invest works</b><span>3 STEPS</span></div><div class="v25-steps" style="margin-top:12px"><div class="v25-step"><i>1</i><b>Deposit</b><span>Fund your Aster wallet.</span></div><div class="v25-step"><i>2</i><b>Choose</b><span>Select Crypto or Forex.</span></div><div class="v25-step"><i>3</i><b>Monitor</b><span>Track strategy status.</span></div></div>';
 const anchor=s.querySelector('.invest-cards')||s.firstElementChild;s.insertBefore(art,anchor);
 const note=document.createElement('div');note.className='notice';note.innerHTML='<b>Risk first.</b> Projections are mathematical illustrations only. Returns are not guaranteed and strategies can lose value.';s.insertBefore(note,s.querySelector('.projection')||s.lastElementChild);
}
function wallet(){
 const s=$('#wallet');if(!s||s.dataset.v25)return;s.dataset.v25=1;
 const v=document.createElement('div');v.className='v25-wallet-visual';v.innerHTML='<div class="v25-wallet-copy"><small>ASTER TREASURY</small><strong>USDT Wallet</strong><span>Network-specific deposit rails · BEP20 / TRC20</span></div>';s.prepend(v);
}
function profile(){const s=$('#profile');if(!s||s.dataset.v25)return;s.dataset.v25=1;const c=s.querySelector('.card');if(c){const x=document.createElement('div');x.className='v25-chart-card';x.style.marginTop='12px';x.innerHTML='<div class="v25-chart-head"><b>Account security</b><span>READY FOR BACKEND</span></div><div class="small muted" style="margin-top:8px">Authentication, KYC/AML, sessions and withdrawal controls belong to the secure production backend.</div>';s.insertBefore(x,c)}}
function wire(){ $$('[data-v25-go]').forEach(b=>b.onclick=()=>window.go?.(b.dataset.v25Go)); $$('.v25-strategy-card').forEach(c=>c.onclick=()=>{toast('Open Auto-Invest to configure this strategy');window.go?.('invest')});}
function boot(){home();invest();wallet();profile();wire();toast('Aster V25 loaded');}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot);else boot();
})();