package com.tianji.probabilitylab.nativev4.ai

import kotlin.math.roundToInt

/**
 * Audits the short explanation returned with a forecast. Invalid or English-only explanations are
 * hidden, but a valid position/scores matrix is still kept so presentation quality never causes a
 * second expensive prediction request.
 */
object AiExplanationPolicy {
    val FACTOR_LABELS = listOf(
        "近20期频次",
        "近60期频次",
        "当前遗漏",
        "后继转移",
        "趋势稳定性",
    )

    data class Audit(
        val normalizedWeights: List<Double>,
        val activeFactors: Int,
        val validMultiFactor: Boolean,
    ) {
        val weightSummary: String
            get() = FACTOR_LABELS.zip(normalizedWeights).joinToString(" · ") { (label, weight) ->
                "$label ${(weight * 100).roundToInt()}%"
            }
    }

    fun auditWeights(raw: List<Double>): Audit {
        if (raw.size != FACTOR_LABELS.size || raw.any { !it.isFinite() || it < 0.0 }) {
            return Audit(emptyList(), 0, false)
        }
        val sum = raw.sum()
        if (!sum.isFinite() || sum <= 0.0) return Audit(emptyList(), 0, false)
        val normalized = raw.map { it / sum }
        val active = normalized.count { it >= 0.08 }
        val valid = active >= 3 && (normalized.maxOrNull() ?: 1.0) <= 0.65
        return Audit(normalized, active, valid)
    }

    fun isChineseExplanation(vararg values: String): Boolean = values.all { value ->
        val text = value.trim()
        if (text.isBlank()) return@all false
        val han = text.count { it in '\u4E00'..'\u9FFF' }
        val latin = text.count { it.isLetter() && it !in '\u4E00'..'\u9FFF' }
        han >= 4 && han.toDouble() / (han + latin).coerceAtLeast(1) >= 0.35
    }

    fun concise(value: String, maxChars: Int): String = value
        .replace(Regex("\\s+"), " ")
        .trim()
        .take(maxChars)
}
