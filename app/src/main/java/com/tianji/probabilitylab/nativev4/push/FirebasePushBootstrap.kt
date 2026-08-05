package com.tianji.probabilitylab.nativev4.push

import android.content.Context
import com.google.android.gms.tasks.OnCompleteListener
import com.google.firebase.FirebaseApp
import com.google.firebase.FirebaseOptions
import com.google.firebase.messaging.FirebaseMessaging
import com.tianji.probabilitylab.nativev4.BuildConfig

object FirebasePushBootstrap {
    val isConfigured: Boolean
        get() = BuildConfig.TIANJI_FIREBASE_PROJECT_ID.isNotBlank() &&
            BuildConfig.TIANJI_FIREBASE_APP_ID.isNotBlank() &&
            BuildConfig.TIANJI_FIREBASE_API_KEY.isNotBlank() &&
            BuildConfig.TIANJI_FIREBASE_SENDER_ID.isNotBlank()

    fun initialize(context: Context, onToken: (String) -> Unit) {
        if (!isConfigured) return
        FirebaseApp.getApps(context).firstOrNull()
            ?: FirebaseApp.initializeApp(
                context,
                FirebaseOptions.Builder()
                    .setProjectId(BuildConfig.TIANJI_FIREBASE_PROJECT_ID)
                    .setApplicationId(BuildConfig.TIANJI_FIREBASE_APP_ID)
                    .setApiKey(BuildConfig.TIANJI_FIREBASE_API_KEY)
                    .setGcmSenderId(BuildConfig.TIANJI_FIREBASE_SENDER_ID)
                    .build(),
            )
            ?: return

        @Suppress("DEPRECATION")
        FirebaseMessaging.getInstance().token.addOnCompleteListener(
            OnCompleteListener { task ->
                if (!task.isSuccessful) return@OnCompleteListener
                task.result
                    ?.takeIf { it.isNotBlank() }
                    ?.let(onToken)
            },
        )
    }
}
