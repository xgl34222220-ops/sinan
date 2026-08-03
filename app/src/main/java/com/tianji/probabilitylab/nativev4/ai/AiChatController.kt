package com.tianji.probabilitylab.nativev4.ai

import android.os.Handler
import android.os.Looper
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import com.tianji.probabilitylab.nativev4.model.Draw
import com.tianji.probabilitylab.nativev4.model.DrawSnapshot
import com.tianji.probabilitylab.nativev4.model.ForecastReport
import org.json.JSONArray
import org.json.JSONObject
import java.io.BufferedReader
import java.net.HttpURLConnection
import java.net.SocketTimeoutException
import java.net.URL
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicInteger
import kotlin.math.abs
import kotlin.math.max

/**
 * Runs free-form questions independently from the official forward forecast archive.
 * Chat replies are never persisted as verified results and never replace first-frozen forecasts.
 */
class AiChatController {
    private val executor = Executors.newSingleThreadExecutor()
    private val mainHandler = Handler(Looper.getMainLooper())
    private val generation = AtomicInteger(0)
    private val client = RemoteAiChatClient()

    var session by mutableStateOf(AiChatSession(profileId = ""))
        private set

    fun selectProfile(profileId: String, targetPeriod: String?) {
        if (profileId.isBlank()) {
            if (session.profileId.isNotBlank()) {
                session = AiChatSession(
                    profileId = "",
                    personaId = session.personaId,
                    targetPeriod = targetPeriod,
                )
            }
            return
        }
        if (session.profileId == profileId && session.targetPeriod == targetPeriod) return
        cancel()
        session = AiChatSession(
            profileId = profileId,
            personaId = session.personaId,
            targetPeriod = targetPeriod,
        )
    }

    fun selectPersona(personaId: String) {
        if (session.isRunning) return
        val persona = AiChatPersona.fromId(personaId)
        if (session.personaId != persona.id) {
            session = session.copy(personaId = persona.id, error = null)
        }
    }

    fun send(
        config: AiConfig,
        snapshot: DrawSnapshot,
        report: ForecastReport,
        question: String,
    ) {
        val text = question.trim()
        if (text.isBlank() || session.isRunning) return
        selectProfile(config.id, report.targetPeriod)
        val previousMessages = AiChatProtocol.trimHistory(session.messages)
        val userMessage = AiChatMessage(role = AiChatRole.USER, content = text)
        val assistantMessage = AiChatMessage(role = AiChatRole.ASSISTANT, content = "")
        val persona = AiChatPersona.fromId(session.personaId)
        val token = generation.incrementAndGet()
        session = session.copy(
            messages = session.messages + userMessage + assistantMessage,
            isRunning = true,
            progress = "正在整理当前接口历史…",
            error = null,
            prediction = null,
            streamingMessageId = assistantMessage.id,
        )
        executor.execute {
            val result = runCatching {
                client.chat(
                    config = config,
                    snapshot = snapshot,
                    report = report,
                    previousMessages = previousMessages,
                    question = text,
                    persona = persona,
                    onProgress = { progress ->
                        mainHandler.post {
                            if (generation.get() == token && session.isRunning) {
                                session = session.copy(progress = progress)
                            }
                        }
                    },
                    onStreamText = { content ->
                        mainHandler.post {
                            if (generation.get() == token && session.isRunning) {
                                replaceMessage(assistantMessage.id) { current ->
                                    current.copy(content = content)
                                }
                            }
                        }
                    },
                )
            }
            mainHandler.post {
                if (generation.get() != token) return@post
                result.fold(
                    onSuccess = { reply ->
                        replaceMessage(assistantMessage.id) { current ->
                            current.copy(content = reply.content, latencyMs = reply.latencyMs)
                        }
                        session = session.copy(
                            isRunning = false,
                            progress = if (reply.reasoningVerified) {
                                reply.reasoningTokens?.let { "回答完成 · 推理 $it tokens" }
                                    ?: "回答完成 · 已验证模型思考"
                            } else {
                                "回答完成"
                            },
                            error = null,
                            prediction = reply.prediction,
                            streamingMessageId = null,
                        )
                    },
                    onFailure = { cause ->
                        val partial = session.messages
                            .firstOrNull { it.id == assistantMessage.id }
                            ?.content.orEmpty()
                        session = session.copy(
                            messages = if (partial.isBlank()) {
                                session.messages.filterNot { it.id == assistantMessage.id }
                            } else {
                                session.messages
                            },
                            isRunning = false,
                            progress = "",
                            error = cause.message ?: "对话分析失败",
                            streamingMessageId = null,
                        )
                    },
                )
            }
        }
    }

    fun cancel() {
        generation.incrementAndGet()
        client.cancel()
        if (session.isRunning) {
            val streamingId = session.streamingMessageId
            val partial = session.messages.firstOrNull { it.id == streamingId }?.content.orEmpty()
            session = session.copy(
                messages = if (streamingId != null && partial.isBlank()) {
                    session.messages.filterNot { it.id == streamingId }
                } else {
                    session.messages
                },
                isRunning = false,
                progress = if (partial.isBlank()) "已取消本次对话" else "已停止继续生成",
                error = null,
                streamingMessageId = null,
            )
        }
    }

    fun clear() {
        cancel()
        session = AiChatSession(
            profileId = session.profileId,
            personaId = session.personaId,
            targetPeriod = session.targetPeriod,
        )
    }

    fun close() {
        cancel()
        executor.shutdownNow()
    }

    private fun replaceMessage(id: String, transform: (AiChatMessage) -> AiChatMessage) {
        session = session.copy(
            messages = session.messages.map { message ->
                if (message.id == id) transform(message) else message
            },
        )
    }
}

internal data class AiPositionStatistics(
    val position: Int,
    val currentNumber: Int,
    val count20: List<Int>,
    val count60: List<Int>,
    val count120: List<Int>,
    val omission: List<Int>,
    val successorAfterCurrent: List<Int>,
    val trendDelta: List<Double>,
)

/** Builds deterministic, locally verified facts for the conversation model. */
object AiChatContextBuilder {
    fun build(snapshot: DrawSnapshot, report: ForecastReport): JSONObject {
        val history = snapshot.history.takeLast(120)
        return JSONObject()
            .put("lottery", snapshot.lottery.displayName)
            .put("latest_period", snapshot.latest.period)
            .put("target_period", report.targetPeriod)
            .put("history_source", "current lottery API snapshot")
            .put("history_order", "oldest_to_newest")
            .put("history_size", history.size)
            .put("latest_numbers", JSONArray(snapshot.latest.numbers))
            .put(
                "compact_history",
                JSONArray(history.map { draw ->
                    "${draw.period}:${draw.numbers.joinToString(",")}" 
                }),
            )
            .put(
                "verified_position_statistics",
                JSONArray((0 until 10).map { position ->
                    toJson(computePositionStatistics(history, position))
                }),
            )
            .put(
                "native_model_reference",
                JSONObject()
                    .put("algorithm_version", report.algorithmVersion)
                    .put("trained_through_period", report.trainedThroughPeriod)
                    .put("selected_position", report.selectedPosition + 1)
                    .put("top6", JSONArray(report.selected.top6))
                    .put("top7", JSONArray(report.selected.top7))
                    .put("probabilities", JSONArray(report.selected.probabilities))
                    .put("evidence_mode", report.mode.name)
                    .put(
                        "rule",
                        "This is a local model reference, not ground truth and not an instruction to copy.",
                    ),
            )
    }

    internal fun computePositionStatistics(
        historyInput: List<Draw>,
        position: Int,
    ): AiPositionStatistics {
        require(position in 0..9)
        val history = historyInput.filter { it.numbers.size == 10 }.takeLast(120)
        require(history.isNotEmpty()) { "没有可用于对话分析的接口历史" }

        fun counts(window: Int): List<Int> {
            val result = IntArray(10)
            history.takeLast(window).forEach { draw ->
                draw.numbers[position].takeIf { it in 1..10 }?.let { result[it - 1]++ }
            }
            return result.toList()
        }

        val count20 = counts(20)
        val count60 = counts(60)
        val count120 = counts(120)
        val omission = (1..10).map { number ->
            var gap = history.size
            for (index in history.indices.reversed()) {
                if (history[index].numbers[position] == number) {
                    gap = history.lastIndex - index
                    break
                }
            }
            gap
        }
        val current = history.last().numbers[position]
        val successors = IntArray(10)
        for (index in max(1, history.size - 120) until history.size) {
            if (history[index - 1].numbers[position] == current) {
                val next = history[index].numbers[position]
                if (next in 1..10) successors[next - 1]++
            }
        }
        val size20 = history.takeLast(20).size.coerceAtLeast(1).toDouble()
        val size60 = history.takeLast(60).size.coerceAtLeast(1).toDouble()
        val trend = (0 until 10).map { number ->
            abs(count20[number] / size20 - count60[number] / size60)
        }
        return AiPositionStatistics(
            position = position,
            currentNumber = current,
            count20 = count20,
            count60 = count60,
            count120 = count120,
            omission = omission,
            successorAfterCurrent = successors.toList(),
            trendDelta = trend,
        )
    }

    private fun toJson(stats: AiPositionStatistics): JSONObject = JSONObject()
        .put("position", stats.position + 1)
        .put("current_number", stats.currentNumber)
        .put("count_20_by_number_1_to_10", JSONArray(stats.count20))
        .put("count_60_by_number_1_to_10", JSONArray(stats.count60))
        .put("count_120_by_number_1_to_10", JSONArray(stats.count120))
        .put("omission_by_number_1_to_10", JSONArray(stats.omission))
        .put("successor_after_current_by_number_1_to_10", JSONArray(stats.successorAfterCurrent))
        .put("trend_delta_20_vs_60_by_number_1_to_10", JSONArray(stats.trendDelta))
}

private class RemoteAiChatClient {
    @Volatile
    private var activeConnection: HttpURLConnection? = null

    fun cancel() {
        activeConnection?.disconnect()
        activeConnection = null
    }

    fun chat(
        config: AiConfig,
        snapshot: DrawSnapshot,
        report: ForecastReport,
        previousMessages: List<AiChatMessage>,
        question: String,
        persona: AiChatPersona,
        onProgress: (String) -> Unit,
        onStreamText: (String) -> Unit,
    ): AiChatReply {
        require(config.isComplete) { "AI 配置不完整" }
        val endpoint = URL(config.endpoint.trim())
        require(endpoint.protocol == "https") { "AI 接口必须使用 HTTPS" }
        val started = System.currentTimeMillis()
        val wantsPrediction = AiChatProtocol.wantsPrediction(question)
        val context = AiChatContextBuilder.build(snapshot, report)
        val decision = AiReasoningEngine.resolve(config)
        val responsesApi = endpoint.path.trimEnd('/').endsWith("/responses")
        val messages = conversationMessages(
            context = context,
            previousMessages = previousMessages,
            question = question,
            wantsPrediction = wantsPrediction,
            persona = persona,
        )
        val publisher = VisibleStreamPublisher(onStreamText)

        fun runRequest(activeDecision: AiReasoningDecision): JSONObject {
            val streamingRequest = requestBody(
                config = config,
                responsesApi = responsesApi,
                messages = messages,
                decision = activeDecision,
                stream = true,
            )
            return try {
                execute(
                    endpoint = endpoint,
                    config = config,
                    request = streamingRequest,
                    timeoutMs = timeoutFor(activeDecision),
                    onProgress = onProgress,
                    publisher = publisher,
                )
            } catch (_: AiChatStreamingRejectedException) {
                publisher.reset()
                onProgress("当前接口不支持流式返回，已切换兼容输出…")
                execute(
                    endpoint = endpoint,
                    config = config,
                    request = requestBody(
                        config = config,
                        responsesApi = responsesApi,
                        messages = messages,
                        decision = activeDecision,
                        stream = false,
                    ),
                    timeoutMs = timeoutFor(activeDecision),
                    onProgress = onProgress,
                    publisher = publisher,
                )
            }
        }

        onProgress("正在连接 ${config.displayName} · ${persona.displayName}…")
        val response = try {
            runRequest(decision)
        } catch (cause: AiChatProtocolRejectedException) {
            if (!decision.sendControl) throw cause
            publisher.reset()
            onProgress("接口拒绝显式思考参数，正在使用模型默认协议重发一次…")
            runRequest(
                decision.copy(sendControl = false, enableThinking = false, effort = null),
            )
        }
        val rawContent = extractContent(response)
        require(rawContent.isNotBlank()) { "模型没有返回可显示的回答" }
        val prediction = if (wantsPrediction) AiChatProtocol.parsePrediction(rawContent) else null
        val content = AiChatProtocol.visibleText(rawContent, prediction != null)
        publisher.finish(content)
        val usage = extractUsage(response)
        val reasoningVerified = extractReasoning(response).isNotBlank() ||
            (usage.reasoningTokens ?: 0) > 0
        onProgress("回答完成，正在整理候选卡片…")
        return AiChatReply(
            content = content,
            prediction = prediction,
            latencyMs = System.currentTimeMillis() - started,
            responseId = response.optString("id"),
            reasoningTokens = usage.reasoningTokens,
            reasoningVerified = reasoningVerified,
        )
    }

    private fun conversationMessages(
        context: JSONObject,
        previousMessages: List<AiChatMessage>,
        question: String,
        wantsPrediction: Boolean,
        persona: AiChatPersona,
    ): JSONArray = JSONArray().apply {
        put(
            JSONObject()
                .put("role", "system")
                .put("content", systemPrompt(wantsPrediction, persona)),
        )
        put(
            JSONObject()
                .put("role", "user")
                .put(
                    "content",
                    "以下是客户端刚刚根据当前开奖接口历史逐期计算的事实。所有回答只能以这些事实为依据：\n${context}",
                ),
        )
        AiChatProtocol.trimHistory(previousMessages).forEach { message ->
            put(
                JSONObject()
                    .put("role", if (message.role == AiChatRole.USER) "user" else "assistant")
                    .put("content", message.content),
            )
        }
        put(JSONObject().put("role", "user").put("content", question))
    }

    private fun systemPrompt(wantsPrediction: Boolean, persona: AiChatPersona): String = buildString {
        append(
            "你是天机内置的开奖记录分析助手，当前分析人设为【${persona.displayName}】。" +
                "人设要求：${persona.instruction}" +
                "使用简体中文直接、自然地回答，支持连续追问。" +
                "只能引用客户端提供的当前开奖接口历史、逐期统计和本机模型参考；不得虚构期号、次数或数据来源。" +
                "用户问某名次多少期、某号码出现多少次、遗漏多少期、当前号码之后常接哪些号时，必须从已核验字段计算并明确窗口。" +
                "用户说出现几率大时，应解释为历史样本中的相对频次或模型相对评分，不得称为真实中奖概率。" +
                "不要输出隐藏思维链，不得承诺必中、盈利或准确率。证据接近时明确说差异小。" +
                "回答采用适合聊天阅读的短段落，先回应问题，再给依据，不要堆砌无关术语。",
        )
        if (wantsPrediction) {
            append(
                "用户本次要求候选或预测。正文先给简洁依据，随后追加且只追加一个" +
                    "<tianji_forecast>{\"position\":1至10整数,\"scores\":[按号码1至10排列的10项非负评分]}</tianji_forecast>。" +
                    "scores必须来自本次上下文比较，避免无依据并列。",
            )
        }
    }

    private fun requestBody(
        config: AiConfig,
        responsesApi: Boolean,
        messages: JSONArray,
        decision: AiReasoningDecision,
        stream: Boolean,
    ): JSONObject = JSONObject().apply {
        put("model", config.model.trim())
        put("stream", stream)
        if (responsesApi) {
            put("store", false)
            put("input", messages)
        } else {
            put("messages", messages)
        }
        if (!decision.expectsReasoning && decision.protocol != AiReasoningProtocol.OPENAI) {
            put("temperature", 0.2)
        }
        applyReasoning(decision, responsesApi)
    }

    private fun JSONObject.applyReasoning(
        decision: AiReasoningDecision,
        responsesApi: Boolean,
    ) {
        if (!decision.sendControl) return
        when (decision.protocol) {
            AiReasoningProtocol.DEEPSEEK -> {
                put(
                    "thinking",
                    JSONObject().put("type", if (decision.enableThinking) "enabled" else "disabled"),
                )
                if (decision.enableThinking) put("reasoning_effort", decision.effort ?: "high")
            }
            AiReasoningProtocol.OPENAI -> if (decision.enableThinking) {
                if (responsesApi) {
                    put("reasoning", JSONObject().put("effort", decision.effort ?: "high"))
                } else {
                    put("reasoning_effort", decision.effort ?: "high")
                }
            }
            AiReasoningProtocol.OPENROUTER -> put(
                "reasoning",
                if (decision.enableThinking) {
                    JSONObject().put("effort", decision.effort ?: "high").put("exclude", true)
                } else {
                    JSONObject().put("enabled", false)
                },
            )
            AiReasoningProtocol.ENABLE_THINKING -> put("enable_thinking", decision.enableThinking)
            AiReasoningProtocol.AUTO, AiReasoningProtocol.NONE -> Unit
        }
    }

    private fun execute(
        endpoint: URL,
        config: AiConfig,
        request: JSONObject,
        timeoutMs: Int,
        onProgress: (String) -> Unit,
        publisher: VisibleStreamPublisher,
    ): JSONObject {
        var lastFailure: Throwable? = null
        repeat(2) { attempt ->
            var deliveredVisibleText = false
            val connection = endpoint.openConnection() as HttpURLConnection
            activeConnection = connection
            try {
                connection.requestMethod = "POST"
                connection.connectTimeout = 12_000
                connection.readTimeout = timeoutMs
                connection.doOutput = true
                connection.useCaches = false
                connection.setRequestProperty("Content-Type", "application/json")
                connection.setRequestProperty("Accept", "text/event-stream, application/json")
                connection.setRequestProperty("Authorization", "Bearer ${config.apiKey.trim()}")
                connection.outputStream.use { output ->
                    output.write(request.toString().toByteArray(Charsets.UTF_8))
                }
                onProgress(
                    if (request.optBoolean("stream", false)) {
                        "模型正在分析，回答开始后会实时显示…"
                    } else {
                        "模型正在分析，完成后将分段显示…"
                    },
                )
                val code = connection.responseCode
                if (code in 200..299) {
                    val reader = connection.inputStream.bufferedReader(Charsets.UTF_8)
                    return readSuccessResponse(
                        reader = reader,
                        contentType = connection.contentType.orEmpty(),
                        publisher = publisher,
                        isCancelled = { activeConnection !== connection },
                        onVisibleDelivered = { deliveredVisibleText = true },
                    )
                }
                val body = connection.errorStream
                    ?.bufferedReader(Charsets.UTF_8)?.use { it.readText() }.orEmpty()
                if (
                    code in listOf(400, 404, 422) &&
                    listOf("reasoning", "thinking", "enable_thinking", "reasoning_effort")
                        .any { body.contains(it, ignoreCase = true) }
                ) {
                    throw AiChatProtocolRejectedException("AI 接口拒绝当前思考参数：${body.take(140)}")
                }
                if (
                    request.optBoolean("stream", false) &&
                    code in listOf(400, 404, 405, 415, 422) &&
                    body.contains("stream", ignoreCase = true)
                ) {
                    throw AiChatStreamingRejectedException()
                }
                if (attempt == 0 && (code == 429 || code in 500..599)) {
                    onProgress(if (code == 429) "供应商限流，正在重连一次…" else "供应商暂时异常，正在重连一次…")
                    Thread.sleep(if (code == 429) 1_500L else 500L)
                    return@repeat
                }
                error("AI 接口 HTTP $code：${body.take(180)}")
            } catch (cause: SocketTimeoutException) {
                lastFailure = cause
                if (attempt == 0 && !deliveredVisibleText) {
                    onProgress("模型响应超时，正在进行一次网络重连…")
                    return@repeat
                }
                throw IllegalStateException(
                    if (deliveredVisibleText) "流式回答中断，已保留已生成内容" else "模型响应超时",
                    cause,
                )
            } finally {
                if (activeConnection === connection) activeConnection = null
                connection.disconnect()
            }
        }
        throw IllegalStateException("模型对话超过 ${timeoutMs / 1_000} 秒或重连后仍失败", lastFailure)
    }

    private fun readSuccessResponse(
        reader: BufferedReader,
        contentType: String,
        publisher: VisibleStreamPublisher,
        isCancelled: () -> Boolean,
        onVisibleDelivered: () -> Unit,
    ): JSONObject = reader.use {
        val prefix = mutableListOf<String>()
        var firstMeaningful: String? = null
        while (firstMeaningful == null) {
            val line = it.readLine() ?: break
            prefix += line
            if (line.isNotBlank()) firstMeaningful = line
        }
        val looksLikeSse = contentType.contains("text/event-stream", ignoreCase = true) ||
            firstMeaningful?.trimStart()?.let { line ->
                line.startsWith("data:") || line.startsWith("event:") || line.startsWith(":")
            } == true
        if (looksLikeSse) {
            readSse(it, prefix, publisher, isCancelled, onVisibleDelivered)
        } else {
            val body = buildString {
                prefix.forEachIndexed { index, line ->
                    if (index > 0) append('\n')
                    append(line)
                }
                val remainder = it.readText()
                if (remainder.isNotEmpty()) {
                    if (isNotEmpty()) append('\n')
                    append(remainder)
                }
            }
            val root = JSONObject(body)
            val content = extractContent(root)
            emitBufferedFallback(content, publisher, isCancelled, onVisibleDelivered)
            root
        }
    }

    private fun readSse(
        reader: BufferedReader,
        initialLines: List<String>,
        publisher: VisibleStreamPublisher,
        isCancelled: () -> Boolean,
        onVisibleDelivered: () -> Unit,
    ): JSONObject {
        val rawContent = StringBuilder()
        val reasoning = StringBuilder()
        var responseId = ""
        var usage: JSONObject? = null
        var eventName = ""
        val eventData = mutableListOf<String>()

        fun appendVisible(delta: String) {
            if (delta.isEmpty()) return
            rawContent.append(delta)
            if (publisher.append(delta)) onVisibleDelivered()
        }

        fun consumeEvent() {
            if (eventData.isEmpty()) {
                eventName = ""
                return
            }
            val data = eventData.joinToString("\n").trim()
            eventData.clear()
            if (data.isBlank() || data == "[DONE]") {
                eventName = ""
                return
            }
            val root = runCatching { JSONObject(data) }.getOrNull()
                ?: run {
                    eventName = ""
                    return
                }
            root.optJSONObject("error")?.let { error ->
                throw IllegalStateException(
                    error.optString("message").ifBlank { "模型流式接口返回错误" },
                )
            }
            responseId = root.optString("id").ifBlank { responseId }
            root.optJSONObject("usage")?.let { usage = it }

            val type = root.optString("type").ifBlank { eventName }
            when {
                type == "response.output_text.delta" -> appendVisible(root.optString("delta"))
                type == "response.output_text.done" && rawContent.isEmpty() -> {
                    appendVisible(root.optString("text"))
                }
                type.contains("reasoning", ignoreCase = true) && type.endsWith(".delta") -> {
                    reasoning.append(root.optString("delta"))
                }
                type == "response.completed" -> {
                    root.optJSONObject("response")?.let { completed ->
                        responseId = completed.optString("id").ifBlank { responseId }
                        completed.optJSONObject("usage")?.let { usage = it }
                        if (rawContent.isEmpty()) appendVisible(extractContent(completed))
                        reasoning.append(extractReasoning(completed))
                    }
                }
            }

            val choice = root.optJSONArray("choices")?.optJSONObject(0)
            val delta = choice?.optJSONObject("delta")
            extractTextNode(delta?.opt("content"))
                .takeIf(String::isNotEmpty)
                ?.let(::appendVisible)
            extractTextNode(delta?.opt("reasoning_content"))
                .takeIf(String::isNotEmpty)
                ?.let(reasoning::append)
            if (rawContent.isEmpty()) {
                val message = choice?.optJSONObject("message")
                extractTextNode(message?.opt("content"))
                    .takeIf(String::isNotEmpty)
                    ?.let(::appendVisible)
                extractTextNode(message?.opt("reasoning_content"))
                    .takeIf(String::isNotEmpty)
                    ?.let(reasoning::append)
            }
            eventName = ""
        }

        fun processLine(line: String) {
            if (isCancelled()) throw IllegalStateException("已取消本次对话")
            when {
                line.isBlank() -> consumeEvent()
                line.startsWith("event:") -> eventName = line.substringAfter(':').trim()
                line.startsWith("data:") -> eventData += line.substringAfter(':').trimStart()
                line.startsWith(":") -> Unit
            }
        }

        initialLines.forEach(::processLine)
        while (true) {
            val line = reader.readLine() ?: break
            processLine(line)
        }
        consumeEvent()
        publisher.flush()
        require(rawContent.isNotBlank()) { "模型没有返回可显示的流式回答" }
        return JSONObject()
            .put("id", responseId)
            .put("output_text", rawContent.toString())
            .put("_tianji_reasoning", reasoning.toString())
            .put("usage", usage ?: JSONObject())
    }

    private fun emitBufferedFallback(
        content: String,
        publisher: VisibleStreamPublisher,
        isCancelled: () -> Boolean,
        onVisibleDelivered: () -> Unit,
    ) {
        if (content.isBlank()) return
        content.chunked(8).forEach { chunk ->
            if (isCancelled() || Thread.currentThread().isInterrupted) {
                throw IllegalStateException("已取消本次对话")
            }
            if (publisher.append(chunk)) onVisibleDelivered()
            Thread.sleep(12L)
        }
        publisher.flush()
    }

    private fun timeoutFor(decision: AiReasoningDecision): Int = when {
        decision.preference == AiReasoningMode.HIGH -> 180_000
        decision.expectsReasoning -> 120_000
        else -> 75_000
    }

    private fun extractContent(root: JSONObject): String {
        root.optString("output_text").trim().takeIf(String::isNotBlank)?.let { return it }
        val chatContent = root.optJSONArray("choices")
            ?.optJSONObject(0)
            ?.optJSONObject("message")
            ?.opt("content")
        extractTextNode(chatContent).trim().takeIf(String::isNotBlank)?.let { return it }
        val output = root.optJSONArray("output") ?: return ""
        return (0 until output.length()).flatMap { index ->
            val content = output.optJSONObject(index)?.optJSONArray("content") ?: return@flatMap emptyList()
            (0 until content.length()).mapNotNull { contentIndex ->
                val item = content.optJSONObject(contentIndex) ?: return@mapNotNull null
                item.optString("text").ifBlank { item.optString("content") }
                    .takeIf(String::isNotBlank)
            }
        }.joinToString("\n")
    }

    private fun extractTextNode(value: Any?): String = when (value) {
        null, JSONObject.NULL -> ""
        is String -> value
        is JSONObject -> value.optString("text").ifBlank {
            value.optString("content").ifBlank { value.optString("value") }
        }
        is JSONArray -> (0 until value.length()).mapNotNull { index ->
            extractTextNode(value.opt(index)).takeIf(String::isNotBlank)
        }.joinToString("")
        else -> ""
    }

    private fun extractReasoning(root: JSONObject): String = root
        .optString("_tianji_reasoning")
        .ifBlank {
            root.optJSONArray("choices")
                ?.optJSONObject(0)
                ?.optJSONObject("message")
                ?.optString("reasoning_content")
                .orEmpty()
        }

    private fun extractUsage(root: JSONObject): AiTokenUsage {
        val usage = root.optJSONObject("usage") ?: return AiTokenUsage()
        val reasoning = usage.optJSONObject("completion_tokens_details")
            ?.optInt("reasoning_tokens", -1)?.takeIf { it >= 0 }
            ?: usage.optJSONObject("output_tokens_details")
                ?.optInt("reasoning_tokens", -1)?.takeIf { it >= 0 }
        fun firstPositive(vararg keys: String): Int? = keys.firstNotNullOfOrNull { key ->
            usage.optInt(key, -1).takeIf { it >= 0 }
        }
        return AiTokenUsage(
            inputTokens = firstPositive("prompt_tokens", "input_tokens"),
            outputTokens = firstPositive("completion_tokens", "output_tokens"),
            reasoningTokens = reasoning,
        )
    }

    private class VisibleStreamPublisher(
        private val onText: (String) -> Unit,
    ) {
        private val raw = StringBuilder()
        private var lastVisible = ""
        private var lastEmitAt = 0L

        fun append(delta: String): Boolean {
            if (delta.isEmpty()) return false
            raw.append(delta)
            val visible = AiChatProtocol.visibleStreamingText(raw.toString())
            if (visible == lastVisible) return false
            val now = System.currentTimeMillis()
            val urgent = delta.any { it == '\n' || it in "。！？；：" } ||
                visible.length - lastVisible.length >= 12
            if (urgent || now - lastEmitAt >= 35L) {
                lastVisible = visible
                lastEmitAt = now
                onText(visible)
                return visible.isNotBlank()
            }
            return false
        }

        fun flush() {
            val visible = AiChatProtocol.visibleStreamingText(raw.toString())
            if (visible != lastVisible) {
                lastVisible = visible
                lastEmitAt = System.currentTimeMillis()
                onText(visible)
            }
        }

        fun finish(finalText: String) {
            lastVisible = finalText
            onText(finalText)
        }

        fun reset() {
            raw.clear()
            lastVisible = ""
            lastEmitAt = 0L
            onText("")
        }
    }

    private class AiChatProtocolRejectedException(message: String) : IllegalStateException(message)
    private class AiChatStreamingRejectedException : IllegalStateException()
}
