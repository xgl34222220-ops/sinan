package com.tianji.probabilitylab.nativev4.ai

import com.tianji.probabilitylab.nativev4.model.Draw
import com.tianji.probabilitylab.nativev4.model.LotteryType
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class AiPromptCompactorTest {
    private fun draw(period: String, shift: Int = 0): Draw {
        val numbers = (1..10).map { ((it - 1 + shift) % 10) + 1 }
        return Draw(LotteryType.AZXY10, period, numbers)
    }

    @Test
    fun compactHistoryKeepsRequestedWindow() {
        val history = (1..120).map { draw(it.toString(), it % 10) }
        val compact = AiPromptCompactor.compactDraws(history, 120)

        assertEquals(120, compact.length())
        assertEquals("1", compact.getJSONArray(0).getString(0))
        assertEquals("120", compact.getJSONArray(119).getString(0))
        assertEquals(10, compact.getJSONArray(119).getString(1).split(',').size)
    }

    @Test
    fun statisticsCoverAllPositionsAndNumbers() {
        val history = (1..80).map { draw(it.toString(), it % 10) }
        val stats = AiPromptCompactor.verifiedPositionStatistics(history)

        assertEquals(10, stats.length())
        repeat(10) { index ->
            val item = stats.getJSONObject(index)
            assertEquals(index + 1, item.getInt("position"))
            assertEquals(10, item.getJSONArray("recent20_counts_1_to_10").length())
            assertEquals(10, item.getJSONArray("recent60_counts_1_to_10").length())
            assertEquals(10, item.getJSONArray("current_omissions_1_to_10").length())
            assertEquals(10, item.getJSONArray("next_after_current_counts_1_to_10").length())
        }
    }

    @Test
    fun reasoningRuleRequiresRealThinkingAndPromptCompletion() {
        assertTrue(AiPromptCompactor.REASONING_RULE.contains("真实推理"))
        assertTrue(AiPromptCompactor.REASONING_RULE.contains("立即输出JSON"))
    }
}
