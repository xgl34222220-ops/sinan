package com.tianji.probabilitylab.nativev4.ai

enum class AiConversationStage {
    PREPARING,
    REQUEST,
    CONNECTED,
    REASONING,
    OUTPUT,
    VALIDATING,
    CONTINUATION,
    RETRY,
    SUCCESS,
    ERROR,
    CANCELLED,
}

data class AiConversationEvent(
    val stage: AiConversationStage,
    val message: String,
    val elapsedMs: Long,
    val createdAtEpochMs: Long,
)

/** Keeps a compact user-visible timeline instead of replacing the status with one opaque line. */
object AiConversationTimeline {
    fun event(
        stage: AiConversationStage,
        message: String,
        elapsedMs: Long = 0L,
        nowEpochMs: Long = System.currentTimeMillis(),
    ) = AiConversationEvent(
        stage = stage,
        message = message.trim(),
        elapsedMs = elapsedMs.coerceAtLeast(0L),
        createdAtEpochMs = nowEpochMs,
    )

    fun classify(message: String): AiConversationStage = when {
        "取消" in message -> AiConversationStage.CANCELLED
        "失败" in message || "超时" in message || "错误" in message || "中断" in message || "断流" in message -> AiConversationStage.ERROR
        "重连" in message || "重试" in message || "切换" in message -> AiConversationStage.RETRY
        "补全" in message || "继续对话" in message -> AiConversationStage.CONTINUATION
        "校验" in message || "核验" in message -> AiConversationStage.VALIDATING
        "预测核心" in message || "生成结构化" in message || "结果字符" in message -> AiConversationStage.OUTPUT
        "推理" in message -> AiConversationStage.REASONING
        "已连接" in message || "服务器接受" in message -> AiConversationStage.CONNECTED
        "发送" in message || "建立 HTTPS" in message || "建立HTTPS" in message -> AiConversationStage.REQUEST
        "同步" in message || "准备" in message -> AiConversationStage.PREPARING
        else -> AiConversationStage.REQUEST
    }

    fun merge(
        existing: List<AiConversationEvent>,
        next: AiConversationEvent,
        maxEvents: Int = 24,
    ): List<AiConversationEvent> {
        val replaceableStages = setOf(
            AiConversationStage.REASONING,
            AiConversationStage.OUTPUT,
            AiConversationStage.CONNECTED,
        )
        val phaseBoundaries = setOf(
            AiConversationStage.CONTINUATION,
            AiConversationStage.RETRY,
            AiConversationStage.SUCCESS,
            AiConversationStage.ERROR,
            AiConversationStage.CANCELLED,
        )
        val merged = if (next.stage in replaceableStages) {
            val boundaryIndex = existing.indexOfLast { it.stage in phaseBoundaries }
            val replaceIndex = existing.indices.reversed().firstOrNull { index ->
                index > boundaryIndex && existing[index].stage == next.stage
            }
            if (replaceIndex == null) {
                existing + next
            } else {
                existing.toMutableList().apply { this[replaceIndex] = next }
            }
        } else {
            existing + next
        }
        return merged.takeLast(maxEvents.coerceAtLeast(1))
    }
}
