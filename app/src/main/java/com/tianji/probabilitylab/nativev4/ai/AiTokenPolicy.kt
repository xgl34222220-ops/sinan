package com.tianji.probabilitylab.nativev4.ai

import java.net.URL

data class AiTokenBudget(
    val parameter: String?,
    val value: Int?,
    val label: String,
)

/**
 * Formal predictions keep real reasoning in AUTO/HIGH, but still use a bounded output budget.
 * The wall-clock deadline is the primary guarantee that a model cannot think until after the draw;
 * these token ceilings prevent an unexpectedly large transcript from bypassing cost controls.
 */
object AiTokenPolicy {
    const val LOW_MAX_OUTPUT_TOKENS: Int = 2048
    const val AUTO_MAX_OUTPUT_TOKENS: Int = 8192
    const val HIGH_MAX_OUTPUT_TOKENS: Int = 16384

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
            AiReasoningMode.AUTO -> AUTO_MAX_OUTPUT_TOKENS to "自动思考"
            AiReasoningMode.HIGH -> HIGH_MAX_OUTPUT_TOKENS to "深度思考"
        }
        return AiTokenBudget(
            parameter = if (boundedOpenAiResponses) "max_output_tokens" else "max_tokens",
            value = value,
            label = "正式预测推理与核心输出上限 $value tokens（$modeLabel）",
        )
    }
}
