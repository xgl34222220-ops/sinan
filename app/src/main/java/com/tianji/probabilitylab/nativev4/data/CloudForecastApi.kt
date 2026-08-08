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
 * Read-only cloud AI archive client. Native cloud forecasts are deliberately excluded here:
 * AppController already has a separate local/native forecast path and mixing the two would pollute
 * the UI's AI vote count and consensus semantics.
 *
 * Cloud history is secondary UI data, so it must never hold the latest-draw path for several
 * seconds. Successful responses are cached per lottery and reused on a timeout or transient error.
 */
class CloudForecastApi {
    private val activeConnections = ConcurrentHashMap.newKeySet<HttpURLConnection>()
    private val forecastCache = ConcurrentHashMap<LotteryType, List<AiForecastRecord>>()

    fun cancelActiveRequests() {
        activeConnections.toList().forEach(HttpURLConnection::disconnect)
        activeConnections.clear()
    }

    fun fetchForecasts(lottery: LotteryType, limit: Int = 120): List<AiForecastRecord> {
        val cached = forecastCache[lottery].orEmpty()
        val baseUrl = BuildConfig.TIANJI_CLOUD_BASE_URL.trim().trimEnd('/')
        if (!baseUrl.startsWith("https://")) return cached
        val url = URL("$baseUrl/v1/forecasts/${lottery.apiKey}?limit=${limit.coerceIn(1, 500)}")
        val connection = url.openConnection() as HttpURLConnection
        activeConnections += connection
        return try {
            connection.requestMethod = "GET"
            connection.connectTimeout = 1_500
            connection.readTimeout = 2_500
            connection.useCaches = false
            connection.setRequestProperty("Accept", "application/json")
            connection.setRequestProperty("Cache-Control", "no-cache")
            val code = connection.responseCode
            if (code !in 200..299) return cached
            val body = connection.inputStream.bufferedReader(Charsets.UTF_8).use { it.readText() }
            val parsed = parseForecasts(JSONArray(body), lottery)
            forecastCache[lottery] = parsed
            parsed
        } catch (_: Exception) {
            cached
        } finally {
            activeConnections -= connection
            connection.disconnect()
        }
    }

    private fun parseForecasts(array: JSONArray, lottery: LotteryType): List<AiForecastRecord> =
        buildList {
            for (index in 0 until array.length()) {
                val value = array.optJSONObject(index) ?: continue
                if (!value.optString("source").trim().equals("ai", ignoreCase = true)) continue
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
        val source = "ai"
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
        val actual = optNullableInt("actual_number")
        return AiForecastRecord(
            id = cloudId,
            lottery = lottery,
            profileId = "cloud:ai:$model",
            profileName = "天机云端 AI",
            targetPeriod = targetPeriod,
            trainedThroughPeriod = trainedThrough,
            position = position,
            top6 = top6,
            top7 = top7,
            probabilities = probabilities,
            analysis = localizeCloudAnalysis(optString("analysis")),
            riskNote = localizeCloudRisk(optString("risk_note")),
            selfRating = probabilities.sortedDescending().take(6).sum().coerceIn(0.0, 1.0),
            model = model,
            analysisMode = AiAnalysisMode.DEEP,
            reasoningMode = AiReasoningMode.AUTO,
            reasoningProtocol = AiReasoningProtocol.AUTO,
            reasoningState = AiReasoningState.DEFAULT,
            reasoningTokens = null,
            inputTokens = null,
            outputTokens = null,
            estimatedCost = null,
            executionNote = "云端 AI 全天后台生成 · 服务器不可用时不影响手机本地模式",
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

    private fun localizeCloudAnalysis(raw: String): String {
        val value = raw.trim()
        if (value.isBlank()) return "服务器后台生成并按目标期冻结"
        if (value.containsChinese()) return value

        val frequencyPattern = Regex(
            pattern = """Position\s+(\d+)\s+shows\s+number\s+(\d+)\s+appearing\s+(\d+)\s+times\s+in\s+last\s+(\d+)\s+draws,?\s*highest\s+frequency\.?\s*Recent\s+trend\s+favors\s+(\d+),?\s*with\s+last\s+draw\s+being\s+(\d+)\.?""",
            option = RegexOption.IGNORE_CASE,
        )
        frequencyPattern.find(value)?.let { match ->
            val (position, number, count, draws, favored, last) = match.destructured
            return "第${position}名中，号码${number}在最近${draws}期出现${count}次，出现频率最高；近期走势偏向号码${favored}，最近一期为号码${last}。"
        }

        return "模型返回的说明不是中文，已隐藏英文原文；请以号码矩阵和真实前向验证结果为准。"
    }

    private fun localizeCloudRisk(raw: String): String {
        val value = raw.trim()
        if (value.isBlank()) return "随机开奖不可可靠预测，仅用于前向验证"
        if (value.containsChinese()) return value

        val normalized = value.lowercase()
        if (
            "small sample" in normalized ||
            "randomness" in normalized ||
            "no guarantee" in normalized ||
            "future outcome" in normalized
        ) {
            return "样本量较小，随机性可能造成偏差；不能保证未来结果。"
        }
        return "随机开奖不可可靠预测；英文风险说明已转为中文兜底，仅用于前向验证。"
    }

    private fun String.containsChinese(): Boolean = any { character ->
        character.code in 0x3400..0x9FFF
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
