from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from . import web_console as _web_console
from .public_v4 import enhance_public_html


FILTER_PATCH = r"""
(()=>{
  document.documentElement.classList.add('tianji-console-v4');
  const select=document.getElementById('v3Lottery');
  if(!select)return;
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
})();
"""


@lru_cache(maxsize=1)
def _assets() -> tuple[str, str]:
    root = Path(__file__).resolve().parent
    # V5.9.4 ships a single consolidated runtime asset to prevent override drift.
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
    # Keep the historical marker because deployment regression tests use it to confirm
    # that the enhanced console has been installed.
    style = (
        f"<style>/* Tianji Cloud Console V5.9.4 unified | Cloud Console V3 compatibility */"
        f"{style_text}</style>"
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
