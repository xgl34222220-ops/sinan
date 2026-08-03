#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
analysis = ROOT / "app/src/main/java/com/tianji/probabilitylab/nativev4/ai/AiAnalysis.kt"
controller = ROOT / "app/src/main/java/com/tianji/probabilitylab/nativev4/AppController.kt"
screens = ROOT / "app/src/main/java/com/tianji/probabilitylab/nativev4/ui/Screens.kt"
readme = ROOT / "README.md"


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected 1 match, got {count}: {old[:150]!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


# ---------------------------------------------------------------------------
# AiAnalysis: preserve a visible conversation timeline and stop opaque reruns.
# ---------------------------------------------------------------------------
replace_once(
    analysis,
    '''data class AiRunStatus(
    val profileId: String,
    val state: AiConnectionState = AiConnectionState.UNTESTED,
    val message: String = "尚未测试",
    val latencyMs: Long? = null,
    val checkedAtEpochMs: Long? = null,
)
''',
    '''data class AiRunStatus(
    val profileId: String,
    val state: AiConnectionState = AiConnectionState.UNTESTED,
    val message: String = "尚未测试",
    val latencyMs: Long? = null,
    val checkedAtEpochMs: Long? = null,
    val timeline: List<AiConversationEvent> = emptyList(),
)
''',
)

replace_once(
    analysis,
    '''        val userPrompt = analysisPayload(snapshot, report, historyLimit).toString()
        val retryPrompt = JSONObject(userPrompt).apply {
            put(
                "retry_rule",
                "上一轮没有生成完整JSON。本轮继续真实思考，但禁止重新逐期复述；直接利用已核验统计完成比较并尽快输出position与10项scores。",
            )
        }.toString()
        val started = System.currentTimeMillis()
''',
    '''        val userPrompt = analysisPayload(snapshot, report, historyLimit).toString()
        val started = System.currentTimeMillis()
''',
)

replace_once(
    analysis,
    '''            return parseForecastContent(
                content = content,
''',
    '''            onProgress(
                "预测核心已完整，正在本机校验概率矩阵并生成六码/七码",
                System.currentTimeMillis() - started,
            )
            return parseForecastContent(
                content = content,
''',
)

old_retry = '''        val firstFailure = primary.exceptionOrNull() ?: error("AI 分析失败")
        val reasoningControlFailure = isReasoningControlFailure(firstFailure, primaryDecision)
        if (!isRetriableModelOutput(firstFailure) && !reasoningControlFailure) throw firstFailure
        onProgress(
            "首次请求在推理前或输出开始前失败，正在重新请求",
            System.currentTimeMillis() - started,
        )

        return runCatching {
            val reasoningFallback = primaryDecision.expectsReasoning || reasoningControlFailure
            val retryDecision = if (reasoningFallback) {
                AiReasoningEngine.fallback(config)
            } else primaryDecision
            execute(
                reasoningDecision = retryDecision,
                readTimeoutMs = when {
                    retryDecision.expectsReasoning && retryDecision.protocol == AiReasoningProtocol.DEEPSEEK -> 300_000
                    retryDecision.expectsReasoning -> 180_000
                    else -> 60_000
                },
                executionNote = if (reasoningFallback) {
                    "${config.analysisMode.label} · 保留真实思考重试"
                } else {
                    "${config.analysisMode.label} · 保留思考并重试输出格式"
                },
                fallback = reasoningFallback,
                prompt = retryPrompt,
            )
        }.getOrElse { retryFailure ->
            error(
                "模型保留思考重试后仍未返回完整预测数据：${firstFailure.message.orEmpty().take(80)}；" +
                    "重试：${retryFailure.message.orEmpty().take(80)}",
            )
        }
'''
new_retry = '''        val firstFailure = primary.exceptionOrNull() ?: error("AI 分析失败")
        val reasoningControlFailure = isReasoningControlFailure(firstFailure, primaryDecision)
        if (!reasoningControlFailure) {
            // Partial output is already continued inside execute(). Transport timeouts, broken
            // streams and invalid model output must remain visible instead of silently starting a
            // second full 60/120-period analysis.
            throw firstFailure
        }
        onProgress(
            "接口拒绝显式思考参数；确认尚未进入模型推理，正在仅一次切换为模型默认思考协议",
            System.currentTimeMillis() - started,
        )
        val defaultThinkingDecision = primaryDecision.copy(
            sendControl = false,
            enableThinking = true,
            effort = null,
            displayLabel = "${primaryDecision.protocol.label} · 模型默认思考",
        )
        return runCatching {
            execute(
                reasoningDecision = defaultThinkingDecision,
                readTimeoutMs = if (primaryDecision.protocol == AiReasoningProtocol.DEEPSEEK) {
                    240_000
                } else {
                    120_000
                },
                executionNote = "${config.analysisMode.label} · 显式参数被拒绝后使用模型默认思考",
                fallback = true,
                prompt = userPrompt,
            )
        }.getOrElse { retryFailure ->
            error(
                "接口拒绝显式思考参数，切换模型默认思考后仍失败：" +
                    retryFailure.message.orEmpty().take(140),
            )
        }
'''
replace_once(analysis, old_retry, new_retry)

replace_once(
    analysis,
    '''        val started = System.currentTimeMillis()
        for (attempt in 0..1) {
            val connection = endpoint.openConnection() as HttpURLConnection
''',
    '''        val started = System.currentTimeMillis()
        for (attempt in 0..1) {
            onProgress(
                if (attempt == 0) "正在建立 HTTPS 连接" else "正在进行网络层重连 1/1",
                System.currentTimeMillis() - started,
            )
            val connection = endpoint.openConnection() as HttpURLConnection
''',
)

replace_once(
    analysis,
    '''                connection.setRequestProperty("Authorization", "Bearer ${config.apiKey.trim()}")
                connection.outputStream.use { it.write(request.toString().toByteArray(Charsets.UTF_8)) }
                val code = connection.responseCode
''',
    '''                connection.setRequestProperty("Authorization", "Bearer ${config.apiKey.trim()}")
                connection.outputStream.use { it.write(request.toString().toByteArray(Charsets.UTF_8)) }
                onProgress("请求已发送，等待服务器接受", System.currentTimeMillis() - started)
                val code = connection.responseCode
''',
)

replace_once(
    analysis,
    '''                    return RemoteResponse(
                        json = json,
''',
    '''                    onProgress("模型响应已结束，正在本机校验 JSON", System.currentTimeMillis() - started)
                    return RemoteResponse(
                        json = json,
''',
)

replace_once(
    analysis,
    '''                } else if (attempt == 0 && code == 429) {
                    val retrySeconds = connection.getHeaderField("Retry-After")?.trim()?.toLongOrNull()
                        ?.coerceIn(1L, 10L) ?: 2L
                    retryDelayMs = retrySeconds * 1_000L
                } else if (attempt == 0 && code in 500..599) {
                    retryDelayMs = 500L
''',
    '''                } else if (attempt == 0 && code == 429) {
                    val retrySeconds = connection.getHeaderField("Retry-After")?.trim()?.toLongOrNull()
                        ?.coerceIn(1L, 10L) ?: 2L
                    retryDelayMs = retrySeconds * 1_000L
                    onProgress(
                        "供应商限流，${retrySeconds}秒后进行一次网络层重连",
                        System.currentTimeMillis() - started,
                    )
                } else if (attempt == 0 && code in 500..599) {
                    retryDelayMs = 500L
                    onProgress(
                        "供应商 HTTP $code，正在进行一次网络层重连",
                        System.currentTimeMillis() - started,
                    )
''',
)

replace_once(
    analysis,
    '''            } catch (_: SocketTimeoutException) {
                error("模型响应超过 ${readTimeoutMs / 1_000} 秒；请改用省时推理或 Flash 模型")
''',
    '''            } catch (_: SocketTimeoutException) {
                onProgress(
                    "等待模型输出超时，本次请求已停止，不会自动重新预测",
                    System.currentTimeMillis() - started,
                )
                error("模型响应超过 ${readTimeoutMs / 1_000} 秒；本次已停止，未自动重新预测")
''',
)

# ---------------------------------------------------------------------------
# Controller: retain the complete timeline instead of overwriting one message.
# ---------------------------------------------------------------------------
replace_once(
    controller,
    '''import com.tianji.probabilitylab.nativev4.ai.AiConfig
import com.tianji.probabilitylab.nativev4.ai.AiConnectionState
''',
    '''import com.tianji.probabilitylab.nativev4.ai.AiConfig
import com.tianji.probabilitylab.nativev4.ai.AiConnectionStage
'''.replace("AiConnectionStage", "AiConnectionState") +
    '''import com.tianji.probabilitylab.nativev4.ai.AiConversationStage
import com.tianji.probabilitylab.nativev4.ai.AiConversationTimeline
''',
)

replace_once(
    controller,
    '''                    status.copy(state = AiConnectionState.UNTESTED, message = "数据刷新，任务已取消")
''',
    '''                    status.copy(
                        state = AiConnectionState.UNTESTED,
                        message = "数据刷新，任务已取消",
                        timeline = AiConversationTimeline.merge(
                            status.timeline,
                            AiConversationTimeline.event(
                                AiConversationStage.CANCELLED,
                                "数据刷新，当前分析已取消",
                            ),
                        ),
                    )
''',
)

old_cancel = '''    fun cancelAi(profileId: String) {
        aiTasks.cancel(profileId)
        remoteAiAnalyzer.cancelActiveRequests(profileId)
        state = state.copy(
            aiStatuses = state.aiStatuses + (
                profileId to AiRunStatus(
                    profileId,
                    AiConnectionState.CANCELLED,
                    "已取消本次请求",
                    checkedAtEpochMs = System.currentTimeMillis(),
                )
            ),
        )
    }
'''
new_cancel = '''    fun cancelAi(profileId: String) {
        aiTasks.cancel(profileId)
        remoteAiAnalyzer.cancelActiveRequests(profileId)
        val current = state.aiStatuses[profileId] ?: AiRunStatus(profileId)
        state = state.copy(
            aiStatuses = state.aiStatuses + (
                profileId to current.copy(
                    state = AiConnectionState.CANCELLED,
                    message = "已取消本次请求",
                    checkedAtEpochMs = System.currentTimeMillis(),
                    timeline = AiConversationTimeline.merge(
                        current.timeline,
                        AiConversationTimeline.event(
                            AiConversationStage.CANCELLED,
                            "用户取消了当前请求",
                        ),
                    ),
                )
            ),
        )
    }
'''
replace_once(controller, old_cancel, new_cancel)

replace_once(
    controller,
    '''            config.id to AiRunStatus(
                profileId = config.id,
                state = AiConnectionState.ANALYZING,
                message = "正在从开奖接口强制同步最新历史…",
            )
''',
    '''            val message = "正在从开奖接口强制同步最新历史…"
            config.id to AiRunStatus(
                profileId = config.id,
                state = AiConnectionState.ANALYZING,
                message = message,
                timeline = listOf(
                    AiConversationTimeline.event(AiConversationStage.PREPARING, message),
                ),
            )
''',
)

replace_once(
    controller,
    '''                            val reasoning = AiReasoningEngine.resolve(config).displayLabel
                            val message = "接口历史已同步，正在${config.analysisMode.label} · $reasoning…"
                            config.id to AiRunStatus(config.id, AiConnectionState.ANALYZING, message)
''',
    '''                            val reasoning = AiReasoningEngine.resolve(config).displayLabel
                            val message = "接口历史已同步，准备${config.analysisMode.label} · $reasoning"
                            val current = state.aiStatuses[config.id] ?: AiRunStatus(config.id)
                            config.id to current.copy(
                                state = AiConnectionState.ANALYZING,
                                message = message,
                                timeline = AiConversationTimeline.merge(
                                    current.timeline,
                                    AiConversationTimeline.event(AiConversationStage.REQUEST, message),
                                ),
                            )
''',
)

old_progress = '''                                state = state.copy(
                                    aiStatuses = state.aiStatuses + (
                                        config.id to AiRunStatus(
                                            profileId = config.id,
                                            state = AiConnectionState.ANALYZING,
                                            message = "$message · ${elapsedMs / 1_000}s",
                                            checkedAtEpochMs = System.currentTimeMillis(),
                                        )
                                    ),
                                )
'''
new_progress = '''                                val current = state.aiStatuses[config.id] ?: AiRunStatus(config.id)
                                val event = AiConversationTimeline.event(
                                    stage = AiConversationTimeline.classify(message),
                                    message = message,
                                    elapsedMs = elapsedMs,
                                )
                                state = state.copy(
                                    aiStatuses = state.aiStatuses + (
                                        config.id to current.copy(
                                            state = AiConnectionState.ANALYZING,
                                            message = "$message · ${elapsedMs / 1_000}s",
                                            checkedAtEpochMs = System.currentTimeMillis(),
                                            timeline = AiConversationTimeline.merge(current.timeline, event),
                                        )
                                    ),
                                )
'''
replace_once(controller, old_progress, new_progress)

old_success = '''                                    config.id to AiRunStatus(
                                        profileId = config.id,
                                        state = AiConnectionState.CONNECTED,
                                        message = when {
                                            !completed.inserted -> "本期已有冻结预测，保留首次结果"
                                            forecast.reasoningState == AiReasoningState.FALLBACK ->
                                                "${forecast.executionNote} · 已冻结降级结果"
                                            forecast.reasoningState == AiReasoningState.VERIFIED ->
                                                forecast.reasoningTokens?.let { "已冻结 · 推理 $it tokens" }
                                                    ?: "已冻结 · 推理状态已验证"
                                            forecast.responseId.isBlank() -> "已接入并冻结预测"
                                            else -> "已冻结 · 响应 ${forecast.responseId.takeLast(10)}"
                                        },
                                        latencyMs = forecast.latencyMs,
                                        checkedAtEpochMs = forecast.createdAtEpochMs,
                                    )
'''
new_success = '''                                    config.id to run {
                                        val current = state.aiStatuses[config.id] ?: AiRunStatus(config.id)
                                        val successMessage = when {
                                            !completed.inserted -> "本期已有冻结预测，保留首次结果"
                                            forecast.reasoningState == AiReasoningState.FALLBACK ->
                                                "${forecast.executionNote} · 已冻结协议兼容结果"
                                            forecast.reasoningState == AiReasoningState.VERIFIED ->
                                                forecast.reasoningTokens?.let { "已冻结 · 推理 $it tokens" }
                                                    ?: "已冻结 · 推理状态已验证"
                                            forecast.responseId.isBlank() -> "已接入并冻结预测"
                                            else -> "已冻结 · 响应 ${forecast.responseId.takeLast(10)}"
                                        }
                                        current.copy(
                                            state = AiConnectionState.CONNECTED,
                                            message = successMessage,
                                            latencyMs = forecast.latencyMs,
                                            checkedAtEpochMs = forecast.createdAtEpochMs,
                                            timeline = AiConversationTimeline.merge(
                                                current.timeline,
                                                AiConversationTimeline.event(
                                                    AiConversationStage.SUCCESS,
                                                    successMessage,
                                                    forecast.latencyMs,
                                                ),
                                            ),
                                        )
                                    }
'''
replace_once(controller, old_success, new_success)

old_failure = '''                                    config.id to AiRunStatus(
                                        profileId = config.id,
                                        state = AiConnectionState.FAILED,
                                        message = it.message ?: "AI 分析失败",
                                        checkedAtEpochMs = System.currentTimeMillis(),
                                    )
'''
new_failure = '''                                    config.id to run {
                                        val current = state.aiStatuses[config.id] ?: AiRunStatus(config.id)
                                        val failureMessage = it.message ?: "AI 分析失败"
                                        current.copy(
                                            state = AiConnectionState.FAILED,
                                            message = failureMessage,
                                            checkedAtEpochMs = System.currentTimeMillis(),
                                            timeline = AiConversationTimeline.merge(
                                                current.timeline,
                                                AiConversationTimeline.event(
                                                    AiConversationStage.ERROR,
                                                    failureMessage,
                                                ),
                                            ),
                                        )
                                    }
'''
replace_once(controller, old_failure, new_failure)

replace_once(
    controller,
    '''            config.id to AiRunStatus(
                profileId = config.id,
                state = AiConnectionState.FAILED,
                message = message,
                checkedAtEpochMs = System.currentTimeMillis(),
            )
''',
    '''            val current = state.aiStatuses[config.id] ?: AiRunStatus(config.id)
            config.id to current.copy(
                state = AiConnectionState.FAILED,
                message = message,
                checkedAtEpochMs = System.currentTimeMillis(),
                timeline = AiConversationTimeline.merge(
                    current.timeline,
                    AiConversationTimeline.event(AiConversationStage.ERROR, message),
                ),
            )
''',
)

# ---------------------------------------------------------------------------
# Compose UI: expandable chat-like analysis conversation.
# ---------------------------------------------------------------------------
replace_once(
    screens,
    '''import com.tianji.probabilitylab.nativev4.ai.AiConnectionState
import com.tianji.probabilitylab.nativev4.ai.AiConsensusEngine
''',
    '''import com.tianji.probabilitylab.nativev4.ai.AiConnectionState
import com.tianji.probabilitylab.nativev4.ai.AiConversationStage
import com.tianji.probabilitylab.nativev4.ai.AiConsensusEngine
''',
)
replace_once(
    screens,
    '''import com.tianji.probabilitylab.nativev4.ai.AiReasoningState
import com.tianji.probabilitylab.nativev4.model.Draw
''',
    '''import com.tianji.probabilitylab.nativev4.ai.AiReasoningState
import com.tianji.probabilitylab.nativev4.ai.AiRunStatus
import com.tianji.probabilitylab.nativev4.model.Draw
''',
)

new_status_function = r'''@Composable
private fun AiStatusRow(
    config: AiConfig,
    state: AppUiState,
    onCancelAi: (String) -> Unit,
) {
    val colors = LocalTianjiColors.current
    val status = state.aiStatuses[config.id]
    val currentState = status?.state ?: AiConnectionState.UNTESTED
    var expanded by remember(config.id) { mutableStateOf(false) }
    val showTimeline = expanded ||
        currentState == AiConnectionState.ANALYZING ||
        currentState == AiConnectionState.FAILED
    val tint = when (currentState) {
        AiConnectionState.CONNECTED -> colors.green
        AiConnectionState.FAILED -> colors.red
        AiConnectionState.CANCELLED -> colors.amber
        AiConnectionState.TESTING, AiConnectionState.ANALYZING -> colors.accent
        AiConnectionState.UNTESTED -> colors.amber
    }
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(16.dp))
            .background(tint.copy(alpha = 0.065f))
            .border(1.dp, tint.copy(alpha = 0.2f), RoundedCornerShape(16.dp))
            .padding(horizontal = 11.dp, vertical = 10.dp),
    ) {
        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
            if (currentState == AiConnectionState.TESTING || currentState == AiConnectionState.ANALYZING) {
                CircularProgressIndicator(Modifier.size(14.dp), color = tint, strokeWidth = 1.8.dp)
            } else {
                Icon(
                    if (currentState == AiConnectionState.CONNECTED) {
                        Icons.Rounded.CheckCircle
                    } else {
                        Icons.Rounded.Info
                    },
                    null,
                    tint = tint,
                    modifier = Modifier.size(14.dp),
                )
            }
            Spacer(Modifier.width(7.dp))
            Column(Modifier.weight(1f)) {
                Text(
                    config.displayName,
                    color = colors.textSoft,
                    fontSize = 8.5.sp,
                    fontWeight = FontWeight.Bold,
                )
                Text(
                    "${config.analysisMode.label} · ${AiReasoningEngine.resolve(config).displayLabel}",
                    color = colors.textDim,
                    fontSize = 6.5.sp,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
                Text(
                    status?.message ?: "配置已保存，尚未测试",
                    color = tint,
                    fontSize = 7.sp,
                    maxLines = 2,
                    lineHeight = 11.sp,
                    overflow = TextOverflow.Ellipsis,
                )
            }
            if (currentState == AiConnectionState.ANALYZING || currentState == AiConnectionState.TESTING) {
                MiniActionButton("取消", Modifier.width(48.dp), tint = colors.amber) {
                    onCancelAi(config.id)
                }
            } else {
                status?.latencyMs?.let { Text("${it}ms", color = tint, fontSize = 8.sp) }
            }
        }
        if (!status?.timeline.isNullOrEmpty()) {
            Spacer(Modifier.height(9.dp))
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(10.dp))
                    .clickable { expanded = !expanded }
                    .padding(horizontal = 8.dp, vertical = 6.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(
                    "分析对话",
                    color = colors.textSoft,
                    fontSize = 7.5.sp,
                    fontWeight = FontWeight.Bold,
                    modifier = Modifier.weight(1f),
                )
                Text(
                    if (showTimeline) "收起" else "查看 ${status?.timeline?.size ?: 0} 条",
                    color = colors.accent,
                    fontSize = 7.sp,
                    fontWeight = FontWeight.Bold,
                )
            }
            if (showTimeline && status != null) {
                Spacer(Modifier.height(5.dp))
                AiConversationWindow(status)
            }
        }
    }
}

@Composable
private fun AiConversationWindow(status: AiRunStatus) {
    val colors = LocalTianjiColors.current
    val visible = status.timeline.takeLast(10)
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(14.dp))
            .background(Color.Black.copy(alpha = 0.16f))
            .border(1.dp, colors.line, RoundedCornerShape(14.dp))
            .padding(9.dp),
        verticalArrangement = Arrangement.spacedBy(7.dp),
    ) {
        visible.forEach { event ->
            val isModel = event.stage == AiConversationStage.REASONING ||
                event.stage == AiConversationStage.OUTPUT
            val (label, tint) = when (event.stage) {
                AiConversationStage.PREPARING -> "准备" to colors.textDim
                AiConversationStage.REQUEST -> "天机" to colors.accent
                AiConversationStage.CONNECTED -> "连接" to colors.accent
                AiConversationStage.REASONING -> "模型推理" to colors.accent
                AiConversationStage.OUTPUT -> "模型结果" to colors.green
                AiConversationStage.VALIDATING -> "本机校验" to colors.amber
                AiConversationStage.CONTINUATION -> "继续对话" to colors.amber
                AiConversationStage.RETRY -> "协议重发" to colors.amber
                AiConversationStage.SUCCESS -> "完成" to colors.green
                AiConversationStage.ERROR -> "错误" to colors.red
                AiConversationStage.CANCELLED -> "取消" to colors.amber
            }
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(
                        start = if (isModel) 22.dp else 0.dp,
                        end = if (isModel) 0.dp else 22.dp,
                    )
                    .clip(RoundedCornerShape(12.dp))
                    .background(tint.copy(alpha = 0.085f))
                    .border(1.dp, tint.copy(alpha = 0.18f), RoundedCornerShape(12.dp))
                    .padding(horizontal = 9.dp, vertical = 8.dp),
            ) {
                Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                    Text(label, color = tint, fontSize = 6.8.sp, fontWeight = FontWeight.Bold)
                    Spacer(Modifier.weight(1f))
                    Text(
                        "+${event.elapsedMs / 1_000}s",
                        color = colors.textDim,
                        fontSize = 6.5.sp,
                    )
                }
                Spacer(Modifier.height(3.dp))
                Text(
                    event.message,
                    color = colors.textSoft,
                    fontSize = 7.4.sp,
                    lineHeight = 11.5.sp,
                )
            }
        }
        if (status.timeline.size > visible.size) {
            Text(
                "较早的 ${status.timeline.size - visible.size} 条过程已折叠",
                color = colors.textDim,
                fontSize = 6.5.sp,
                modifier = Modifier.padding(horizontal = 4.dp),
            )
        }
    }
}

'''
text = screens.read_text(encoding="utf-8")
pattern = re.compile(
    r'@Composable\nprivate fun AiStatusRow\(.*?\n\}\n\n@Composable\nprivate fun AiConsensusCard',
    re.S,
)
match = pattern.search(text)
if not match:
    raise RuntimeError("Screens.kt: AiStatusRow block not found")
text = text[:match.start()] + new_status_function + '@Composable\nprivate fun AiConsensusCard' + text[match.end():]
screens.write_text(text, encoding="utf-8")

replace_once(
    readme,
    '''- 记录首个推理、推理阶段和结果阶段耗时，便于区分模型排队、真实推理和结果生成的慢点。
- 不降低模型 Token 上限、不关闭 thinking、不缩短60/120期历史。
''',
    '''- 记录首个推理、推理阶段和结果阶段耗时，便于区分模型排队、真实推理和结果生成的慢点。
- 新增可展开的“分析对话”窗口，逐步显示同步、连接、推理、结果生成、校验、同一对话补全和失败原因。
- 普通超时、断流和解析错误不再悄悄启动第二轮完整预测；只有接口明确拒绝思考参数且尚未进入推理时，才允许一次透明的模型默认思考协议重发。
- 不降低模型 Token 上限、不关闭 thinking、不缩短60/120期历史。
''',
)

print("v5.5.5 conversation-window patch applied")
