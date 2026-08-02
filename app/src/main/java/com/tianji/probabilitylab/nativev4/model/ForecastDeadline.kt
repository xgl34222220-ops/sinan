package com.tianji.probabilitylab.nativev4.model

import java.time.Instant
import java.time.LocalDateTime
import java.time.OffsetDateTime
import java.time.ZoneId
import java.time.format.DateTimeFormatter

object ApiTimeParser {
    private val chinaZone = ZoneId.of("Asia/Shanghai")
    private val localFormats = listOf(
        DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss"),
        DateTimeFormatter.ofPattern("yyyy/MM/dd HH:mm:ss"),
        DateTimeFormatter.ISO_LOCAL_DATE_TIME,
    )

    fun parseEpochMillis(value: String): Long? {
        val normalized = value.trim()
        if (normalized.isBlank()) return null

        normalized.toLongOrNull()?.let { raw ->
            return when {
                raw <= 0L -> null
                raw < 10_000_000_000L -> raw * 1_000L
                else -> raw
            }
        }
        runCatching { Instant.parse(normalized).toEpochMilli() }.getOrNull()?.let { return it }
        runCatching { OffsetDateTime.parse(normalized).toInstant().toEpochMilli() }.getOrNull()?.let { return it }
        for (formatter in localFormats) {
            runCatching {
                LocalDateTime.parse(normalized, formatter)
                    .atZone(chinaZone)
                    .toInstant()
                    .toEpochMilli()
            }.getOrNull()?.let { return it }
        }
        return null
    }
}

data class ForecastDeadline(
    /** Server/lottery timeline target, used by the countdown display. */
    val epochMs: Long,
    /** Equivalent deadline on the device clock, used to lock submissions safely. */
    val localDeadlineEpochMs: Long,
    val source: Source,
) {
    enum class Source { API, INTERVAL_FALLBACK }
}

object ForecastDeadlineResolver {
    fun resolve(snapshot: DrawSnapshot): ForecastDeadline? {
        snapshot.nextDrawAtEpochMs?.takeIf { it > 0L }?.let { target ->
            return ForecastDeadline(
                epochMs = target,
                localDeadlineEpochMs = localDeadline(snapshot, target),
                source = ForecastDeadline.Source.API,
            )
        }
        val latestDrawEpoch = ApiTimeParser.parseEpochMillis(snapshot.latest.drawTime) ?: return null
        val target = latestDrawEpoch + snapshot.lottery.drawIntervalMinutes * 60_000L
        return ForecastDeadline(
            epochMs = target,
            localDeadlineEpochMs = localDeadline(snapshot, target),
            source = ForecastDeadline.Source.INTERVAL_FALLBACK,
        )
    }

    fun isBeforeDeadline(snapshot: DrawSnapshot, nowEpochMs: Long = System.currentTimeMillis()): Boolean =
        resolve(snapshot)?.let { nowEpochMs < it.localDeadlineEpochMs } ?: false

    private fun localDeadline(snapshot: DrawSnapshot, targetEpochMs: Long): Long {
        val serverAtSync = snapshot.serverTimeEpochMs?.takeIf { it > 0L } ?: return targetEpochMs
        val localAtSync = snapshot.sourceHealth.syncedAtEpochMs.takeIf { it > 0L } ?: return targetEpochMs
        return localAtSync + (targetEpochMs - serverAtSync)
    }
}
