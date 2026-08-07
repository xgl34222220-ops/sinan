from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from . import web_console as _web_console
from .public_v4 import enhance_public_html


V510_STYLE = r"""
:where(button,a,input,select,summary):focus-visible{outline:3px solid color-mix(in srgb,var(--primary) 32%,transparent);outline-offset:2px}
#recordsPro .v3-controls{position:sticky;top:64px;z-index:18;background:color-mix(in srgb,var(--surface) 94%,transparent);backdrop-filter:blur(18px);-webkit-backdrop-filter:blur(18px)}
.v510-platform{margin-top:14px}.v510-platform-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:9px}.v510-platform-card{padding:14px;border:1px solid var(--line);border-radius:19px;background:var(--surface);box-shadow:var(--shadow2)}.v510-platform-card span{display:block;color:var(--muted);font-size:9px}.v510-platform-card strong{display:block;margin-top:6px;font-size:15px;overflow-wrap:anywhere}.v510-platform-card small{display:block;margin-top:4px;color:var(--muted);font-size:9px;line-height:1.45}.v510-stage-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:7px;margin-top:10px}.v510-stage{display:flex;align-items:center;justify-content:space-between;gap:8px;padding:9px 10px;border-radius:13px;border:1px solid var(--line);background:var(--soft);font-size:9px}.v510-stage b{font-size:10px}.v510-stage.error{color:var(--bad);background:var(--bad-soft)}.v510-stage.ok b{color:var(--good)}
.v510-deploy{display:grid;grid-template-columns:minmax(0,1.4fr) repeat(3,minmax(0,.7fr));gap:10px;align-items:center;margin-top:10px;padding:14px 15px;border:1px solid var(--line);border-radius:19px;background:linear-gradient(135deg,var(--primary-soft),var(--surface));box-shadow:var(--shadow2)}.v510-deploy.attention{background:linear-gradient(135deg,var(--bad-soft),var(--surface));border-color:color-mix(in srgb,var(--bad) 22%,var(--line))}.v510-deploy-main{min-width:0}.v510-deploy-title{display:flex;align-items:center;gap:7px;font-size:12px;font-weight:820}.v510-deploy-dot{width:8px;height:8px;border-radius:50%;background:var(--good);box-shadow:0 0 0 5px color-mix(in srgb,var(--good) 13%,transparent)}.v510-deploy.attention .v510-deploy-dot{background:var(--bad);box-shadow:0 0 0 5px color-mix(in srgb,var(--bad) 12%,transparent)}.v510-deploy-message{margin-top:4px;color:var(--muted);font-size:10px;line-height:1.55}.v510-deploy-meta span{display:block;color:var(--muted);font-size:9px}.v510-deploy-meta strong{display:block;margin-top:4px;font-size:11px;overflow-wrap:anywhere}.v510-commit{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;letter-spacing:.02em}
@media(max-width:1040px){.v510-platform-grid{grid-template-columns:repeat(3,minmax(0,1fr))}.v510-deploy{grid-template-columns:repeat(3,minmax(0,1fr))}.v510-deploy-main{grid-column:1/-1}}
@media(max-width:760px){.v510-platform-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.v510-stage-grid{grid-template-columns:1fr}.v510-deploy{grid-template-columns:1fr 1fr}#recordsPro .v3-controls{top:57px}}
@media(max-width:520px){.v510-platform-grid,.v510-deploy{grid-template-columns:1fr}.v510-deploy-main{grid-column:auto}}
@media(prefers-reduced-motion:reduce){*,*:before,*:after{scroll-behavior:auto!important;animation-duration:.01ms!important;animation-iteration-count:1!important;transition-duration:.01ms!important}}
"""


FILTER_PATCH = r"""
(()=>{
  document.documentElement.classList.add('tianji-console-v510');
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

  const esc=value=>String(value??'').replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  const age=value=>{if(!value)return'尚未执行';const diff=Math.max(0,Date.now()-Number(value));if(diff<60000)return Math.floor(diff/1000)+' 秒前';if(diff<3600000)return Math.floor(diff/60000)+' 分钟前';if(diff<86400000)return Math.floor(diff/3600000)+' 小时前';return Math.floor(diff/86400000)+' 天前'};
  const duration=value=>value===null||value===undefined?'—':Number(value)<1000?Math.round(Number(value))+' ms':(Number(value)/1000).toFixed(1)+' s';
  const commit=value=>String(value||'—').slice(0,12);
  let lastPlatformSuccess=0;

  async function loadPlatform(){
    const overview=document.getElementById('panel-overview');
    if(!overview)return;
    try{
      const response=await fetch('/health/detail',{cache:'no-store'});
      if(!response.ok)return;
      const data=await response.json();
      lastPlatformSuccess=Date.now();
      let section=document.getElementById('v510Platform');
      if(!section){section=document.createElement('section');section.id='v510Platform';section.className='section v510-platform';overview.appendChild(section)}
      const aiHealth=data.ai_health||{};
      const delivery=data.delivery_health||{};
      const fcm=(delivery.channels||{}).fcm||{};
      const telegram=(delivery.channels||{}).telegram||{};
      const workerState=String(data.worker?.status||'waiting').toLowerCase();
      const workerOk=['ok','running','healthy'].includes(workerState);
      const healthy=data.status==='ok'&&data.database?.ok!==false&&workerOk;
      section.innerHTML=`
        <div class="v3-head"><div><h3>服务状态</h3><p>只显示日常需要看的运行、AI 和推送状态；内部任务名、数据库细节与毫秒耗时已隐藏。</p></div><span class="badge ${healthy?'good':'warn'}">${healthy?'运行正常':'需要检查'}</span></div>
        <div class="v510-platform-grid">
          <article class="v510-platform-card"><span>云端服务</span><strong class="${workerOk?'good':'warn'}">${workerOk?'运行正常':'等待恢复'}</strong><small>Worker 心跳 ${age(data.worker?.updated_at_epoch_ms)}</small></article>
          <article class="v510-platform-card"><span>AI 任务</span><strong class="${Number(aiHealth.failed||0)?'warn':'good'}">${Number(aiHealth.running||0)} 运行 · ${Number(aiHealth.failed||0)} 失败</strong><small>${Number(aiHealth.failed||0)?'有失败任务需要留意':'当前调度正常'}</small></article>
          <article class="v510-platform-card"><span>App 预警</span><strong class="${Number(fcm.failed||0)?'warn':'good'}">${Number(fcm.sent||0)} 成功 · ${Number(fcm.failed||0)} 失败</strong><small>最近 24 小时 FCM 预警</small></article>
          <article class="v510-platform-card"><span>Telegram</span><strong class="${Number(telegram.failed||0)?'warn':'good'}">${Number(telegram.sent||0)} 成功 · ${Number(telegram.failed||0)} 失败</strong><small>最近 24 小时 · 预警优先发送</small></article>
        </div>`;
    }catch(_error){
      let section=document.getElementById('v510Platform');
      if(!section){
        const overview=document.getElementById('panel-overview');
        if(!overview)return;
        section=document.createElement('section');section.id='v510Platform';section.className='section v510-platform';overview.appendChild(section);
      }
      section.innerHTML=`<div class="v510-deploy attention"><div class="v510-deploy-main"><div class="v510-deploy-title"><i class="v510-deploy-dot"></i>服务状态刷新失败</div><div class="v510-deploy-message">暂时读取不到最新状态，请检查网络后刷新；后台预警与预测任务不会因为这个页面失败而停止。</div></div><div class="v510-deploy-meta"><span>最后成功刷新</span><strong>${lastPlatformSuccess?new Date(lastPlatformSuccess).toLocaleTimeString('zh-CN',{hour12:false}):'尚未成功'}</strong></div></div>`;
    }
  }
  loadPlatform();
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
        f"<style>/* Tianji Cloud Console V5.10 canonical | Cloud Console V3 compatibility */"
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
