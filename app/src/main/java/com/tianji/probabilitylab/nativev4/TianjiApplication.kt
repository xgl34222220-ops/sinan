package com.tianji.probabilitylab.nativev4

import android.app.Application
import com.tianji.probabilitylab.nativev4.push.PushAlertCoordinator

class TianjiApplication : Application() {
    override fun onCreate() {
        super.onCreate()
        TianjiRuntime.from(this)
        PushAlertCoordinator.initialize(this)
    }
}
