package com.tianji.probabilitylab.nativev4.ai

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class AiReasoningCheckpointTest {
    @Test
    fun doesNotInterruptBeforeEnoughReasoning() {
        assertFalse(
            AiReasoningCheckpoint.shouldFinalize(
                reasoningChars = AiReasoningCheckpoint.MIN_REASONING_CHARS - 1,
                contentChars = 0,
                elapsedMs = AiReasoningCheckpoint.MIN_ELAPSED_MS + 10_000,
            ),
        )
    }

    @Test
    fun doesNotInterruptAfterResultContentStarts() {
        assertFalse(
            AiReasoningCheckpoint.shouldFinalize(
                reasoningChars = AiReasoningCheckpoint.MIN_REASONING_CHARS + 1_000,
                contentChars = 1,
                elapsedMs = AiReasoningCheckpoint.MIN_ELAPSED_MS + 10_000,
            ),
        )
    }

    @Test
    fun finalizesSameConversationAfterRealReasoningCheckpoint() {
        assertTrue(
            AiReasoningCheckpoint.shouldFinalize(
                reasoningChars = AiReasoningCheckpoint.MIN_REASONING_CHARS,
                contentChars = 0,
                elapsedMs = AiReasoningCheckpoint.MIN_ELAPSED_MS,
            ),
        )
    }
}
