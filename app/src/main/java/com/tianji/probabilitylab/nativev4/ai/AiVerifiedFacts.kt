package com.tianji.probabilitylab.nativev4.ai

import com.tianji.probabilitylab.nativev4.model.Draw

data class AiPositionFacts(
    val position: Int,
    val latestNumber: Int,
    val recent20Counts: List<Int>,
    val omissions: List<Int>,
    val sizeSide: String,
    val sizeStreak: Int,
)

object AiFactEngine {
    fun calculate(history: List<Draw>): List<AiPositionFacts> {
        val ordered = history
            .associateBy(Draw::period)
            .values
            .sortedWith(compareBy<Draw>({ it.period.length }, Draw::period))
        require(ordered.isNotEmpty()) { "没有可供事实核验的开奖历史" }
        val recent = ordered.takeLast(20)
        return (0 until 10).map { position ->
            val latestNumber = ordered.last().numbers[position]
            val recentCounts = (1..10).map { candidate ->
                recent.count { it.numbers[position] == candidate }
            }
            val omissions = (1..10).map { candidate ->
                var gap = 0
                for (index in ordered.lastIndex downTo 0) {
                    if (ordered[index].numbers[position] == candidate) break
                    gap++
                }
                gap
            }
            val latestIsSmall = latestNumber <= 5
            val streak = ordered.asReversed().takeWhile {
                (it.numbers[position] <= 5) == latestIsSmall
            }.size
            AiPositionFacts(
                position = position,
                latestNumber = latestNumber,
                recent20Counts = recentCounts,
                omissions = omissions,
                sizeSide = if (latestIsSmall) "小" else "大",
                sizeStreak = streak,
            )
        }
    }

    fun verifiedSummary(history: List<Draw>, position: Int, top6: List<Int>): String {
        val ordered = history
            .associateBy(Draw::period)
            .values
            .sortedWith(compareBy<Draw>({ it.period.length }, Draw::period))
        val facts = calculate(ordered)[position]
        val counts = top6.joinToString("、") { number ->
            "${number}号${facts.recent20Counts[number - 1]}次"
        }
        val omissions = top6.joinToString("、") { number ->
            "${number}号${facts.omissions[number - 1]}期"
        }
        return "开奖接口历史·本机计算（接口返回${ordered.size}期，截至${ordered.last().period}期）：" +
            "第${position + 1}名最新" +
            "${facts.latestNumber}号，连续${facts.sizeSide}${facts.sizeStreak}期；" +
            "近20期出现：$counts；当前遗漏：$omissions。AI只负责候选排序，统计数字均由本机逐期计算。"
    }
}
