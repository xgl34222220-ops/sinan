package com.tianji.probabilitylab.nativev4

import android.content.Intent
import android.content.res.Configuration
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
            statusBarStyle = transparentAutoSystemBarStyle(),
            navigationBarStyle = transparentAutoSystemBarStyle(),
        )
        handlePushIntent(intent)
        setContent { TianjiApp() }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        handlePushIntent(intent)
    }

    private fun transparentAutoSystemBarStyle(): SystemBarStyle = SystemBarStyle.auto(
        lightScrim = Color.TRANSPARENT,
        darkScrim = Color.TRANSPARENT,
    ) {
        resources.configuration.uiMode and Configuration.UI_MODE_NIGHT_MASK ==
            Configuration.UI_MODE_NIGHT_YES
    }

    private fun handlePushIntent(intent: Intent?) {
        intent ?: return
        val openPrediction =
            intent.getBooleanExtra(PushNotificationManager.EXTRA_OPEN_PREDICTION, false) ||
                intent.getStringExtra(PushNotificationManager.EXTRA_OPEN_PREDICTION)
                    ?.toBooleanStrictOrNull() == true
        if (openPrediction) {
            PushAlertNavigation.openPrediction(
                lottery = intent.getStringExtra(PushNotificationManager.EXTRA_LOTTERY).orEmpty(),
                targetPeriod = intent.getStringExtra(PushNotificationManager.EXTRA_TARGET_PERIOD).orEmpty(),
            )
            return
        }
        val openAlertCenter =
            intent.getBooleanExtra(PushNotificationManager.EXTRA_OPEN_ALERT_CENTER, false) ||
                intent.getStringExtra(PushNotificationManager.EXTRA_OPEN_ALERT_CENTER)
                    ?.toBooleanStrictOrNull() == true ||
                intent.hasExtra(PushNotificationManager.EXTRA_ALERT_ID)
        if (!openAlertCenter) return

        val alertId = when (val value = intent.extras?.get(PushNotificationManager.EXTRA_ALERT_ID)) {
            is Number -> value.toLong()
            is String -> value.toLongOrNull() ?: 0L
            else -> 0L
        }
        PushAlertNavigation.open(alertId)
    }
}
