from pathlib import Path

ROOT = Path('.')


def replace_once(path: str, old: str, new: str) -> None:
    file = ROOT / path
    text = file.read_text(encoding='utf-8')
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{path}: expected one match, found {count}: {old[:120]!r}')
    file.write_text(text.replace(old, new, 1), encoding='utf-8')


analysis_path = ROOT / 'app/src/main/java/com/tianji/probabilitylab/nativev4/ai/AiAnalysis.kt'
analysis = analysis_path.read_text(encoding='utf-8')

old_imports = '''import java.net.HttpURLConnection
import java.net.SocketTimeoutException
import java.net.URL'''
new_imports = '''import java.io.EOFException
import java.io.IOException
import java.net.HttpURLConnection
import java.net.SocketException
import java.net.SocketTimeoutException
import java.net.URL'''
if analysis.count(old_imports) != 1:
    raise SystemExit('AiAnalysis.kt: network import block changed unexpectedly')
analysis = analysis.replace(old_imports, new_imports, 1)

old_catches = '''            } catch (_: SocketTimeoutException) {
                onProgress(
                    "等待模型输出超时，本次请求已停止，不会自动重新预测",
                    System.currentTimeMillis() - started,
                )
                error("模型响应超过 ${readTimeoutMs / 1_000} 秒；本次已停止，未自动重新预测")
            } finally {'''
new_catches = '''            } catch (_: SocketTimeoutException) {
                onProgress(
                    "等待模型输出超时，本次请求已停止，不会自动重新预测",
                    System.currentTimeMillis() - started,
                )
                error("模型响应超过 ${readTimeoutMs / 1_000} 秒；本次已停止，未自动重新预测")
            } catch (cause: EOFException) {
                val message = transportFailureMessage(cause)
                onProgress("$message，本次未自动重新预测", System.currentTimeMillis() - started)
                error("$message；本次未自动重新预测")
            } catch (cause: SocketException) {
                val message = transportFailureMessage(cause)
                onProgress("$message，本次未自动重新预测", System.currentTimeMillis() - started)
                error("$message；本次未自动重新预测")
            } catch (cause: IOException) {
                val message = transportFailureMessage(cause)
                onProgress("$message，本次未自动重新预测", System.currentTimeMillis() - started)
                error("$message；本次未自动重新预测")
            } finally {'''
if analysis.count(old_catches) != 1:
    raise SystemExit('AiAnalysis.kt: network catch block changed unexpectedly')
analysis = analysis.replace(old_catches, new_catches, 1)

stream_start = analysis.index('        reader.forEachLine { rawLine ->')
stream_end_marker = '\n    private fun JSONObject.streamPhaseSummary(): String {'
stream_end = analysis.index(stream_end_marker, stream_start)
new_stream_tail = '''        var streamFailure: IOException? = null
        try {
            reader.forEachLine { rawLine ->
                val line = rawLine.trim()
                if (line.isBlank()) return@forEachLine
                if (!line.startsWith("data:")) {
                    if (line.startsWith("{")) plainBody.append(line)
                    return@forEachLine
                }
                val payload = line.removePrefix("data:").trim()
                if (payload == "[DONE]" || payload.isBlank()) return@forEachLine
                val chunk = runCatching { JSONObject(payload) }.getOrNull() ?: return@forEachLine
                responseId = chunk.optString("id").ifBlank { responseId }
                chunk.optJSONObject("usage")?.let { usage = it }
                val choice = chunk.optJSONArray("choices")?.optJSONObject(0) ?: return@forEachLine
                finishReason = choice.optString("finish_reason").ifBlank { finishReason }
                val delta = choice.optJSONObject("delta") ?: return@forEachLine
                val reasoningPart = delta.optString("reasoning_content")
                val contentPart = delta.optString("content")
                if (reasoningPart.isNotEmpty()) {
                    if (firstReasoningMs < 0L) firstReasoningMs = System.currentTimeMillis() - startedAtMs
                    reasoning.append(reasoningPart)
                    report("模型正在推理 · 已收到 ${reasoning.length} 个推理字符")
                }
                if (contentPart.isNotEmpty()) {
                    if (firstContentMs < 0L) firstContentMs = System.currentTimeMillis() - startedAtMs
                    content.append(contentPart)
                    if (AiForecastPayloadExtractor.containsForecastCore(content.toString())) {
                        report("已收到完整预测核心，正在校验说明与结束状态")
                    } else {
                        report("模型正在生成结构化预测 · 已收到 ${content.length} 个结果字符")
                    }
                }
            }
        } catch (cause: IOException) {
            streamFailure = cause
        }

        if (content.isEmpty() && reasoning.isEmpty() && plainBody.isNotEmpty()) {
            val plainJson = runCatching { JSONObject(plainBody.toString()) }.getOrElse { parseFailure ->
                streamFailure?.let { throw it }
                throw parseFailure
            }
            streamFailure?.let { failure ->
                plainJson.put("_tianji_stream_interrupted", true)
                plainJson.put("_tianji_stream_error", transportFailureMessage(failure))
                onProgress(
                    "网络连接中断，但已恢复服务器返回内容，正在本机校验",
                    System.currentTimeMillis() - startedAtMs,
                )
            }
            return plainJson
        }

        val message = JSONObject().put("content", content.toString())
        if (reasoning.isNotEmpty()) message.put("reasoning_content", reasoning.toString())
        val result = JSONObject()
            .put("id", responseId)
            .put(
                "choices",
                JSONArray().put(
                    JSONObject()
                        .put("index", 0)
                        .put(
                            "finish_reason",
                            finishReason.ifBlank {
                                if (streamFailure == null) "stop" else "network_interrupted"
                            },
                        )
                        .put("message", message),
                ),
            )
            .apply {
                usage?.let { put("usage", it) }
                put("_tianji_first_reasoning_ms", firstReasoningMs)
                put("_tianji_first_content_ms", firstContentMs)
                put("_tianji_stream_finished_ms", System.currentTimeMillis() - startedAtMs)
            }

        streamFailure?.let { failure ->
            if (content.isEmpty() && reasoning.isEmpty()) throw failure
            result.put("_tianji_stream_interrupted", true)
            result.put("_tianji_stream_error", transportFailureMessage(failure))
            onProgress(
                if (result.hasCompleteForecastContent()) {
                    "网络连接中断，但已恢复完整预测核心，正在本机校验"
                } else {
                    "网络连接中断，已保留已接收内容，正在沿用同一对话补全结果"
                },
                System.currentTimeMillis() - startedAtMs,
            )
        }
        return result
    }

    private fun transportFailureMessage(cause: Throwable): String {
        val message = cause.message.orEmpty().lowercase()
        return when {
            cause is SocketTimeoutException -> "等待模型输出超时"
            cause is EOFException -> "模型连接提前结束"
            cause is SocketException && listOf(
                "software caused connection abort",
                "connection reset",
                "broken pipe",
                "socket closed",
            ).any(message::contains) -> "网络连接被系统、代理或服务器中断"
            cause is SocketException -> "网络连接异常中断"
            cause is IOException -> "网络连接在模型输出过程中中断"
            else -> "AI 网络请求失败"
        }
    }
'''
analysis = analysis[:stream_start] + new_stream_tail + analysis[stream_end:]

old_phase = '''        if (finished < 0L) return ""
        fun seconds(value: Long): String = String.format(java.util.Locale.US, "%.1fs", value / 1000.0)
        return when {
            firstReasoning >= 0L && firstContent >= firstReasoning ->
                "首个推理 ${seconds(firstReasoning)} · 推理阶段 ${seconds(firstContent - firstReasoning)} · 结果阶段 ${seconds((finished - firstContent).coerceAtLeast(0L))}"
            firstContent >= 0L ->
                "首个结果 ${seconds(firstContent)} · 结果阶段 ${seconds((finished - firstContent).coerceAtLeast(0L))}"
            else -> "响应总耗时 ${seconds(finished)}"
        }'''
new_phase = '''        if (finished < 0L) return ""
        fun seconds(value: Long): String = String.format(java.util.Locale.US, "%.1fs", value / 1000.0)
        val timing = when {
            firstReasoning >= 0L && firstContent >= firstReasoning ->
                "首个推理 ${seconds(firstReasoning)} · 推理阶段 ${seconds(firstContent - firstReasoning)} · 结果阶段 ${seconds((finished - firstContent).coerceAtLeast(0L))}"
            firstContent >= 0L ->
                "首个结果 ${seconds(firstContent)} · 结果阶段 ${seconds((finished - firstContent).coerceAtLeast(0L))}"
            else -> "响应总耗时 ${seconds(finished)}"
        }
        return if (optBoolean("_tianji_stream_interrupted")) "$timing · 断流后已恢复" else timing'''
if analysis.count(old_phase) != 1:
    raise SystemExit('AiAnalysis.kt: stream phase summary changed unexpectedly')
analysis = analysis.replace(old_phase, new_phase, 1)
analysis_path.write_text(analysis, encoding='utf-8')

# Compact alternating reasoning/output updates into one live card per stage.
timeline_path = ROOT / 'app/src/main/java/com/tianji/probabilitylab/nativev4/ai/AiConversationTimeline.kt'
timeline = timeline_path.read_text(encoding='utf-8')
timeline = timeline.replace(
    '        "失败" in message || "超时" in message || "错误" in message -> AiConversationStage.ERROR',
    '        "失败" in message || "超时" in message || "错误" in message || "中断" in message || "断流" in message -> AiConversationStage.ERROR',
    1,
)
old_merge = '''        val replaceLatest = next.stage in setOf(
            AiConversationStage.REASONING,
            AiConversationStage.OUTPUT,
            AiConversationStage.CONNECTED,
        ) && existing.lastOrNull()?.stage == next.stage
        val merged = if (replaceLatest) existing.dropLast(1) + next else existing + next
        return merged.takeLast(maxEvents.coerceAtLeast(1))'''
new_merge = '''        val replaceableStages = setOf(
            AiConversationStage.REASONING,
            AiConversationStage.OUTPUT,
            AiConversationStage.CONNECTED,
        )
        val phaseBoundaries = setOf(
            AiConversationStage.CONTINUATION,
            AiConversationStage.RETRY,
            AiConversationStage.SUCCESS,
            AiConversationStage.ERROR,
            AiConversationStage.CANCELLED,
        )
        val merged = if (next.stage in replaceableStages) {
            val boundaryIndex = existing.indexOfLast { it.stage in phaseBoundaries }
            val replaceIndex = existing.indices.reversed().firstOrNull { index ->
                index > boundaryIndex && existing[index].stage == next.stage
            }
            if (replaceIndex == null) {
                existing + next
            } else {
                existing.toMutableList().apply { this[replaceIndex] = next }
            }
        } else {
            existing + next
        }
        return merged.takeLast(maxEvents.coerceAtLeast(1))'''
if timeline.count(old_merge) != 1:
    raise SystemExit('AiConversationTimeline.kt: merge block changed unexpectedly')
timeline = timeline.replace(old_merge, new_merge, 1)
timeline_path.write_text(timeline, encoding='utf-8')

# Prevent raw English transport exceptions from leaking into the UI.
error_messages = '''package com.tianji.probabilitylab.nativev4.ai

object AiErrorMessages {
    fun userFacing(error: Throwable, fallback: String): String {
        val message = error.message.orEmpty().trim()
        val lower = message.lowercase()
        return when {
            listOf(
                "software caused connection abort",
                "connection reset",
                "broken pipe",
                "socket closed",
                "unexpected end of stream",
            ).any(lower::contains) -> "网络连接在模型输出过程中中断，本次未自动重新预测"
            "timeout" in lower || "timed out" in lower -> "等待接口响应超时，请检查网络或稍后重试"
            message.any { it in '\u4e00'..'\u9fff' } -> message.take(180)
            else -> "$fallback，请检查网络、代理或接口设置"
        }
    }
}
'''
(ROOT / 'app/src/main/java/com/tianji/probabilitylab/nativev4/ai/AiErrorMessages.kt').write_text(
    error_messages,
    encoding='utf-8',
)

controller_path = ROOT / 'app/src/main/java/com/tianji/probabilitylab/nativev4/AppController.kt'
controller = controller_path.read_text(encoding='utf-8')
import_anchor = 'import com.tianji.probabilitylab.nativev4.ai.AiConnectionState\n'
if controller.count(import_anchor) != 1:
    raise SystemExit('AppController.kt: import anchor changed unexpectedly')
controller = controller.replace(
    import_anchor,
    import_anchor + 'import com.tianji.probabilitylab.nativev4.ai.AiErrorMessages\n',
    1,
)
controller = controller.replace(
    'message = it.message ?: "读取模型列表失败",',
    'message = AiErrorMessages.userFacing(it, "读取模型列表失败"),',
    1,
)
controller = controller.replace(
    'message = it.message ?: "连接失败",',
    'message = AiErrorMessages.userFacing(it, "连接失败"),',
    1,
)
controller = controller.replace(
    'val failureMessage = it.message ?: "AI 分析失败"',
    'val failureMessage = AiErrorMessages.userFacing(it, "AI 分析失败")',
    1,
)
controller_path.write_text(controller, encoding='utf-8')

# Tests.
timeline_test_path = ROOT / 'app/src/test/java/com/tianji/probabilitylab/nativev4/ai/AiConversationTimelineTest.kt'
timeline_test = timeline_test_path.read_text(encoding='utf-8')
classification_anchor = '''        assertEquals(
            AiConversationStage.RETRY,
            AiConversationTimeline.classify("接口拒绝参数，正在切换模型默认思考协议"),
        )'''
classification_new = classification_anchor + '''
        assertEquals(
            AiConversationStage.ERROR,
            AiConversationTimeline.classify("网络连接中断，已保留已接收内容"),
        )'''
if timeline_test.count(classification_anchor) != 1:
    raise SystemExit('AiConversationTimelineTest.kt: classification anchor changed unexpectedly')
timeline_test = timeline_test.replace(classification_anchor, classification_new, 1)
insert_marker = '''    @Test
    fun preservesPhaseChangesAndCapsHistory() {'''
new_test = '''    @Test
    fun compactsAlternatingReasoningAndOutputUpdates() {
        var events = emptyList<AiConversationEvent>()
        repeat(8) { index ->
            events = AiConversationTimeline.merge(
                events,
                AiConversationTimeline.event(
                    AiConversationStage.REASONING,
                    "推理-$index",
                    index.toLong(),
                    index.toLong(),
                ),
            )
            events = AiConversationTimeline.merge(
                events,
                AiConversationTimeline.event(
                    AiConversationStage.OUTPUT,
                    "结果-$index",
                    index.toLong(),
                    index.toLong(),
                ),
            )
        }
        assertEquals(2, events.size)
        assertEquals("推理-7", events.first { it.stage == AiConversationStage.REASONING }.message)
        assertEquals("结果-7", events.first { it.stage == AiConversationStage.OUTPUT }.message)
    }

'''
if timeline_test.count(insert_marker) != 1:
    raise SystemExit('AiConversationTimelineTest.kt: insertion marker changed unexpectedly')
timeline_test = timeline_test.replace(insert_marker, new_test + insert_marker, 1)
timeline_test_path.write_text(timeline_test, encoding='utf-8')

error_test = '''package com.tianji.probabilitylab.nativev4.ai

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
'''
(ROOT / 'app/src/test/java/com/tianji/probabilitylab/nativev4/ai/AiErrorMessagesTest.kt').write_text(
    error_test,
    encoding='utf-8',
)

# Version and notes.
replace_once('app/build.gradle.kts', '        versionCode = 32', '        versionCode = 33')
replace_once('app/build.gradle.kts', '        versionName = "5.5.7"', '        versionName = "5.5.8"')

release_notes = '''# 天机 v5.5.8

本版修复正式预测长连接中断后整次结果丢失，以及过程卡片重复堆叠的问题。

## 断流恢复

- 捕获 Socket、EOF 和普通网络 I/O 中断，不再直接显示 `Software caused connection abort` 等英文底层错误。
- 连接中断时优先抢救已经接收的内容；若预测核心完整，直接进入本机校验并保存结果。
- 若只有部分推理或部分结果，保留当前内容并沿用同一对话补全最终 JSON，不重新执行整段历史分析。
- 若没有任何可恢复内容，使用中文错误提示，并明确不会自动重复调用计费接口。
- 结果记录会标记“断流后已恢复”，方便后续诊断。

## 过程界面

- 推理和结构化结果阶段改为原位更新；即使二者交替流式输出，也各自只保留一张实时卡片。
- 网络中断和断流恢复会被正确归类为错误/恢复阶段，不再错误显示成普通请求。

## 错误安全

- 模型列表、连接测试和正式分析统一转换用户可读错误。
- 未识别的英文供应商异常不再原样泄露到界面。

## 验证

- 新增连接中断中文化测试。
- 新增交替推理/结果卡片压缩测试。
- 通过 Debug/Release 单元测试、Android Lint 和 Release APK 构建后再合并。
'''
(ROOT / 'RELEASE_NOTES_v5.5.8.md').write_text(release_notes, encoding='utf-8')

readme_path = ROOT / 'README.md'
readme = readme_path.read_text(encoding='utf-8')
readme = readme.replace('- 版本：5.5.7 正式版', '- 版本：5.5.8 修复版', 1)
marker = '## v5.5.7 速度与后台对话修复\n'
section = '''## v5.5.8 断流恢复与过程收口

- 正式预测流式连接中断后会抢救已接收的完整预测核心；只有部分内容时沿用同一对话补全，不重复执行历史分析。
- Socket、EOF 和普通 I/O 异常统一转换为中文提示，不再在界面显示底层英文错误。
- 推理与结果过程卡片改为分阶段原位更新，避免交替输出时不断向下堆叠。

'''
if readme.count(marker) != 1:
    raise SystemExit('README.md: v5.5.7 marker changed unexpectedly')
readme = readme.replace(marker, section + marker, 1)
readme_path.write_text(readme, encoding='utf-8')

# Sanity checks and remove one-time bootstrap files from the clean commit.
final_analysis = analysis_path.read_text(encoding='utf-8')
assert 'catch (cause: SocketException)' in final_analysis
assert '_tianji_stream_interrupted' in final_analysis
assert '断流后已恢复' in final_analysis
assert 'Software caused connection abort' not in controller_path.read_text(encoding='utf-8')

(ROOT / '.github/scripts/apply-v5.5.8.py').unlink()
(ROOT / '.github/workflows/apply-v5.5.8.yml').unlink()
