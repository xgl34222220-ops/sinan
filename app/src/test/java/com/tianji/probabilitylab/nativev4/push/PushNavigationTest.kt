package com.tianji.probabilitylab.nativev4.push

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class PushNavigationTest {
    @Test
    fun predictionTargetCanBeOpenedAndConsumed() {
        PushAlertNavigation.openPrediction("azxy10", "21348220")
        assertEquals("azxy10", PushAlertNavigation.pendingPrediction.value?.lottery)
        assertEquals("21348220", PushAlertNavigation.pendingPrediction.value?.targetPeriod)
        PushAlertNavigation.consumePrediction()
        assertNull(PushAlertNavigation.pendingPrediction.value)
    }
}
