package com.tianji.probabilitylab.nativev4.ai

import com.tianji.probabilitylab.nativev4.model.Draw
import org.json.JSONArray
import org.json.JSONObject

/**
 * Keeps the full requested history while removing redundant JSON structure and precomputing facts
 * that the model would otherwise spend thousands of reasoning tokens recounting by hand.
 */
object AiPromptCompactor {
    const val FORMAT = "each item is [period, comma-separated positions 1..10]"
    const val REASONING_RULE =
        "必须进行真实推理，但禁止逐期复述开奖记录或重复计算已核验统计；优先比较本机给出的频次、遗漏与后继转移，原始历史只用于交叉核验。完成比较后立即输出JSON。"

    fun compactDraws(history: List<Draw>, limit: Int): JSONArray = JSONArray().apply {
        history.takeLast(limit.coerceAtLeast(1)).forEach { draw ->
            put(
                JSONArray()
                    .put(draw.period)
                    .put(draw.numbers.joinToString(",")),
            )
        }
    }

    fun verifiedPositionStatistics(history: List<Draw>): JSONArray {
        val usable = history.filter { it.numbers.size >= 10 }
        return JSONArray().apply {
            repeat(10) { position ->
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
                put(
                    JSONObject()
                        .put("position", position + 1)
                        .put("latest_number", latest)
                        .put("recent20_counts_1_to_10", JSONArray(recent20))
                        .put("recent60_counts_1_to_10", JSONArray(recent60))
                        .put("current_omissions_1_to_10", JSONArray(omissions))
                        .put("next_after_current_counts_1_to_10", JSONArray(transitions))
                        .put("latest_size_side", side)
                        .put("latest_size_streak", streak),
                )
            }
        }
    }

    private fun counts(values: List<Int>): List<Int> = (1..10).map { number ->
        values.count { it == number }
    }
}
