package com.tianji.probabilitylab.nativev4.push

import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage

class TianjiMessagingService : FirebaseMessagingService() {
    override fun onNewToken(token: String) {
        PushAlertCoordinator.ensureInitialized(applicationContext)
        PushAlertCoordinator.updateFcmToken(token)
    }

    override fun onMessageReceived(message: RemoteMessage) {
        PushAlertCoordinator.ensureInitialized(applicationContext)
        PushAlertCoordinator.receiveRemoteData(message.data)
    }
}
