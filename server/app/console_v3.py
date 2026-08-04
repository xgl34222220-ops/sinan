from __future__ import annotations

from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def _assets() -> tuple[str, str]:
    root = Path(__file__).resolve().parent
    return (
        (root / "console_v3.css").read_text(encoding="utf-8"),
        (root / "console_v3.js").read_text(encoding="utf-8"),
    )


def enhance_console_html(value: str) -> str:
    style_text, script_text = _assets()
    style = f"<style>{style_text}</style>"
    script = f"<script>{script_text}</script>"
    if "</head>" in value:
        value = value.replace("</head>", style + "</head>", 1)
    else:
        value = style + value
    if "</body>" in value:
        value = value.replace("</body>", script + "</body>", 1)
    else:
        value += script
    return value
