package com.tianji.probabilitylab.nativev4.ai

import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class AiIndependenceContractTest {
    private fun source(name: String): String = File(
        "src/main/java/com/tianji/probabilitylab/nativev4/ai/$name",
    ).readText()

    @Test
    fun formalPredictionUsesRawHistoryWithoutNativeStatistics() {
        val source = source("AiAnalysis.kt")
        val payload = source.substringAfter("private fun analysisPayload(")
            .substringBefore("private fun isRetriableModelOutput")
        assertTrue(payload.contains("raw_draws_oldest_to_newest"))
        assertTrue(payload.contains("raw-history-v1"))
        assertFalse(payload.contains("verified_position_statistics"))
        assertFalse(payload.contains("report.selectedPosition"))
        assertFalse(payload.contains("report.selected.top6"))
    }

    @Test
    fun independentChatDoesNotDefaultToNativePositionOrInjectNativeFacts() {
        val source = source("AiChatController.kt")
        assertFalse(source.contains("?: report.selectedPosition"))
        val builder = source.substringAfter("object AiChatContextBuilder")
            .substringBefore("private class RemoteAiChatClient")
        assertTrue(builder.contains("judgementMode == AiJudgementMode.INDEPENDENT"))
        assertTrue(builder.contains("raw-history-v1"))
        assertTrue(builder.contains("if (independent)"))
        assertTrue(builder.contains("else {
                    put(
                        "verified_position_statistics""))
    }
}
