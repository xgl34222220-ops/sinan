package com.tianji.probabilitylab.nativev4.push

object PushProtocol {
    const val VERSION = 2
    const val EVENT_PREDICTION_READY = "prediction_ready"
    const val EVENT_MISS_PREALERT = "miss_prealert"
    const val EVENT_MISS_ALERT = "miss_alert"
    const val EVENT_MISS_ESCALATION = "miss_escalation"
    const val EVENT_HIT_RECOVERY = "hit_recovery"
    const val EVENT_SERVICE_WARNING = "service_warning"
    const val EVENT_SYSTEM_NOTICE = "system_notice"
    const val SEVERITY_INFO = "info"
    const val SEVERITY_SUCCESS = "success"
    const val SEVERITY_WARNING = "warning"
    const val SEVERITY_CRITICAL = "critical"
}

data class PushAlert(
    val id: Long,
    val eventKey: String,
    val lottery: String,
    val lotteryName: String,
    val source: String,
    val sourceName: String,
    val model: String,
    val streak: Int,
    val threshold: Int,
    val latestTargetPeriod: String,
    val recentPeriods: List<String>,
    val title: String,
    val body: String,
    val createdAtEpochMs: Long,
    val isRead: Boolean,
    val schemaVersion: Int = 1,
    val eventType: String = PushProtocol.EVENT_MISS_ALERT,
    val severity: String = PushProtocol.SEVERITY_WARNING,
    val deepLink: String = "",
    val collapseKey: String = "",
    val expiresAtEpochMs: Long? = null,
) {
    val isExpired: Boolean
        get() = expiresAtEpochMs?.let { it <= System.currentTimeMillis() } == true

    val isRiskAlert: Boolean
        get() = eventType in setOf(
            PushProtocol.EVENT_MISS_PREALERT,
            PushProtocol.EVENT_MISS_ALERT,
            PushProtocol.EVENT_MISS_ESCALATION,
            PushProtocol.EVENT_SERVICE_WARNING,
        )

    val stableNotificationKey: String
        get() = collapseKey.ifBlank {
            // A warning that grows from two misses to three or more must update the
            // same system notification instead of creating one notification per level.
            listOf(lottery, source, model).joinToString(":")
        }
}

data class PushPreferences(
    val enabled: Boolean = true,
    val xyftEnabled: Boolean = true,
    val azxy10Enabled: Boolean = true,
    val aiEnabled: Boolean = true,
    val nativeEnabled: Boolean = true,
    val escalationEnabled: Boolean = true,
) {
    fun accepts(alert: PushAlert): Boolean {
        if (!enabled || alert.isExpired) return false
        if (alert.lottery == "xyft" && !xyftEnabled) return false
        if (alert.lottery == "azxy10" && !azxy10Enabled) return false
        if (alert.source == "ai" && !aiEnabled) return false
        if (alert.source == "native" && !nativeEnabled) return false
        val isEscalation =
            alert.eventType == PushProtocol.EVENT_MISS_ESCALATION ||
                alert.streak > alert.threshold
        if (isEscalation && !escalationEnabled) return false
        return true
    }
}

data class PushConnectionStatus(
    val registered: Boolean = false,
    val firebaseConfigured: Boolean = false,
    val serverConfigured: Boolean = false,
    val fcmTokenPresent: Boolean = false,
    val fallbackMinutes: Int = 15,
    val detail: String = "正在初始化预警服务",
    val protocolVersion: Int = 1,
    val lastSyncedAtEpochMs: Long? = null,
) {
    val instantReady: Boolean
        get() = registered && firebaseConfigured && serverConfigured && fcmTokenPresent
}
