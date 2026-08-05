package com.tianji.probabilitylab.nativev4.ai

internal enum class AiContinuityMode {
    FRESH,
    NATURAL_FOLLOW_UP,
    ADJACENT_SETTLED,
    EXPLICIT_REVIEW,
}

internal data class AiTurnContinuity(
    val mode: AiContinuityMode,
    val previousMessages: List<AiChatMessage>,
    val relevantFeedback: String,
    val relevantRecord: AiChatCandidateRecord?,
)

/**
 * Decides whether a previous prediction is actually relevant to the current sentence.
 * Same rank alone is never enough: a fresh question days later starts from the current API data.
 */
internal object AiConversationContinuity {
    private val explicitReviewTerms = listOf(
        "复盘", "上次", "之前那次", "刚才那期", "为什么没中", "为什么未中", "为什么不中",
        "没中", "未中", "不中", "命中没有", "结果怎么样",
    )
    private val naturalFollowUpTerms = listOf(
        "为什么", "怎么判断", "解释一下", "继续", "再看看", "再分析", "怎么调整",
        "哪里有问题", "哪里错了", "提高", "优化", "这一期", "下一期", "下期",
    )

    fun resolve(
        question: String,
        activePosition: Int?,
        currentTargetPeriod: String,
        latestApiPeriod: String,
        messages: List<AiChatMessage>,
        candidates: List<AiChatCandidateRecord>,
    ): AiTurnContinuity {
        if (activePosition == null) {
            return AiTurnContinuity(
                mode = AiContinuityMode.FRESH,
                previousMessages = emptyList(),
                relevantFeedback = "",
                relevantRecord = null,
            )
        }

        val normalized = question.replace(" ", "")
        val explicitRank = AiPositionScope.extract(question) != null
        val explicitReview = explicitReviewTerms.any(normalized::contains)
        val naturalFollowUp = naturalFollowUpTerms.any(normalized::contains)
        val sameTargetConversation = messages.any { message ->
            val scope = message.positionScope ?: AiPositionScope.extract(message.content)
            scope == activePosition && message.targetPeriod == currentTargetPeriod
        }
        val latestSettled = candidates.asReversed().firstOrNull { record ->
            record.prediction.position == activePosition && record.actualNumber != null
        }
        val adjacentSettled = latestSettled?.takeIf { it.targetPeriod == latestApiPeriod }

        val mode = when {
            explicitReview -> AiContinuityMode.EXPLICIT_REVIEW
            adjacentSettled != null && naturalFollowUp -> AiContinuityMode.ADJACENT_SETTLED
            naturalFollowUp && (!explicitRank || sameTargetConversation) ->
                AiContinuityMode.NATURAL_FOLLOW_UP
            else -> AiContinuityMode.FRESH
        }
        val relevantRecord = when (mode) {
            AiContinuityMode.EXPLICIT_REVIEW -> latestSettled
            AiContinuityMode.ADJACENT_SETTLED -> adjacentSettled
            AiContinuityMode.FRESH,
            AiContinuityMode.NATURAL_FOLLOW_UP,
            -> null
        }
        val scopedMessages = when (mode) {
            AiContinuityMode.FRESH -> emptyList()
            else -> {
                val allowedPeriods = buildSet {
                    currentTargetPeriod.takeIf(String::isNotBlank)?.let(::add)
                    relevantRecord?.targetPeriod?.takeIf(String::isNotBlank)?.let(::add)
                }
                AiPositionScope.filterPrevious(messages, activePosition)
                    .filter { message ->
                        message.targetPeriod == null || allowedPeriods.isEmpty() ||
                            message.targetPeriod in allowedPeriods
                    }
                    .takeLast(12)
            }
        }

        return AiTurnContinuity(
            mode = mode,
            previousMessages = scopedMessages,
            relevantFeedback = relevantRecord?.let { record -> feedback(record, mode, currentTargetPeriod) }.orEmpty(),
            relevantRecord = relevantRecord,
        )
    }

    private fun feedback(
        record: AiChatCandidateRecord,
        mode: AiContinuityMode,
        currentTargetPeriod: String,
    ): String = buildString {
        append("与当前问题直接相关的已结算记录：")
        append("目标期${record.targetPeriod}，第${record.prediction.position + 1}名，候选")
        append(record.prediction.top6.joinToString("/"))
        val actual = record.actualNumber
        if (actual != null) {
            append("，实际号码$actual，结果")
            append(if (actual in record.prediction.top6) "命中" else "未中")
        }
        append("。当前目标期为$currentTargetPeriod。")
        append(
            when (mode) {
                AiContinuityMode.ADJACENT_SETTLED ->
                    "该记录正好是当前目标期前一期开奖，可用于复盘后调整本期。"
                AiContinuityMode.EXPLICIT_REVIEW ->
                    "这是用户明确要求复盘的历史记录；必须写明具体期号，不得称作上一期，除非它确实紧邻当前期。"
                else -> ""
            },
        )
        append("只复盘真实候选与实际号码的偏差，不得编造失效原因；调整后仍需以当前上游开奖 API 历史为准。")
    }
}
