package com.tianji.probabilitylab.nativev4.data

import com.tianji.probabilitylab.nativev4.model.Draw
import com.tianji.probabilitylab.nativev4.model.LotteryType
import java.math.BigInteger
import java.time.LocalDate
import java.time.format.DateTimeFormatter

data class HistoryIntegrityResult(
    val valid: Boolean,
    val count: Int,
    val message: String,
    val gapAfterPeriod: String? = null,
)

/** Verifies that a model window came from one ordered, gap-free API history. */
object HistoryIntegrity {
    fun inspect(
        lottery: LotteryType,
        historyInput: List<Draw>,
        latestPeriod: String,
        minimumHistory: Int,
    ): HistoryIntegrityResult {
        val history = historyInput
            .filter { it.lottery == lottery }
            .distinctBy(Draw::period)
            .sortedWith(compareBy<Draw>({ it.period.length }, { it.period }))
        if (history.size < minimumHistory) {
            return HistoryIntegrityResult(
                valid = false,
                count = history.size,
                message = "接口仅返回 ${history.size} 期，至少需要 $minimumHistory 期",
            )
        }
        if (history.lastOrNull()?.period != latestPeriod) {
            return HistoryIntegrityResult(
                valid = false,
                count = history.size,
                message = "接口历史末期与最新期号不一致",
            )
        }
        val invalidDraw = history.firstOrNull {
            it.numbers.size != 10 || it.numbers.toSet().size != 10 || it.numbers.any { number -> number !in 1..10 }
        }
        if (invalidDraw != null) {
            return HistoryIntegrityResult(
                valid = false,
                count = history.size,
                message = "接口第 ${invalidDraw.period} 期号码无效",
            )
        }
        val gap = history.zipWithNext().firstOrNull { (previous, next) ->
            !isImmediateSuccessor(lottery, previous.period, next.period)
        }
        if (gap != null) {
            return HistoryIntegrityResult(
                valid = false,
                count = history.size,
                message = "接口历史在 ${gap.first.period} → ${gap.second.period} 之间断档",
                gapAfterPeriod = gap.first.period,
            )
        }
        return HistoryIntegrityResult(
            valid = true,
            count = history.size,
            message = "开奖接口连续历史 ${history.size} 期已核验",
        )
    }

    internal fun isImmediateSuccessor(lottery: LotteryType, previous: String, next: String): Boolean =
        when (lottery) {
            LotteryType.AZXY10 -> numericSuccessor(previous, next)
            LotteryType.XYFT -> datedSuccessor(previous, next)
        }

    private fun numericSuccessor(previous: String, next: String): Boolean = runCatching {
        BigInteger(next) == BigInteger(previous) + BigInteger.ONE
    }.getOrDefault(false)

    private fun datedSuccessor(previous: String, next: String): Boolean {
        val prior = parseDatedPeriod(previous) ?: return false
        val following = parseDatedPeriod(next) ?: return false
        return if (prior.date == following.date) {
            following.sequence == prior.sequence + 1
        } else {
            following.date == prior.date.plusDays(1) && following.sequence == 1
        }
    }

    private fun parseDatedPeriod(period: String): DatedPeriod? {
        val match = Regex("^(\\d{8})(\\d{3,})$").matchEntire(period) ?: return null
        return runCatching {
            DatedPeriod(
                date = LocalDate.parse(match.groupValues[1], DateTimeFormatter.BASIC_ISO_DATE),
                sequence = match.groupValues[2].toInt(),
            )
        }.getOrNull()
    }

    private data class DatedPeriod(val date: LocalDate, val sequence: Int)
}

