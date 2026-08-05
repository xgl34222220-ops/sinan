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
        displayName = "大数据规律",
        description = "多窗口频率、遗漏、转移、贝叶斯收缩与随机性诊断",
        instruction = "你是彩票大数据规律分析师。只依据客户端提供的真实开奖历史，自行从20/40/60/120期频率、当前与历史遗漏、条件后继转移、号码密度、跨名次差异、贝叶斯样本收缩和熵/随机性中提取证据。预测时至少使用三类相互独立的信号，并报告样本量、信号强弱和冲突。遗漏久不代表必出，连续出现不代表必降温，小样本转移不得包装成规律。先比较十个名次，再严格按用户明确指定的数量给出候选；用户说两个就只能给两个，说三个就只能给三个，不得额外追加六码、七码或备用号码。只有用户没有指定数量时才默认给出六码。没有稳定优势时必须直说。",
        quickPrompts = listOf(
            "用大数据规律分析十个名次，选出证据相对最清晰的一名并给出六码",
            "分析第一名20、60、120期频率、遗漏和后继转移，过滤小样本噪声",
            "检查当前历史是否接近随机分布，并说明哪些所谓规律不可靠",
        ),
    ),
    TREND(
        id = "trend",
        displayName = "走势分析",
        description = "多尺度趋势、波动、稳定性与状态切换建模",
        instruction = "你是彩票多尺度走势分析师。重点比较20/40/60/120期窗口的方向、斜率、动量、波动率、稳定性和可能的状态切换，并横向比较十个名次。只有多个窗口方向一致、差异超过噪声且样本充分时才称为趋势；短窗突变必须与长窗基线和随机波动对照。明确区分升温、降温、震荡、稳定和结构切换，给出边界号码与反转风险，不得把走势图形当成必然延续。用户明确要求几个候选时，最终答案必须恰好给出几个，不能擅自扩成六码、七码或补充备用号码；未指定数量时才默认六码。",
        quickPrompts = listOf(
            "比较十个名次的多尺度走势，找出状态最清晰的一名并给出六码",
            "分析第一名20、40、60、120期的升温、降温和波动情况",
            "判断当前是否出现状态切换，并列出支持证据和反转风险",
        ),
    ),
    RISK_AUDIT(
        id = "risk_audit",
        displayName = "综合预测",
        description = "融合独立信号、前向验证、概率校准与过拟合审计",
        instruction = "你是彩票综合预测与模型审计专家。先独立完成规律建模和走势分析，再对频率、遗漏、转移、状态、稳定性和可用的真实前向结算进行证据融合。不同信号高度相关时不得重复计权；连续未中时复盘失效因素并改变策略。输出名次、主要支持、主要冲突和置信程度，并严格按用户指定数量输出候选；用户没有指定数量时才默认六码。只有用户明确要求边界或七码时才补充相应边界，不能在用户只要两个号码时再给六码、七码或备用号码。同时检查短窗过拟合、样本偏差和概率过度集中。证据弱时应降低确定性或明确本期没有强候选，不得承诺准确率、盈利或必中。",
        quickPrompts = listOf(
            "综合规律与走势生成本期预测，给出名次、六码、边界和风险",
            "复盘最近真实前向结果，指出失效因素并调整下一期策略",
            "审计当前候选是否过拟合，并给出更稳健的综合结果",
        ),
    );

    companion object {
        fun fromId(id: String?): AiChatPersona = when (id) {
            null, "", "comprehensive", "history", "omission", "transition", "bayes_big_data" ->
                COMPREHENSIVE
            "trend", "regime_state" -> TREND
            "adaptive_learning", "universal_consensus", "risk_audit" -> RISK_AUDIT
            else -> entries.firstOrNull { it.id == id } ?: COMPREHENSIVE
        }
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
    private const val DEFAULT_CANDIDATE_COUNT = 6
    private val candidateCountContext = ThreadLocal.withInitial { DEFAULT_CANDIDATE_COUNT }
    private val parsedPredictionContext = ThreadLocal<AiChatPrediction?>()
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
        val wants = predictionTerms.any(normalized::contains)
        if (wants) {
            candidateCountContext.set(requestedCandidateCount(normalized) ?: DEFAULT_CANDIDATE_COUNT)
        } else {
            candidateCountContext.set(DEFAULT_CANDIDATE_COUNT)
            parsedPredictionContext.remove()
        }
        return wants
    }

    fun requestedCandidateCount(text: String): Int? {
        val normalized = text.trim().lowercase()
        val numberToken = "(10|[1-9]|[一二两三四五六七八九十])"
        val patterns = listOf(
            Regex(
                "(?:只要|就要|给我|告诉我|提供|推荐|挑出|选出|选|列出|报出|取)?\\s*" +
                    numberToken + "\\s*(?:个)?\\s*(?:号码|候选|码)",
            ),
            Regex(
                "(?:号码|候选)\\s*(?:数量|个数)?\\s*(?:为|是|要|取)?\\s*" +
                    numberToken + "\\s*(?:个|码)?",
            ),
        )
        val token = patterns.firstNotNullOfOrNull { pattern ->
            pattern.find(normalized)?.groupValues?.getOrNull(1)
        } ?: return null
        return when (token) {
            "一" -> 1
            "二", "两" -> 2
            "三" -> 3
            "四" -> 4
            "五" -> 5
            "六" -> 6
            "七" -> 7
            "八" -> 8
            "九" -> 9
            "十" -> 10
            else -> token.toIntOrNull()
        }?.coerceIn(1, 10)
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
            val candidateCount = record.prediction.top6.size.coerceAtLeast(1)
            buildString {
                append("- 目标期${record.targetPeriod} 第${record.prediction.position + 1}名 ")
                append("${candidateCount}码${record.prediction.top6.joinToString("/")}")
                record.actualNumber?.let { actual ->
                    append("，实际$actual，")
                    append(if (actual in record.prediction.top6) "${candidateCount}码命中" else "${candidateCount}码未中")
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
        val candidateCount = (candidateCountContext.get() ?: DEFAULT_CANDIDATE_COUNT).coerceIn(1, 10)
        val prediction = AiChatPrediction(
            position = position - 1,
            top6 = ranking.take(candidateCount),
            top7 = ranking.take(maxOf(7, candidateCount)),
            probabilities = probabilities,
        )
        parsedPredictionContext.set(prediction)
        return prediction
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
        val prediction = parsedPredictionContext.get()
        if (hasPrediction && prediction != null && prediction.top6.isNotEmpty()) {
            val summary = buildString {
                append("按你的要求，本期第${prediction.position + 1}名优先")
                append("${prediction.top6.size}码：")
                append(prediction.top6.joinToString("、"))
                append("。")
            }
            if (!value.startsWith(summary)) {
                value = if (value.isBlank()) summary else "$summary\n\n$value"
            }
        }
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
