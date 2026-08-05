package com.tianji.probabilitylab.nativev4.push

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.Build
import androidx.core.app.NotificationCompat
import com.tianji.probabilitylab.nativev4.MainActivity
import com.tianji.probabilitylab.nativev4.R
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow

object PushAlertNavigation {
    private val pending = MutableStateFlow<Long?>(null)
    val pendingAlertId = pending.asStateFlow()

    fun open(alertId: Long = 0L) {
        pending.value = alertId
    }

    fun consume() {
        pending.value = null
    }
}

object PushNotificationManager {
    const val CHANNEL_ID = "tianji_prediction_alerts"
    const val EXTRA_OPEN_ALERT_CENTER = "open_alert_center"
    const val EXTRA_ALERT_ID = "alert_id"

    fun createChannel(context: Context) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
        val manager = context.getSystemService(NotificationManager::class.java)
        val channel = NotificationChannel(
            CHANNEL_ID,
            "预测连续未命中预警",
            NotificationManager.IMPORTANCE_HIGH,
        ).apply {
            description = "天机云端按彩种、来源和模型发送的连续未命中预警"
            enableVibration(true)
        }
        manager.createNotificationChannel(channel)
    }

    fun show(context: Context, alert: PushAlert) {
        val intent = Intent(context, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_SINGLE_TOP
            putExtra(EXTRA_OPEN_ALERT_CENTER, true)
            putExtra(EXTRA_ALERT_ID, alert.id)
        }
        val pendingIntent = PendingIntent.getActivity(
            context,
            alert.id.hashCode(),
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
        val notification = NotificationCompat.Builder(context, CHANNEL_ID)
            .setSmallIcon(R.mipmap.ic_launcher)
            .setContentTitle(alert.title)
            .setContentText(alert.body)
            .setStyle(
                NotificationCompat.BigTextStyle().bigText(
                    buildString {
                        append(alert.body)
                        if (alert.recentPeriods.isNotEmpty()) {
                            append("\n最近期号：")
                            append(alert.recentPeriods.joinToString("、"))
                        }
                    },
                ),
            )
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setCategory(NotificationCompat.CATEGORY_ALARM)
            .setAutoCancel(true)
            .setContentIntent(pendingIntent)
            .build()
        context.getSystemService(NotificationManager::class.java)
            .notify(alert.id.hashCode(), notification)
    }
}
