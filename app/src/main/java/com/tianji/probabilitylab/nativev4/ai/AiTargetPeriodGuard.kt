package com.tianji.probabilitylab.nativev4.ai

/**
 * Keeps the model's visible prediction heading aligned with the target period selected by the app.
 * Old period references are still allowed inside evidence and review text; only current-target labels
 * and prediction headings are corrected.
 */
internal object AiTargetPeriodGuard {
    private val predictionHeadingPeriod = Regex(
        """(?m)^(\s*(?:#{1,6}\s*)?)(\d{6,20})(\s*期\s*(?:(?:综合|本期|下期|下一期)?\s*)?(?:第\s*[一二三四五六七八九十0-9]+\s*名\s*)?(?:预测|候选|推荐).*)$""",
    )
    private val targetLabelPeriod = Regex(
        """(目标期\s*[:：]?\s*)(\d{6,20})(\s*期?)""",
    )

    fun reconcilePredictionText(
        text: String,
        expectedTargetPeriod: String,
        isPrediction: Boolean,
    ): String {
        val expected = expectedTargetPeriod.trim()
        if (!isPrediction || expected.isBlank() || text.isBlank()) return text

        val correctedHeading = predictionHeadingPeriod.replace(text) { match ->
            match.groupValues[1] + expected + match.groupValues[3]
        }
        return targetLabelPeriod.replace(correctedHeading) { match ->
            match.groupValues[1] + expected + match.groupValues[3]
        }
    }

    fun contextualizePreviousMessage(
        message: AiChatMessage,
        expectedTargetPeriod: String,
    ): String {
        val oldTarget = message.targetPeriod.orEmpty().trim()
        val expected = expectedTargetPeriod.trim()
        if (oldTarget.isBlank() || expected.isBlank() || oldTarget == expected) {
            return message.content
        }
        return "【旧目标期：${oldTarget}期，仅供历史复盘；当前目标期不是该期】\n${message.content}"
    }

    fun currentRequestInstruction(expectedTargetPeriod: String): String {
        val expected = expectedTargetPeriod.trim()
        return "本次请求的唯一当前目标期是${expected}期。此前对话中出现的其他期号全部属于历史内容。" +
            "预测标题、正文中的当前期描述、结构化候选和最终候选卡必须统一使用${expected}期；" +
            "不得复制旧回答中的目标期号，也不得自行推算或改写当前目标期。"
    }
}
