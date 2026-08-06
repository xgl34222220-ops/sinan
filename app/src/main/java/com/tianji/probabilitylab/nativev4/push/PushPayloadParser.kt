package com.tianji.probabilitylab.nativev4.push

import org.json.JSONArray
import org.json.JSONObject

internal object PushPayloadParser {
    fun fromJson(value: JSONObject): PushAlert? {
        val id = value.optLong("id", -1L)
        if (id <= 0L) return null
        val data = value.optJSONObject("data") ?: JSONObject()
        val streak = value.optInt("streak", data.optString("streak").toIntOrNull() ?: 0)
        val threshold = value.optInt("threshold", data.optString("threshold").toIntOrNull() ?: 3)
        val eventType = firstNonBlank(
            value.optString("event_type"),
            data.optString("event_type"),
            legacyEventType(data.optString("type"), streak, threshold),
        )
        return PushAlert(
            id = id,
            eventKey = firstNonBlank(value.optString("event_key"), data.optString("event_key")),
            lottery = firstNonBlank(value.optString("lottery"), data.optString("lottery")),
            lotteryName = firstNonBlank(value.optString("lottery_name"), data.optString("lottery_name")),
            source = firstNonBlank(value.optString("source"), data.optString("source")),
            sourceName = firstNonBlank(value.optString("source_name"), data.optString("source_name")),
            model = firstNonBlank(value.optString("model"), data.optString("model")),
            streak = streak,
            threshold = threshold,
            latestTargetPeriod = firstNonBlank(
                value.optString("latest_target_period"),
                data.optString("latest_target_period"),
            ),
            recentPeriods = value.optJSONArray("recent_periods").toStrings().ifEmpty {
                data.optString("recent_periods").split(',').map(String::trim).filter(String::isNotBlank)
            },
            title = firstNonBlank(
                value.optString("title"),
                data.optString("title"),
                defaultTitle(eventType, streak),
            ),
            body = firstNonBlank(value.optString("body"), data.optString("body")),
            createdAtEpochMs = value.optLong(
                "created_at_epoch_ms",
                data.optString("created_at_epoch_ms").toLongOrNull() ?: System.currentTimeMillis(),
            ),
            isRead = value.optBoolean("is_read", false),
            schemaVersion = value.optInt(
                "schema_version",
                data.optString("schema_version").toIntOrNull() ?: 1,
            ),
            eventType = eventType,
            severity = firstNonBlank(
                value.optString("severity"),
                data.optString("severity"),
                defaultSeverity(eventType),
            ),
            deepLink = firstNonBlank(value.optString("deep_link"), data.optString("deep_link")),
            collapseKey = firstNonBlank(
                value.optString("collapse_key"),
                data.optString("collapse_key"),
            ),
            expiresAtEpochMs = value.longOrNull("expires_at_epoch_ms")
                ?: data.optString("expires_at_epoch_ms").toLongOrNull(),
        )
    }

    fun fromRemoteData(data: Map<String, String>): PushAlert? {
        val id = data["alert_id"]?.toLongOrNull() ?: return null
        val streak = data["streak"]?.toIntOrNull() ?: 0
        val threshold = data["threshold"]?.toIntOrNull() ?: 3
        val eventType = firstNonBlank(
            data["event_type"].orEmpty(),
            legacyEventType(data["type"].orEmpty(), streak, threshold),
        )
        return PushAlert(
            id = id,
            eventKey = data["event_key"].orEmpty(),
            lottery = data["lottery"].orEmpty(),
            lotteryName = data["lottery_name"].orEmpty(),
            source = data["source"].orEmpty(),
            sourceName = data["source_name"].orEmpty(),
            model = data["model"].orEmpty(),
            streak = streak,
            threshold = threshold,
            latestTargetPeriod = data["latest_target_period"].orEmpty(),
            recentPeriods = data["recent_periods"].orEmpty()
                .split(',').map(String::trim).filter(String::isNotBlank),
            title = firstNonBlank(data["title"].orEmpty(), defaultTitle(eventType, streak)),
            body = data["body"].orEmpty().ifBlank { defaultBody(data, streak) },
            createdAtEpochMs = data["created_at_epoch_ms"]?.toLongOrNull()
                ?: System.currentTimeMillis(),
            isRead = false,
            schemaVersion = data["schema_version"]?.toIntOrNull() ?: 1,
            eventType = eventType,
            severity = firstNonBlank(data["severity"].orEmpty(), defaultSeverity(eventType)),
            deepLink = data["deep_link"].orEmpty(),
            collapseKey = data["collapse_key"].orEmpty(),
            expiresAtEpochMs = data["expires_at_epoch_ms"]?.toLongOrNull(),
        )
    }

    private fun legacyEventType(type: String, streak: Int, threshold: Int): String {
        if (type.isNotBlank() && type != "prediction_miss_alert") return type
        return when {
            streak <= 2 -> PushProtocol.EVENT_MISS_PREALERT
            streak > threshold -> PushProtocol.EVENT_MISS_ESCALATION
            else -> PushProtocol.EVENT_MISS_ALERT
        }
    }

    private fun defaultSeverity(eventType: String): String = when (eventType) {
        PushProtocol.EVENT_PREDICTION_READY -> PushProtocol.SEVERITY_INFO
        PushProtocol.EVENT_HIT_RECOVERY -> PushProtocol.SEVERITY_SUCCESS
        PushProtocol.EVENT_MISS_ESCALATION -> PushProtocol.SEVERITY_CRITICAL
        PushProtocol.EVENT_MISS_ALERT,
        PushProtocol.EVENT_SERVICE_WARNING -> PushProtocol.SEVERITY_WARNING
        else -> PushProtocol.SEVERITY_INFO
    }

    private fun defaultTitle(eventType: String, streak: Int): String = when (eventType) {
        PushProtocol.EVENT_PREDICTION_READY -> "新一期云端 AI 预测"
        PushProtocol.EVENT_HIT_RECOVERY -> "连续不中后恢复命中"
        PushProtocol.EVENT_MISS_PREALERT -> "两期不中预警"
        PushProtocol.EVENT_MISS_ESCALATION -> "连续 $streak 期不中升级预警"
        PushProtocol.EVENT_SERVICE_WARNING -> "天机服务异常"
        else -> "三期不中加强提醒"
    }

    private fun defaultBody(data: Map<String, String>, streak: Int): String = buildString {
        append(data["lottery_name"].orEmpty())
        if (!data["source_name"].isNullOrBlank()) append(" · ${data["source_name"]}")
        if (!data["model"].isNullOrBlank()) append(" · ${data["model"]}")
        if (streak > 0) append(" 已连续 $streak 期 Top 6 未命中")
    }

    private fun firstNonBlank(vararg values: String): String =
        values.firstOrNull(String::isNotBlank).orEmpty()

    private fun JSONObject.longOrNull(key: String): Long? =
        if (has(key) && !isNull(key)) optLong(key) else null

    private fun JSONArray?.toStrings(): List<String> = if (this == null) {
        emptyList()
    } else {
        buildList {
            for (index in 0 until length()) {
                optString(index).takeIf(String::isNotBlank)?.let(::add)
            }
        }
    }
}
