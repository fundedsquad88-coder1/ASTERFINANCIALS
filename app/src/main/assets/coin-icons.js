(function(){
  const icons={
    'BTC/USDT':['btc','Bitcoin'], 'ETH/USDT':['eth','Ethereum'], 'BNB/USDT':['bnb','BNB'], 'XRP/USDT':['xrp','XRP'],
    'SOL/USDT':['sol','Solana'], 'TRX/USDT':['trx','TRON'], 'DOGE/USDT':['doge','Dogecoin'], 'LINK/USDT':['link','Chainlink'],
    'ADA/USDT':['ada','Cardano'], 'LTC/USDT':['ltc','Litecoin'], 'BCH/USDT':['bch','Bitcoin Cash'], 'AVAX/USDT':['avax','Avalanche'],
    'DOT/USDT':['dot','Polkadot'], 'UNI/USDT':['uni','Uniswap'], 'NEAR/USDT':['near','NEAR Protocol'], 'SUI/USDT':['sui','Sui'],
    'SHIB/USDT':['shib','Shiba Inu'], 'HBAR/USDT':['hbar','Hedera'], 'APT/USDT':['apt','Aptos'], 'ATOM/USDT':['atom','Cosmos']
  };
  const commodity={
    'XAU/USDT':{text:'Au',bg:'#D4AF37',fg:'#17120a'},
    'XAG/USDT':{text:'Ag',bg:'#BFC4CA',fg:'#151719'},
    'WTI/USDT':{text:'WTI',bg:'#5E6570',fg:'#fff'},
    'BRENT/USDT':{text:'Br',bg:'#20252c',fg:'#f0c75e'}
  };
  const $=id=>document.getElementById(id);
  function svgIcon(o){const svg=`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><circle cx="32" cy="32" r="30" fill="${o.bg}"/><text x="32" y="36" text-anchor="middle" dominant-baseline="middle" font-family="Arial,sans-serif" font-size="${o.text.length>2?16:25}" font-weight="800" fill="${o.fg}">${o.text}</text></svg>`;return 'data:image/svg+xml;charset=UTF-8,'+encodeURIComponent(svg)}
  function apply(){document.querySelectorAll('.market').forEach(row=>{if(row.querySelector('.coin-logo'))return;const first=row.children[0];if(!first)return;const label=(first.textContent||'').trim().split(/\s+/)[0];const spec=icons[label];const comm=commodity[label];if(!spec&&!comm)return;const img=document.createElement('img');img.className='coin-logo';img.alt=(spec?spec[1]:label)+' logo';img.loading='lazy';img.width=42;img.height=42;if(spec){img.src=`https://cdn.jsdelivr.net/gh/atomiclabs/cryptocurrency-icons@master/128/color/${spec[0]}.png`;img.onerror=function(){this.onerror=null;this.src=svgIcon({text:label.split('/')[0],bg:'#d5a83f',fg:'#111'})}}else img.src=svgIcon(comm);first.prepend(img)})}
  function style(){if($('asterCoinIcons'))return;const s=document.createElement('style');s.id='asterCoinIcons';s.textContent='.market:before{display:none!important}.market{display:flex!important}.market>.coin-logo{width:42px;height:42px;min-width:42px;object-fit:contain;border-radius:50%;margin-right:11px;align-self:center}.market>span:first-child{display:block!important;min-width:0}.market>.coin-logo+span{}';document.head.appendChild(s)}
  function init(){style();apply();const root=$('app')||document.body;new MutationObserver(()=>apply()).observe(root,{childList:true,subtree:true});setTimeout(apply,400);setTimeout(apply,1200)}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
})();
