package com.tianji.probabilitylab.nativev4.data

data class TargetPeriodCheck(
    val open: Boolean,
    val message: String,
)

/**
 * Decides whether a result may still enter the forward archive using a freshly fetched latest
 * payload. The safety window avoids accepting a response that arrives immediately before draw time.
 */
object TargetPeriodGuard {
    fun evaluate(
        expectedTargetPeriod: String,
        latestPeriod: String,
        nextPeriod: String,
        serverTimeEpochMs: Long?,
        nextDrawAtEpochMs: Long?,
        safetyWindowMs: Long = 5_000L,
    ): TargetPeriodCheck {
        if (latestPeriod == expectedTargetPeriod) {
            return TargetPeriodCheck(
                open = false,
                message = "目标期已经开奖，结果仅可查看，未写入前向档案",
            )
        }
        if (nextPeriod != expectedTargetPeriod) {
            return TargetPeriodCheck(
                open = false,
                message = "目标期已变化：当前接口下一期为 $nextPeriod，原目标期 $expectedTargetPeriod 未写入档案",
            )
        }
        if (
            serverTimeEpochMs != null &&
            nextDrawAtEpochMs != null &&
            serverTimeEpochMs >= nextDrawAtEpochMs - safetyWindowMs
        ) {
            return TargetPeriodCheck(
                open = false,
                message = "距离开奖不足 ${safetyWindowMs / 1_000} 秒，结果未写入前向档案",
            )
        }
        return TargetPeriodCheck(open = true, message = "目标期仍开放")
    }
}
