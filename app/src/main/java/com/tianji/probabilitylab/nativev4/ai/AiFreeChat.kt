package com.tianji.probabilitylab.nativev4.ai

import java.util.UUID

enum class AiChatRole {
    USER,
    ASSISTANT,
}

data class AiChatMessage(
    val id: String = UUID.randomUUID().toString(),
    val role: AiChatRole,
    val content: String,
    val createdAtEpochMs: Long = System.currentTimeMillis(),
    val latencyMs: Long? = null,
)

data class AiChatPrediction(
    val position: Int,
    val top6: List<Int>,
    val top7: List<Int>,
    val probabilities: List<Double>,
)

data class AiChatSession(
    val profileId: String,
    val messages: List<AiChatMessage> = emptyList(),
    val isRunning: Boolean = false,
    val progress: String = "",
    val error: String? = null,
    val prediction: AiChatPrediction? = null,
    val targetPeriod: String? = null,
)

data class AiChatReply(
    val content: String,
    val prediction: AiChatPrediction?,
    val latencyMs: Long,
    val responseId: String,
    val reasoningTokens: Int?,
    val reasoningVerified: Boolean,
)

/**
 * Keeps free-form chat independent from the official frozen forecast protocol.
 * A prediction card is only extracted when the user's own request asks for candidates.
 */
object AiChatProtocol {
    private val predictionTerms = listOf(
        "预测", "候选", "六码", "七码", "号码", "出号", "推荐", "名次",
        "position", "scores", "forecast", "pick",
    )

    fun wantsPrediction(text: String): Boolean {
        val normalized = text.trim().lowercase()
        return predictionTerms.any(normalized::contains)
    }

    fun parsePrediction(text: String): AiChatPrediction? {
        val canonical = AiForecastPayloadExtractor.salvageCoreJson(text) ?: return null
        val position = Regex("\\\"position\\\":(10|[1-9])")
            .find(canonical)?.groupValues?.getOrNull(1)?.toIntOrNull() ?: return null
        val scoreText = Regex("\\\"scores\\\":\\[([^]]+)]")
            .find(canonical)?.groupValues?.getOrNull(1) ?: return null
        val scores = scoreText.split(',').mapNotNull { it.trim().toDoubleOrNull() }
        if (scores.size != 10 || scores.any { !it.isFinite() || it < 0.0 }) return null
        val sum = scores.sum()
        if (!sum.isFinite() || sum <= 0.0) return null
        val probabilities = scores.map { it / sum }
        val ranking = probabilities.indices
            .sortedWith(compareByDescending<Int> { probabilities[it] }.thenBy { it })
            .map { it + 1 }
        return AiChatPrediction(
            position = position - 1,
            top6 = ranking.take(6),
            top7 = ranking.take(7),
            probabilities = probabilities,
        )
    }

    fun visibleText(text: String, hasPrediction: Boolean): String {
        var value = text.trim()
        value = value.replace(
            Regex("(?s)<tianji_forecast>.*?</tianji_forecast>"),
            "",
        ).trim()
        if (hasPrediction) {
            AiForecastPayloadExtractor.balancedJsonObjects(value)
                .firstOrNull { AiForecastPayloadExtractor.salvageCoreJson(it) != null }
                ?.let { value = value.replace(it, "").trim() }
        }
        value = value
            .replace(Regex("(?s)```json\\s*```"), "")
            .replace(Regex("\\n{3,}"), "\n\n")
            .trim()
        return value.ifBlank {
            if (hasPrediction) "已根据你的要求生成结构化候选结果。" else "模型已完成本次分析。"
        }
    }

    fun trimHistory(messages: List<AiChatMessage>, maxMessages: Int = 16): List<AiChatMessage> =
        messages.filter { it.content.isNotBlank() }.takeLast(maxMessages.coerceAtLeast(1))
}
