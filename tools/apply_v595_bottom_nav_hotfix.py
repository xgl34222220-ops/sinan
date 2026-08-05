from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, content: str) -> None:
    (ROOT / path).write_text(content, encoding="utf-8")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


def regex_once(text: str, pattern: str, replacement: str, label: str) -> str:
    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.S)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {count}")
    return updated


# Fix the full-screen bottom navigation regression.
path = "app/src/main/java/com/tianji/probabilitylab/nativev4/ui/AppShellV2.kt"
text = read(path)
text = replace_once(
    text,
    ".heightIn(min = 64.dp)",
    ".heightIn(min = 64.dp, max = 72.dp)",
    "bottom bar bounded height",
)
text = regex_once(
    text,
    r"(private fun StandardNavItem\(.*?modifier = modifier\s*)\.fillMaxHeight\(\)",
    r"\1.height(56.dp)",
    "standard navigation item height",
)
text = regex_once(
    text,
    r"(private fun ChatNavItem\(.*?modifier = modifier\s*)\.fillMaxHeight\(\)",
    r"\1.height(56.dp)",
    "AI navigation item height",
)
write(path, text)

# Bump the emergency hotfix version.
path = "app/build.gradle.kts"
text = read(path)
text = replace_once(text, 'versionCode = 46', 'versionCode = 47', 'versionCode')
text = replace_once(text, 'versionName = "5.9.4"', 'versionName = "5.9.5"', 'versionName')
write(path, text)

# Prepare the release workflow for v5.9.5 and verify upgrade continuity from v5.9.4.
path = ".github/workflows/release.yml"
text = read(path)
for old, new, label in (
    ("RELEASE_NOTES_v5.9.4.md", "RELEASE_NOTES_v5.9.5.md", "release notes path"),
    ("tianji-v5.9.4-release", "tianji-v5.9.5-release", "release concurrency"),
    ("test \"$VERSION\" = '5.9.4'", "test \"$VERSION\" = '5.9.5'", "release version guard"),
    ("test \"$VERSION_CODE\" = '46'", "test \"$VERSION_CODE\" = '47'", "release code guard"),
    ("PREVIOUS_TAG='v5.9.3'", "PREVIOUS_TAG='v5.9.4'", "previous release tag"),
    ("PREVIOUS_TAG='v5.9.2'", "PREVIOUS_TAG='v5.9.3'", "previous release fallback"),
):
    text = replace_once(text, old, new, label)
write(path, text)

# Add concise release notes that clearly identify the emergency regression fix.
write(
    "RELEASE_NOTES_v5.9.5.md",
    """# 天机 v5.9.5\n\n这是针对 v5.9.4 底部导航异常拉伸问题的紧急修复版本，不修改预测算法、开奖同步、数据库结构或冻结结算规则。\n\n## 修复\n\n- 修复底部导航栏在部分设备上被拉伸到接近全屏的问题。\n- 修复选中导航项背景变成长竖条的问题。\n- 底部导航栏高度限制为 64–72dp。\n- 普通导航项与中央 AI 导航项改为明确的 56dp 高度，不再请求父容器全部可用高度。\n- 保留 v5.9.4 的渐变开奖球、AI 任务状态、档案筛选和控制台改进。\n\n## 兼容性\n\n- 应用 ID：`com.tianji.probabilitylab.nativev5`\n- 版本号：`5.9.5`\n- versionCode：`47`\n- 延续 nativev5 正式签名，可从 v5.9.4 直接覆盖升级。\n""",
)

print("Applied Tianji v5.9.5 bottom navigation hotfix.")
