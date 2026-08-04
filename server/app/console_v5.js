(()=>{
  const q=(selector,root=document)=>root.querySelector(selector);
  document.documentElement.classList.add('tianji-console-v5');

  const topbar=q('.topbar');
  const topButtons=topbar?[...topbar.querySelectorAll('.icon-btn')]:[];
  if(topButtons[0]){
    topButtons[0].setAttribute('aria-label','切换深浅色');
    topButtons[0].setAttribute('title','切换深浅色');
  }
  if(topButtons[1]){
    topButtons[1].setAttribute('aria-label','退出控制台');
    topButtons[1].setAttribute('title','退出控制台');
  }

  const diagnostics=q('#diagnostics');
  if(diagnostics){
    let moreButton=null;
    const refresh=()=>{
      const count=diagnostics.querySelectorAll('.diag').length;
      if(count<=4){
        diagnostics.classList.remove('v5-collapsed');
        moreButton?.remove();
        moreButton=null;
        return;
      }
      if(!moreButton){
        diagnostics.classList.add('v5-collapsed');
        moreButton=document.createElement('button');
        moreButton.type='button';
        moreButton.className='v5-more';
        moreButton.textContent=`展开全部诊断（${count} 项）`;
        moreButton.addEventListener('click',()=>{
          const collapsed=diagnostics.classList.toggle('v5-collapsed');
          moreButton.textContent=collapsed?`展开全部诊断（${count} 项）`:'收起诊断';
        });
        diagnostics.insertAdjacentElement('afterend',moreButton);
      }else if(diagnostics.classList.contains('v5-collapsed')){
        moreButton.textContent=`展开全部诊断（${count} 项）`;
      }
    };
    new MutationObserver(refresh).observe(diagnostics,{childList:true});
    refresh();
  }

  document.querySelectorAll('.nav-btn').forEach(button=>{
    button.addEventListener('click',()=>{
      if(matchMedia('(max-width: 740px)').matches){
        requestAnimationFrame(()=>scrollTo({top:0,behavior:'smooth'}));
      }
    });
  });

  const updateViewport=()=>{
    document.documentElement.style.setProperty('--v5-vh',`${window.innerHeight*0.01}px`);
  };
  updateViewport();
  window.addEventListener('resize',updateViewport,{passive:true});
})();
