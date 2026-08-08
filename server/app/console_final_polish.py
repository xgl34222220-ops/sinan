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
@media(max-width:760px){.v68-pipeline{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:520px){
  .v68-pipeline{grid-template-columns:repeat(2,minmax(0,1fr));gap:6px}
  .v68-pipeline-item{padding:7px 8px}
  .v68-pipeline-item span,.v68-pipeline-summary{font-size:10px}
  .v68-pipeline-item strong{font-size:12px}
  .tianji-console-v620 .mobile-nav .nav-btn{font-size:11px!important}
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
  let timer=0;
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
