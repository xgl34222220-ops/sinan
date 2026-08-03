package com.tianji.probabilitylab.nativev4.service

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.IBinder
import androidx.core.app.NotificationCompat
import androidx.core.content.ContextCompat
import com.tianji.probabilitylab.nativev4.MainActivity

class AiForegroundService : Service() {
    override fun onCreate() {
        super.onCreate()
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val manager = getSystemService(NotificationManager::class.java)
            manager.createNotificationChannel(
                NotificationChannel(
                    CHANNEL_ID,
                    "天机 AI 后台任务",
                    NotificationManager.IMPORTANCE_LOW,
                ).apply {
                    description = "保持正式预测和分析对话在切出页面后继续运行"
                    setShowBadge(false)
                },
            )
        }
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val title = intent?.getStringExtra(EXTRA_TITLE).orEmpty().ifBlank { "天机 AI 正在运行" }
        val detail = intent?.getStringExtra(EXTRA_DETAIL).orEmpty().ifBlank { "返回应用可查看实时进度" }
        val openIntent = PendingIntent.getActivity(
            this,
            0,
            Intent(this, MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
        val notification = NotificationCompat.Builder(this, CHANNEL_ID)
            .setSmallIcon(android.R.drawable.stat_notify_sync)
            .setContentTitle(title)
            .setContentText(detail)
            .setContentIntent(openIntent)
            .setOngoing(true)
            .setOnlyAlertOnce(true)
            .setCategory(NotificationCompat.CATEGORY_PROGRESS)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .build()
        startForeground(NOTIFICATION_ID, notification)
        return START_STICKY
    }

    override fun onBind(intent: Intent?): IBinder? = null

    companion object {
        private const val CHANNEL_ID = "tianji_ai_tasks"
        private const val NOTIFICATION_ID = 5909
        private const val EXTRA_TITLE = "title"
        private const val EXTRA_DETAIL = "detail"

        fun show(context: Context, title: String, detail: String) {
            val intent = Intent(context, AiForegroundService::class.java)
                .putExtra(EXTRA_TITLE, title)
                .putExtra(EXTRA_DETAIL, detail)
            runCatching { ContextCompat.startForegroundService(context.applicationContext, intent) }
        }

        fun hide(context: Context) {
            runCatching { context.applicationContext.stopService(Intent(context, AiForegroundService::class.java)) }
        }
    }
}
