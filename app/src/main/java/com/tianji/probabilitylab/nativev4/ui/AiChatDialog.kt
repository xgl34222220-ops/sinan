package com.tianji.probabilitylab.nativev4.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.systemBars
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.AutoAwesome
import androidx.compose.material.icons.rounded.ChatBubble
import androidx.compose.material.icons.rounded.Close
import androidx.compose.material.icons.rounded.DeleteSweep
import androidx.compose.material.icons.rounded.History
import androidx.compose.material.icons.rounded.Refresh
import androidx.compose.material.icons.automirrored.rounded.Send
import androidx.compose.material.icons.rounded.StopCircle
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.Icon
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.IconButton
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import com.tianji.probabilitylab.nativev4.ai.AiChatArchiveId
import com.tianji.probabilitylab.nativev4.ai.AiChatArchiveSummary
import com.tianji.probabilitylab.nativev4.ai.AiChatController
import com.tianji.probabilitylab.nativev4.ai.AiChatMessage
import com.tianji.probabilitylab.nativev4.ai.AiChatPersona
import com.tianji.probabilitylab.nativev4.ai.AiChatPrediction
import com.tianji.probabilitylab.nativev4.ai.AiChatRole
import com.tianji.probabilitylab.nativev4.ai.AiChatSession
import com.tianji.probabilitylab.nativev4.ai.AiConfig
import com.tianji.probabilitylab.nativev4.model.DrawSnapshot
import com.tianji.probabilitylab.nativev4.model.ForecastReport
import com.tianji.probabilitylab.nativev4.ui.theme.LocalTianjiColors

@Composable
fun AiChatFloatingButton(
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val colors = LocalTianjiColors.current
    FloatingActionButton(
        onClick = onClick,
        modifier = modifier.size(52.dp),
        shape = CircleShape,
        containerColor = colors.accent,
        contentColor = Color.White,
    ) {
        Icon(Icons.Rounded.ChatBubble, contentDescription = "打开分析对话")
    }
}

@Composable
fun AiChatDialog(
    controller: AiChatController,
    configs: List<AiConfig>,
    modelCatalogs: Map<String, List<String>>,
    snapshot: DrawSnapshot?,
    report: ForecastReport?,
    onRefresh: () -> Unit,
    onDismiss: () -> Unit,
) {
    val colors = LocalTianjiColors.current
    val completeConfigs = remember(configs) { configs.filter(AiConfig::isComplete) }
    val session = controller.session
    val selectedPersona = AiChatPersona.fromId(session.personaId)
    val preferredConfig = completeConfigs.firstOrNull { it.id == session.profileId }
        ?: completeConfigs.firstOrNull()
    val configSignature = completeConfigs.joinToString("|") { "${it.id}:${it.model}" }
    val catalogSignature = modelCatalogs.entries
        .sortedBy { it.key }
        .joinToString("|") { (id, models) -> "$id:${models.joinToString(",")}" }

    fun modelOptions(config: AiConfig?): List<String> {
        if (config == null) return session.model.takeIf(String::isNotBlank)?.let(::listOf).orEmpty()
        return buildList {
            config.model.trim().takeIf(String::isNotBlank)?.let(::add)
            addAll(modelCatalogs[config.id].orEmpty())
            addAll(config.provider.fallbackModels)
            if (session.profileId == config.id) {
                session.model.trim().takeIf(String::isNotBlank)?.let(::add)
            }
        }.map(String::trim).filter(String::isNotBlank).distinct()
    }

    val availableModels = modelOptions(preferredConfig)
    val selectedModel = when {
        session.profileId == preferredConfig?.id && session.model in availableModels -> session.model
        preferredConfig?.model?.isNotBlank() == true -> preferredConfig.model
        else -> availableModels.firstOrNull().orEmpty()
    }
    val lotteryKey = snapshot?.lottery?.apiKey.orEmpty()
    val currentTarget = report?.targetPeriod
    val currentArchiveId = if (
        preferredConfig != null && selectedModel.isNotBlank() &&
        lotteryKey.isNotBlank() && !currentTarget.isNullOrBlank()
    ) {
        AiChatArchiveId.of(lotteryKey, currentTarget, preferredConfig.id, selectedModel)
    } else {
        ""
    }
    val archiveItems = controller.archives
        .filter { summary ->
            (lotteryKey.isBlank() || summary.lotteryKey == lotteryKey) &&
                (preferredConfig == null || summary.profileId == preferredConfig.id)
        }
        .sortedByDescending(AiChatArchiveSummary::updatedAtEpochMs)

    var input by rememberSaveable { mutableStateOf("") }
    var archiveMenuExpanded by rememberSaveable { mutableStateOf(false) }
    val listState = rememberLazyListState()

    fun openCurrent(config: AiConfig?, model: String) {
        controller.selectContext(
            profileId = config?.id.orEmpty(),
            profileName = config?.displayName.orEmpty(),
            model = model,
            lotteryKey = lotteryKey,
            targetPeriod = currentTarget,
        )
    }

    LaunchedEffect(configSignature, catalogSignature, lotteryKey, currentTarget) {
        openCurrent(preferredConfig, selectedModel)
    }
    LaunchedEffect(
        session.messages.size,
        session.messages.lastOrNull()?.content?.length,
        session.isRunning,
        session.prediction,
    ) {
        val extra = if (session.prediction != null) 1 else 0
        val lastIndex = session.messages.size + extra - 1
        if (lastIndex >= 0) listState.animateScrollToItem(lastIndex)
    }

    fun submit(text: String) {
        val config = completeConfigs.firstOrNull { it.id == controller.session.profileId }
            ?: preferredConfig
        val currentSnapshot = snapshot
        val currentReport = report
        if (
            config == null || currentSnapshot == null || currentReport == null ||
            controller.session.isReadOnlyArchive
        ) return
        val question = text.trim()
        if (question.isBlank()) return
        input = ""
        controller.send(
            config = config.copy(model = controller.session.model.ifBlank { selectedModel }),
            snapshot = currentSnapshot,
            report = currentReport,
            question = question,
        )
    }

    Dialog(
        onDismissRequest = {
            controller.cancel()
            onDismiss()
        },
        properties = DialogProperties(
            usePlatformDefaultWidth = false,
            decorFitsSystemWindows = false,
        ),
    ) {
        Surface(
            modifier = Modifier
                .fillMaxSize()
                .background(colors.page)
                .windowInsetsPadding(WindowInsets.systemBars),
            color = colors.page,
        ) {
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .imePadding()
                    .padding(horizontal = 12.dp),
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(top = 10.dp, bottom = 8.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Box(
                        modifier = Modifier
                            .size(38.dp)
                            .clip(RoundedCornerShape(13.dp))
                            .background(colors.accent.copy(alpha = 0.14f)),
                        contentAlignment = Alignment.Center,
                    ) {
                        Icon(
                            Icons.Rounded.AutoAwesome,
                            contentDescription = null,
                            tint = colors.accent,
                            modifier = Modifier.size(20.dp),
                        )
                    }
                    Spacer(Modifier.width(10.dp))
                    Column(Modifier.weight(1f)) {
                        Text(
                            "天机分析对话",
                            color = colors.text,
                            fontSize = 17.sp,
                            fontWeight = FontWeight.ExtraBold,
                        )
                        Text(
                            if (session.isReadOnlyArchive) {
                                "历史归档只读 · 对话与候选长期保存"
                            } else {
                                "真实流式输出 · 对话与候选按目标期归档"
                            },
                            color = colors.textDim,
                            fontSize = 8.sp,
                        )
                    }
                    Box {
                        IconButton(
                            onClick = { archiveMenuExpanded = true },
                            enabled = !session.isRunning,
                        ) {
                            Icon(Icons.Rounded.History, "历史对话与候选", tint = colors.textSoft)
                        }
                        DropdownMenu(
                            expanded = archiveMenuExpanded,
                            onDismissRequest = { archiveMenuExpanded = false },
                        ) {
                            DropdownMenuItem(
                                text = {
                                    Column {
                                        Text("返回当前目标期", fontWeight = FontWeight.Bold)
                                        Text(
                                            "${currentTarget ?: "待同步"} · ${selectedModel.ifBlank { "待选模型" }}",
                                            fontSize = 11.sp,
                                        )
                                    }
                                },
                                onClick = {
                                    archiveMenuExpanded = false
                                    openCurrent(preferredConfig, selectedModel)
                                },
                            )
                            if (archiveItems.isNotEmpty()) HorizontalDivider()
                            archiveItems.take(60).forEach { archive ->
                                DropdownMenuItem(
                                    text = {
                                        Column {
                                            Text(
                                                "目标期 ${archive.targetPeriod}",
                                                fontWeight = if (archive.id == session.archiveId) {
                                                    FontWeight.Bold
                                                } else {
                                                    FontWeight.Medium
                                                },
                                            )
                                            Text(
                                                buildString {
                                                    append(archive.model)
                                                    append(" · ${archive.messageCount}条对话")
                                                    if (archive.hasPrediction) append(" · 有候选")
                                                },
                                                fontSize = 11.sp,
                                            )
                                        }
                                    },
                                    onClick = {
                                        archiveMenuExpanded = false
                                        if (archive.id == currentArchiveId) {
                                            openCurrent(preferredConfig, selectedModel)
                                        } else {
                                            controller.openArchive(archive.id)
                                        }
                                    },
                                )
                            }
                            if (archiveItems.isEmpty()) {
                                DropdownMenuItem(
                                    text = { Text("暂无已保存的历史对话") },
                                    enabled = false,
                                    onClick = {},
                                )
                            }
                        }
                    }
                    IconButton(onClick = onRefresh, enabled = !session.isRunning && !session.isReadOnlyArchive) {
                        Icon(Icons.Rounded.Refresh, "刷新开奖历史", tint = colors.textSoft)
                    }
                    IconButton(
                        onClick = controller::clear,
                        enabled = (session.messages.isNotEmpty() || session.prediction != null) &&
                            !session.isRunning,
                    ) {
                        Icon(Icons.Rounded.DeleteSweep, "删除当前记录", tint = colors.textSoft)
                    }
                    IconButton(
                        onClick = {
                            controller.cancel()
                            onDismiss()
                        },
                    ) {
                        Icon(Icons.Rounded.Close, "关闭", tint = colors.textSoft)
                    }
                }

                SelectorLabel("配置")
                if (completeConfigs.isNotEmpty()) {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .horizontalScroll(rememberScrollState())
                            .padding(bottom = 6.dp),
                        horizontalArrangement = Arrangement.spacedBy(7.dp),
                    ) {
                        completeConfigs.forEach { config ->
                            FilterChip(
                                selected = session.profileId == config.id,
                                onClick = {
                                    val nextModel = modelOptions(config).firstOrNull { it == config.model }
                                        ?: modelOptions(config).firstOrNull().orEmpty()
                                    openCurrent(config, nextModel)
                                },
                                enabled = !session.isRunning && !session.isReadOnlyArchive,
                                label = {
                                    Text(
                                        config.displayName,
                                        maxLines = 1,
                                        overflow = TextOverflow.Ellipsis,
                                        fontSize = 8.sp,
                                    )
                                },
                            )
                        }
                    }
                }

                SelectorLabel("模型")
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .horizontalScroll(rememberScrollState())
                        .padding(bottom = 6.dp),
                    horizontalArrangement = Arrangement.spacedBy(7.dp),
                ) {
                    availableModels.forEach { model ->
                        FilterChip(
                            selected = session.model == model,
                            onClick = { openCurrent(preferredConfig, model) },
                            enabled = !session.isRunning && !session.isReadOnlyArchive,
                            label = {
                                Text(
                                    model,
                                    maxLines = 1,
                                    overflow = TextOverflow.Ellipsis,
                                    fontSize = 8.sp,
                                )
                            },
                        )
                    }
                    if (availableModels.isEmpty()) {
                        Text(
                            "请先读取模型列表或保存模型",
                            color = colors.textDim,
                            fontSize = 8.sp,
                            modifier = Modifier.padding(8.dp),
                        )
                    }
                }

                SelectorLabel("分析人设")
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .horizontalScroll(rememberScrollState())
                        .padding(bottom = 6.dp),
                    horizontalArrangement = Arrangement.spacedBy(7.dp),
                ) {
                    AiChatPersona.values().forEach { persona ->
                        FilterChip(
                            selected = session.personaId == persona.id,
                            onClick = { controller.selectPersona(persona.id) },
                            enabled = !session.isRunning && !session.isReadOnlyArchive,
                            label = {
                                Text(
                                    persona.displayName,
                                    maxLines = 1,
                                    fontSize = 8.sp,
                                )
                            },
                        )
                    }
                }
                Text(
                    "${selectedPersona.displayName} · ${selectedPersona.description}",
                    color = colors.accent,
                    fontSize = 7.5.sp,
                    lineHeight = 11.sp,
                    modifier = Modifier
                        .fillMaxWidth()
                        .clip(RoundedCornerShape(10.dp))
                        .background(colors.accent.copy(alpha = 0.07f))
                        .padding(horizontal = 10.dp, vertical = 7.dp),
                )
                Spacer(Modifier.height(7.dp))

                SourceNotice(
                    snapshot = snapshot,
                    report = report,
                    hasConfig = preferredConfig != null,
                    session = session,
                )
                Spacer(Modifier.height(8.dp))

                LazyColumn(
                    state = listState,
                    modifier = Modifier.weight(1f).fillMaxWidth(),
                    contentPadding = androidx.compose.foundation.layout.PaddingValues(
                        top = 6.dp,
                        bottom = 12.dp,
                    ),
                    verticalArrangement = Arrangement.spacedBy(9.dp),
                ) {
                    if (session.messages.isEmpty()) {
                        item(key = "welcome") {
                            WelcomePanel(
                                persona = selectedPersona,
                                enabled = preferredConfig != null && snapshot != null && report != null &&
                                    !session.isReadOnlyArchive,
                                onPrompt = ::submit,
                            )
                        }
                    }
                    items(session.messages, key = AiChatMessage::id) { message ->
                        ChatMessageBubble(
                            message = message,
                            isStreaming = message.id == session.streamingMessageId && session.isRunning,
                        )
                    }
                    session.prediction?.let { prediction ->
                        item(key = "prediction-${session.archiveId}-${session.messages.size}") {
                            ChatPredictionCard(
                                prediction = prediction,
                                targetPeriod = session.targetPeriod,
                            )
                        }
                    }
                    if (session.isRunning) {
                        item(key = "running-status") {
                            StreamingStatus(
                                progress = session.progress,
                                hasVisibleText = session.messages
                                    .firstOrNull { it.id == session.streamingMessageId }
                                    ?.content?.isNotBlank() == true,
                                onCancel = controller::cancel,
                            )
                        }
                    }
                    session.error?.let { error ->
                        item(key = "error") {
                            Text(
                                error,
                                color = colors.red,
                                fontSize = 8.5.sp,
                                lineHeight = 13.sp,
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .clip(RoundedCornerShape(13.dp))
                                    .background(colors.red.copy(alpha = 0.07f))
                                    .border(
                                        1.dp,
                                        colors.red.copy(alpha = 0.18f),
                                        RoundedCornerShape(13.dp),
                                    )
                                    .padding(11.dp),
                            )
                        }
                    }
                }

                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(bottom = 10.dp),
                    verticalAlignment = Alignment.Bottom,
                ) {
                    OutlinedTextField(
                        value = input,
                        onValueChange = { input = it },
                        enabled = preferredConfig != null && snapshot != null && report != null &&
                            !session.isRunning && !session.isReadOnlyArchive,
                        modifier = Modifier.weight(1f),
                        shape = RoundedCornerShape(18.dp),
                        placeholder = {
                            Text(
                                if (session.isReadOnlyArchive) {
                                    "历史归档为只读，请从时钟按钮返回当前期"
                                } else {
                                    selectedPersona.quickPrompts.firstOrNull()
                                        ?: "输入你想分析的问题"
                                },
                                fontSize = 8.5.sp,
                            )
                        },
                        minLines = 1,
                        maxLines = 4,
                        keyboardOptions = KeyboardOptions(imeAction = ImeAction.Send),
                        keyboardActions = KeyboardActions(onSend = { submit(input) }),
                    )
                    Spacer(Modifier.width(8.dp))
                    Button(
                        onClick = { submit(input) },
                        enabled = input.isNotBlank() && preferredConfig != null &&
                            snapshot != null && report != null && !session.isRunning &&
                            !session.isReadOnlyArchive,
                        modifier = Modifier.size(52.dp),
                        shape = CircleShape,
                        contentPadding = androidx.compose.foundation.layout.PaddingValues(0.dp),
                        colors = ButtonDefaults.buttonColors(containerColor = colors.accent),
                    ) {
                        Icon(Icons.AutoMirrored.Rounded.Send, contentDescription = "发送", tint = Color.White)
                    }
                }
            }
        }
    }
}


@Composable
private fun SelectorLabel(text: String) {
    val colors = LocalTianjiColors.current
    Text(
        text,
        color = colors.textDim,
        fontSize = 7.sp,
        fontWeight = FontWeight.Bold,
        modifier = Modifier.padding(start = 2.dp, bottom = 2.dp),
    )
}

@Composable
private fun SourceNotice(
    snapshot: DrawSnapshot?,
    report: ForecastReport?,
    hasConfig: Boolean,
    session: AiChatSession,
) {
    val colors = LocalTianjiColors.current
    val tint = when {
        session.isReadOnlyArchive -> colors.accent
        !hasConfig -> colors.amber
        snapshot == null || report == null -> colors.red
        snapshot.sourceHealth.isFresh -> colors.green
        else -> colors.amber
    }
    val text = when {
        session.isReadOnlyArchive ->
            "历史归档 · 目标期 ${session.targetPeriod ?: "未知"} · ${session.model} · 只读"
        !hasConfig -> "请先在数据页保存一个完整的 AI 配置"
        snapshot == null || report == null -> "开奖历史尚未准备完成，请先刷新"
        else -> "已载入 ${snapshot.history.takeLast(120).size} 期接口历史 · 目标期 ${report.targetPeriod} · ${session.model}"
    }
    Text(
        text,
        color = tint,
        fontSize = 8.sp,
        fontWeight = FontWeight.Bold,
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(12.dp))
            .background(tint.copy(alpha = 0.07f))
            .border(1.dp, tint.copy(alpha = 0.18f), RoundedCornerShape(12.dp))
            .padding(horizontal = 11.dp, vertical = 9.dp),
    )
}

@Composable
private fun WelcomePanel(
    persona: AiChatPersona,
    enabled: Boolean,
    onPrompt: (String) -> Unit,
) {
    val colors = LocalTianjiColors.current
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(20.dp))
            .background(Color.White.copy(alpha = 0.035f))
            .border(1.dp, colors.line, RoundedCornerShape(20.dp))
            .padding(15.dp),
    ) {
        Text(
            "${persona.displayName}可以这样问",
            color = colors.text,
            fontSize = 13.sp,
            fontWeight = FontWeight.Bold,
        )
        Spacer(Modifier.height(5.dp))
        Text(
            persona.description + "。回答只基于当前接口历史和本机模型参考，不会冒充真实中奖概率。",
            color = colors.textDim,
            fontSize = 8.sp,
            lineHeight = 13.sp,
        )
        Spacer(Modifier.height(12.dp))
        persona.quickPrompts.forEach { prompt ->
            OutlinedButton(
                onClick = { onPrompt(prompt) },
                enabled = enabled,
                modifier = Modifier.fillMaxWidth().padding(vertical = 3.dp),
                shape = RoundedCornerShape(13.dp),
            ) {
                Text(
                    prompt,
                    color = if (enabled) colors.textSoft else colors.textDim,
                    fontSize = 8.sp,
                    modifier = Modifier.fillMaxWidth(),
                )
            }
        }
    }
}

@Composable
private fun ChatMessageBubble(
    message: AiChatMessage,
    isStreaming: Boolean,
) {
    val colors = LocalTianjiColors.current
    val user = message.role == AiChatRole.USER
    Box(
        modifier = Modifier.fillMaxWidth(),
        contentAlignment = if (user) Alignment.CenterEnd else Alignment.CenterStart,
    ) {
        Column(
            modifier = Modifier
                .widthIn(max = 340.dp)
                .clip(
                    RoundedCornerShape(
                        topStart = 18.dp,
                        topEnd = 18.dp,
                        bottomStart = if (user) 18.dp else 5.dp,
                        bottomEnd = if (user) 5.dp else 18.dp,
                    ),
                )
                .background(
                    if (user) colors.accent.copy(alpha = 0.22f)
                    else Color.White.copy(alpha = 0.045f),
                )
                .border(
                    1.dp,
                    if (user) colors.accent.copy(alpha = 0.25f) else colors.line,
                    RoundedCornerShape(18.dp),
                )
                .padding(horizontal = 13.dp, vertical = 11.dp),
        ) {
            if (!user) {
                Text(
                    "天机分析助手",
                    color = colors.accent,
                    fontSize = 7.sp,
                    fontWeight = FontWeight.Bold,
                )
                Spacer(Modifier.height(5.dp))
            }
            val visibleContent = when {
                message.content.isNotBlank() && isStreaming -> message.content + " ▍"
                message.content.isNotBlank() -> message.content
                isStreaming -> "正在思考并等待首段回答…"
                else -> ""
            }
            if (visibleContent.isNotBlank()) {
                Text(
                    visibleContent,
                    color = if (message.content.isBlank()) colors.textDim else colors.textSoft,
                    fontSize = 9.sp,
                    lineHeight = 15.sp,
                )
            }
            message.latencyMs?.let { latency ->
                Spacer(Modifier.height(5.dp))
                Text(
                    "${latency / 1_000.0}s",
                    color = colors.textDim,
                    fontSize = 6.5.sp,
                    modifier = Modifier.align(Alignment.End),
                )
            }
        }
    }
}

@Composable
private fun StreamingStatus(
    progress: String,
    hasVisibleText: Boolean,
    onCancel: () -> Unit,
) {
    val colors = LocalTianjiColors.current
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(13.dp))
            .background(colors.accent.copy(alpha = 0.055f))
            .border(1.dp, colors.accent.copy(alpha = 0.14f), RoundedCornerShape(13.dp))
            .padding(horizontal = 11.dp, vertical = 8.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        CircularProgressIndicator(
            modifier = Modifier.size(14.dp),
            color = colors.accent,
            strokeWidth = 2.dp,
        )
        Spacer(Modifier.width(8.dp))
        Text(
            progress.ifBlank {
                if (hasVisibleText) "正在继续生成…" else "正在分析…"
            },
            color = colors.textDim,
            fontSize = 7.5.sp,
            modifier = Modifier.weight(1f),
        )
        IconButton(onClick = onCancel, modifier = Modifier.size(30.dp)) {
            Icon(
                Icons.Rounded.StopCircle,
                contentDescription = "停止生成",
                tint = colors.amber,
            )
        }
    }
}

@Composable
private fun ChatPredictionCard(
    prediction: AiChatPrediction,
    targetPeriod: String?,
) {
    val colors = LocalTianjiColors.current
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(20.dp))
            .background(colors.accent.copy(alpha = 0.075f))
            .border(1.dp, colors.accent.copy(alpha = 0.22f), RoundedCornerShape(20.dp))
            .padding(15.dp),
    ) {
        Text(
            "对话候选 · 第${prediction.position + 1}名",
            color = colors.accent,
            fontSize = 11.sp,
            fontWeight = FontWeight.ExtraBold,
        )
        Text(
            "目标期 ${targetPeriod ?: "待同步"} · 仅供本次对话比较，不计入真实成绩",
            color = colors.textDim,
            fontSize = 7.sp,
        )
        Spacer(Modifier.height(12.dp))
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceEvenly) {
            prediction.top6.forEach { number -> ChatNumberBall(number) }
        }
        Spacer(Modifier.height(10.dp))
        val ranked = prediction.probabilities.indices
            .sortedByDescending { prediction.probabilities[it] }
            .take(3)
        Text(
            ranked.joinToString(" · ") { index ->
                "${index + 1}号 ${(prediction.probabilities[index] * 100).format1()}%"
            },
            color = colors.textSoft,
            fontSize = 7.5.sp,
        )
    }
}

@Composable
private fun ChatNumberBall(number: Int) {
    val colors = LocalTianjiColors.current
    Box(
        modifier = Modifier
            .size(34.dp)
            .clip(CircleShape)
            .background(colors.accent.copy(alpha = 0.18f))
            .border(1.dp, colors.accent.copy(alpha = 0.35f), CircleShape),
        contentAlignment = Alignment.Center,
    ) {
        Text(
            number.toString(),
            color = colors.text,
            fontSize = 11.sp,
            fontWeight = FontWeight.ExtraBold,
        )
    }
}

private fun Double.format1(): String = String.format(java.util.Locale.US, "%.1f", this)
