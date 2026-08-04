package com.tianji.probabilitylab.nativev4.ai

import org.junit.Assert.assertEquals
import org.junit.Test

class AiChatPersonaTest {
    @Test
    fun onlyThreeFocusedPersonasRemain() {
        assertEquals(3, AiChatPersona.entries.size)
        assertEquals(
            listOf("大数据规律", "走势分析", "综合预测"),
            AiChatPersona.entries.map(AiChatPersona::displayName),
        )
    }

    @Test
    fun legacyPersonaIdsMigrateWithoutBreakingArchives() {
        assertEquals(AiChatPersona.COMPREHENSIVE, AiChatPersona.fromId("history"))
        assertEquals(AiChatPersona.COMPREHENSIVE, AiChatPersona.fromId("omission"))
        assertEquals(AiChatPersona.COMPREHENSIVE, AiChatPersona.fromId("transition"))
        assertEquals(AiChatPersona.COMPREHENSIVE, AiChatPersona.fromId("bayes_big_data"))
        assertEquals(AiChatPersona.TREND, AiChatPersona.fromId("regime_state"))
        assertEquals(AiChatPersona.RISK_AUDIT, AiChatPersona.fromId("adaptive_learning"))
        assertEquals(AiChatPersona.RISK_AUDIT, AiChatPersona.fromId("universal_consensus"))
    }
}
