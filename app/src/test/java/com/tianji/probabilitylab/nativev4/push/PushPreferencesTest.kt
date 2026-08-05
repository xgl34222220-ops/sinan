package com.tianji.probabilitylab.nativev4.push

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class PushPreferencesTest {
    private val baseAlert = PushAlert(
        id = 1,
        eventKey = "event",
        lottery = "xyft",
        lotteryName = "幸运飞艇",
        source = "ai",
        sourceName = "天机云端 AI",
        model = "model",
        streak = 3,
        threshold = 3,
        latestTargetPeriod = "100",
        recentPeriods = listOf("100", "99", "98"),
        title = "三期不中预警",
        body = "",
        createdAtEpochMs = 1,
        isRead = false,
    )

    @Test
    fun sourceAndLotteryPreferencesAreIndependent() {
        assertTrue(PushPreferences().accepts(baseAlert))
        assertFalse(PushPreferences(xyftEnabled = false).accepts(baseAlert))
        assertFalse(PushPreferences(aiEnabled = false).accepts(baseAlert))
        assertTrue(
            PushPreferences(nativeEnabled = false).accepts(baseAlert),
        )
    }

    @Test
    fun escalationCanBeDisabledWithoutBlockingFirstWarning() {
        val prefs = PushPreferences(escalationEnabled = false)
        assertTrue(prefs.accepts(baseAlert))
        assertFalse(prefs.accepts(baseAlert.copy(streak = 4)))
    }
}
