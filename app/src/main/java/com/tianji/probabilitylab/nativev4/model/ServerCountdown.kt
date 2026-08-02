package com.tianji.probabilitylab.nativev4.model

import kotlin.math.ceil

object ServerCountdown {
    fun remainingSeconds(
        nextDrawAtEpochMs: Long,
        serverTimeAtSyncEpochMs: Long,
        localSyncedAtEpochMs: Long,
        localNowEpochMs: Long,
    ): Int {
        val serverOffset = serverTimeAtSyncEpochMs - localSyncedAtEpochMs
        val serverNow = localNowEpochMs + serverOffset
        return ceil((nextDrawAtEpochMs - serverNow) / 1_000.0).toInt().coerceAtLeast(0)
    }
}
