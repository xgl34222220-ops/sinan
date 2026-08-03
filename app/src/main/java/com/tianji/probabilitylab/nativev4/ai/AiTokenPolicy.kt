package com.tianji.probabilitylab.nativev4.ai

import java.net.URL

data class AiTokenBudget(
    val parameter: String?,
    val value: Int?,
    val label: String,
)

/**
 * Formal predictions need a compact JSON score matrix, not an unbounded model transcript.
 * Official DeepSeek V4 requests therefore use a mode-aware ceiling. Compatible/unknown services
 * remain provider-controlled so a non-standard API is not broken by an unsupported parameter.
 */
object AiTokenPolicy {
    const val LOW_MAX_OUTPUT_TOKENS: Int = 1024
    const val AUTO_MAX_OUTPUT_TOKENS: Int = 1536
    const val HIGH_MAX_OUTPUT_TOKENS: Int = 2048

    fun resolve(config: AiConfig, responsesApi: Boolean): AiTokenBudget {
        val host = runCatching { URL(config.endpoint.trim()).host.lowercase() }.getOrDefault("")
        val model = config.model.trim().lowercase()
        val boundedDeepSeek = config.provider == AiProvider.DEEPSEEK ||
            host.contains("deepseek") || model.startsWith("deepseek-")
        val boundedOpenAiResponses = config.provider == AiProvider.OPENAI && responsesApi

        if (!boundedDeepSeek && !boundedOpenAiResponses) {
            return AiTokenBudget(
                parameter = null,
                value = null,
                label = "输出空间由模型/供应商上限决定（客户端不限）",
            )
        }

        val (value, modeLabel) = when (config.reasoningMode) {
            AiReasoningMode.LOW -> LOW_MAX_OUTPUT_TOKENS to "省时"
            AiReasoningMode.AUTO -> AUTO_MAX_OUTPUT_TOKENS to "自动"
            AiReasoningMode.HIGH -> HIGH_MAX_OUTPUT_TOKENS to "深入"
        }
        return AiTokenBudget(
            parameter = if (boundedOpenAiResponses) "max_output_tokens" else "max_tokens",
            value = value,
            label = "正式预测核心输出上限 $value tokens（$modeLabel）",
        )
    }
}
