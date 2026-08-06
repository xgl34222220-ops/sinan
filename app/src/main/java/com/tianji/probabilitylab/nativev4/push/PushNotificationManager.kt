package com.tianji.probabilitylab.nativev4.push

import android.Manifest
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import com.tianji.probabilitylab.nativev4.MainActivity
import com.tianji.probabilitylab.nativev4.R
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow

object PushAlertNavigation {
    private val pending = MutableStateFlow<Long?>(null)
    val pendingAlertId = pending.asStateFlow()
    fun open(alertId: Long = 0L) { pending.value = alertId }
    fun consume() { pending.value = null }
}

object PushNotificationManager {
    const val RISK_CHANNEL_ID = "tianji_prediction_alerts"
    const val UPDATE_CHANNEL_ID = "tianji_prediction_updates"
    const val EXTRA_OPEN_ALERT_CENTER = "open_alert_center"
    const val EXTRA_ALERT_ID = "alert_id"

    @Volatile private var applicationContext: Context? = null
    val notificationsEnabled: Boolean
        get() = applicationContext?.let(::canPostNotifications) ?: true

    fun createChannels(context: Context) {
        applicationContext = context.applicationContext
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
        val manager = context.getSystemService(NotificationManager::class.java)
        manager.createNotificationChannels(
            listOf(
                NotificationChannel(
                    UPDATE_CHANNEL_ID,
                    "每期预测与恢复提醒",
                    NotificationManager.IMPORTANCE_DEFAULT,
                ).apply {
                    description = "云端 AI 新一期预测完成与连续不中后恢复命中提醒"
                    enableVibration(false)
                },
                NotificationChannel(
                    RISK_CHANNEL_ID,
                    "连续未命中风险预警",
                    NotificationManager.IMPORTANCE_HIGH,
                ).apply {
                    description = "两期预警、三期加强提醒和后续升级预警"
                    enableVibration(true)
                },
            ),
        )
    }

    fun show(context: Context, alert: PushAlert) {
        if (alert.isExpired || !canPostNotifications(context)) return
        val notificationId = alert.stableNotificationKey.hashCode()
        val intent = Intent(context, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_SINGLE_TOP
            putExtra(EXTRA_OPEN_ALERT_CENTER, true)
            putExtra(EXTRA_ALERT_ID, alert.id)
        }
        val pendingIntent = PendingIntent.getActivity(
            context,
            notificationId,
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
        val channel = if (alert.isRiskAlert) RISK_CHANNEL_ID else UPDATE_CHANNEL_ID
        val expanded = buildString {
            append(alert.body)
            if (alert.latestTargetPeriod.isNotBlank()) {
                append("\n目标期：")
                append(alert.latestTargetPeriod)
            }
            if (alert.recentPeriods.isNotEmpty()) {
                append("\n最近期号：")
                append(alert.recentPeriods.joinToString("、"))
            }
        }
        val notification = NotificationCompat.Builder(context, channel)
            .setSmallIcon(R.drawable.ic_stat_tianji)
            .setContentTitle(alert.title)
            .setContentText(alert.body)
            .setStyle(NotificationCompat.BigTextStyle().bigText(expanded))
            .setPriority(
                if (alert.isRiskAlert) NotificationCompat.PRIORITY_HIGH
                else NotificationCompat.PRIORITY_DEFAULT,
            )
            .setCategory(
                if (alert.isRiskAlert) NotificationCompat.CATEGORY_ALARM
                else NotificationCompat.CATEGORY_STATUS,
            )
            .setGroup("tianji_${alert.lottery.ifBlank { "general" }}")
            .setOnlyAlertOnce(true)
            .setAutoCancel(true)
            .setContentIntent(pendingIntent)
            .setWhen(alert.createdAtEpochMs)
            .setShowWhen(true)
            .build()
        NotificationManagerCompat.from(context).notify(notificationId, notification)
    }

    private fun canPostNotifications(context: Context): Boolean {
        val permissionGranted =
            Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU ||
                ContextCompat.checkSelfPermission(
                    context,
                    Manifest.permission.POST_NOTIFICATIONS,
                ) == PackageManager.PERMISSION_GRANTED
        return permissionGranted &&
            NotificationManagerCompat.from(context).areNotificationsEnabled()
    }
}
