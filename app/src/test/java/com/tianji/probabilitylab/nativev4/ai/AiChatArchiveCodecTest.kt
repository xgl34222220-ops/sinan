package com.tianji.probabilitylab.nativev4.ai

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class AiChatArchiveCodecTest {
    @Test
    fun archiveRoundTripKeepsPeriodModelMessagesAndCandidate() {
        val archive = AiChatArchive(
            id = AiChatArchiveId.of("azxy10", "21347340", "profile-1", "deepseek-v4-pro"),
            lotteryKey = "azxy10",
            profileId = "profile-1",
            profileName = "DeepSeek 主力",
            model = "deepseek-v4-pro",
            targetPeriod = "21347340",
            personaId = AiChatPersona.TREND.id,
            messages = listOf(
                AiChatMessage(id = "u1", role = AiChatRole.USER, content = "分析第一名"),
                AiChatMessage(id = "a1", role = AiChatRole.ASSISTANT, content = "历史相对候选如下"),
            ),
            prediction = AiChatPrediction(
                position = 0,
                top6 = listOf(9, 1, 6, 3, 5, 10),
                top7 = listOf(9, 1, 6, 3, 5, 10, 2),
                probabilities = List(10) { index -> (index + 1).toDouble() },
            ),
            createdAtEpochMs = 100L,
            updatedAtEpochMs = 200L,
        )

        val decoded = AiChatArchiveCodec.decode(AiChatArchiveCodec.encode(listOf(archive))).single()

        assertEquals(archive.id, decoded.id)
        assertEquals("21347340", decoded.targetPeriod)
        assertEquals("deepseek-v4-pro", decoded.model)
        assertEquals(AiChatPersona.TREND.id, decoded.personaId)
        assertEquals(listOf("分析第一名", "历史相对候选如下"), decoded.messages.map { it.content })
        assertEquals(listOf(9, 1, 6, 3, 5, 10), decoded.prediction?.top6)
        assertEquals(10, decoded.prediction?.probabilities?.size)
        assertTrue(AiChatArchiveCodec.summary(decoded).hasPrediction)
    }

    @Test
    fun archiveIdentitySeparatesTargetPeriodAndModel() {
        val flash = AiChatArchiveId.of("azxy10", "100", "profile", "deepseek-v4-flash")
        val pro = AiChatArchiveId.of("azxy10", "100", "profile", "deepseek-v4-pro")
        val nextPeriod = AiChatArchiveId.of("azxy10", "101", "profile", "deepseek-v4-flash")

        assertNotEquals(flash, pro)
        assertNotEquals(flash, nextPeriod)
    }
}
