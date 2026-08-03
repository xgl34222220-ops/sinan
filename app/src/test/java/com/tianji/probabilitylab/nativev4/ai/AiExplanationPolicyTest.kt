package com.tianji.probabilitylab.nativev4.ai

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class AiExplanationPolicyTest {
    @Test
    fun acceptsBalancedMultiFactorWeights() {
        val audit = AiExplanationPolicy.auditWeights(listOf(0.20, 0.20, 0.25, 0.25, 0.10))

        assertTrue(audit.validMultiFactor)
        assertEquals(5, audit.normalizedWeights.size)
        assertEquals(1.0, audit.normalizedWeights.sum(), 1e-9)
    }

    @Test
    fun rejectsSingleOrTwoFactorShortcut() {
        assertFalse(
            AiExplanationPolicy.auditWeights(listOf(0.0, 0.0, 0.5, 0.5, 0.0)).validMultiFactor,
        )
        assertFalse(
            AiExplanationPolicy.auditWeights(listOf(0.75, 0.10, 0.05, 0.05, 0.05)).validMultiFactor,
        )
    }

    @Test
    fun distinguishesChineseExplanationFromEnglishOnlyText() {
        assertTrue(
            AiExplanationPolicy.isChineseExplanation(
                "综合近20期和近60期频次，并结合遗漏与后继转移。",
                "第九名的多项统计分歧较小。",
                "候选排序由多因素共同决定。",
                "样本有限，结论存在波动。",
            ),
        )
        assertFalse(
            AiExplanationPolicy.isChineseExplanation(
                "The raw score is omission plus transition count.",
                "Position nine has the largest omission.",
                "Candidates follow the same formula.",
                "The sample is limited.",
            ),
        )
    }
}
