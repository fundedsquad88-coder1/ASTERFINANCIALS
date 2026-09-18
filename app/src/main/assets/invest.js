
(function(){
  const state={kind:'crypto',step:1,amount:1000,rate:20,weeks:4};
  function name(){return state.kind==='crypto'?'Crypto Auto-Invest':'Forex Auto-Invest'}
  function end(){return state.amount*Math.pow(1+state.rate/100,state.weeks)}
  function addStyles(){
    const s=document.createElement('style');
    s.textContent='.flowCard{padding:15px}.flowTop{display:flex;align-items:center;justify-content:space-between;margin-bottom:12px}.flowStep{font-size:8px;letter-spacing:.12em;color:#f0ce70;font-weight:900;text-transform:uppercase}.flowTitle{font-size:20px;font-weight:900;margin:3px 0}.flowOptions{display:grid;grid-template-columns:1fr 1fr;gap:8px}.flowOption{border:1px solid #252830;background:#111318;color:#f4f2eb;border-radius:14px;padding:13px;text-align:left}.flowOption.selected{border-color:#c39731;background:#1a1811}.flowOption b{display:block;font-size:11px;margin-bottom:4px}.flowOption span{display:block;font-size:8px;color:#858a94;line-height:1.45}.amountInput{width:100%;border:1px solid #252830;background:#0d0f13;color:#f4f2eb;border-radius:12px;padding:13px;font-size:17px;font-weight:850}.flowSummary{background:#121419;border:1px solid #252830;border-radius:13px;padding:12px;margin-top:10px}.flowSummaryRow{display:flex;justify-content:space-between;padding:6px 0;font-size:9px}.flowSummaryRow span:first-child{color:#858a94}.flowActions{display:flex;gap:8px;margin-top:12px}.flowActions .btn{flex:1}.flowRisk{margin-top:10px;padding:10px;border-radius:11px;background:#211d12;border:1px solid #4c3c19;color:#cfc28d;font-size:8px;line-height:1.5}@media(max-width:430px){.flowOptions{grid-template-columns:1fr}}';
    document.head.appendChild(s);
  }
  function render(){
    const b=document.getElementById('flowBody'),t=document.getElementById('flowTitle'),st=document.getElementById('flowStep');
    if(!b)return; st.textContent='Step '+state.step+' of 4';
    if(state.step===1){
      t.textContent='Choose an Auto-Invest';
      b.innerHTML='<div class="flowOptions"><button class="flowOption '+(state.kind==='crypto'?'selected':'')+'" id="cryptoOpt"><b>Crypto Auto-Invest</b><span>BTC, ETH, SOL, BNB and XRP strategy universe.</span></button><button class="flowOption '+(state.kind==='forex'?'selected':'')+'" id="forexOpt"><b>Forex Auto-Invest</b><span>EUR/USD, GBP/USD, USD/JPY and XAU/USD strategy universe.</span></button></div><div class="flowActions"><button class="btn goldBtn" id="flowNext">Continue</button></div>';
      document.getElementById('cryptoOpt').onclick=()=>{state.kind='crypto';render()};
      document.getElementById('forexOpt').onclick=()=>{state.kind='forex';render()};
      document.getElementById('flowNext').onclick=()=>{state.step=2;render()};
    }else if(state.step===2){
      t.textContent='Set your amount';
      b.innerHTML='<div class="label">ILLUSTRATIVE STARTING AMOUNT · USDT</div><input id="flowAmount" class="amountInput" type="number" min="1" step="1" value="'+state.amount+'"><div class="flowSummary"><div class="flowSummaryRow"><span>Strategy</span><b>'+name()+'</b></div><div class="flowSummaryRow"><span>Illustrative weekly range</span><b>20–25%</b></div></div><div class="flowActions"><button class="btn" id="flowBack">Back</button><button class="btn goldBtn" id="flowNext">Continue</button></div>';
      document.getElementById('flowBack').onclick=()=>{state.step=1;render()};
      document.getElementById('flowNext').onclick=()=>{state.amount=Math.max(1,Number(document.getElementById('flowAmount').value)||1);state.step=3;render()};
    }else if(state.step===3){
      t.textContent='Choose duration';
      b.innerHTML='<div class="flowOptions"><button class="flowOption '+(state.weeks===4?'selected':'')+'" data-w="4"><b>4 weeks</b><span>Short illustrative projection.</span></button><button class="flowOption '+(state.weeks===8?'selected':'')+'" data-w="8"><b>8 weeks</b><span>Extended illustrative projection.</span></button><button class="flowOption '+(state.weeks===12?'selected':'')+'" data-w="12"><b>12 weeks</b><span>Longer illustrative projection.</span></button><button class="flowOption" id="rateOpt"><b>Target: '+state.rate+'%</b><span>Toggle the illustrative weekly rate.</span></button></div><div class="flowSummary"><div class="flowSummaryRow"><span>Illustrative end value</span><b>$'+end().toLocaleString(undefined,{minimumFractionDigits:2,maximumFractionDigits:2})+'</b></div></div><div class="flowActions"><button class="btn" id="flowBack">Back</button><button class="btn goldBtn" id="flowNext">Review</button></div>';
      document.querySelectorAll('[data-w]').forEach(x=>x.onclick=()=>{state.weeks=Number(x.dataset.w);render()});
      document.getElementById('rateOpt').onclick=()=>{state.rate=state.rate===20?25:20;render()};
      document.getElementById('flowBack').onclick=()=>{state.step=2;render()};
      document.getElementById('flowNext').onclick=()=>{state.step=4;render()};
    }else{
      t.textContent='Review Auto-Invest';
      b.innerHTML='<div class="flowSummary"><div class="flowSummaryRow"><span>Product</span><b>'+name()+'</b></div><div class="flowSummaryRow"><span>Starting amount</span><b>'+state.amount.toLocaleString()+' USDT</b></div><div class="flowSummaryRow"><span>Illustrative weekly rate</span><b>'+state.rate+'%</b></div><div class="flowSummaryRow"><span>Duration</span><b>'+state.weeks+' weeks</b></div><div class="flowSummaryRow"><span>Illustrative end value</span><b>$'+end().toLocaleString(undefined,{minimumFractionDigits:2,maximumFractionDigits:2})+'</b></div></div><div class="flowRisk">This is a configuration preview, not a promise of return. Live activation requires finalized product terms, an authenticated account, a server-side ledger and required compliance controls. No funds are moved by confirming this preview.</div><div class="flowActions"><button class="btn" id="flowBack">Back</button><button class="btn goldBtn" id="confirmFlow">Confirm Preview</button></div>';
      document.getElementById('flowBack').onclick=()=>{state.step=3;render()};
      document.getElementById('confirmFlow').onclick=()=>{if(window.note)note('Configuration complete. Live activation remains disabled until the secure account and ledger backend are connected.')};
    }
  }
  function start(k){state.kind=k;state.step=1;render();if(window.nav)nav('invest-flow')}
  window.startAutoInvest=start;
  function init(){
    addStyles();
    const sec=document.createElement('section');sec.id='invest-flow';sec.className='view';
    sec.innerHTML='<div class="hero"><div class="eyebrow">Auto-Invest Setup</div><h1>Configure your <span>strategy.</span></h1><p class="sub">Review the plan before any live activation. No funds are moved from this screen.</p></div><div class="card flowCard"><div class="flowTop"><div><div id="flowStep" class="flowStep">Step 1 of 4</div><div id="flowTitle" class="flowTitle">Choose an Auto-Invest</div></div><button class="btn" id="flowCancel">Cancel</button></div><div id="flowBody"></div></div>';
    const wallet=document.getElementById('wallet');wallet.parentNode.insertBefore(sec,wallet);
    document.getElementById('flowCancel').onclick=()=>nav('autoinvest');
    document.querySelectorAll('.goldBtn').forEach(x=>{if(x.textContent.trim()==='Start Auto-Invest')x.onclick=()=>start(x.closest('.autoBody')&&x.closest('.autoBody').querySelector('h3').textContent.toLowerCase().indexOf('forex')>=0?'forex':'crypto')});
    render();
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
})();