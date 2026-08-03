package com.tianji.probabilitylab.nativev4.ai

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class AiReasoningFallbackTest {
    private fun config(mode: AiReasoningMode) = AiConfig(
        provider = AiProvider.DEEPSEEK,
        endpoint = AiProvider.DEEPSEEK.defaultEndpoint,
        model = AiProvider.DEEPSEEK.defaultModel,
        reasoningMode = mode,
    )

    @Test
    fun autoUsesProviderDefaultInsteadOfForcingHigh() {
        val value = AiReasoningEngine.resolve(config(AiReasoningMode.AUTO))
        assertFalse(value.sendControl)
        assertFalse(value.enableThinking)
        assertFalse(value.expectsReasoning)
        assertNull(value.effort)
        assertTrue(value.displayLabel.contains("模型默认"))
    }

    @Test
    fun lowExplicitlyDisablesControllableDeepSeekThinking() {
        val value = AiReasoningEngine.resolve(config(AiReasoningMode.LOW))
        assertTrue(value.sendControl)
        assertFalse(value.enableThinking)
        assertFalse(value.expectsReasoning)
    }

    @Test
    fun deepStillUsesMaximumEffort() {
        val value = AiReasoningEngine.resolve(config(AiReasoningMode.HIGH))
        assertTrue(value.sendControl)
        assertTrue(value.enableThinking)
        assertTrue(value.expectsReasoning)
        assertEquals("max", value.effort)
    }
}
