package com.tianji.probabilitylab.nativev4.ai

import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class AiRuntimeRecoveryContractTest {
    private fun source(name: String): String = File(
        "src/main/java/com/tianji/probabilitylab/nativev4/ai/$name",
    ).readText()

    @Test
    fun chatFinalizesReasoningOnlyAndEmptyStreams() {
        val text = source("AiChatController.kt")
        assertTrue(text.contains("模型只返回了思考流"))
        assertTrue(text.contains("流式接口没有返回正文"))
        assertTrue(text.contains("finalizationDecision"))
        assertTrue(text.contains("rawContent.isBlank() && reasoning.isBlank()"))
        assertTrue(text.contains("reasoning_content"))
        assertTrue(text.contains("thinking"))
        assertFalse(text.contains("模型没有返回可显示的流式回答"))
    }

    @Test
    fun formalForecastUsesOneBoundedSameModelClosure() {
        val text = source("AiAnalysis.kt")
        assertTrue(text.contains("isRetriableModelOutput(firstFailure)"))
        assertTrue(text.contains("同模型限时核心收口"))
        assertTrue(text.contains("effectiveTokenBudget"))
        assertTrue(text.contains("正式预测核心输出预算 4096 tokens"))
        assertFalse(text.contains("本次已停止，未自动重新预测"))
    }

    @Test
    fun deepSeekAutoForecastPrioritizesCompletion() {
        val text = source("AiReasoning.kt")
        assertTrue(text.contains("正式预测自动省时 · 对话保留思考"))
        assertTrue(text.contains("enableThinking = false"))
    }
}
