package com.tianji.probabilitylab.nativev4.push

import android.content.Context
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit
import kotlinx.coroutines.flow.StateFlow

object PushAlertCoordinator {
    private val executor = Executors.newSingleThreadExecutor()
    private val api = PushAlertApi()
    @Volatile private var initialized = false
    private lateinit var appContext: Context
    private lateinit var store: PushAlertStore

    val alerts: StateFlow<List<PushAlert>>
        get() = store.alerts
    val preferences: StateFlow<PushPreferences>
        get() = store.settings
    val status: StateFlow<PushConnectionStatus>
        get() = store.status

    fun initialize(context: Context) {
        if (initialized) return
        synchronized(this) {
            if (initialized) return
            appContext = context.applicationContext
            store = PushAlertStore(appContext)
            PushNotificationManager.createChannel(appContext)
            scheduleFallback(appContext)
            initialized = true
            FirebasePushBootstrap.initialize(appContext, ::updateFcmToken)
            executor.execute {
                syncNow(notifyNew = false)
            }
        }
    }

    fun ensureInitialized(context: Context) {
        if (!initialized) initialize(context)
    }

    fun updateFcmToken(token: String) {
        if (!initialized || token.isBlank()) return
        store.fcmToken = token
        executor.execute {
            syncNow(notifyNew = false)
        }
    }

    fun updatePreferences(value: PushPreferences) {
        store.updatePreferences(value)
        executor.execute {
            runCatching { api.updatePreferences(store, value) }
                .onSuccess(store::updateStatus)
                .onFailure { failure ->
                    store.updateStatus(
                        store.status.value.copy(
                            detail = failure.message ?: "推送设置同步失败",
                        ),
                    )
                }
        }
    }

    fun markRead(alertId: Long) {
        store.markRead(alertId)
        executor.execute {
            runCatching { api.markRead(store, alertId) }
        }
    }

    fun markAllRead() {
        store.markAllRead()
        executor.execute {
            runCatching { api.markAllRead(store) }
        }
    }

    fun refresh() {
        executor.execute { syncNow(notifyNew = false) }
    }

    fun syncForWorker(context: Context): Boolean {
        ensureInitialized(context)
        return syncNow(notifyNew = true)
    }

    fun receiveRemoteData(data: Map<String, String>) {
        if (!initialized) return
        val alert = data.toAlert() ?: return
        val new = store.mergeAlerts(listOf(alert))
        if (new.isNotEmpty() && store.settings.value.accepts(alert)) {
            PushNotificationManager.show(appContext, alert)
        }
    }

    private fun syncNow(notifyNew: Boolean): Boolean {
        return runCatching {
            val connection = api.register(store, store.settings.value)
            store.updateStatus(connection)
            val values = api.fetchAlerts(store)
            val newAlerts = store.mergeAlerts(values)
            val canNotify = notifyNew && store.initialSyncComplete
            if (canNotify) {
                newAlerts
                    .filter(store.settings.value::accepts)
                    .forEach { PushNotificationManager.show(appContext, it) }
            }
            store.initialSyncComplete = true
            true
        }.getOrElse { failure ->
            store.updateStatus(
                PushConnectionStatus(
                    registered = false,
                    firebaseConfigured = FirebasePushBootstrap.isConfigured,
                    fcmTokenPresent = store.fcmToken.isNotBlank(),
                    fallbackMinutes = 15,
                    detail = failure.message ?: "预警服务暂时不可用",
                ),
            )
            false
        }
    }

    private fun scheduleFallback(context: Context) {
        val request = PeriodicWorkRequestBuilder<PushAlertWorker>(
            15,
            TimeUnit.MINUTES,
        ).build()
        WorkManager.getInstance(context).enqueueUniquePeriodicWork(
            PushAlertWorker.UNIQUE_WORK,
            ExistingPeriodicWorkPolicy.UPDATE,
            request,
        )
    }

    private fun Map<String, String>.toAlert(): PushAlert? {
        if (get("type") != "prediction_miss_alert") return null
        val id = get("alert_id")?.toLongOrNull() ?: return null
        return PushAlert(
            id = id,
            eventKey = "",
            lottery = get("lottery").orEmpty(),
            lotteryName = get("lottery_name").orEmpty(),
            source = get("source").orEmpty(),
            sourceName = get("source_name").orEmpty(),
            model = get("model").orEmpty(),
            streak = get("streak")?.toIntOrNull() ?: 3,
            threshold = get("threshold")?.toIntOrNull() ?: 3,
            latestTargetPeriod = get("latest_target_period").orEmpty(),
            recentPeriods = get("recent_periods")
                .orEmpty()
                .split(',')
                .filter(String::isNotBlank),
            title = if ((get("streak")?.toIntOrNull() ?: 3) > 3) {
                "连续 ${get("streak")} 期不中升级预警"
            } else {
                "三期不中预警"
            },
            body = buildString {
                append(get("lottery_name").orEmpty())
                append(" · ")
                append(get("source_name").orEmpty())
                append(" · ")
                append(get("model").orEmpty())
                append(" 已连续 ")
                append(get("streak").orEmpty())
                append(" 期 Top 6 未命中")
            },
            createdAtEpochMs = System.currentTimeMillis(),
            isRead = false,
        )
    }
}
