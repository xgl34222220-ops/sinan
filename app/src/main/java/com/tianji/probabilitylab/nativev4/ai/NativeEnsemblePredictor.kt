package com.tianji.probabilitylab.nativev4.ai

import com.tianji.probabilitylab.nativev4.model.ConfidenceInterval
import com.tianji.probabilitylab.nativev4.model.Draw
import com.tianji.probabilitylab.nativev4.model.EvidenceMode
import com.tianji.probabilitylab.nativev4.model.ForecastReport
import com.tianji.probabilitylab.nativev4.model.ModelPerformance
import com.tianji.probabilitylab.nativev4.model.PositionPrediction
import java.math.BigInteger
import kotlin.math.abs
import kotlin.math.exp
import kotlin.math.ln
import kotlin.math.max
import kotlin.math.min
import kotlin.math.pow
import kotlin.math.roundToInt
import kotlin.math.sqrt
import kotlin.math.tanh
import kotlin.random.Random

object NativeEnsemblePredictor {
    const val ALGORITHM_VERSION = "native-ensemble-4.1"
    private const val N = 10
    private const val MIN_HISTORY = 180
    private const val MAX_VALIDATION = 240
    private const val EPSILON = 1e-12

    private data class Spec(
        val key: String,
        val name: String,
        val shortName: String,
        val prior: Double,
    )

    private val specs = listOf(
        Spec("uniform", "无优势随机基线", "基线", 0.10),
        Spec("bayes", "贝叶斯长期频率", "长期", 0.09),
        Spec("dynamic", "动态贝叶斯状态", "动态", 0.14),
        Spec("recency_fast", "12期快速状态", "12期", 0.11),
        Spec("recency_medium", "36期中速状态", "36期", 0.11),
        Spec("recency_slow", "96期慢速状态", "96期", 0.09),
        Spec("markov", "稀疏多阶转移", "转移", 0.11),
        Spec("movement", "名次迁移", "迁移", 0.08),
        Spec("ranking", "排名位置模型", "排名", 0.04),
        Spec("interval", "间隔风险挑战者", "间隔", 0.01),
        Spec("native_ai", "端侧轻量神经网络", "神经AI", 0.12),
    )

    fun predict(historyInput: List<Draw>, payoutMultiplier: Double = 9.8): ForecastReport {
        val history = historyInput.asSequence()
            .filter { it.numbers.size == N && it.numbers.toSet().size == N }
            .distinctBy(Draw::period)
            .sortedWith(compareBy<Draw>({ it.period.length }, Draw::period))
            .toList()
        require(history.size >= MIN_HISTORY) {
            "原生模型至少需要 $MIN_HISTORY 期有效历史，当前 ${history.size} 期"
        }

        val validationDraws = min(MAX_VALIDATION, max(60, history.size / 5))
            .coerceAtMost(history.size - 120)
        val validationStart = history.size - validationDraws
        val fitCount = max(36, (validationDraws * 0.58).roundToInt())
            .coerceAtMost(validationDraws - 24)
        val neuralAudit = TinyNeuralModel(seedFor(history, "audit"))
            .also { it.train(history.subList(0, validationStart)) }
        val samples = (validationStart until history.size).map { index ->
            Sample(
                matrices = matrices(history, index, neuralAudit),
                actual = history[index].numbers,
            )
        }

        val fit = samples.take(fitCount)
        val modelStats = specs.indices.map { model -> evaluateModel(fit, model) }
        val fitSelections = fit.size * N
        val rawWeights = modelStats.mapIndexed { index, stat ->
            if (index == 0) 0.025
            else {
                val hits = (stat.hitRate * fitSelections).roundToInt()
                val coverageLower = wilson(hits, fitSelections).low
                val probabilitySkill = (ln(N.toDouble()) - stat.loss - 0.008).coerceAtLeast(0.0)
                val coverageSkill = (coverageLower - 0.60).coerceAtLeast(0.0)
                specs[index].prior * probabilitySkill * coverageSkill * 1_000.0
            }
        }
        val weights = if (rawWeights.drop(1).sum() <= EPSILON) {
            List(specs.size) { if (it == 0) 1.0 else 0.0 }
        } else normalize(rawWeights)
        val shadowWeights = normalize(
            modelStats.mapIndexed { index, stat ->
                specs[index].prior * exp(((ln(N.toDouble()) - stat.loss) * 3.0).coerceIn(-2.0, 2.0))
            },
        )

        var top6Hits = 0
        var top7Hits = 0
        var lossSum = 0.0
        val blind = samples.drop(fitCount)
        blind.forEach { sample ->
            val matrix = combine(sample.matrices, weights)
            val position = choosePosition(matrix)
            val ranking = ranked(matrix[position])
            val actual = sample.actual[position]
            if (actual in ranking.take(6)) top6Hits++
            if (actual in ranking.take(7)) top7Hits++
            lossSum -= ln(matrix[position][actual - 1].coerceAtLeast(EPSILON))
        }
        val blindCount = blind.size.coerceAtLeast(1)
        val top6Rate = top6Hits.toDouble() / blindCount
        val top7Rate = top7Hits.toDouble() / blindCount
        val top6Interval = wilson(top6Hits, blindCount)
        val top7Interval = wilson(top7Hits, blindCount)
        val averageLoss = lossSum / blindCount
        val randomLoss = ln(N.toDouble())
        val breakEven = (7.0 / payoutMultiplier).coerceIn(0.0, 1.0)
        val blockedReasons = buildList {
            if (blind.size < 96) add("最终冻结盲测不足 96 期")
            if (top6Interval.low <= 0.60) add("六码命中率下界未超过随机 60%")
            if (top7Interval.low <= breakEven) {
                add("七码命中率下界未超过 ${(breakEven * 100).format1()}% 盈亏线")
            }
            if (averageLoss >= randomLoss) add("概率损失未优于均匀随机模型")
            if (weights.drop(1).sum() <= EPSILON) add("候选模型均未形成可验证优势")
        }

        val neuralFinal = TinyNeuralModel(seedFor(history, "final")).also { it.train(history) }
        val displayUsesShadow = weights.drop(1).sum() <= EPSILON
        val displayWeights = if (displayUsesShadow) {
            normalize(shadowWeights.mapIndexed { index, weight -> if (index == 0) 0.0 else weight })
        } else weights
        val finalMatrix = combine(matrices(history, history.size, neuralFinal), displayWeights)
        val selectedPosition = choosePosition(finalMatrix)
        val positions = finalMatrix.mapIndexed { position, row ->
            val order = ranked(row)
            val sorted = row.sortedDescending()
            PositionPrediction(
                position = position,
                probabilities = row.toList(),
                top6 = order.take(6),
                top7 = order.take(7),
                coverage6 = order.take(6).sumOf { row[it - 1] },
                coverage7 = order.take(7).sumOf { row[it - 1] },
                boundaryMargin = (sorted[6] - sorted[7]).coerceAtLeast(0.0),
            )
        }
        val performances = specs.mapIndexed { index, spec ->
            val stat = modelStats[index]
            val weight = weights[index]
            ModelPerformance(
                key = spec.key,
                name = spec.name,
                shortName = spec.shortName,
                priorWeight = spec.prior,
                weight = weight,
                shadowWeight = shadowWeights[index],
                hitRate = stat.hitRate,
                logLoss = stat.loss,
                status = when {
                    index == 0 && weight > 0.99 -> "baseline"
                    weight >= 0.08 -> "active"
                    weight >= 0.005 -> "watch"
                    shadowWeights[index] >= 0.06 -> "shadow"
                    else -> "paused"
                },
            )
        }.sortedWith(
            compareByDescending<ModelPerformance> { it.key == "uniform" }
                .thenByDescending { it.weight }
                .thenByDescending { it.shadowWeight },
        )
        val latest = history.last()
        return ForecastReport(
            algorithmVersion = ALGORITHM_VERSION,
            trainedThroughPeriod = latest.period,
            targetPeriod = incrementPeriod(latest.period),
            historySize = history.size,
            validationDraws = blind.size,
            mode = if (blockedReasons.isEmpty()) EvidenceMode.CERTIFIED else EvidenceMode.OBSERVE,
            displayUsesShadow = displayUsesShadow,
            selectedPosition = selectedPosition,
            positions = positions,
            models = performances,
            top6HitRate = top6Rate,
            top7HitRate = top7Rate,
            top6Interval = top6Interval,
            top7Interval = top7Interval,
            randomTop6Baseline = 0.60,
            randomTop7Baseline = 0.70,
            breakEvenTop7 = breakEven,
            averageLogLoss = averageLoss,
            randomLogLoss = randomLoss,
            dataAdequacy = ((history.size / 3_000.0) * 100).roundToInt().coerceIn(10, 100),
            blockedReasons = blockedReasons,
        )
    }

    private fun matrices(
        history: List<Draw>,
        end: Int,
        neural: TinyNeuralModel,
    ): List<Array<DoubleArray>> = listOf(
        uniform(),
        frequency(history, end, 300, 1.8),
        dynamic(history, end),
        frequency(history, end, 12, 0.9),
        frequency(history, end, 36, 0.72),
        frequency(history, end, 96, 0.58),
        markov(history, end),
        movement(history, end),
        ranking(history, end),
        interval(history, end),
        neural.predict(history, end),
    )

    private fun uniform() = Array(N) { DoubleArray(N) { 1.0 / N } }

    private fun frequency(
        history: List<Draw>,
        end: Int,
        window: Int,
        alpha: Double,
    ): Array<DoubleArray> {
        val matrix = Array(N) { DoubleArray(N) { alpha } }
        for (index in max(0, end - window) until end) {
            for (position in 0 until N) matrix[position][history[index].numbers[position] - 1]++
        }
        return sinkhorn(matrix)
    }

    private fun dynamic(history: List<Draw>, end: Int): Array<DoubleArray> {
        val matrix = Array(N) { DoubleArray(N) { 0.9 } }
        val start = max(0, end - 360)
        for (index in start until end) {
            val age = end - 1 - index
            val weight = 0.5.pow(age / 56.0)
            for (position in 0 until N) matrix[position][history[index].numbers[position] - 1] += weight
        }
        return sinkhorn(matrix)
    }

    private fun markov(history: List<Draw>, end: Int): Array<DoubleArray> {
        val matrix = Array(N) { DoubleArray(N) { 0.8 } }
        if (end < 2) return sinkhorn(matrix)
        val current = history[end - 1]
        for (index in max(1, end - 180) until end) {
            for (position in 0 until N) {
                if (history[index - 1].numbers[position] == current.numbers[position]) {
                    matrix[position][history[index].numbers[position] - 1] += 1.0
                }
            }
        }
        return sinkhorn(matrix)
    }

    private fun movement(history: List<Draw>, end: Int): Array<DoubleArray> {
        val transitions = Array(N) { DoubleArray(N) { 0.7 } }
        for (index in max(1, end - 180) until end) {
            val previous = history[index - 1].numbers
            val next = history[index].numbers
            for (number in 1..N) transitions[previous.indexOf(number)][next.indexOf(number)]++
        }
        val previous = history[end - 1].numbers
        val matrix = Array(N) { DoubleArray(N) }
        for (position in 0 until N) {
            for (candidate in 1..N) matrix[position][candidate - 1] = transitions[previous.indexOf(candidate)][position]
        }
        return sinkhorn(matrix)
    }

    private fun ranking(history: List<Draw>, end: Int): Array<DoubleArray> {
        val matrix = Array(N) { DoubleArray(N) { 1.1 } }
        val start = max(0, end - 240)
        for (index in start until end) {
            val weight = 0.65 + 0.35 * (index - start + 1) / max(1.0, (end - start).toDouble())
            history[index].numbers.forEachIndexed { position, number ->
                matrix[position][number - 1] += weight
                if (position > 0) matrix[position - 1][number - 1] += weight * 0.12
                if (position < N - 1) matrix[position + 1][number - 1] += weight * 0.12
            }
        }
        return sinkhorn(matrix)
    }

    private fun interval(history: List<Draw>, end: Int): Array<DoubleArray> {
        val matrix = Array(N) { DoubleArray(N) { 0.5 } }
        for (position in 0 until N) {
            for (candidate in 1..N) {
                var gap = min(80, end)
                for (index in end - 1 downTo max(0, end - 80)) {
                    if (history[index].numbers[position] == candidate) {
                        gap = end - 1 - index
                        break
                    }
                }
                matrix[position][candidate - 1] += (gap + 2.0).pow(0.42)
            }
        }
        return sinkhorn(matrix)
    }

    private fun evaluateModel(samples: List<Sample>, model: Int): ModelStat {
        var hits = 0
        var loss = 0.0
        var selections = 0
        samples.forEach { sample ->
            val matrix = sample.matrices[model]
            for (position in 0 until N) {
                val actual = sample.actual[position]
                if (actual in ranked(matrix[position]).take(6)) hits++
                loss -= ln(matrix[position][actual - 1].coerceAtLeast(EPSILON))
                selections++
            }
        }
        return ModelStat(
            hitRate = hits.toDouble() / selections.coerceAtLeast(1),
            loss = loss / selections.coerceAtLeast(1),
        )
    }

    private fun combine(
        matrices: List<Array<DoubleArray>>,
        weights: List<Double>,
    ): Array<DoubleArray> {
        val result = Array(N) { DoubleArray(N) }
        matrices.forEachIndexed { model, matrix ->
            for (position in 0 until N) for (number in 0 until N) {
                result[position][number] += weights[model] * matrix[position][number]
            }
        }
        return sinkhorn(result)
    }

    private fun choosePosition(matrix: Array<DoubleArray>): Int = matrix.indices.maxByOrNull { position ->
        val sorted = matrix[position].sortedDescending()
        sorted.take(7).sum() + (sorted[6] - sorted[7]) * 1.5
    } ?: 0

    private fun ranked(row: DoubleArray): List<Int> = row.indices
        .sortedWith(compareByDescending<Int> { row[it] }.thenBy { it })
        .map { it + 1 }

    private fun normalize(values: List<Double>): List<Double> {
        val safe = values.map { if (it.isFinite() && it > 0.0) it else 0.0 }
        val total = safe.sum()
        return if (total <= EPSILON) List(values.size) { 1.0 / values.size } else safe.map { it / total }
    }

    private fun sinkhorn(input: Array<DoubleArray>): Array<DoubleArray> {
        val matrix = Array(N) { row -> input[row].copyOf() }
        repeat(18) {
            for (row in 0 until N) normalizeInPlace(matrix[row])
            for (column in 0 until N) {
                var total = 0.0
                for (row in 0 until N) total += matrix[row][column]
                total = total.coerceAtLeast(EPSILON)
                for (row in 0 until N) matrix[row][column] /= total
            }
        }
        matrix.forEach(::normalizeInPlace)
        return matrix
    }

    private fun normalizeInPlace(values: DoubleArray) {
        val total = values.sum().coerceAtLeast(EPSILON)
        for (index in values.indices) values[index] /= total
    }

    private fun wilson(hits: Int, draws: Int): ConfidenceInterval {
        if (draws <= 0) return ConfidenceInterval(0.0, 1.0)
        val z = 1.959963984540054
        val p = hits.toDouble() / draws
        val denominator = 1.0 + z * z / draws
        val center = (p + z * z / (2.0 * draws)) / denominator
        val radius = z * sqrt(p * (1 - p) / draws + z * z / (4.0 * draws * draws)) / denominator
        return ConfidenceInterval((center - radius).coerceIn(0.0, 1.0), (center + radius).coerceIn(0.0, 1.0))
    }

    private fun incrementPeriod(period: String): String {
        val match = Regex("^(.*?)(\\d+)$").matchEntire(period) ?: return "待公布"
        val prefix = match.groupValues[1]
        val digits = match.groupValues[2]
        return runCatching {
            prefix + BigInteger(digits).add(BigInteger.ONE).toString().padStart(digits.length, '0')
        }.getOrDefault("待公布")
    }

    private fun seedFor(history: List<Draw>, role: String): Int =
        "${history.first().lottery.apiKey}:$role:$ALGORITHM_VERSION".fold(17) { hash, char -> hash * 31 + char.code }

    private fun Double.format1() = String.format(java.util.Locale.US, "%.1f", this)

    private data class Sample(val matrices: List<Array<DoubleArray>>, val actual: List<Int>)
    private data class ModelStat(val hitRate: Double, val loss: Double)

    private class TinyNeuralModel(seed: Int) {
        private val features = 8
        private val hidden = 4
        private val random = Random(seed)
        private val first = Array(hidden) { DoubleArray(features) { (random.nextDouble() - 0.5) * 0.07 } }
        private val firstBias = DoubleArray(hidden)
        private val second = DoubleArray(hidden) { (random.nextDouble() - 0.5) * 0.07 }

        fun train(history: List<Draw>) {
            if (history.size < 48) return
            val start = max(48, history.size - 120)
            val examples = (start until history.size).map { index ->
                FeatureBuilder.matrix(history, index) to history[index].numbers
            }
            repeat(4) { epoch ->
                val rate = 0.018 / sqrt(epoch + 1.0)
                val ordered = if (epoch % 2 == 0) examples else examples.asReversed()
                ordered.forEach { (matrix, actual) ->
                    for (position in 0 until N) trainPosition(matrix[position], actual[position] - 1, rate)
                }
            }
        }

        fun predict(history: List<Draw>, end: Int): Array<DoubleArray> {
            val matrix = FeatureBuilder.matrix(history, end)
            val raw = Array(N) { position ->
                DoubleArray(N) { candidate -> exp(output(hidden(matrix[position][candidate])).coerceIn(-8.0, 8.0)) }
            }
            return sinkhorn(raw)
        }

        private fun trainPosition(input: Array<DoubleArray>, target: Int, rate: Double) {
            val hiddenValues = Array(N) { hidden(input[it]) }
            val probabilities = softmax(DoubleArray(N) { output(hiddenValues[it]) })
            val secondBefore = second.copyOf()
            val gradSecond = DoubleArray(hidden)
            val gradFirst = Array(hidden) { DoubleArray(features) }
            val gradBias = DoubleArray(hidden)
            for (candidate in 0 until N) {
                val delta = probabilities[candidate] - if (candidate == target) 1.0 else 0.0
                for (node in 0 until hidden) {
                    gradSecond[node] += delta * hiddenValues[candidate][node]
                    val hiddenDelta = delta * secondBefore[node] *
                        (1.0 - hiddenValues[candidate][node] * hiddenValues[candidate][node])
                    gradBias[node] += hiddenDelta
                    for (feature in 0 until features) gradFirst[node][feature] += hiddenDelta * input[candidate][feature]
                }
            }
            for (node in 0 until hidden) {
                second[node] -= rate * (gradSecond[node] + 0.002 * second[node])
                firstBias[node] -= rate * gradBias[node]
                for (feature in 0 until features) {
                    first[node][feature] -= rate *
                        (gradFirst[node][feature] + 0.002 * first[node][feature]).coerceIn(-4.0, 4.0)
                }
            }
        }

        private fun hidden(input: DoubleArray) = DoubleArray(hidden) { node ->
            var value = firstBias[node]
            for (feature in 0 until features) value += first[node][feature] * input[feature]
            tanh(value)
        }

        private fun output(input: DoubleArray): Double {
            var value = 0.0
            for (node in 0 until hidden) value += second[node] * input[node]
            return value
        }

        private fun softmax(scores: DoubleArray): DoubleArray {
            val maximum = scores.maxOrNull() ?: 0.0
            val values = DoubleArray(scores.size) { exp(scores[it] - maximum) }
            val total = values.sum().coerceAtLeast(EPSILON)
            return DoubleArray(scores.size) { values[it] / total }
        }
    }

    private object FeatureBuilder {
        fun matrix(history: List<Draw>, end: Int): Array<Array<DoubleArray>> =
            Array(N) { position -> Array(N) { candidate -> feature(history, end, position, candidate + 1) } }

        private fun feature(history: List<Draw>, end: Int, position: Int, candidate: Int): DoubleArray {
            val last = history[end - 1]
            val previousPosition = last.numbers.indexOf(candidate).coerceAtLeast(0)
            return doubleArrayOf(
                1.0,
                (frequency(history, end, 12, position, candidate) * 10 - 1).coerceIn(-1.5, 2.5),
                (frequency(history, end, 36, position, candidate) * 10 - 1).coerceIn(-1.5, 2.5),
                (frequency(history, end, 120, position, candidate) * 10 - 1).coerceIn(-1.5, 2.5),
                (transition(history, end, position, candidate) * 10 - 1).coerceIn(-1.5, 2.5),
                (gap(history, end, position, candidate) / 18.0).coerceIn(0.0, 2.0) - 0.55,
                0.5 - min(1.0, abs(previousPosition - position) / 5.0),
                (if (last.numbers[position] == candidate) 1.0 else 0.0) - 0.1,
            )
        }

        private fun frequency(
            history: List<Draw>, end: Int, window: Int, position: Int, candidate: Int,
        ): Double {
            val start = max(0, end - window)
            var hits = 0
            for (index in start until end) if (history[index].numbers[position] == candidate) hits++
            return hits.toDouble() / max(1, end - start)
        }

        private fun transition(history: List<Draw>, end: Int, position: Int, candidate: Int): Double {
            if (end < 2) return 0.1
            val previous = history[end - 1].numbers[position]
            var matches = 0
            var hits = 0
            for (index in max(1, end - 120) until end) {
                if (history[index - 1].numbers[position] == previous) {
                    matches++
                    if (history[index].numbers[position] == candidate) hits++
                }
            }
            return (hits + 0.8) / (matches + 8.0)
        }

        private fun gap(history: List<Draw>, end: Int, position: Int, candidate: Int): Int {
            val start = max(0, end - 60)
            for (index in end - 1 downTo start) {
                if (history[index].numbers[position] == candidate) return end - 1 - index
            }
            return end - start
        }
    }
}
