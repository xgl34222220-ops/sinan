package com.tianji.probabilitylab.nativev4.ai

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class AiTargetPeriodGuardTest {
    @Test
    fun correctsWrongPredictionHeadingWithoutChangingHistoryEvidence() {
        val input = """
            21348012 期综合预测

            名次：第五名
            历史截至21348019期，共120期样本。
        """.trimIndent()

        val output = AiTargetPeriodGuard.reconcilePredictionText(
            text = input,
            expectedTargetPeriod = "21348020",
            isPrediction = true,
        )

        assertTrue(output.startsWith("21348020 期综合预测"))
        assertTrue(output.contains("历史截至21348019期"))
    }

    @Test
    fun correctsTargetLabelAndMarkdownHeading() {
        val input = """
            ## 21348012期第五名预测
            目标期：21348012期
        """.trimIndent()

        assertEquals(
            """
                ## 21348020期第五名预测
                目标期：21348020期
            """.trimIndent(),
            AiTargetPeriodGuard.reconcilePredictionText(
                text = input,
                expectedTargetPeriod = "21348020",
                isPrediction = true,
            ),
        )
    }

    @Test
    fun marksOldConversationPeriodAsHistory() {
        val message = AiChatMessage(
            role = AiChatRole.ASSISTANT,
            content = "21348012期综合预测",
            targetPeriod = "21348012",
        )
        val result = AiTargetPeriodGuard.contextualizePreviousMessage(message, "21348020")

        assertTrue(result.contains("旧目标期：21348012期"))
        assertTrue(result.contains("当前目标期不是该期"))
    }

    @Test
    fun leavesFreeChatAndHistoricalEvidenceUntouched() {
        val text = "你好，历史截至21348019期。"
        assertEquals(
            text,
            AiTargetPeriodGuard.reconcilePredictionText(
                text = text,
                expectedTargetPeriod = "21348020",
                isPrediction = false,
            ),
        )
    }
}
