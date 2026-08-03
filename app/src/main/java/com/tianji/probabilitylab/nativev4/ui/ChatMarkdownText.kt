package com.tianji.probabilitylab.nativev4.ui

import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.unit.TextUnit

private val headingPattern = Regex("""^\s{0,3}(#{1,6})\s+(.+)$""")
private val bulletPattern = Regex("""^\s*[-*+]\s+(.+)$""")
private val quotePattern = Regex("""^\s*>\s?(.*)$""")
private val horizontalRulePattern = Regex("""^\s*(?:-{3,}|\*{3,}|_{3,})\s*$""")

@Composable
internal fun ChatMarkdownText(
    text: String,
    color: Color,
    fontSize: TextUnit,
    lineHeight: TextUnit,
    modifier: Modifier = Modifier,
) {
    val rendered = remember(text) { parseChatMarkdown(text) }
    Text(
        text = rendered,
        color = color,
        fontSize = fontSize,
        lineHeight = lineHeight,
        fontWeight = FontWeight.Normal,
        modifier = modifier,
    )
}

internal fun parseChatMarkdown(raw: String): AnnotatedString = buildAnnotatedString {
    val lines = raw.replace("\r\n", "\n").replace('\r', '\n').split('\n')
    lines.forEachIndexed { index, line ->
        appendMarkdownLine(line)
        if (index != lines.lastIndex) append('\n')
    }
}

private fun AnnotatedString.Builder.appendMarkdownLine(line: String) {
    if (horizontalRulePattern.matches(line)) {
        append("────────────")
        return
    }

    val heading = headingPattern.matchEntire(line)
    if (heading != null) {
        withStyle(SpanStyle(fontWeight = FontWeight.Bold)) {
            appendInlineMarkdown(heading.groupValues[2])
        }
        return
    }

    val quote = quotePattern.matchEntire(line)
    if (quote != null) {
        append("▍ ")
        withStyle(SpanStyle(fontStyle = FontStyle.Italic)) {
            appendInlineMarkdown(quote.groupValues[1])
        }
        return
    }

    val bullet = bulletPattern.matchEntire(line)
    if (bullet != null) {
        append("• ")
        appendInlineMarkdown(bullet.groupValues[1])
        return
    }

    appendInlineMarkdown(line)
}

private fun AnnotatedString.Builder.appendInlineMarkdown(source: String) {
    var index = 0
    while (index < source.length) {
        when {
            source[index] == '\\' && index + 1 < source.length -> {
                append(source[index + 1])
                index += 2
            }
            source.startsWith("**", index) || source.startsWith("__", index) -> {
                val marker = source.substring(index, index + 2)
                val end = source.indexOf(marker, index + 2)
                if (end >= index + 2) {
                    withStyle(SpanStyle(fontWeight = FontWeight.Bold)) {
                        append(source.substring(index + 2, end))
                    }
                    index = end + 2
                } else {
                    // 流式输出可能暂时只有开头标记，隐藏标记避免星号闪烁。
                    index += 2
                }
            }
            source[index] == '`' -> {
                val end = source.indexOf('`', index + 1)
                if (end > index + 1) {
                    withStyle(SpanStyle(fontFamily = FontFamily.Monospace)) {
                        append(source.substring(index + 1, end))
                    }
                    index = end + 1
                } else {
                    index++
                }
            }
            source[index] == '*' || source[index] == '_' -> {
                val marker = source[index]
                val end = source.indexOf(marker, index + 1)
                if (end > index + 1) {
                    withStyle(SpanStyle(fontStyle = FontStyle.Italic)) {
                        append(source.substring(index + 1, end))
                    }
                    index = end + 1
                } else {
                    append(marker)
                    index++
                }
            }
            source[index] == '[' -> {
                val labelEnd = source.indexOf(']', index + 1)
                val urlStart = if (labelEnd >= 0) source.indexOf('(', labelEnd + 1) else -1
                val urlEnd = if (urlStart == labelEnd + 1) source.indexOf(')', urlStart + 1) else -1
                if (labelEnd > index && urlStart == labelEnd + 1 && urlEnd > urlStart) {
                    withStyle(SpanStyle(fontWeight = FontWeight.Medium)) {
                        append(source.substring(index + 1, labelEnd))
                    }
                    index = urlEnd + 1
                } else {
                    append(source[index])
                    index++
                }
            }
            else -> {
                append(source[index])
                index++
            }
        }
    }
}
