package com.tianji.probabilitylab.nativev4.push

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
)

data class PushPreferences(
    val enabled: Boolean = true,
    val xyftEnabled: Boolean = true,
    val azxy10Enabled: Boolean = true,
    val aiEnabled: Boolean = true,
    val nativeEnabled: Boolean = true,
    val escalationEnabled: Boolean = true,
) {
    fun accepts(alert: PushAlert): Boolean {
        if (!enabled) return false
        if (alert.lottery == "xyft" && !xyftEnabled) return false
        if (alert.lottery == "azxy10" && !azxy10Enabled) return false
        if (alert.source == "ai" && !aiEnabled) return false
        if (alert.source == "native" && !nativeEnabled) return false
        if (alert.streak > alert.threshold && !escalationEnabled) return false
        return true
    }
}

data class PushConnectionStatus(
    val registered: Boolean = false,
    val firebaseConfigured: Boolean = false,
    val fcmTokenPresent: Boolean = false,
    val fallbackMinutes: Int = 15,
    val detail: String = "正在初始化预警服务",
)
