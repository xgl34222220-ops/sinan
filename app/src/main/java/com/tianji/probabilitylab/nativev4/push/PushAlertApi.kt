package com.tianji.probabilitylab.nativev4.push

import android.os.Build
import com.tianji.probabilitylab.nativev4.BuildConfig
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder

class PushAlertApi {
    private fun baseUrl(): String = BuildConfig.TIANJI_CLOUD_BASE_URL.trim().trimEnd('/')

    fun register(store: PushAlertStore, preferences: PushPreferences): PushConnectionStatus {
        val body = JSONObject()
            .put("installation_id", store.installationId)
            .put("secret", store.deviceSecret)
            .put("fcm_token", store.fcmToken)
            .put("platform", "android")
            .put("app_version", BuildConfig.VERSION_NAME)
            .put("device_name", "${Build.MANUFACTURER} ${Build.MODEL}".trim())
            .put("preferences", preferences.toJson())
        return request("POST", "/v1/push/devices", body, store).toStatus(
            FirebasePushBootstrap.isConfigured,
            store.fcmToken.isNotBlank(),
        )
    }

    fun updatePreferences(store: PushAlertStore, preferences: PushPreferences): PushConnectionStatus =
        request(
            "PUT",
            "/v1/push/devices/${encode(store.installationId)}/preferences",
            preferences.toJson(),
            store,
        ).toStatus(FirebasePushBootstrap.isConfigured, store.fcmToken.isNotBlank())

    fun fetchAlerts(store: PushAlertStore, afterId: Long = store.lastServerAlertId): List<PushAlert> {
        val path = "/v1/push/alerts?installation_id=${encode(store.installationId)}" +
            "&limit=120&after_id=${afterId.coerceAtLeast(0L)}"
        val items = request("GET", path, null, store).optJSONArray("items") ?: JSONArray()
        return buildList {
            for (index in 0 until items.length()) {
                items.optJSONObject(index)?.let(PushPayloadParser::fromJson)?.let(::add)
            }
        }
    }

    fun markRead(store: PushAlertStore, alertId: Long) {
        request(
            "POST",
            "/v1/push/alerts/$alertId/read?installation_id=${encode(store.installationId)}",
            JSONObject(),
            store,
        )
    }

    fun markAllRead(store: PushAlertStore) {
        request(
            "POST",
            "/v1/push/alerts/read-all?installation_id=${encode(store.installationId)}",
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
            connection.setRequestProperty("X-Tianji-Protocol", PushProtocol.VERSION.toString())
            connection.setRequestProperty(
                "User-Agent",
                "Tianji/${BuildConfig.VERSION_NAME} Android/${Build.VERSION.SDK_INT}",
            )
            if (body != null) {
                connection.doOutput = true
                connection.setRequestProperty("Content-Type", "application/json; charset=UTF-8")
                connection.outputStream.use {
                    it.write(body.toString().toByteArray(Charsets.UTF_8))
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
        .put("enabled", enabled).put("xyft_enabled", xyftEnabled)
        .put("azxy10_enabled", azxy10Enabled).put("ai_enabled", aiEnabled)
        .put("native_enabled", nativeEnabled).put("escalation_enabled", escalationEnabled)

    private fun JSONObject.toStatus(
        firebaseConfigured: Boolean,
        fcmTokenPresent: Boolean,
    ): PushConnectionStatus {
        val registered = optBoolean("registered", true)
        val serverConfigured = optBoolean("push_configured", false)
        val fallbackMinutes = optInt("fallback_poll_minutes", 15)
        val notificationEnabled = PushNotificationManager.notificationsEnabled
        return PushConnectionStatus(
            registered = registered,
            firebaseConfigured = firebaseConfigured,
            serverConfigured = serverConfigured,
            fcmTokenPresent = fcmTokenPresent,
            fallbackMinutes = fallbackMinutes,
            protocolVersion = optInt("protocol_version", 1),
            lastSyncedAtEpochMs = System.currentTimeMillis(),
            detail = when {
                !notificationEnabled -> "系统通知权限未开启；预警中心仍会同步"
                registered && firebaseConfigured && serverConfigured && fcmTokenPresent ->
                    "FCM 即时推送已连接，${fallbackMinutes} 分钟后台检查作为兜底"
                !firebaseConfigured && !serverConfigured ->
                    "当前 APK 与云端均未配置 FCM，暂用 ${fallbackMinutes} 分钟后台检查"
                !firebaseConfigured -> "当前 APK 未注入 Firebase 客户端配置"
                firebaseConfigured && !fcmTokenPresent -> "正在等待设备令牌"
                !serverConfigured -> "设备令牌已取得，但云端服务账号尚未配置"
                !registered -> "设备尚未完成云端注册"
                else -> "FCM 正在建立连接"
            },
        )
    }

    private fun encode(value: String): String = URLEncoder.encode(value, Charsets.UTF_8.name())
}
