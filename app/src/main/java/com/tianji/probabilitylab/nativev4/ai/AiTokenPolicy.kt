package com.tianji.probabilitylab.nativev4.ai

import java.net.URL

data class AiTokenBudget(
    val parameter: String?,
    val value: Int?,
    val label: String,
)

/**
 * The client must not impose a smaller arbitrary output ceiling than the selected model.
 * Known official model limits may be sent explicitly; unknown or compatible services are left
 * provider-controlled by omitting the output-token parameter entirely.
 */
object AiTokenPolicy {
    const val DEEPSEEK_V4_MAX_OUTPUT_TOKENS: Int = 384 * 1024

    fun resolve(config: AiConfig, responsesApi: Boolean): AiTokenBudget {
        val host = runCatching { URL(config.endpoint.trim()).host.lowercase() }.getOrDefault("")
        val model = config.model.trim().lowercase()
        val officialDeepSeekV4 = host.endsWith("deepseek.com") &&
            (model == "deepseek-v4-flash" || model == "deepseek-v4-pro")

        return if (officialDeepSeekV4) {
            AiTokenBudget(
                parameter = if (responsesApi) "max_output_tokens" else "max_tokens",
                value = DEEPSEEK_V4_MAX_OUTPUT_TOKENS,
                label = "输出空间 384K（DeepSeek 模型上限）",
            )
        } else {
            AiTokenBudget(
                parameter = null,
                value = null,
                label = "输出空间由模型/供应商上限决定（客户端不限）",
            )
        }
    }
}
