package com.tianji.probabilitylab.nativev4.ai

object AiErrorMessages {
    fun userFacing(error: Throwable, fallback: String): String {
        val message = error.message.orEmpty().trim()
        val lower = message.lowercase()
        return when {
            listOf(
                "software caused connection abort",
                "connection reset",
                "broken pipe",
                "socket closed",
                "unexpected end of stream",
            ).any(lower::contains) -> "网络连接在模型输出过程中中断，本次未自动重新预测"
            "timeout" in lower || "timed out" in lower -> "等待接口响应超时，请检查网络或稍后重试"
            message.any { it in '一'..'鿿' } -> message.take(180)
            else -> "$fallback，请检查网络、代理或接口设置"
        }
    }
}
