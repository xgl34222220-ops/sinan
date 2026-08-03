#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected 1 match, got {count}: {old[:100]!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


analysis = ROOT / "app/src/main/java/com/tianji/probabilitylab/nativev4/ai/AiAnalysis.kt"
gradle = ROOT / "app/build.gradle.kts"
readme = ROOT / "README.md"
test = ROOT / "app/src/test/java/com/tianji/probabilitylab/nativev4/ai/AiForecastPayloadExtractorTest.kt"

old_stream = r'''    private fun readChatStream(
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
        var firstReasoningMs = -1L
        var firstContentMs = -1L

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
                if (firstReasoningMs < 0L) firstReasoningMs = System.currentTimeMillis() - startedAtMs
                reasoning.append(reasoningPart)
                report("模型正在推理 · 已收到 ${reasoning.length} 个推理字符")
            }
            if (contentPart.isNotEmpty()) {
                if (firstContentMs < 0L) firstContentMs = System.currentTimeMillis() - startedAtMs
                content.append(contentPart)
                if (AiForecastPayloadExtractor.containsForecastCore(content.toString())) {
                    report("已收到完整预测核心，正在校验说明与结束状态")
                } else {
                    report("模型正在生成结构化预测 · 已收到 ${content.length} 个结果字符")
                }
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
            .apply {
                usage?.let { put("usage", it) }
                put("_tianji_first_reasoning_ms", firstReasoningMs)
                put("_tianji_first_content_ms", firstContentMs)
                put("_tianji_stream_finished_ms", System.currentTimeMillis() - startedAtMs)
            }
    }

    private fun JSONObject.streamPhaseSummary(): String {
        val firstReasoning = optLong("_tianji_first_reasoning_ms", -1L)
        val firstContent = optLong("_tianji_first_content_ms", -1L)
        val finished = optLong("_tianji_stream_finished_ms", -1L)
        if (finished < 0L) return ""
        fun seconds(value: Long): String = String.format(java.util.Locale.US, "%.1fs", value / 1000.0)
        return when {
            firstReasoning >= 0L && firstContent >= firstReasoning ->
                "首个推理 ${seconds(firstReasoning)} · 推理阶段 ${seconds(firstContent - firstReasoning)} · 结果阶段 ${seconds((finished - firstContent).coerceAtLeast(0L))}"
            firstContent >= 0L ->
                "首个结果 ${seconds(firstContent)} · 结果阶段 ${seconds((finished - firstContent).coerceAtLeast(0L))}"
            else -> "响应总耗时 ${seconds(finished)}"
        }
    }
'''

new_stream = r'''    private fun readChatStream(
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
        var firstReasoningMs = -1L
        var firstContentMs = -1L
        var earlyComplete = false

        fun report(message: String, force: Boolean = false) {
            val now = System.currentTimeMillis()
            if (force || now - lastProgressAt >= 1_000L) {
                lastProgressAt = now
                onProgress(message, now - startedAtMs)
            }
        }

        while (true) {
            val rawLine = reader.readLine() ?: break
            val line = rawLine.trim()
            if (line.isBlank()) continue
            if (!line.startsWith("data:")) {
                if (line.startsWith("{")) plainBody.append(line)
                continue
            }
            val payload = line.removePrefix("data:").trim()
            if (payload == "[DONE]" || payload.isBlank()) continue
            val chunk = runCatching { JSONObject(payload) }.getOrNull() ?: continue
            responseId = chunk.optString("id").ifBlank { responseId }
            chunk.optJSONObject("usage")?.let { usage = it }
            val choice = chunk.optJSONArray("choices")?.optJSONObject(0) ?: continue
            finishReason = choice.optString("finish_reason").ifBlank { finishReason }
            val delta = choice.optJSONObject("delta") ?: continue
            val reasoningPart = delta.opt("reasoning_content")
                ?.takeUnless { it == JSONObject.NULL }
                ?.toString()
                .orEmpty()
            val contentPart = delta.opt("content")
                ?.takeUnless { it == JSONObject.NULL }
                ?.toString()
                .orEmpty()
            if (reasoningPart.isNotEmpty()) {
                if (firstReasoningMs < 0L) firstReasoningMs = System.currentTimeMillis() - startedAtMs
                reasoning.append(reasoningPart)
                report("模型正在推理 · 已收到 ${reasoning.length} 个推理字符")
            }
            if (contentPart.isNotEmpty()) {
                if (firstContentMs < 0L) firstContentMs = System.currentTimeMillis() - startedAtMs
                content.append(contentPart)
                if (AiForecastPayloadExtractor.containsForecastCore(content.toString())) {
                    earlyComplete = true
                    finishReason = "stop"
                    report("已取得完整预测结果，已主动结束剩余输出", force = true)
                    break
                }
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
            .apply {
                usage?.let { put("usage", it) }
                put("_tianji_first_reasoning_ms", firstReasoningMs)
                put("_tianji_first_content_ms", firstContentMs)
                put("_tianji_stream_finished_ms", System.currentTimeMillis() - startedAtMs)
                put("_tianji_early_complete", earlyComplete)
            }
    }

    private fun JSONObject.streamPhaseSummary(): String {
        val firstReasoning = optLong("_tianji_first_reasoning_ms", -1L)
        val firstContent = optLong("_tianji_first_content_ms", -1L)
        val finished = optLong("_tianji_stream_finished_ms", -1L)
        val earlyComplete = optBoolean("_tianji_early_complete", false)
        if (finished < 0L) return ""
        fun seconds(value: Long): String = String.format(java.util.Locale.US, "%.1fs", value / 1000.0)
        val phases = when {
            firstReasoning >= 0L && firstContent >= firstReasoning ->
                "首个推理 ${seconds(firstReasoning)} · 推理阶段 ${seconds(firstContent - firstReasoning)} · 结果阶段 ${seconds((finished - firstContent).coerceAtLeast(0L))}"
            firstContent >= 0L ->
                "首个结果 ${seconds(firstContent)} · 结果阶段 ${seconds((finished - firstContent).coerceAtLeast(0L))}"
            else -> "响应总耗时 ${seconds(finished)}"
        }
        return if (earlyComplete) "$phases · 完整结果到达后主动收口" else phases
    }
'''

replace_once(analysis, old_stream, new_stream)
replace_once(
    gradle,
    'versionCode = 30\n        versionName = "5.5.5"',
    'versionCode = 31\n        versionName = "5.5.6"',
)
replace_once(readme, '- 版本：5.5.5', '- 版本：5.5.6')
replace_once(
    readme,
    '## v5.5.4 流式结果恢复',
    '''## v5.5.6 完整结果立即返回

- 保留模型自身最大 Token 空间、真实 thinking 和完整 60/120 期历史。
- 流式响应一旦出现有效 position 与 10 项 scores，立即主动结束剩余输出并进入本机校验。
- 不再等待供应商继续生成长篇说明或最终 `[DONE]`，避免结果已出仍持续几十秒到数分钟。
- 修复流式 `content=null` / `reasoning_content=null` 被错误拼接成 `nullnull…` 的问题。
- 提前收口导致供应商未返回最终 usage 时，只显示已验证思考，不伪造 Token 数量。
- 说明字段尚未完成时保留有效预测矩阵，并使用本机逐期核验摘要，不重新请求模型。

## v5.5.4 流式结果恢复''',
)

insert_before = '''    @Test
    fun rejectsIncompleteScoreArray() {'''
new_test = '''    @Test
    fun coreBecomesAvailableImmediatelyAfterTenthScore() {
        val incomplete = "{\\\"position\\\":8,\\\"scores\\\":[0.1,0.2,0.3]"
        val completeCoreWithUnfinishedExplanation =
            "{\\\"position\\\":8,\\\"scores\\\":[$scores],\\\"calculation_summary\\\":\\\"仍在生成"

        assertNull(AiForecastPayloadExtractor.salvageCoreJson(incomplete))
        assertNotNull(AiForecastPayloadExtractor.salvageCoreJson(completeCoreWithUnfinishedExplanation))
    }

    @Test
    fun rejectsIncompleteScoreArray() {'''
replace_once(test, insert_before, new_test)

print("v5.5.6 early-result patch applied")
