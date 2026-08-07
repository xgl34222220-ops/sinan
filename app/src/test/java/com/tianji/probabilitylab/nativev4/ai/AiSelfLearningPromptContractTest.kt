package com.tianji.probabilitylab.nativev4.ai

import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class AiSelfLearningPromptContractTest {
    private fun source(name: String): String = File(
        "src/main/java/com/tianji/probabilitylab/nativev4/ai/$name",
    ).readText()

    @Test
    fun continualWrapperInjectsEvidenceBeforeRemoteInference() {
        val source = source("ContinualRemoteAiAnalyzer.kt")
        val analyze = source.substringAfter("fun analyze(")
            .substringBefore("data class AiPositionForwardEvidence")
        val build = analyze.indexOf("promptEvidence(plan)")
        val remote = analyze.indexOf("delegate.analyze(")
        assertTrue(build >= 0)
        assertTrue(remote > build)
        assertTrue(analyze.contains("selfLearningEvidence = selfLearningEvidence"))
    }

    @Test
    fun remotePayloadAllowsOwnLearningButStillRejectsNativeAnswers() {
        val source = source("AiAnalysis.kt")
        assertTrue(source.contains("raw-history+ai-self-learning-v2"))
        assertTrue(source.contains("ai_self_learning_evidence"))
        assertTrue(source.contains("原始历史+AI自学习证据 · 严格隔离本机答案"))
        val payload = source.substringAfter("private fun analysisPayload(")
            .substringBefore("private fun isRetriableModelOutput")
        assertFalse(payload.contains("report.selectedPosition"))
        assertFalse(payload.contains("report.selected.top6"))
        assertFalse(payload.contains("native_model_reference"))
    }
}
