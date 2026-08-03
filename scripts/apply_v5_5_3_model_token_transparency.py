#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected 1 match, got {count}: {old[:160]!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def regex_replace(path: Path, pattern: str, replacement: str, expected: int) -> None:
    text = path.read_text(encoding="utf-8")
    updated, count = re.subn(pattern, replacement, text, flags=re.S)
    if count != expected:
        raise RuntimeError(f"{path}: expected {expected} regex matches, got {count}: {pattern}")
    path.write_text(updated, encoding="utf-8")


analysis = ROOT / "app/src/main/java/com/tianji/probabilitylab/nativev4/ai/AiAnalysis.kt"
controller = ROOT / "app/src/main/java/com/tianji/probabilitylab/nativev4/AppController.kt"
screens = ROOT / "app/src/main/java/com/tianji/probabilitylab/nativev4/ui/Screens.kt"
gradle = ROOT / "app/build.gradle.kts"
readme = ROOT / "README.md"

# Capability probes must also stop imposing small client-side token ceilings.
replace_once(
    analysis,
    '''            reasoningDecision = baseDecision,
            maxTokens = if (baseDecision.expectsReasoning) 8_192 else 1_024,
            readTimeoutMs = if (baseDecision.expectsReasoning) 90_000 else 30_000,
            jsonOutput = true,
''',
    '''            reasoningDecision = baseDecision,
            readTimeoutMs = if (baseDecision.expectsReasoning) 90_000 else 30_000,
            jsonOutput = true,
            explainOutput = false,
''',
)
replace_once(
    analysis,
    '''                reasoningDecision = highDecision,
                maxTokens = if (highDecision.protocol == AiReasoningProtocol.DEEPSEEK) 32_768 else 8_192,
                readTimeoutMs = if (highDecision.protocol == AiReasoningProtocol.DEEPSEEK) 180_000 else 90_000,
                jsonOutput = true,
''',
    '''                reasoningDecision = highDecision,
                readTimeoutMs = if (highDecision.protocol == AiReasoningProtocol.DEEPSEEK) 180_000 else 90_000,
                jsonOutput = true,
                explainOutput = false,
''',
)

replace_once(
    analysis,
    '''    fun analyze(
        config: AiConfig,
        snapshot: DrawSnapshot,
        report: ForecastReport,
    ): AiForecast {''',
    '''    fun analyze(
        config: AiConfig,
        snapshot: DrawSnapshot,
        report: ForecastReport,
        onProgress: (String, Long) -> Unit = { _, _ -> },
    ): AiForecast {''',
)

replace_once(
    analysis,
    '''        fun execute(
            reasoningDecision: AiReasoningDecision,
            maxTokens: Int,
            readTimeoutMs: Int,
            executionNote: String,
            fallback: Boolean = false,
            prompt: String = userPrompt,
        ): AiForecast {''',
    '''        fun execute(
            reasoningDecision: AiReasoningDecision,
            readTimeoutMs: Int,
            executionNote: String,
            fallback: Boolean = false,
            prompt: String = userPrompt,
        ): AiForecast {''',
)

replace_once(
    analysis,
    '''                userPrompt = prompt,
                reasoningDecision = reasoningDecision,
                maxTokens = maxTokens,
                readTimeoutMs = readTimeoutMs,
                jsonOutput = true,
            )''',
    '''                userPrompt = prompt,
                reasoningDecision = reasoningDecision,
                readTimeoutMs = readTimeoutMs,
                jsonOutput = true,
                explainOutput = true,
                streamResponse = true,
                onProgress = onProgress,
            )''',
)

replace_once(
    analysis,
    '''                executionNote = executionNote,
                history = snapshot.history,''',
    '''                executionNote = "$executionNote · ${response.tokenBudgetLabel}",
                history = snapshot.history,''',
)

# Remove both primary and retry arbitrary maxTokens when blocks.
regex_replace(
    analysis,
    r'''\n\s*maxTokens = when \{.*?\n\s*\},\n\s*readTimeoutMs =''',
    '''
                readTimeoutMs =''',
    expected=2,
)

replace_once(
    analysis,
    '''        reasoningDecision: AiReasoningDecision,
        maxTokens: Int,
        readTimeoutMs: Int,
        jsonOutput: Boolean,
    ): RemoteResponse {''',
    '''        reasoningDecision: AiReasoningDecision,
        readTimeoutMs: Int,
        jsonOutput: Boolean,
        explainOutput: Boolean,
        streamResponse: Boolean = false,
        onProgress: (String, Long) -> Unit = { _, _ -> },
    ): RemoteResponse {''',
)

replace_once(
    analysis,
    '''        val responsesApi = endpoint.path.trimEnd('/').endsWith("/responses")
        val request = JSONObject().apply {
            put("model", config.model.trim())
            put("stream", false)
''',
    '''        val responsesApi = endpoint.path.trimEnd('/').endsWith("/responses")
        var useStreaming = streamResponse && !responsesApi
        val tokenBudget = AiTokenPolicy.resolve(config, responsesApi)
        val request = JSONObject().apply {
            put("model", config.model.trim())
            put("stream", useStreaming)
            if (useStreaming && config.provider != AiProvider.COMPATIBLE) {
                put("stream_options", JSONObject().put("include_usage", true))
            }
            tokenBudget.parameter?.let { parameter -> put(parameter, tokenBudget.value) }
''',
)

replace_once(analysis, '                put("max_output_tokens", maxTokens)\n', '')
replace_once(
    analysis,
    '''                    put("text", JSONObject().put("format", forecastJsonSchema(responsesApi = true)))''',
    '''                    put(
                        "text",
                        JSONObject().put(
                            "format",
                            forecastJsonSchema(responsesApi = true, explainOutput = explainOutput),
                        ),
                    )''',
)
replace_once(
    analysis,
    '''                if (config.provider == AiProvider.OPENAI) put("max_completion_tokens", maxTokens)
                else put("max_tokens", maxTokens)
''',
    '',
)
replace_once(
    analysis,
    '''                    put("response_format", forecastJsonSchema(responsesApi = false))''',
    '''                    put(
                        "response_format",
                        forecastJsonSchema(responsesApi = false, explainOutput = explainOutput),
                    )''',
)

old_response = '''                val code = connection.responseCode
                val body = (if (code in 200..299) connection.inputStream else connection.errorStream)
                    ?.bufferedReader(Charsets.UTF_8)?.use { it.readText() }.orEmpty()
                if (code in 200..299) {
                    return RemoteResponse(JSONObject(body), System.currentTimeMillis() - started)
                }
                if (attempt == 0 && code == 429) {
                    val retrySeconds = connection.getHeaderField("Retry-After")?.trim()?.toLongOrNull()
                        ?.coerceIn(1L, 10L) ?: 2L
                    retryDelayMs = retrySeconds * 1_000L
                } else if (attempt == 0 && code in 500..599) {
                    retryDelayMs = 500L
                } else {
                    error("AI 接口 HTTP $code：${body.take(160)}")
                }
'''
new_response = '''                val code = connection.responseCode
                if (code in 200..299) {
                    onProgress("已连接模型，等待推理输出", System.currentTimeMillis() - started)
                    val json = connection.inputStream
                        ?.bufferedReader(Charsets.UTF_8)
                        ?.use { reader ->
                            if (useStreaming) {
                                readChatStream(reader, started, onProgress)
                            } else {
                                JSONObject(reader.readText())
                            }
                        } ?: error("AI 接口返回空响应")
                    return RemoteResponse(
                        json = json,
                        latencyMs = System.currentTimeMillis() - started,
                        tokenBudgetLabel = tokenBudget.label,
                    )
                }
                val body = connection.errorStream
                    ?.bufferedReader(Charsets.UTF_8)?.use { it.readText() }.orEmpty()
                if (
                    attempt == 0 && useStreaming && code in listOf(400, 404, 405, 422) &&
                    (body.contains("stream", ignoreCase = true) ||
                        body.contains("stream_options", ignoreCase = true))
                ) {
                    useStreaming = false
                    request.put("stream", false)
                    request.remove("stream_options")
                    retryDelayMs = 0L
                    onProgress("接口不支持流式返回，已切换普通对话响应", System.currentTimeMillis() - started)
                } else if (attempt == 0 && code == 429) {
                    val retrySeconds = connection.getHeaderField("Retry-After")?.trim()?.toLongOrNull()
                        ?.coerceIn(1L, 10L) ?: 2L
                    retryDelayMs = retrySeconds * 1_000L
                } else if (attempt == 0 && code in 500..599) {
                    retryDelayMs = 500L
                } else {
                    error("AI 接口 HTTP $code：${body.take(160)}")
                }
'''
replace_once(analysis, old_response, new_response)

stream_reader = '''
    private fun readChatStream(
        reader: java.io.BufferedReader,
        startedAtMs: Long,
        onProgress: (String, Long) -> Unit,
    ): JSONObject {
        val content = StringBuilder()
        val reasoning = StringBuilder()
        val plainBody = StringBuilder()
        var responseId = ""
        var finishReason = ""
        var usage: JSONObject? = null
        var lastProgressAt = 0L

        fun report(message: String) {
            val now = System.currentTimeMillis()
            if (now - lastProgressAt >= 1_000L) {
                lastProgressAt = now
                onProgress(message, now - startedAtMs)
            }
        }

        reader.forEachLine { rawLine ->
            val line = rawLine.trim()
            if (line.isBlank()) return@forEachLine
            if (!line.startsWith("data:")) {
                if (line.startsWith("{")) plainBody.append(line)
                return@forEachLine
            }
            val payload = line.removePrefix("data:").trim()
            if (payload == "[DONE]" || payload.isBlank()) return@forEachLine
            val chunk = runCatching { JSONObject(payload) }.getOrNull() ?: return@forEachLine
            responseId = chunk.optString("id").ifBlank { responseId }
            chunk.optJSONObject("usage")?.let { usage = it }
            val choice = chunk.optJSONArray("choices")?.optJSONObject(0) ?: return@forEachLine
            finishReason = choice.optString("finish_reason").ifBlank { finishReason }
            val delta = choice.optJSONObject("delta") ?: return@forEachLine
            val reasoningPart = delta.optString("reasoning_content")
            val contentPart = delta.optString("content")
            if (reasoningPart.isNotEmpty()) {
                reasoning.append(reasoningPart)
                report("模型正在推理 · 已收到 ${reasoning.length} 个推理字符")
            }
            if (contentPart.isNotEmpty()) {
                content.append(contentPart)
                report("模型正在生成结构化预测 · 已收到 ${content.length} 个结果字符")
            }
        }

        if (content.isEmpty() && plainBody.isNotEmpty()) return JSONObject(plainBody.toString())
        val message = JSONObject().put("content", content.toString())
        if (reasoning.isNotEmpty()) message.put("reasoning_content", reasoning.toString())
        return JSONObject()
            .put("id", responseId)
            .put(
                "choices",
                JSONArray().put(
                    JSONObject()
                        .put("index", 0)
                        .put("finish_reason", finishReason.ifBlank { "stop" })
                        .put("message", message),
                ),
            )
            .apply { usage?.let { put("usage", it) } }
    }

'''
replace_once(
    analysis,
    '    private fun JSONObject.extractContent(): String =',
    stream_reader + '    private fun JSONObject.extractContent(): String =',
)

# Visible, auditable explanation fields. They are summaries, not hidden chain of thought.
replace_once(
    analysis,
    '    private fun forecastJsonSchema(responsesApi: Boolean): JSONObject {',
    '    private fun forecastJsonSchema(responsesApi: Boolean, explainOutput: Boolean): JSONObject {',
)

old_schema = '''        val schema = JSONObject()
            .put("type", "object")
            .put(
                "properties",
                JSONObject()
                    .put(
                        "position",
                        JSONObject().put("type", "integer").put("minimum", 1).put("maximum", 10),
                    )
                    .put("scores", scoreArray),
            )
            .put("required", JSONArray(listOf("position", "scores")))
            .put("additionalProperties", false)
'''
new_schema = '''        val properties = JSONObject()
            .put(
                "position",
                JSONObject().put("type", "integer").put("minimum", 1).put("maximum", 10),
            )
            .put("scores", scoreArray)
        val required = mutableListOf("position", "scores")
        if (explainOutput) {
            properties
                .put(
                    "calculation_summary",
                    JSONObject().put("type", "string").put("maxLength", 800),
                )
                .put(
                    "position_reason",
                    JSONObject().put("type", "string").put("maxLength", 500),
                )
                .put(
                    "candidate_reason",
                    JSONObject().put("type", "string").put("maxLength", 800),
                )
                .put(
                    "uncertainty",
                    JSONObject().put("type", "string").put("maxLength", 500),
                )
            required += listOf(
                "calculation_summary",
                "position_reason",
                "candidate_reason",
                "uncertainty",
            )
        }
        val schema = JSONObject()
            .put("type", "object")
            .put("properties", properties)
            .put("required", JSONArray(required))
            .put("additionalProperties", false)
'''
replace_once(analysis, old_schema, new_schema)

old_analysis_fields = '''            analysis = AiFactEngine.verifiedSummary(history, position - 1, top6).take(500),
            riskNote = buildString {
                append("AI 仅参与候选排序；统计由本机对刚同步的开奖接口历史逐期复核。随机开奖无法保证准确率或盈利。")
                if (lowBoundarySeparation) append(" 本次第6与第7候选差距较小，候选边界稳定性偏低。")
            },
'''
new_analysis_fields = '''            analysis = buildString {
                val calculation = json.optString("calculation_summary").trim()
                val positionEvidence = json.optString("position_reason").trim()
                val candidateEvidence = json.optString("candidate_reason").trim()
                append("计算摘要：")
                append(
                    calculation.ifBlank {
                        AiFactEngine.verifiedSummary(history, position - 1, top6)
                    },
                )
                if (positionEvidence.isNotBlank()) append("\n名次依据：$positionEvidence")
                if (candidateEvidence.isNotBlank()) append("\n候选依据：$candidateEvidence")
            }.take(1_800),
            riskNote = buildString {
                val uncertainty = json.optString("uncertainty").trim()
                if (uncertainty.isNotBlank()) append("AI 不确定性：$uncertainty ")
                append("统计由本机对刚同步的开奖接口历史逐期复核；随机开奖无法保证准确率或盈利。")
                if (lowBoundarySeparation) append(" 本次第6与第7候选差距较小，候选边界稳定性偏低。")
            }.take(900),
'''
replace_once(analysis, old_analysis_fields, new_analysis_fields)

replace_once(
    analysis,
    '''                JSONObject()
                    .put("position", "integer 1..10")
                    .put("scores", "array of exactly 10 non-negative raw scores for numbers 1..10; keep at least 6 decimal places; do not round values into ties"),
''',
    '''                JSONObject()
                    .put("position", "integer 1..10")
                    .put("scores", "array of exactly 10 non-negative raw scores for numbers 1..10; keep at least 6 decimal places; do not round values into ties")
                    .put("calculation_summary", "concise auditable description of statistical method; do not expose hidden chain of thought")
                    .put("position_reason", "cite the verified facts that made this position stronger than the other nine")
                    .put("candidate_reason", "cite verified frequency, omission, transition or drift evidence behind the score ordering")
                    .put("uncertainty", "state weak evidence, conflicts and instability without claiming certainty"),
''',
)

old_system = '''        const val SYSTEM_PROMPT = """你是独立概率排序模型。输入含真实开奖、由客户端逐期计算并核验的统计表，以及不含候选结果的本地模型质量摘要。本地盲测候选已被刻意隐藏。遗漏、近20期次数和大小连开必须以 verified_position_statistics 为唯一事实来源，不得自行心算或改写。你必须先比较position 1至10的全部统计，再选择证据最充分的一个名次；不得默认选择第1名，也不得因为字段顺序或历史示例偏向任何固定名次。随后按号码1至10顺序输出10个非负原始评分，每项至少保留6位小数。六码、七码和最终号码排序均由客户端根据原始scores确定。只输出 required_json_schema 指定的 position 与 scores，不要解释、不要Markdown，不承诺准确率、盈利或必中。"""
'''
new_system = '''        const val SYSTEM_PROMPT = """你是独立概率排序模型。输入含真实开奖和由客户端逐期计算并核验的统计表，本地盲测候选已被刻意隐藏。遗漏、近20/60期次数、后继转移和大小连开必须以 verified_position_statistics 为事实来源，原始历史仅用于交叉核验。你必须先比较position 1至10，再选择证据最充分的名次；不得默认第1名或偏向固定名次。随后按号码1至10顺序输出10个非负原始评分，每项至少保留6位小数，六码、七码和最终排序由客户端从scores确定。除position与scores外，还必须返回calculation_summary、position_reason、candidate_reason和uncertainty，让用户看见可核验的计算依据；这些字段只写简洁结论和使用了哪些已核验统计，不得输出隐藏思维链、逐字内心推理或Markdown。只输出required_json_schema规定的JSON，不承诺准确率、盈利或必中。"""
'''
replace_once(analysis, old_system, new_system)

replace_once(
    analysis,
    '    private data class RemoteResponse(val json: JSONObject, val latencyMs: Long)\n',
    '''    private data class RemoteResponse(
        val json: JSONObject,
        val latencyMs: Long,
        val tokenBudgetLabel: String,
    )
''',
)

# Live progress lets the UI show connection/thinking/output stages instead of a frozen spinner.
replace_once(
    controller,
    '''                    val forecast = remoteAiAnalyzer.analyze(config, snapshot, report)
''',
    '''                    val forecast = remoteAiAnalyzer.analyze(config, snapshot, report) { message, elapsedMs ->
                        mainHandler.post {
                            if (
                                aiGeneration.get() == token &&
                                state.report?.targetPeriod == report.targetPeriod &&
                                state.aiStatuses[config.id]?.state == AiConnectionState.ANALYZING
                            ) {
                                state = state.copy(
                                    aiStatuses = state.aiStatuses + (
                                        config.id to AiRunStatus(
                                            profileId = config.id,
                                            state = AiConnectionState.ANALYZING,
                                            message = "$message · ${elapsedMs / 1_000}s",
                                            checkedAtEpochMs = System.currentTimeMillis(),
                                        )
                                    ),
                                )
                            }
                        }
                    }
''',
)

# Make the result card clearly distinguish the model's auditable summary.
replace_once(
    screens,
    '''        Spacer(Modifier.height(12.dp))
        Text(result.analysis, color = colors.textSoft, fontSize = 9.sp, lineHeight = 15.sp)
''',
    '''        Spacer(Modifier.height(12.dp))
        Text(
            "AI 可核验计算依据",
            color = colors.accent,
            fontSize = 8.sp,
            fontWeight = FontWeight.Bold,
        )
        Spacer(Modifier.height(5.dp))
        Text(result.analysis, color = colors.textSoft, fontSize = 9.sp, lineHeight = 15.sp)
''',
)
replace_once(
    screens,
    '''        AiReasoningState.FALLBACK ->
            "推理未完成 · 当前为关闭推理后的重试结果（不代表本期好坏）" to colors.amber
''',
    '''        AiReasoningState.FALLBACK ->
            "保留真实思考后的重试结果（不代表本期好坏）" to colors.amber
''',
)

replace_once(gradle, 'versionCode = 27\n        versionName = "5.5.2"', 'versionCode = 28\n        versionName = "5.5.3"')
replace_once(readme, '- 版本：5.5.2', '- 版本：5.5.3')
replace_once(
    readme,
    '## v5.5.2 思考效率优化',
    '''## v5.5.3 模型上限与透明计算

- 官方 DeepSeek V4 请求使用模型自身 384K 最大输出空间，不再使用客户端 32K/65K/96K 人工上限。
- OpenAI 与未知兼容模型不发送客户端输出 Token 上限，由所选模型和供应商执行自身限制。
- Chat Completions 分析改为流式接收，页面实时显示连接、思考与生成结构化结果阶段及耗时。
- 流式参数不兼容时自动退回普通对话响应，不会因兼容接口不支持 SSE 而直接失败。
- AI 结果必须附带可核验的计算摘要、名次依据、候选依据和不确定性，不再用本机固定文案冒充 AI 分析过程。
- 仅展示可审计的统计依据摘要，不展示或保存模型隐藏思维链。

## v5.5.2 思考效率优化''',
)

final_analysis = analysis.read_text(encoding="utf-8")
if "maxTokens:" in final_analysis or "maxTokens = when" in final_analysis:
    raise RuntimeError("client maxTokens remnants remain")
if 'put("max_completion_tokens"' in final_analysis:
    raise RuntimeError("client max_completion_tokens remnant remains")
if "explainOutput = true" not in final_analysis or "readChatStream" not in final_analysis:
    raise RuntimeError("v5.5.3 analysis changes incomplete")

print("v5.5.3 model-token transparency patch applied")
