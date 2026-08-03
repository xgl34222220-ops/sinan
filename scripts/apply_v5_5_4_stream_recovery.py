#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected 1 match, got {count}: {old[:140]!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


analysis = ROOT / "app/src/main/java/com/tianji/probabilitylab/nativev4/ai/AiAnalysis.kt"
gradle = ROOT / "app/build.gradle.kts"
readme = ROOT / "README.md"

old_execute = '''            val response = post(
                config = config,
                temperature = if (reasoningDecision.expectsReasoning) 0.1 else 0.2,
                systemPrompt = SYSTEM_PROMPT,
                userPrompt = prompt,
                reasoningDecision = reasoningDecision,
                readTimeoutMs = readTimeoutMs,
                jsonOutput = true,
                explainOutput = true,
                streamResponse = true,
                onProgress = onProgress,
            )
            response.json.requireCompletedResponse()
            val usage = response.json.extractUsage()
            val hasReasoningContent = response.json.extractReasoningContent().isNotBlank()
            val content = response.json.extractContent()
            require(content.isNotBlank()) {
                if (response.json.extractReasoningContent().isNotBlank()) {
                    "模型只返回了思考过程，没有生成最终 JSON"
                } else {
                    "模型返回了空内容"
                }
            }
            return parseForecastContent(
                content = content,
'''
new_execute = '''            var response = post(
                config = config,
                temperature = if (reasoningDecision.expectsReasoning) 0.1 else 0.2,
                systemPrompt = SYSTEM_PROMPT,
                userPrompt = prompt,
                reasoningDecision = reasoningDecision,
                readTimeoutMs = readTimeoutMs,
                jsonOutput = true,
                explainOutput = true,
                streamResponse = true,
                onProgress = onProgress,
            )
            var payload = response.json.extractCompleteForecastPayload()
            var continuedConversation = false
            if (
                payload == null &&
                (response.json.extractContent().isNotBlank() ||
                    response.json.extractReasoningContent().isNotBlank())
            ) {
                continuedConversation = true
                onProgress(
                    "首次推理已完成，正在沿用同一对话补全最终 JSON",
                    System.currentTimeMillis() - started,
                )
                response = runCatching {
                    post(
                        config = config,
                        temperature = if (reasoningDecision.expectsReasoning) 0.1 else 0.2,
                        systemPrompt = SYSTEM_PROMPT,
                        userPrompt = prompt,
                        reasoningDecision = reasoningDecision,
                        readTimeoutMs = 120_000,
                        jsonOutput = true,
                        explainOutput = true,
                        streamResponse = true,
                        onProgress = onProgress,
                        previousAssistantContent = response.json.extractContent(),
                        previousReasoningContent = response.json.extractReasoningContent(),
                        followUpPrompt = FINALIZE_JSON_PROMPT,
                    )
                }.getOrElse { cause ->
                    throw AiConversationFinalizationException(
                        "首次推理已完成，但继续对话补全结果失败：${cause.message.orEmpty().take(100)}",
                        cause,
                    )
                }
                payload = response.json.extractCompleteForecastPayload()
                if (payload == null) {
                    throw AiConversationFinalizationException(
                        "首次推理与继续对话均未返回完整的 position 和 10 项 scores",
                    )
                }
            }
            response.json.requireCompletedResponse()
            val usage = response.json.extractUsage()
            val hasReasoningContent = response.json.extractReasoningContent().isNotBlank()
            val content = payload ?: response.json.extractContent()
            require(content.isNotBlank()) {
                if (response.json.extractReasoningContent().isNotBlank()) {
                    "模型只返回了思考过程，没有生成最终 JSON"
                } else {
                    "模型返回了空内容"
                }
            }
            return parseForecastContent(
                content = content,
'''
replace_once(analysis, old_execute, new_execute)

replace_once(
    analysis,
    '''                executionNote = "$executionNote · ${response.tokenBudgetLabel}",
''',
    '''                executionNote = buildString {
                    append(executionNote)
                    if (continuedConversation) append(" · 同一对话补全结果")
                    append(" · ${response.tokenBudgetLabel}")
                },
''',
)

replace_once(
    analysis,
    '''        val reasoningControlFailure = isReasoningControlFailure(firstFailure, primaryDecision)
        if (!isRetriableModelOutput(firstFailure) && !reasoningControlFailure) throw firstFailure

        return runCatching {
''',
    '''        val reasoningControlFailure = isReasoningControlFailure(firstFailure, primaryDecision)
        if (!isRetriableModelOutput(firstFailure) && !reasoningControlFailure) throw firstFailure
        onProgress(
            "首次请求在推理前或输出开始前失败，正在重新请求",
            System.currentTimeMillis() - started,
        )

        return runCatching {
''',
)

replace_once(
    analysis,
    '''        streamResponse: Boolean = false,
        onProgress: (String, Long) -> Unit = { _, _ -> },
    ): RemoteResponse {
''',
    '''        streamResponse: Boolean = false,
        onProgress: (String, Long) -> Unit = { _, _ -> },
        previousAssistantContent: String = "",
        previousReasoningContent: String = "",
        followUpPrompt: String = "",
    ): RemoteResponse {
''',
)

replace_once(
    analysis,
    '''        val tokenBudget = AiTokenPolicy.resolve(config, responsesApi)
        val request = JSONObject().apply {
''',
    '''        val tokenBudget = AiTokenPolicy.resolve(config, responsesApi)

        fun conversationMessages(includeReasoning: Boolean): JSONArray = JSONArray().apply {
            put(JSONObject().put("role", "system").put("content", systemPrompt))
            put(JSONObject().put("role", "user").put("content", userPrompt))
            if (followUpPrompt.isNotBlank()) {
                val assistant = JSONObject()
                    .put("role", "assistant")
                    .put("content", previousAssistantContent)
                if (
                    includeReasoning &&
                    reasoningDecision.protocol == AiReasoningProtocol.DEEPSEEK &&
                    previousReasoningContent.isNotBlank()
                ) {
                    assistant.put("reasoning_content", previousReasoningContent)
                }
                put(assistant)
                put(JSONObject().put("role", "user").put("content", followUpPrompt))
            }
        }

        val request = JSONObject().apply {
''',
)

replace_once(
    analysis,
    '''                    JSONArray()
                        .put(JSONObject().put("role", "system").put("content", systemPrompt))
                        .put(JSONObject().put("role", "user").put("content", userPrompt)),
''',
    '''                    conversationMessages(includeReasoning = false),
''',
)
replace_once(
    analysis,
    '''                    JSONArray()
                        .put(JSONObject().put("role", "system").put("content", systemPrompt))
                        .put(JSONObject().put("role", "user").put("content", userPrompt)),
''',
    '''                    conversationMessages(includeReasoning = true),
''',
)

replace_once(
    analysis,
    '''            if (contentPart.isNotEmpty()) {
                content.append(contentPart)
                report("模型正在生成结构化预测 · 已收到 ${content.length} 个结果字符")
            }
''',
    '''            if (contentPart.isNotEmpty()) {
                content.append(contentPart)
                if (AiForecastPayloadExtractor.containsForecastCore(content.toString())) {
                    report("已收到完整预测核心，正在校验说明与结束状态")
                } else {
                    report("模型正在生成结构化预测 · 已收到 ${content.length} 个结果字符")
                }
            }
''',
)

old_complete = '''    private fun JSONObject.hasCompleteForecastContent(): Boolean {
        val content = extractContent()
        if (content.isBlank()) return false
        return runCatching {
            val json = JSONObject(stripCodeFence(content))
            val position = json.optInt("position", 0)
            val scores = json.optJSONArray("scores") ?: return@runCatching false
            position in 1..10 && scores.length() == 10 && (0 until scores.length()).all { index ->
                val score = scores.optDouble(index, Double.NaN)
                score.isFinite() && score >= 0.0
            }
        }.getOrDefault(false)
    }
'''
new_complete = '''    private fun JSONObject.extractCompleteForecastPayload(): String? {
        val sources = listOf(extractContent(), extractReasoningContent())
        for (source in sources) {
            for (candidate in AiForecastPayloadExtractor.balancedJsonObjects(source)) {
                val valid = runCatching { JSONObject(candidate).hasForecastCore() }.getOrDefault(false)
                if (valid) return candidate
            }
        }
        for (source in sources) {
            AiForecastPayloadExtractor.salvageCoreJson(source)?.let { return it }
        }
        return null
    }

    private fun JSONObject.hasForecastCore(): Boolean {
        val position = optInt("position", 0)
        val scores = optJSONArray("scores") ?: return false
        return position in 1..10 && scores.length() == 10 && (0 until scores.length()).all { index ->
            val score = scores.optDouble(index, Double.NaN)
            score.isFinite() && score >= 0.0
        }
    }

    private fun JSONObject.hasCompleteForecastContent(): Boolean =
        extractCompleteForecastPayload() != null
'''
replace_once(analysis, old_complete, new_complete)

replace_once(
    analysis,
    '''    private fun isRetriableModelOutput(error: Throwable): Boolean {
        val message = error.message.orEmpty()
''',
    '''    private fun isRetriableModelOutput(error: Throwable): Boolean {
        if (error is AiConversationFinalizationException) return false
        val message = error.message.orEmpty()
''',
)

replace_once(
    analysis,
    '''    private data class RemoteResponse(
        val json: JSONObject,
        val latencyMs: Long,
        val tokenBudgetLabel: String,
    )

    private companion object {
''',
    '''    private data class RemoteResponse(
        val json: JSONObject,
        val latencyMs: Long,
        val tokenBudgetLabel: String,
    )

    private class AiConversationFinalizationException(
        message: String,
        cause: Throwable? = null,
    ) : IllegalStateException(message, cause)

    private companion object {
        const val FINALIZE_JSON_PROMPT =
            "你已经完成上一轮统计分析。不要重新计算、不要复述推理过程。只根据上一轮结论立即输出一个JSON对象，必须包含position、10项scores、calculation_summary、position_reason、candidate_reason和uncertainty。"
''',
)

replace_once(gradle, 'versionCode = 28\n        versionName = "5.5.3"', 'versionCode = 29\n        versionName = "5.5.4"')
replace_once(readme, '- 版本：5.5.3', '- 版本：5.5.4')
replace_once(
    readme,
    '## v5.5.3 模型上限、流式状态与透明计算',
    '''## v5.5.4 流式结果恢复

- 流式响应不再要求整段文本必须刚好是一个 JSON，可从说明文字、代码围栏或推理末尾提取完整预测对象。
- 当 position 与 10 项 scores 已完整生成、仅后续说明被截断时，直接恢复核心预测，不再整轮重新推理。
- 第一轮确实没有最终 JSON 时，沿用同一对话和已完成的 DeepSeek reasoning_content 请求补全结果，不重新分析 120 期历史。
- 继续对话仍失败时明确报错，不再自动启动第三次完整推理。
- 状态栏明确区分“首次推理”“同一对话补全结果”和真正的重新请求。

## v5.5.3 模型上限、流式状态与透明计算''',
)

print("v5.5.4 stream recovery patch applied")
