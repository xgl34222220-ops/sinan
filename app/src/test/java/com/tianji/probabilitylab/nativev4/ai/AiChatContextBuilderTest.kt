package com.tianji.probabilitylab.nativev4.ai

import com.tianji.probabilitylab.nativev4.model.Draw
import com.tianji.probabilitylab.nativev4.model.LotteryType
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class AiChatContextBuilderTest {
    @Test
    fun computesCountsOmissionAndSuccessorsForRequestedPosition() {
        val history = listOf(1, 2, 1, 3, 1).mapIndexed { index, first ->
            draw(period = "202608030${index + 1}", first = first)
        }

        val stats = AiChatContextBuilder.computePositionStatistics(history, position = 0)

        assertEquals(1, stats.currentNumber)
        assertEquals(3, stats.count120[0])
        assertEquals(1, stats.count120[1])
        assertEquals(1, stats.count120[2])
        assertEquals(0, stats.omission[0])
        assertEquals(3, stats.omission[1])
        assertEquals(1, stats.omission[2])
        assertEquals(1, stats.successorAfterCurrent[1])
        assertEquals(1, stats.successorAfterCurrent[2])
    }

    @Test
    fun analysisWindowNeverUsesMoreThanLatest120Draws() {
        val history = (1..150).map { index ->
            draw(
                period = index.toString().padStart(4, '0'),
                first = if (index <= 30) 10 else 1,
            )
        }

        val stats = AiChatContextBuilder.computePositionStatistics(history, position = 0)

        assertEquals(120, stats.count120.sum())
        assertEquals(120, stats.count120[0])
        assertEquals(0, stats.count120[9])
        assertTrue(stats.trendDelta.all { it >= 0.0 })
    }

    private fun draw(period: String, first: Int): Draw = Draw(
        lottery = LotteryType.AZXY10,
        period = period,
        numbers = listOf(first) + (1..10).filterNot { it == first },
        drawTime = "",
        source = "test",
    )
}
