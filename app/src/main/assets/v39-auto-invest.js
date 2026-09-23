/* V39 — Auto-Invest only experience */
(function(){
'use strict';
function ready(fn){if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',fn,{once:true});else fn()}
ready(function(){
  const $=(s,r=document)=>r.querySelector(s), $$=(s,r=document)=>[...r.querySelectorAll(s)];
  const hide=s=>{$$(s).forEach(x=>x.classList.add('v39-hide'))};
  /* Hard product boundary: Auto-Invest / Wealth only. */
  hide('#markets,#roiCalc,#homeTicker,#homeMarkets,#news,#news2');
  hide('[data-go="markets"],[data-go="roiCalc"]');
  $$('a').filter(a=>/market|trade|binary/i.test(a.textContent||'')).forEach(a=>a.classList.add('v39-hide'));
  /* Remove legacy copy that makes the product sound like a trading app. */
  /* Keep the product language focused on wealth allocation, not market speculation. */
  $('body *').forEach(el=>{
    if(el.children.length===0 && /Live markets\.|Live market data|Market pulse|Latest market news/i.test(el.textContent||'')){
      el.classList.add('v39-hide');
    }
  });
  const home=$('#home');
  if(home && !$('#v39Plan')){
    const grid=home.querySelector('.grid2');
    const plan=document.createElement('section');
    plan.id='v39Plan'; plan.className='v39-plan';
    plan.innerHTML='<div class="v39-kicker">Aster Auto-Invest</div><h3>One plan. Automated wealth building.</h3><p>Choose a strategy, set your capital and let Aster handle the account workflow when a supported execution provider is connected.</p><div class="v39-plan-grid"><div class="v39-plan-step"><b>01 · Choose</b><span>Select a strategy</span></div><div class="v39-plan-step"><b>02 · Allocate</b><span>Set your capital</span></div><div class="v39-plan-step"><b>03 · Automate</b><span>Review & activate</span></div></div><button class="primary" data-go="invest" style="margin-top:14px;background:#fff;color:#17131c">Build my Auto-Invest plan</button>';
    if(grid) grid.insertAdjacentElement('afterend',plan); else home.appendChild(plan);
  }
  const invest=$('#invest');
  if(invest && !$('#v39Controls')){
    const controls=document.createElement('div'); controls.id='v39Controls'; controls.className='v39-control';
    controls.innerHTML='<div class="card"><div class="eyebrow">Allocation mode</div><select id="v39Allocation"><option>Balanced allocation</option><option>Growth allocation</option><option>Capital preservation</option></select></div><div class="card"><div class="eyebrow">Automation</div><select id="v39Cadence"><option>Weekly review</option><option>Monthly review</option><option>Manual review</option></select></div>';
    const notice=invest.querySelector('.notice'); if(notice) notice.insertAdjacentElement('beforebegin',controls); else invest.appendChild(controls);
    const how=document.createElement('div'); how.className='card'; how.innerHTML='<div class="row"><div><div class="eyebrow">Aster execution model</div><b>Review → authorize → execute</b></div><span class="v39-status"><i></i>Fail-closed</span></div><div class="divider"></div><div class="small muted">A strategy is never shown as active or profitable unless the authenticated backend and configured execution/valuation provider confirm it.</div>';
    if(notice) notice.insertAdjacentElement('afterend',how);
  }
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