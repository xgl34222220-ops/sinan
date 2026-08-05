package com.tianji.probabilitylab.nativev4.push

import android.content.Context
import androidx.work.Worker
import androidx.work.WorkerParameters

class PushAlertWorker(
    appContext: Context,
    parameters: WorkerParameters,
) : Worker(appContext, parameters) {
    override fun doWork(): Result =
        if (PushAlertCoordinator.syncForWorker(applicationContext)) {
            Result.success()
        } else {
            Result.retry()
        }

    companion object {
        const val UNIQUE_WORK = "tianji-push-alert-fallback"
    }
}
