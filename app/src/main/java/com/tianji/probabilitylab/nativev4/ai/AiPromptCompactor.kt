package com.tianji.probabilitylab.nativev4.ai

import com.tianji.probabilitylab.nativev4.model.Draw
import org.json.JSONArray
import org.json.JSONObject

internal data class CompactDrawRow(
    val period: String,
    val numbers: String,
)

internal data class CompactPositionFacts(
    val position: Int,
    val latestNumber: Int,
    val recent20Counts: List<Int>,
    val recent60Counts: List<Int>,
    val omissions: List<Int>,
    val transitionsAfterLatest: List<Int>,
    val sizeSide: String,
    val sizeStreak: Int,
)

/**
 * Keeps the full requested history while removing redundant JSON structure and precomputing facts
 * that the model would otherwise spend thousands of reasoning tokens recounting by hand.
 */
object AiPromptCompactor {
    const val FORMAT = "each item is [period, comma-separated positions 1..10]"
    const val REASONING_RULE =
        "必须进行真实推理，但禁止逐期复述开奖记录或重复计算已核验统计；优先比较本机给出的频次、遗漏与后继转移，原始历史只用于交叉核验。完成比较后立即输出JSON。"

    internal fun compactRows(history: List<Draw>, limit: Int): List<CompactDrawRow> =
        history.takeLast(limit.coerceAtLeast(1)).map { draw ->
            CompactDrawRow(
                period = draw.period,
                numbers = draw.numbers.joinToString(","),
            )
        }

    internal fun positionFacts(history: List<Draw>): List<CompactPositionFacts> {
        val usable = history.filter { it.numbers.size >= 10 }
        return List(10) { position ->
            val values = usable.map { it.numbers[position] }
            val latest = values.lastOrNull() ?: 0
            val recent20 = counts(values.takeLast(20))
            val recent60 = counts(values.takeLast(60))
            val omissions = (1..10).map { number ->
                values.asReversed().indexOf(number).let { index ->
                    if (index < 0) values.size else index
                }
            }
            val transitions = MutableList(10) { 0 }
            if (latest in 1..10) {
                for (index in 0 until values.lastIndex) {
                    if (values[index] == latest) {
                        val next = values[index + 1]
                        if (next in 1..10) transitions[next - 1]++
                    }
                }
            }
            val side = if (latest in 1..5) "small" else "large"
            var streak = 0
            for (value in values.asReversed()) {
                val currentSide = if (value in 1..5) "small" else "large"
                if (currentSide != side) break
                streak++
            }
            CompactPositionFacts(
                position = position + 1,
                latestNumber = latest,
                recent20Counts = recent20,
                recent60Counts = recent60,
                omissions = omissions,
                transitionsAfterLatest = transitions,
                sizeSide = side,
                sizeStreak = streak,
            )
        }
    }

    fun compactDraws(history: List<Draw>, limit: Int): JSONArray = JSONArray().apply {
        compactRows(history, limit).forEach { row ->
            put(JSONArray().put(row.period).put(row.numbers))
        }
    }

    fun verifiedPositionStatistics(history: List<Draw>): JSONArray = JSONArray().apply {
        positionFacts(history).forEach { facts ->
            put(
                JSONObject()
                    .put("position", facts.position)
                    .put("latest_number", facts.latestNumber)
                    .put("recent20_counts_1_to_10", JSONArray(facts.recent20Counts))
                    .put("recent60_counts_1_to_10", JSONArray(facts.recent60Counts))
                    .put("current_omissions_1_to_10", JSONArray(facts.omissions))
                    .put("next_after_current_counts_1_to_10", JSONArray(facts.transitionsAfterLatest))
                    .put("latest_size_side", facts.sizeSide)
                    .put("latest_size_streak", facts.sizeStreak),
            )
        }
    }

    private fun counts(values: List<Int>): List<Int> = (1..10).map { number ->
        values.count { it == number }
    }
}
