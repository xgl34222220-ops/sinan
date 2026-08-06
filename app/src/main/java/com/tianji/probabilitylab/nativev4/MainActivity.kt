package com.tianji.probabilitylab.nativev4

import android.content.Intent
import android.graphics.Color
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.SystemBarStyle
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import com.tianji.probabilitylab.nativev4.push.PushAlertNavigation
import com.tianji.probabilitylab.nativev4.push.PushNotificationManager
import com.tianji.probabilitylab.nativev4.ui.TianjiApp

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge(
            statusBarStyle = SystemBarStyle.dark(Color.TRANSPARENT),
            navigationBarStyle = SystemBarStyle.dark(Color.TRANSPARENT),
        )
        handlePushIntent(intent)
        setContent { TianjiApp() }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        handlePushIntent(intent)
    }

    private fun handlePushIntent(intent: Intent?) {
        if (intent?.getBooleanExtra(PushNotificationManager.EXTRA_OPEN_ALERT_CENTER, false) == true) {
            PushAlertNavigation.open(
                intent.getLongExtra(PushNotificationManager.EXTRA_ALERT_ID, 0L),
            )
        }
    }
}
