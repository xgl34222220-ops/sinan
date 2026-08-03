package com.tianji.probabilitylab.nativev4.ui

import com.tianji.probabilitylab.nativev4.ai.AiChatMessage
import com.tianji.probabilitylab.nativev4.ai.AiChatRole
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class ChatMessageActionsTest {
    @Test
    fun clipboardAndSpeechUseRenderedPlainText() {
        assertEquals(
            "结论\n• 号码 8",
            chatMessagePlainText("**结论**\n- 号码 8"),
        )
    }

    @Test
    fun assistantRepeatUsesItsPrecedingUserPrompt() {
        val messages = listOf(
            AiChatMessage(id = "u1", role = AiChatRole.USER, content = "分析第五名"),
            AiChatMessage(id = "a1", role = AiChatRole.ASSISTANT, content = "第一版回答"),
            AiChatMessage(id = "u2", role = AiChatRole.USER, content = "再比较遗漏"),
            AiChatMessage(id = "a2", role = AiChatRole.ASSISTANT, content = "第二版回答"),
        )
        assertEquals("分析第五名", repeatPromptFor(messages, "a1"))
        assertEquals("再比较遗漏", repeatPromptFor(messages, "a2"))
        assertEquals("再比较遗漏", repeatPromptFor(messages, "u2"))
    }

    @Test
    fun systemMessagesCannotTriggerAnotherPaidRequest() {
        val messages = listOf(
            AiChatMessage(id = "s", role = AiChatRole.SYSTEM, content = "目标期已切换"),
        )
        assertNull(repeatPromptFor(messages, "s"))
    }
}
