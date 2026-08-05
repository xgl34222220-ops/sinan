(()=>{
  const q=(selector,root=document)=>root.querySelector(selector),qa=(selector,root=document)=>[...root.querySelectorAll(selector)];
  const esc=value=>String(value??'').replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  const fmt=value=>value?new Date(value).toLocaleString('zh-CN',{hour12:false,month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit'}):'时间未知';
  const pct=value=>value===null||value===undefined?'暂无':Math.round(Number(value)*100)+'%';
  const bytes=value=>{const n=Number(value||0);if(n<1024)return n+' B';if(n<1024**2)return(n/1024).toFixed(1)+' KB';if(n<1024**3)return(n/1024**2).toFixed(1)+' MB';return(n/1024**3).toFixed(2)+' GB'};
  const stateOf=record=>record.top6_hit===true?'hit':record.top6_hit===false?'miss':'pending';
  const stateLabel=value=>value==='hit'?'命中':value==='miss'?'未中':'待开奖';
  const api=async path=>{const response=await fetch(path,{cache:'no-store',headers:{'X-Tianji-Admin':'1'}});if(response.status===401){location.href='/admin';throw Error('登录已过期')}const data=await response.json().catch(()=>({}));if(!response.ok)throw Error(data.detail||('HTTP '+response.status));return data};
  const progress=q('#v3Progress')||(()=>{const node=document.createElement('div');node.id='v3Progress';document.body.appendChild(node);return node})();
  let busy=0;const begin=()=>{busy++;progress.classList.add('show')},end=()=>{busy=Math.max(0,busy-1);if(!busy)setTimeout(()=>progress.classList.remove('show'),130)};

  const recordsPanel=q('#panel-records');
  let recordState={source:'all',status:'all',lottery:'all',model:'',days:'0',offset:0,limit:24,total:0,models:[]};
  if(recordsPanel){
    const old=q('#recordsV2',recordsPanel);if(old)old.style.display='none';
    const workspace=document.createElement('div');workspace.id='recordsPro';workspace.innerHTML=`
      <div class="v3-summary" id="v3RecordSummary"><div class="v3-empty"><strong>正在统计全部历史</strong>读取云端档案与成绩</div></div>
      <section class="v3-section"><div class="v3-head"><div><h3>分段真实成绩</h3><p>最近 20、50、100 条已结算记录与全部历史分开统计。</p></div></div><div class="v3-window-grid" id="v3Windows"></div></section>
      <section class="v3-section"><div class="v3-head"><div><h3>模型表现</h3><p>按正式冻结模型独立统计，不把不同模型混在一起。</p></div></div><div class="v3-model-grid" id="v3Models"></div></section>
      <section class="v3-section"><div class="v3-head"><div><h3>名次成绩</h3><p>查看第 1～10 名分别生成过多少次以及真实六码命中表现。</p></div></div><div class="v3-window-grid" id="v3Positions"></div></section>
      <div class="v3-card v3-controls">
        <div class="v3-control"><label>来源</label><select class="v3-select" id="v3Source"><option value="all">全部来源</option><option value="ai">云端 AI</option><option value="native">本机云端</option></select></div>
        <div class="v3-control"><label>状态</label><select class="v3-select" id="v3Status"><option value="all">全部状态</option><option value="pending">待开奖</option><option value="hit">命中</option><option value="miss">未中</option></select></div>
        <div class="v3-control"><label>彩种</label><select class="v3-select" id="v3Lottery"><option value="all">全部彩种</option></select></div>
        <div class="v3-control"><label>模型</label><select class="v3-select" id="v3Model"><option value="">全部模型</option></select></div>
        <div class="v3-control"><label>时间范围</label><select class="v3-select" id="v3Days"><option value="0">全部历史</option><option value="7">近 7 天</option><option value="30">近 30 天</option><option value="90">近 90 天</option><option value="365">近 1 年</option></select></div>
      </div>
      <div class="v3-record-grid" id="v3RecordGrid"><div class="v3-empty"><strong>正在读取档案</strong>请稍候</div></div>
      <div class="v3-pagination"><button class="btn secondary" id="v3Prev">上一页</button><span class="v3-page-text" id="v3PageText">—</span><button class="btn secondary" id="v3Next">下一页</button></div>`;
    q('.panel-head',recordsPanel)?.insertAdjacentElement('afterend',workspace);
    const bind=(id,key)=>{q(id)?.addEventListener('change',event=>{recordState[key]=event.target.value;recordState.offset=0;loadRecords();loadInsights()})};
    bind('#v3Source','source');bind('#v3Status','status');bind('#v3Lottery','lottery');bind('#v3Model','model');bind('#v3Days','days');
    q('#v3Prev')?.addEventListener('click',()=>{recordState.offset=Math.max(0,recordState.offset-recordState.limit);loadRecords()});
    q('#v3Next')?.addEventListener('click',()=>{if(recordState.offset+recordState.limit<recordState.total){recordState.offset+=recordState.limit;loadRecords()}});
  }

  function recordCard(record){const type=record.source==='ai'?'ai':'native',status=stateOf(record),detail=[record.analysis,record.risk_note].filter(Boolean).join(' · ');return `<article class="v3-record ${type}"><div class="v3-record-top"><div class="v3-record-source"><span class="v3-source-mark">${type==='ai'?'AI':'本机'}</span><div><div class="v3-record-title">${esc(record.lottery_name)}</div><div class="v3-record-sub">${esc(record.source_name)}</div></div></div><span class="v3-state ${status}">${stateLabel(status)}</span></div><div class="v3-record-main"><div><div class="v3-rank">第 ${Number(record.position)+1} 名</div><div class="v3-record-model">${esc(record.model)}</div></div><div class="v3-period">目标期<strong>${esc(record.target_period)}</strong></div></div><div class="v3-balls">${(record.top6||[]).map(number=>`<span class="v3-ball">${number}</span>`).join('')}</div><div class="v3-record-foot"><span>训练截止 ${esc(record.trained_through_period)}</span><span>${fmt(record.created_at_epoch_ms)}</span></div>${detail?`<details class="v3-details"><summary>查看分析与风险说明</summary><p>${esc(detail)}</p></details>`:''}</article>`}
  function queryString(extra={}){const params=new URLSearchParams({source:recordState.source,status:recordState.status,lottery:recordState.lottery,model:recordState.model,days:recordState.days,limit:String(recordState.limit),offset:String(recordState.offset),...extra});return params.toString()}
  async function loadRecords(){if(!recordsPanel)return;begin();try{const data=await api('/admin/api/records?'+queryString());recordState.total=data.total;recordState.models=data.models||[];const grid=q('#v3RecordGrid');grid.innerHTML=data.items.length?data.items.map(recordCard).join(''):'<div class="v3-empty"><strong>没有符合条件的档案</strong>调整来源、状态、彩种或模型筛选</div>';const page=Math.floor(recordState.offset/recordState.limit)+1,pages=Math.max(1,Math.ceil(data.total/recordState.limit));q('#v3PageText').textContent=`第 ${page} / ${pages} 页 · 共 ${data.total} 条`;q('#v3Prev').disabled=recordState.offset===0;q('#v3Next').disabled=!data.has_more;const modelSelect=q('#v3Model');const current=recordState.model;modelSelect.innerHTML='<option value="">全部模型</option>'+data.models.map(item=>`<option value="${esc(item.model)}">${esc(item.model)} · ${item.count}</option>`).join('');modelSelect.value=current}catch(error){q('#v3RecordGrid').innerHTML=`<div class="v3-empty"><strong>档案读取失败</strong>${esc(error.message)}</div>`}finally{end()}}
  function summaryCard(label,value,foot,accent,soft){return `<article class="v3-summary-card" style="--accent:${accent};--accent-soft:${soft}"><div class="v3-summary-label">${label}</div><div class="v3-summary-value">${value}</div><div class="v3-summary-foot">${foot}</div></article>`}
  async function loadInsights(){if(!recordsPanel)return;begin();try{const params=new URLSearchParams({source:recordState.source,lottery:recordState.lottery,model:recordState.model,days:recordState.days});const data=await api('/admin/api/insights?'+params.toString()),all=data.overall,ai=data.sources.ai,native=data.sources.native;q('#v3RecordSummary').innerHTML=[summaryCard('全部历史档案',all.count,`${all.settled} 条已结算 · ${all.pending} 条待开奖`,'var(--primary)','var(--primary-soft)'),summaryCard('云端 AI',ai.count,`${pct(ai.hit_rate)} 六码命中`,'#765ff6','#eeeaff'),summaryCard('本机云端',native.count,`${pct(native.hit_rate)} 六码命中`,'#3185d8','#e9f4ff'),summaryCard('当前连续',all.streak.current,all.streak.current_type==='hit'?'连续命中':all.streak.current_type==='miss'?'连续未中':'暂无结算','var(--warn)','var(--warn-soft)')].join('');q('#v3Windows').innerHTML=['20','50','100','all'].map(key=>{const value=all.windows[key],label=key==='all'?'全部历史':'最近 '+key+' 条';return `<article class="v3-window"><span>${label}</span><strong>${pct(value.hit_rate)}</strong><span>${value.hits}/${value.settled} 命中 · 最长未中 ${all.streak.longest_miss}</span></article>`}).join('');q('#v3Models').innerHTML=data.models.length?data.models.slice(0,8).map(item=>`<article class="v3-model-card"><div class="v3-model-top"><div class="v3-model-name">${esc(item.model)}</div><span class="badge ${item.source==='ai'?'':'good'}">${item.source==='ai'?'云端 AI':'本机'}</span></div><div class="v3-model-metrics"><div class="v3-mini"><span>全部命中</span><strong>${pct(item.hit_rate)}</strong></div><div class="v3-mini"><span>正式档案</span><strong>${item.count}</strong></div><div class="v3-mini"><span>平均耗时</span><strong>${item.average_latency_seconds===null?'—':item.average_latency_seconds+'s'}</strong></div><div class="v3-mini"><span>任务失败</span><strong>${pct(item.job_failure_rate)}</strong></div></div></article>`).join(''):'<div class="v3-empty"><strong>暂无模型成绩</strong>等待正式档案结算</div>';q('#v3Positions').innerHTML=(all.positions||[]).map(item=>`<article class="v3-window"><span>第 ${Number(item.position)+1} 名</span><strong>${pct(item.hit_rate)}</strong><span>${item.hits}/${item.settled} 命中 · ${item.count} 条</span></article>`).join('')}catch(error){q('#v3RecordSummary').innerHTML=`<div class="v3-empty"><strong>统计读取失败</strong>${esc(error.message)}</div>`}finally{end()}}

  const overview=q('#panel-overview');
  if(overview){
    const draw=document.createElement('section');draw.className='section v3-section';draw.id='drawWorkspace';draw.innerHTML='<div class="v3-head"><div><h3>下一期开奖与任务</h3><p>倒计时、冻结状态和当前任务放在同一处查看。</p></div></div><div class="v3-draw-grid" id="v3DrawGrid"><div class="v3-empty"><strong>正在读取任务状态</strong>请稍候</div></div>';
    q('#adminMetrics',overview)?.insertAdjacentElement('afterend',draw);
    const ops=document.createElement('section');ops.className='section';ops.id='opsWorkspace';ops.innerHTML='<div class="v3-head"><div><h3>云端维护</h3><p>自动更新、备份、存储、数据完整性与最近任务时间线。</p></div><button class="btn secondary" id="v3RefreshOps">刷新状态</button></div><div class="v3-ops-grid" id="v3OpsGrid"></div><div class="v3-card" id="v3Integrity"></div><div class="v3-card v3-timeline" id="v3Timeline"></div>';
    overview.appendChild(ops);q('#v3RefreshOps')?.addEventListener('click',loadOperations);
  }
  function countdown(target){if(!target)return'等待时间';const diff=Number(target)-Date.now();if(diff<=0)return'等待开奖';const total=Math.floor(diff/1000),minutes=Math.floor(total/60),seconds=total%60;return`${String(minutes).padStart(2,'0')}:${String(seconds).padStart(2,'0')}`}
  function jobLabel(job,auto){if(!auto)return['已关闭','warn'];if(!job)return['等待调度','warn'];const map={queued:['排队中','warn'],running:['分析中','warn'],completed:['已冻结','good'],duplicate:['已冻结','good'],error:['调用失败','bad'],discarded:['封盘丢弃','bad'],skipped:['等待下期','warn']};return map[job.status]||['等待调度','warn']}
  async function loadDraws(){if(!overview)return;begin();try{const data=await api('/admin/api/state');const auto=!!data.ai_registry.auto_predict;q('#v3DrawGrid').innerHTML=data.lotteries.map(item=>{const ai=jobLabel(item.ai_job,auto),native=(item.forecasts||[]).find(record=>record.source==='native'&&record.target_period===item.next_period),aiRecord=(item.forecasts||[]).find(record=>record.source==='ai'&&record.target_period===item.next_period);return `<article class="v3-card v3-draw" data-target="${item.next_draw_at_epoch_ms||''}"><div class="v3-draw-top"><div><h4>${esc(item.name)}</h4><div class="sub">最新期 ${esc(item.latest_period||'等待同步')} · 目标期 ${esc(item.next_period||'—')}</div></div><div class="v3-countdown">${countdown(item.next_draw_at_epoch_ms)}</div></div><div class="v3-task-row"><div class="v3-task-chip"><strong>本机云端 · ${native?'已冻结':'等待中'}</strong><span>${native?'第 '+(Number(native.position)+1)+' 名 · '+native.top6.join(' '):'等待目标期生成'}</span></div><div class="v3-task-chip"><strong>云端 AI · ${ai[0]}</strong><span>${aiRecord?'第 '+(Number(aiRecord.position)+1)+' 名 · '+aiRecord.top6.join(' '):esc(item.ai_job?.message||item.ai_job?.model||'等待当前模型')}</span></div></div></article>`}).join('')}catch(error){q('#v3DrawGrid').innerHTML=`<div class="v3-empty"><strong>任务状态读取失败</strong>${esc(error.message)}</div>`}finally{end()}}
  setInterval(()=>qa('.v3-draw[data-target]').forEach(card=>{const value=q('.v3-countdown',card);if(value)value.textContent=countdown(card.dataset.target)}),1000);
  function updateLabel(status){const map={updated:['更新成功','good'],up_to_date:['已是最新','good'],source_synced:['代码已同步','good'],updating:['正在更新','warn'],check_failed:['检查失败','bad'],backup_failed:['备份失败','bad'],blocked:['已暂停重试','bad'],rolled_back:['已自动回滚','warn'],rollback_failed:['回滚失败','bad']};return map[status]||['状态未知','warn']}
  async function loadOperations(){if(!overview)return;begin();try{const data=await api('/admin/api/operations'),update=updateLabel(data.auto_update.status),backup=data.backup.latest,integrity=data.integrity,storage=data.storage;q('#v3OpsGrid').innerHTML=`<article class="v3-card v3-op"><div class="v3-op-icon">UP</div><h4>自动更新</h4><div class="v3-op-value ${update[1]}">${update[0]}</div><p>${esc(data.auto_update.message||'—')}<br>${fmt(data.auto_update.updated_at_epoch_ms)}</p></article><article class="v3-card v3-op"><div class="v3-op-icon">BK</div><h4>数据库备份</h4><div class="v3-op-value ${backup?'good':'warn'}">${backup?'正常':'暂无'}</div><p>${backup?esc(backup.name)+' · '+bytes(backup.size_bytes):'未找到可读取的备份'}<br>${backup?fmt(backup.updated_at_epoch_ms):'—'}</p></article><article class="v3-card v3-op"><div class="v3-op-icon">DB</div><h4>数据库</h4><div class="v3-op-value">${bytes(storage.database_size_bytes)}</div><p>SQLite ${integrity.sqlite==='ok'?'完整性正常':'需要检查'}<br>磁盘剩余 ${bytes(storage.disk_free_bytes)}</p></article><article class="v3-card v3-op"><div class="v3-op-icon">DS</div><h4>磁盘使用</h4><div class="v3-op-value ${storage.disk_used_ratio>.9?'bad':storage.disk_used_ratio>.75?'warn':'good'}">${pct(storage.disk_used_ratio)}</div><p>已用 ${bytes(storage.disk_used_bytes)}<br>总计 ${bytes(storage.disk_total_bytes)}</p></article>`;q('#v3Integrity').innerHTML=`<div class="card-pad"><div class="card-head"><div><h3>数据完整性检查</h3><p>检查 SQLite、异常开奖号码、已开奖未结算和近期可能缺失期号。</p></div><span class="badge ${integrity.ok?'good':'warn'}">${integrity.ok?'检查正常':'需要留意'}</span></div><div class="v3-integrity"><div class="v3-integrity-item"><span>SQLite</span><strong>${esc(integrity.sqlite)}</strong></div><div class="v3-integrity-item"><span>异常开奖</span><strong>${integrity.invalid_draws}</strong></div><div class="v3-integrity-item"><span>结算积压</span><strong>${integrity.settlement_backlog}</strong></div><div class="v3-integrity-item"><span>近期疑似缺期</span><strong>${integrity.recent_missing_periods_estimate}</strong></div></div>${integrity.missing_examples?.length?`<div class="notice" style="margin-top:9px">${integrity.missing_examples.map(esc).join('<br>')}</div>`:''}</div>`;q('#v3Timeline').innerHTML=data.timeline.length?data.timeline.map(event=>`<div class="v3-event"><div class="v3-event-time">${fmt(event.time).slice(6)}</div><span class="v3-event-dot ${esc(event.level)}"></span><div><div class="v3-event-title">${esc(event.title)}</div><div class="v3-event-detail">${esc(event.detail)}</div></div></div>`).join(''):'<div class="v3-empty"><strong>暂无任务记录</strong>等待下一轮同步</div>'}catch(error){q('#v3OpsGrid').innerHTML=`<div class="v3-empty"><strong>维护状态读取失败</strong>${esc(error.message)}</div>`}finally{end()}}

  let lastScroll=window.scrollY;window.addEventListener('scroll',()=>{const nav=q('.mobile-nav');if(!nav)return;const current=window.scrollY;if(current>lastScroll+10&&current>120)nav.classList.add('compact');else if(current<lastScroll-10)nav.classList.remove('compact');lastScroll=current},{passive:true});
  loadRecords();loadInsights();loadDraws();loadOperations();setInterval(()=>{loadDraws();loadOperations()},30000);
})();


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



(()=>{
  const qa=(s,r=document)=>[...r.querySelectorAll(s)];
  const enhanceBalls=(root=document)=>{
    qa('.number,.v3-ball,.ball',root).forEach(el=>{
      const n=Number(String(el.textContent||'').trim());
      if(Number.isInteger(n)&&n>=1&&n<=10)el.dataset.number=String(n);
    });
  };
  const rankDiagnostics=()=>{
    const list=document.getElementById('diagnostics');
    if(!list)return;
    const weight={bad:0,warn:1,good:2};
    const rows=[...list.children];
    rows.forEach(row=>{
      const badge=row.querySelector('.badge');
      const severity=badge?.classList.contains('bad')?'bad':badge?.classList.contains('warn')?'warn':'good';
      row.dataset.severity=severity;
    });
    const sorted=[...rows].sort((a,b)=>(weight[a.dataset.severity]??3)-(weight[b.dataset.severity]??3));
    if(sorted.some((row,index)=>row!==rows[index]))sorted.forEach(row=>list.appendChild(row));
  };
  const restorePanel=()=>{
    const name=sessionStorage.getItem('tianji-console-panel');
    if(name)document.querySelector(`.nav-btn[data-panel="${name}"]`)?.click();
  };
  qa('.nav-btn[data-panel]').forEach(btn=>btn.addEventListener('click',()=>sessionStorage.setItem('tianji-console-panel',btn.dataset.panel||'overview')));
  const label=(id,value)=>{const el=document.getElementById(id);if(el&&!el.getAttribute('aria-label'))el.setAttribute('aria-label',value)};
  label('logoutBtn','退出登录');label('runBtn','立即同步开奖与任务');
  const logoutButton=document.getElementById('logoutBtn');
  logoutButton?.addEventListener('click',event=>{if(!confirm('确认退出天机控制台？')){event.preventDefault();event.stopImmediatePropagation()}},true);
  qa('.topbar .icon-btn').forEach((el,index)=>{if(!el.getAttribute('aria-label'))el.setAttribute('aria-label',index===0?'切换明暗主题':'退出登录')});
  const syncExpandableState=()=>{
    const account=document.querySelector('.v5-account-toggle');
    const filter=document.querySelector('.v5-filter-toggle');
    if(account&&!account.dataset.v594){
      account.dataset.v594='1';account.setAttribute('aria-expanded','false');
      account.addEventListener('click',()=>{
        const expanded=account.textContent?.includes('只看当前')||false;
        account.setAttribute('aria-expanded',String(expanded));
        sessionStorage.setItem('tianji-account-expanded',String(expanded));
      });
      if(sessionStorage.getItem('tianji-account-expanded')==='true')account.click();
    }
    if(filter&&!filter.dataset.v594){
      filter.dataset.v594='1';filter.setAttribute('aria-expanded','false');
      filter.addEventListener('click',()=>{
        const expanded=filter.textContent?.includes('收起')||false;
        filter.setAttribute('aria-expanded',String(expanded));
        sessionStorage.setItem('tianji-filter-expanded',String(expanded));
      });
      if(sessionStorage.getItem('tianji-filter-expanded')==='true')filter.click();
    }
  };
  enhanceBalls();rankDiagnostics();syncExpandableState();restorePanel();
  new MutationObserver(records=>{
    records.forEach(record=>record.addedNodes.forEach(node=>{if(node.nodeType===1)enhanceBalls(node)}));
    rankDiagnostics();syncExpandableState();
  }).observe(document.body,{childList:true,subtree:true});
})();


(()=>{
  const overview=document.querySelector('#panel-overview');
  if(!overview)return;
  const esc=value=>String(value??'').replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  const workspace=document.createElement('section');
  workspace.className='section v597-watch-section';
  workspace.id='v597MissWatchWorkspace';
  workspace.innerHTML=`<div class="v3-head"><div><h3>双彩种三期不中预警</h3><p>幸运飞艇与澳洲幸运10放在同一处；每个预测来源和模型独立计算，连续三期六码未中立即报警。</p></div><span class="badge" id="v597WatchBadge">正在检查</span></div><div class="v597-watch-grid" id="v597WatchGrid"><div class="v3-empty"><strong>正在读取预测健康</strong>请稍候</div></div>`;
  const draw=document.querySelector('#drawWorkspace');
  if(draw)draw.insertAdjacentElement('afterend',workspace);else overview.prepend(workspace);

  const periodRow=item=>{
    const periods=item.recent_three||[];
    if(!periods.length)return '<div class="v597-period-empty">暂无已结算记录</div>';
    return `<div class="v597-periods">${periods.map(record=>`<span class="v597-period ${record.hit?'hit':'miss'}"><b>${esc(record.target_period)}</b><small>${record.hit?'命中':'未中'} · 第 ${Number(record.position)+1} 名</small></span>`).join('')}</div>`;
  };
  const predictionCard=item=>`<article class="v597-prediction ${item.warning?'warning':'safe'}"><div class="v597-prediction-head"><div><span class="v597-source ${item.source==='ai'?'ai':'native'}">${esc(item.source_name)}</span><strong>${esc(item.model)}</strong></div><span class="v597-streak">${item.current_miss_streak} 期未中</span></div><div class="v597-status ${item.warning?'bad':'good'}">${item.warning?'已达到三期预警':'当前未触发预警'}</div>${periodRow(item)}<div class="v597-meta">已结算 ${item.settled_records} · 待开奖 ${item.pending_records}</div></article>`;
  const lotteryCard=lottery=>`<section class="v597-lottery ${lottery.warning_count?'warning':''}"><div class="v597-lottery-head"><div><h4>${esc(lottery.name)}</h4><p>每种预测单独追踪连续未中</p></div><span class="badge ${lottery.warning_count?'bad':'good'}">${lottery.warning_count?lottery.warning_count+' 项预警':'全部正常'}</span></div><div class="v597-prediction-list">${lottery.predictions?.length?lottery.predictions.map(predictionCard).join(''):'<div class="v3-empty"><strong>暂无预测记录</strong>等待云端产生并完成结算</div>'}</div></section>`;

  async function loadMissWatch(){
    const grid=document.querySelector('#v597WatchGrid'),badge=document.querySelector('#v597WatchBadge');
    if(!grid||!badge)return;
    try{
      const response=await fetch('/admin/api/operations',{cache:'no-store',headers:{'X-Tianji-Admin':'1'}});
      if(response.status===401){location.href='/admin';return}
      const data=await response.json();
      if(!response.ok)throw Error(data.detail||('HTTP '+response.status));
      const watch=data.miss_watch||{warning_count:0,lotteries:[]};
      badge.className='badge '+(watch.warning_count?'bad':'good');
      badge.textContent=watch.warning_count?`${watch.warning_count} 项预警`:'暂无三期预警';
      grid.innerHTML=watch.lotteries?.length?watch.lotteries.map(lotteryCard).join(''):'<div class="v3-empty"><strong>暂无预警数据</strong>等待正式预测完成结算</div>';
    }catch(error){
      badge.className='badge warn';badge.textContent='读取失败';
      grid.innerHTML=`<div class="v3-empty"><strong>预警读取失败</strong>${esc(error.message)}</div>`;
    }
  }
  loadMissWatch();
  setInterval(loadMissWatch,30000);
})();
