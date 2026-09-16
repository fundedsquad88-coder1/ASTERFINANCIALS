(function(){
  const oldStartMarket=window.startMarket;
  let chart=null,series=null,socket=null,active='BTCUSDT',interval='1m',resizeObserver=null;
  const $=id=>document.getElementById(id);
  const labels={BTCUSDT:'BTC/USDT',ETHUSDT:'ETH/USDT',BNBUSDT:'BNB/USDT',XRPUSDT:'XRP/USDT',SOLUSDT:'SOL/USDT',TRXUSDT:'TRX/USDT',DOGEUSDT:'DOGE/USDT',LINKUSDT:'LINK/USDT',ADAUSDT:'ADA/USDT',LTCUSDT:'LTC/USDT',BCHUSDT:'BCH/USDT',AVAXUSDT:'AVAX/USDT',DOTUSDT:'DOT/USDT',UNIUSDT:'UNI/USDT',NEARUSDT:'NEAR/USDT',SUIUSDT:'SUI/USDT',SHIBUSDT:'SHIB/USDT',HBARUSDT:'HBAR/USDT',APTUSDT:'APT/USDT',ATOMUSDT:'ATOM/USDT',XAUUSDT:'XAU/USDT',XAGUSDT:'XAG/USDT',WTIUSDT:'WTI/USDT',BRENTUSDT:'BRENT/USDT'};
  function destroy(){
    if(socket){try{socket.close()}catch(e){} socket=null;}
    if(resizeObserver){try{resizeObserver.disconnect()}catch(e){} resizeObserver=null;}
    if(chart){try{chart.remove()}catch(e){} chart=null;series=null;}
    const el=$('chart');if(el)el.innerHTML='';
  }
  function setup(){
    const L=window.LightweightCharts,el=$('chart');
    if(!L||!el)return false;
    const w=Math.max(1,el.clientWidth),h=Math.max(1,el.clientHeight);
    chart=L.createChart(el,{width:w,height:h,layout:{background:{type:'solid',color:'#070808'},textColor:'#858585'},grid:{vertLines:{color:'#171818'},horzLines:{color:'#171818'}},rightPriceScale:{borderColor:'#282828',scaleMargins:{top:.08,bottom:.08}},timeScale:{borderColor:'#282828',timeVisible:true,secondsVisible:false,rightOffset:4,barSpacing:8},crosshair:{mode:1}});
    series=chart.addSeries(L.CandlestickSeries,{upColor:'#20c77a',downColor:'#ef5555',borderVisible:false,wickUpColor:'#20c77a',wickDownColor:'#ef5555'});
    const resize=()=>{if(chart&&el.clientWidth&&el.clientHeight)chart.resize(el.clientWidth,el.clientHeight,true)};
    if(window.ResizeObserver){resizeObserver=new ResizeObserver(resize);resizeObserver.observe(el)}
    window.addEventListener('resize',resize,{passive:true});
    return true;
  }
  async function start(sym){
    active=sym||active;
    if(active==='XAUUSDT'&&typeof oldStartMarket==='function')return oldStartMarket(active);
    const request=active;
    destroy();
    $('pair').textContent=labels[request]||request;
    $('feed').textContent='CONNECTING';
    $('price').textContent='—';
    if(!setup()){ $('feed').textContent='UNAVAILABLE'; return; }
    try{
      const r=await fetch('https://api.binance.com/api/v3/klines?symbol='+encodeURIComponent(request)+'&interval='+encodeURIComponent(interval)+'&limit=300',{cache:'no-store'});
      if(!r.ok)throw Error('Market data request failed');
      const data=await r.json();
      if(active!==request)return;
      const bars=data.map(k=>({time:Math.floor(Number(k[0])/1000),open:Number(k[1]),high:Number(k[2]),low:Number(k[3]),close:Number(k[4])})).filter(b=>Number.isFinite(b.time)&&[b.open,b.high,b.low,b.close].every(Number.isFinite));
      if(!bars.length)throw Error('No chart data received');
      series.setData(bars);
      chart.timeScale().fitContent();
      chart.resize($('chart').clientWidth,$('chart').clientHeight,true);
      $('price').textContent=bars[bars.length-1].close.toLocaleString();
      $('feed').textContent='LIVE';
      socket=new WebSocket('wss://stream.binance.com:9443/ws/'+request.toLowerCase()+'@kline_'+interval);
      socket.onmessage=e=>{try{const k=JSON.parse(e.data).k;if(!k||active!==request)return;const b={time:Math.floor(Number(k.t)/1000),open:Number(k.o),high:Number(k.h),low:Number(k.l),close:Number(k.c)};if(series)series.update(b);$('price').textContent=b.close.toLocaleString()}catch(err){}};
      socket.onerror=()=>{if(active===request)$('feed').textContent='LIVE DATA · WS RETRY'};
      socket.onclose=()=>{if(active===request)$('feed').textContent='DISCONNECTED'};
    }catch(e){if(active===request){$('feed').textContent='UNAVAILABLE';$('price').textContent='—';}}
  }
  window.startMarket=start;
  const oldShow=window.show;
  window.show=function(id){
    if(id==='trade'){
      document.querySelectorAll('.screen').forEach(x=>x.classList.remove('active'));
      const trade=$('trade');if(trade)trade.classList.add('active');
      document.querySelectorAll('.nav button').forEach((b,i)=>b.classList.toggle('on',i===2));
      setTimeout(()=>start(active),60);
      return;
    }
    if(typeof oldShow==='function')oldShow(id);
  };
  const p=$('periods');
  if(p)p.addEventListener('click',e=>{const b=e.target.closest('button[data-i]');if(!b)return;interval=b.dataset.i;setTimeout(()=>start(active),0)});
})();
