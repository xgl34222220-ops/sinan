package com.tianji.probabilitylab.nativev4.data

import com.tianji.probabilitylab.nativev4.BuildConfig
import com.tianji.probabilitylab.nativev4.ai.AiAnalysisMode
import com.tianji.probabilitylab.nativev4.ai.AiForecastRecord
import com.tianji.probabilitylab.nativev4.ai.AiReasoningMode
import com.tianji.probabilitylab.nativev4.ai.AiReasoningProtocol
import com.tianji.probabilitylab.nativev4.ai.AiReasoningState
import com.tianji.probabilitylab.nativev4.model.LotteryType
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.util.concurrent.ConcurrentHashMap
import kotlin.math.absoluteValue

/**
 * Read-only cloud archive client. Failure is deliberately non-fatal: AppController keeps the
 * existing direct开奖、手机直连 AI and local statistical paths when the VPS is unavailable.
 */
class CloudForecastApi {
    private val activeConnections = ConcurrentHashMap.newKeySet<HttpURLConnection>()

    fun cancelActiveRequests() {
        activeConnections.toList().forEach(HttpURLConnection::disconnect)
        activeConnections.clear()
    }

    fun fetchForecasts(lottery: LotteryType, limit: Int = 120): List<AiForecastRecord> {
        val baseUrl = BuildConfig.TIANJI_CLOUD_BASE_URL.trim().trimEnd('/')
        if (!baseUrl.startsWith("https://")) return emptyList()
        val url = URL("$baseUrl/v1/forecasts/${lottery.apiKey}?limit=${limit.coerceIn(1, 500)}")
        val connection = url.openConnection() as HttpURLConnection
        activeConnections += connection
        return try {
            connection.requestMethod = "GET"
            connection.connectTimeout = 3_000
            connection.readTimeout = 5_000
            connection.useCaches = false
            connection.setRequestProperty("Accept", "application/json")
            connection.setRequestProperty("Cache-Control", "no-cache")
            val code = connection.responseCode
            if (code !in 200..299) return emptyList()
            val body = connection.inputStream.bufferedReader(Charsets.UTF_8).use { it.readText() }
            parseForecasts(JSONArray(body), lottery)
        } finally {
            activeConnections -= connection
            connection.disconnect()
        }
    }

    private fun parseForecasts(array: JSONArray, lottery: LotteryType): List<AiForecastRecord> =
        buildList {
            for (index in 0 until array.length()) {
                val value = array.optJSONObject(index) ?: continue
                value.toRecord(lottery)?.let(::add)
            }
        }

    private fun JSONObject.toRecord(lottery: LotteryType): AiForecastRecord? {
        val targetPeriod = optString("target_period").trim()
        val trainedThrough = optString("trained_through_period").trim()
        val position = optInt("position", -1)
        val top6 = optJSONArray("top6").toIntList()
        val top7 = optJSONArray("top7").toIntList()
        val probabilities = optJSONArray("probabilities").toDoubleList()
        val source = optString("source").trim().ifBlank { "cloud" }
        val model = optString("model").trim().ifBlank { "tianji-cloud" }
        if (
            targetPeriod.isBlank() ||
            trainedThrough.isBlank() ||
            position !in 0..9 ||
            top6.size != 6 ||
            top7.size != 7 ||
            probabilities.size != 10
        ) return null

        val stableKey = "$targetPeriod|$source|$model|$position"
        val cloudId = -(stableKey.hashCode().toLong().absoluteValue + 1L)
        val isAi = source.equals("ai", ignoreCase = true)
        val actual = optNullableInt("actual_number")
        return AiForecastRecord(
            id = cloudId,
            lottery = lottery,
            profileId = "cloud:$source:$model",
            profileName = if (isAi) "天机云端 AI" else "天机云端本机",
            targetPeriod = targetPeriod,
            trainedThroughPeriod = trainedThrough,
            position = position,
            top6 = top6,
            top7 = top7,
            probabilities = probabilities,
            analysis = optString("analysis").ifBlank { "服务器后台生成并按目标期冻结" },
            riskNote = optString("risk_note").ifBlank { "随机开奖不可可靠预测，仅用于前向验证" },
            selfRating = probabilities.sortedDescending().take(6).sum().coerceIn(0.0, 1.0),
            model = model,
            analysisMode = AiAnalysisMode.DEEP,
            reasoningMode = if (isAi) AiReasoningMode.AUTO else AiReasoningMode.LOW,
            reasoningProtocol = if (isAi) AiReasoningProtocol.AUTO else AiReasoningProtocol.NONE,
            reasoningState = if (isAi) AiReasoningState.DEFAULT else AiReasoningState.UNSUPPORTED,
            reasoningTokens = null,
            inputTokens = null,
            outputTokens = null,
            estimatedCost = null,
            executionNote = "云端全天后台生成 · 服务器不可用时不影响手机本地模式",
            createdAtEpochMs = optLong("created_at_epoch_ms", System.currentTimeMillis()),
            latencyMs = 0L,
            responseId = "cloud-${optLong("id", cloudId.absoluteValue)}",
            forecastHash = "cloud-$stableKey",
            previousHash = "",
            actualNumber = actual,
            top6Hit = optNullableBoolean("top6_hit"),
            top7Hit = optNullableBoolean("top7_hit"),
            brierScore = null,
            logLoss = null,
            actualRank = actual?.let { number ->
                probabilities.indices
                    .sortedByDescending { probabilities[it] }
                    .indexOf(number - 1)
                    .takeIf { it >= 0 }
                    ?.plus(1)
            },
        )
    }

    private fun JSONArray?.toIntList(): List<Int> = if (this == null) {
        emptyList()
    } else {
        buildList {
            for (index in 0 until length()) {
                optInt(index).takeIf { it in 1..10 }?.let(::add)
            }
        }
    }

    private fun JSONArray?.toDoubleList(): List<Double> = if (this == null) {
        emptyList()
    } else {
        buildList {
            for (index in 0 until length()) {
                val value = optDouble(index, Double.NaN)
                if (!value.isFinite() || value < 0.0) return emptyList()
                add(value)
            }
        }
    }

    private fun JSONObject.optNullableInt(key: String): Int? =
        if (!has(key) || isNull(key)) null else optInt(key)

    private fun JSONObject.optNullableBoolean(key: String): Boolean? =
        if (!has(key) || isNull(key)) null else optBoolean(key)
}
