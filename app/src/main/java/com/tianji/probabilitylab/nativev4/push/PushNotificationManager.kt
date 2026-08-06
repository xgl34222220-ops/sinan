package com.tianji.probabilitylab.nativev4.push

import android.Manifest
import android.annotation.SuppressLint
import android.app.NotificationChannel
import android.app.NotificationChannelGroup
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

data class PushPredictionTarget(val lottery: String, val targetPeriod: String)

object PushAlertNavigation {
    private val pending = MutableStateFlow<Long?>(null)
    private val prediction = MutableStateFlow<PushPredictionTarget?>(null)
    val pendingAlertId = pending.asStateFlow()
    val pendingPrediction = prediction.asStateFlow()
    fun open(alertId: Long = 0L) { pending.value = alertId }
    fun consume() { pending.value = null }
    fun openPrediction(lottery: String, targetPeriod: String) {
        prediction.value = PushPredictionTarget(lottery, targetPeriod)
    }
    fun consumePrediction() { prediction.value = null }
}

object PushNotificationManager {
    const val RISK_CHANNEL_ID = "tianji_prediction_alerts"
    const val UPDATE_CHANNEL_ID = "tianji_prediction_updates"
    const val EXTRA_OPEN_ALERT_CENTER = "open_alert_center"
    const val EXTRA_OPEN_PREDICTION = "open_prediction"
    const val EXTRA_ALERT_ID = "alert_id"
    const val EXTRA_LOTTERY = "lottery"
    const val EXTRA_TARGET_PERIOD = "target_period"
    private const val CHANNEL_GROUP_ID = "tianji_prediction_group"

    @Volatile private var applicationContext: Context? = null
    val notificationsEnabled: Boolean
        get() = applicationContext?.let(::canPostNotifications) ?: true

    fun createChannels(context: Context) {
        applicationContext = context.applicationContext
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
        val manager = context.getSystemService(NotificationManager::class.java)
        manager.createNotificationChannelGroup(
            NotificationChannelGroup(CHANNEL_GROUP_ID, "天机预测通知"),
        )
        manager.createNotificationChannels(
            listOf(
                NotificationChannel(
                    UPDATE_CHANNEL_ID,
                    "每期预测与恢复提醒",
                    NotificationManager.IMPORTANCE_DEFAULT,
                ).apply {
                    group = CHANNEL_GROUP_ID
                    description = "云端 AI 新一期预测完成与连续不中后恢复命中提醒"
                    enableVibration(false)
                    setShowBadge(true)
                },
                NotificationChannel(
                    RISK_CHANNEL_ID,
                    "连续未命中风险预警",
                    NotificationManager.IMPORTANCE_HIGH,
                ).apply {
                    group = CHANNEL_GROUP_ID
                    description = "两期预警、三期加强提醒和后续升级预警"
                    enableVibration(true)
                    setShowBadge(true)
                },
            ),
        )
    }

    @SuppressLint("MissingPermission")
    fun show(context: Context, alert: PushAlert) {
        // Lint cannot follow the runtime permission guard through this helper.
        if (alert.isExpired || !canPostNotifications(context)) return
        val notificationId = alert.stableNotificationKey.hashCode()
        val groupKey = groupKey(alert)
        val openIntent = if (alert.eventType == PushProtocol.EVENT_PREDICTION_READY) {
            openPredictionIntent(context, alert, notificationId)
        } else {
            openAlertIntent(context, alert.id, notificationId)
        }
        val markReadIntent = markReadIntent(context, alert.id, notificationId)
        val channel = if (alert.isRiskAlert) RISK_CHANNEL_ID else UPDATE_CHANNEL_ID
        val expanded = buildString {
            append(alert.body)
            if (alert.latestTargetPeriod.isNotBlank()) {
                append("\n目标期：")
                append(alert.latestTargetPeriod)
            }
            if (alert.recentPeriods.isNotEmpty() && alert.isRiskAlert) {
                append("\n最近期号：")
                append(alert.recentPeriods.joinToString("、"))
            }
        }
        val notification = NotificationCompat.Builder(context, channel)
            .setSmallIcon(R.drawable.ic_stat_tianji)
            .setContentTitle(alert.title)
            .setContentText(alert.body)
            .setSubText(alert.lotteryName.ifBlank { alert.sourceName })
            .setStyle(NotificationCompat.BigTextStyle().bigText(expanded))
            .setPriority(
                if (alert.isRiskAlert) NotificationCompat.PRIORITY_HIGH
                else NotificationCompat.PRIORITY_DEFAULT,
            )
            .setCategory(
                if (alert.isRiskAlert) NotificationCompat.CATEGORY_ALARM
                else NotificationCompat.CATEGORY_STATUS,
            )
            .setGroup(groupKey)
            .setGroupAlertBehavior(NotificationCompat.GROUP_ALERT_CHILDREN)
            .setOnlyAlertOnce(true)
            .setAutoCancel(true)
            .setContentIntent(openIntent)
            .addAction(
                R.drawable.ic_stat_tianji,
                "查看预测",
                openIntent,
            )
            .addAction(
                R.drawable.ic_stat_tianji,
                "标记已读",
                markReadIntent,
            )
            .setWhen(alert.createdAtEpochMs)
            .setShowWhen(true)
            .setSilent(!alert.isRiskAlert)
            .build()
        val manager = NotificationManagerCompat.from(context)
        manager.notify(notificationId, notification)
        manager.notify(
            summaryId(groupKey),
            summaryNotification(context, alert, groupKey, openIntent, channel),
        )
    }

    private fun openPredictionIntent(
        context: Context,
        alert: PushAlert,
        requestCode: Int,
    ): PendingIntent {
        val intent = Intent(context, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_SINGLE_TOP
            putExtra(EXTRA_OPEN_PREDICTION, true)
            putExtra(EXTRA_LOTTERY, alert.lottery)
            putExtra(EXTRA_TARGET_PERIOD, alert.latestTargetPeriod)
        }
        return PendingIntent.getActivity(
            context,
            requestCode,
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
    }

    private fun openAlertIntent(
        context: Context,
        alertId: Long,
        requestCode: Int,
    ): PendingIntent {
        val intent = Intent(context, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_SINGLE_TOP
            putExtra(EXTRA_OPEN_ALERT_CENTER, true)
            putExtra(EXTRA_ALERT_ID, alertId)
        }
        return PendingIntent.getActivity(
            context,
            requestCode,
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
    }

    private fun markReadIntent(
        context: Context,
        alertId: Long,
        notificationId: Int,
    ): PendingIntent {
        val intent = Intent(context, PushNotificationActionReceiver::class.java).apply {
            action = PushNotificationActionReceiver.ACTION_MARK_READ
            putExtra(PushNotificationActionReceiver.EXTRA_ALERT_ID, alertId)
            putExtra(PushNotificationActionReceiver.EXTRA_NOTIFICATION_ID, notificationId)
        }
        return PendingIntent.getBroadcast(
            context,
            notificationId xor 0x5A17,
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
    }

    private fun summaryNotification(
        context: Context,
        alert: PushAlert,
        groupKey: String,
        openIntent: PendingIntent,
        channel: String,
    ) = NotificationCompat.Builder(context, channel)
        .setSmallIcon(R.drawable.ic_stat_tianji)
        .setContentTitle(alert.lotteryName.ifBlank { "天机预测通知" })
        .setContentText("预测、恢复与风险状态已按彩种归组")
        .setStyle(
            NotificationCompat.InboxStyle()
                .setSummaryText("点击进入通知中心查看完整记录")
                .addLine(alert.title),
        )
        .setGroup(groupKey)
        .setGroupSummary(true)
        .setGroupAlertBehavior(NotificationCompat.GROUP_ALERT_CHILDREN)
        .setContentIntent(openIntent)
        .setAutoCancel(true)
        .setSilent(true)
        .build()

    private fun groupKey(alert: PushAlert): String =
        "tianji_${alert.lottery.ifBlank { "general" }}"

    private fun summaryId(groupKey: String): Int =
        "summary:$groupKey".hashCode()

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
