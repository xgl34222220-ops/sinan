package com.tianji.probabilitylab.nativev4.ai

import com.tianji.probabilitylab.nativev4.model.Draw
import com.tianji.probabilitylab.nativev4.model.LotteryType
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class AiAdaptiveLearningTest {
    @Test
    fun independentSignalsProduceNormalizedScores() {
        val history = (1..120).map { index ->
            val first = if (index > 95 && index % 3 != 0) 7 else (index % 10) + 1
            Draw(
                lottery = LotteryType.AZXY10,
                period = index.toString().padStart(4, '0'),
                numbers = listOf(first) + (1..10).filterNot { it == first },
                drawTime = "",
                source = "test",
            )
        }
        val snapshot = AiAdaptiveSignalEngine.compute(history, 0)
        assertEquals(6, snapshot.factorProbabilities.size)
        assertTrue(snapshot.factorProbabilities.all { factor -> kotlin.math.abs(factor.sum() - 1.0) < 1e-9 })
        assertEquals(10, snapshot.adaptiveScores.size)
        assertTrue(kotlin.math.abs(snapshot.adaptiveScores.sum() - 1.0) < 1e-9)
    }

    @Test
    fun resolvedActualNumberChangesExpertWeights() {
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
            settledBefore = 0,
        )
        assertTrue(next.first() > AiLearningProfile.DEFAULT_WEIGHTS.first())
        assertTrue(kotlin.math.abs(next.sum() - 1.0) < 1e-9)
    }

    @Test
    fun judgementModeDefaultsToBlindIndependentAnalysis() {
        assertEquals(AiJudgementMode.INDEPENDENT, AiJudgementMode.fromId(null))
        assertEquals(AiJudgementMode.CONTRARIAN, AiJudgementMode.fromId("CONTRARIAN"))
    }
}
