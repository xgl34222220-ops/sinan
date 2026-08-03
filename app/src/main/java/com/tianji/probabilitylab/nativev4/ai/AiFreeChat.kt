package com.tianji.probabilitylab.nativev4.ai

import java.util.UUID
import kotlin.math.ceil

enum class AiChatRole {
    SYSTEM,
    USER,
    ASSISTANT,
}

enum class AiChatPersona(
    val id: String,
    val displayName: String,
    val description: String,
    val instruction: String,
    val quickPrompts: List<String>,
) {
    COMPREHENSIVE(
        id = "comprehensive",
        displayName = "综合研判",
        description = "综合真实历史、持续学习权重、遗漏、转移与状态变化",
        instruction = "综合使用20/60/120期频次、当前遗漏、收缩后继转移、短长窗口变化和持续学习档案。默认独立于本机候选；先给结论，再列最关键证据、策略变化和不确定性，避免只凭单一指标下结论。",
        quickPrompts = listOf(
            "综合分析第一名，给出下一期相对候选和主要依据",
            "上一期候选没有命中，复盘后调整这期的分析策略",
            "结合历史统计和本机模型，解释当前六码的优缺点",
        ),
    ),
    HISTORY(
        id = "history",
        displayName = "历史分析",
        description = "专注真实接口历史、频次、遗漏和样本窗口",
        instruction = "以历史统计审计员的方式回答。优先核对期数、窗口、次数、占比、遗漏和样本量；明确区分20期、60期和120期，发现样本不足或差异很小时必须指出。",
        quickPrompts = listOf(
            "分析第一名最近60期，哪些号码相对活跃？",
            "第一名1到10号最近20、60、120期分别出现多少次？",
            "查看第三名各号码当前遗漏多少期，并指出极端值",
        ),
    ),
    TREND(
        id = "trend",
        displayName = "走势研判",
        description = "比较短中长窗口的升温、降温与稳定性",
        instruction = "以走势研判员的方式回答。重点比较20期对60期、60期对120期的相对变化，识别升温、降温、震荡和稳定，但不得把短期波动描述成必然趋势。候选应同时考虑趋势强度和样本稳定性。",
        quickPrompts = listOf(
            "研判第一名最近20期相对60期的升温和降温号码",
            "比较十个名次的短期走势，哪个名次变化最明显？",
            "找出第一名短中长窗口方向一致的号码",
        ),
    ),
    OMISSION(
        id = "omission",
        displayName = "遗漏追踪",
        description = "追踪当前遗漏、回补节奏和过热风险",
        instruction = "以遗漏追踪员的方式回答。重点分析当前遗漏、历史出现节奏和近期密度，同时明确说明遗漏久不代表下一期必出，连续出现也不代表必然降温，避免赌徒谬误。",
        quickPrompts = listOf(
            "查看第一名当前遗漏最高和最低的号码",
            "第一名哪些号码近期密集出现，哪些号码长时间未出现？",
            "结合遗漏和频次给出第一名相对候选，但说明风险",
        ),
    ),
    TRANSITION(
        id = "transition",
        displayName = "转移分析",
        description = "分析当前号码之后历史上更常出现的后继号",
        instruction = "以后继转移分析员的方式回答。围绕当前号码，统计历史上下一期各号码的出现次数和样本总量；样本少时降低结论强度，并与总体频次对照，避免把偶然转移当规律。",
        quickPrompts = listOf(
            "第一名当前号码之后，历史上更常接哪些号？",
            "比较第一名后继转移和总体频次，哪些号码被明显高估或低估？",
            "分析第五名当前号码的历史后继分布和样本量",
        ),
    ),
    ADAPTIVE_LEARNING(
        id = "adaptive_learning",
        displayName = "自适应学习",
        description = "读取前向结算形成的长期权重，命中强化、未中纠偏",
        instruction = "把adaptive_learning视为可审计的长期策略记忆。必须比较本期信号与历史权重是否仍适用；连续未中时明确改变至少一个分析侧重点，禁止照搬上一期号码。",
        quickPrompts = listOf(
            "根据持续学习档案分析下一期，说明这次改变了什么策略",
            "复盘最近未中的原因，重新分配六类因子的侧重点",
            "用独立学习模式给出六码，并说明与上一期策略的不同",
        ),
    ),
    BAYES_BIG_DATA(
        id = "bayes_big_data",
        displayName = "贝叶斯大数据",
        description = "用收缩估计处理小样本，避免把偶然次数夸成趋势",
        instruction = "优先使用贝叶斯长窗频率和样本收缩。所有转移、遗漏和短窗结论都要结合样本量；差异不足时主动降低确定性，不得用1次对2次包装成强规律。",
        quickPrompts = listOf(
            "用贝叶斯收缩分析第六名，给出稳健六码",
            "比较最近20期与120期，但过滤小样本噪声",
            "哪些号码看似热门但经样本收缩后并不突出？",
        ),
    ),
    REGIME_STATE(
        id = "regime_state",
        displayName = "状态走势",
        description = "识别稳定、震荡、升温、降温和可能的状态切换",
        instruction = "分析短中长窗口方向、波动和状态变化。只有多窗口一致且样本充分时才称为趋势；出现冲突时优先保守候选并指出可能的状态切换。",
        quickPrompts = listOf(
            "分析十个名次的状态变化，选择信号最清晰的一名",
            "找出短中长窗口方向一致且波动较小的号码",
            "判断当前是稳定、震荡还是可能发生状态切换",
        ),
    ),
    UNIVERSAL_CONSENSUS(
        id = "universal_consensus",
        displayName = "万能码共识",
        description = "汇总多个独立信号的共同候选，不把名称当成必中承诺",
        instruction = "所谓万能码只表示贝叶斯、近期热度、遗漏、转移、状态和稳定性多个独立信号的共识池。必须列出支持数、冲突和边界号码；若共识弱，应明确说本期没有强万能码。",
        quickPrompts = listOf(
            "生成本期万能码共识池，并列出每个号码得到哪些信号支持",
            "找出六类信号共同支持最多的六码，同时标注冲突",
            "本期是否存在强共识？如果没有就直接说明没有",
        ),
    ),
    RISK_AUDIT(
        id = "risk_audit",
        displayName = "风险审计",
        description = "反向检查候选、样本偏差和过拟合风险",
        instruction = "以严格的风险审计员方式回答。主动寻找候选中的样本偏差、短窗过拟合、指标冲突、边界过小和本机模型不稳定之处；可以否定不可靠结论，并给出更保守的候选或建议继续观察。",
        quickPrompts = listOf(
            "审计当前第一名六码，哪些号码证据最弱？",
            "检查当前候选是否过度依赖最近20期",
            "从反方角度解释为什么这组候选可能失败",
        ),
    );

    companion object {
        fun fromId(id: String?): AiChatPersona =
            entries.firstOrNull { it.id == id } ?: COMPREHENSIVE
    }
}

data class AiChatMessage(
    val id: String = UUID.randomUUID().toString(),
    val role: AiChatRole,
    val content: String,
    val targetPeriod: String? = null,
    val createdAtEpochMs: Long = System.currentTimeMillis(),
    val latencyMs: Long? = null,
)

data class AiChatPrediction(
    val position: Int,
    val top6: List<Int>,
    val top7: List<Int>,
    val probabilities: List<Double>,
)

data class AiChatCandidateRecord(
    val id: String = UUID.randomUUID().toString(),
    val messageId: String,
    val targetPeriod: String,
    val prediction: AiChatPrediction,
    val actualNumber: Int? = null,
    val resolvedPeriod: String? = null,
    val createdAtEpochMs: Long = System.currentTimeMillis(),
)

data class AiChatArchive(
    val id: String,
    val lotteryKey: String,
    val profileId: String,
    val profileName: String,
    val model: String,
    val title: String = "新对话",
    val targetPeriod: String,
    val personaId: String = AiChatPersona.COMPREHENSIVE.id,
    val judgementMode: AiJudgementMode = AiJudgementMode.INDEPENDENT,
    val memorySummary: String = "",
    val continuationOf: String? = null,
    val messages: List<AiChatMessage> = emptyList(),
    val candidates: List<AiChatCandidateRecord> = emptyList(),
    val createdAtEpochMs: Long = System.currentTimeMillis(),
    val updatedAtEpochMs: Long = System.currentTimeMillis(),
)

data class AiChatArchiveSummary(
    val id: String,
    val lotteryKey: String,
    val profileId: String,
    val targetPeriod: String,
    val profileName: String,
    val model: String,
    val title: String,
    val preview: String,
    val personaId: String,
    val messageCount: Int,
    val hasPrediction: Boolean,
    val updatedAtEpochMs: Long,
)

data class AiChatSession(
    val archiveId: String = "",
    val lotteryKey: String = "",
    val profileId: String,
    val profileName: String = "",
    val model: String = "",
    val title: String = "新对话",
    val personaId: String = AiChatPersona.COMPREHENSIVE.id,
    val judgementMode: AiJudgementMode = AiJudgementMode.INDEPENDENT,
    val memorySummary: String = "",
    val continuationOf: String? = null,
    val messages: List<AiChatMessage> = emptyList(),
    val candidates: List<AiChatCandidateRecord> = emptyList(),
    val isRunning: Boolean = false,
    val progress: String = "",
    val error: String? = null,
    val prediction: AiChatPrediction? = null,
    val targetPeriod: String? = null,
    val streamingMessageId: String? = null,
    val isReadOnlyArchive: Boolean = false,
    val contextUsagePercent: Int = 0,
    val rolloverNotice: String? = null,
    val learningProfile: AiLearningProfile = AiLearningProfile(),
    val createdAtEpochMs: Long = System.currentTimeMillis(),
    val updatedAtEpochMs: Long = System.currentTimeMillis(),
)

data class AiChatReply(
    val content: String,
    val prediction: AiChatPrediction?,
    val latencyMs: Long,
    val responseId: String,
    val reasoningTokens: Int?,
    val reasoningVerified: Boolean,
)

data class AiChatContextPlan(
    val messages: List<AiChatMessage>,
    val estimatedTokens: Int,
    val safeBudgetTokens: Int,
    val shouldRollover: Boolean,
) {
    val usagePercent: Int = ((estimatedTokens * 100.0) / safeBudgetTokens)
        .toInt().coerceIn(0, 100)
}

object AiChatConversationId {
    fun newId(lotteryKey: String, profileId: String, model: String): String =
        listOf(lotteryKey.trim(), profileId.trim(), model.trim(), UUID.randomUUID().toString())
            .joinToString("\u001F")
}

/** Kept only for decoding v1 period archives. New conversations use random stable IDs. */
object AiChatArchiveId {
    fun of(lotteryKey: String, targetPeriod: String, profileId: String, model: String): String =
        listOf(lotteryKey, targetPeriod, profileId, model).joinToString("\u001F") { it.trim() }
}

object AiChatProtocol {
    private const val SAFE_CONTEXT_TOKENS = 18_000
    private const val ROLLOVER_MESSAGES = 72
    private const val MEMORY_LIMIT = 5_500
    private val predictionTerms = listOf(
        "预测", "预判", "候选", "六码", "七码", "号码", "出号", "推荐", "名次",
        "position", "scores", "forecast", "pick",
    )
    private val strategyTerms = listOf(
        "没中", "未中", "命中", "调整", "策略", "降低", "提高", "保留", "排除",
        "权重", "复盘", "偏重", "不要", "继续", "改成",
    )

    fun wantsPrediction(text: String): Boolean {
        val normalized = text.trim().lowercase()
        return predictionTerms.any(normalized::contains)
    }

    fun estimateTokens(text: String): Int {
        if (text.isBlank()) return 0
        val cjk = text.count { it.code in 0x2E80..0x9FFF }
        val other = text.length - cjk
        return ceil(cjk * 0.95 + other * 0.28).toInt().coerceAtLeast(1)
    }

    fun planContext(
        messages: List<AiChatMessage>,
        memorySummary: String,
        safeBudgetTokens: Int = SAFE_CONTEXT_TOKENS,
    ): AiChatContextPlan {
        val clean = messages.filter { it.content.isNotBlank() }
        val total = estimateTokens(memorySummary) + clean.sumOf { estimateTokens(it.content) }
        val available = (safeBudgetTokens - estimateTokens(memorySummary) - 1_800).coerceAtLeast(2_000)
        var used = 0
        val kept = ArrayDeque<AiChatMessage>()
        clean.asReversed().forEach { message ->
            val cost = estimateTokens(message.content) + 8
            if (kept.isNotEmpty() && used + cost > available) return@forEach
            kept.addFirst(message)
            used += cost
        }
        return AiChatContextPlan(
            messages = kept.toList(),
            estimatedTokens = total,
            safeBudgetTokens = safeBudgetTokens,
            shouldRollover = total >= (safeBudgetTokens * 0.86).toInt() || clean.size >= ROLLOVER_MESSAGES,
        )
    }

    fun buildConversationTitle(firstQuestion: String): String = firstQuestion
        .replace(Regex("\\s+"), " ")
        .trim()
        .take(22)
        .ifBlank { "新对话" }

    fun buildMemorySummary(
        previousSummary: String,
        messages: List<AiChatMessage>,
        candidates: List<AiChatCandidateRecord>,
    ): String {
        val feedback = messages
            .filter { it.role == AiChatRole.USER && strategyTerms.any(it.content::contains) }
            .takeLast(14)
            .joinToString("\n") { "- ${it.content.replace(Regex("\\s+"), " ").take(240)}" }
        val recent = messages
            .filter { it.role != AiChatRole.SYSTEM }
            .takeLast(12)
            .joinToString("\n") { message ->
                val role = if (message.role == AiChatRole.USER) "用户" else "助手"
                "$role：${message.content.replace(Regex("\\s+"), " ").take(260)}"
            }
        val candidateDigest = candidates.takeLast(8).joinToString("\n") { record ->
            buildString {
                append("- 目标期${record.targetPeriod} 第${record.prediction.position + 1}名 ")
                append("六码${record.prediction.top6.joinToString("/")}")
                record.actualNumber?.let { actual ->
                    append("，实际$actual，")
                    append(if (actual in record.prediction.top6) "六码命中" else "六码未中")
                }
            }
        }
        return buildString {
            appendLine("长期对话记忆（仅用于延续用户明确表达的分析偏好，不代表模型已训练）：")
            if (previousSummary.isNotBlank()) {
                appendLine(previousSummary.take(1_600))
            }
            if (feedback.isNotBlank()) {
                appendLine("用户的策略反馈：")
                appendLine(feedback)
            }
            if (candidateDigest.isNotBlank()) {
                appendLine("近期候选与开奖核验：")
                appendLine(candidateDigest)
            }
            if (recent.isNotBlank()) {
                appendLine("最近对话摘要：")
                append(recent)
            }
        }.take(MEMORY_LIMIT)
    }

    fun parsePrediction(text: String): AiChatPrediction? {
        val canonical = AiForecastPayloadExtractor.salvageCoreJson(text) ?: return null
        val position = Regex("\\\"position\\\":(10|[1-9])")
            .find(canonical)?.groupValues?.getOrNull(1)?.toIntOrNull() ?: return null
        val scoreText = Regex("\\\"scores\\\":\\[([^]]+)]")
            .find(canonical)?.groupValues?.getOrNull(1) ?: return null
        val scores = scoreText.split(',').mapNotNull { it.trim().toDoubleOrNull() }
        if (scores.size != 10 || scores.any { !it.isFinite() || it < 0.0 }) return null
        val sum = scores.sum()
        if (!sum.isFinite() || sum <= 0.0) return null
        val probabilities = scores.map { it / sum }
        val ranking = probabilities.indices
            .sortedWith(compareByDescending<Int> { probabilities[it] }.thenBy { it })
            .map { it + 1 }
        return AiChatPrediction(
            position = position - 1,
            top6 = ranking.take(6),
            top7 = ranking.take(7),
            probabilities = probabilities,
        )
    }

    fun visibleText(text: String, hasPrediction: Boolean): String {
        var value = text.trim()
        value = value.replace(Regex("(?s)<tianji_forecast>.*?</tianji_forecast>"), "").trim()
        if (hasPrediction) {
            AiForecastPayloadExtractor.balancedJsonObjects(value)
                .firstOrNull { AiForecastPayloadExtractor.salvageCoreJson(it) != null }
                ?.let { value = value.replace(it, "").trim() }
        }
        value = value
            .replace(Regex("(?s)```json\\s*```"), "")
            .replace(Regex("\\n{3,}"), "\n\n")
            .trim()
        return value.ifBlank {
            if (hasPrediction) "已根据你的要求生成结构化候选结果。" else "模型已完成本次分析。"
        }
    }

    fun visibleStreamingText(text: String): String {
        val markerIndex = text.indexOf("<tianji_forecast>", ignoreCase = true)
        val visible = if (markerIndex >= 0) text.substring(0, markerIndex) else text
        return visible
            .replace(Regex("(?s)```json.*$"), "")
            .replace(Regex("\\n{3,}"), "\n\n")
            .trimStart()
    }

    fun trimHistory(messages: List<AiChatMessage>, maxMessages: Int = 36): List<AiChatMessage> =
        messages.filter { it.content.isNotBlank() }.takeLast(maxMessages.coerceAtLeast(1))
}
