from __future__ import annotations

import re
from pathlib import Path

gradle = Path("app/build.gradle.kts").read_text(encoding="utf-8")
readme = Path("README.md").read_text(encoding="utf-8")
version = re.search(r'versionName\s*=\s*"([^"]+)"', gradle)
if version is None:
    raise SystemExit("无法读取 Android versionName")
current = version.group(1)
if f"当前正式版：**{current}**" not in readme:
    raise SystemExit(f"README 当前正式版与 Android 不一致：{current}")
note = Path(f"RELEASE_NOTES_v{current}.md")
if not note.exists():
    raise SystemExit(f"缺少正式发行说明：{note}")
print(f"version consistency ok: {current}")
