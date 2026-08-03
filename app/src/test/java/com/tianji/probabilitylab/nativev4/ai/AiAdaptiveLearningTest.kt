package com.tianji.probabilitylab.nativev4.ai

import com.tianji.probabilitylab.nativev4.model.Draw
import com.tianji.probabilitylab.nativev4.model.LotteryType
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import kotlin.math.abs

class AiAdaptiveLearningTest {
    @Test
    fun independentSignalsProduceNormalizedScores() {
        val snapshot = AiAdaptiveSignalEngine.compute(history(120), 0)
        assertEquals(6, snapshot.factorProbabilities.size)
        assertTrue(snapshot.factorProbabilities.all { factor -> abs(factor.sum() - 1.0) < 1e-9 })
        assertEquals(10, snapshot.adaptiveScores.size)
        assertTrue(abs(snapshot.adaptiveScores.sum() - 1.0) < 1e-9)
        assertTrue(abs(snapshot.effectiveWeights.sum() - 1.0) < 1e-9)
    }

    @Test
    fun resolvedActualNumberChangesExpertWeightsWithoutLockingForever() {
        val factors = listOf(
            listOf(0.7) + List(9) { 0.3 / 9.0 },
            List(10) { 0.1 },
            List(10) { 0.1 },
            List(10) { 0.1 },
            List(10) { 0.1 },
            List(10) { 0.1 },
        )
        val next = AiAdaptiveSignalEngine.updatedWeights(
            AiLearningProfile.DEFAULT_WEIGHTS,
            factors,
            actualNumber = 1,
            settledBefore = 500,
        )
        assertTrue(next.first() > AiLearningProfile.DEFAULT_WEIGHTS.first())
        assertTrue(next.all { it >= 0.025 })
        assertTrue(abs(next.sum() - 1.0) < 1e-9)
    }

    @Test
    fun staleLongTermPriorIsAlmostDiscardedAfterManyUnseenPeriods() {
        val profile = AiLearningProfile(
            settled = 200,
            top6Hits = 130,
            weights = listOf(0.75, 0.05, 0.05, 0.05, 0.05, 0.05),
            lastLearnedPeriod = "0040",
        )
        val snapshot = AiAdaptiveSignalEngine.compute(history(160), 0, profile)
        assertTrue(snapshot.periodsSinceLearning >= 100)
        assertTrue(snapshot.longTermBlend < 0.01)
        assertTrue(snapshot.effectiveWeights.first() < 0.50)
    }

    @Test
    fun evenFreshLongTermPriorCannotDominateCurrentHistory() {
        val profile = AiLearningProfile(
            settled = 200,
            top6Hits = 130,
            weights = listOf(0.75, 0.05, 0.05, 0.05, 0.05, 0.05),
            lastLearnedPeriod = "0160",
        )
        val snapshot = AiAdaptiveSignalEngine.compute(history(160, recentNumber = 7), 0, profile)
        assertTrue(snapshot.longTermBlend <= 0.45)
        assertTrue(snapshot.effectiveWeights.first() < profile.weights.first())
        assertTrue(snapshot.regimeLabel.isNotBlank())
    }

    @Test
    fun officialLearningStrategySeparatesAnalysisModes() {
        val fast = AiConfig(
            model = "same-model",
            analysisMode = AiAnalysisMode.FAST,
            reasoningMode = AiReasoningMode.LOW,
        )
        val deep = fast.copy(
            analysisMode = AiAnalysisMode.DEEP,
            reasoningMode = AiReasoningMode.HIGH,
        )
        assertTrue(AiLearningStrategy.official(fast) != AiLearningStrategy.official(deep))
    }

    @Test
    fun judgementModeDefaultsToBlindIndependentAnalysis() {
        assertEquals(AiJudgementMode.INDEPENDENT, AiJudgementMode.fromId(null))
        assertEquals(AiJudgementMode.CONTRARIAN, AiJudgementMode.fromId("CONTRARIAN"))
    }

    private fun history(count: Int, recentNumber: Int? = null): List<Draw> =
        (1..count).map { index ->
            val first = if (recentNumber != null && index > count - 18 && index % 4 != 0) {
                recentNumber
            } else {
                (index % 10) + 1
            }
            Draw(
                lottery = LotteryType.AZXY10,
                period = index.toString().padStart(4, '0'),
                numbers = listOf(first) + (1..10).filterNot { it == first },
                drawTime = "",
                source = "test",
            )
        }
}
