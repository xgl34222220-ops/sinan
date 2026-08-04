from __future__ import annotations

from functools import lru_cache
from pathlib import Path


PUBLIC_SCRIPT = r"""
(()=>{
  document.documentElement.classList.remove('tianji-public-v4');
  document.documentElement.classList.add('tianji-public-v5');

  const themeMeta=document.querySelector('meta[name="theme-color"]');
  const syncTheme=()=>{
    if(!themeMeta)return;
    themeMeta.content=document.documentElement.dataset.theme==='dark'?'#0c0f16':'#f4f6fb';
  };
  syncTheme();

  const tagNumbers=(root=document)=>{
    root.querySelectorAll('.number,.ball').forEach(node=>{
      const value=String(node.textContent||'').trim();
      if(/^([1-9]|10)$/.test(value)){
        node.dataset.number=value;
        node.setAttribute('aria-label',`号码 ${value}`);
      }
    });
  };
  tagNumbers();

  const observer=new MutationObserver(records=>{
    records.forEach(record=>record.addedNodes.forEach(node=>{
      if(node.nodeType!==1)return;
      if(node.matches?.('.number,.ball'))tagNumbers(node.parentElement||document);
      else tagNumbers(node);
    }));
  });
  observer.observe(document.body,{childList:true,subtree:true});

  const themeButton=document.querySelector('.topbar .icon-btn[onclick*="toggleTheme"]');
  themeButton?.addEventListener('click',()=>requestAnimationFrame(syncTheme));

  const refreshButton=document.getElementById('refreshBtn');
  refreshButton?.addEventListener('click',()=>{
    const icon=refreshButton.querySelector('svg');
    icon?.classList.remove('public-v5-pulse');
    void icon?.getBoundingClientRect();
    icon?.classList.add('public-v5-pulse');
  });
})();
"""


@lru_cache(maxsize=1)
def _style() -> str:
    root = Path(__file__).resolve().parent
    return (root / "public_v5.css").read_text(encoding="utf-8")


def enhance_public_html(value: str) -> str:
    style = f"<style>/* Tianji Public Cloud V5 */{_style()}</style>"
    script = f"<script>{PUBLIC_SCRIPT}</script>"

    value = value.replace(
        '<html lang="zh-CN" data-theme="light">',
        '<html lang="zh-CN" data-theme="light" class="tianji-public-v5">',
        1,
    )
    if "</head>" in value:
        value = value.replace("</head>", style + "</head>", 1)
    else:
        value = style + value
    if "</body>" in value:
        value = value.replace("</body>", script + "</body>", 1)
    else:
        value += script
    return value
