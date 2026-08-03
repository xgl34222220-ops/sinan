from pathlib import Path

path = Path("app/src/main/java/com/tianji/probabilitylab/nativev4/ui/AiChatDialog.kt")
text = path.read_text(encoding="utf-8")

if "private fun ChatMessageActions(" in text:
    print("Chat message actions already applied")
    raise SystemExit(0)


def replace_once(old: str, new: str, name: str) -> None:
    global text
    if old not in text:
        raise SystemExit(f"{name} anchor not found")
    text = text.replace(old, new, 1)


replace_once(
    "package com.tianji.probabilitylab.nativev4.ui\n\n",
    "package com.tianji.probabilitylab.nativev4.ui\n\n"
    "import android.speech.tts.TextToSpeech\n"
    "import android.widget.Toast\n",
    "package imports",
)
replace_once(
    "import androidx.compose.foundation.text.KeyboardOptions\n",
    "import androidx.compose.foundation.text.KeyboardOptions\n"
    "import androidx.compose.foundation.text.selection.SelectionContainer\n",
    "selection import",
)
replace_once(
    "import androidx.compose.runtime.Composable\n",
    "import androidx.compose.runtime.Composable\n"
    "import androidx.compose.runtime.DisposableEffect\n",
    "disposable import",
)
replace_once(
    "import androidx.compose.ui.graphics.SolidColor\n",
    "import androidx.compose.ui.graphics.SolidColor\n"
    "import androidx.compose.ui.platform.LocalClipboardManager\n"
    "import androidx.compose.ui.platform.LocalContext\n"
    "import androidx.compose.ui.text.AnnotatedString\n",
    "clipboard imports",
)

replace_once(
    """    val colors = LocalTianjiColors.current
    val completeConfigs = remember(configs) { configs.filter(AiConfig::isComplete) }
""",
    """    val colors = LocalTianjiColors.current
    val context = LocalContext.current
    val clipboard = LocalClipboardManager.current
    var speechEngine by remember { mutableStateOf<TextToSpeech?>(null) }
    DisposableEffect(context.applicationContext) {
        var engine: TextToSpeech? = null
        engine = TextToSpeech(context.applicationContext) { status ->
            if (status == TextToSpeech.SUCCESS) {
                val languageResult = engine?.setLanguage(Locale.SIMPLIFIED_CHINESE)
                if (
                    languageResult == TextToSpeech.LANG_MISSING_DATA ||
                    languageResult == TextToSpeech.LANG_NOT_SUPPORTED
                ) {
                    engine?.language = Locale.getDefault()
                }
                speechEngine = engine
            }
        }
        onDispose {
            if (speechEngine === engine) speechEngine = null
            engine?.stop()
            engine?.shutdown()
        }
    }

    fun copyMessage(message: AiChatMessage) {
        val plain = chatMessagePlainText(message.content)
        if (plain.isBlank()) return
        clipboard.setText(AnnotatedString(plain))
        Toast.makeText(context, "已复制", Toast.LENGTH_SHORT).show()
    }

    fun speakMessage(message: AiChatMessage) {
        val plain = chatMessagePlainText(message.content)
        if (plain.isBlank()) return
        val engine = speechEngine
        if (engine == null) {
            Toast.makeText(context, "朗读引擎正在初始化", Toast.LENGTH_SHORT).show()
            return
        }
        val result = engine.speak(
            plain,
            TextToSpeech.QUEUE_FLUSH,
            null,
            "tianji-chat-${message.id}",
        )
        if (result == TextToSpeech.ERROR) {
            Toast.makeText(context, "当前系统朗读引擎不可用", Toast.LENGTH_SHORT).show()
        }
    }

    val completeConfigs = remember(configs) { configs.filter(AiConfig::isComplete) }
""",
    "dialog actions",
)

replace_once(
    """    }

    Dialog(
        onDismissRequest = onDismiss,
""",
    """    }

    fun repeatMessage(message: AiChatMessage) {
        if (controller.session.isRunning) return
        val prompt = repeatPromptFor(controller.session.messages, message.id)
        if (prompt.isNullOrBlank()) {
            Toast.makeText(context, "找不到这条回答对应的问题", Toast.LENGTH_SHORT).show()
            return
        }
        submit(prompt)
    }

    Dialog(
        onDismissRequest = onDismiss,
""",
    "repeat action",
)

replace_once(
    """                        ChatMessageBubble(
                            message = message,
                            isStreaming = message.id == session.streamingMessageId && session.isRunning,
                        )
""",
    """                        ChatMessageBubble(
                            message = message,
                            isStreaming = message.id == session.streamingMessageId && session.isRunning,
                            canRepeat = !session.isRunning,
                            onCopy = { copyMessage(message) },
                            onSpeak = { speakMessage(message) },
                            onRepeat = { repeatMessage(message) },
                        )
""",
    "message invocation",
)

old_bubble = """@Composable
private fun ChatMessageBubble(message: AiChatMessage, isStreaming: Boolean) {
    val colors = LocalTianjiColors.current
    if (message.role == AiChatRole.SYSTEM) {
        SystemEventChip(message.content)
        return
    }
    if (message.role == AiChatRole.USER) {
        Box(Modifier.fillMaxWidth(), contentAlignment = Alignment.CenterEnd) {
            Text(
                message.content,
                color = colors.text,
                fontSize = 13.sp,
                lineHeight = 19.sp,
                modifier = Modifier.widthIn(max = 286.dp)
                    .clip(RoundedCornerShape(18.dp, 18.dp, 6.dp, 18.dp))
                    .background(colors.accent.copy(alpha = 0.13f))
                    .padding(horizontal = 13.dp, vertical = 10.dp),
            )
        }
        return
    }

    Column(Modifier.fillMaxWidth().animateContentSize()) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Icon(Icons.Rounded.AutoAwesome, null, tint = colors.accent, modifier = Modifier.size(13.dp))
            Spacer(Modifier.width(5.dp))
            Text("天机", color = colors.accent, fontSize = 9.5.sp, fontWeight = FontWeight.Bold)
        }
        Spacer(Modifier.height(5.dp))
        val visible = when {
            message.content.isNotBlank() && isStreaming -> message.content + " ▍"
            message.content.isNotBlank() -> message.content
            isStreaming -> "正在思考，等待第一段正文…"
            else -> ""
        }
        ChatMarkdownText(
            text = visible,
            color = if (message.content.isBlank()) colors.textDim else colors.textSoft,
            fontSize = 13.5.sp,
            lineHeight = 21.sp,
        )
        message.latencyMs?.let {
            Text(
                "${it / 1_000.0}s",
                color = colors.textDim,
                fontSize = 8.5.sp,
                modifier = Modifier.padding(top = 5.dp),
            )
        }
    }
}
"""

new_bubble = """@Composable
private fun ChatMessageBubble(
    message: AiChatMessage,
    isStreaming: Boolean,
    canRepeat: Boolean,
    onCopy: () -> Unit,
    onSpeak: () -> Unit,
    onRepeat: () -> Unit,
) {
    val colors = LocalTianjiColors.current
    if (message.role == AiChatRole.SYSTEM) {
        SystemEventChip(message.content)
        return
    }
    if (message.role == AiChatRole.USER) {
        Column(Modifier.fillMaxWidth(), horizontalAlignment = Alignment.End) {
            SelectionContainer {
                Text(
                    message.content,
                    color = colors.text,
                    fontSize = 13.sp,
                    lineHeight = 19.sp,
                    modifier = Modifier.widthIn(max = 286.dp)
                        .clip(RoundedCornerShape(18.dp, 18.dp, 6.dp, 18.dp))
                        .background(colors.accent.copy(alpha = 0.13f))
                        .padding(horizontal = 13.dp, vertical = 10.dp),
                )
            }
            ChatMessageActions(
                role = message.role,
                enabled = canRepeat,
                onCopy = onCopy,
                onSpeak = onSpeak,
                onRepeat = onRepeat,
            )
        }
        return
    }

    Column(Modifier.fillMaxWidth().animateContentSize()) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Icon(Icons.Rounded.AutoAwesome, null, tint = colors.accent, modifier = Modifier.size(13.dp))
            Spacer(Modifier.width(5.dp))
            Text("天机", color = colors.accent, fontSize = 9.5.sp, fontWeight = FontWeight.Bold)
        }
        Spacer(Modifier.height(5.dp))
        val visible = when {
            message.content.isNotBlank() && isStreaming -> message.content + " ▍"
            message.content.isNotBlank() -> message.content
            isStreaming -> "正在思考，等待第一段正文…"
            else -> ""
        }
        SelectionContainer {
            ChatMarkdownText(
                text = visible,
                color = if (message.content.isBlank()) colors.textDim else colors.textSoft,
                fontSize = 13.5.sp,
                lineHeight = 21.sp,
            )
        }
        message.latencyMs?.let {
            Text(
                "${it / 1_000.0}s",
                color = colors.textDim,
                fontSize = 8.5.sp,
                modifier = Modifier.padding(top = 5.dp),
            )
        }
        if (!isStreaming && message.content.isNotBlank()) {
            ChatMessageActions(
                role = message.role,
                enabled = canRepeat,
                onCopy = onCopy,
                onSpeak = onSpeak,
                onRepeat = onRepeat,
            )
        }
    }
}

@Composable
private fun ChatMessageActions(
    role: AiChatRole,
    enabled: Boolean,
    onCopy: () -> Unit,
    onSpeak: () -> Unit,
    onRepeat: () -> Unit,
) {
    Row(
        modifier = Modifier.padding(top = 5.dp),
        horizontalArrangement = Arrangement.spacedBy(3.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        ChatMessageAction("复制", true, onCopy)
        ChatMessageAction("朗读", true, onSpeak)
        ChatMessageAction(
            if (role == AiChatRole.USER) "再次提问" else "重新回答",
            enabled,
            onRepeat,
        )
    }
}

@Composable
private fun ChatMessageAction(label: String, enabled: Boolean, onClick: () -> Unit) {
    val colors = LocalTianjiColors.current
    Text(
        label,
        color = if (enabled) colors.textDim else colors.textDim.copy(alpha = 0.38f),
        fontSize = 9.sp,
        fontWeight = FontWeight.Medium,
        modifier = Modifier.clip(RoundedCornerShape(9.dp))
            .clickable(enabled = enabled, onClick = onClick)
            .padding(horizontal = 7.dp, vertical = 4.dp),
    )
}
"""
replace_once(old_bubble, new_bubble, "message bubble")

path.write_text(text, encoding="utf-8")
print("Applied chat message actions")
