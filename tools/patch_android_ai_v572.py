from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    file = Path(path)
    text = file.read_text()
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected exactly one match, found {count}")
    file.write_text(text.replace(old, new, 1))


reasoning = "app/src/main/java/com/tianji/probabilitylab/nativev4/ai/AiReasoning.kt"
replace_once(
    reasoning,
    '''                AiReasoningProtocol.DEEPSEEK -> resolved.copy(
                    sendControl = true,
                    enableThinking = true,
                    effort = "high",
                    displayLabel = "${resolved.protocol.label} · 正式预测自动思考 · 限时收口",
                )''',
    '''                AiReasoningProtocol.DEEPSEEK -> resolved.copy(
                    sendControl = true,
                    enableThinking = false,
                    effort = null,
                    displayLabel = "${resolved.protocol.label} · 正式预测自动省时 · 对话保留思考",
                )''',
)

analysis = "app/src/main/java/com/tianji/probabilitylab/nativev4/ai/AiAnalysis.kt"
replace_once(
    analysis,
    '''        val tokenBudget = AiTokenPolicy.resolve(config, responsesApi)

        fun conversationMessages(includeReasoning: Boolean): JSONArray = JSONArray().apply {''',
    '''        val tokenBudget = AiTokenPolicy.resolve(config, responsesApi)
        val effectiveTokenBudget = if (
            streamResponse && jsonOutput && config.provider != AiProvider.COMPATIBLE
        ) {
            AiTokenBudget(
                parameter = tokenBudget.parameter
                    ?: if (responsesApi) "max_output_tokens" else "max_tokens",
                value = if (reasoningDecision.preference == AiReasoningMode.HIGH) 8_192 else 4_096,
                label = if (reasoningDecision.preference == AiReasoningMode.HIGH) {
                    "正式预测核心输出预算 8192 tokens · 完整矩阵到达即结束"
                } else {
                    "正式预测核心输出预算 4096 tokens · 完整矩阵到达即结束"
                },
            )
        } else {
            tokenBudget
        }

        fun conversationMessages(includeReasoning: Boolean): JSONArray = JSONArray().apply {''',
)
replace_once(
    analysis,
    '''            tokenBudget.parameter?.let { parameter -> put(parameter, tokenBudget.value) }''',
    '''            effectiveTokenBudget.parameter?.let { parameter ->
                put(parameter, effectiveTokenBudget.value)
            }''',
)
replace_once(
    analysis,
    '''                        tokenBudgetLabel = tokenBudget.label,''',
    '''                        tokenBudgetLabel = effectiveTokenBudget.label,''',
)
replace_once(
    analysis,
    '''            } catch (_: SocketTimeoutException) {
                onProgress(
                    "等待模型输出超时，本次请求已停止，不会自动重新预测",
                    System.currentTimeMillis() - started,
                )
                error("模型响应超过 ${readTimeoutMs / 1_000} 秒；本次已停止，未自动重新预测")
            } catch (cause: EOFException) {''',
    '''            } catch (_: SocketTimeoutException) {
                onProgress(
                    "等待模型输出超时，正在交由同模型限时收口策略处理",
                    System.currentTimeMillis() - started,
                )
                error("模型响应超过 ${readTimeoutMs / 1_000} 秒")
            } catch (cause: EOFException) {''',
)
replace_once(
    analysis,
    '''        val firstFailure = primary.exceptionOrNull() ?: error("AI 分析失败")
        val reasoningControlFailure = isReasoningControlFailure(firstFailure, primaryDecision)
        if (!reasoningControlFailure) {
            // Partial output is already continued inside execute(). Transport timeouts, broken
            // streams and invalid model output must remain visible instead of silently starting a
            // second full 60/120-period analysis.
            throw firstFailure
        }
        onProgress(
            "接口拒绝显式思考参数；确认尚未进入模型推理，正在仅一次切换为模型默认思考协议",
            System.currentTimeMillis() - started,
        )''',
    '''        val firstFailure = primary.exceptionOrNull() ?: error("AI 分析失败")
        if (isRetriableModelOutput(firstFailure)) {
            val finalizationDecision = when (primaryDecision.protocol) {
                AiReasoningProtocol.DEEPSEEK,
                AiReasoningProtocol.OPENROUTER,
                AiReasoningProtocol.ENABLE_THINKING,
                -> primaryDecision.copy(
                    sendControl = true,
                    enableThinking = false,
                    effort = null,
                    displayLabel = "${primaryDecision.protocol.label} · 同模型限时核心收口",
                )
                AiReasoningProtocol.OPENAI,
                AiReasoningProtocol.AUTO,
                AiReasoningProtocol.NONE,
                -> primaryDecision.copy(
                    sendControl = false,
                    enableThinking = false,
                    effort = null,
                    displayLabel = "同模型限时核心收口",
                )
            }
            val finalizationTimeoutMs = if (config.analysisMode == AiAnalysisMode.DEEP) 35_000 else 25_000
            onProgress(
                "首次请求没有按时生成完整矩阵；正在用同一模型、同一份原始历史关闭额外思考并收口一次",
                System.currentTimeMillis() - started,
            )
            return runCatching {
                execute(
                    reasoningDecision = finalizationDecision,
                    readTimeoutMs = finalizationTimeoutMs,
                    executionNote = "${config.analysisMode.label} · 同模型限时核心收口",
                    fallback = true,
                    prompt = userPrompt,
                )
            }.getOrElse { finalFailure ->
                error(
                    "首次分析失败（${firstFailure.message.orEmpty().take(90)}）；" +
                        "同模型关闭额外思考收口仍失败（${finalFailure.message.orEmpty().take(90)}）",
                )
            }
        }
        val reasoningControlFailure = isReasoningControlFailure(firstFailure, primaryDecision)
        if (!reasoningControlFailure) {
            throw firstFailure
        }
        onProgress(
            "接口拒绝显式思考参数；确认尚未进入模型推理，正在仅一次切换为模型默认思考协议",
            System.currentTimeMillis() - started,
        )''',
)

chat = "app/src/main/java/com/tianji/probabilitylab/nativev4/ai/AiChatController.kt"
replace_once(
    chat,
    '''        val response = try {
            runRequest(decision)
        } catch (cause: AiChatProtocolRejectedException) {
            if (!decision.sendControl) throw cause
            publisher.reset()
            onProgress("接口拒绝显式思考参数，正在使用模型默认协议重发一次…")
            runRequest(
                decision.copy(sendControl = false, enableThinking = false, effort = null),
            )
        }
        val rawContent = extractContent(response)
        require(rawContent.isNotBlank()) { "模型没有返回可显示的回答" }''',
    '''        var response = try {
            runRequest(decision)
        } catch (cause: AiChatProtocolRejectedException) {
            if (!decision.sendControl) throw cause
            publisher.reset()
            onProgress("接口拒绝显式思考参数，正在使用模型默认协议重发一次…")
            runRequest(
                decision.copy(sendControl = false, enableThinking = false, effort = null),
            )
        }
        var rawContent = extractContent(response)
        if (rawContent.isBlank()) {
            val hadReasoning = extractReasoning(response).isNotBlank()
            publisher.reset()
            onProgress(
                if (hadReasoning) {
                    "模型只返回了思考流，正在用同一模型关闭额外思考并生成最终正文…"
                } else {
                    "流式接口没有返回正文，正在切换同一模型的普通兼容输出…"
                },
            )
            val finalizationDecision = when (decision.protocol) {
                AiReasoningProtocol.DEEPSEEK,
                AiReasoningProtocol.OPENROUTER,
                AiReasoningProtocol.ENABLE_THINKING,
                -> decision.copy(
                    sendControl = true,
                    enableThinking = false,
                    effort = null,
                    displayLabel = "${decision.protocol.label} · 对话正文收口",
                )
                AiReasoningProtocol.OPENAI,
                AiReasoningProtocol.AUTO,
                AiReasoningProtocol.NONE,
                -> decision.copy(
                    sendControl = false,
                    enableThinking = false,
                    effort = null,
                    displayLabel = "对话正文收口",
                )
            }
            val finalizationMessages = JSONArray(messages.toString()).apply {
                put(
                    JSONObject()
                        .put("role", "user")
                        .put(
                            "content",
                            if (wantsPrediction) {
                                "上一请求没有产生最终正文。请立即基于同一份原始历史完成回答，不要输出思考过程，并按原要求在正文后追加完整 tianji_forecast。"
                            } else {
                                "上一请求没有产生最终正文。请立即基于同一上下文给出简体中文最终回答，不要输出思考过程。"
                            },
                        ),
                )
            }
            response = try {
                execute(
                    endpoint = endpoint,
                    config = config,
                    request = requestBody(
                        config = config,
                        responsesApi = responsesApi,
                        messages = finalizationMessages,
                        decision = finalizationDecision,
                        stream = false,
                        wantsPrediction = wantsPrediction,
                    ),
                    timeoutMs = 45_000,
                    onProgress = onProgress,
                    publisher = publisher,
                )
            } catch (cause: AiChatProtocolRejectedException) {
                execute(
                    endpoint = endpoint,
                    config = config,
                    request = requestBody(
                        config = config,
                        responsesApi = responsesApi,
                        messages = finalizationMessages,
                        decision = finalizationDecision.copy(sendControl = false),
                        stream = false,
                        wantsPrediction = wantsPrediction,
                    ),
                    timeoutMs = 45_000,
                    onProgress = onProgress,
                    publisher = publisher,
                )
            }
            rawContent = extractContent(response)
        }
        require(rawContent.isNotBlank()) {
            if (extractReasoning(response).isNotBlank()) {
                "模型只返回了思考过程；关闭思考收口后仍没有最终正文"
            } else {
                "模型接口已响应，但流式与普通输出均没有返回正文"
            }
        }''',
)
replace_once(
    chat,
    '''        if (config.provider != AiProvider.COMPATIBLE) {
            put(if (responsesApi) "max_output_tokens" else "max_tokens", if (wantsPrediction) 4096 else 2048)
        }''',
    '''        if (config.provider != AiProvider.COMPATIBLE) {
            val outputBudget = when {
                decision.expectsReasoning && wantsPrediction -> 8_192
                decision.expectsReasoning -> 6_144
                wantsPrediction -> 4_096
                else -> 2_048
            }
            put(if (responsesApi) "max_output_tokens" else "max_tokens", outputBudget)
        }''',
)
replace_once(
    chat,
    '''            extractTextNode(delta?.opt("reasoning_content"))
                .takeIf(String::isNotEmpty)
                ?.let(reasoning::append)''',
    '''            listOf("reasoning_content", "reasoning", "thinking").forEach { key ->
                extractTextNode(delta?.opt(key))
                    .takeIf(String::isNotEmpty)
                    ?.let(reasoning::append)
            }
            listOf("reasoning_content", "reasoning", "thinking").forEach { key ->
                extractTextNode(root.opt(key))
                    .takeIf(String::isNotEmpty)
                    ?.let(reasoning::append)
            }''',
)
replace_once(
    chat,
    '''        if (rawContent.isBlank()) {
            streamFailure?.let { throw it }
            error("模型没有返回可显示的流式回答")
        }''',
    '''        if (rawContent.isBlank() && reasoning.isBlank()) {
            streamFailure?.let { throw it }
        }''',
)

build = "app/build.gradle.kts"
replace_once(
    build,
    '        versionCode = 38\n        versionName = "5.7.1"',
    '        versionCode = 39\n        versionName = "5.7.2"',
)

Path("app/src/test/java/com/tianji/probabilitylab/nativev4/ai/AiRuntimeRecoveryContractTest.kt").write_text('''package com.tianji.probabilitylab.nativev4.ai

import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class AiRuntimeRecoveryContractTest {
    private fun source(name: String): String = File(
        "src/main/java/com/tianji/probabilitylab/nativev4/ai/$name",
    ).readText()

    @Test
    fun chatFinalizesReasoningOnlyAndEmptyStreams() {
        val text = source("AiChatController.kt")
        assertTrue(text.contains("模型只返回了思考流"))
        assertTrue(text.contains("流式接口没有返回正文"))
        assertTrue(text.contains("finalizationDecision"))
        assertTrue(text.contains("rawContent.isBlank() && reasoning.isBlank()"))
        assertTrue(text.contains("listOf(\"reasoning_content\", \"reasoning\", \"thinking\")"))
        assertFalse(text.contains("error(\"模型没有返回可显示的流式回答\")"))
    }

    @Test
    fun formalForecastUsesOneBoundedSameModelClosure() {
        val text = source("AiAnalysis.kt")
        assertTrue(text.contains("isRetriableModelOutput(firstFailure)"))
        assertTrue(text.contains("同模型限时核心收口"))
        assertTrue(text.contains("effectiveTokenBudget"))
        assertTrue(text.contains("正式预测核心输出预算 4096 tokens"))
        assertFalse(text.contains("本次已停止，未自动重新预测"))
    }

    @Test
    fun deepSeekAutoForecastPrioritizesCompletion() {
        val text = source("AiReasoning.kt")
        assertTrue(text.contains("正式预测自动省时 · 对话保留思考"))
        assertTrue(text.contains("enableThinking = false"))
    }
}
''')

Path("RELEASE_NOTES_v5.7.2.md").write_text('''# 天机 v5.7.2

本次为 Android AI 运行时热修复：

- 修复 DeepSeek 流式对话只返回思考内容时直接报“没有可显示回答”的问题。
- 对话流没有正文时，自动使用同一模型关闭额外思考并进行一次普通正文收口。
- 兼容 `reasoning_content`、`reasoning` 与 `thinking` 三类思考流字段，但不向界面泄露隐藏思维链。
- DeepSeek 自动模式的正式预测优先生成核心矩阵；深入模式仍保留长思考。
- 正式预测超时或只产生不完整内容时，使用同一模型、同一份原始历史做一次有界核心收口，不更换模型、不改目标期。
- 正式预测输出预算改为有界核心预算，收到完整 position + scores 后立即结束。
- 版本号升级为 5.7.2，versionCode 39。
''')
