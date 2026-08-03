#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
analysis = ROOT / "app/src/main/java/com/tianji/probabilitylab/nativev4/ai/AiAnalysis.kt"
notes = ROOT / "RELEASE_NOTES_v5.5.6.md"


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected 1 match, got {count}: {old[:160]!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


replace_once(
    analysis,
    '''            val response = post(
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
            val payload = response.json.extractCompleteForecastPayload()
''',
    '''            var checkpointReasoning = ""
            var response = post(
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
            if (response.json.optBoolean("_tianji_reasoning_checkpoint", false)) {
                checkpointReasoning = response.json.extractReasoningContent()
                require(checkpointReasoning.isNotBlank()) {
                    "模型进入思考收口阶段，但没有保留到可复用的推理上下文"
                }
                onProgress(
                    "真实推理已达到收口点，正在同一对话整理 position 与 scores；不会重新分析120期",
                    System.currentTimeMillis() - started,
                )
                val finalizationDecision = reasoningDecision.copy(
                    sendControl = reasoningDecision.protocol == AiReasoningProtocol.DEEPSEEK,
                    enableThinking = false,
                    effort = null,
                    displayLabel = "${reasoningDecision.protocol.label} · 已完成思考，整理结果",
                )
                response = post(
                    config = config,
                    temperature = 0.0,
                    systemPrompt = SYSTEM_PROMPT,
                    userPrompt = prompt,
                    reasoningDecision = finalizationDecision,
                    readTimeoutMs = 45_000,
                    jsonOutput = true,
                    explainOutput = false,
                    streamResponse = true,
                    onProgress = onProgress,
                    previousAssistantContent = "",
                    previousReasoningContent = checkpointReasoning,
                    followUpPrompt = "基于上面已经完成的真实推理，不要重新分析历史，也不要继续展开思考。现在立即只输出一个JSON对象：position为1至10整数，scores为按号码1至10排列的10项非负原始评分。",
                )
            }
            val payload = response.json.extractCompleteForecastPayload()
''',
)

replace_once(
    analysis,
    '''            val hasReasoningContent = response.json.extractReasoningContent().isNotBlank()
''',
    '''            val hasReasoningContent = checkpointReasoning.isNotBlank() ||
                response.json.extractReasoningContent().isNotBlank()
''',
)

replace_once(
    analysis,
    '''        var earlyComplete = false
''',
    '''        var earlyComplete = false
        var reasoningCheckpoint = false
''',
)

replace_once(
    analysis,
    '''                reasoning.append(reasoningPart)
                report("模型正在推理 · 已收到 ${reasoning.length} 个推理字符")
            }
            if (contentPart.isNotEmpty()) {
''',
    '''                reasoning.append(reasoningPart)
                report("模型正在推理 · 已收到 ${reasoning.length} 个推理字符")
                val elapsedMs = System.currentTimeMillis() - startedAtMs
                if (
                    AiReasoningCheckpoint.shouldFinalize(
                        reasoningChars = reasoning.length,
                        contentChars = content.length,
                        elapsedMs = elapsedMs,
                    )
                ) {
                    reasoningCheckpoint = true
                    finishReason = "reasoning_checkpoint"
                    report(
                        "真实推理已达到收口点，准备沿用同一对话生成核心预测",
                        force = true,
                    )
                    break
                }
            }
            if (contentPart.isNotEmpty()) {
''',
)

replace_once(
    analysis,
    '''                put("_tianji_early_complete", earlyComplete)
''',
    '''                put("_tianji_early_complete", earlyComplete)
                put("_tianji_reasoning_checkpoint", reasoningCheckpoint)
''',
)

replace_once(
    notes,
    '''- 模型已开始推理后，缺少完整核心 JSON、超时或断流都会明确失败，不再自动补全或重新预测。
''',
    '''- 正常情况下仍是一轮预测；若模型只持续输出思考且迟迟不开始JSON，在收到至少5000个真实推理字符并持续45秒后，保存现有推理上下文并在同一对话仅整理核心JSON，不重新分析历史。
- 普通超时、断流、空响应或无效JSON仍明确失败，不会重新开始一轮预测。
''',
)

print("v5.5.6 reasoning checkpoint patch applied")
