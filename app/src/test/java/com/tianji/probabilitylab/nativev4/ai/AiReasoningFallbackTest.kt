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

    @Test fun formalAutoUsesFastForecastDecision() {
        val value = AiReasoningEngine.resolveForecast(config(AiReasoningMode.AUTO))
        assertTrue(value.sendControl)
        assertFalse(value.enableThinking)
        assertFalse(value.expectsReasoning)
    }

    @Test fun formalHighKeepsMaxEffort() {
        val value = AiReasoningEngine.resolveForecast(config(AiReasoningMode.HIGH))
        assertTrue(value.enableThinking)
        assertTrue(value.expectsReasoning)
        assertEquals("max", value.effort)
    }

    @Test fun retryNeverDisablesThinking() {
        val value = AiReasoningEngine.fallback(config(AiReasoningMode.AUTO))
        assertTrue(value.sendControl)
        assertTrue(value.enableThinking)
        assertTrue(value.expectsReasoning)
    }
}
