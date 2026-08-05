package com.tianji.probabilitylab.nativev4.ai

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

class AiFreeChatTest {
    @Test
    fun onlyPredictionLikeRequestsAskForStructuredCandidates() {
        assertTrue(AiChatProtocol.wantsPrediction("分析第八名并给出六码候选"))
        assertTrue(AiChatProtocol.wantsPrediction("走势预判第一名"))
        assertTrue(AiChatProtocol.wantsPrediction("please forecast position 3"))
        assertFalse(AiChatProtocol.wantsPrediction("解释近60期大小连开是否稳定"))
    }

    @Test
    fun understandsNaturalCandidateCountRequests() {
        assertEquals(2, AiChatProtocol.requestedCandidateCount("幸运飞艇下一期最有可能开出两个号码"))
        assertEquals(2, AiChatProtocol.requestedCandidateCount("第2名给我2个候选"))
        assertEquals(2, AiChatProtocol.requestedCandidateCount("只要两码，不要备用号码"))
        assertEquals(3, AiChatProtocol.requestedCandidateCount("告诉我最可能的三个号码"))
        assertEquals(6, AiChatProtocol.requestedCandidateCount("给我六码"))
        assertEquals(7, AiChatProtocol.requestedCandidateCount("列出七码候选"))
        assertEquals(null, AiChatProtocol.requestedCandidateCount("分析第一名近期走势"))
    }

    @Test
    fun extractsPredictionWithoutChangingAiRanking() {
        val reply = """
            简要结论如下。
            <tianji_forecast>{"position":8,"scores":[0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,1.0]}</tianji_forecast>
        """.trimIndent()

        AiChatProtocol.wantsPrediction("分析第八名并给出六码候选")
        val prediction = AiChatProtocol.parsePrediction(reply)
        assertNotNull(prediction)
        assertEquals(7, prediction!!.position)
        assertEquals(listOf(10, 9, 8, 7, 6, 5), prediction.top6)
        assertEquals(10, prediction.probabilities.size)
        val visible = AiChatProtocol.visibleText(reply, hasPrediction = true)
        assertTrue(visible.contains("简要结论"))
        assertTrue(visible.startsWith("按你的要求，本期第8名优先6码：10、9、8、7、6、5。"))
        assertFalse(visible.contains("scores"))
    }

    @Test
    fun exactTwoNumberRequestProducesOnlyTwoVisibleCandidates() {
        val reply = """
            已完成历史分析。
            <tianji_forecast>{"position":1,"scores":[0.9,0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,1.0]}</tianji_forecast>
        """.trimIndent()

        assertTrue(AiChatProtocol.wantsPrediction("告诉我下一期最有可能开出的两个号码"))
        val prediction = AiChatProtocol.parsePrediction(reply)
        assertNotNull(prediction)
        assertEquals(listOf(10, 1), prediction!!.top6)
        assertEquals(7, prediction.top7.size)
        val visible = AiChatProtocol.visibleText(reply, hasPrediction = true)
        assertTrue(visible.startsWith("按你的要求，本期第1名优先2码：10、1。"))
        assertFalse(visible.startsWith("按你的要求，本期第1名优先6码"))
    }

    @Test
    fun requestsWithoutCountStillDefaultToSixCandidates() {
        val reply = """
            <tianji_forecast>{"position":3,"scores":[1,2,3,4,5,6,7,8,9,10]}</tianji_forecast>
        """.trimIndent()

        assertTrue(AiChatProtocol.wantsPrediction("预测下一期号码"))
        val prediction = AiChatProtocol.parsePrediction(reply)
        assertEquals(6, prediction!!.top6.size)
    }

    @Test
    fun streamingTextNeverLeaksForecastPayload() {
        val partial = "先给出分析依据。\n<tianji_forecast>{\"position\":1,\"scores\":[1,2"
        assertEquals("先给出分析依据。\n", AiChatProtocol.visibleStreamingText(partial))
    }

    @Test
    fun builtInPersonasAreCompleteAndLegacyIdsRemainResolvable() {
        assertEquals(3, AiChatPersona.entries.size)
        assertEquals(AiChatPersona.COMPREHENSIVE, AiChatPersona.fromId("history"))
        assertEquals(AiChatPersona.TREND, AiChatPersona.fromId("regime_state"))
        assertEquals(AiChatPersona.RISK_AUDIT, AiChatPersona.fromId("adaptive_learning"))
        assertEquals(AiChatPersona.COMPREHENSIVE, AiChatPersona.fromId("unknown"))
        AiChatPersona.entries.forEach { persona ->
            assertTrue(persona.displayName.isNotBlank())
            assertTrue(persona.instruction.isNotBlank())
            assertTrue(persona.quickPrompts.size >= 3)
        }
    }

    @Test
    fun conversationHistoryIsBounded() {
        val messages = (1..30).map {
            AiChatMessage(role = AiChatRole.USER, content = "message-$it")
        }
        val trimmed = AiChatProtocol.trimHistory(messages, 12)
        assertEquals(12, trimmed.size)
        assertEquals("message-19", trimmed.first().content)
        assertEquals("message-30", trimmed.last().content)
    }
}
