package com.tianji.probabilitylab.nativev4

import com.tianji.probabilitylab.nativev4.model.LotteryType
import java.lang.reflect.Method

/**
 * Realtime UI/push refreshes should only reload the lottery currently on screen.
 *
 * AppController intentionally keeps refreshLottery private because it owns all state merging and
 * cancellation semantics. This small compatibility bridge reuses that canonical path without
 * widening the controller API during the v6.1.x stabilization cycle. If an obfuscation or future
 * refactor changes the private method, it safely falls back to the existing full refresh.
 */
private val currentLotteryRefreshMethod: Method? by lazy {
    runCatching {
        AppController::class.java.getDeclaredMethod(
            "refreshLottery",
            LotteryType::class.java,
            Boolean::class.javaPrimitiveType,
        ).apply { isAccessible = true }
    }.getOrNull()
}

fun AppController.refreshCurrentLottery() {
    val method = currentLotteryRefreshMethod
    if (method == null) {
        refresh()
        return
    }
    val current = state.lottery
    val refreshed = runCatching {
        method.invoke(this, current, true)
    }.isSuccess
    if (!refreshed) refresh()
}
