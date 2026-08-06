package com.tianji.probabilitylab.nativev4.ai

import com.tianji.probabilitylab.nativev4.model.Draw
import com.tianji.probabilitylab.nativev4.model.LotteryType
import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Test
import kotlin.math.abs

class ContinualRemoteAiAnalyzerTest {
    @Test
    fun planValidatesAllTenPositionsWithoutProbabilityLeakage() {
        val plan = AiContinualForecastEngine.buildPlan(
            historyInput = history(120),
            profiles = List(10) { AiLearningProfile() },
        )

        assertEquals(10, plan.positions.size)
        assertTrue(plan.positions.all { it.validationSamples == 48 })
        assertTrue(plan.positions.all { abs(it.currentProbabilities.sum() - 1.0) < 1e-9 })
        assertTrue(plan.best.position in 0..9)
    }

    @Test
    fun weakRandomPositionIsRejectedWhenValidatedPositionIsClearlyBetter() {
        val plan = manualPlan(
            bestPosition = 4,
            selectedPosition = 0,
            selectedScore = 0.30,
        )

        val error = assertThrows(IllegalArgumentException::class.java) {
            AiContinualForecastEngine.calibrate(forecast(position = 0), plan)
        }
        assertTrue(error.message.orEmpty().contains("拒绝冻结随机弱名次"))
    }

    @Test
    fun acceptedForecastKeepsAiIndependentAndAddsSettledLearningCalibration() {
        val plan = manualPlan(
            bestPosition = 4,
            selectedPosition = 4,
            selectedScore = 1.55,
        )
        val result = AiContinualForecastEngine.calibrate(forecast(position = 4), plan)

        assertEquals(4, result.position)
        assertEquals(6, result.top6.size)
        assertEquals(7, result.top7.size)
        assertTrue(abs(result.probabilities.sum() - 1.0) < 1e-9)
        assertTrue(result.analysis.contains("持续学习校准"))
        assertTrue(result.riskNote.contains("真实开奖结算"))
        assertTrue(result.executionNote.contains("十名次滚动前向门槛"))
    }

    private fun manualPlan(
        bestPosition: Int,
        selectedPosition: Int,
        selectedScore: Double,
    ): AiContinualForecastPlan {
        val positions = (0 until 10).map { position ->
            val isBest = position == bestPosition
            val isSelected = position == selectedPosition
            AiPositionForwardEvidence(
                position = position,
                validationSamples = 48,
                top6Hits = if (isBest) 34 else 24,
                top6HitRate = if (isBest) 0.67 else 0.56,
                averageLogLoss = if (isBest) 2.20 else 2.48,
                maxMissStreak = if (isBest) 3 else 11,
                boundaryMargin = if (isBest) 0.012 else 0.002,
                validationScore = when {
                    isBest -> 1.60
                    isSelected -> selectedScore
                    else -> 0.45 + position * 0.01
                },
                gatePassed = isBest,
                currentProbabilities = normalized((10 downTo 1).map { it.toDouble() }),
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
            analysis = "远程AI独立原始历史分析",
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
