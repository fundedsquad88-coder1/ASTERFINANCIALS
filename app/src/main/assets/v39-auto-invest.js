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
  /* Keep the Home content and remove only the three panels requested. */
  if(home){
    home.querySelectorAll('.card,.art-banner,.v25-hero,.market-context,[id]').forEach(el=>{
      if(el===home || el.id==='home') return;
      const label=(el.innerText||el.textContent||'').replace(/\s+/g,' ').trim().toLowerCase();
      if(label.includes('roi calculator') || label.includes('global markets, beautifully simple') ||
         label.includes('aster pulse') || label.includes('markets are moving')){
        if(el.matches('.card,.art-banner,.v25-hero,.market-context')) el.remove();
        else { const panel=el.closest('.card,.art-banner,.v25-hero,.market-context'); if(panel&&home.contains(panel))panel.remove(); }
      }
    });
    home.querySelector('#homeMarkets')?.remove();
    home.querySelector('#homeTicker')?.remove();
    home.querySelector('#news')?.closest('.card')?.remove();
    home.querySelectorAll('.section-head').forEach(head=>{if(/market pulse|aster pulse/i.test(head.textContent||''))head.remove()});
    /* Live crypto + forex doomscroll feed at the bottom of Home. */
    if(!$('#v39NewsPanel',home)){
      const panel=document.createElement('section');
      panel.id='v39NewsPanel';
      panel.className='v39-news-panel';
      panel.innerHTML='<div class="v39-news-head"><div><div class="eyebrow">MARKET INTELLIGENCE</div><b>Crypto & Forex Live News</b></div><span class="v39-live"><i></i> LIVE</span></div><div id="v39NewsFeed" class="v39-news-feed" role="feed" aria-label="Scrollable crypto and forex market headlines"><div class="small muted">Loading live headlines…</div></div>';
      home.appendChild(panel);
    }
    const refreshNews=()=>{if(typeof window.loadNews==='function')window.loadNews('#v39NewsFeed')};
    window.addEventListener('load',refreshNews,{once:true});
    if(document.readyState==='complete')refreshNews();
    if(!window.__asterNewsRefresh)window.__asterNewsRefresh=window.setInterval(refreshNews,300000);
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