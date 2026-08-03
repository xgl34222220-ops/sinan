package com.tianji.probabilitylab.nativev4.ai

import java.net.URL

data class AiTokenBudget(
    val parameter: String?,
    val value: Int?,
    val label: String,
)

/**
 * The output limit is only a safety ceiling; it must not be used to simulate a faster model by
 * cutting off reasoning. Official DeepSeek V4 therefore receives its documented maximum output
 * space in every reasoning mode. Compatible and model-dependent APIs remain uncapped by the
 * client so the provider can apply the selected model's own maximum.
 *
 * Streaming completion is still terminated immediately once Tianji has received a complete
 * position + scores core, so a high ceiling does not make a short answer wait for unused tokens.
 */
object AiTokenPolicy {
    const val DEEPSEEK_V4_MAX_OUTPUT_TOKENS: Int = 384 * 1024

    // Kept as aliases for source compatibility. Reasoning mode controls thinking effort, not the
    // amount of output space available to the model.
    const val LOW_MAX_OUTPUT_TOKENS: Int = DEEPSEEK_V4_MAX_OUTPUT_TOKENS
    const val AUTO_MAX_OUTPUT_TOKENS: Int = DEEPSEEK_V4_MAX_OUTPUT_TOKENS
    const val HIGH_MAX_OUTPUT_TOKENS: Int = DEEPSEEK_V4_MAX_OUTPUT_TOKENS

    fun resolve(config: AiConfig, responsesApi: Boolean): AiTokenBudget {
        val host = runCatching { URL(config.endpoint.trim()).host.lowercase() }.getOrDefault("")
        val model = config.model.trim().lowercase()
        val officialDeepSeekV4 = host.endsWith("deepseek.com") && model.startsWith("deepseek-v4")

        if (!officialDeepSeekV4) {
            return AiTokenBudget(
                parameter = null,
                value = null,
                label = "使用所选模型/供应商的最大输出空间（客户端不限制）",
            )
        }

        return AiTokenBudget(
            parameter = if (responsesApi) "max_output_tokens" else "max_tokens",
            value = DEEPSEEK_V4_MAX_OUTPUT_TOKENS,
            label = "使用 DeepSeek V4 最大输出空间 384K tokens · 完整结果到达即结束",
        )
    }
}
