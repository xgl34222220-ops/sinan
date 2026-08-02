package com.tianji.probabilitylab.nativev4.ai

import org.junit.Assert.assertEquals
import org.junit.Test

class AiProbabilityVectorBoundaryTest {
    @Test(expected = IllegalArgumentException::class)
    fun `flat scores remain rejected`() {
        AiProbabilityVector.requireForecastable(List(10) { 1.0 })
    }

    @Test(expected = IllegalArgumentException::class)
    fun `sixth and seventh exact tie is rejected instead of arbitrarily selecting one`() {
        AiProbabilityVector.requireForecastable(
            listOf(0.20, 0.18, 0.16, 0.14, 0.10, 0.05, 0.05, 0.04, 0.04, 0.04),
        )
    }

    @Test
    fun `high precision raw scores decide the sixth seventh boundary`() {
        val probabilities = AiProbabilityVector.requireForecastable(
            listOf(0.20, 0.18, 0.16, 0.14, 0.10, 0.050001, 0.05, 0.04, 0.039999, 0.04),
        )

        assertEquals(listOf(1, 2, 3, 4, 5, 6), AiProbabilityVector.ranking(probabilities).take(6))
        assertEquals(1.0, probabilities.sum(), 1e-12)
    }
}
