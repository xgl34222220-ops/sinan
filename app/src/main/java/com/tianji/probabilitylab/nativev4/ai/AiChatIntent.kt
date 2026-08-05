package com.tianji.probabilitylab.nativev4.ai

/**
 * Keeps ordinary conversation separate from lottery analysis and structured prediction.
 * The router only selects the required data/output contract; the user's latest sentence remains
 * authoritative and is still interpreted by the model as normal language.
 */
internal enum class AiChatIntent(
    val usesLotteryContext: Boolean,
    val wantsPrediction: Boolean,
) {
    FREE_CHAT(usesLotteryContext = false, wantsPrediction = false),
    LOTTERY_ANALYSIS(usesLotteryContext = true, wantsPrediction = false),
    LOTTERY_PREDICTION(usesLotteryContext = true, wantsPrediction = true),
}

internal object AiChatIntentRouter {
    private val lotteryTerms = listOf(
        "幸运飞艇", "澳洲幸运10", "澳洲", "赛车", "开奖", "期号", "期次", "下一期", "下期", "上期",
        "号码", "候选", "胆码", "六码", "七码", "两码", "三码", "名次", "冠军",
        "走势", "遗漏", "热号", "冷号", "频率", "转移", "命中", "没中", "未中", "不中",
        "复盘", "概率", "评分", "预测", "策略", "历史数据", "开奖数据",
    )
    private val predictionActions = listOf(
        "预测", "推荐", "给我", "告诉我", "提供", "生成", "列出", "选出", "挑出",
        "选两个", "选三个", "重点看", "看好", "最可能", "最有可能", "会开", "开出",
        "来一组", "给一组", "报两个", "报三个", "再看看", "再分析", "继续看",
    )
    private val predictionObjects = listOf(
        "号码", "候选", "胆码", "六码", "七码", "两码", "三码", "下一期", "下期", "预测",
    )
    private val hardAnalysisOnlySignals = listOf(
        "不要预测", "不需要预测", "不用预测", "别预测", "不要给号码", "别给号码",
        "不需要号码", "只分析", "只解释",
    )
    private val reviewSignals = listOf(
        "为什么", "怎么会", "解释", "复盘", "刚才", "上次", "没中", "未中", "不中",
    )
    private val nextPeriodTerms = listOf("下一期", "下期", "再看看", "再分析", "继续看")

    fun resolve(text: String): AiChatIntent {
        val normalized = text.trim().lowercase()
        if (normalized.isBlank()) return AiChatIntent.FREE_CHAT

        val isLotteryRelated = lotteryTerms.any(normalized::contains)
        if (!isLotteryRelated) return AiChatIntent.FREE_CHAT

        if (hardAnalysisOnlySignals.any(normalized::contains)) {
            return AiChatIntent.LOTTERY_ANALYSIS
        }

        val asksNextPeriod = nextPeriodTerms.any(normalized::contains) &&
            (
                predictionObjects.any(normalized::contains) ||
                    AiPositionScope.extract(normalized) != null
                )
        if (asksNextPeriod) return AiChatIntent.LOTTERY_PREDICTION

        // An explanation such as “为什么给了两个号码” must remain an explanation, while
        // “分析第一名，给两个号码” is a new prediction request.
        if (reviewSignals.any(normalized::contains)) {
            return AiChatIntent.LOTTERY_ANALYSIS
        }

        val explicitPrediction = (
            predictionActions.any(normalized::contains) &&
                predictionObjects.any(normalized::contains)
            ) || AiChatProtocol.requestedCandidateCount(normalized) != null

        return if (explicitPrediction) {
            AiChatIntent.LOTTERY_PREDICTION
        } else {
            AiChatIntent.LOTTERY_ANALYSIS
        }
    }
}
