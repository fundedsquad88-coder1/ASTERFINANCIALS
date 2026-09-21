(function(){
'use strict';
const API=window.ASTER_API_BASE||localStorage.getItem('aster_api_base')||'';
const esc=s=>String(s??'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
function toast(m){if(window.showToast)window.showToast(m);else{const e=document.createElement('div');e.className='v25-toast';e.textContent=m;document.body.appendChild(e);setTimeout(()=>e.remove(),2400)}}
async function api(path,opt={}){
 if(!API) throw new Error('Aster API is not connected yet');
 const r=await fetch(API+path,{credentials:'include',headers:{'Content-Type':'application/json',...(opt.headers||{})},...opt});
 const data=await r.json().catch(()=>({}));
 if(!r.ok) throw new Error(data.detail||data.message||'Request failed');
 return data;
}
function card(title,sub,body){return '<section class="v26-card v26-center"><div class="v26-head"><div><div class="v26-title">'+title+'</div><div class="v26-sub">'+sub+'</div></div></div>'+body+'</section>'}
function profile(){
 const root=document.querySelector('#profile'); if(!root||root.dataset.v26)return; root.dataset.v26='1';
 root.insertAdjacentHTML('beforeend',card('Account & Security','Production-ready account controls',
 '<div class="v26-status"><span class="v26-dot"></span> Secure session architecture</div><div class="v26-actions"><button class="v26-btn" id="v26-login">Sign in</button><button class="v26-btn secondary" id="v26-register">Create account</button></div><div class="v26-note">Password reset, session revocation, notifications and referral APIs are wired on the production-core backend. Connect the API base URL to activate live account actions.</div>'));
 document.getElementById('v26-login').onclick=()=>authSheet(false); document.getElementById('v26-register').onclick=()=>authSheet(true);
}
function authSheet(register){
 const back=document.getElementById('sheetBack'),sh=document.getElementById('sheet'); if(!back||!sh)return;
 sh.innerHTML='<div class="grab"></div><h3>'+(register?'Create Aster account':'Sign in to Aster')+'</h3><div class="v26-auth"><input class="v26-input" id="v26-email" type="email" placeholder="Email"><input class="v26-input" id="v26-pass" type="password" placeholder="Password (12+ characters)">'+(register?'<input class="v26-input" id="v26-ref" placeholder="Referral code (optional)">':'')+'<button class="primary" id="v26-submit">'+(register?'Create account':'Sign in')+'</button><button class="secondary" id="v26-reset">Forgot password?</button><div class="v26-note">'+(API?'Connected to Aster API.':'Backend-ready UI: set ASTER_API_BASE before release.')+'</div></div>';
 back.classList.add('on');
 document.getElementById('v26-submit').onclick=async()=>{try{const email=document.getElementById('v26-email').value.trim(),password=document.getElementById('v26-pass').value;const csrf=await api(register?'/v1/auth/register':'/v1/auth/login',{method:'POST',body:JSON.stringify(register?{email,password,referral_code:document.getElementById('v26-ref')?.value||null}:{email,password})});if(csrf.csrf_token){sessionStorage.setItem('aster_csrf',csrf.csrf_token)}back.classList.remove('on');toast(register?'Account created':'Welcome back')}catch(e){toast(e.message)}};document.getElementById('v26-reset').onclick=async()=>{try{await api('/v1/auth/password-reset/request',{method:'POST',body:JSON.stringify({email:document.getElementById('v26-email').value.trim()})});toast('If the account exists, reset instructions will be sent.')}catch(e){toast(e.message)}}}
function wallet(){
 const root=document.querySelector('#wallet');if(!root||root.dataset.v26)return;root.dataset.v26='1';
 root.insertAdjacentHTML('beforeend',card('Transaction Center','Funding and settlement lifecycle',
 '<div class="v26-row"><span>Deposits</span><b>Pending → Confirmed</b></div><div class="v26-row"><span>Withdrawals</span><b>Pending → Settled</b></div><div class="v26-row"><span>Ledger</span><b>Idempotent</b></div><div class="v26-actions"><button class="v26-btn" id="v26-tx">View transactions</button><button class="v26-btn secondary" id="v26-refresh">Refresh wallet</button></div><div class="v26-note">Aster treasury deposits are credited only after independently verified blockchain/provider confirmation. Withdrawal failures release held funds back to available balance.</div>'));
 document.getElementById('v26-refresh').onclick=async()=>{try{const w=await api('/v1/wallet');toast('Balance refreshed · '+w.available+' USDT available')}catch(e){toast(e.message)}};document.getElementById('v26-tx').onclick=async()=>{try{const rows=await api('/v1/transactions');toast((rows.length||0)+' transactions loaded')}catch(e){toast(e.message)}};
}
function invest(){
 const root=document.querySelector('#invest');if(!root||root.dataset.v26)return;root.dataset.v26='1';
 root.insertAdjacentHTML('beforeend',card('Strategy Controls','Pause, resume or release principal',
 '<div class="v26-row"><span>Core Crypto</span><span class="v26-chip">AUTO</span></div><div class="v26-row"><span>Global FX</span><span class="v26-chip">AUTO</span></div><div class="v26-note">Strategy activation moves available balance into invested balance. Release returns principal through the ledger; actual strategy valuation/execution remains server-controlled and is never simulated as guaranteed profit.</div>'));
}
function boot(){profile();wallet();invest();if(API)toast('Aster API connected')}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot);else boot();
})();