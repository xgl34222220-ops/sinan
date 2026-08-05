#!/usr/bin/env python3
from pathlib import Path

root = Path(__file__).resolve().parents[1]
controller = root / "app/src/main/java/com/tianji/probabilitylab/nativev4/ai/AiChatController.kt"
gradle = root / "app/build.gradle.kts"
notes = root / "RELEASE_NOTES_v5.10.4.md"

def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected one match, got {count}: {old!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")

replace_once(
    controller,
    "            isPrediction = prediction != null,\n",
    "            isPrediction = wantsPrediction,\n",
)
replace_once(gradle, '        versionCode = 55\n', '        versionCode = 56\n')
replace_once(gradle, '        versionName = "5.10.3"\n', '        versionName = "5.10.4"\n')
notes.write_text(
    """# 天机 v5.10.4\n\n## AI 目标期二次修复\n\n- 修复模型未返回完整结构化 `tianji_forecast` 时，客户端跳过目标期校正的问题。\n- 只要当前请求属于明确预测，正文中的预测标题和目标期字段都会按顶部当前目标期校正。\n- 不再依赖候选 JSON 是否成功解析，避免顶部显示 21348025、正文仍写 21348012。\n- 历史开奖期号、样本截至期和复盘证据仍保持原样，不会被批量替换。\n\n## 验证\n\n- 执行 Android 单元测试、Lint、Debug 与 Release 构建。\n""",
    encoding="utf-8",
)
print("patched v5.10.4")
