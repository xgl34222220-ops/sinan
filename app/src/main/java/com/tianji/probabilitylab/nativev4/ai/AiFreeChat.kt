package com.tianji.probabilitylab.nativev4.ai

import java.util.UUID

enum class AiChatRole {
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
        description = "综合频次、遗漏、转移、趋势和本机模型",
        instruction = "综合使用20/60/120期频次、当前遗漏、后继转移、短长窗口变化和本机模型参考。先给结论，再列最关键证据和不确定性，避免只凭单一指标下结论。",
        quickPrompts = listOf(
            "综合分析第一名，给出下一期相对候选和主要依据",
            "比较十个名次，当前哪个名次的候选边界更清晰？",
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
            values().firstOrNull { it.id == id } ?: COMPREHENSIVE
    }
}

data class AiChatMessage(
    val id: String = UUID.randomUUID().toString(),
    val role: AiChatRole,
    val content: String,
    val createdAtEpochMs: Long = System.currentTimeMillis(),
    val latencyMs: Long? = null,
)

data class AiChatPrediction(
    val position: Int,
    val top6: List<Int>,
    val top7: List<Int>,
    val probabilities: List<Double>,
)

data class AiChatArchive(
    val id: String,
    val lotteryKey: String,
    val profileId: String,
    val profileName: String,
    val model: String,
    val targetPeriod: String,
    val personaId: String = AiChatPersona.COMPREHENSIVE.id,
    val messages: List<AiChatMessage> = emptyList(),
    val prediction: AiChatPrediction? = null,
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
    val personaId: String = AiChatPersona.COMPREHENSIVE.id,
    val messages: List<AiChatMessage> = emptyList(),
    val isRunning: Boolean = false,
    val progress: String = "",
    val error: String? = null,
    val prediction: AiChatPrediction? = null,
    val targetPeriod: String? = null,
    val streamingMessageId: String? = null,
    val isReadOnlyArchive: Boolean = false,
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

object AiChatArchiveId {
    fun of(lotteryKey: String, targetPeriod: String, profileId: String, model: String): String =
        listOf(lotteryKey, targetPeriod, profileId, model)
            .joinToString("\u001F") { it.trim() }
}

/**
 * Keeps free-form chat independent from the official frozen forecast protocol.
 * A prediction card is only extracted when the user's own request asks for candidates.
 */
object AiChatProtocol {
    private val predictionTerms = listOf(
        "预测", "预判", "候选", "六码", "七码", "号码", "出号", "推荐", "名次",
        "position", "scores", "forecast", "pick",
    )

    fun wantsPrediction(text: String): Boolean {
        val normalized = text.trim().lowercase()
        return predictionTerms.any(normalized::contains)
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
        value = value.replace(
            Regex("(?s)<tianji_forecast>.*?</tianji_forecast>"),
            "",
        ).trim()
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

    fun trimHistory(messages: List<AiChatMessage>, maxMessages: Int = 16): List<AiChatMessage> =
        messages.filter { it.content.isNotBlank() }.takeLast(maxMessages.coerceAtLeast(1))
}
