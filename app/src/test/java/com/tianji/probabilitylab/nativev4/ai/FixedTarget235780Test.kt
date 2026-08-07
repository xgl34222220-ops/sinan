package com.tianji.probabilitylab.nativev4.ai

import com.tianji.probabilitylab.nativev4.model.Draw
import com.tianji.probabilitylab.nativev4.model.LotteryType
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class FixedTarget235780Test {
    @Test
    fun targetPoolUsesZeroAsInternalTen() {
        assertEquals(listOf(2, 3, 5, 7, 8, 10), AiContinualForecastEngine.TARGET_NUMBERS)
        assertEquals("235780", AiContinualForecastEngine.TARGET_LABEL)
        assertEquals(0.60, AiContinualForecastEngine.RANDOM_TARGET_RATE, 1e-12)
    }

    @Test
    fun fixedTargetLearnerPrefersPositionWithPersistentTargetEvidence() {
        val target = AiContinualForecastEngine.TARGET_NUMBERS
        val history = (0 until 120).map { index ->
            val first = target[index % target.size]
            val remaining = (1..10).filter { it != first }
            val shift = index % remaining.size
            val rotated = remaining.drop(shift) + remaining.take(shift)
            Draw(
                lottery = LotteryType.XYFT,
                period = (100000 + index).toString(),
                numbers = listOf(first) + rotated,
            )
        }
        val plan = AiContinualForecastEngine.buildPlan(
            historyInput = history,
            profiles = List(10) { AiLearningProfile() },
        )
        assertEquals(0, plan.best.position)
        assertTrue(plan.best.targetProbability > AiContinualForecastEngine.RANDOM_TARGET_RATE)
        assertEquals(6, AiContinualForecastEngine.TARGET_NUMBERS.size)
    }
}
