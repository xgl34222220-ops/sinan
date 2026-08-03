package com.tianji.probabilitylab.nativev4.ai

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class AiTokenPolicyTest {
    @Test
    fun officialDeepSeekV4UsesDocumentedModelMaximum() {
        val config = AiConfig(
            provider = AiProvider.DEEPSEEK,
            endpoint = "https://api.deepseek.com/chat/completions",
            model = "deepseek-v4-pro",
        )

        val budget = AiTokenPolicy.resolve(config, responsesApi = false)

        assertEquals("max_tokens", budget.parameter)
        assertEquals(384 * 1024, budget.value)
        assertTrue(budget.label.contains("模型上限"))
    }

    @Test
    fun unknownCompatibleModelHasNoClientTokenCap() {
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

    @Test
    fun openAiResponsesLeavesLimitToSelectedModel() {
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
