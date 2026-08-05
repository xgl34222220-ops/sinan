from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from . import web_console as _web_console
from .public_v4 import enhance_public_html


V510_STYLE = r"""
:where(button,a,input,select,summary):focus-visible{outline:3px solid color-mix(in srgb,var(--primary) 32%,transparent);outline-offset:2px}
#recordsPro .v3-controls{position:sticky;top:64px;z-index:18;background:color-mix(in srgb,var(--surface) 94%,transparent);backdrop-filter:blur(18px);-webkit-backdrop-filter:blur(18px)}
.v510-platform{margin-top:14px}.v510-platform-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:9px}.v510-platform-card{padding:14px;border:1px solid var(--line);border-radius:19px;background:var(--surface);box-shadow:var(--shadow2)}.v510-platform-card span{display:block;color:var(--muted);font-size:9px}.v510-platform-card strong{display:block;margin-top:6px;font-size:15px;overflow-wrap:anywhere}.v510-stage-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:7px;margin-top:10px}.v510-stage{display:flex;align-items:center;justify-content:space-between;gap:8px;padding:9px 10px;border-radius:13px;border:1px solid var(--line);background:var(--soft);font-size:9px}.v510-stage b{font-size:10px}.v510-stage.error{color:var(--bad);background:var(--bad-soft)}.v510-stage.ok b{color:var(--good)}
@media(max-width:760px){.v510-platform-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.v510-stage-grid{grid-template-columns:1fr}#recordsPro .v3-controls{top:57px}}
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
  const age=value=>{if(!value)return'尚未执行';const diff=Math.max(0,Date.now()-Number(value));if(diff<60000)return Math.floor(diff/1000)+' 秒前';if(diff<3600000)return Math.floor(diff/60000)+' 分钟前';return Math.floor(diff/3600000)+' 小时前'};
  const duration=value=>value===null||value===undefined?'—':Number(value)<1000?Math.round(Number(value))+' ms':(Number(value)/1000).toFixed(1)+' s';

  async function loadPlatform(){
    const overview=document.getElementById('panel-overview');
    if(!overview)return;
    try{
      const response=await fetch('/health/detail',{cache:'no-store'});
      if(!response.ok)return;
      const data=await response.json();
      let section=document.getElementById('v510Platform');
      if(!section){section=document.createElement('section');section.id='v510Platform';section.className='section v510-platform';overview.appendChild(section)}
      const backup=data.backup||{};
      const cycles=Object.entries(data.cycles||{});
      const stages=cycles.flatMap(([lottery,cycle])=>(cycle?.stages||[]).map(stage=>({...stage,lottery})));
      section.innerHTML=`
        <div class="v3-head"><div><h3>平台健康与任务阶段</h3><p>数据库、Worker、自动备份与每个周期的真实耗时。</p></div><span class="badge ${data.status==='ok'?'good':'warn'}">${data.status==='ok'?'运行正常':'需要检查'}</span></div>
        <div class="v510-platform-grid">
          <article class="v510-platform-card"><span>数据库</span><strong>${data.database?.ok?'连接正常':'连接异常'}</strong></article>
          <article class="v510-platform-card"><span>Worker 心跳</span><strong>${esc(data.worker?.status||'waiting')} · ${age(data.worker?.updated_at_epoch_ms)}</strong></article>
          <article class="v510-platform-card"><span>最近备份</span><strong>${backup.status==='ok'?age(backup.completed_at_epoch_ms):backup.message?'失败':'等待首次备份'}</strong></article>
          <article class="v510-platform-card"><span>服务版本</span><strong>${esc(data.version||'—')}</strong></article>
        </div>
        <div class="v510-stage-grid">${stages.length?stages.slice(-14).reverse().map(stage=>`<div class="v510-stage ${stage.status==='error'?'error':'ok'}"><span>${esc(stage.lottery)} · ${esc(stage.name)}</span><b>${stage.status==='error'?'失败':duration(stage.duration_ms)}</b></div>`).join(''):'<div class="v3-empty"><strong>等待任务阶段数据</strong>下一次 Worker 周期完成后自动显示</div>'}</div>`;
    }catch(_error){}
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
