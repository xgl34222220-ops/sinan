package com.tianji.probabilitylab.nativev4.ui

import androidx.compose.ui.text.font.FontWeight
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class ChatMarkdownTextTest {
    @Test
    fun boldMarkersAreRenderedWithoutRawAsterisks() {
        val rendered = parseChatMarkdown("**④ 号码 9**\n**注意：** 不承诺必中")
        assertEquals("④ 号码 9\n注意： 不承诺必中", rendered.text)
        assertTrue(rendered.spanStyles.any { it.item.fontWeight == FontWeight.Bold })
    }

    @Test
    fun blockSyntaxBecomesReadablePlainStructure() {
        val rendered = parseChatMarkdown("- 最近20期5次\n> 仅代表历史相对频次\n---")
        assertEquals("• 最近20期5次\n▍ 仅代表历史相对频次\n────────────", rendered.text)
    }

    @Test
    fun unfinishedStreamingBoldMarkerDoesNotFlashStars() {
        val rendered = parseChatMarkdown("当前结果：**号码 9")
        assertEquals("当前结果：号码 9", rendered.text)
    }
}
