package com.tianji.probabilitylab.nativev4.ai

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class AiReasoningFallbackTest {
    @Test
    fun deepSeekFallbackExplicitlyDisablesThinking() {
        val config = AiConfig(
            provider = AiProvider.DEEPSEEK,
            endpoint = AiProvider.DEEPSEEK.defaultEndpoint,
            model = AiProvider.DEEPSEEK.defaultModel,
            reasoningMode = AiReasoningMode.HIGH,
        )
        val fallback = AiReasoningEngine.fallback(config)
        assertEquals(AiReasoningProtocol.DEEPSEEK, fallback.protocol)
        assertTrue(fallback.sendControl)
        assertFalse(fallback.enableThinking)
        assertFalse(fallback.expectsReasoning)
    }
}
