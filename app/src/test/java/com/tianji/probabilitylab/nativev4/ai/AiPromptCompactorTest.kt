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
        val compact = AiPromptCompactor.compactRows(history, 120)

        assertEquals(120, compact.size)
        assertEquals("1", compact.first().period)
        assertEquals("120", compact.last().period)
        assertEquals(10, compact.last().numbers.split(',').size)
    }

    @Test
    fun statisticsCoverAllPositionsAndNumbers() {
        val history = (1..80).map { draw(it.toString(), it % 10) }
        val stats = AiPromptCompactor.positionFacts(history)

        assertEquals(10, stats.size)
        stats.forEachIndexed { index, item ->
            assertEquals(index + 1, item.position)
            assertEquals(10, item.recent20Counts.size)
            assertEquals(10, item.recent60Counts.size)
            assertEquals(10, item.omissions.size)
            assertEquals(10, item.transitionsAfterLatest.size)
        }
    }

    @Test
    fun reasoningRuleRequiresRealThinkingAndPromptCompletion() {
        assertTrue(AiPromptCompactor.REASONING_RULE.contains("真实推理"))
        assertTrue(AiPromptCompactor.REASONING_RULE.contains("立即输出JSON"))
    }
}
