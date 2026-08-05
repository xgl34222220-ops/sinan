package com.tianji.probabilitylab.nativev4.ai

import com.tianji.probabilitylab.nativev4.model.Draw
import com.tianji.probabilitylab.nativev4.model.DrawSnapshot
import com.tianji.probabilitylab.nativev4.model.ForecastReport
import org.json.JSONArray
import org.json.JSONObject

data class AiVerifiedRecentValue(
    val period: String,
    val number: Int,
)

data class AiVerifiedPositionFacts(
    val lotteryKey: String,
    val lotteryName: String,
    val position: Int,
    val latestPeriod: String,
    val targetPeriod: String,
    val sampleStartPeriod: String,
    val sampleEndPeriod: String,
    val sampleSize: Int,
    val currentNumber: Int,
    val recent10NewestFirst: List<AiVerifiedRecentValue>,
    val count20: List<Int>,
    val count60: List<Int>,
    val count120: List<Int>,
    val omission: List<Int>,
) {
    fun toJson(): JSONObject = JSONObject()
        .put("source", "client_verified_from_current_lottery_snapshot")
        .put("lottery_key", lotteryKey)
        .put("lottery_name", lotteryName)
        .put("position", position + 1)
        .put("latest_period", latestPeriod)
        .put("target_period", targetPeriod)
        .put("sample_start_period", sampleStartPeriod)
        .put("sample_end_period", sampleEndPeriod)
        .put("sample_size", sampleSize)
        .put("current_number", currentNumber)
        .put(
            "recent_10_newest_to_oldest",
            JSONArray(recent10NewestFirst.map { value ->
                JSONObject().put("period", value.period).put("number", value.number)
            }),
        )
        .put("count_20_by_number_1_to_10", JSONArray(count20))
        .put("count_60_by_number_1_to_10", JSONArray(count60))
        .put("count_120_by_number_1_to_10", JSONArray(count120))
        .put("omission_by_number_1_to_10", JSONArray(omission))
}

/** Resolves the rank for one turn without turning the conversation into a rigid command parser. */
object AiPositionScope {
    private val positionPattern = Regex("""第\s*([一二三四五六七八九十0-9]{1,2})\s*名""")
    private val allPositionTerms = listOf(
        "十个名次", "所有名次", "全部名次", "各个名次", "哪个名次", "哪一名",
        "比较名次", "横向比较", "全名次",
    )

    fun extract(text: String): Int? {
        val token = positionPattern.find(text)?.groupValues?.getOrNull(1) ?: return null
        val value = token.toIntOrNull() ?: when (token) {
            "一" -> 1
            "二" -> 2
            "三" -> 3
            "四" -> 4
            "五" -> 5
            "六" -> 6
            "七" -> 7
            "八" -> 8
            "九" -> 9
            "十" -> 10
            else -> return null
        }
        return (value - 1).takeIf { it in 0..9 }
    }

    fun requestsAllPositions(text: String): Boolean = allPositionTerms.any(text::contains)

    fun resolve(question: String, previousMessages: List<AiChatMessage>): Int? {
        extract(question)?.let { return it }
        if (requestsAllPositions(question)) return null
        return previousMessages.asReversed().firstNotNullOfOrNull { message ->
            message.positionScope ?: extract(message.content)
        }
    }

    /**
     * Keep the same free conversation visible, but do not send another rank's analysis back to the
     * model for the current turn. Legacy messages are scoped conservatively from their visible text.
     */
    fun filterPrevious(
        messages: List<AiChatMessage>,
        activePosition: Int?,
    ): List<AiChatMessage> {
        if (activePosition == null) return messages
        return messages.filter { message ->
            val inferred = message.positionScope ?: extract(message.content)
            inferred == null || inferred == activePosition
        }
    }
}

object AiVerifiedPositionEngine {
    fun calculate(
        snapshot: DrawSnapshot,
        report: ForecastReport,
        position: Int,
    ): AiVerifiedPositionFacts {
        require(position in 0..9) { "分析名次必须在第一名到第十名之间" }
        val history = canonical(snapshot.history)
        require(history.isNotEmpty()) { "没有可用于核验的${snapshot.lottery.displayName}开奖历史" }

        fun counts(window: Int): List<Int> {
            val result = IntArray(10)
            history.takeLast(window).forEach { draw ->
                draw.numbers[position].takeIf { it in 1..10 }?.let { result[it - 1]++ }
            }
            return result.toList()
        }

        val omission = (1..10).map { number ->
            val index = history.indexOfLast { it.numbers[position] == number }
            if (index < 0) history.size else history.lastIndex - index
        }
        return AiVerifiedPositionFacts(
            lotteryKey = snapshot.lottery.apiKey,
            lotteryName = snapshot.lottery.displayName,
            position = position,
            latestPeriod = snapshot.latest.period,
            targetPeriod = report.targetPeriod,
            sampleStartPeriod = history.first().period,
            sampleEndPeriod = history.last().period,
            sampleSize = history.size,
            currentNumber = history.last().numbers[position],
            recent10NewestFirst = history.takeLast(10).asReversed().map { draw ->
                AiVerifiedRecentValue(draw.period, draw.numbers[position])
            },
            count20 = counts(20),
            count60 = counts(60),
            count120 = counts(120),
            omission = omission,
        )
    }

    private fun canonical(input: List<Draw>): List<Draw> = input.asSequence()
        .filter { it.numbers.size == 10 && it.numbers.toSet().size == 10 }
        .associateBy(Draw::period)
        .values
        .sortedWith(compareBy<Draw>({ it.period.length }, Draw::period))
        .takeLast(120)
}

/** Keeps every displayed numeric fact under client control; the model supplies interpretation only. */
object AiVerifiedAnswerComposer {
    private val numericFactTriggers = listOf(
        "近10", "近20", "近60", "近120", "最近十", "最近20", "最近60", "最近120",
        "出现次数", "频率统计", "高频区", "低频区", "冷号", "热号", "遗漏", "后继",
        "承接概率", "短期趋势", "号码序列", "次）", "次)", "%", "％",
    )

    fun compose(
        modelText: String,
        facts: AiVerifiedPositionFacts?,
        intent: AiChatIntent,
    ): String {
        if (facts == null) return modelText.trim()
        val interpretation = sanitize(modelText, intent)
        return buildString {
            append(verifiedBlock(facts))
            append("\n\n### AI 解读\n")
            append(
                interpretation.ifBlank {
                    "模型没有返回可保留的定性解读；以上数据已由 App 根据当前彩种快照逐期核验。"
                },
            )
        }.trim()
    }

    fun verifiedBlock(facts: AiVerifiedPositionFacts): String = buildString {
        append("### App 已核验数据 · ${facts.lotteryName} · 第${facts.position + 1}名\n")
        append("数据截至 ${facts.latestPeriod} 期，当前目标期 ${facts.targetPeriod}，有效样本 ${facts.sampleSize} 期。\n")
        append("最近10期（新→旧）：")
        append(facts.recent10NewestFirst.joinToString("、") { "${it.period}:${it.number}" })
        append("\n近20/60/120期次数（号码1→10）：")
        append((1..10).joinToString("；") { number ->
            val index = number - 1
            "${number}号 ${facts.count20[index]}/${facts.count60[index]}/${facts.count120[index]}"
        })
        append("\n当前遗漏（号码1→10）：")
        append((1..10).joinToString("、") { number -> "${number}号${facts.omission[number - 1]}期" })
        append("\n以上期号、序列、次数和遗漏均由 App 从当前${facts.lotteryName}快照计算，AI 无权改写。")
    }

    private fun sanitize(text: String, intent: AiChatIntent): String = text
        .lineSequence()
        .filterNot { line ->
            val hasDigit = line.any(Char::isDigit)
            val isNumericClaim = hasDigit && numericFactTriggers.any(line::contains)
            val isUnrequestedCandidate = intent == AiChatIntent.LOTTERY_ANALYSIS && hasDigit &&
                listOf("候选", "推荐", "六码", "七码", "优先号码").any(line::contains)
            isNumericClaim || isUnrequestedCandidate
        }
        .joinToString("\n")
        .replace(Regex("\n{3,}"), "\n\n")
        .trim()
}
