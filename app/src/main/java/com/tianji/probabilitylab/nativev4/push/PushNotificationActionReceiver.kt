package com.tianji.probabilitylab.nativev4.push

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import androidx.core.app.NotificationManagerCompat

class PushNotificationActionReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != ACTION_MARK_READ) return
        val alertId = intent.getLongExtra(EXTRA_ALERT_ID, 0L)
        if (alertId <= 0L) return
        PushAlertCoordinator.ensureInitialized(context.applicationContext)
        PushAlertCoordinator.markRead(alertId)
        val notificationId = intent.getIntExtra(EXTRA_NOTIFICATION_ID, 0)
        if (notificationId != 0) {
            NotificationManagerCompat.from(context).cancel(notificationId)
        }
    }

    companion object {
        const val ACTION_MARK_READ = "com.tianji.probabilitylab.action.MARK_ALERT_READ"
        const val EXTRA_ALERT_ID = "alert_id"
        const val EXTRA_NOTIFICATION_ID = "notification_id"
    }
}
