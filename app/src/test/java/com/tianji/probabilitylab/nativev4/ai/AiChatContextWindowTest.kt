package com.tianji.probabilitylab.nativev4.ai

import org.junit.Assert.assertTrue
import org.junit.Test

class AiChatContextWindowTest {
    @Test
    fun longConversationTriggersRolloverWithoutDroppingStoredMessages() {
        val messages = (0 until 80).map { index ->
            AiChatMessage(
                role = if (index % 2 == 0) AiChatRole.USER else AiChatRole.ASSISTANT,
                content = "第${index}轮对话：" + "分析内容".repeat(120),
            )
        }
        val plan = AiChatProtocol.planContext(messages, "")
        assertTrue(plan.shouldRollover)
        assertTrue(plan.messages.isNotEmpty())
        assertTrue(plan.messages.size < messages.size)
    }

    @Test
    fun memorySummaryKeepsExplicitStrategyFeedbackAndOutcome() {
        val messages = listOf(
            AiChatMessage(role = AiChatRole.USER, content = "上一期没中，降低最近20期热号权重"),
            AiChatMessage(role = AiChatRole.ASSISTANT, content = "下一期将提高中长窗口稳定性权重"),
        )
        val candidate = AiChatCandidateRecord(
            messageId = "a",
            targetPeriod = "101",
            prediction = AiChatPrediction(0, listOf(1,2,3,4,5,6), listOf(1,2,3,4,5,6,7), List(10) { 0.1 }),
            actualNumber = 9,
            resolvedPeriod = "101",
        )
        val summary = AiChatProtocol.buildMemorySummary("", messages, listOf(candidate))
        assertTrue(summary.contains("降低最近20期热号权重"))
        assertTrue(summary.contains("6码未中"))
    }
}