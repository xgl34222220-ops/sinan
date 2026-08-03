package com.tianji.probabilitylab.nativev4.ai

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class AiConversationTimelineTest {
    @Test
    fun classifiesVisibleAnalysisPhases() {
        assertEquals(
            AiConversationStage.REASONING,
            AiConversationTimeline.classify("模型正在推理 · 已收到 1200 个推理字符"),
        )
        assertEquals(
            AiConversationStage.CONTINUATION,
            AiConversationTimeline.classify("首次推理已完成，正在沿用同一对话补全最终 JSON"),
        )
        assertEquals(
            AiConversationStage.RETRY,
            AiConversationTimeline.classify("接口拒绝参数，正在切换模型默认思考协议"),
        )
        assertEquals(
            AiConversationStage.ERROR,
            AiConversationTimeline.classify("网络连接中断，已保留已接收内容"),
        )
    }

    @Test
    fun replacesRapidReasoningUpdatesInsteadOfGrowingForever() {
        val first = AiConversationTimeline.event(
            AiConversationStage.REASONING,
            "已收到 100 个推理字符",
            1_000L,
            1L,
        )
        val second = AiConversationTimeline.event(
            AiConversationStage.REASONING,
            "已收到 500 个推理字符",
            2_000L,
            2L,
        )
        val merged = AiConversationTimeline.merge(listOf(first), second)

        assertEquals(1, merged.size)
        assertTrue(merged.single().message.contains("500"))
    }

    @Test
    fun compactsAlternatingReasoningAndOutputUpdates() {
        var events = emptyList<AiConversationEvent>()
        repeat(8) { index ->
            events = AiConversationTimeline.merge(
                events,
                AiConversationTimeline.event(
                    AiConversationStage.REASONING,
                    "推理-$index",
                    index.toLong(),
                    index.toLong(),
                ),
            )
            events = AiConversationTimeline.merge(
                events,
                AiConversationTimeline.event(
                    AiConversationStage.OUTPUT,
                    "结果-$index",
                    index.toLong(),
                    index.toLong(),
                ),
            )
        }
        assertEquals(2, events.size)
        assertEquals("推理-7", events.first { it.stage == AiConversationStage.REASONING }.message)
        assertEquals("结果-7", events.first { it.stage == AiConversationStage.OUTPUT }.message)
    }

    @Test
    fun preservesPhaseChangesAndCapsHistory() {
        var events = emptyList<AiConversationEvent>()
        repeat(40) { index ->
            events = AiConversationTimeline.merge(
                events,
                AiConversationTimeline.event(
                    if (index % 2 == 0) AiConversationStage.REQUEST else AiConversationStage.VALIDATING,
                    "event-$index",
                    index.toLong(),
                    index.toLong(),
                ),
            )
        }
        assertEquals(24, events.size)
        assertEquals("event-39", events.last().message)
    }
}
