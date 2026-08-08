package com.tianji.probabilitylab.nativev4

import android.content.Context
import com.tianji.probabilitylab.nativev4.ai.AiChatController
import com.tianji.probabilitylab.nativev4.push.PushAlertCoordinator

/**
 * Process-scoped runtime. Activity/Compose recreation no longer closes active AI sockets.
 * The foreground service keeps this process at foreground priority while a task is running.
 */
class TianjiRuntime private constructor(context: Context) {
    val chatController = AiChatController(context.applicationContext)
    val appController = AppController(context.applicationContext)

    init {
        PushAlertCoordinator.setRealtimeRefreshCallback {
            // Push means the shared server lane observed a meaningful event. Refresh both lotteries
            // so switching tabs never exposes the other lottery's stale cache.
            appController.refresh()
        }
    }

    companion object {
        @Volatile
        private var instance: TianjiRuntime? = null

        fun from(context: Context): TianjiRuntime = instance ?: synchronized(this) {
            instance ?: TianjiRuntime(context.applicationContext).also { instance = it }
        }
    }
}
