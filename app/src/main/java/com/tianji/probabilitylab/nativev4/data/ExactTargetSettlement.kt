package com.tianji.probabilitylab.nativev4.data

import com.tianji.probabilitylab.nativev4.model.Draw

data class ExactSettlement(
    val actualNumber: Int,
    val top6Hit: Boolean,
    val top7Hit: Boolean,
)

/** Settlement is deliberately keyed by target period; the newest draw is never substituted. */
object ExactTargetSettlement {
    fun evaluate(
        draws: List<Draw>,
        targetPeriod: String,
        position: Int,
        top6: List<Int>,
        top7: List<Int>,
    ): ExactSettlement? {
        val targetDraw = draws.firstOrNull { it.period == targetPeriod } ?: return null
        val actual = targetDraw.numbers.getOrNull(position) ?: return null
        return ExactSettlement(
            actualNumber = actual,
            top6Hit = actual in top6,
            top7Hit = actual in top7,
        )
    }
}
