package com.tianji.probabilitylab.nativev4.ai

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class AiTokenPolicyTest {
    private fun deepSeek(mode: AiReasoningMode) = AiConfig(
        provider = AiProvider.DEEPSEEK,
        endpoint = "https://api.deepseek.com/chat/completions",
        model = "deepseek-v4-pro",
        reasoningMode = mode,
    )

    @Test fun officialDeepSeekAutoUsesBoundedForecastBudget() {
        val budget = AiTokenPolicy.resolve(deepSeek(AiReasoningMode.AUTO), responsesApi = false)
        assertEquals("max_tokens", budget.parameter)
        assertEquals(AiTokenPolicy.AUTO_MAX_OUTPUT_TOKENS, budget.value)
        assertTrue(budget.label.contains("自动"))
    }

    @Test fun officialDeepSeekLowUsesSmallestForecastBudget() {
        val budget = AiTokenPolicy.resolve(deepSeek(AiReasoningMode.LOW), responsesApi = false)
        assertEquals(AiTokenPolicy.LOW_MAX_OUTPUT_TOKENS, budget.value)
    }

    @Test fun officialDeepSeekHighKeepsLargerBoundedBudget() {
        val budget = AiTokenPolicy.resolve(deepSeek(AiReasoningMode.HIGH), responsesApi = false)
        assertEquals(AiTokenPolicy.HIGH_MAX_OUTPUT_TOKENS, budget.value)
    }

    @Test fun unknownCompatibleModelHasNoClientTokenCap() {
        val config = AiConfig(
            provider = AiProvider.COMPATIBLE,
            endpoint = "https://example.com/v1/chat/completions",
            model = "future-model",
        )
        val budget = AiTokenPolicy.resolve(config, responsesApi = false)
        assertNull(budget.parameter)
        assertNull(budget.value)
        assertTrue(budget.label.contains("客户端不限"))
    }

    @Test fun openAiResponsesLeavesLimitToSelectedModel() {
        val config = AiConfig(
            provider = AiProvider.OPENAI,
            endpoint = "https://api.openai.com/v1/responses",
            model = "gpt-5",
        )
        val budget = AiTokenPolicy.resolve(config, responsesApi = true)
        assertNull(budget.parameter)
        assertNull(budget.value)
    }
}
