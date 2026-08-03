package com.tianji.probabilitylab.nativev4.ai

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Assert.assertEquals
import org.junit.Test

class AiFormalForecastPolicyTest {
    @Test
    fun highDeepSeekFormalForecastStillDisablesLongThinking() {
        val config = AiConfig(
            provider = AiProvider.DEEPSEEK,
            endpoint = "https://api.deepseek.com/chat/completions",
            model = "deepseek-v4-pro",
            apiKey = "test",
            reasoningMode = AiReasoningMode.HIGH,
        )
        val decision = AiReasoningEngine.resolveForecast(config)
        assertTrue(decision.sendControl)
        assertFalse(decision.enableThinking)
        assertTrue(decision.displayLabel.contains("限时"))
    }

    @Test
    fun formalCoreBudgetIsBounded() {
        val config = AiConfig(
            provider = AiProvider.DEEPSEEK,
            endpoint = "https://api.deepseek.com/chat/completions",
            model = "deepseek-v4-pro",
            apiKey = "test",
            reasoningMode = AiReasoningMode.HIGH,
        )
        val budget = AiTokenPolicy.resolve(config, responsesApi = false)
        assertEquals("max_tokens", budget.parameter)
        assertTrue((budget.value ?: Int.MAX_VALUE) <= 2048)
    }
}
