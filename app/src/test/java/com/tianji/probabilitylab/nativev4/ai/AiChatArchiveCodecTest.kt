package com.tianji.probabilitylab.nativev4.ai

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class AiChatArchiveCodecTest {
    @Test
    fun roundTripKeepsConversationMemoryMessagesAndCandidateHistory() {
        val prediction = AiChatPrediction(
            position = 0,
            top6 = listOf(9, 1, 6, 3, 5, 10),
            top7 = listOf(9, 1, 6, 3, 5, 10, 2),
            probabilities = List(10) { index -> (index + 1).toDouble() },
        )
        val archive = AiChatArchive(
            id = "conversation-1",
            lotteryKey = "azxy10",
            profileId = "profile-1",
            profileName = "DeepSeek 主力",
            model = "deepseek-v4-pro",
            title = "第一名跨期调整",
            targetPeriod = "21347341",
            personaId = AiChatPersona.TREND.id,
            memorySummary = "上一期未中，用户要求降低短期热号权重",
            continuationOf = "conversation-0",
            messages = listOf(
                AiChatMessage(id = "u1", role = AiChatRole.USER, content = "上一期没中，调整策略", targetPeriod = "21347341"),
                AiChatMessage(id = "a1", role = AiChatRole.ASSISTANT, content = "本期降低短窗权重", targetPeriod = "21347341"),
            ),
            candidates = listOf(
                AiChatCandidateRecord(
                    id = "c1",
                    messageId = "a1",
                    targetPeriod = "21347341",
                    prediction = prediction,
                    actualNumber = 4,
                    resolvedPeriod = "21347341",
                ),
            ),
            createdAtEpochMs = 100L,
            updatedAtEpochMs = 200L,
        )

        val decoded = AiChatArchiveCodec.decode(AiChatArchiveCodec.encode(listOf(archive))).single()

        assertEquals(archive.id, decoded.id)
        assertEquals("第一名跨期调整", decoded.title)
        assertEquals("上一期未中，用户要求降低短期热号权重", decoded.memorySummary)
        assertEquals("conversation-0", decoded.continuationOf)
        assertEquals(listOf("上一期没中，调整策略", "本期降低短窗权重"), decoded.messages.map { it.content })
        assertEquals(listOf(9, 1, 6, 3, 5, 10), decoded.candidates.single().prediction.top6)
        assertEquals(4, decoded.candidates.single().actualNumber)
        assertTrue(AiChatArchiveCodec.summary(decoded).hasPrediction)
    }

    @Test
    fun newConversationIdsDoNotDependOnTargetPeriod() {
        val first = AiChatConversationId.newId("azxy10", "profile", "deepseek-v4-pro")
        val second = AiChatConversationId.newId("azxy10", "profile", "deepseek-v4-pro")
        assertNotEquals(first, second)
    }

    @Test
    fun legacySchemaOnePredictionMigratesIntoCandidateHistory() {
        val legacy = """{"schema":1,"archives":[{"id":"legacy","lottery_key":"azxy10","profile_id":"p","profile_name":"P","model":"m","target_period":"100","persona_id":"trend","created_at":1,"updated_at":2,"messages":[{"id":"a","role":"ASSISTANT","content":"结果","created_at":1,"latency_ms":null}],"prediction":{"position":0,"top6":[1,2,3,4,5,6],"top7":[1,2,3,4,5,6,7],"probabilities":[1,1,1,1,1,1,1,1,1,1]}}]}"""
        val decoded = AiChatArchiveCodec.decode(legacy).single()
        assertEquals(1, decoded.candidates.size)
        assertEquals("100", decoded.candidates.single().targetPeriod)
    }
}
