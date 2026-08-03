package com.tianji.probabilitylab.nativev4.ai

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class AiFormalForecastPolicyTest {
    @Test
    fun highDeepSeekFormalForecastKeepsMaxThinkingWithDeadlineLabel() {
        val config = AiConfig(
            provider = AiProvider.DEEPSEEK,
            endpoint = "https://api.deepseek.com/chat/completions",
            model = "deepseek-v4-pro",
            apiKey = "test",
            reasoningMode = AiReasoningMode.HIGH,
        )
        val decision = AiReasoningEngine.resolveForecast(config)
        assertTrue(decision.sendControl)
        assertTrue(decision.enableThinking)
        assertTrue(decision.expectsReasoning)
        assertEquals("max", decision.effort)
        assertTrue(decision.displayLabel.contains("深度思考"))
        assertTrue(decision.displayLabel.contains("限时收口"))
    }

    @Test
    fun formalDeepReasoningUsesTheModelMaximumOutputSpace() {
        val config = AiConfig(
            provider = AiProvider.DEEPSEEK,
            endpoint = "https://api.deepseek.com/chat/completions",
            model = "deepseek-v4-pro",
            apiKey = "test",
            reasoningMode = AiReasoningMode.HIGH,
        )
        val budget = AiTokenPolicy.resolve(config, responsesApi = false)
        assertEquals("max_tokens", budget.parameter)
        assertEquals(AiTokenPolicy.DEEPSEEK_V4_MAX_OUTPUT_TOKENS, budget.value)
        assertEquals(384 * 1024, budget.value)
    }
}
