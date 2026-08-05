package com.tianji.probabilitylab.nativev4.ai

/**
 * Keeps ordinary conversation separate from lottery analysis and structured prediction.
 * The model remains free to answer naturally; the router only decides whether expensive
 * lottery history and structured candidate output are actually needed.
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
        "幸运飞艇", "赛车", "开奖", "期号", "期次", "下一期", "下期", "上期",
        "号码", "候选", "胆码", "六码", "七码", "两码", "三码", "名次", "冠军",
        "走势", "遗漏", "热号", "冷号", "频率", "转移", "命中", "没中", "未中",
        "复盘", "概率", "评分", "预测", "策略", "历史数据", "开奖数据",
    )
    private val predictionActions = listOf(
        "预测", "推荐", "给我", "告诉我", "提供", "生成", "列出", "选出", "挑出",
        "选两个", "选三个", "重点看", "看好", "最可能", "最有可能", "会开", "开出",
        "来一组", "给一组", "报两个", "报三个",
    )
    private val predictionObjects = listOf(
        "号码", "候选", "胆码", "六码", "七码", "两码", "三码", "下一期", "下期", "预测",
    )
    private val analysisOnlySignals = listOf(
        "为什么", "怎么会", "解释", "复盘", "刚才", "上次", "没中", "未中",
        "不要预测", "不需要预测", "不用预测", "别预测", "不要给号码", "别给号码",
        "不需要号码", "只分析", "只解释",
    )

    fun resolve(text: String): AiChatIntent {
        val normalized = text.trim().lowercase()
        if (normalized.isBlank()) return AiChatIntent.FREE_CHAT

        val isLotteryRelated = lotteryTerms.any(normalized::contains)
        if (!isLotteryRelated) return AiChatIntent.FREE_CHAT

        val analysisOnly = analysisOnlySignals.any(normalized::contains)
        val asksForPrediction = predictionActions.any(normalized::contains) &&
            predictionObjects.any(normalized::contains)

        return if (asksForPrediction && !analysisOnly) {
            AiChatIntent.LOTTERY_PREDICTION
        } else {
            AiChatIntent.LOTTERY_ANALYSIS
        }
    }
}
