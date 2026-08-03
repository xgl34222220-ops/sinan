package com.tianji.probabilitylab.nativev4

import android.app.Application

class TianjiApplication : Application() {
    override fun onCreate() {
        super.onCreate()
        TianjiRuntime.from(this)
    }
}
