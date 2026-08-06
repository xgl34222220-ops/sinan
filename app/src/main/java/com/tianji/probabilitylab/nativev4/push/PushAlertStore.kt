package com.tianji.probabilitylab.nativev4.push

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import java.util.UUID
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

class PushAlertStore(context: Context) {
    private val preferences = context.getSharedPreferences("tianji-push-alerts", Context.MODE_PRIVATE)
    private val identityStore = SecurePushIdentityStore(preferences)
    private val _alerts = MutableStateFlow(loadAlerts())
    private val _settings = MutableStateFlow(loadPreferences())
    private val _status = MutableStateFlow(PushConnectionStatus())

    val alerts: StateFlow<List<PushAlert>> = _alerts.asStateFlow()
    val settings: StateFlow<PushPreferences> = _settings.asStateFlow()
    val status: StateFlow<PushConnectionStatus> = _status.asStateFlow()

    val installationId: String
        get() = preferences.getString(KEY_INSTALLATION_ID, null)
            ?: UUID.randomUUID().toString().also {
                preferences.edit().putString(KEY_INSTALLATION_ID, it).apply()
            }
    val deviceSecret: String get() = identityStore.deviceSecret()

    var fcmToken: String
        get() = preferences.getString(KEY_FCM_TOKEN, "").orEmpty()
        set(value) { preferences.edit().putString(KEY_FCM_TOKEN, value).apply() }
    var initialSyncComplete: Boolean
        get() = preferences.getBoolean(KEY_INITIAL_SYNC, false)
        set(value) { preferences.edit().putBoolean(KEY_INITIAL_SYNC, value).apply() }
    var lastServerAlertId: Long
        get() = preferences.getLong(KEY_LAST_SERVER_ALERT_ID, 0L)
        private set(value) {
            preferences.edit().putLong(KEY_LAST_SERVER_ALERT_ID, value.coerceAtLeast(0L)).apply()
        }

    fun updateStatus(value: PushConnectionStatus) { _status.value = value }

    fun updatePreferences(value: PushPreferences) {
        preferences.edit()
            .putBoolean(KEY_ENABLED, value.enabled)
            .putBoolean(KEY_XYFT, value.xyftEnabled)
            .putBoolean(KEY_AZXY10, value.azxy10Enabled)
            .putBoolean(KEY_AI, value.aiEnabled)
            .putBoolean(KEY_NATIVE, value.nativeEnabled)
            .putBoolean(KEY_ESCALATION, value.escalationEnabled)
            .apply()
        _settings.value = value
    }

    fun mergeAlerts(values: List<PushAlert>): List<PushAlert> {
        if (values.isEmpty()) return emptyList()
        val previous = _alerts.value.associateBy(PushAlert::id)
        val merged = (values + _alerts.value)
            .groupBy(PushAlert::id)
            .map { (_, items) ->
                val remote = items.first()
                remote.copy(isRead = remote.isRead || previous[remote.id]?.isRead == true)
            }
            .sortedByDescending(PushAlert::id)
            .take(MAX_ALERTS)
        _alerts.value = merged
        saveAlerts(merged)
        return values.filter { it.id !in previous }
    }

    fun advanceServerCursor(values: List<PushAlert>) {
        values.maxOfOrNull(PushAlert::id)?.let { latest ->
            if (latest > lastServerAlertId) lastServerAlertId = latest
        }
    }

    fun markRead(alertId: Long) {
        val updated = _alerts.value.map { if (it.id == alertId) it.copy(isRead = true) else it }
        _alerts.value = updated
        saveAlerts(updated)
    }

    fun markAllRead() {
        val updated = _alerts.value.map { it.copy(isRead = true) }
        _alerts.value = updated
        saveAlerts(updated)
    }

    private fun loadPreferences() = PushPreferences(
        enabled = preferences.getBoolean(KEY_ENABLED, true),
        xyftEnabled = preferences.getBoolean(KEY_XYFT, true),
        azxy10Enabled = preferences.getBoolean(KEY_AZXY10, true),
        aiEnabled = preferences.getBoolean(KEY_AI, true),
        nativeEnabled = preferences.getBoolean(KEY_NATIVE, true),
        escalationEnabled = preferences.getBoolean(KEY_ESCALATION, true),
    )

    private fun loadAlerts(): List<PushAlert> = runCatching {
        val array = JSONArray(preferences.getString(KEY_ALERTS, "[]").orEmpty())
        buildList {
            for (index in 0 until array.length()) array.optJSONObject(index)?.toAlert()?.let(::add)
        }
    }.getOrDefault(emptyList())

    private fun saveAlerts(values: List<PushAlert>) {
        val array = JSONArray()
        values.forEach { array.put(it.toJson()) }
        preferences.edit().putString(KEY_ALERTS, array.toString()).apply()
    }

    private fun PushAlert.toJson() = JSONObject()
        .put("id", id).put("event_key", eventKey).put("lottery", lottery)
        .put("lottery_name", lotteryName).put("source", source)
        .put("source_name", sourceName).put("model", model).put("streak", streak)
        .put("threshold", threshold).put("latest_target_period", latestTargetPeriod)
        .put("recent_periods", JSONArray(recentPeriods)).put("title", title).put("body", body)
        .put("created_at_epoch_ms", createdAtEpochMs).put("is_read", isRead)
        .put("schema_version", schemaVersion).put("event_type", eventType)
        .put("severity", severity).put("deep_link", deepLink).put("collapse_key", collapseKey)
        .apply { expiresAtEpochMs?.let { put("expires_at_epoch_ms", it) } }

    private fun JSONObject.toAlert(): PushAlert? {
        val id = optLong("id", -1L)
        if (id <= 0L) return null
        return PushAlert(
            id = id,
            eventKey = optString("event_key"), lottery = optString("lottery"),
            lotteryName = optString("lottery_name"), source = optString("source"),
            sourceName = optString("source_name"), model = optString("model"),
            streak = optInt("streak", 0), threshold = optInt("threshold", 3),
            latestTargetPeriod = optString("latest_target_period"),
            recentPeriods = optJSONArray("recent_periods").toStrings(),
            title = optString("title", "天机提醒"), body = optString("body"),
            createdAtEpochMs = optLong("created_at_epoch_ms", System.currentTimeMillis()),
            isRead = optBoolean("is_read", false), schemaVersion = optInt("schema_version", 1),
            eventType = optString("event_type", PushProtocol.EVENT_MISS_ALERT),
            severity = optString("severity", PushProtocol.SEVERITY_WARNING),
            deepLink = optString("deep_link"), collapseKey = optString("collapse_key"),
            expiresAtEpochMs = if (has("expires_at_epoch_ms")) optLong("expires_at_epoch_ms") else null,
        )
    }

    private fun JSONArray?.toStrings(): List<String> = if (this == null) emptyList() else buildList {
        for (index in 0 until length()) optString(index).takeIf(String::isNotBlank)?.let(::add)
    }

    companion object {
        private const val MAX_ALERTS = 200
        private const val KEY_INSTALLATION_ID = "installation_id"
        private const val KEY_FCM_TOKEN = "fcm_token"
        private const val KEY_INITIAL_SYNC = "initial_sync_complete"
        private const val KEY_LAST_SERVER_ALERT_ID = "last_server_alert_id"
        private const val KEY_ALERTS = "alerts"
        private const val KEY_ENABLED = "enabled"
        private const val KEY_XYFT = "xyft_enabled"
        private const val KEY_AZXY10 = "azxy10_enabled"
        private const val KEY_AI = "ai_enabled"
        private const val KEY_NATIVE = "native_enabled"
        private const val KEY_ESCALATION = "escalation_enabled"
    }
}
