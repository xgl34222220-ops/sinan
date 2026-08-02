package com.tianji.probabilitylab.nativev4.data

import com.tianji.probabilitylab.nativev4.model.Draw

/** Rejects conflicting upstream records instead of silently overwriting the same period. */
object DrawMergePolicy {
    fun merge(draws: List<Draw>): List<Draw> {
        val grouped = draws.groupBy(Draw::period)
        val conflict = grouped.entries.firstOrNull { (_, records) ->
            records.map(Draw::numbers).distinct().size > 1
        }
        require(conflict == null) {
            val period = conflict?.key.orEmpty()
            "上游同一期 $period 返回了不同开奖号码，已停止预测并等待重新核验"
        }
        return grouped.values
            .map { records -> records.last() }
            .sortedWith(compareBy<Draw>({ it.period.length }, Draw::period))
    }
}
