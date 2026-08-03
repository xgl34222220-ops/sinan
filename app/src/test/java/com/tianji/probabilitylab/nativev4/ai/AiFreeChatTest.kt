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
    fun extractsPredictionWithoutChangingAiRanking() {
        val reply = """
            简要结论如下。
            <tianji_forecast>{"position":8,"scores":[0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,1.0]}</tianji_forecast>
        """.trimIndent()

        val prediction = AiChatProtocol.parsePrediction(reply)
        assertNotNull(prediction)
        assertEquals(7, prediction!!.position)
        assertEquals(listOf(10, 9, 8, 7, 6, 5), prediction.top6)
        assertEquals(10, prediction.probabilities.size)
        assertTrue(AiChatProtocol.visibleText(reply, hasPrediction = true).contains("简要结论"))
        assertFalse(AiChatProtocol.visibleText(reply, hasPrediction = true).contains("scores"))
    }

    @Test
    fun streamingTextNeverLeaksForecastPayload() {
        val partial = "先给出分析依据。\n<tianji_forecast>{\"position\":1,\"scores\":[1,2"
        assertEquals("先给出分析依据。\n", AiChatProtocol.visibleStreamingText(partial))
    }

    @Test
    fun builtInPersonasAreCompleteAndResolvable() {
        assertEquals(6, AiChatPersona.values().size)
        assertEquals(AiChatPersona.HISTORY, AiChatPersona.fromId("history"))
        assertEquals(AiChatPersona.COMPREHENSIVE, AiChatPersona.fromId("unknown"))
        AiChatPersona.values().forEach { persona ->
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
