from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from . import web_console as _web_console
from .public_v4 import enhance_public_html


V510_STYLE = r"""
:where(button,a,input,select,summary):focus-visible{outline:3px solid color-mix(in srgb,var(--primary) 32%,transparent);outline-offset:2px}
#recordsPro .v3-controls{position:sticky;top:64px;z-index:18;background:color-mix(in srgb,var(--surface) 94%,transparent);backdrop-filter:blur(18px);-webkit-backdrop-filter:blur(18px)}
.v510-platform{margin-top:10px}.v510-platform-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:9px}.v510-platform-card{padding:14px;border:1px solid var(--line);border-radius:19px;background:var(--surface);box-shadow:var(--shadow2)}.v510-platform-card span{display:block;color:var(--muted);font-size:11px}.v510-platform-card strong{display:block;margin-top:6px;font-size:15px;overflow-wrap:anywhere}.v510-platform-card small{display:block;margin-top:4px;color:var(--muted);font-size:11px;line-height:1.45}.v510-stage-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:7px;margin-top:10px}.v510-stage{display:flex;align-items:center;justify-content:space-between;gap:8px;padding:9px 10px;border-radius:13px;border:1px solid var(--line);background:var(--soft);font-size:11px}.v510-stage b{font-size:12px}.v510-stage.error{color:var(--bad);background:var(--bad-soft)}.v510-stage.ok b{color:var(--good)}
.v510-deploy{display:grid;grid-template-columns:minmax(0,1.4fr) repeat(3,minmax(0,.7fr));gap:10px;align-items:center;margin-top:10px;padding:14px 15px;border:1px solid var(--line);border-radius:19px;background:linear-gradient(135deg,var(--primary-soft),var(--surface));box-shadow:var(--shadow2)}.v510-deploy.attention{background:linear-gradient(135deg,var(--bad-soft),var(--surface));border-color:color-mix(in srgb,var(--bad) 22%,var(--line))}.v510-deploy-main{min-width:0}.v510-deploy-title{display:flex;align-items:center;gap:7px;font-size:13px;font-weight:820}.v510-deploy-dot{width:8px;height:8px;border-radius:50%;background:var(--good);box-shadow:0 0 0 5px color-mix(in srgb,var(--good) 13%,transparent)}.v510-deploy.attention .v510-deploy-dot{background:var(--bad);box-shadow:0 0 0 5px color-mix(in srgb,var(--bad) 12%,transparent)}.v510-deploy-message{margin-top:4px;color:var(--muted);font-size:11px;line-height:1.55}.v510-deploy-meta span{display:block;color:var(--muted);font-size:11px}.v510-deploy-meta strong{display:block;margin-top:4px;font-size:12px;overflow-wrap:anywhere}.v510-commit{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;letter-spacing:.02em}
.v630-health-summary{display:flex;align-items:center;justify-content:space-between;gap:10px}.v630-health-summary strong{display:block;font-size:14px}.v630-health-summary small{display:block;margin-top:2px;color:var(--muted);font-size:10px;line-height:1.45}.v630-healthbar{display:flex;gap:8px;flex-wrap:wrap;margin-top:9px}.v630-health-pill{display:flex;align-items:center;gap:7px;min-height:35px;padding:0 11px;border-radius:999px;border:1px solid var(--line);background:var(--soft);font-size:11px;font-weight:760}.v630-health-pill i{width:8px;height:8px;border-radius:50%;background:var(--good);box-shadow:0 0 0 4px color-mix(in srgb,var(--good) 12%,transparent)}.v630-health-pill.warn i{background:var(--warn);box-shadow:0 0 0 4px color-mix(in srgb,var(--warn) 12%,transparent)}.v630-health-pill.bad i{background:var(--bad);box-shadow:0 0 0 4px color-mix(in srgb,var(--bad) 12%,transparent)}.v630-health-details{margin-top:8px}.v630-health-details>summary{cursor:pointer;list-style:none;color:var(--muted);font-size:11px;font-weight:760;padding:7px 2px}.v630-health-details>summary::-webkit-details-marker{display:none}.v630-health-details>summary:after{content:'展开详情';margin-left:7px;color:var(--primary)}.v630-health-details[open]>summary:after{content:'收起详情'}
.v620-realtime{margin-top:11px}.v620-realtime-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:11px;margin-top:10px}.v620-realtime-card{padding:15px;border:1px solid var(--line);border-radius:20px;background:linear-gradient(145deg,color-mix(in srgb,var(--primary-soft) 34%,var(--surface)),var(--surface));box-shadow:var(--shadow2)}.v620-realtime-card.bad{border-color:color-mix(in srgb,var(--bad) 30%,var(--line));background:linear-gradient(145deg,color-mix(in srgb,var(--bad-soft) 58%,var(--surface)),var(--surface))}.v620-realtime-card.warn{border-color:color-mix(in srgb,var(--warn) 26%,var(--line));background:linear-gradient(145deg,color-mix(in srgb,var(--warn-soft) 54%,var(--surface)),var(--surface))}.v620-realtime.stale .v620-realtime-card{opacity:.72}.v620-realtime-head{display:flex;align-items:center;justify-content:space-between;gap:9px}.v620-realtime-title{display:flex;align-items:center;gap:7px;min-width:0}.v620-realtime-title strong{font-size:15px}.v620-card-state{display:inline-flex;align-items:center;min-height:23px;padding:0 8px;border-radius:999px;background:var(--good-soft);color:var(--good);font-size:10px;font-weight:820}.v620-card-state.warn{background:var(--warn-soft);color:var(--warn)}.v620-card-state.bad{background:var(--bad-soft);color:var(--bad)}.v620-realtime-head>span{font-size:11px;color:var(--muted);white-space:nowrap}.v620-latency-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin-top:11px}.v620-latency{padding:10px;border-radius:14px;background:var(--soft);border:1px solid var(--line)}.v620-latency span{display:block;font-size:11px;color:var(--muted)}.v620-latency strong{display:block;margin-top:4px;font-size:17px;letter-spacing:-.03em}.v620-latency em{display:block;margin-top:3px;font-style:normal;font-size:11px;color:var(--muted)}.v620-realtime-foot{display:flex;justify-content:space-between;gap:10px;margin-top:9px;color:var(--muted);font-size:11px;line-height:1.5}.v620-realtime-foot b{color:var(--text);font-weight:760}.v620-build{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:11px;color:var(--muted)}.v620-fresh{display:inline-flex;align-items:center;min-height:25px;padding:0 8px;border-radius:999px;font-size:11px;font-weight:760;background:var(--good-soft);color:var(--good);margin-left:7px}.v620-fresh.warn{background:var(--warn-soft);color:var(--warn)}
.tianji-console-v620 .metric-label,.tianji-console-v620 .section-head p,.tianji-console-v620 .panel-head p,.tianji-console-v620 .card-head p,.tianji-console-v620 .sub,.tianji-console-v620 .quick-meta,.tianji-console-v620 .quick-note,.tianji-console-v620 .profile-model,.tianji-console-v620 .profile-endpoint{font-size:max(11px,1em)}.tianji-console-v620 .metric-foot,.tianji-console-v620 .badge,.tianji-console-v620 .target,.tianji-console-v620 .empty,.tianji-console-v620 .disclaimer{font-size:11px}.tianji-console-v620 .nav-tail,.tianji-console-v620 .side-label{font-size:10px}
/* v6.5 UI Final Polish 2: shared density + semantic token layer */
.tianji-console-v620{--v65-card-radius:18px;--v65-control-radius:14px;--v65-gap:9px}
.tianji-console-v620 .card,.tianji-console-v620 .lottery-card{border-radius:var(--v65-card-radius)}
.tianji-console-v620 .btn,.tianji-console-v620 .icon-btn,.tianji-console-v620 .status{border-radius:var(--v65-control-radius)}
.tianji-console-v620 .v620-realtime-card{border-radius:var(--v65-card-radius)}
.tianji-console-v620 .v630-health-pill{font-size:11px}
@media(max-width:1040px){.v510-platform-grid{grid-template-columns:repeat(3,minmax(0,1fr))}.v510-deploy{grid-template-columns:repeat(3,minmax(0,1fr))}.v510-deploy-main{grid-column:1/-1}}
@media(max-width:760px){.v510-platform-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.v510-stage-grid{grid-template-columns:1fr}.v510-deploy{grid-template-columns:1fr 1fr}#recordsPro .v3-controls{top:57px}.v620-realtime-grid{grid-template-columns:1fr}}
@media(max-width:520px){
  .tianji-console-v620 .shell{padding-bottom:calc(108px + env(safe-area-inset-bottom))!important}
  .tianji-console-v620 .topbar{min-height:52px;margin-bottom:8px;padding:5px 7px;border-radius:17px}
  .tianji-console-v620 .topbar .mark{width:34px;height:34px;flex-basis:34px;border-radius:12px}
  .tianji-console-v620 .topbar .mark{display:none}.tianji-console-v620 .topbar .brand h1{display:none}.tianji-console-v620 .topbar .brand p{display:none}
  .tianji-console-v620 .topbar .icon-btn{width:36px;height:36px;min-height:36px;border-radius:12px}
  .tianji-console-v620 .panel-head{margin-bottom:7px;align-items:center}.tianji-console-v620 .panel-head h2{font-size:20px}.tianji-console-v620 .panel-head p{display:none}.tianji-console-v620 #runBtn{min-height:36px;padding:0 11px}
  .v510-platform-grid,.v510-deploy{grid-template-columns:1fr}.v510-deploy-main{grid-column:auto}.v630-health-pill{flex:1 1 calc(50% - 8px);justify-content:flex-start;min-height:34px;padding:0 9px;font-size:11px}.v630-health-summary small{display:none}.v630-health-details{margin-top:5px}
  .v620-realtime{margin-top:8px}.v620-realtime .v3-head{align-items:center;margin-bottom:0}.v620-realtime .v3-head p,.v620-build{display:none}.v620-realtime-card{padding:12px;border-radius:17px}.v620-realtime-title strong{font-size:14px}.v620-realtime-head>span{font-size:11px}.v620-card-state{min-height:23px;padding:0 8px;font-size:11px}
  .v620-latency-grid{grid-template-columns:minmax(0,1.45fr) minmax(0,.78fr) minmax(0,.78fr);gap:6px;margin-top:9px}.v620-latency{padding:8px 7px;border-radius:12px;min-width:0}.v620-latency span{font-size:11px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.v620-latency strong{font-size:14px}.v620-latency:first-child strong{font-size:22px}.v620-latency em{font-size:11px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.v620-latency:not(:first-child) em{display:none}.v620-realtime-foot{margin-top:7px;font-size:11px;gap:6px;flex-wrap:wrap}
  .tianji-console-v620 .mobile-nav{left:12px!important;right:12px!important;bottom:calc(11px + env(safe-area-inset-bottom))!important;padding:4px!important;border-radius:21px!important}.tianji-console-v620 .mobile-nav .nav-btn{min-height:43px!important;border-radius:15px!important;font-size:11px!important}.tianji-console-v620 .mobile-nav .nav-tail{display:none!important}
}
@media(prefers-reduced-motion:reduce){*,*:before,*:after{scroll-behavior:auto!important;animation-duration:.01ms!important;animation-iteration-count:1!important;transition-duration:.01ms!important}}
"""


FILTER_PATCH = r"""
(()=>{
  document.documentElement.classList.add('tianji-console-v620');
  const select=document.getElementById('v3Lottery');
  if(select){
    fetch('/admin/api/state',{cache:'no-store'})
      .then(response=>response.ok?response.json():Promise.reject())
      .then(data=>{
        const current=select.value;
        select.innerHTML='<option value="all">全部彩种</option>'+(data.lotteries||[])
          .map(item=>`<option value="${String(item.key).replace(/[&<>"']/g,'')}">${String(item.name).replace(/[&<>"']/g,'')}</option>`)
          .join('');
        select.value=current;
      })
      .catch(()=>{});
  }

  const compact=window.matchMedia('(max-width:520px)').matches;
  const runButton=document.getElementById('runBtn');
  if(compact&&runButton)runButton.textContent='同步';
  const esc=value=>String(value??'').replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  const age=value=>{if(!value)return'尚未执行';const diff=Math.max(0,Date.now()-Number(value));if(diff<60000)return Math.floor(diff/1000)+' 秒前';if(diff<3600000)return Math.floor(diff/60000)+' 分钟前';if(diff<86400000)return Math.floor(diff/3600000)+' 小时前';return Math.floor(diff/86400000)+' 天前'};
  const duration=value=>value===null||value===undefined?'—':Number(value)<1000?Math.round(Number(value))+' ms':(Number(value)/1000).toFixed(1)+' s';
  const commit=value=>String(value||'—').slice(0,12);
  const latencyClass=value=>{
    const n=Number(value);
    if(!Number.isFinite(n))return'';
    if(n<=3000)return'good';
    if(n<=7000)return'warn';
    return'bad';
  };
  const latencyLabel=value=>{
    const n=Number(value);
    if(!Number.isFinite(n))return'等待样本';
    if(n<=2000)return'优秀';
    if(n<=4000)return'正常';
    if(n<=7000)return'偏慢';
    return'异常';
  };
  const trend=(current,average)=>{
    const c=Number(current),a=Number(average);
    if(!Number.isFinite(c)||!Number.isFinite(a)||a<=0)return'暂无趋势';
    const delta=c-a;
    if(Math.abs(delta)<120)return'≈ 与 EMA 持平';
    return`${delta<0?'↓':'↑'} ${duration(Math.abs(delta))} 较 EMA`;
  };
  const updateRealtimePill=(state,text)=>{
    const pill=document.getElementById('v630RealtimePill');
    if(!pill)return;
    pill.className=`v630-health-pill ${state||''}`.trim();
    pill.innerHTML=`<i></i>Realtime ${esc(text)}`;
  };
  const installAfterPanelHead=section=>{
    const overview=document.getElementById('panel-overview');
    const anchor=overview?.querySelector('.panel-head');
    if(anchor&&section&&anchor.nextElementSibling!==section)anchor.insertAdjacentElement('afterend',section);
  };
  let lastPlatformSuccess=0;
  let lastRealtimeSuccess=0;

  async function loadPlatform(){
    const overview=document.getElementById('panel-overview');
    if(!overview)return;
    try{
      const response=await fetch('/health/detail',{cache:'no-store'});
      if(!response.ok)return;
      const data=await response.json();
      lastPlatformSuccess=Date.now();
      let section=document.getElementById('v510Platform');
      if(!section){section=document.createElement('section');section.id='v510Platform';section.className='section v510-platform'}
      installAfterPanelHead(section);
      const aiHealth=data.ai_health||{};
      const delivery=data.delivery_health||{};
      const fcm=(delivery.channels||{}).fcm||{};
      const telegram=(delivery.channels||{}).telegram||{};
      const workerState=String(data.worker?.status||'waiting').toLowerCase();
      const workerOk=['ok','running','healthy'].includes(workerState);
      const healthy=data.status==='ok'&&data.database?.ok!==false&&workerOk;
      const aiOk=Number(aiHealth.failed||0)===0;
      const fcmOk=Number(fcm.failed||0)===0;
      const telegramOk=Number(telegram.failed||0)===0;
      section.innerHTML=`
        <div class="v630-health-summary"><div><strong>系统健康</strong><small>正常时只看状态胶囊；异常时再展开详细运行指标。</small></div><span class="badge ${healthy?'good':'warn'}">${healthy?'运行正常':'需要检查'}</span></div>
        <div class="v630-healthbar">
          <span class="v630-health-pill ${workerOk?'':'warn'}"><i></i>服务 ${workerOk?'正常':'待恢复'}</span>
          <span id="v630RealtimePill" class="v630-health-pill"><i></i>Realtime ${lastRealtimeSuccess?'已连接':'等待'}</span>
          <span class="v630-health-pill ${aiOk?'':'warn'}"><i></i>AI ${aiOk?'正常':Number(aiHealth.failed||0)+' 失败'}</span>
          <span class="v630-health-pill ${fcmOk?'':'warn'}"><i></i>FCM ${fcmOk?'正常':Number(fcm.failed||0)+' 失败'}</span>
          <span class="v630-health-pill ${telegramOk?'':'warn'}"><i></i>Telegram ${telegramOk?'正常':Number(telegram.failed||0)+' 失败'}</span>
        </div>
        <details class="v630-health-details" ${healthy&&aiOk&&fcmOk&&telegramOk?'':'open'}>
          <summary>详细运行指标</summary>
          <div class="v510-platform-grid">
            <article class="v510-platform-card"><span>云端服务</span><strong class="${workerOk?'good':'warn'}">${workerOk?'运行正常':'等待恢复'}</strong><small>Worker 心跳 ${age(data.worker?.updated_at_epoch_ms)}</small></article>
            <article class="v510-platform-card"><span>AI 任务</span><strong class="${aiOk?'good':'warn'}">${Number(aiHealth.running||0)} 运行 · ${Number(aiHealth.failed||0)} 失败</strong><small>${aiOk?'当前调度正常':'有失败任务需要留意'}</small></article>
            <article class="v510-platform-card"><span>App 预警</span><strong class="${fcmOk?'good':'warn'}">${Number(fcm.sent||0)} 成功 · ${Number(fcm.failed||0)} 失败</strong><small>最近 24 小时 FCM 预警</small></article>
            <article class="v510-platform-card"><span>Telegram</span><strong class="${telegramOk?'good':'warn'}">${Number(telegram.sent||0)} 成功 · ${Number(telegram.failed||0)} 失败</strong><small>最近 24 小时 · 与 FCM 并行投递</small></article>
          </div>
        </details>`;
    }catch(_error){
      let section=document.getElementById('v510Platform');
      if(!section){section=document.createElement('section');section.id='v510Platform';section.className='section v510-platform'}
      installAfterPanelHead(section);
      section.innerHTML=`<div class="v510-deploy attention"><div class="v510-deploy-main"><div class="v510-deploy-title"><i class="v510-deploy-dot"></i>服务状态刷新失败</div><div class="v510-deploy-message">暂时读取不到最新状态，请检查网络后刷新；后台预警与预测任务不会因为这个页面失败而停止。</div></div><div class="v510-deploy-meta"><span>最后成功刷新</span><strong>${lastPlatformSuccess?new Date(lastPlatformSuccess).toLocaleTimeString('zh-CN',{hour12:false}):'尚未成功'}</strong></div></div>`;
    }
  }

  let realtimeTimer=0;
  async function loadRealtimeLatency(){
    window.clearTimeout(realtimeTimer);
    const overview=document.getElementById('panel-overview');
    if(!overview){realtimeTimer=window.setTimeout(loadRealtimeLatency,8000);return}
    let delay=8000;
    try{
      if(document.hidden){realtimeTimer=window.setTimeout(loadRealtimeLatency,delay);return}
      const response=await fetch('/admin/api/realtime',{cache:'no-store'});
      if(!response.ok)throw new Error('realtime');
      const data=await response.json();
      lastRealtimeSuccess=Date.now();
      let section=document.getElementById('v620Realtime');
      if(!section){section=document.createElement('section');section.id='v620Realtime';section.className='section v620-realtime'}
      const health=document.getElementById('v510Platform');
      if(health&&health.nextElementSibling!==section)health.insertAdjacentElement('afterend',section);
      else if(!health)installAfterPanelHead(section);
      section.classList.remove('stale');
      const lotteries=[...(data.lotteries||[])].sort((a,b)=>{
        const av=Number(a.detection_delay_ms??a.detection_delay_ema_ms??-1);
        const bv=Number(b.detection_delay_ms??b.detection_delay_ema_ms??-1);
        return bv-av;
      });
      const cards=lotteries.map(item=>{
        const current=item.detection_delay_ms;
        const average=item.detection_delay_ema_ms;
        const shown=current===null||current===undefined?average:current;
        const state=latencyClass(shown);
        return `<article class="v620-realtime-card ${state}">
          <div class="v620-realtime-head"><div class="v620-realtime-title"><strong>${esc(item.name||item.key)}</strong><span class="v620-card-state ${state}">${latencyLabel(shown)}</span></div><span>更新 ${age(item.updated_at_epoch_ms)}</span></div>
          <div class="v620-latency-grid">
            <div class="v620-latency"><span>开奖发现延迟</span><strong class="${state}">${duration(shown)}</strong><em>${trend(current,average)}</em></div>
            <div class="v620-latency"><span>探测请求</span><strong>${duration(item.probe_latency_ms)}</strong><em>${latencyLabel(item.probe_latency_ms)}</em></div>
            <div class="v620-latency"><span>写库结算</span><strong>${duration(item.settlement_latency_ms)}</strong><em>${latencyLabel(item.settlement_latency_ms)}</em></div>
          </div>
          <div class="v620-realtime-foot"><span>EMA <b>${duration(average)}</b> · 历史最慢 <b>${duration(item.max_detection_delay_ms)}</b></span><span>样本 <b>${Number(item.draw_detection_samples||0)}</b></span></div>
        </article>`;
      }).join('');
      section.innerHTML=`<div class="v3-head"><div><h3>实时开奖链路 <span class="v620-fresh">实时</span></h3><p>异常彩种自动排到最前，主指标看开奖发现延迟，探测与写库耗时用于定位瓶颈。</p></div><span class="v620-build">service ${esc(data.service_version||'—')} · ${esc(data.runtime_revision||'runtime —')}</span></div><div class="v620-realtime-grid">${cards||'<div class="empty">等待实时 Worker 写入首个延迟样本</div>'}</div>`;
      const observed=lotteries.map(item=>Number(item.detection_delay_ms??item.detection_delay_ema_ms)).filter(Number.isFinite);
      if(observed.length){
        const worst=Math.max(...observed);
        updateRealtimePill(latencyClass(worst), `${latencyLabel(worst)} ${duration(worst)}`);
      }else updateRealtimePill('', '等待样本');
      const targets=(data.lotteries||[]).map(item=>Number(item.next_draw_at_epoch_ms||0)).filter(Boolean);
      if(targets.some(target=>target-Date.now()>=-90000&&target-Date.now()<=180000))delay=3000;
    }catch(_error){
      delay=5000;
      const section=document.getElementById('v620Realtime');
      if(section){
        section.classList.add('stale');
        const fresh=section.querySelector('.v620-fresh');
        if(fresh){
          fresh.className='v620-fresh warn';
          fresh.textContent=`数据已过期 · ${age(lastRealtimeSuccess)}`;
        }
      }
      updateRealtimePill('warn', lastRealtimeSuccess?`过期 ${age(lastRealtimeSuccess)}`:'不可用');
    }
    realtimeTimer=window.setTimeout(loadRealtimeLatency,delay);
  }

  const drawCountdown=target=>{
    if(!target)return'等待时间';
    const diff=Number(target)-Date.now();
    if(diff<=0)return'等待开奖';
    const total=Math.floor(diff/1000),minutes=Math.floor(total/60),seconds=total%60;
    return`${String(minutes).padStart(2,'0')}:${String(seconds).padStart(2,'0')}`;
  };
  const drawRefreshDelay=lotteries=>{
    let delay=30000;
    for(const item of lotteries||[]){
      const target=Number(item.next_draw_at_epoch_ms||0);
      if(!target)continue;
      const remaining=target-Date.now();
      if(remaining>=-90000&&remaining<=60000)delay=Math.min(delay,3000);
      else if(remaining>60000&&remaining<=180000)delay=Math.min(delay,8000);
    }
    return delay;
  };
  let drawRefreshTimer=0;
  async function refreshRealtimeDraws(){
    window.clearTimeout(drawRefreshTimer);
    let delay=30000;
    try{
      if(document.hidden){drawRefreshTimer=window.setTimeout(refreshRealtimeDraws,delay);return}
      const response=await fetch('/admin/api/state',{cache:'no-store'});
      if(!response.ok)throw new Error('state');
      const data=await response.json();
      const cards=[...document.querySelectorAll('#v3DrawGrid .v3-draw')];
      for(const item of data.lotteries||[]){
        const card=cards.find(node=>node.querySelector('h4')?.textContent?.trim()===String(item.name||'').trim());
        if(!card)continue;
        card.dataset.target=String(item.next_draw_at_epoch_ms||'');
        const sub=card.querySelector('.sub');
        if(sub)sub.textContent=`最新期 ${item.latest_period||'等待同步'} · 目标期 ${item.next_period||'—'}`;
        const countdown=card.querySelector('.v3-countdown');
        if(countdown)countdown.textContent=drawCountdown(item.next_draw_at_epoch_ms);
      }
      delay=drawRefreshDelay(data.lotteries||[]);
    }catch(_error){delay=5000}
    drawRefreshTimer=window.setTimeout(refreshRealtimeDraws,delay);
  }

  loadPlatform();
  loadRealtimeLatency();
  refreshRealtimeDraws();
  window.setInterval(loadPlatform,30000);
})();
"""


@lru_cache(maxsize=1)
def _assets() -> tuple[str, str]:
    root = Path(__file__).resolve().parent
    # v5.10 keeps one canonical console stylesheet and script. Older generated
    # console_v3/v5/v6 assets were removed to prevent cascade and event-handler drift.
    style_text = (root / "console_v594.css").read_text(encoding="utf-8")
    script_text = (root / "console_v594.js").read_text(encoding="utf-8")
    return style_text, script_text


def enhance_console_html(value: str) -> str:
    style_text, script_text = _assets()
    head_meta = (
        '<meta name="theme-color" content="#f5f6fb">'
        '<meta name="color-scheme" content="dark light">'
    )
    if "viewport-fit=cover" not in value:
        head_meta += (
            '<meta name="viewport" '
            'content="width=device-width,initial-scale=1,viewport-fit=cover">'
        )
    style = (
        f"<style>/* Tianji Cloud Console V6.3 density / hierarchy compatibility */"
        f"{style_text}{V510_STYLE}</style>"
    )
    script = f"<script>{script_text}</script><script>{FILTER_PATCH}</script>"
    if "</head>" in value:
        value = value.replace("</head>", head_meta + style + "</head>", 1)
    else:
        value = head_meta + style + value
    if "</body>" in value:
        value = value.replace("</body>", script + "</body>", 1)
    else:
        value += script
    return value


def _install_public_page_v4() -> None:
    original = _web_console.public_page
    if getattr(original, "_tianji_public_v4", False):
        return

    def public_page_v4() -> str:
        return enhance_public_html(original())

    setattr(public_page_v4, "_tianji_public_v4", True)
    _web_console.public_page = public_page_v4


_install_public_page_v4()