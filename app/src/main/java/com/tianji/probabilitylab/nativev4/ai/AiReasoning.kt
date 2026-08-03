package com.tianji.probabilitylab.nativev4.ai

import java.net.URL

enum class AiReasoningMode(val label: String, val detail: String) {
    AUTO("自动", "不强制参数，由模型和供应商决定"),
    LOW("省时", "降低或关闭可控推理，优先速度与费用"),
    HIGH("深入", "请求供应商高强度推理，可能更慢且更贵"),
}

enum class AiReasoningProtocol(val label: String) {
    AUTO("自动识别"),
    DEEPSEEK("DeepSeek thinking"),
    OPENAI("OpenAI reasoning"),
    OPENROUTER("OpenRouter reasoning"),
    ENABLE_THINKING("enable_thinking"),
    NONE("普通接口 / 不可控"),
}

enum class AiReasoningState(val label: String) {
    DEFAULT("模型默认"),
    DISABLED("已关闭可控推理"),
    REQUESTED("已请求推理，供应商未返回用量"),
    VERIFIED("已验证推理"),
    FALLBACK("推理重试成功"),
    UNSUPPORTED("未检测到可控推理"),
}

data class AiTokenUsage(
    val inputTokens: Int? = null,
    val outputTokens: Int? = null,
    val reasoningTokens: Int? = null,
)

data class AiReasoningDecision(
    val protocol: AiReasoningProtocol,
    val preference: AiReasoningMode,
    val supported: Boolean,
    val sendControl: Boolean,
    val enableThinking: Boolean,
    val effort: String?,
    val displayLabel: String,
) {
    val expectsReasoning: Boolean
        get() = supported && sendControl && enableThinking
}

object AiReasoningEngine {
    fun resolve(config: AiConfig, overrideMode: AiReasoningMode? = null): AiReasoningDecision {
        val preference = overrideMode ?: config.reasoningMode
        val protocol = when {
            config.reasoningProtocol != AiReasoningProtocol.AUTO -> config.reasoningProtocol
            config.provider == AiProvider.DEEPSEEK -> AiReasoningProtocol.DEEPSEEK
            config.provider == AiProvider.OPENAI -> AiReasoningProtocol.OPENAI
            else -> detectCompatibleProtocol(config.endpoint)
        }
        if (protocol == AiReasoningProtocol.NONE) {
            return AiReasoningDecision(
                protocol = protocol,
                preference = preference,
                supported = false,
                sendControl = false,
                enableThinking = false,
                effort = null,
                displayLabel = "未检测到可控推理 · 仅执行历史分析",
            )
        }
        return when (preference) {
            AiReasoningMode.AUTO -> AiReasoningDecision(
                protocol, preference, true, false, false, null,
                "${protocol.label} · 模型默认",
            )
            AiReasoningMode.LOW -> when (protocol) {
                AiReasoningProtocol.DEEPSEEK,
                AiReasoningProtocol.ENABLE_THINKING -> AiReasoningDecision(
                    protocol, preference, true, true, false, null,
                    "${protocol.label} · 已关闭可控推理",
                )
                else -> AiReasoningDecision(
                    protocol, preference, true, true, true, "low",
                    "${protocol.label} · 低推理",
                )
            }
            AiReasoningMode.HIGH -> AiReasoningDecision(
                protocol, preference, true, true, true,
                if (protocol == AiReasoningProtocol.DEEPSEEK) "max" else "high",
                "${protocol.label} · 高推理",
            )
        }
    }

    fun fallback(config: AiConfig): AiReasoningDecision {
        val current = resolve(config)
        if (!current.supported) return current.copy(displayLabel = "${current.displayLabel} · 重试")
        return current.copy(
            sendControl = true,
            enableThinking = true,
            effort = when {
                current.protocol == AiReasoningProtocol.DEEPSEEK &&
                    config.reasoningMode == AiReasoningMode.HIGH -> "max"
                current.effort.isNullOrBlank() -> "high"
                else -> current.effort
            },
            displayLabel = "${current.protocol.label} · 保留思考重试",
        )
    }

    fun stateFor(
        decision: AiReasoningDecision,
        usage: AiTokenUsage,
        hasReasoningContent: Boolean,
        fallback: Boolean,
    ): AiReasoningState = when {
        fallback -> AiReasoningState.FALLBACK
        !decision.supported -> AiReasoningState.UNSUPPORTED
        !decision.sendControl -> AiReasoningState.DEFAULT
        !decision.enableThinking -> AiReasoningState.DISABLED
        hasReasoningContent || (usage.reasoningTokens ?: 0) > 0 -> AiReasoningState.VERIFIED
        else -> AiReasoningState.REQUESTED
    }

    private fun detectCompatibleProtocol(endpoint: String): AiReasoningProtocol {
        val host = runCatching { URL(endpoint.trim()).host.lowercase() }.getOrDefault("")
        return when {
            "deepseek" in host -> AiReasoningProtocol.DEEPSEEK
            "openai" in host -> AiReasoningProtocol.OPENAI
            "openrouter" in host -> AiReasoningProtocol.OPENROUTER
            "dashscope" in host || "aliyuncs" in host || "siliconflow" in host ->
                AiReasoningProtocol.ENABLE_THINKING
            else -> AiReasoningProtocol.NONE
        }
    }
}
