#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
analysis = ROOT / "app/src/main/java/com/tianji/probabilitylab/nativev4/ai/AiAnalysis.kt"
notes = ROOT / "RELEASE_NOTES_v5.5.6.md"

text = analysis.read_text(encoding="utf-8")

old_call = """            var response = post(
                config = config,
                temperature = if (reasoningDecision.expectsReasoning) 0.1 else 0.2,
                systemPrompt = SYSTEM_PROMPT,
                userPrompt = prompt,
                reasoningDecision = reasoningDecision,
                readTimeoutMs = readTimeoutMs,
                jsonOutput = true,
                explainOutput = false,
                streamResponse = true,
                onProgress = onProgress,
            )
"""
new_call = old_call.replace("var response", "val response")
if text.count(old_call) != 1:
    raise RuntimeError(f"expected one primary post call, got {text.count(old_call)}")
text = text.replace(old_call, new_call, 1)

pattern = re.compile(
    r'''            var payload = response\.json\.extractCompleteForecastPayload\(\)\n'''
    r'''            var continuedConversation = false\n'''
    r'''            if \(\n.*?'''
    r'''            \}\n'''
    r'''            response\.json\.requireCompletedResponse\(\)''',
    re.DOTALL,
)
replacement = '''            val payload = response.json.extractCompleteForecastPayload()
                ?: throw AiConversationFinalizationException(
                    "模型未返回完整的 position 和 10 项 scores；本次请求已停止，未自动再次调用",
                )
            response.json.requireCompletedResponse()'''
text, count = pattern.subn(replacement, text, count=1)
if count != 1:
    raise RuntimeError(f"expected one same-conversation completion block, got {count}")

old_content = "            val content = payload ?: response.json.extractContent()\n"
if text.count(old_content) != 1:
    raise RuntimeError(f"expected one payload fallback, got {text.count(old_content)}")
text = text.replace(old_content, "            val content = payload\n", 1)

old_note = '                    if (continuedConversation) append(" · 同一对话补全结果")\n'
if text.count(old_note) != 1:
    raise RuntimeError(f"expected one continuation execution note, got {text.count(old_note)}")
text = text.replace(old_note, "", 1)

old_constant = '''        const val FINALIZE_JSON_PROMPT =
            "你已经完成分析。不要重新计算或解释，立即只输出包含position与10项scores的紧凑JSON。"
'''
if text.count(old_constant) != 1:
    raise RuntimeError(f"expected one finalize prompt constant, got {text.count(old_constant)}")
text = text.replace(old_constant, "", 1)

analysis.write_text(text, encoding="utf-8")

notes_text = notes.read_text(encoding="utf-8")
old_line = "- 首次返回缺少最终 JSON 时，只沿用同一对话请求补全两个核心字段，不重新分析 120 期历史。"
new_line = "- 一次点击只发送一次预测请求；缺少完整核心 JSON 时明确失败，不再自动补全或重新调用模型。"
if notes_text.count(old_line) != 1:
    raise RuntimeError(f"expected release-note continuation line, got {notes_text.count(old_line)}")
notes.write_text(notes_text.replace(old_line, new_line, 1), encoding="utf-8")

print("v5.5.6 single-request policy applied")
