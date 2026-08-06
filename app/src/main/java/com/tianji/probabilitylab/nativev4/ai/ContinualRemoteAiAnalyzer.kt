package com.tianji.probabilitylab.nativev4.ai

import android.content.Context
import com.tianji.probabilitylab.nativev4.model.Draw
import com.tianji.probabilitylab.nativev4.model.DrawSnapshot
import com.tianji.probabilitylab.nativev4.model.ForecastReport
import kotlin.math.exp
import kotlin.math.ln
import kotlin.math.max

/**
 * App-side AI guard that keeps the remote model independent from the native forecast while still
 * making every settled AI result useful to the next prediction.
 *
 * The remote provider continues to receive raw history only. After it returns, Tianji evaluates
 * the selected position with leakage-free rolling forward tests and blends the number matrix with
 * the profile that belongs to this exact lottery + AI profile + model mode + position.
 */
class ContinualRemoteAiAnalyzer(context: Context) {
    private val delegate = RemoteAiAnalyzer(context.applicationContext)
    private val learningStore = AiAdaptiveLearningStore(context.applicationContext)

    fun cancelActiveRequests(profileId: String? = null) =
        delegate.cancelActiveRequests(profileId)

    fun listModels(config: AiConfig): AiModelCatalog = delegate.listModels(config)

    fun testConnection(config: AiConfig): AiConnectionProbe = delegate.testConnection(config)

    fun analyze(
        config: AiConfig,
        snapshot: DrawSnapshot,
        report: ForecastReport,
        onProgress: (String, Long) -> Unit = { _, _ -> },
    ): AiForecast {
        val started = System.currentTimeMillis()
        onProgress("正在对十个名次执行滚动前向学习验证", 0L)
        val strategy = AiLearningStrategy.official(config)
        val profiles = (0 until 10).map { position ->
            learningStore.profile(
                lotteryKey = snapshot.lottery.apiKey,
                profileId = config.id,
                model = strategy,
                position = position,
            )
        }
        val plan = AiContinualForecastEngine.buildPlan(snapshot.history, profiles)
        val remote = delegate.analyze(config, snapshot, report, onProgress)
        onProgress(
            "AI矩阵已返回，正在按真实结算成绩校准名次与号码权重",
            System.currentTimeMillis() - started,
        )
        return AiContinualForecastEngine.calibrate(remote, plan)
    }
}

data class AiPositionForwardEvidence(
    val position: Int,
    val validationSamples: Int,
    val top6Hits: Int,
    val top6HitRate: Double,
    val averageLogLoss: Double,
    val maxMissStreak: Int,
    val boundaryMargin: Double,
    val validationScore: Double,
    val gatePassed: Boolean,
    val currentProbabilities: List<Double>,
    val learningProfile: AiLearningProfile,
) {
    val excessOverRandom: Double get() = top6HitRate - 0.60
}

data class AiContinualForecastPlan(
    val historySize: Int,
    val positions: List<AiPositionForwardEvidence>,
) {
    val best: AiPositionForwardEvidence = positions.maxBy { it.validationScore }
    val passedCount: Int = positions.count { it.gatePassed }

    fun evidence(position: Int): AiPositionForwardEvidence =
        positions.first { it.position == position }
}

object AiContinualForecastEngine {
    private const val MAX_VALIDATION_SAMPLES = 48
    private const val RANDOM_TOP6_RATE = 0.60
    private const val UNIFORM_LOG_LOSS = 2.302585092994046

    fun buildPlan(
        historyInput: List<Draw>,
        profiles: List<AiLearningProfile>,
        maxValidationSamples: Int = MAX_VALIDATION_SAMPLES,
    ): AiContinualForecastPlan {
        val history = historyInput
            .filter { draw -> draw.numbers.size == 10 && draw.numbers.toSet().size == 10 }
            .distinctBy { it.period }
            .takeLast(240)
        require(history.size >= 40) { "持续学习至少需要40期有效历史" }
        val normalizedProfiles = (0 until 10).map { position ->
            profiles.getOrNull(position) ?: AiLearningProfile()
        }
        val positions = (0 until 10).map { position ->
            buildPositionEvidence(
                history = history,
                position = position,
                profile = normalizedProfiles[position],
                maxValidationSamples = maxValidationSamples,
            )
        }
        return AiContinualForecastPlan(history.size, positions)
    }

    fun calibrate(
        forecast: AiForecast,
        plan: AiContinualForecastPlan,
    ): AiForecast {
        val selected = plan.evidence(forecast.position)
        val best = plan.best
        val qualityRatio = selected.validationScore / best.validationScore.coerceAtLeast(1e-9)
        val selectedRank = plan.positions
            .sortedByDescending { it.validationScore }
            .indexOfFirst { it.position == selected.position } + 1

        // Do not freeze an obviously weak random position when a materially better, fully validated
        // position exists. This is a veto only; it never substitutes the native model's position or
        // candidate set into the AI result.
        require(
            !best.gatePassed || selected.gatePassed || selectedRank <= 4 || qualityRatio >= 0.70,
        ) {
            "AI选择的第${selected.position + 1}名未通过持续学习门槛，且真实前向成绩明显弱于第${best.position + 1}名；本期拒绝冻结随机弱名次"
        }

        val sampleConfidence = (selected.learningProfile.settled / 80.0).coerceIn(0.0, 1.0)
        val forwardConfidence = if (selected.gatePassed) 1.0 else {
            ((selected.top6HitRate - 0.50) / 0.15).coerceIn(0.0, 1.0)
        }
        val learningWeight = (
            0.18 + sampleConfidence * 0.10 + forwardConfidence * 0.10
        ).coerceIn(0.18, 0.38)
        val aiWeight = 1.0 - learningWeight
        val calibrated = normalize(
            forecast.probabilities.indices.map { index ->
                forecast.probabilities[index] * aiWeight +
                    selected.currentProbabilities[index] * learningWeight
            },
        )
        val ranking = calibrated.indices
            .sortedByDescending { calibrated[it] }
            .map { it + 1 }
        val top6 = ranking.take(6)
        val top7 = ranking.take(7)
        AiOutputValidator.requireValidCandidateSets(top6, top7)
        val entropy = -calibrated.sumOf { probability ->
            if (probability <= 0.0) 0.0 else probability * ln(probability)
        }
        val concentration = (1.0 - entropy / ln(10.0)).coerceIn(0.0, 1.0)
        val gateText = if (selected.gatePassed) {
            "已通过强证据门槛"
        } else {
            "当前未形成强优势，按弱证据运行"
        }
        val learningPercent = learningWeight * 100.0
        val aiPercent = aiWeight * 100.0
        val recentRate = selected.learningProfile.recent20Top6Rate
        val learningSummary = buildString {
            append("\n持续学习校准：十个名次分别滚动前向验证，当前${plan.passedCount}个名次通过门槛；")
            append("AI选择第${selected.position + 1}名，验证${selected.validationSamples}期，")
            append("六码命中率${formatPercent(selected.top6HitRate)}，")
            append("相对随机基准${formatSignedPercent(selected.excessOverRandom)}，")
            append("最长连续未中${selected.maxMissStreak}期，$gateText。")
            append("最终号码矩阵保留AI ${formatPercent(aiWeight)}，")
            append("该模型在该名次的在线学习权重${formatPercent(learningWeight)}。")
            if (selected.learningProfile.settled > 0) {
                append("已结算${selected.learningProfile.settled}期")
                recentRate?.let { append("，近20期命中率${formatPercent(it)}") }
                append("。")
            }
        }
        return forecast.copy(
            top6 = top6,
            top7 = top7,
            probabilities = calibrated,
            analysis = (forecast.analysis + learningSummary).take(1_600),
            riskNote = (
                forecast.riskNote +
                    " App端已启用按彩种、AI配置、模型模式和具体名次隔离的在线学习；" +
                    "只有真实开奖结算会改变下一期权重，持续学习不代表准确率会单调上升。"
                ).take(900),
            selfRating = max(forecast.selfRating, concentration * 0.85),
            executionNote = (
                forecast.executionNote +
                    " · 十名次滚动前向门槛 · AI${String.format(java.util.Locale.US, "%.0f", aiPercent)}%" +
                    "+名次学习${String.format(java.util.Locale.US, "%.0f", learningPercent)}%"
                ).take(500),
        )
    }

    private fun buildPositionEvidence(
        history: List<Draw>,
        position: Int,
        profile: AiLearningProfile,
        maxValidationSamples: Int,
    ): AiPositionForwardEvidence {
        val current = AiAdaptiveSignalEngine.compute(history, position, profile)
        val start = max(30, history.size - maxValidationSamples.coerceAtLeast(24))
        var hits = 0
        var samples = 0
        var runningMiss = 0
        var maxMiss = 0
        var totalLogLoss = 0.0
        for (cursor in start until history.size) {
            val prefix = history.take(cursor)
            // Neutral historical profile prevents today's learned weights from leaking backwards
            // into old validation periods.
            val snapshot = AiAdaptiveSignalEngine.compute(
                prefix,
                position,
                AiLearningProfile(),
            )
            val ranking = snapshot.adaptiveScores.indices
                .sortedByDescending { snapshot.adaptiveScores[it] }
            val actual = history[cursor].numbers[position]
            val hit = actual in ranking.take(6).map { it + 1 }
            if (hit) {
                hits++
                runningMiss = 0
            } else {
                runningMiss++
                maxMiss = max(maxMiss, runningMiss)
            }
            totalLogLoss += -ln(snapshot.adaptiveScores[actual - 1].coerceAtLeast(1e-12))
            samples++
        }
        val hitRate = (hits + 6.0) / (samples + 10.0)
        val averageLogLoss = if (samples == 0) UNIFORM_LOG_LOSS else totalLogLoss / samples
        val rankedCurrent = current.adaptiveScores.indices
            .sortedByDescending { current.adaptiveScores[it] }
        val boundary = current.adaptiveScores[rankedCurrent[5]] -
            current.adaptiveScores[rankedCurrent[6]]
        val lossEdge = ((UNIFORM_LOG_LOSS - averageLogLoss) / UNIFORM_LOG_LOSS)
            .coerceIn(-0.35, 0.35)
        val validationScore = (
            1.0 +
                (hitRate - RANDOM_TOP6_RATE) * 5.0 +
                lossEdge * 0.9 +
                boundary * 4.0 -
                max(0, maxMiss - 3) * 0.03
            ).coerceAtLeast(0.05)
        val passed = samples >= 24 &&
            hitRate >= 0.615 &&
            averageLogLoss <= UNIFORM_LOG_LOSS * 1.01 &&
            maxMiss <= 8
        return AiPositionForwardEvidence(
            position = position,
            validationSamples = samples,
            top6Hits = hits,
            top6HitRate = hitRate,
            averageLogLoss = averageLogLoss,
            maxMissStreak = maxMiss,
            boundaryMargin = boundary,
            validationScore = validationScore,
            gatePassed = passed,
            currentProbabilities = current.adaptiveScores,
            learningProfile = profile,
        )
    }

    private fun normalize(values: List<Double>): List<Double> {
        val safe = values.map { value ->
            if (value.isFinite() && value > 0.0) value else 1e-12
        }
        val total = safe.sum().takeIf { it.isFinite() && it > 0.0 } ?: 1.0
        return safe.map { it / total }
    }

    private fun formatPercent(value: Double): String =
        String.format(java.util.Locale.US, "%.1f%%", value * 100.0)

    private fun formatSignedPercent(value: Double): String =
        String.format(java.util.Locale.US, "%+.1f个百分点", value * 100.0)
}
