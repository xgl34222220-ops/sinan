package com.tianji.probabilitylab.nativev4.ai

import org.junit.Assert.assertEquals
import org.junit.Test

class AiTargetPeriodCallSiteRegressionTest {
    @Test
    fun explicitPredictionTextIsReconciledEvenWithoutParsedForecastPayload() {
        val visibleText = "21348012 期第七名预测\n\n六码候选\n4, 9, 2, 10, 7, 1"
        val corrected = AiTargetPeriodGuard.reconcilePredictionText(
            text = visibleText,
            expectedTargetPeriod = "21348025",
            isPrediction = true,
        )

        assertEquals(
            "21348025 期第七名预测\n\n六码候选\n4, 9, 2, 10, 7, 1",
            corrected,
        )
    }
}
