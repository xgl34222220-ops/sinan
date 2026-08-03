package com.tianji.probabilitylab.nativev4.ui

import com.tianji.probabilitylab.nativev4.ai.AiChatMessage
import com.tianji.probabilitylab.nativev4.ai.AiChatRole

/** Plain text used by clipboard and Android text-to-speech. */
internal fun chatMessagePlainText(content: String): String =
    parseChatMarkdown(content).text.trim()

/**
 * Resolves the explicit prompt for “再次提问/重新回答”. Assistant regeneration uses the user
 * message immediately preceding that answer and appends a new turn, so the old answer is retained.
 */
internal fun repeatPromptFor(messages: List<AiChatMessage>, messageId: String): String? {
    val index = messages.indexOfFirst { it.id == messageId }
    if (index < 0) return null
    val message = messages[index]
    return when (message.role) {
        AiChatRole.USER -> message.content.trim().takeIf(String::isNotBlank)
        AiChatRole.ASSISTANT -> messages.subList(0, index)
            .lastOrNull { it.role == AiChatRole.USER && it.content.isNotBlank() }
            ?.content
            ?.trim()
        AiChatRole.SYSTEM -> null
    }
}
