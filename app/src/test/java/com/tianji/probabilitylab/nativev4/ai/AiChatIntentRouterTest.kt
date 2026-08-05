package com.tianji.probabilitylab.nativev4.ai

import org.junit.Assert.assertEquals
import org.junit.Test

class AiChatIntentRouterTest {
    @Test
    fun greetingUsesFastFreeChat() {
        assertEquals(AiChatIntent.FREE_CHAT, AiChatIntentRouter.resolve("你好"))
        assertEquals(AiChatIntent.FREE_CHAT, AiChatIntentRouter.resolve("你是谁，能做什么"))
    }

    @Test
    fun explanationDoesNotBecomeAnotherPrediction() {
        assertEquals(
            AiChatIntent.LOTTERY_ANALYSIS,
            AiChatIntentRouter.resolve("为什么刚才给了六个号码？解释一下"),
        )
        assertEquals(
            AiChatIntent.LOTTERY_ANALYSIS,
            AiChatIntentRouter.resolve("分析最近走势，不要给号码"),
        )
    }

    @Test
    fun explicitCandidateRequestUsesPredictionMode() {
        assertEquals(
            AiChatIntent.LOTTERY_PREDICTION,
            AiChatIntentRouter.resolve("告诉我下一期最有可能开出的两个号码"),
        )
        assertEquals(
            AiChatIntent.LOTTERY_PREDICTION,
            AiChatIntentRouter.resolve("六码里重点看两个号码"),
        )
    }
}
