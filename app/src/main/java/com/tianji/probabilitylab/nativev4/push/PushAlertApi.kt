package com.tianji.probabilitylab.nativev4.push

import android.os.Build
import com.tianji.probabilitylab.nativev4.BuildConfig
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

class PushAlertApi {
    private fun baseUrl(): String = BuildConfig.TIANJI_CLOUD_BASE_URL.trim().trimEnd('/')

    fun register(
        store: PushAlertStore,
        preferences: PushPreferences,
    ): PushConnectionStatus {
        val body = JSONObject()
            .put("installation_id", store.installationId)
            .put("secret", store.deviceSecret)
            .put("fcm_token", store.fcmToken)
            .put("platform", "android")
            .put("app_version", BuildConfig.VERSION_NAME)
            .put("device_name", "${Build.MANUFACTURER} ${Build.MODEL}".trim())
            .put("preferences", preferences.toJson())
        val response = request("POST", "/v1/push/devices", body, store)
        return response.toStatus(
            firebaseConfigured = FirebasePushBootstrap.isConfigured,
            fcmTokenPresent = store.fcmToken.isNotBlank(),
        )
    }

    fun updatePreferences(
        store: PushAlertStore,
        preferences: PushPreferences,
    ): PushConnectionStatus {
        val response = request(
            "PUT",
            "/v1/push/devices/${store.installationId}/preferences",
            preferences.toJson(),
            store,
        )
        return response.toStatus(
            firebaseConfigured = FirebasePushBootstrap.isConfigured,
            fcmTokenPresent = store.fcmToken.isNotBlank(),
        )
    }

    fun fetchAlerts(store: PushAlertStore): List<PushAlert> {
        val path = "/v1/push/alerts?installation_id=${store.installationId}&limit=120"
        val response = request("GET", path, null, store)
        val items = response.optJSONArray("items") ?: JSONArray()
        return buildList {
            for (index in 0 until items.length()) {
                items.optJSONObject(index)?.toAlert()?.let(::add)
            }
        }
    }

    fun markRead(store: PushAlertStore, alertId: Long) {
        request(
            "POST",
            "/v1/push/alerts/$alertId/read?installation_id=${store.installationId}",
            JSONObject(),
            store,
        )
    }

    fun markAllRead(store: PushAlertStore) {
        request(
            "POST",
            "/v1/push/alerts/read-all?installation_id=${store.installationId}",
            JSONObject(),
            store,
        )
    }

    private fun request(
        method: String,
        path: String,
        body: JSONObject?,
        store: PushAlertStore,
    ): JSONObject {
        val base = baseUrl()
        require(base.startsWith("https://")) { "云端地址无效" }
        val connection = URL("$base$path").openConnection() as HttpURLConnection
        return try {
            connection.requestMethod = method
            connection.connectTimeout = 5_000
            connection.readTimeout = 8_000
            connection.useCaches = false
            connection.setRequestProperty("Accept", "application/json")
            connection.setRequestProperty("X-Tianji-Device-Secret", store.deviceSecret)
            if (body != null) {
                connection.doOutput = true
                connection.setRequestProperty("Content-Type", "application/json; charset=UTF-8")
                connection.outputStream.use { output ->
                    output.write(body.toString().toByteArray(Charsets.UTF_8))
                }
            }
            val code = connection.responseCode
            val stream = if (code in 200..299) connection.inputStream else connection.errorStream
            val text = stream?.bufferedReader(Charsets.UTF_8)?.use { it.readText() }.orEmpty()
            if (code !in 200..299) {
                val detail = runCatching { JSONObject(text).optString("detail") }.getOrNull()
                error(detail?.takeIf(String::isNotBlank) ?: "云端预警请求失败（$code）")
            }
            if (text.isBlank()) JSONObject() else JSONObject(text)
        } finally {
            connection.disconnect()
        }
    }

    private fun PushPreferences.toJson() = JSONObject()
        .put("enabled", enabled)
        .put("xyft_enabled", xyftEnabled)
        .put("azxy10_enabled", azxy10Enabled)
        .put("ai_enabled", aiEnabled)
        .put("native_enabled", nativeEnabled)
        .put("escalation_enabled", escalationEnabled)

    private fun JSONObject.toStatus(
        firebaseConfigured: Boolean,
        fcmTokenPresent: Boolean,
    ) = PushConnectionStatus(
        registered = optBoolean("registered", true),
        firebaseConfigured = firebaseConfigured,
        fcmTokenPresent = fcmTokenPresent,
        fallbackMinutes = optInt("fallback_poll_minutes", 15),
        detail = when {
            firebaseConfigured && fcmTokenPresent -> "即时推送已连接，15 分钟后台检查作为兜底"
            firebaseConfigured -> "Firebase 已配置，正在等待设备令牌"
            else -> "即时推送尚未配置，当前使用 15 分钟后台检查"
        },
    )

    private fun JSONObject.toAlert(): PushAlert? {
        val id = optLong("id", -1L)
        if (id <= 0L) return null
        return PushAlert(
            id = id,
            eventKey = optString("event_key"),
            lottery = optString("lottery"),
            lotteryName = optString("lottery_name"),
            source = optString("source"),
            sourceName = optString("source_name"),
            model = optString("model"),
            streak = optInt("streak", 3),
            threshold = optInt("threshold", 3),
            latestTargetPeriod = optString("latest_target_period"),
            recentPeriods = optJSONArray("recent_periods").toStrings(),
            title = optString("title", "三期不中预警"),
            body = optString("body"),
            createdAtEpochMs = optLong("created_at_epoch_ms", System.currentTimeMillis()),
            isRead = optBoolean("is_read", false),
        )
    }

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
