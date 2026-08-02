package com.tianji.probabilitylab.nativev4.domain

import com.tianji.probabilitylab.nativev4.model.Draw
import com.tianji.probabilitylab.nativev4.model.LotteryType
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotEquals
import org.junit.Test

class HistoryFingerprintTest {
    private val draw = Draw(
        lottery = LotteryType.AZXY10,
        period = "100",
        numbers = (1..10).toList(),
        drawTime = "2026-08-03 00:00:00",
    )

    @Test
    fun sameHistoryHasStableFingerprint() {
        assertEquals(
            HistoryFingerprint.of(listOf(draw)),
            HistoryFingerprint.of(listOf(draw)),
        )
    }

    @Test
    fun correctedHistoryInvalidatesCache() {
        assertNotEquals(
            HistoryFingerprint.of(listOf(draw)),
            HistoryFingerprint.of(listOf(draw.copy(numbers = (2..10).toList() + 1))),
        )
    }
}
