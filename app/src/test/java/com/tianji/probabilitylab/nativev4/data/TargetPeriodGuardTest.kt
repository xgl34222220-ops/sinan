package com.tianji.probabilitylab.nativev4.data

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class TargetPeriodGuardTest {
    @Test
    fun targetRemainsOpenBeforeSafetyWindow() {
        assertTrue(
            TargetPeriodGuard.evaluate(
                expectedTargetPeriod = "101",
                latestPeriod = "100",
                nextPeriod = "101",
                serverTimeEpochMs = 10_000L,
                nextDrawAtEpochMs = 20_000L,
            ).open,
        )
    }

    @Test
    fun alreadyDrawnTargetIsRejected() {
        assertFalse(
            TargetPeriodGuard.evaluate(
                expectedTargetPeriod = "101",
                latestPeriod = "101",
                nextPeriod = "102",
                serverTimeEpochMs = 20_000L,
                nextDrawAtEpochMs = 30_000L,
            ).open,
        )
    }

    @Test
    fun changedNextPeriodIsRejected() {
        assertFalse(
            TargetPeriodGuard.evaluate(
                expectedTargetPeriod = "101",
                latestPeriod = "100",
                nextPeriod = "102",
                serverTimeEpochMs = 10_000L,
                nextDrawAtEpochMs = 20_000L,
            ).open,
        )
    }

    @Test
    fun safetyWindowRejectsLateResult() {
        assertFalse(
            TargetPeriodGuard.evaluate(
                expectedTargetPeriod = "101",
                latestPeriod = "100",
                nextPeriod = "101",
                serverTimeEpochMs = 16_000L,
                nextDrawAtEpochMs = 20_000L,
                safetyWindowMs = 5_000L,
            ).open,
        )
    }
}
