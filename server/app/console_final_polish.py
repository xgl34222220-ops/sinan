from __future__ import annotations


_FINAL_STYLE = r"""
/* Tianji v6.8 consolidated experience layer: restrained surfaces + end-to-end latency details. */
.tianji-console-v620{
  --v68-card-radius:18px;
  --v68-control-radius:13px;
  --v68-caption-size:11px;
}
.tianji-console-v620 .v510-platform-card,
.tianji-console-v620 .v510-deploy,
.tianji-console-v620 .v620-realtime-card{border-radius:var(--v68-card-radius)}
.tianji-console-v620 .v510-stage,
.tianji-console-v620 .v620-latency{border-radius:var(--v68-control-radius)}
.tianji-console-v620 .v620-realtime-card{
  box-shadow:none;
  background:color-mix(in srgb,var(--surface) 98%,var(--primary-soft) 2%);
}
.tianji-console-v620 .v620-latency{background:color-mix(in srgb,var(--soft) 92%,transparent)}
.v68-pipeline{
  display:grid;
  grid-template-columns:repeat(4,minmax(0,1fr));
  gap:7px;
  margin-top:8px;
  padding-top:8px;
  border-top:1px solid var(--line);
}
.v68-pipeline-item{
  min-width:0;
  padding:8px 9px;
  border-radius:12px;
  background:color-mix(in srgb,var(--soft) 92%,transparent);
  border:1px solid var(--line);
}
.v68-pipeline-item span{display:block;color:var(--muted);font-size:10px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.v68-pipeline-item strong{display:block;margin-top:3px;font-size:13px;letter-spacing:-.02em;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.v68-pipeline-item small{display:block;margin-top:2px;color:var(--muted);font-size:9px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.v68-pipeline-item.warn strong{color:var(--warn)}
.v68-pipeline-item.bad strong{color:var(--bad)}
.v68-pipeline-summary{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-top:7px;color:var(--muted);font-size:10px}
.v68-pipeline-summary b{color:var(--text);font-weight:780}

/* v6.10: AI workspace should read like a product dashboard, not a setup form. */
.tianji-console-v620 .model-choice.active{
  color:var(--text)!important;
  border:2px solid var(--primary)!important;
  background:var(--primary-soft)!important;
  box-shadow:0 10px 24px rgba(50,111,232,.14)!important;
}
.tianji-console-v620 .model-choice.active strong{color:var(--primary)!important}
.tianji-console-v620 .model-choice.active span{color:var(--text2)!important;opacity:1!important}
.tianji-console-v620 .quick-actions.models-ready #readQuickModelsBtn{
  min-height:34px;
  padding:0 10px;
  font-size:10px;
  background:var(--soft);
  color:var(--text2);
  border:1px solid var(--line);
  box-shadow:none;
}
.tianji-console-v620 .quick-actions #manageCurrentBtn{margin-left:auto}
.v610-ai-runtime{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;margin-top:12px}
.v610-ai-job{position:relative;overflow:hidden;padding:12px;border:1px solid var(--line);border-radius:16px;background:var(--soft)}
.v610-ai-job:before{content:"";position:absolute;inset:0 auto 0 0;width:3px;background:var(--primary);opacity:.75}
.v610-ai-job.good:before{background:var(--good)}
.v610-ai-job.warn:before{background:var(--warn)}
.v610-ai-job.bad:before{background:var(--bad)}
.v610-ai-job-head{display:flex;align-items:flex-start;justify-content:space-between;gap:8px}
.v610-ai-job-title{min-width:0}.v610-ai-job-title strong{display:block;font-size:11px}.v610-ai-job-title span{display:block;margin-top:2px;color:var(--muted);font-size:9px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.v610-ai-job-status{flex:0 0 auto;padding:4px 7px;border-radius:999px;background:var(--primary-soft);color:var(--primary);font-size:8px;font-weight:800}
.v610-ai-job.good .v610-ai-job-status{background:var(--good-soft);color:var(--good)}
.v610-ai-job.warn .v610-ai-job-status{background:var(--warn-soft);color:var(--warn)}
.v610-ai-job.bad .v610-ai-job-status{background:var(--bad-soft);color:var(--bad)}
.v610-ai-job-meta{margin-top:7px;color:var(--text2);font-size:9px;line-height:1.55}
.v610-ai-budget{height:5px;margin-top:8px;border-radius:999px;background:var(--line);overflow:hidden}
.v610-ai-budget i{display:block;height:100%;border-radius:inherit;background:linear-gradient(90deg,var(--primary),var(--primary2));transition:width .35s ease}
.v610-ai-job.warn .v610-ai-budget i{background:var(--warn)}
.v610-ai-job.bad .v610-ai-budget i{background:var(--bad)}
.v610-ai-foot{display:flex;justify-content:space-between;gap:8px;margin-top:5px;color:var(--muted);font-size:8px}

@supports not (color:color-mix(in srgb,#000 50%,#fff)){
  body{background:var(--bg)}
  .topbar,.hero,.card,.metric,.lottery-card,.sidebar,.icon-btn,.status{background:var(--surface)}
  .model-choice{background:var(--solid)}
  .model-choice.active{background:var(--primary-soft)!important;border-color:var(--primary)!important}
}

@media(max-width:760px){.v68-pipeline{grid-template-columns:repeat(2,minmax(0,1fr))}.v610-ai-runtime{grid-template-columns:1fr}}
@media(max-width:520px){
  .v68-pipeline{grid-template-columns:repeat(2,minmax(0,1fr));gap:6px}
  .v68-pipeline-item{padding:7px 8px}
  .v68-pipeline-item span,.v68-pipeline-summary{font-size:10px}
  .v68-pipeline-item strong{font-size:12px}
  .tianji-console-v620 .mobile-nav .nav-btn{font-size:11px!important}
  .tianji-console-v620 .quick-actions{align-items:center}
  .tianji-console-v620 .quick-actions #manageCurrentBtn{margin-left:0}
}
@media(prefers-reduced-motion:reduce){*,*:before,*:after{scroll-behavior:auto!important;animation-duration:.01ms!important;animation-iteration-count:1!important;transition-duration:.01ms!important}}
"""

_FINAL_SCRIPT = r"""
(()=>{
  const duration=value=>value===null||value===undefined?'—':Number(value)<1000?Math.round(Number(value))+' ms':(Number(value)/1000).toFixed(1)+' s';
  const tone=value=>{
    const n=Number(value);
    if(!Number.isFinite(n))return'';
    if(n>12000)return'bad';
    if(n>5000)return'warn';
    return'';
  };
  const metric=(label,current,p50,p95)=>`<div class="v68-pipeline-item ${tone(current)}"><span>${label}</span><strong>${duration(current)}</strong><small>P50 ${duration(p50)} · P95 ${duration(p95)}</small></div>`;
  const clock=value=>{
    const ms=Math.max(0,Number(value)||0),s=Math.floor(ms/1000),m=Math.floor(s/60);
    return m>0?`${m}:${String(s%60).padStart(2,'0')}`:`${s}s`;
  };
  const aiStatus=value=>({queued:'排队中',running:'分析中',completed:'已冻结',duplicate:'已冻结',discarded:'截止丢弃',error:'连接失败',disabled:'AI 已关闭',skipped:'本期不启动'}[value]||'等待中');
  const aiTone=value=>value==='completed'||value==='duplicate'?'good':value==='discarded'||value==='error'?'bad':value==='skipped'||value==='disabled'?'warn':'';
  let timer=0,aiState=null;

  function polishModelControls(){
    const switcher=document.getElementById('modelSwitcher'),actions=document.querySelector('.quick-actions'),read=document.getElementById('readQuickModelsBtn'),manage=document.getElementById('manageCurrentBtn');
    const ready=Boolean(switcher&&switcher.children.length);
    if(actions)actions.classList.toggle('models-ready',ready);
    if(read){read.textContent=ready?'重新读取模型':'读取此 Key 支持的模型';read.classList.toggle('primary',!ready);read.classList.toggle('secondary',ready)}
    if(manage)manage.textContent='接口与 Key ›';
  }

  function ensureAiRuntime(){
    let host=document.getElementById('v610AiRuntime');
    if(host)return host;
    const inner=document.querySelector('.quick-card .quick-inner');
    if(!inner)return null;
    host=document.createElement('div');host.id='v610AiRuntime';host.className='v610-ai-runtime';
    const note=inner.querySelector('.quick-note');
    if(note)inner.insertBefore(host,note);else inner.appendChild(host);
    return host;
  }

  function renderAiRuntime(){
    const host=ensureAiRuntime();if(!host||!aiState)return;
    const now=Date.now(),enabled=aiState.ai_lottery_auto||{};
    host.innerHTML=(aiState.lotteries||[]).map(item=>{
      const job=item.ai_job||{},isEnabled=enabled[item.key]!==false;
      const status=isEnabled?(job.status||'waiting'):'disabled';
      const claimed=Number(job.claimed_at||0),updated=Number(job.updated_at||0),next=Number(item.next_draw_at_epoch_ms||0);
      const elapsed=claimed?Math.max(0,(status==='running'||status==='queued'?now:updated||now)-claimed):0;
      const guardAt=next?next-40000:0,guardLeft=guardAt?guardAt-now:0,total=claimed&&guardAt>claimed?guardAt-claimed:0;
      const pct=status==='running'&&total?Math.max(2,Math.min(100,elapsed/total*100)):status==='completed'||status==='duplicate'?100:status==='discarded'?100:0;
      const meta=status==='running'||status==='queued'
        ?`已用时 ${clock(elapsed)} · 距 40 秒硬截止 ${guardAt?clock(guardLeft):'—'}`
        :status==='disabled'?'开奖同步与服务器模型继续运行':(job.message||'等待下一期满足启动条件');
      const model=job.model||aiState.ai?.model||'未选择模型';
      return `<div class="v610-ai-job ${aiTone(status)}"><div class="v610-ai-job-head"><div class="v610-ai-job-title"><strong>${item.name||item.key}</strong><span>目标 ${job.target_period||item.next_period||'待同步'} · ${model}</span></div><span class="v610-ai-job-status">${aiStatus(status)}</span></div><div class="v610-ai-job-meta">${meta}</div>${status==='running'||status==='queued'||pct===100?`<div class="v610-ai-budget"><i style="width:${pct}%"></i></div><div class="v610-ai-foot"><span>${status==='running'?'完整评审处理中':'任务已进入队列'}</span><span>${next?'开奖 '+clock(next-now):''}</span></div>`:''}</div>`;
    }).join('');
  }

  async function pullAiState(){
    try{
      if(document.hidden)return;
      const response=await fetch('/admin/api/state',{cache:'no-store'});
      if(response.ok){aiState=await response.json();renderAiRuntime()}
    }catch(_error){}
  }

  async function enrich(){
    window.clearTimeout(timer);
    let delay=7000;
    try{
      if(document.hidden){timer=window.setTimeout(enrich,delay);return}
      const response=await fetch('/admin/api/realtime',{cache:'no-store'});
      if(!response.ok)throw new Error('realtime');
      const data=await response.json();
      const section=document.getElementById('v620Realtime');
      if(section){
        for(const item of data.lotteries||[]){
          const card=[...section.querySelectorAll('.v620-realtime-card')].find(node=>node.querySelector('.v620-realtime-title strong')?.textContent?.trim()===String(item.name||item.key).trim());
          if(!card)continue;
          card.querySelector('.v68-pipeline')?.remove();
          card.querySelector('.v68-pipeline-summary')?.remove();
          const grid=document.createElement('div');
          grid.className='v68-pipeline';
          grid.innerHTML=[
            metric('开奖发现',item.detection_delay_ms,item.detection_delay_p50_ms,item.detection_delay_p95_ms),
            metric('写库结算',item.settlement_latency_ms,item.settlement_latency_p50_ms,item.settlement_latency_p95_ms),
            metric('App/FCM 投递',item.push_latency_ms,item.push_p50_ms,item.push_p95_ms),
            metric('完整预测周期',item.full_cycle_duration_ms,item.full_cycle_p50_ms,item.full_cycle_p95_ms),
          ].join('');
          const anchor=card.querySelector('.v620-latency-grid');
          if(anchor)anchor.insertAdjacentElement('afterend',grid); else card.appendChild(grid);
          const summary=document.createElement('div');
          summary.className='v68-pipeline-summary';
          summary.innerHTML=`<span>投递总链路 <b>${duration(item.delivery_latency_ms)}</b> · Telegram <b>${duration(item.telegram_latency_ms)}</b></span><span>${item.push_ok===false?'FCM 异常':item.telegram_ok===false?'Telegram 异常':'链路正常'}</span>`;
          grid.insertAdjacentElement('afterend',summary);
        }
      }
      const targets=(data.lotteries||[]).map(item=>Number(item.next_draw_at_epoch_ms||0)).filter(Boolean);
      if(targets.some(target=>target-Date.now()>=-90000&&target-Date.now()<=180000))delay=3000;
    }catch(_error){delay=5000}
    timer=window.setTimeout(enrich,delay);
  }

  const switcher=document.getElementById('modelSwitcher');
  if(switcher)new MutationObserver(polishModelControls).observe(switcher,{childList:true,subtree:false});
  polishModelControls();
  pullAiState();
  window.setInterval(()=>{renderAiRuntime();polishModelControls()},1000);
  window.setInterval(pullAiState,5000);
  enrich();
})();
"""

_INSTALLED = False


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    from . import console_v3

    style_marker = "Tianji v6.8 consolidated experience layer"
    if style_marker not in console_v3.V510_STYLE:
        console_v3.V510_STYLE += _FINAL_STYLE
    script_marker = "v68-pipeline"
    if script_marker not in console_v3.FILTER_PATCH:
        console_v3.FILTER_PATCH += _FINAL_SCRIPT
    _INSTALLED = True
