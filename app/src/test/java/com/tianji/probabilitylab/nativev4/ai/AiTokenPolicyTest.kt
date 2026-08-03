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

    @Test fun officialDeepSeekUsesDocumentedMaximumInEveryReasoningMode() {
        AiReasoningMode.entries.forEach { mode ->
            val budget = AiTokenPolicy.resolve(deepSeek(mode), responsesApi = false)
            assertEquals("max_tokens", budget.parameter)
            assertEquals(AiTokenPolicy.DEEPSEEK_V4_MAX_OUTPUT_TOKENS, budget.value)
            assertTrue(budget.label.contains("384K"))
            assertTrue(budget.label.contains("完整结果到达即结束"))
        }
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
        assertTrue(budget.label.contains("客户端不限制"))
    }

    @Test fun modelDependentOpenAiResponsesHasNoArtificialClientCap() {
        val config = AiConfig(
            provider = AiProvider.OPENAI,
            endpoint = "https://api.openai.com/v1/responses",
            model = "gpt-5",
            reasoningMode = AiReasoningMode.HIGH,
        )
        val budget = AiTokenPolicy.resolve(config, responsesApi = true)
        assertNull(budget.parameter)
        assertNull(budget.value)
        assertTrue(budget.label.contains("最大输出空间"))
    }
}
