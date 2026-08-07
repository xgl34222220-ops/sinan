package com.tianji.probabilitylab.nativev4.ai

import android.content.Context
import com.tianji.probabilitylab.nativev4.model.Draw
import com.tianji.probabilitylab.nativev4.model.DrawSnapshot
import com.tianji.probabilitylab.nativev4.model.ForecastReport
import kotlin.math.abs
import kotlin.math.ln
import kotlin.math.max

/**
 * App-side fixed-target continual predictor.
 *
 * The forecast target is no longer a dynamically generated six-number set. Tianji always evaluates
 * the fixed pool 2/3/5/7/8/0 (0 is represented internally as 10) and asks one question only:
 * which of the ten positions is most likely to land inside that pool on the next draw?
 *
 * The remote model is still called as an independent audit source. The final position, however, is
 * selected by a leakage-free binary continual learner whose random baseline is explicitly 60%.
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
        onProgress("正在计算十个名次进入固定六码235780的下一期概率", 0L)
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
            "AI旁路评审已返回，正在按固定六码真实前向成绩确定最终名次",
            System.currentTimeMillis() - started,
        )
        return AiContinualForecastEngine.calibrate(remote, plan)
    }
}

data class AiPositionForwardEvidence(
    val position: Int,
    val validationSamples: Int,
    val targetHits: Int,
    val targetHitRate: Double,
    val averageBinaryLogLoss: Double,
    val maxMissStreak: Int,
    val currentMissStreak: Int,
    val targetProbability: Double,
    val validationScore: Double,
    val gatePassed: Boolean,
    val currentProbabilities: List<Double>,
    val learningProfile: AiLearningProfile,
) {
    val excessOverRandom: Double get() = targetHitRate - AiContinualForecastEngine.RANDOM_TARGET_RATE
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
    const val RANDOM_TARGET_RATE = 0.60
    val TARGET_NUMBERS: List<Int> = listOf(2, 3, 5, 7, 8, 10)
    const val TARGET_LABEL = "235780"

    private const val MAX_VALIDATION_SAMPLES = 60
    private val BINARY_LOG_LOSS_BASELINE = -(
        RANDOM_TARGET_RATE * ln(RANDOM_TARGET_RATE) +
            (1.0 - RANDOM_TARGET_RATE) * ln(1.0 - RANDOM_TARGET_RATE)
        )

    fun buildPlan(
        historyInput: List<Draw>,
        profiles: List<AiLearningProfile>,
        maxValidationSamples: Int = MAX_VALIDATION_SAMPLES,
    ): AiContinualForecastPlan {
        val history = historyInput
            .filter { draw -> draw.numbers.size == 10 && draw.numbers.toSet().size == 10 }
            .distinctBy { it.period }
            .takeLast(240)
        require(history.size >= 40) { "固定六码235780持续学习至少需要40期有效历史" }
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
        val selected = plan.best
        val remoteEvidence = plan.evidence(forecast.position)
        val remoteAgrees = forecast.position == selected.position
        val probabilities = if (remoteAgrees) {
            blendInsideFixedGroups(
                base = selected.currentProbabilities,
                remote = forecast.probabilities,
                targetProbability = selected.targetProbability,
                remoteWeight = 0.22,
            )
        } else {
            selected.currentProbabilities
        }
        val top6 = TARGET_NUMBERS
        val outside = (1..10).filterNot(TARGET_NUMBERS::contains)
        val hedge = outside.maxBy { number -> probabilities[number - 1] }
        val top7 = TARGET_NUMBERS + hedge
        AiOutputValidator.requireValidCandidateSets(top6, top7)

        val rankedPositions = plan.positions.sortedByDescending { it.validationScore }
        val runnerUp = rankedPositions.getOrNull(1)
        val probabilityGap = runnerUp?.let {
            selected.targetProbability - it.targetProbability
        } ?: 0.0
        val targetEdge = selected.targetProbability - RANDOM_TARGET_RATE
        val fixedConfidence = (
            abs(targetEdge) / 0.16 +
                (selected.validationSamples / 60.0).coerceIn(0.0, 1.0) * 0.20
            ).coerceIn(0.0, 1.0)
        val gateText = if (selected.gatePassed) {
            "通过固定目标前向门槛"
        } else {
            "暂未形成强优势，仍按相对最高名次输出"
        }
        val remoteText = if (remoteAgrees) {
            "远端AI旁路评审与固定目标学习器同选第${selected.position + 1}名。"
        } else {
            "远端AI旧通用评审偏向第${remoteEvidence.position + 1}名，仅作为旁路审计，不覆盖固定目标决策。"
        }
        val learningSummary = buildString {
            append("\n固定目标预测：六码固定为$TARGET_LABEL（0按10处理），不再生成动态六码。")
            append("十个名次分别判断下一期是否落入2/3/5/7/8/10；随机基准60%。")
            append("当前第${selected.position + 1}名概率${formatPercent(selected.targetProbability)}，")
            append("相对随机基准${formatSignedPercent(targetEdge)}，")
            append("领先第二候选${formatSignedPercent(probabilityGap)}。")
            append("滚动验证${selected.validationSamples}期，固定六码命中率${formatPercent(selected.targetHitRate)}，")
            append("最长连续未进${selected.maxMissStreak}期，当前连续未进${selected.currentMissStreak}期，$gateText。")
            append(remoteText)
        }
        return forecast.copy(
            position = selected.position,
            top6 = top6,
            top7 = top7,
            probabilities = probabilities,
            analysis = (forecast.analysis + learningSummary).take(1_700),
            riskNote = (
                "固定六码$TARGET_LABEL在每期开奖中恰好覆盖10个位置里的6个位置，因此任取一个名次随机命中基准就是60%。" +
                    "系统只允许用开奖前历史做滚动验证；短期高于60%不等于存在可持续规律。"
                ).take(900),
            selfRating = fixedConfidence,
            executionNote = (
                forecast.executionNote +
                    " · 固定六码$TARGET_LABEL · 十名次二分类前向学习 · 最终第${selected.position + 1}名"
                ).take(520),
        )
    }

    private fun buildPositionEvidence(
        history: List<Draw>,
        position: Int,
        profile: AiLearningProfile,
        maxValidationSamples: Int,
    ): AiPositionForwardEvidence {
        val values = history.map { draw -> draw.numbers[position] }
        val currentTargetProbability = fixedTargetProbability(values)
        val currentProbabilities = fixedTargetDistribution(values, currentTargetProbability)
        val start = max(30, history.size - maxValidationSamples.coerceAtLeast(24))
        var hits = 0
        var samples = 0
        var runningMiss = 0
        var maxMiss = 0
        var totalLogLoss = 0.0
        for (cursor in start until history.size) {
            val prefixValues = history.take(cursor).map { draw -> draw.numbers[position] }
            val probability = fixedTargetProbability(prefixValues)
            val actualHit = history[cursor].numbers[position] in TARGET_NUMBERS
            hits += if (actualHit) 1 else 0
            totalLogLoss += -ln(
                (if (actualHit) probability else 1.0 - probability).coerceAtLeast(1e-12),
            )
            if (actualHit) {
                runningMiss = 0
            } else {
                runningMiss++
                maxMiss = max(maxMiss, runningMiss)
            }
            samples++
        }
        val hitRate = if (samples == 0) {
            RANDOM_TARGET_RATE
        } else {
            (hits + 6.0) / (samples + 10.0)
        }
        val averageLogLoss = if (samples == 0) {
            BINARY_LOG_LOSS_BASELINE
        } else {
            totalLogLoss / samples
        }
        val reliability = (samples / 60.0).coerceIn(0.0, 1.0)
        val hitEdge = (hitRate - RANDOM_TARGET_RATE).coerceIn(-0.25, 0.25)
        val lossEdge = (
            (BINARY_LOG_LOSS_BASELINE - averageLogLoss) / BINARY_LOG_LOSS_BASELINE
            ).coerceIn(-0.35, 0.35)
        val currentEdge = currentTargetProbability - RANDOM_TARGET_RATE
        val score = (
            currentTargetProbability +
                currentEdge * 0.35 +
                reliability * hitEdge * 0.24 +
                reliability * lossEdge * 0.08 -
                max(0, maxMiss - 4) * 0.015
            ).coerceIn(0.05, 0.95)
        val passed = samples >= 24 &&
            hitRate >= 0.61 &&
            averageLogLoss <= BINARY_LOG_LOSS_BASELINE * 1.02 &&
            maxMiss <= 8
        return AiPositionForwardEvidence(
            position = position,
            validationSamples = samples,
            targetHits = hits,
            targetHitRate = hitRate,
            averageBinaryLogLoss = averageLogLoss,
            maxMissStreak = maxMiss,
            currentMissStreak = currentMissStreak(values),
            targetProbability = currentTargetProbability,
            validationScore = score,
            gatePassed = passed,
            currentProbabilities = currentProbabilities,
            learningProfile = profile,
        )
    }

    private fun fixedTargetProbability(values: List<Int>): Double {
        if (values.isEmpty()) return RANDOM_TARGET_RATE
        val windows = listOf(
            12 to 0.36,
            30 to 0.30,
            60 to 0.22,
            120 to 0.12,
        )
        var multiscale = 0.0
        windows.forEach { (window, weight) ->
            val subset = values.takeLast(window.coerceAtMost(values.size))
            val hits = subset.count(TARGET_NUMBERS::contains).toDouble()
            multiscale += weight * betaRate(hits, subset.size.toDouble())
        }

        var decayWeight = 1.0
        var decayHits = 0.0
        var decayTotal = 0.0
        values.takeLast(120).asReversed().forEach { value ->
            decayTotal += decayWeight
            if (value in TARGET_NUMBERS) decayHits += decayWeight
            decayWeight *= 0.94
        }
        val recency = betaRate(decayHits, decayTotal, priorStrength = 5.0)

        val currentState = values.last() in TARGET_NUMBERS
        var transitionHits = 0.0
        var transitionTotal = 0.0
        for (index in 1 until values.size) {
            if ((values[index - 1] in TARGET_NUMBERS) == currentState) {
                transitionTotal += 1.0
                if (values[index] in TARGET_NUMBERS) transitionHits += 1.0
            }
        }
        val transition = betaRate(transitionHits, transitionTotal, priorStrength = 8.0)

        val currentNumber = values.last()
        var successorHits = 0.0
        var successorTotal = 0.0
        for (index in 1 until values.size) {
            if (values[index - 1] == currentNumber) {
                successorTotal += 1.0
                if (values[index] in TARGET_NUMBERS) successorHits += 1.0
            }
        }
        val successor = betaRate(successorHits, successorTotal, priorStrength = 7.0)

        var probability =
            multiscale * 0.46 + recency * 0.24 + transition * 0.20 + successor * 0.10
        val reliability = (values.size / 120.0).coerceIn(0.0, 1.0)
        probability = RANDOM_TARGET_RATE +
            (probability - RANDOM_TARGET_RATE) * (0.45 + 0.55 * reliability)
        return probability.coerceIn(0.38, 0.82)
    }

    private fun fixedTargetDistribution(
        values: List<Int>,
        targetProbability: Double,
    ): List<Double> {
        val recent = values.takeLast(60.coerceAtMost(values.size))
        val counts = (1..10).associateWith { number -> recent.count { it == number } + 1.5 }
        val outside = (1..10).filterNot(TARGET_NUMBERS::contains)
        val targetTotal = TARGET_NUMBERS.sumOf { number -> counts.getValue(number) }
        val outsideTotal = outside.sumOf { number -> counts.getValue(number) }
        return (1..10).map { number ->
            if (number in TARGET_NUMBERS) {
                targetProbability * counts.getValue(number) / targetTotal
            } else {
                (1.0 - targetProbability) * counts.getValue(number) / outsideTotal
            }
        }.let(::normalize)
    }

    private fun blendInsideFixedGroups(
        base: List<Double>,
        remote: List<Double>,
        targetProbability: Double,
        remoteWeight: Double,
    ): List<Double> {
        if (base.size != 10 || remote.size != 10) return base
        val blended = normalize(
            base.indices.map { index ->
                base[index] * (1.0 - remoteWeight) + remote[index] * remoteWeight
            },
        )
        val targetTotal = TARGET_NUMBERS.sumOf { number -> blended[number - 1] }
        val outside = (1..10).filterNot(TARGET_NUMBERS::contains)
        val outsideTotal = outside.sumOf { number -> blended[number - 1] }
        return (1..10).map { number ->
            if (number in TARGET_NUMBERS) {
                targetProbability * blended[number - 1] / targetTotal.coerceAtLeast(1e-12)
            } else {
                (1.0 - targetProbability) * blended[number - 1] / outsideTotal.coerceAtLeast(1e-12)
            }
        }.let(::normalize)
    }

    private fun betaRate(
        hits: Double,
        total: Double,
        priorStrength: Double = 10.0,
    ): Double =
        (hits + RANDOM_TARGET_RATE * priorStrength) / (total + priorStrength)

    private fun currentMissStreak(values: List<Int>): Int {
        var streak = 0
        for (value in values.asReversed()) {
            if (value in TARGET_NUMBERS) break
            streak++
        }
        return streak
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
