(function(){
  const css=`
  :root{--bg:#050606;--panel:#0b0d0d;--panel2:#101212;--line:rgba(232,189,80,.16);--gold:#e8bd50;--gold2:#f4d77e;--text:#f7f5ef;--muted:#858987;--green:#24d47f;--red:#ef5a5a}
  body{font-family:Inter,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif;background:radial-gradient(circle at 80% -10%,rgba(232,189,80,.10),transparent 34%),var(--bg);letter-spacing:.05px}
  .app{background:linear-gradient(180deg,rgba(255,255,255,.012),transparent 28%)}
  .top{padding:20px 18px 10px}.brand{width:116px;height:38px}.top .gold{font-size:18px;opacity:.9}
  .sandbox{margin:8px 18px;padding:8px 10px;border:1px solid rgba(232,189,80,.28);background:rgba(232,189,80,.055);border-radius:999px;font-size:9px;letter-spacing:1px}
  .card{margin:12px 18px;padding:17px;border:1px solid var(--line);border-radius:18px;background:linear-gradient(145deg,rgba(255,255,255,.035),rgba(255,255,255,.012));box-shadow:0 10px 30px rgba(0,0,0,.20)}
  .balance{font-size:34px;font-weight:700;letter-spacing:-1px}.muted{color:#8f9491}.gold{color:var(--gold)}
  .actions{gap:9px;margin:14px 18px}.action{min-height:76px;border:1px solid rgba(232,189,80,.14);border-radius:16px;background:linear-gradient(180deg,#111414,#0b0d0d);box-shadow:inset 0 1px rgba(255,255,255,.03)}.action b{font-size:22px;color:var(--gold2)}
  .section{padding:17px 18px}.head{margin-bottom:12px}.head b{font-size:18px;letter-spacing:-.2px}
  .market{position:relative;padding:15px 4px;border-bottom:1px solid rgba(255,255,255,.055);align-items:center}.market:before{display:none}.market>span:first-child{display:block;flex:1}.market small{font-size:10px}.market .status,.market .muted{font-size:9px;letter-spacing:.5px}.coin-icon{width:38px;height:38px;min-width:38px;margin-right:11px;border-radius:50%;object-fit:cover;display:block;background:#151818;border:1px solid rgba(255,255,255,.10);box-shadow:0 3px 12px rgba(0,0,0,.25)}
  .nav{height:78px;background:rgba(8,10,10,.96);backdrop-filter:blur(18px);border-top:1px solid rgba(232,189,80,.16);padding-bottom:env(safe-area-inset-bottom)}.nav button{font-size:9px}.nav i{font-size:20px;margin:8px 8px 5px}.nav .on{font-weight:700}
  .trade{padding:0 18px}.back{padding:14px 18px}.pair{padding:14px 15px;border-radius:15px;background:linear-gradient(135deg,rgba(232,189,80,.07),rgba(255,255,255,.018));border-color:rgba(232,189,80,.22)}.price{font-size:32px;font-weight:700;letter-spacing:-1px}.chartbox{height:330px;border:1px solid rgba(255,255,255,.08);border-radius:16px;background:linear-gradient(180deg,#090b0b,#060707);box-shadow:inset 0 1px rgba(255,255,255,.025);margin:12px 0}.periods{padding-bottom:2px}.periods button,.pill{border-radius:999px;background:#0d1010;border-color:#242727;padding:8px 13px}.periods .sel{background:rgba(232,189,80,.09)}
  .bookbox{border-radius:13px;background:rgba(255,255,255,.018);border-color:rgba(255,255,255,.07)}.controls{gap:10px}.field{border-radius:13px;background:#0b0d0d;border-color:rgba(255,255,255,.08)}.field input,.field select{font-size:15px}.tradebtn{padding:16px;border-radius:13px;font-size:13px;box-shadow:0 7px 18px rgba(0,0,0,.18)}.higher{background:linear-gradient(135deg,#19bd72,#087d48)}.lower{background:linear-gradient(135deg,#e84e4e,#9d2929)}
  .goldbtn,.outlinebtn{border-radius:13px;padding:14px}.goldbtn{background:linear-gradient(135deg,#f0c95b,#c99727);box-shadow:0 8px 18px rgba(213,168,63,.13)}.outlinebtn{background:#0d1010;border-color:rgba(232,189,80,.35)}
  .modal{background:rgba(0,0,0,.76);backdrop-filter:blur(8px)}.sheet{background:linear-gradient(180deg,#111414,#090b0b);border-color:rgba(232,189,80,.20);border-radius:24px 24px 0 0;padding:22px 18px}.form input{border-radius:12px;background:#070909;border-color:#272b2a}.tabs button{border-radius:11px}.tabs .sel{background:rgba(232,189,80,.08)}
  .stat{border-radius:13px;background:rgba(255,255,255,.018);border-color:rgba(255,255,255,.07)}.plan{border-radius:15px;background:linear-gradient(145deg,rgba(232,189,80,.055),rgba(255,255,255,.012))}.listitem{border-bottom-color:rgba(255,255,255,.055)}.toast{border-radius:13px;box-shadow:0 10px 30px rgba(0,0,0,.35)}
  .section>.head>span{font-size:11px}.notice{font-size:10px}.attribution{padding-bottom:8px}
  .live-dot{display:inline-block;width:6px;height:6px;border-radius:50%;background:var(--green);box-shadow:0 0 8px rgba(36,212,127,.7);margin-right:5px}
  .hero-strip{display:flex;align-items:center;gap:12px;padding:15px 16px;border-radius:16px;background:linear-gradient(120deg,rgba(232,189,80,.10),rgba(232,189,80,.025));border:1px solid rgba(232,189,80,.14)}
  .hero-strip .mark{width:42px;height:42px;border-radius:13px;display:grid;place-items:center;background:linear-gradient(135deg,#f1cb61,#8e651b);color:#080909;font-weight:900;font-size:20px;box-shadow:0 8px 18px rgba(232,189,80,.12)}
  @media(min-width:600px){.app{max-width:520px;margin:auto}.nav{max-width:520px;left:50%;right:auto;width:520px;transform:translateX(-50%)}}
  `;
  const logoBase='https://cdn.jsdelivr.net/gh/atomiclabs/cryptocurrency-icons@master/128/color/';
  const logoMap={BTCUSDT:'btc',ETHUSDT:'eth',BNBUSDT:'bnb',XRPUSDT:'xrp',SOLUSDT:'sol',TRXUSDT:'trx',DOGEUSDT:'doge',LINKUSDT:'link',ADAUSDT:'ada',LTCUSDT:'ltc',BCHUSDT:'bch',AVAXUSDT:'avax',DOTUSDT:'dot',UNIUSDT:'uni',NEARUSDT:'near',SUIUSDT:'sui',SHIBUSDT:'shib',HBARUSDT:'hbar',APTUSDT:'apt',ATOMUSDT:'atom'};
  const commodityLogo={XAUUSDT:'gold',XAGUSDT:'silver',WTIUSDT:'oil',BRENTUSDT:'oil'};
  function style(){if(document.getElementById('asterPolish'))return;const s=document.createElement('style');s.id='asterPolish';s.textContent=css;document.head.appendChild(s)}
  function decorateMarkets(){
    document.querySelectorAll('.market').forEach(row=>{
      if(row.querySelector('.coin-icon'))return;
      const onclick=row.getAttribute('onclick')||'';
      const m=onclick.match(/startMarket\('([^']+)'\)/); const sym=m?m[1]:'';
      if(!sym)return;
      const first=row.querySelector('span:first-child'); if(!first)return;
      const img=document.createElement('img'); img.className='coin-icon'; img.alt=sym.replace('USDT','')+' logo';
      if(logoMap[sym]){img.src=logoBase+logoMap[sym]+'.png';}
      else if(commodityLogo[sym]){
        img.src='data:image/svg+xml;charset=UTF-8,'+encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 80 80"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#f6d875"/><stop offset="1" stop-color="#a56f12"/></linearGradient></defs><circle cx="40" cy="40" r="37" fill="url(#g)"/><text x="40" y="47" text-anchor="middle" font-family="Arial,sans-serif" font-weight="700" font-size="22" fill="#111">'+(sym==='XAUUSDT'?'Au':sym==='XAGUSDT'?'Ag':'OIL')+'</text></svg>');
      }
      img.onerror=function(){this.style.display='none'};
      row.insertBefore(img,first);
    });
  }
  function decorate(){
    style();
    const home=document.getElementById('home');
    if(home&&!document.getElementById('heroStrip')){const x=document.createElement('div');x.id='heroStrip';x.className='card hero-strip';x.innerHTML='<div class="mark">A</div><div><b>Aster Financials</b><br><span class="muted">Markets, trading &amp; earning in one place</span></div>';const actions=home.querySelector('.actions');if(actions)actions.parentNode.insertBefore(x,actions)}
    document.querySelectorAll('.status').forEach(el=>{if(el.textContent.trim()==='LIVE'&&!el.querySelector('.live-dot'))el.innerHTML='<span class="live-dot"></span>LIVE'});
    decorateMarkets();
    const chart=document.getElementById('chart');if(chart)chart.setAttribute('aria-label','Aster market price chart');
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',decorate);else decorate();
  setTimeout(decorate,700); setTimeout(decorate,1600); setInterval(decorate,2500);
})();
