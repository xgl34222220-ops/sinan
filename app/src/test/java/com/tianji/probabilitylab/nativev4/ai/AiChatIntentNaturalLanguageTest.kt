package com.tianji.probabilitylab.nativev4.ai

import org.junit.Assert.assertEquals
import org.junit.Test

class AiChatIntentNaturalLanguageTest {
    @Test
    fun explanationContainingCandidateCountDoesNotStartAnotherPrediction() {
        assertEquals(
            AiChatIntent.LOTTERY_ANALYSIS,
            AiChatIntentRouter.resolve("为什么刚才给了两个号码"),
        )
    }

    @Test
    fun directCandidateRequestStartsPredictionWithoutRigidPhrasing() {
        assertEquals(
            AiChatIntent.LOTTERY_PREDICTION,
            AiChatIntentRouter.resolve("分析第一名，给两个号码"),
        )
    }

    @Test
    fun explicitNoPredictionAlwaysWins() {
        assertEquals(
            AiChatIntent.LOTTERY_ANALYSIS,
            AiChatIntentRouter.resolve("分析第一名，不要预测也不要给号码"),
        )
    }
}
