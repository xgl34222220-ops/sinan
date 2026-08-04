(()=>{
  const root=document.documentElement;
  root.classList.remove('tianji-console-v4','tianji-console-v5');
  root.classList.add('tianji-console-v6');

  const q=(selector,scope=document)=>scope.querySelector(selector);
  const qa=(selector,scope=document)=>[...scope.querySelectorAll(selector)];

  const topbar=q('.topbar');
  const topButtons=topbar?qa('.icon-btn',topbar):[];
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
    const refreshDiagnostics=()=>{
      const count=diagnostics.querySelectorAll('.diag').length;
      if(count<=4){
        diagnostics.classList.remove('c6-collapsed');
        moreButton?.remove();
        moreButton=null;
        return;
      }
      if(!moreButton){
        diagnostics.classList.add('c6-collapsed');
        moreButton=document.createElement('button');
        moreButton.type='button';
        moreButton.className='c6-more';
        diagnostics.insertAdjacentElement('afterend',moreButton);
        moreButton.addEventListener('click',()=>{
          const collapsed=diagnostics.classList.toggle('c6-collapsed');
          moreButton.textContent=collapsed?`展开全部诊断（${count} 项）`:'收起诊断';
        });
      }
      moreButton.textContent=diagnostics.classList.contains('c6-collapsed')
        ?`展开全部诊断（${count} 项）`:'收起诊断';
    };
    new MutationObserver(refreshDiagnostics).observe(diagnostics,{childList:true,subtree:false});
    refreshDiagnostics();
  }

  const mobileNav=q('.mobile-nav');
  let previousY=window.scrollY;
  let ticking=false;
  const updateNavVisibility=()=>{
    ticking=false;
    if(!mobileNav||!matchMedia('(max-width:740px)').matches){
      mobileNav?.classList.remove('c6-hidden');
      previousY=window.scrollY;
      return;
    }
    const current=window.scrollY;
    const delta=current-previousY;
    if(current<70||delta<-8){
      mobileNav.classList.remove('c6-hidden');
    }else if(delta>10&&current>160){
      mobileNav.classList.add('c6-hidden');
    }
    previousY=current;
  };
  window.addEventListener('scroll',()=>{
    if(!ticking){
      ticking=true;
      requestAnimationFrame(updateNavVisibility);
    }
  },{passive:true});

  qa('.nav-btn').forEach(button=>{
    button.addEventListener('click',()=>{
      mobileNav?.classList.remove('c6-hidden');
      if(matchMedia('(max-width:740px)').matches){
        requestAnimationFrame(()=>window.scrollTo({top:0,behavior:'smooth'}));
      }
    });
  });

  const decoratePanelHeads=()=>{
    qa('.panel-head').forEach(head=>{
      if(head.dataset.c6Ready)return;
      head.dataset.c6Ready='1';
      const title=q('h2',head)?.textContent?.trim();
      if(title)head.setAttribute('aria-label',title);
    });
  };
  decoratePanelHeads();

  const setViewport=()=>{
    root.style.setProperty('--c6-vh',`${window.innerHeight*.01}px`);
  };
  setViewport();
  window.addEventListener('resize',setViewport,{passive:true});
  window.addEventListener('orientationchange',setViewport,{passive:true});

  const observer=new MutationObserver(()=>{
    decoratePanelHeads();
    if(mobileNav&&window.scrollY<70)mobileNav.classList.remove('c6-hidden');
  });
  observer.observe(document.body,{childList:true,subtree:true});
})();
