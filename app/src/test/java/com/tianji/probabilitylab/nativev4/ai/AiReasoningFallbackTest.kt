package com.tianji.probabilitylab.nativev4.ai

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class AiReasoningFallbackTest {
    private fun config(mode: AiReasoningMode) = AiConfig(
        provider = AiProvider.DEEPSEEK,
        endpoint = AiProvider.DEEPSEEK.defaultEndpoint,
        model = AiProvider.DEEPSEEK.defaultModel,
        reasoningMode = mode,
    )

    @Test fun chatAutoKeepsThinking() {
        val value = AiReasoningEngine.resolve(config(AiReasoningMode.AUTO))
        assertTrue(value.sendControl)
        assertTrue(value.enableThinking)
        assertTrue(value.expectsReasoning)
        assertEquals("high", value.effort)
    }

    @Test fun lowModeActuallyDisablesDeepSeekLongThinking() {
        val value = AiReasoningEngine.resolve(config(AiReasoningMode.LOW))
        assertTrue(value.sendControl)
        assertFalse(value.enableThinking)
        assertFalse(value.expectsReasoning)
    }

    @Test fun formalAutoPrioritizesBoundedCompletion() {
        val value = AiReasoningEngine.resolveForecast(config(AiReasoningMode.AUTO))
        assertTrue(value.sendControl)
        assertFalse(value.enableThinking)
        assertFalse(value.expectsReasoning)
        assertEquals(null, value.effort)
        assertTrue(value.displayLabel.contains("自动省时"))
    }

    @Test fun formalHighKeepsMaxThinkingWithDeadline() {
        val value = AiReasoningEngine.resolveForecast(config(AiReasoningMode.HIGH))
        assertTrue(value.sendControl)
        assertTrue(value.enableThinking)
        assertTrue(value.expectsReasoning)
        assertEquals("max", value.effort)
        assertTrue(value.displayLabel.contains("深度思考"))
        assertTrue(value.displayLabel.contains("限时收口"))
    }

    @Test fun chatRetryNeverDisablesThinking() {
        val value = AiReasoningEngine.fallback(config(AiReasoningMode.AUTO))
        assertTrue(value.sendControl)
        assertTrue(value.enableThinking)
        assertTrue(value.expectsReasoning)
    }
}
