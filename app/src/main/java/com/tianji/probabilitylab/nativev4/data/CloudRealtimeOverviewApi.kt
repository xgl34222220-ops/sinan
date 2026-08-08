package com.tianji.probabilitylab.nativev4.data

import com.tianji.probabilitylab.nativev4.BuildConfig
import com.tianji.probabilitylab.nativev4.model.LotteryType
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

/** Lightweight server-fed state for both lotteries.
 *
 * The normal AppController refresh remains the authoritative history/settlement/prediction lane.
 * This client only keeps both lottery headers current from one small request and lets the UI
 * trigger the heavy lane when a period actually changes.
 */
data class CloudRealtimeLottery(
    val lottery: LotteryType,
    val latestPeriod: String,
    val numbers: List<Int>,
    val nextPeriod: String,
    val nextDrawAtEpochMs: Long?,
    val syncedAtEpochMs: Long?,
    val fetchedAtEpochMs: Long,
)

class CloudRealtimeOverviewApi {
    @Volatile
    private var cache: Map<LotteryType, CloudRealtimeLottery> = emptyMap()

    fun fetchOverview(): Map<LotteryType, CloudRealtimeLottery> {
        val baseUrl = BuildConfig.TIANJI_CLOUD_BASE_URL.trim().trimEnd('/')
        if (!baseUrl.startsWith("https://")) return cache
        val connection = URL("$baseUrl/v1/public/overview").openConnection() as HttpURLConnection
        return try {
            connection.requestMethod = "GET"
            connection.connectTimeout = 1_200
            connection.readTimeout = 1_800
            connection.useCaches = false
            connection.setRequestProperty("Accept", "application/json")
            connection.setRequestProperty("Cache-Control", "no-cache")
            if (connection.responseCode !in 200..299) return cache
            val body = connection.inputStream.bufferedReader(Charsets.UTF_8).use { it.readText() }
            val parsed = parseCloudRealtimeOverview(body)
            if (parsed.isNotEmpty()) cache = parsed
            if (parsed.isNotEmpty()) parsed else cache
        } catch (_: Exception) {
            cache
        } finally {
            connection.disconnect()
        }
    }
}

internal fun parseCloudRealtimeOverview(
    body: String,
    fetchedAtEpochMs: Long = System.currentTimeMillis(),
): Map<LotteryType, CloudRealtimeLottery> {
    val root = runCatching { JSONObject(body) }.getOrNull() ?: return emptyMap()
    val lotteries = root.optJSONArray("lotteries") ?: return emptyMap()
    return buildMap {
        for (index in 0 until lotteries.length()) {
            val item = lotteries.optJSONObject(index) ?: continue
            val key = item.optString("key").trim()
            val lottery = LotteryType.entries.firstOrNull { it.apiKey == key } ?: continue
            val latestPeriod = item.optString("latest_period").trim()
            val nextPeriod = item.optString("next_period").trim()
            val numbers = item.optJSONArray("numbers").toLotteryNumbers()
            if (latestPeriod.isBlank() || numbers.size != 10) continue
            put(
                lottery,
                CloudRealtimeLottery(
                    lottery = lottery,
                    latestPeriod = latestPeriod,
                    numbers = numbers,
                    nextPeriod = nextPeriod.ifBlank { "待同步" },
                    nextDrawAtEpochMs = item.optNullableLong("next_draw_at_epoch_ms"),
                    syncedAtEpochMs = item.optNullableLong("synced_at_epoch_ms"),
                    fetchedAtEpochMs = fetchedAtEpochMs,
                ),
            )
        }
    }
}

private fun JSONArray?.toLotteryNumbers(): List<Int> {
    if (this == null) return emptyList()
    val result = buildList {
        for (index in 0 until length()) {
            optInt(index).takeIf { it in 1..10 }?.let(::add)
        }
    }
    return result.takeIf { it.size == 10 && it.toSet().size == 10 }.orEmpty()
}

private fun JSONObject.optNullableLong(key: String): Long? =
    if (!has(key) || isNull(key)) null else optLong(key).takeIf { it > 0L }
