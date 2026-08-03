package com.tianji.probabilitylab.nativev4.ai

import java.net.SocketException
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class AiErrorMessagesTest {
    @Test
    fun localizesConnectionAbort() {
        assertEquals(
            "网络连接在模型输出过程中中断，本次未自动重新预测",
            AiErrorMessages.userFacing(
                SocketException("Software caused connection abort"),
                "AI 分析失败",
            ),
        )
    }

    @Test
    fun keepsExistingChineseError() {
        val value = AiErrorMessages.userFacing(
            IllegalStateException("模型返回了空内容"),
            "AI 分析失败",
        )
        assertEquals("模型返回了空内容", value)
    }

    @Test
    fun hidesUnknownRawEnglishMessage() {
        val value = AiErrorMessages.userFacing(
            IllegalStateException("some internal provider exception"),
            "AI 分析失败",
        )
        assertTrue(value.startsWith("AI 分析失败"))
        assertFalse(value.contains("internal provider"))
    }
}
