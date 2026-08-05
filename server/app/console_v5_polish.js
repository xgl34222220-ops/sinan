(()=>{
  const q=(selector,root=document)=>root.querySelector(selector);
  const qa=(selector,root=document)=>[...root.querySelectorAll(selector)];

  const profileList=q('#profileList');
  if(profileList){
    let expanded=false;
    const button=document.createElement('button');
    button.type='button';
    button.className='v5-account-toggle';
    profileList.insertAdjacentElement('afterend',button);

    const syncProfiles=()=>{
      const cards=qa('.profile-card',profileList);
      const activeIndex=cards.findIndex(card=>card.classList.contains('active'));
      const visibleIndex=activeIndex>=0?activeIndex:0;
      cards.forEach((card,index)=>{
        card.hidden=!expanded&&index!==visibleIndex;
      });
      const extra=Math.max(0,cards.length-1);
      button.hidden=cards.length<=1;
      button.textContent=expanded?'只看当前账户':`查看全部账户（另有 ${extra} 个）`;
    };

    button.addEventListener('click',()=>{
      expanded=!expanded;
      syncProfiles();
    });
    new MutationObserver(syncProfiles).observe(profileList,{childList:true,subtree:false});
    syncProfiles();
  }

  const controls=q('#recordsPro .v3-controls');
  if(controls){
    let expanded=false;
    const button=document.createElement('button');
    button.type='button';
    button.className='v5-filter-toggle';
    controls.insertAdjacentElement('afterend',button);

    const syncFilters=()=>{
      const mobile=matchMedia('(max-width:740px)').matches;
      controls.classList.toggle('v5-filters-collapsed',mobile&&!expanded);
      button.hidden=!mobile;
      button.textContent=expanded?'收起筛选':'更多筛选';
    };

    button.addEventListener('click',()=>{
      expanded=!expanded;
      syncFilters();
    });
    window.addEventListener('resize',syncFilters,{passive:true});
    syncFilters();
  }
})();
