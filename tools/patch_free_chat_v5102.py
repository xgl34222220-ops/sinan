#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTROLLER = ROOT / "app/src/main/java/com/tianji/probabilitylab/nativev4/ai/AiChatController.kt"
BUILD = ROOT / "app/build.gradle.kts"
TEST = ROOT / "app/src/test/java/com/tianji/probabilitylab/nativev4/ai/AiChatIntentRouterTest.kt"
NOTES = ROOT / "RELEASE_NOTES_v5.10.2.md"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


text = CONTROLLER.read_text(encoding="utf-8")

text = replace_once(
    text,
    """        latestPeriod: String? = null,\n        latestNumbers: List<Int> = emptyList(),\n    ) {""",
    """        latestPeriod: String? = null,\n        latestNumbers: List<Int> = emptyList(),\n        announceTargetTransition: Boolean = true,\n    ) {""",
    "selectContext signature",
)
text = replace_once(
    text,
    """        syncTargetTransition(normalizedTarget, latestPeriod, latestNumbers)\n    }""",
    """        if (announceTargetTransition) {\n            syncTargetTransition(normalizedTarget, latestPeriod, latestNumbers)\n        } else if (normalizedTarget.isNotBlank() && session.targetPeriod != normalizedTarget) {\n            session = session.copy(targetPeriod = normalizedTarget)\n        }\n    }""",
    "silent target transition",
)
text = replace_once(
    text,
    """        if (AiChatProtocol.wantsPrediction(text)) {\n            AiPredictionFreshnessGuard.error(snapshot, report)?.let { message ->""",
    """        val intent = AiChatIntentRouter.resolve(text)\n        AiChatProtocol.wantsPrediction(if (intent.wantsPrediction) text else \"\")\n        if (intent.wantsPrediction) {\n            AiPredictionFreshnessGuard.error(snapshot, report)?.let { message ->""",
    "send intent",
)
text = replace_once(
    text,
    """        val activeModel = session.model.ifBlank { config.model }.trim()\n        settleCandidates(snapshot)\n        selectContext(""",
    """        val activeModel = session.model.ifBlank { config.model }.trim()\n        if (intent.usesLotteryContext) settleCandidates(snapshot)\n        selectContext(""",
    "conditional candidate settlement",
)
text = replace_once(
    text,
    """            latestPeriod = snapshot.latest.period,\n            latestNumbers = snapshot.latest.numbers,\n        )""",
    """            latestPeriod = snapshot.latest.period,\n            latestNumbers = snapshot.latest.numbers,\n            announceTargetTransition = intent.usesLotteryContext,\n        )""",
    "selectContext intent",
)
text = replace_once(
    text,
    """        val plan = AiChatProtocol.planContext(session.messages, session.memorySummary)\n        val previousMessages = plan.messages""",
    """        val plan = AiChatProtocol.planContext(session.messages, session.memorySummary)\n        val previousMessages = if (intent == AiChatIntent.FREE_CHAT) {\n            plan.messages.filter { it.role != AiChatRole.SYSTEM }.takeLast(16)\n        } else {\n            plan.messages\n        }""",
    "free chat history",
)
text = replace_once(
    text,
    """        val learningProfile = learningStore.profile(\n            snapshot.lottery.apiKey,\n            config.id,\n            learningStrategy,\n            learningPosition,\n        )\n        val learningContext = learningStore.snapshot(\n            snapshot.history,\n            snapshot.lottery.apiKey,\n            config.id,\n            learningStrategy,\n            learningPosition,\n        )""",
    """        val learningProfile = if (intent.usesLotteryContext) {\n            learningStore.profile(\n                snapshot.lottery.apiKey,\n                config.id,\n                learningStrategy,\n                learningPosition,\n            )\n        } else {\n            session.learningProfile\n        }\n        val learningContext = if (intent.usesLotteryContext) {\n            learningStore.snapshot(\n                snapshot.history,\n                snapshot.lottery.apiKey,\n                config.id,\n                learningStrategy,\n                learningPosition,\n            )\n        } else {\n            JSONObject()\n        }""",
    "conditional learning context",
)
text = replace_once(
    text,
    """            isRunning = true,\n            progress = \"正在整理当前接口历史…\",""",
    """            isRunning = true,\n            progress = when (intent) {\n                AiChatIntent.FREE_CHAT -> \"正在回复…\"\n                AiChatIntent.LOTTERY_ANALYSIS -> \"正在读取开奖历史…\"\n                AiChatIntent.LOTTERY_PREDICTION -> \"正在分析本期候选…\"\n            },""",
    "initial progress",
)
text = replace_once(
    text,
    """                    learningContext = learningContext,\n                    onProgress = { progress ->""",
    """                    learningContext = learningContext,\n                    intent = intent,\n                    onProgress = { progress ->""",
    "client intent",
)
text = replace_once(
    text,
    """                        session = session.copy(\n                            isRunning = false,\n                            progress = if (reply.reasoningVerified) {\n                                reply.reasoningTokens?.let { \"回答完成 · 推理 $it tokens\" }\n                                    ?: \"回答完成 · 已验证模型思考\"\n                            } else {\n                                \"回答完成\"\n                            } + \" · 已学习 ${resolvedLearning.settled} 期\",""",
    """                        val completion = if (reply.reasoningVerified && intent != AiChatIntent.FREE_CHAT) {\n                            reply.reasoningTokens?.let { \"回答完成 · 推理 $it tokens\" }\n                                ?: \"回答完成 · 已验证模型思考\"\n                        } else {\n                            \"回答完成\"\n                        }\n                        session = session.copy(\n                            isRunning = false,\n                            progress = if (intent.usesLotteryContext) {\n                                \"$completion · 已学习 ${resolvedLearning.settled} 期\"\n                            } else {\n                                completion\n                            },""",
    "completion progress",
)
text = replace_once(
    text,
    """                            error = AiErrorMessages.userFacing(cause, \"对话分析失败\"),""",
    """                            error = AiErrorMessages.userFacing(\n                                cause,\n                                if (intent == AiChatIntent.FREE_CHAT) \"对话失败\" else \"对话分析失败\",\n                            ),""",
    "free chat error",
)
text = replace_once(
    text,
    """                append(if (actual in candidate.prediction.top6) \"上期六码命中\" else \"上期六码未中\")""",
    """                val candidateCount = candidate.prediction.top6.size.coerceAtLeast(1)\n                append(\n                    if (actual in candidate.prediction.top6) {\n                        \"上期${candidateCount}码命中\"\n                    } else {\n                        \"上期${candidateCount}码未中\"\n                    },\n                )""",
    "dynamic candidate count",
)
text = replace_once(
    text,
    """        judgementMode: AiJudgementMode,\n        learningContext: JSONObject,\n    ): JSONObject {""",
    """        judgementMode: AiJudgementMode,\n        learningContext: JSONObject,\n        wantsPrediction: Boolean = AiChatProtocol.wantsPrediction(question),\n    ): JSONObject {""",
    "context builder signature",
)
text = replace_once(
    text,
    """        require(verifiedHistory.isNotEmpty()) { \"没有可用于对话分析的接口历史\" }\n        val wantsPrediction = AiChatProtocol.wantsPrediction(question)\n        val requestedPosition = extractPosition(question)""",
    """        require(verifiedHistory.isNotEmpty()) { \"没有可用于对话分析的接口历史\" }\n        val requestedPosition = extractPosition(question)""",
    "context builder intent",
)
text = replace_once(
    text,
    """        learningContext: JSONObject,\n        onProgress: (String) -> Unit,""",
    """        learningContext: JSONObject,\n        intent: AiChatIntent,\n        onProgress: (String) -> Unit,""",
    "remote chat signature",
)
text = replace_once(
    text,
    """        val started = System.currentTimeMillis()\n        val wantsPrediction = AiChatProtocol.wantsPrediction(question)\n        val context = AiChatContextBuilder.build(\n            snapshot, report, question, judgementMode, learningContext,\n        )\n        val decision = AiReasoningEngine.resolve(config)""",
    """        val started = System.currentTimeMillis()\n        val wantsPrediction = intent.wantsPrediction\n        AiChatProtocol.wantsPrediction(if (wantsPrediction) question else \"\")\n        val context = if (intent.usesLotteryContext) {\n            AiChatContextBuilder.build(\n                snapshot = snapshot,\n                report = report,\n                question = question,\n                judgementMode = judgementMode,\n                learningContext = learningContext,\n                wantsPrediction = wantsPrediction,\n            )\n        } else {\n            null\n        }\n        val decision = decisionFor(config, intent)""",
    "remote intent setup",
)
text = replace_once(
    text,
    """            judgementMode = judgementMode,\n        )""",
    """            judgementMode = judgementMode,\n            intent = intent,\n        )""",
    "conversation intent",
)
# Add intent to every request body invocation in RemoteAiChatClient.
text = text.replace(
    """                wantsPrediction = wantsPrediction,\n            )""",
    """                wantsPrediction = wantsPrediction,\n                intent = intent,\n            )""",
)
text = text.replace(
    """                        wantsPrediction = wantsPrediction,\n                    ),""",
    """                        wantsPrediction = wantsPrediction,\n                        intent = intent,\n                    ),""",
)
text = text.replace(
    """                    wantsPrediction = wantsPrediction,\n                ),""",
    """                    wantsPrediction = wantsPrediction,\n                    intent = intent,\n                ),""",
)
# Add intent to transport calls and timeouts.
text = text.replace("timeoutMs = timeoutFor(activeDecision),", "timeoutMs = timeoutFor(activeDecision, intent),")
text = text.replace(
    """                    onProgress = onProgress,\n                    publisher = publisher,""",
    """                    onProgress = onProgress,\n                    publisher = publisher,\n                    intent = intent,""",
)
text = text.replace(
    """                    timeoutMs = 45_000,\n                    onProgress = onProgress,\n                    publisher = publisher,""",
    """                    timeoutMs = if (intent == AiChatIntent.FREE_CHAT) 20_000 else 45_000,\n                    onProgress = onProgress,\n                    publisher = publisher,\n                    intent = intent,""",
)
text = replace_once(
    text,
    """        onProgress(\"正在连接 ${config.displayName} · ${persona.displayName}…\")""",
    """        onProgress(\n            if (intent == AiChatIntent.FREE_CHAT) {\n                \"正在连接 ${config.displayName}…\"\n            } else {\n                \"正在连接 ${config.displayName} · ${persona.displayName}…\"\n            },\n        )""",
    "connection progress",
)
text = replace_once(
    text,
    """        onProgress(if (response.optBoolean(\"_tianji_stream_interrupted\")) {\n            \"网络中断后已恢复现有回答，正在整理候选卡片…\"\n        } else {\n            \"回答完成，正在整理候选卡片…\"\n        })""",
    """        onProgress(\n            when {\n                response.optBoolean(\"_tianji_stream_interrupted\") && wantsPrediction ->\n                    \"网络中断后已恢复现有回答，正在整理候选卡片…\"\n                response.optBoolean(\"_tianji_stream_interrupted\") ->\n                    \"网络中断后已恢复现有回答…\"\n                wantsPrediction -> \"回答完成，正在整理候选卡片…\"\n                else -> \"回答完成…\"\n            },\n        )""",
    "finish progress",
)
text = replace_once(
    text,
    """        context: JSONObject,\n        previousMessages: List<AiChatMessage>,""",
    """        context: JSONObject?,\n        previousMessages: List<AiChatMessage>,""",
    "nullable context",
)
text = replace_once(
    text,
    """        persona: AiChatPersona,\n        judgementMode: AiJudgementMode,\n    ): JSONArray = JSONArray().apply {""",
    """        persona: AiChatPersona,\n        judgementMode: AiJudgementMode,\n        intent: AiChatIntent,\n    ): JSONArray = JSONArray().apply {""",
    "conversation signature",
)
text = replace_once(
    text,
    """                .put(\"role\", \"system\")\n                .put(\"content\", systemPrompt(wantsPrediction, persona, judgementMode)),\n        )\n        put(\n            JSONObject()\n                .put(\"role\", \"user\")\n                .put(\n                    \"content\",\n                    \"以下是当前开奖接口原始历史与必要元数据。独立模式不会包含本机候选、名次、概率矩阵或本机预计算统计；参考/反向模式才会明确附带native_model_reference：\\n${context}\",\n                ),\n        )\n        if (memorySummary.isNotBlank()) {""",
    """                .put(\"role\", \"system\")\n                .put(\"content\", systemPrompt(intent, persona, judgementMode)),\n        )\n        if (context != null) {\n            put(\n                JSONObject()\n                    .put(\"role\", \"user\")\n                    .put(\n                        \"content\",\n                        \"以下是当前开奖接口原始历史与必要元数据。独立模式不会包含本机候选、名次、概率矩阵或本机预计算统计；参考/反向模式才会明确附带native_model_reference：\\n${context}\",\n                    ),\n            )\n        }\n        if (intent.usesLotteryContext && memorySummary.isNotBlank()) {""",
    "conditional context message",
)
text = replace_once(
    text,
    """        previousMessages.filter { it.content.isNotBlank() }.forEach { message ->""",
    """        previousMessages\n            .filter { it.content.isNotBlank() }\n            .filter { intent.usesLotteryContext || it.role != AiChatRole.SYSTEM }\n            .forEach { message ->""",
    "filter system history",
)
start = text.index("    private fun systemPrompt(\n")
end = text.index("    private fun requestBody(\n", start)
new_system_prompt = '''    private fun systemPrompt(\n        intent: AiChatIntent,\n        persona: AiChatPersona,\n        judgementMode: AiJudgementMode,\n    ): String {\n        if (intent == AiChatIntent.FREE_CHAT) {\n            return \"你是天机 App 内置的通用 AI 助手。优先理解用户当前真正想表达的内容，像正常聊天助手一样自然回答。\" +\n                \"普通问候用一两句话快速回应，也可以回答日常、软件使用和通用知识问题。\" +\n                \"除非用户明确提出开奖、走势、历史分析或预测请求，否则禁止主动谈彩票、期号、候选号码、命中率或复盘，\" +\n                \"更不能把“你好”等普通对话理解成预测命令。使用简体中文，直接回答，不输出隐藏思维链。\"\n        }\n        return buildString {\n            val judgementInstruction = when (judgementMode) {\n                AiJudgementMode.INDEPENDENT ->\n                    \"当前为严格独立模式：客户端只提供原始开奖历史，不提供本机选择的名次、候选、概率矩阵、因子权重或本机预计算统计。必须自行提取特征并比较十个名次；不得猜测本机答案，也不得为了显得不同而故意反选。\"\n                AiJudgementMode.NATIVE_REFERENCE ->\n                    \"当前为参考本机模式：native_model_reference只是一份可质疑参考，必须独立计算并在不同时坚持自己的结论。\"\n                AiJudgementMode.CONTRARIAN ->\n                    \"当前为反向审计模式：优先寻找native_model_reference中的薄弱号码、样本偏差和替代方案，不得简单赞同。\"\n            }\n            append(\n                \"你是天机内置的开奖记录分析助手，当前分析人设为【${persona.displayName}】。\" +\n                    \"人设要求：${persona.instruction}\" + judgementInstruction +\n                    \"adaptive_learning由客户端根据此前真实前向开奖结果逐期更新，包含学习期数、命中率、连续未中、六类因子权重和最近策略变化。\" +\n                    \"上一期未中或连续未中时，必须重新检查因子是否失效，并明确说明本期改变了什么；禁止机械复制旧候选。\" +\n                    \"使用简体中文直接、自然地回答，只处理用户当前提出的问题。\" +\n                    \"独立模式只能引用客户端提供的原始开奖历史；参考/反向模式可额外使用明确标注的核验统计与本机参考。不得虚构期号、次数或数据来源。\" +\n                    \"所有转移、遗漏和趋势结论必须同时说明样本强弱；1次与2次之类的小差异不得包装成强规律。\" +\n                    \"用户说出现几率大时，应解释为历史样本中的相对频次或模型相对评分，不得称为真实中奖概率。\" +\n                    \"不要输出隐藏思维链，不得承诺必中、盈利或准确率。证据接近时明确说差异小或没有强候选。\" +\n                    \"回答先给结论，再给关键依据、策略变化和不确定性，不要堆砌无关术语。\",\n            )\n            if (intent == AiChatIntent.LOTTERY_PREDICTION) {\n                append(\n                    \"用户本次明确要求候选或预测。正文先给简洁依据与本期策略变化，随后追加且只追加一个\" +\n                        \"<tianji_forecast>{\\\"position\\\":1至10整数,\\\"scores\\\":[按号码1至10排列的10项非负评分],\" +\n                        \"\\\"strategy_weights\\\":[与六类因子顺序一致的6项非负权重],\\\"strategy_note\\\":\\\"不超过60字的本期策略变化\\\"}</tianji_forecast>。\" +\n                        \"scores必须来自本次独立比较，避免无依据并列。\",\n                )\n            } else {\n                append(\"用户本次只要求解释或分析，不是候选预测请求。禁止主动输出候选号码、六码、七码或tianji_forecast。\")\n            }\n        }\n    }\n\n'''
text = text[:start] + new_system_prompt + text[end:]
text = replace_once(
    text,
    """        stream: Boolean,\n        wantsPrediction: Boolean,\n    ): JSONObject = JSONObject().apply {""",
    """        stream: Boolean,\n        wantsPrediction: Boolean,\n        intent: AiChatIntent,\n    ): JSONObject = JSONObject().apply {""",
    "request body signature",
)
text = replace_once(
    text,
    """        if (config.provider != AiProvider.COMPATIBLE) {\n            val outputBudget = when {\n                decision.expectsReasoning && wantsPrediction -> 8_192\n                decision.expectsReasoning -> 6_144\n                wantsPrediction -> 4_096\n                else -> 2_048\n            }\n            put(if (responsesApi) \"max_output_tokens\" else \"max_tokens\", outputBudget)\n        }""",
    """        val outputBudget = when {\n            intent == AiChatIntent.FREE_CHAT -> 768\n            decision.expectsReasoning && wantsPrediction -> 8_192\n            decision.expectsReasoning -> 6_144\n            wantsPrediction -> 4_096\n            else -> 2_048\n        }\n        if (intent == AiChatIntent.FREE_CHAT || config.provider != AiProvider.COMPATIBLE) {\n            put(if (responsesApi) \"max_output_tokens\" else \"max_tokens\", outputBudget)\n        }""",
    "output budget",
)
text = replace_once(
    text,
    """        if (!decision.expectsReasoning && decision.protocol != AiReasoningProtocol.OPENAI) {\n            put(\"temperature\", 0.2)\n        }""",
    """        if (!decision.expectsReasoning && decision.protocol != AiReasoningProtocol.OPENAI) {\n            put(\"temperature\", if (intent == AiChatIntent.FREE_CHAT) 0.65 else 0.2)\n        }""",
    "temperature",
)
insert_at = text.index("    private fun requestBody(\n")
decision_helper = '''    private fun decisionFor(config: AiConfig, intent: AiChatIntent): AiReasoningDecision {\n        val resolved = AiReasoningEngine.resolve(config)\n        if (intent != AiChatIntent.FREE_CHAT) return resolved\n        return when (resolved.protocol) {\n            AiReasoningProtocol.DEEPSEEK,\n            AiReasoningProtocol.OPENROUTER,\n            AiReasoningProtocol.ENABLE_THINKING,\n            -> resolved.copy(\n                preference = AiReasoningMode.LOW,\n                sendControl = true,\n                enableThinking = false,\n                effort = null,\n                displayLabel = \"快速对话 · 已关闭长思考\",\n            )\n            AiReasoningProtocol.OPENAI,\n            AiReasoningProtocol.AUTO,\n            AiReasoningProtocol.NONE,\n            -> resolved.copy(\n                preference = AiReasoningMode.LOW,\n                sendControl = false,\n                enableThinking = false,\n                effort = null,\n                displayLabel = \"快速对话\",\n            )\n        }\n    }\n\n'''
text = text[:insert_at] + decision_helper + text[insert_at:]
text = replace_once(
    text,
    """        timeoutMs: Int,\n        onProgress: (String) -> Unit,\n        publisher: VisibleStreamPublisher,\n    ): JSONObject {\n        var lastFailure: Throwable? = null\n        repeat(2) { attempt ->""",
    """        timeoutMs: Int,\n        onProgress: (String) -> Unit,\n        publisher: VisibleStreamPublisher,\n        intent: AiChatIntent,\n    ): JSONObject {\n        var lastFailure: Throwable? = null\n        repeat(if (intent == AiChatIntent.FREE_CHAT) 1 else 2) { attempt ->""",
    "execute signature",
)
text = replace_once(
    text,
    """                onProgress(\n                    if (request.optBoolean(\"stream\", false)) {\n                        \"模型正在分析，回答开始后会实时显示…\"\n                    } else {\n                        \"模型正在分析，完成后将分段显示…\"\n                    },\n                )""",
    """                onProgress(\n                    when {\n                        intent == AiChatIntent.FREE_CHAT && request.optBoolean(\"stream\", false) ->\n                            \"正在回复，内容会实时显示…\"\n                        intent == AiChatIntent.FREE_CHAT -> \"正在回复…\"\n                        request.optBoolean(\"stream\", false) ->\n                            \"模型正在分析，回答开始后会实时显示…\"\n                        else -> \"模型正在分析，完成后将分段显示…\"\n                    },\n                )""",
    "transport progress",
)
text = replace_once(
    text,
    """                if (attempt == 0 && (code == 429 || code in 500..599)) {""",
    """                if (intent != AiChatIntent.FREE_CHAT && attempt == 0 && (code == 429 || code in 500..599)) {""",
    "server retry",
)
text = replace_once(
    text,
    """                if (attempt == 0 && !deliveredVisibleText) {""",
    """                if (intent != AiChatIntent.FREE_CHAT && attempt == 0 && !deliveredVisibleText) {""",
    "timeout retry",
)
text = replace_once(
    text,
    """    private fun timeoutFor(decision: AiReasoningDecision): Int = when {\n        decision.preference == AiReasoningMode.HIGH -> 120_000\n        decision.expectsReasoning -> 90_000\n        else -> 60_000\n    }""",
    """    private fun timeoutFor(decision: AiReasoningDecision, intent: AiChatIntent): Int = when {\n        intent == AiChatIntent.FREE_CHAT -> 30_000\n        decision.preference == AiReasoningMode.HIGH -> 120_000\n        decision.expectsReasoning -> 90_000\n        else -> 60_000\n    }""",
    "intent timeout",
)

CONTROLLER.write_text(text, encoding="utf-8")

build = BUILD.read_text(encoding="utf-8")
build = replace_once(build, 'versionCode = 53', 'versionCode = 54', 'version code')
build = replace_once(build, 'versionName = "5.10.1"', 'versionName = "5.10.2"', 'version name')
BUILD.write_text(build, encoding="utf-8")

TEST.parent.mkdir(parents=True, exist_ok=True)
TEST.write_text(
    '''package com.tianji.probabilitylab.nativev4.ai\n\nimport org.junit.Assert.assertEquals\nimport org.junit.Test\n\nclass AiChatIntentRouterTest {\n    @Test\n    fun greetingUsesFastFreeChat() {\n        assertEquals(AiChatIntent.FREE_CHAT, AiChatIntentRouter.resolve("你好"))\n        assertEquals(AiChatIntent.FREE_CHAT, AiChatIntentRouter.resolve("你是谁，能做什么"))\n    }\n\n    @Test\n    fun explanationDoesNotBecomeAnotherPrediction() {\n        assertEquals(\n            AiChatIntent.LOTTERY_ANALYSIS,\n            AiChatIntentRouter.resolve("为什么刚才给了六个号码？解释一下"),\n        )\n        assertEquals(\n            AiChatIntent.LOTTERY_ANALYSIS,\n            AiChatIntentRouter.resolve("分析最近走势，不要给号码"),\n        )\n    }\n\n    @Test\n    fun explicitCandidateRequestUsesPredictionMode() {\n        assertEquals(\n            AiChatIntent.LOTTERY_PREDICTION,\n            AiChatIntentRouter.resolve("告诉我下一期最有可能开出的两个号码"),\n        )\n        assertEquals(\n            AiChatIntent.LOTTERY_PREDICTION,\n            AiChatIntentRouter.resolve("六码里重点看两个号码"),\n        )\n    }\n}\n''',
    encoding="utf-8",
)

NOTES.write_text(
    '''# 天机 v5.10.2\n\n## AI 自由对话修复\n\n- 普通问候和日常问题进入快速自由对话，不再加载开奖历史或主动输出预测号码。\n- “你好”“你是谁”等普通消息关闭可控长思考，减少无意义等待。\n- 开奖解释、走势分析和候选预测分为三种意图，仅明确预测请求才生成候选卡片。\n- 用户只要求解释或复盘时，禁止模型擅自追加六码、七码或下一期预测。\n- 自由对话只携带必要的最近聊天记录，不再注入期次系统消息和长期预测记忆。\n- 预测与复盘仍保留真实开奖历史、学习状态和结构化候选校验。\n\n## 稳定性\n\n- 自由对话输出预算和超时单独收紧，避免简单消息长时间重试。\n- 修复期次衔接提示固定写成“六码命中/未中”的问题，改为显示实际候选数量。\n- 增加问候、解释和明确候选请求的意图路由测试。\n''',
    encoding="utf-8",
)

print("v5.10.2 free chat patch applied")
