#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected one match, got {count}: {old[:120]!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


free_chat = ROOT / "app/src/main/java/com/tianji/probabilitylab/nativev4/ai/AiFreeChat.kt"
archive = ROOT / "app/src/main/java/com/tianji/probabilitylab/nativev4/ai/AiChatArchiveStore.kt"
controller = ROOT / "app/src/main/java/com/tianji/probabilitylab/nativev4/ai/AiChatController.kt"
gradle = ROOT / "app/build.gradle.kts"

replace_once(
    free_chat,
    "    val latencyMs: Long? = null,\n)\n\ndata class AiChatPrediction(",
    "    val latencyMs: Long? = null,\n    val positionScope: Int? = null,\n)\n\ndata class AiChatPrediction(",
)

replace_once(archive, '.put("schema", 3)', '.put("schema", 4)')
replace_once(
    archive,
    '        .put("latency_ms", message.latencyMs ?: JSONObject.NULL)\n',
    '        .put("latency_ms", message.latencyMs ?: JSONObject.NULL)\n'
    '        .put("position_scope", message.positionScope?.plus(1) ?: JSONObject.NULL)\n',
)
replace_once(
    archive,
    '                        latencyMs = item.optLong("latency_ms", -1L).takeIf { it >= 0L },\n',
    '                        latencyMs = item.optLong("latency_ms", -1L).takeIf { it >= 0L },\n'
    '                        positionScope = item.optInt("position_scope", 0)\n'
    '                            .takeIf { it in 1..10 }?.minus(1),\n',
)

replace_once(
    controller,
    '''        val plan = AiChatProtocol.planContext(session.messages, session.memorySummary)
        val previousMessages = if (intent == AiChatIntent.FREE_CHAT) {
            plan.messages.filter { it.role != AiChatRole.SYSTEM }.takeLast(16)
        } else {
            plan.messages
        }
''',
    '''        val plan = AiChatProtocol.planContext(session.messages, session.memorySummary)
        val activePosition = if (intent.usesLotteryContext) {
            AiPositionScope.resolve(text, plan.messages)
        } else {
            null
        }
        val rankScopedMessages = if (intent.usesLotteryContext) {
            AiPositionScope.filterPrevious(plan.messages, activePosition)
        } else {
            plan.messages
        }
        val previousMessages = if (intent == AiChatIntent.FREE_CHAT) {
            rankScopedMessages.filter { it.role != AiChatRole.SYSTEM }.takeLast(16)
        } else {
            rankScopedMessages
        }
''',
)
replace_once(
    controller,
    '''        val userMessage = AiChatMessage(
            role = AiChatRole.USER,
            content = text,
            targetPeriod = report.targetPeriod,
        )
        val assistantMessage = AiChatMessage(
            role = AiChatRole.ASSISTANT,
            content = "",
            targetPeriod = report.targetPeriod,
        )
''',
    '''        val userMessage = AiChatMessage(
            role = AiChatRole.USER,
            content = text,
            targetPeriod = report.targetPeriod,
            positionScope = activePosition,
        )
        val assistantMessage = AiChatMessage(
            role = AiChatRole.ASSISTANT,
            content = "",
            targetPeriod = report.targetPeriod,
            positionScope = activePosition,
        )
''',
)
replace_once(
    controller,
    '''        val requestedPosition = AiAdaptiveSignalEngine.extractRequestedPosition(text)
        // Never default an independent chat request to the native model's selected position.
        // The provisional position only drives the local status card; strict independent prompts
        // omit this learning context and compare all ten positions from raw history.
        val learningPosition = requestedPosition ?: session.prediction?.position ?: 0
''',
    '''        // The current turn's explicit rank is authoritative. A natural follow-up inherits the
        // most recent rank, while an all-rank request deliberately clears the scope.
        val learningPosition = activePosition ?: 0
''',
)
replace_once(
    controller,
    '''                    memorySummary = session.memorySummary,
                    question = text,
                    persona = persona,
                    judgementMode = judgementMode,
                    learningContext = learningContext,
                    intent = intent,
''',
    '''                    memorySummary = if (intent.usesLotteryContext && activePosition != null) {
                        ""
                    } else {
                        session.memorySummary
                    },
                    question = text,
                    persona = persona,
                    judgementMode = judgementMode,
                    learningContext = learningContext,
                    intent = intent,
                    positionScope = activePosition,
''',
)
replace_once(
    controller,
    '''                    onStreamText = { content ->
                        mainHandler.post {
                            if (generation.get() == token && session.isRunning) {
                                replaceMessage(assistantMessage.id) { current -> current.copy(content = content) }
                            }
                        }
                    },
''',
    '''                    onStreamText = { content ->
                        mainHandler.post {
                            if (
                                generation.get() == token && session.isRunning &&
                                (!intent.usesLotteryContext || activePosition == null)
                            ) {
                                replaceMessage(assistantMessage.id) { current -> current.copy(content = content) }
                            }
                        }
                    },
''',
)

replace_once(
    controller,
    '''        learningContext: JSONObject,
        intent: AiChatIntent,
        onProgress: (String) -> Unit,
''',
    '''        learningContext: JSONObject,
        intent: AiChatIntent,
        positionScope: Int?,
        onProgress: (String) -> Unit,
''',
)
replace_once(
    controller,
    '''                learningContext = learningContext,
                wantsPrediction = wantsPrediction,
            )
''',
    '''                learningContext = learningContext,
                wantsPrediction = wantsPrediction,
                positionScope = positionScope,
            )
''',
)
replace_once(
    controller,
    '''            intent = intent,
            expectedTargetPeriod = expectedTargetPeriod,
        )
''',
    '''            intent = intent,
            expectedTargetPeriod = expectedTargetPeriod,
            positionScope = positionScope,
        )
''',
)
replace_once(
    controller,
    '''        val prediction = if (wantsPrediction) AiChatProtocol.parsePrediction(rawContent) else null
        val content = AiTargetPeriodGuard.reconcilePredictionText(
            text = AiChatProtocol.visibleText(rawContent, prediction != null),
            expectedTargetPeriod = expectedTargetPeriod,
            isPrediction = wantsPrediction,
        )
        publisher.finish(content)
''',
    '''        val parsedPrediction = if (wantsPrediction) AiChatProtocol.parsePrediction(rawContent) else null
        val prediction = parsedPrediction?.let { value ->
            if (positionScope != null && value.position != positionScope) {
                value.copy(position = positionScope)
            } else {
                value
            }
        }
        val reconciled = AiTargetPeriodGuard.reconcilePredictionText(
            text = AiChatProtocol.visibleText(rawContent, prediction != null),
            expectedTargetPeriod = expectedTargetPeriod,
            isPrediction = wantsPrediction,
        )
        val verifiedFacts = if (intent.usesLotteryContext && positionScope != null) {
            AiVerifiedPositionEngine.calculate(snapshot, report, positionScope)
        } else {
            null
        }
        val content = AiVerifiedAnswerComposer.compose(reconciled, verifiedFacts, intent)
        publisher.finish(content)
''',
)

replace_once(
    controller,
    '''        learningContext: JSONObject,
        wantsPrediction: Boolean = AiChatProtocol.wantsPrediction(question),
    ): JSONObject {
''',
    '''        learningContext: JSONObject,
        wantsPrediction: Boolean = AiChatProtocol.wantsPrediction(question),
        positionScope: Int? = null,
    ): JSONObject {
''',
)
replace_once(
    controller,
    '''        val requestedPosition = extractPosition(question)
        val positions = requestedPosition?.let(::listOf) ?: (0 until 10).toList()
''',
    '''        val requestedPosition = positionScope ?: AiPositionScope.extract(question)
        val positions = requestedPosition?.let(::listOf) ?: (0 until 10).toList()
''',
)
replace_once(
    controller,
    '''            .put("latest_numbers", JSONArray(snapshot.latest.numbers))
            .put(
                "compact_history",
''',
    '''            .put("latest_numbers", JSONArray(snapshot.latest.numbers))
            .put(
                "verified_position_facts",
                JSONArray(positions.map { position ->
                    AiVerifiedPositionEngine.calculate(snapshot, report, position).toJson()
                }),
            )
            .put(
                "compact_history",
''',
)
replace_once(
    controller,
    '''                if (independent) {
                    "strict: no native selected position, candidates, matrix, factor weights or client precomputed statistics"
                } else {
''',
    '''                if (independent) {
                    "strict: no native selected position, candidates, matrix or factor weights; only deterministic facts recalculated from the current lottery snapshot"
                } else {
''',
)
replace_once(
    controller,
    '''                    put("independence_protocol", "raw-history-v1")
                    put(
                        "independent_analysis_rule",
                        "自行从原始历史提取特征并比较名次；不得猜测本机答案，也不得为了刻意不同而反向选择。",
                    )
''',
    '''                    put("independence_protocol", "raw-history-plus-client-verified-facts-v2")
                    put(
                        "independent_analysis_rule",
                        "verified_position_facts是客户端从当前彩种原始历史逐期计算的权威事实。只能解释和比较，禁止重算、改写或另造期号、序列、次数与遗漏。用户明确指定名次时只处理该名次；只有用户要求全名次比较时才比较十名。",
                    )
''',
)
replace_once(
    controller,
    '''    private fun extractPosition(question: String): Int? {
        val token = Regex("""第\\s*([一二三四五六七八九十0-9]{1,2})\\s*名""")
            .find(question)?.groupValues?.getOrNull(1) ?: return null
        val value = token.toIntOrNull() ?: when (token) {
            "一" -> 1; "二" -> 2; "三" -> 3; "四" -> 4; "五" -> 5
            "六" -> 6; "七" -> 7; "八" -> 8; "九" -> 9; "十" -> 10
            else -> return null
        }
        return (value - 1).takeIf { it in 0..9 }
    }
''',
    '''    private fun extractPosition(question: String): Int? = AiPositionScope.extract(question)
''',
)

replace_once(
    controller,
    '''        intent: AiChatIntent,
        expectedTargetPeriod: String,
    ): JSONArray = JSONArray().apply {
''',
    '''        intent: AiChatIntent,
        expectedTargetPeriod: String,
        positionScope: Int?,
    ): JSONArray = JSONArray().apply {
''',
)
replace_once(
    controller,
    '''                        "以下是当前开奖接口原始历史与必要元数据。独立模式不会包含本机候选、名次、概率矩阵或本机预计算统计；参考/反向模式才会明确附带native_model_reference：\\n${context}",
''',
    '''                        "以下是当前彩种开奖接口历史、必要元数据与客户端逐期核验事实。独立模式不包含本机候选、模型选中名次、概率矩阵或因子权重；verified_position_facts只来自当前彩种原始历史，必须原样遵守。参考/反向模式才会额外附带native_model_reference：\\n${context}",
''',
)
replace_once(
    controller,
    '''        if (intent.usesLotteryContext && expectedTargetPeriod.isNotBlank()) {
            put(
                JSONObject()
                    .put("role", "system")
                    .put(
                        "content",
                        AiTargetPeriodGuard.currentRequestInstruction(expectedTargetPeriod),
                    ),
            )
        }
        val currentQuestion = if (intent.usesLotteryContext && expectedTargetPeriod.isNotBlank()) {
            "【当前唯一目标期：${expectedTargetPeriod}期】\\n$question"
        } else {
            question
        }
''',
    '''        if (intent.usesLotteryContext && expectedTargetPeriod.isNotBlank()) {
            put(
                JSONObject()
                    .put("role", "system")
                    .put(
                        "content",
                        AiTargetPeriodGuard.currentRequestInstruction(expectedTargetPeriod),
                    ),
            )
        }
        if (intent.usesLotteryContext && positionScope != null) {
            put(
                JSONObject()
                    .put("role", "system")
                    .put(
                        "content",
                        "当前本轮唯一分析名次为第${positionScope + 1}名。客户端已排除其他名次的旧分析上下文；保持自然对话，但不得沿用、复制或混合此前其他名次的数据与结论。verified_position_facts是本轮唯一数值事实源。",
                    ),
            )
        }
        val currentQuestion = if (intent.usesLotteryContext && expectedTargetPeriod.isNotBlank()) {
            buildString {
                append("【当前唯一目标期：${expectedTargetPeriod}期】\\n")
                if (positionScope != null) append("【当前唯一分析名次：第${positionScope + 1}名】\\n")
                append(question)
            }
        } else {
            question
        }
''',
)
replace_once(
    controller,
    '''                AiJudgementMode.INDEPENDENT ->
                    "当前为严格独立模式：客户端只提供原始开奖历史，不提供本机选择的名次、候选、概率矩阵、因子权重或本机预计算统计。必须自行提取特征并比较十个名次；不得猜测本机答案，也不得为了显得不同而故意反选。"
''',
    '''                AiJudgementMode.INDEPENDENT ->
                    "当前为严格独立模式：客户端不提供本机候选、模型选择名次、概率矩阵或因子权重；但会提供由当前彩种原始历史逐期计算的verified_position_facts。用户明确指定名次时只分析该名次，用户要求全名次时才比较十名。不得改写核验事实，也不得为了显得不同而故意反选。"
''',
)
replace_once(
    controller,
    '''                    "独立模式只能引用客户端提供的原始开奖历史；参考/反向模式可额外使用明确标注的核验统计与本机参考。不得虚构期号、次数或数据来源。" +
''',
    '''                    "所有模式中的期号、最近序列、20/60/120期次数和遗漏只能引用verified_position_facts。禁止自行重算、补全、修改或生成另一套统计；正文只做定性解释，避免重复整张数字表。不得虚构期号、次数或数据来源。" +
''',
)

replace_once(gradle, '        versionCode = 56\n', '        versionCode = 57\n')
replace_once(gradle, '        versionName = "5.10.4"\n', '        versionName = "5.10.5"\n')

print("patched v5.10.5 rank context")
