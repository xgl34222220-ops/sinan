package com.tianji.probabilitylab.nativev4.ai

import kotlin.math.abs
import kotlin.math.ln

data class AiConsensusInput(
    val profileId: String,
    val modelIdentity: String,
    val position: Int,
    val top6: List<Int>,
    val top7: List<Int>,
    val probabilities: List<Double>,
    val weight: Double = 1.0,
    val settled: Int = 0,
)

data class AiConsensus(
    val position: Int,
    val top6: List<Int>,
    val top7: List<Int>,
    val probabilities: List<Double>,
    val confidenceMargin: Double,
    val disagreement: Double,
    val supportingProfiles: Int,
    val totalProfiles: Int,
    val votes: Map<Int, Double>,
)

data class AiConsensusEvaluation(
    val consensus: AiConsensus?,
    val reasons: List<String>,
) {
    val stable: Boolean get() = consensus != null && reasons.isEmpty()
}

data class ProbabilityMetrics(
    val brierScore: Double,
    val logLoss: Double,
    val actualRank: Int,
)

object AiProbabilityVector {
    fun normalize(raw: List<Double>): List<Double> {
        require(raw.size == 10 && raw.all { it.isFinite() && it >= 0.0 }) {
            "AI 返回的10号码评分无效"
        }
        val sum = raw.sum()
        require(sum > 0.0) { "AI 返回的10号码评分全部为零" }
        return raw.map { it / sum }
    }

    fun ranking(probabilities: List<Double>): List<Int> {
        val normalized = normalize(probabilities)
        return (1..10).sortedWith(
            compareByDescending<Int> { normalized[it - 1] }
                .thenBy { it },
        )
    }

    fun requireForecastable(probabilities: List<Double>): List<Double> {
        val normalized = normalize(probabilities)
        val ranking = ranking(normalized)
        val totalSpread = normalized.maxOrNull()!! - normalized.minOrNull()!!
        val boundaryMargin = normalized[ranking[5] - 1] - normalized[ranking[6] - 1]
        require(totalSpread > 1e-9) {
            "AI 概率矩阵完全相同，请返回至少6位小数的原始scores"
        }
        require(boundaryMargin > 1e-12) {
            "AI 第6与第7候选评分同分，请返回更高精度的原始scores"
        }
        return normalized
    }

    fun legacy(top6: List<Int>, top7: List<Int>): List<Double> {
        val rank = (top6 + top7.filterNot(top6::contains) + (1..10).filterNot(top7::contains)).distinct()
        val raw = (1..10).map { number ->
            val index = rank.indexOf(number).takeIf { it >= 0 } ?: 9
            (10 - index).toDouble()
        }
        return normalize(raw)
    }

    fun metrics(probabilities: List<Double>, actualNumber: Int): ProbabilityMetrics {
        require(actualNumber in 1..10)
        val normalized = normalize(probabilities)
        val brier = normalized.mapIndexed { index, probability ->
            val target = if (index == actualNumber - 1) 1.0 else 0.0
            val delta = probability - target
            delta * delta
        }.average()
        return ProbabilityMetrics(
            brierScore = brier,
            logLoss = -ln(normalized[actualNumber - 1].coerceAtLeast(1e-12)),
            actualRank = ranking(normalized).indexOf(actualNumber) + 1,
        )
    }
}

object AiOutputValidator {
    fun requireValidCandidateSets(top6: List<Int>, top7: List<Int>) {
        require(top6.size == 6 && top6.toSet().size == 6 && top6.all { it in 1..10 }) {
            "AI 返回的六码无效"
        }
        require(
            top7.size == 7 && top7.toSet().size == 7 && top7.all { it in 1..10 } &&
                top7.containsAll(top6),
        ) { "AI 返回的七码无效" }
    }
}

/** Uses one vote per distinct model and only combines models selecting the same position. */
object AiConsensusEngine {
    fun evaluate(inputs: List<AiConsensusInput>): AiConsensusEvaluation {
        val valid = inputs.filter { input ->
            input.position in 0..9 &&
                input.top6.size == 6 && input.top6.toSet().size == 6 &&
                input.top7.size == 7 && input.top7.toSet().size == 7 &&
                input.top7.containsAll(input.top6) &&
                runCatching { AiProbabilityVector.normalize(input.probabilities) }.isSuccess
        }.distinctBy { input ->
            input.modelIdentity.substringAfterLast(" · ").trim().lowercase().ifBlank { input.profileId }
        }
        if (valid.size < 2) {
            return AiConsensusEvaluation(null, listOf("至少需要2个不同模型"))
        }
        val group = valid.groupBy(AiConsensusInput::position)
            .entries
            .sortedWith(
                compareByDescending<Map.Entry<Int, List<AiConsensusInput>>> { entry ->
                    entry.value.sumOf { it.weight.coerceIn(0.1, 3.0) }
                }.thenByDescending { it.value.size }.thenBy { it.key },
            )
            .first()
        if (group.value.size < 2) {
            return AiConsensusEvaluation(null, listOf("AI选择的名次不同，不能混合号码"))
        }

        val weights = group.value.map { it.weight.coerceIn(0.1, 3.0) }
        val totalWeight = weights.sum()
        val probabilities = (0 until 10).map { index ->
            group.value.mapIndexed { modelIndex, input ->
                AiProbabilityVector.normalize(input.probabilities)[index] * weights[modelIndex]
            }.sum() / totalWeight
        }.let(AiProbabilityVector::normalize)
        val ranking = AiProbabilityVector.ranking(probabilities)
        val margin = probabilities[ranking[5] - 1] - probabilities[ranking[6] - 1]
        val disagreement = averagePairwiseDistance(group.value.map { AiProbabilityVector.normalize(it.probabilities) })
        val reasons = buildList {
            if (margin < 0.005) add("第6与第7候选边界过小")
            if (disagreement > 0.32) add("AI概率分歧过大")
            if (group.value.all { it.settled >= 100 && it.weight <= 0.25 }) {
                add("已有前向样本的模型均未超过随机基线")
            }
        }
        val votes = (1..10).associateWith { number ->
            group.value.mapIndexed { index, input ->
                if (number in input.top6) weights[index] else 0.0
            }.sum()
        }
        return AiConsensusEvaluation(
            consensus = AiConsensus(
                position = group.key,
                top6 = ranking.take(6),
                top7 = ranking.take(7),
                probabilities = probabilities,
                confidenceMargin = margin,
                disagreement = disagreement,
                supportingProfiles = group.value.size,
                totalProfiles = valid.size,
                votes = votes,
            ),
            reasons = reasons,
        )
    }

    fun build(inputs: List<AiConsensusInput>): AiConsensus? =
        evaluate(inputs).takeIf(AiConsensusEvaluation::stable)?.consensus

    fun fromForecasts(
        forecasts: List<AiForecast>,
        audits: List<AiProfileAudit> = emptyList(),
    ): AiConsensus? = build(forecastInputs(forecasts, audits))

    fun evaluateForecasts(
        forecasts: List<AiForecast>,
        audits: List<AiProfileAudit> = emptyList(),
    ): AiConsensusEvaluation = evaluate(forecastInputs(forecasts, audits))

    fun fromRecords(
        records: List<AiForecastRecord>,
        audits: List<AiProfileAudit> = emptyList(),
    ): AiConsensus? = build(
        records.map { record ->
            val audit = matchingAudit(
                audits = audits,
                profileId = record.profileId,
                model = record.model,
                analysisMode = record.analysisMode,
                reasoningMode = record.reasoningMode,
                reasoningProtocol = record.reasoningProtocol,
            )
            AiConsensusInput(
                record.profileId,
                record.model,
                record.position,
                record.top6,
                record.top7,
                record.probabilities,
                audit?.forwardWeight ?: 1.0,
                audit?.settled ?: 0,
            )
        },
    )

    private fun forecastInputs(
        forecasts: List<AiForecast>,
        audits: List<AiProfileAudit>,
    ): List<AiConsensusInput> = forecasts.map { forecast ->
        val audit = matchingAudit(
            audits = audits,
            profileId = forecast.profileId,
            model = forecast.model,
            analysisMode = forecast.analysisMode,
            reasoningMode = forecast.reasoningMode,
            reasoningProtocol = forecast.reasoningProtocol,
        )
        AiConsensusInput(
            forecast.profileId,
            forecast.model,
            forecast.position,
            forecast.top6,
            forecast.top7,
            forecast.probabilities,
            audit?.forwardWeight ?: 1.0,
            audit?.settled ?: 0,
        )
    }

    internal fun matchingAudit(
        audits: List<AiProfileAudit>,
        profileId: String,
        model: String,
        analysisMode: AiAnalysisMode,
        reasoningMode: AiReasoningMode,
        reasoningProtocol: AiReasoningProtocol,
    ): AiProfileAudit? {
        val candidates = audits.filter { it.profileId == profileId && it.model == model }
        return candidates.firstOrNull {
            it.analysisMode == analysisMode &&
                it.reasoningMode == reasoningMode &&
                it.reasoningProtocol == reasoningProtocol
        } ?: candidates.singleOrNull()
    }

    private fun averagePairwiseDistance(vectors: List<List<Double>>): Double {
        if (vectors.size < 2) return 0.0
        var total = 0.0
        var pairs = 0
        for (left in 0 until vectors.lastIndex) {
            for (right in left + 1 until vectors.size) {
                total += vectors[left].zip(vectors[right]).sumOf { (a, b) -> abs(a - b) } / 2.0
                pairs++
            }
        }
        return if (pairs == 0) 0.0 else total / pairs
    }
}
