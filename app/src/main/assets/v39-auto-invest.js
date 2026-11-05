/* V39 — Auto-Invest only experience */
(function(){
'use strict';
function ready(fn){if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',fn,{once:true});else fn()}
ready(function(){
  const $=(s,r=document)=>r.querySelector(s), $$=(s,r=document)=>[...r.querySelectorAll(s)];
  const hide=s=>{$$(s).forEach(x=>x.classList.add('v39-hide'))};
  /* Hard product boundary: Auto-Invest / Wealth only. */
  hide('#roiCalc');
  hide('[data-go="roiCalc"]');
  $$('a').filter(a=>/market|trade|binary/i.test(a.textContent||'')).forEach(a=>a.classList.add('v39-hide'));
  /* Remove legacy copy that makes the product sound like a trading app. */
  /* Market information is discovery-only; execution remains outside this app. */
  $$('body *' ).forEach(el=>{
    if(el.children.length===0 && /Live markets\.|Live market data|Market pulse|Latest market news/i.test(el.textContent||'')){
      el.classList.add('v39-hide');
    }
  });
  const home=$('#home');
  /* Replace the old Aster Pulse/market strip with a real, scrollable crypto + forex news feed. */
  if(home && !$('#v39NewsPanel')){
    const panel=document.createElement('section');panel.id='v39NewsPanel';panel.innerHTML='<div class="news-scroll-head"><span class="news-scroll-title">Market intelligence</span><span class="news-scroll-live">LIVE HEADLINES</span></div><div id="v39NewsFeed" role="feed" aria-label="Latest crypto and forex news"><div class="small muted" style="padding:16px">Loading market headlines…</div></div>';
    const hero=home.querySelector('.hero');if(hero)hero.insertAdjacentElement('afterend',panel);else home.prepend(panel);
    const refresh=()=>{if(typeof window.loadNews==='function')window.loadNews('#v39NewsFeed')};
    if(document.readyState==='complete')refresh();else window.addEventListener('load',refresh,{once:true});
    setInterval(refresh,300000);
  }
  /* Home-page cleanup: remove the redundant One Plan promo and Aster Pulse market card. */
  $('#v39Plan')?.remove();
  if(home){
    home.querySelector('#homeMarkets')?.remove();
    home.querySelector('#homeTicker')?.remove();
    home.querySelector('#news')?.closest('.card')?.remove();
    home.querySelectorAll('.live-ticker,.market-card-head,.v25-strategy,.v25-section-title').forEach(el=>el.remove());
    home.querySelectorAll('.section-head').forEach(head=>{
      if(/market pulse|aster pulse/i.test(head.textContent||'')) head.remove();
    });
  }
  const invest=$('#invest');
  /* Keep the Auto-Invest screen focused: no allocation-mode or automation selectors. */
  $('#v39Controls')?.remove();
  const wealth=$('#insights');
  if(wealth && !$('#v39WealthHero')){
    const hero=document.createElement('div'); hero.id='v39WealthHero'; hero.className='v39-wealth-hero';
    hero.innerHTML='<div class="label">Wealth snapshot</div><div class="value" id="v39WealthValue">— USDT</div><div class="small muted" style="margin-top:3px">Authenticated portfolio value · live backend only</div><div class="v39-bars"><div class="v39-bar"><i id="v39WealthBar" style="width:0"></i></div></div>';
    const first=wealth.querySelector('.grid'); if(first) first.insertAdjacentElement('beforebegin',hero); else wealth.appendChild(hero);
  }
  const wallet=$('#wallet');
  if(wallet && !$('#v39Security')){
    const sec=document.createElement('div'); sec.id='v39Security'; sec.className='card v39-security';
    sec.innerHTML='<div class="v39-security-icon">✓</div><div><b>Custody safeguards</b><div class="small muted">Withdrawals remain server-controlled and fail closed until a verified provider confirms settlement.</div></div>';
    const cards=wallet.querySelectorAll('.card'); if(cards.length) cards[cards.length-1].insertAdjacentElement('afterend',sec); else wallet.appendChild(sec);
  }
  /* Replace risky legacy ROI navigation with the investment planner. */
  const roiLinks=$$('[data-go="roiCalc"]'); roiLinks.forEach(b=>{b.dataset.go='invest'; b.textContent='Plan Auto-Invest'});
  /* Refresh the new wealth hero from the existing authenticated portfolio endpoint. */
  async function syncWealth(){
    try{
      const base=(window.ASTER_API_BASE||localStorage.getItem('aster_api_base')||'').replace(/\/$/,'');
      if(!base)return;
      const r=await fetch(base+'/v1/portfolio',{credentials:'include'}); if(!r.ok)return;
      const d=await r.json(); const total=Number(d.total||0), available=Number(d.available||0);
      const invested=Math.max(0,total-available);
      const v=$('#v39WealthValue'), bar=$('#v39WealthBar');
      if(v)v.textContent=Number.isFinite(total)?total.toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2})+' USDT':'— USDT';
      if(bar)bar.style.width=(total?Math.min(100,invested/total*100):0)+'%';
    }catch(e){}
  }
  window.addEventListener('load',syncWealth,{once:true}); syncWealth();
  /* Kill legacy market refresh after the page's initial scripts have completed. */
  if(typeof window.loadMarkets==='function') window.loadMarkets=function(){};
  /* Navigation polish for dynamically inserted controls. */
  document.addEventListener('click',e=>{const b=e.target.closest('[data-go="invest"]');if(b && typeof window.go==='function')window.go('invest')});
});
})();