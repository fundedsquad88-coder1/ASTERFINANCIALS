(function(){
  const oldShow=window.show;
  window.show=function(id){ if(id==='trade') id='markets'; return oldShow?oldShow(id):undefined; };
  document.querySelectorAll('.action').forEach(b=>{ if((b.textContent||'').includes('Trade')){b.style.display='none';} });
  const trade=document.getElementById('trade'); if(trade) trade.setAttribute('aria-hidden','true');
})();