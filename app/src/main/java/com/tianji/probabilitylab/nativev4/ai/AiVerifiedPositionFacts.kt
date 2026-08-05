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
        .put("source", "upstream_lottery_api_current_response")
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

/** Resolves the rank for the current turn while preserving normal conversational follow-ups. */
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
        require(history.isNotEmpty()) { "${snapshot.lottery.displayName}开奖 API 没有返回可用历史" }

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

/** Keeps API facts authoritative while allowing the model to answer naturally. */
internal object AiVerifiedAnswerComposer {
    private val numericFactTriggers = listOf(
        "近10", "近20", "近60", "近120", "最近十", "最近20", "最近60", "最近120",
        "出现次数", "频率统计", "高频区", "低频区", "冷号", "热号", "遗漏", "后继",
        "承接概率", "短期趋势", "号码序列", "次）", "次)", "%", "％",
    )
    private val recentTerms = listOf("近十", "近10", "最近十", "最近10", "十期号码", "10期号码")
    private val countTerms = listOf("次数", "频率", "高频", "低频", "冷号", "热号")
    private val omissionTerms = listOf("遗漏", "多久没出", "多少期没出")

    fun compose(
        modelText: String,
        facts: AiVerifiedPositionFacts?,
        intent: AiChatIntent,
        question: String,
    ): String {
        if (facts == null) return modelText.trim()
        exactLookup(question, facts)?.let { return it }

        val interpretation = sanitize(modelText, intent)
        val sourceLine = "数据源：${facts.lotteryName}上游开奖 API，最新 ${facts.latestPeriod} 期；当前分析第${facts.position + 1}名。"
        return if (interpretation.isBlank()) {
            sourceLine
        } else {
            "$interpretation\n\n$sourceLine"
        }
    }

    private fun exactLookup(question: String, facts: AiVerifiedPositionFacts): String? {
        val normalized = question.replace(" ", "")
        return when {
            recentTerms.any(normalized::contains) -> buildString {
                append("${facts.lotteryName}第${facts.position + 1}名最近10期（新→旧）：")
                append(facts.recent10NewestFirst.joinToString("、") { "${it.period}期=${it.number}" })
                append("。\n数据直接来自当前上游开奖 API 响应，最新一期为 ${facts.latestPeriod}。")
            }
            countTerms.any(normalized::contains) -> buildString {
                append("${facts.lotteryName}第${facts.position + 1}名出现次数（号码1→10，近20/60/120期）：\n")
                append((1..10).joinToString("；") { number ->
                    val index = number - 1
                    "${number}号 ${facts.count20[index]}/${facts.count60[index]}/${facts.count120[index]}"
                })
                append("。\n数据直接来自当前上游开奖 API 响应，统计截至 ${facts.latestPeriod} 期。")
            }
            omissionTerms.any(normalized::contains) -> buildString {
                append("${facts.lotteryName}第${facts.position + 1}名当前遗漏（号码1→10）：")
                append((1..10).joinToString("、") { number -> "${number}号${facts.omission[number - 1]}期" })
                append("。\n数据直接来自当前上游开奖 API 响应，统计截至 ${facts.latestPeriod} 期。")
            }
            else -> null
        }
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
