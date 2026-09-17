(function(){
  function ensureMarketsScreen(){
    let root=document.getElementById('markets');
    if(!root){
      const app=document.querySelector('.app');
      if(!app)return null;
      root=document.createElement('div');
      root.id='markets';
      root.className='screen';
      app.appendChild(root);
    }
    return root;
  }
  function hideLegacyHomeMarkets(){
    const home=document.getElementById('home');
    if(!home)return;
    home.querySelectorAll('.market').forEach(row=>{
      const section=row.closest('.section');
      if(section)section.classList.add('legacyMarketsHidden');
    });
  }
  const css='.legacyMarketsHidden{display:none!important}.m26Boot{padding:30px 18px;text-align:center;color:var(--muted,#8d94a3);font-size:11px}';
  document.head.insertAdjacentHTML('beforeend','<style>'+css+'</style>');
  hideLegacyHomeMarkets();
  ensureMarketsScreen();
  const previousShow=window.show;
  window.show=function(id){
    if(id==='markets'){
      const root=ensureMarketsScreen();
      if(!root)return;
      document.querySelectorAll('.screen').forEach(x=>x.classList.remove('active'));
      root.classList.add('active');
      document.querySelectorAll('.nav button').forEach(x=>x.classList.remove('on','active'));
      const buttons=document.querySelectorAll('.nav button');
      if(buttons[1])buttons[1].classList.add('on','active');
      if(previousShow)previousShow('markets');
      root.classList.add('active');
      window.scrollTo(0,0);
      return;
    }
    if(previousShow)previousShow(id);
  };
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',function(){hideLegacyHomeMarkets();ensureMarketsScreen();});
})();