package com.tianji.probabilitylab.nativev4.data

import com.tianji.probabilitylab.nativev4.model.ApiTimeParser
import com.tianji.probabilitylab.nativev4.model.Draw
import com.tianji.probabilitylab.nativev4.model.DrawSnapshot
import com.tianji.probabilitylab.nativev4.model.LotteryType
import com.tianji.probabilitylab.nativev4.model.SourceHealth
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.time.LocalDate
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicInteger
import kotlin.math.min

data class HistoricalFetchResult(
    val draws: List<Draw>,
    val failedDates: List<LocalDate>,
)

class LotteryApi {
    private val baseUrl = "https://api.api68.com"
    private val activeConnections = ConcurrentHashMap.newKeySet<HttpURLConnection>()
    private val cancellationGeneration = AtomicInteger(0)

    fun cancelActiveRequests() {
        cancellationGeneration.incrementAndGet()
        activeConnections.toList().forEach(HttpURLConnection::disconnect)
        activeConnections.clear()
    }

    fun fetchSnapshot(lottery: LotteryType, days: Int = 14): DrawSnapshot {
        val requestToken = cancellationGeneration.get()
        val zone = ZoneId.of("Asia/Shanghai")
        val dates = (0 until days.coerceIn(1, MAX_RECENT_DAYS)).map {
            LocalDate.now(zone).minusDays(it.toLong())
        }
        val fetched = fetchDates(lottery, dates, requestToken)
        ensureActive(requestToken)
        val latestPayload = fetchLatestWithRetry(lottery, requestToken)
            ?: error("最新开奖接口没有返回有效期号")
        val merged = DrawMergePolicy.merge(fetched.draws + latestPayload.draw)
            .takeLast(lottery.historyTarget)
        val newest = merged.lastOrNull() ?: error("开奖接口没有返回有效数据")
        return DrawSnapshot(
            lottery = lottery,
            history = merged,
            latest = newest,
            nextPeriod = latestPayload.nextPeriod.takeIf { latestPayload.draw.period == newest.period }
                ?: incrementPeriod(newest.period),
            sourceHealth = SourceHealth(
                label = "实时接口",
                isFresh = true,
                independentSources = 1,
                message = if (fetched.failedDates.isEmpty()) {
                    "已核验最近 ${dates.size} 天接口历史；当前仅有一个独立上游"
                } else {
                    "已同步 ${dates.size - fetched.failedDates.size}/${dates.size} 天；缺失日期将重试，连续性仍由本机强校验"
                },
                syncedAtEpochMs = System.currentTimeMillis(),
            ),
            serverTimeEpochMs = latestPayload.serverTimeEpochMs,
            nextDrawAtEpochMs = latestPayload.nextDrawAtEpochMs,
        )
    }

    /** Fetches exact historical dates used to settle forecasts created before the recent window. */
    fun fetchHistoricalDates(lottery: LotteryType, dates: Set<LocalDate>): HistoricalFetchResult =
        fetchDates(lottery, dates.sorted().take(MAX_BACKFILL_DATES), cancellationGeneration.get())

    /**
     * Re-reads the latest upstream payload immediately before an AI or consensus result is frozen.
     * This prevents a result that crossed draw time from entering the forward archive.
     */
    fun verifyTargetPeriodOpen(
        lottery: LotteryType,
        targetPeriod: String,
        safetyWindowMs: Long = 5_000L,
    ): TargetPeriodCheck {
        val requestToken = cancellationGeneration.get()
        val latest = fetchLatestWithRetry(lottery, requestToken)
            ?: error("最新开奖接口没有返回有效期号")
        ensureActive(requestToken)
        return TargetPeriodGuard.evaluate(
            expectedTargetPeriod = targetPeriod,
            latestPeriod = latest.draw.period,
            nextPeriod = latest.nextPeriod,
            serverTimeEpochMs = latest.serverTimeEpochMs,
            nextDrawAtEpochMs = latest.nextDrawAtEpochMs,
            safetyWindowMs = safetyWindowMs,
        )
    }

    private fun fetchDates(
        lottery: LotteryType,
        dates: List<LocalDate>,
        requestToken: Int,
    ): HistoricalFetchResult {
        if (dates.isEmpty()) return HistoricalFetchResult(emptyList(), emptyList())
        val pool = Executors.newFixedThreadPool(min(6, dates.size))
        val futures = dates.associateWith { date ->
            pool.submit<List<Draw>> {
                fetchDateWithRetry(lottery, date.format(DateTimeFormatter.ISO_LOCAL_DATE), requestToken)
            }
        }
        val draws = mutableListOf<Draw>()
        val failed = mutableListOf<LocalDate>()
        try {
            futures.forEach { (date, future) ->
                runCatching { future.get(18, TimeUnit.SECONDS) }
                    .onSuccess(draws::addAll)
                    .onFailure { failed += date }
            }
        } finally {
            pool.shutdownNow()
        }
        return HistoricalFetchResult(
            draws = DrawMergePolicy.merge(draws),
            failedDates = failed.sorted(),
        )
    }

    private fun fetchDateWithRetry(lottery: LotteryType, date: String, requestToken: Int): List<Draw> {
        var failure: Throwable? = null
        repeat(2) { attempt ->
            ensureActive(requestToken)
            runCatching { fetchDate(lottery, date) }
                .onSuccess { return it }
                .onFailure { failure = it }
            if (attempt == 0) Thread.sleep(250)
        }
        throw failure ?: IllegalStateException("开奖历史同步失败：$date")
    }

    private fun fetchLatestWithRetry(lottery: LotteryType, requestToken: Int): LatestPayload? {
        var failure: Throwable? = null
        repeat(2) { attempt ->
            ensureActive(requestToken)
            runCatching { fetchLatest(lottery) }
                .onSuccess { if (it != null) return it }
                .onFailure { failure = it }
            if (attempt == 0) Thread.sleep(250)
        }
        failure?.let { throw it }
        return null
    }

    private fun ensureActive(requestToken: Int) {
        check(cancellationGeneration.get() == requestToken && !Thread.currentThread().isInterrupted) {
            "请求已被新的刷新任务取消"
        }
    }

    private fun fetchDate(lottery: LotteryType, date: String): List<Draw> {
        val url = "$baseUrl/pks/getPksHistoryList.do?lotCode=${lottery.lotCode}" +
            "&date=$date&pageSize=2000&_t=${System.currentTimeMillis()}"
        return parseDrawArray(unwrapData(request(url)), lottery)
    }

    private fun fetchLatest(lottery: LotteryType): LatestPayload? {
        val url = "$baseUrl/pks/getLotteryPksInfo.do?lotCode=${lottery.lotCode}" +
            "&_t=${System.currentTimeMillis()}"
        val payload = unwrapData(request(url))
        val value = when (payload) {
            is JSONObject -> payload
            is JSONArray -> payload.optJSONObject(0)
            else -> null
        } ?: return null
        val draw = parseDraw(value, lottery) ?: return null
        return LatestPayload(
            draw = draw,
            nextPeriod = firstText(value, "drawIssue", "nextIssue")
                .ifBlank { incrementPeriod(draw.period) },
            serverTimeEpochMs = ApiTimeParser.parseEpochMillis(firstText(value, "serverTime")),
            nextDrawAtEpochMs = ApiTimeParser.parseEpochMillis(firstText(value, "drawTime", "nextDrawTime")),
        )
    }

    private fun request(url: String): JSONObject {
        val connection = URL(url).openConnection() as HttpURLConnection
        activeConnections += connection
        return try {
            connection.requestMethod = "GET"
            connection.connectTimeout = 7_000
            connection.readTimeout = 7_000
            connection.useCaches = false
            connection.setRequestProperty("Accept", "application/json")
            connection.setRequestProperty("Cache-Control", "no-cache")
            connection.setRequestProperty("Referer", "https://www.168kai.com/")
            if (connection.responseCode !in 200..299) error("开奖接口 HTTP ${connection.responseCode}")
            val body = connection.inputStream.bufferedReader(Charsets.UTF_8).use { it.readText() }
            JSONObject(body)
        } finally {
            activeConnections -= connection
            connection.disconnect()
        }
    }

    private fun unwrapData(root: JSONObject): Any? {
        val result = root.opt("result")
        return when (result) {
            is JSONObject -> result.opt("data") ?: result
            null -> root.opt("data")
            else -> result
        }
    }

    private fun parseDrawArray(value: Any?, lottery: LotteryType): List<Draw> {
        val array = when (value) {
            is JSONArray -> value
            is JSONObject -> value.optJSONArray("list") ?: value.optJSONArray("data")
            else -> null
        } ?: return emptyList()
        return buildList {
            for (index in 0 until array.length()) {
                array.optJSONObject(index)?.let { parseDraw(it, lottery) }?.let(::add)
            }
        }
    }

    private fun parseDraw(value: JSONObject, lottery: LotteryType): Draw? {
        val period = firstText(value, "preDrawIssue", "issue", "period", "drawIssue")
        val numbers = firstText(value, "preDrawCode", "drawCode", "numbers", "code")
            .split(Regex("[,\\s|]+"))
            .mapNotNull(String::toIntOrNull)
            .filter { it in 1..10 }
            .take(10)
        if (period.isBlank() || numbers.size != 10 || numbers.toSet().size != 10) return null
        return Draw(
            lottery = lottery,
            period = period,
            numbers = numbers,
            drawTime = firstText(value, "preDrawTime", "openTime", "time"),
        )
    }

    private fun firstText(value: JSONObject, vararg keys: String): String {
        for (key in keys) {
            val item = value.opt(key) ?: continue
            if (item == JSONObject.NULL) continue
            item.toString().trim().takeIf(String::isNotBlank)?.let { return it }
        }
        return ""
    }

    private fun incrementPeriod(period: String): String {
        val match = Regex("^(.*?)(\\d+)$").matchEntire(period) ?: return "待同步"
        val prefix = match.groupValues[1]
        val digits = match.groupValues[2]
        return runCatching {
            prefix + java.math.BigInteger(digits).add(java.math.BigInteger.ONE)
                .toString().padStart(digits.length, '0')
        }.getOrDefault("待同步")
    }

    private data class LatestPayload(
        val draw: Draw,
        val nextPeriod: String,
        val serverTimeEpochMs: Long?,
        val nextDrawAtEpochMs: Long?,
    )

    private companion object {
        const val MAX_RECENT_DAYS = 14
        const val MAX_BACKFILL_DATES = 40
    }
}
