package com.tianji.probabilitylab.nativev4.ai

/**
 * A checkpoint is not a model token cap. It stops an open-ended reasoning stream only after
 * enough real reasoning has already arrived, then asks the same conversation to serialize its
 * existing conclusion as the tiny forecast JSON.
 */
object AiReasoningCheckpoint {
    const val MIN_REASONING_CHARS = 5_000
    const val MIN_ELAPSED_MS = 45_000L

    fun shouldFinalize(
        reasoningChars: Int,
        contentChars: Int,
        elapsedMs: Long,
    ): Boolean =
        contentChars == 0 &&
            reasoningChars >= MIN_REASONING_CHARS &&
            elapsedMs >= MIN_ELAPSED_MS
}
