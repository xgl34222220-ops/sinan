package com.tianji.probabilitylab.nativev4.ai

import com.tianji.probabilitylab.nativev4.model.Draw
import com.tianji.probabilitylab.nativev4.model.LotteryType
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import kotlin.math.abs

class ContinualRemoteAiAnalyzerTest {
    @Test
    fun planValidatesAllTenPositionsAgainstFixedTarget() {
        val plan = AiContinualForecastEngine.buildPlan(
            historyInput = history(120),
            profiles = List(10) { AiLearningProfile() },
        )

        assertEquals(10, plan.positions.size)
        assertTrue(plan.positions.all { it.validationSamples == 60 })
        assertTrue(plan.positions.all { abs(it.currentProbabilities.sum() - 1.0) < 1e-9 })
        assertTrue(plan.best.position in 0..9)
        assertEquals(listOf(2, 3, 5, 7, 8, 10), AiContinualForecastEngine.TARGET_NUMBERS)
    }

    @Test
    fun weakAiPreferenceCannotOverrideStrongForwardEvidence() {
        val plan = manualPlan(
            bestPosition = 4,
            remotePosition = 0,
            remoteScore = 0.30,
        )

        val result = AiContinualForecastEngine.calibrate(forecast(position = 0), plan)
        assertEquals(4, result.position)
        assertEquals(AiContinualForecastEngine.TARGET_NUMBERS, result.top6)
        assertTrue(result.analysis.contains("前向验证68% + AI评分32%"))
    }

    @Test
    fun promptEvidenceContainsOwnLearningButNeverNativeAnswer() {
        val plan = manualPlan(
            bestPosition = 4,
            remotePosition = 0,
            remoteScore = 0.30,
        )
        val json = AiContinualForecastEngine.promptEvidence(plan)

        assertEquals("tianji-ai-self-learning-v1", json.getString("schema"))
        assertEquals("235780", json.getString("target_pool"))
        assertEquals(0.60, json.getDouble("random_baseline"), 1e-9)
        assertEquals(10, json.getJSONArray("positions").length())
        val first = json.getJSONArray("positions").getJSONObject(0)
        assertTrue(first.has("validation_samples"))
        assertTrue(first.has("average_binary_log_loss"))
        assertTrue(first.has("own_long_term_factor_weights"))
        assertFalse(json.has("native_position"))
        assertFalse(json.has("native_top6"))
        assertFalse(json.has("native_top7"))
        assertFalse(json.has("native_probabilities"))
        assertFalse(first.has("native_position"))
        assertFalse(first.has("native_top6"))
    }

    @Test
    fun acceptedForecastUsesFixed235780PoolAndBinaryLearningSummary() {
        val plan = manualPlan(
            bestPosition = 4,
            remotePosition = 4,
            remoteScore = 0.70,
        )
        val result = AiContinualForecastEngine.calibrate(forecast(position = 4), plan)

        assertEquals(4, result.position)
        assertEquals(listOf(2, 3, 5, 7, 8, 10), result.top6)
        assertEquals(7, result.top7.size)
        assertTrue(abs(result.probabilities.sum() - 1.0) < 1e-9)
        assertTrue(result.analysis.contains("固定目标预测"))
        assertTrue(result.analysis.contains("随机基准60%"))
        assertTrue(result.riskNote.contains("随机命中基准就是60%"))
        assertTrue(result.executionNote.contains("AI自学习证据已注入"))
        assertTrue(result.executionNote.contains("与本机答案隔离"))
        assertTrue(result.executionNote.contains("固定六码235780"))
    }

    private fun manualPlan(
        bestPosition: Int,
        remotePosition: Int,
        remoteScore: Double,
    ): AiContinualForecastPlan {
        val positions = (0 until 10).map { position ->
            val isBest = position == bestPosition
            val isRemote = position == remotePosition
            val targetProbability = when {
                isBest -> 0.69
                isRemote -> 0.57
                else -> 0.58 + position * 0.002
            }
            AiPositionForwardEvidence(
                position = position,
                validationSamples = 60,
                targetHits = if (isBest) 41 else 33,
                targetHitRate = if (isBest) 0.67 else 0.56,
                averageBinaryLogLoss = if (isBest) 0.64 else 0.72,
                maxMissStreak = if (isBest) 3 else 9,
                currentMissStreak = if (isBest) 0 else 2,
                targetProbability = targetProbability,
                validationScore = when {
                    isBest -> 0.78
                    isRemote -> remoteScore
                    else -> 0.50 + position * 0.01
                },
                gatePassed = isBest,
                currentProbabilities = fixedDistribution(targetProbability),
                learningProfile = AiLearningProfile(
                    settled = if (isBest) 80 else 12,
                    top6Hits = if (isBest) 54 else 6,
                    recentTop6 = listOf(1, 1, 0, 1, 1, 1),
                ),
            )
        }
        return AiContinualForecastPlan(historySize = 120, positions = positions)
    }

    private fun forecast(position: Int): AiForecast {
        val probabilities = normalized((10 downTo 1).map { it.toDouble() })
        val ranking = probabilities.indices.sortedByDescending { probabilities[it] }.map { it + 1 }
        return AiForecast(
            profileId = "profile",
            profileName = "测试模型",
            targetPeriod = "0121",
            position = position,
            top6 = ranking.take(6),
            top7 = ranking.take(7),
            probabilities = probabilities,
            analysis = "远程AI固定235780位置评分",
            riskNote = "随机开奖无法保证准确率",
            selfRating = 0.2,
            model = "DeepSeek · test",
            analysisMode = AiAnalysisMode.DEEP,
            reasoningMode = AiReasoningMode.HIGH,
            reasoningProtocol = AiReasoningProtocol.DEEPSEEK,
            reasoningState = AiReasoningState.VERIFIED,
            reasoningTokens = 100,
            inputTokens = 200,
            outputTokens = 100,
            estimatedCost = null,
            executionNote = "严格独立原始历史输入",
            createdAtEpochMs = 1L,
            latencyMs = 1_000L,
            responseId = "response",
        )
    }

    private fun fixedDistribution(targetProbability: Double): List<Double> {
        val target = AiContinualForecastEngine.TARGET_NUMBERS.toSet()
        return (1..10).map { number ->
            if (number in target) targetProbability / 6.0 else (1.0 - targetProbability) / 4.0
        }
    }

    private fun normalized(values: List<Double>): List<Double> {
        val total = values.sum()
        return values.map { it / total }
    }

    private fun history(count: Int): List<Draw> =
        (1..count).map { index ->
            val first = (index % 10) + 1
            Draw(
                lottery = LotteryType.AZXY10,
                period = index.toString().padStart(4, '0'),
                numbers = listOf(first) + (1..10).filterNot { it == first },
                drawTime = "",
                source = "test",
            )
        }
}
