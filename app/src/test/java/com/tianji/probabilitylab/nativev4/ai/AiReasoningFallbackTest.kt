package com.tianji.probabilitylab.nativev4.ai

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class AiReasoningFallbackTest {
    private fun config(mode: AiReasoningMode) = AiConfig(
        provider = AiProvider.DEEPSEEK,
        endpoint = AiProvider.DEEPSEEK.defaultEndpoint,
        model = AiProvider.DEEPSEEK.defaultModel,
        reasoningMode = mode,
    )

    @Test fun autoKeepsThinking() {
        val value = AiReasoningEngine.resolve(config(AiReasoningMode.AUTO))
        assertTrue(value.sendControl)
        assertTrue(value.enableThinking)
        assertTrue(value.expectsReasoning)
        assertEquals("high", value.effort)
    }

    @Test fun deepUsesMaxEffort() {
        assertEquals("max", AiReasoningEngine.resolve(config(AiReasoningMode.HIGH)).effort)
    }

    @Test fun retryNeverDisablesThinking() {
        val value = AiReasoningEngine.fallback(config(AiReasoningMode.AUTO))
        assertTrue(value.sendControl)
        assertTrue(value.enableThinking)
        assertTrue(value.expectsReasoning)
    }
}
