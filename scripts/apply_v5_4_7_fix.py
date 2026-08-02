from pathlib import Path


def replace_once(value: str, old: str, new: str, label: str) -> str:
    if old not in value:
        raise RuntimeError(f"missing patch target: {label}")
    return value.replace(old, new, 1)


ai = Path("app/src/main/java/com/tianji/probabilitylab/nativev4/ai/AiAnalysis.kt")
reasoning = Path("app/src/main/java/com/tianji/probabilitylab/nativev4/ai/AiReasoning.kt")
gradle = Path("app/build.gradle.kts")
readme = Path("README.md")

a = ai.read_text()
r = reasoning.read_text()
g = gradle.read_text()
rd = readme.read_text()

a = replace_once(
    a,
    """                maxTokens = if (primaryDecision.expectsReasoning) 4_096 else 640,
                readTimeoutMs = if (primaryDecision.expectsReasoning) 60_000 else 30_000,""",
    """                maxTokens = when {
                    primaryDecision.expectsReasoning && primaryDecision.protocol == AiReasoningProtocol.DEEPSEEK -> 32_768
                    primaryDecision.expectsReasoning -> 8_192
                    else -> 1_024
                },
                readTimeoutMs = when {
                    primaryDecision.expectsReasoning && primaryDecision.protocol == AiReasoningProtocol.DEEPSEEK -> 180_000
                    primaryDecision.expectsReasoning -> 90_000
                    else -> 30_000
                },""",
    "primary output budget",
)

a = replace_once(
    a,
    """            val retryDecision = if (reasoningFallback) {
                AiReasoningEngine.resolve(config, AiReasoningMode.AUTO)
            } else primaryDecision""",
    """            val retryDecision = if (reasoningFallback) {
                AiReasoningEngine.fallback(config)
            } else primaryDecision""",
    "fallback decision",
)

a = replace_once(
    a,
    """                maxTokens = 640,
                readTimeoutMs = 20_000,""",
    """                maxTokens = 1_024,
                readTimeoutMs = 45_000,""",
    "fallback limits",
)

a = replace_once(
    a,
    """                    val reason = if (reasoningControlFailure) "推理参数被接口拒绝" else "推理无最终答案"
                    "${config.analysisMode.label} · $reason → ${retryDecision.displayLabel}重试"""",
    """                    val reason = when {
                        reasoningControlFailure -> "推理参数被接口拒绝"
                        firstFailure.message.orEmpty().contains("输出上限") -> "高推理达到输出上限"
                        else -> "推理无最终答案"
                    }
                    "${config.analysisMode.label} · $reason → ${retryDecision.displayLabel}"""",
    "fallback note",
)

a = replace_once(
    a,
    """    private fun JSONObject.requireCompletedResponse() {
        val status = optString("status")
        if (status == "incomplete") {
            val reason = optJSONObject("incomplete_details")?.optString("reason").orEmpty()
            error("模型输出不完整：${reason.ifBlank { "达到输出上限" }}")
        }
        val choice = optJSONArray("choices")?.optJSONObject(0)
        when (choice?.optString("finish_reason")) {
            "length" -> error("模型达到输出上限，没有生成完整 JSON")
            "content_filter" -> error("模型输出被内容过滤器中断")
        }""",
    """    private fun JSONObject.hasCompleteForecastContent(): Boolean {
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

    private fun JSONObject.requireCompletedResponse() {
        val completeForecastContent = hasCompleteForecastContent()
        val status = optString("status")
        if (status == "incomplete" && !completeForecastContent) {
            val reason = optJSONObject("incomplete_details")?.optString("reason").orEmpty()
            error("模型输出不完整：${reason.ifBlank { "达到输出上限" }}")
        }
        val choice = optJSONArray("choices")?.optJSONObject(0)
        when (choice?.optString("finish_reason")) {
            "length" -> if (!completeForecastContent) error("模型达到输出上限，没有生成完整 JSON")
            "content_filter" -> error("模型输出被内容过滤器中断")
        }""",
    "accept complete JSON on length finish",
)

r = replace_once(
    r,
    """    fun stateFor(
        decision: AiReasoningDecision,""",
    """    fun fallback(config: AiConfig): AiReasoningDecision {
        val low = resolve(config, AiReasoningMode.LOW)
        return when (low.protocol) {
            AiReasoningProtocol.DEEPSEEK,
            AiReasoningProtocol.OPENROUTER,
            AiReasoningProtocol.ENABLE_THINKING -> low.copy(
                sendControl = true,
                enableThinking = false,
                effort = null,
                displayLabel = "${low.protocol.label} · 已强制关闭推理重试",
            )
            else -> low.copy(displayLabel = "${low.displayLabel} · 重试")
        }
    }

    fun stateFor(
        decision: AiReasoningDecision,""",
    "explicit fallback",
)

g = replace_once(g, "versionCode = 23", "versionCode = 24", "version code")
g = replace_once(g, 'versionName = "5.4.6"', 'versionName = "5.4.7"', "version name")
rd = replace_once(rd, "- 版本：5.4.6", "- 版本：5.4.7", "README version")

ai.write_text(a)
reasoning.write_text(r)
gradle.write_text(g)
readme.write_text(rd)

Path("RELEASE_NOTES_v5.4.7.md").write_text(
    """# 天机 v5.4.7 测试版

- 修复 DeepSeek 高推理达到输出上限后，重试仍默认开启思考导致再次截断的问题。
- DeepSeek 高推理输出预算由 4096 提升到 32768，最长等待调整为 180 秒。
- 高推理失败后明确发送 thinking=disabled，再用 1024 token 生成最终 JSON。
- 即使接口返回 length，只要 position 与 10 项 scores 已完整有效，仍可安全接收。
- 保留 60/120 期窗口、独立名次选择、六码/七码客户端排序和真实开奖验证。
"""
)

test = Path("app/src/test/java/com/tianji/probabilitylab/nativev4/ai/AiReasoningFallbackTest.kt")
test.parent.mkdir(parents=True, exist_ok=True)
test.write_text(
    """package com.tianji.probabilitylab.nativev4.ai

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class AiReasoningFallbackTest {
    @Test
    fun deepSeekFallbackExplicitlyDisablesThinking() {
        val config = AiConfig(
            provider = AiProvider.DEEPSEEK,
            endpoint = AiProvider.DEEPSEEK.defaultEndpoint,
            model = AiProvider.DEEPSEEK.defaultModel,
            reasoningMode = AiReasoningMode.HIGH,
        )
        val fallback = AiReasoningEngine.fallback(config)
        assertEquals(AiReasoningProtocol.DEEPSEEK, fallback.protocol)
        assertTrue(fallback.sendControl)
        assertFalse(fallback.enableThinking)
        assertFalse(fallback.expectsReasoning)
    }
}
"""
)

print("Applied Tianji v5.4.7 DeepSeek output-limit fix")
