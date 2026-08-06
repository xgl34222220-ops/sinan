package com.tianji.probabilitylab.nativev4.push

import android.content.Context
import androidx.work.Constraints
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.NetworkType
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit
import kotlinx.coroutines.flow.StateFlow

object PushAlertCoordinator {
    private val executor = Executors.newSingleThreadExecutor { task ->
        Thread(task, "tianji-push-sync").apply { isDaemon = true }
    }
    private val api = PushAlertApi()
    @Volatile private var initialized = false
    private lateinit var appContext: Context
    private lateinit var store: PushAlertStore

    val alerts: StateFlow<List<PushAlert>> get() = store.alerts
    val preferences: StateFlow<PushPreferences> get() = store.settings
    val status: StateFlow<PushConnectionStatus> get() = store.status

    fun initialize(context: Context) {
        if (initialized) return
        synchronized(this) {
            if (initialized) return
            appContext = context.applicationContext
            store = PushAlertStore(appContext)
            PushNotificationManager.createChannels(appContext)
            scheduleFallback(appContext)
            initialized = true
            FirebasePushBootstrap.initialize(appContext, ::updateFcmToken)
            executor.execute { syncNow(notifyNew = false) }
        }
    }

    fun ensureInitialized(context: Context) { if (!initialized) initialize(context) }

    fun updateFcmToken(token: String) {
        if (!initialized || token.isBlank() || store.fcmToken == token) return
        store.fcmToken = token
        executor.execute { syncNow(notifyNew = false) }
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
        executor.execute { runCatching { api.markRead(store, alertId) } }
    }

    fun markAllRead() {
        store.markAllRead()
        executor.execute { runCatching { api.markAllRead(store) } }
    }

    fun refresh() { executor.execute { syncNow(notifyNew = false) } }

    fun syncForWorker(context: Context): Boolean {
        ensureInitialized(context)
        return syncNow(notifyNew = true)
    }

    fun receiveRemoteData(data: Map<String, String>) {
        if (!initialized) return
        val alert = PushPayloadParser.fromRemoteData(data) ?: return
        val new = store.mergeAlerts(listOf(alert))
        if (new.isNotEmpty() && store.settings.value.accepts(alert) && !alert.isExpired) {
            PushNotificationManager.show(appContext, alert)
        }
    }

    private fun syncNow(notifyNew: Boolean): Boolean = runCatching {
        val connection = api.register(store, store.settings.value)
        val values = api.fetchAlerts(store, afterId = store.lastServerAlertId)
        val newAlerts = store.mergeAlerts(values)
        if (notifyNew && store.initialSyncComplete) {
            newAlerts.filter(store.settings.value::accepts)
                .filterNot(PushAlert::isExpired)
                .forEach { PushNotificationManager.show(appContext, it) }
        }
        store.initialSyncComplete = true
        store.updateStatus(
            connection.copy(
                protocolVersion = maxOf(
                    connection.protocolVersion,
                    values.maxOfOrNull(PushAlert::schemaVersion) ?: 1,
                ),
                lastSyncedAtEpochMs = System.currentTimeMillis(),
            ),
        )
        true
    }.getOrElse { failure ->
        val previous = store.status.value
        store.updateStatus(
            PushConnectionStatus(
                registered = false,
                firebaseConfigured = FirebasePushBootstrap.isConfigured,
                serverConfigured = previous.serverConfigured,
                fcmTokenPresent = store.fcmToken.isNotBlank(),
                fallbackMinutes = previous.fallbackMinutes,
                protocolVersion = previous.protocolVersion,
                lastSyncedAtEpochMs = previous.lastSyncedAtEpochMs,
                detail = failure.message ?: "预警服务暂时不可用",
            ),
        )
        false
    }

    private fun scheduleFallback(context: Context) {
        val request = PeriodicWorkRequestBuilder<PushAlertWorker>(
            15, TimeUnit.MINUTES, 5, TimeUnit.MINUTES,
        ).setConstraints(
            Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build(),
        ).build()
        WorkManager.getInstance(context).enqueueUniquePeriodicWork(
            PushAlertWorker.UNIQUE_WORK,
            ExistingPeriodicWorkPolicy.UPDATE,
            request,
        )
    }
}
