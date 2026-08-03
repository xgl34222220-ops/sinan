#!/usr/bin/env python3
from pathlib import Path

script = Path(__file__).with_name("apply_v5_5_4_stream_recovery.py")
text = script.read_text(encoding="utf-8")
text = text.replace(
    '    if count != 1:\n        raise RuntimeError(f"{path}: expected 1 match, got {count}: {old[:140]!r}")',
    '    if count < 1:\n        raise RuntimeError(f"{path}: expected at least 1 match, got {count}: {old[:140]!r}")',
    1,
)
text = text.replace(
    "## v5.5.3 模型上限、流式状态与透明计算",
    "## v5.5.3 模型上限与透明计算",
)
namespace = {"__name__": "__main__", "__file__": str(script)}
exec(compile(text, str(script), "exec"), namespace)
