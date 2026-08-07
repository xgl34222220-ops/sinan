package com.tianji.probabilitylab.nativev4

/**
 * v6.2 compatibility shim.
 *
 * [AppController] now owns the current-lottery refresh API directly. The old Java-reflection
 * bridge is intentionally gone so R8/obfuscation can no longer change realtime refresh behavior.
 * This extension remains temporarily source-compatible with imports from the v6.1.x UI while the
 * member function always wins normal Kotlin dispatch.
 */
@Deprecated(
    message = "Use AppController.refreshCurrentLottery() member API",
    level = DeprecationLevel.WARNING,
)
fun AppController.refreshCurrentLottery() {
    this.refreshCurrentLottery()
}
