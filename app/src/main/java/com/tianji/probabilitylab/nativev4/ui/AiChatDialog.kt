package com.tianji.probabilitylab.nativev4.ui

import androidx.compose.animation.animateContentSize
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
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
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.rounded.Send
import androidx.compose.material.icons.rounded.Add
import androidx.compose.material.icons.rounded.AutoAwesome
import androidx.compose.material.icons.rounded.ChatBubble
import androidx.compose.material.icons.rounded.Close
import androidx.compose.material.icons.rounded.DeleteSweep
import androidx.compose.material.icons.rounded.History
import androidx.compose.material.icons.rounded.KeyboardArrowDown
import androidx.compose.material.icons.rounded.KeyboardArrowUp
import androidx.compose.material.icons.rounded.MoreVert
import androidx.compose.material.icons.rounded.Refresh
import androidx.compose.material.icons.rounded.StopCircle
import androidx.compose.material.icons.rounded.Tune
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
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
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import com.tianji.probabilitylab.nativev4.ai.AiChatArchiveSummary
import com.tianji.probabilitylab.nativev4.ai.AiChatCandidateRecord
import com.tianji.probabilitylab.nativev4.ai.AiChatController
import com.tianji.probabilitylab.nativev4.ai.AiChatMessage
import com.tianji.probabilitylab.nativev4.ai.AiChatPersona
import com.tianji.probabilitylab.nativev4.ai.AiChatRole
import com.tianji.probabilitylab.nativev4.ai.AiChatSession
import com.tianji.probabilitylab.nativev4.ai.AiConfig
import com.tianji.probabilitylab.nativev4.model.DrawSnapshot
import com.tianji.probabilitylab.nativev4.model.ForecastReport
import com.tianji.probabilitylab.nativev4.ui.theme.LocalTianjiColors
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

@Composable
fun AiChatFloatingButton(onClick: () -> Unit, modifier: Modifier = Modifier) {
    val colors = LocalTianjiColors.current
    FloatingActionButton(
        onClick = onClick,
        modifier = modifier.size(52.dp),
        shape = RoundedCornerShape(18.dp),
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
    val selectedConfig = completeConfigs.firstOrNull { it.id == session.profileId }
        ?: completeConfigs.firstOrNull()

    fun modelOptions(config: AiConfig?): List<String> = buildList {
        if (config != null) {
            config.model.trim().takeIf(String::isNotBlank)?.let(::add)
            addAll(modelCatalogs[config.id].orEmpty())
            addAll(config.provider.fallbackModels)
        }
        if (session.profileId == config?.id) session.model.takeIf(String::isNotBlank)?.let(::add)
    }.map(String::trim).filter(String::isNotBlank).distinct()

    val models = modelOptions(selectedConfig)
    val selectedModel = session.model.takeIf { it in models }
        ?: selectedConfig?.model?.takeIf(String::isNotBlank)
        ?: models.firstOrNull().orEmpty()
    val lotteryKey = snapshot?.lottery?.apiKey.orEmpty()
    val targetPeriod = report?.targetPeriod

    var input by rememberSaveable { mutableStateOf("") }
    var showHistory by rememberSaveable { mutableStateOf(false) }
    var showNewConversation by rememberSaveable { mutableStateOf(false) }
    var showControls by rememberSaveable { mutableStateOf(false) }
    var moreExpanded by rememberSaveable { mutableStateOf(false) }
    val listState = rememberLazyListState()

    fun openContext(config: AiConfig?, model: String) {
        controller.selectContext(
            profileId = config?.id.orEmpty(),
            profileName = config?.displayName.orEmpty(),
            model = model,
            lotteryKey = lotteryKey,
            targetPeriod = targetPeriod,
            latestPeriod = snapshot?.latest?.period,
            latestNumbers = snapshot?.latest?.numbers.orEmpty(),
        )
    }

    val signature = completeConfigs.joinToString("|") { "${it.id}:${it.model}" } +
        modelCatalogs.entries.sortedBy { it.key }.joinToString("|") { it.value.joinToString(",") }
    LaunchedEffect(signature, lotteryKey, targetPeriod, snapshot?.latest?.period) {
        openContext(selectedConfig, selectedModel)
    }
    LaunchedEffect(
        session.messages.size,
        session.messages.lastOrNull()?.content?.length,
        session.isRunning,
        session.candidates.size,
    ) {
        val last = session.messages.lastIndex
        if (last >= 0) listState.animateScrollToItem(last)
    }

    fun submit(value: String) {
        val config = completeConfigs.firstOrNull { it.id == controller.session.profileId }
            ?: selectedConfig
        val activeSnapshot = snapshot
        val activeReport = report
        val question = value.trim()
        if (config == null || activeSnapshot == null || activeReport == null || question.isBlank()) return
        input = ""
        controller.send(
            config = config.copy(model = controller.session.model.ifBlank { selectedModel }),
            snapshot = activeSnapshot,
            report = activeReport,
            question = question,
        )
    }

    Dialog(
        onDismissRequest = onDismiss,
        properties = DialogProperties(usePlatformDefaultWidth = false, decorFitsSystemWindows = false),
    ) {
        Surface(
            modifier = Modifier.fillMaxSize().windowInsetsPadding(WindowInsets.systemBars),
            color = colors.page,
        ) {
            Column(
                modifier = Modifier.fillMaxSize().imePadding().padding(horizontal = 14.dp),
            ) {
                ChatTopBar(
                    session = session,
                    onNew = { showNewConversation = true },
                    onHistory = { showHistory = true },
                    onClose = onDismiss,
                    onMore = { moreExpanded = true },
                    moreExpanded = moreExpanded,
                    dismissMore = { moreExpanded = false },
                    onRefresh = onRefresh,
                    onClear = controller::clear,
                    onDelete = controller::deleteCurrent,
                )

                SessionControlStrip(
                    expanded = showControls,
                    onToggle = { showControls = !showControls },
                    configs = completeConfigs,
                    selectedConfig = selectedConfig,
                    models = models,
                    selectedModel = selectedModel,
                    session = session,
                    snapshot = snapshot,
                    report = report,
                    onConfig = { config ->
                        val next = modelOptions(config).firstOrNull { it == config.model }
                            ?: modelOptions(config).firstOrNull().orEmpty()
                        openContext(config, next)
                    },
                    onModel = { openContext(selectedConfig, it) },
                    onPersona = controller::selectPersona,
                )

                val candidatesByMessage = session.candidates.groupBy(AiChatCandidateRecord::messageId)
                LazyColumn(
                    state = listState,
                    modifier = Modifier.weight(1f).fillMaxWidth(),
                    contentPadding = PaddingValues(top = 16.dp, bottom = 16.dp),
                    verticalArrangement = Arrangement.spacedBy(14.dp),
                ) {
                    if (session.messages.isEmpty()) {
                        item("welcome") {
                            WelcomePanel(
                                persona = AiChatPersona.fromId(session.personaId),
                                enabled = selectedConfig != null && snapshot != null && report != null,
                                onPrompt = ::submit,
                            )
                        }
                    }
                    items(session.messages, key = AiChatMessage::id) { message ->
                        ChatMessageBubble(
                            message = message,
                            isStreaming = message.id == session.streamingMessageId && session.isRunning,
                        )
                        candidatesByMessage[message.id].orEmpty().forEach { record ->
                            Spacer(Modifier.height(8.dp))
                            ChatPredictionCard(record)
                        }
                    }
                    val detached = session.candidates.filter { it.messageId.isBlank() }
                    items(detached, key = AiChatCandidateRecord::id) { record -> ChatPredictionCard(record) }
                    if (session.isRunning) {
                        item("running") { StreamingStatus(session.progress, controller::cancel) }
                    }
                    session.rolloverNotice?.let { notice ->
                        item("rollover") { SystemEventChip(notice) }
                    }
                    session.error?.let { error ->
                        item("error") {
                            Surface(
                                shape = RoundedCornerShape(16.dp),
                                color = colors.red.copy(alpha = 0.08f),
                            ) {
                                Text(
                                    error,
                                    color = colors.red,
                                    fontSize = 12.5.sp,
                                    lineHeight = 18.sp,
                                    modifier = Modifier.padding(horizontal = 14.dp, vertical = 11.dp),
                                )
                            }
                        }
                    }
                }

                ChatComposer(
                    input = input,
                    onInput = { input = it },
                    enabled = selectedConfig != null && snapshot != null && report != null && !session.isRunning,
                    isRunning = session.isRunning,
                    placeholder = AiChatPersona.fromId(session.personaId).quickPrompts.firstOrNull()
                        ?: "继续追问，或告诉它上一期哪里需要调整",
                    onSend = { submit(input) },
                    onStop = controller::cancel,
                )
            }
        }
    }

    if (showHistory) {
        ConversationHistoryDialog(
            items = controller.archives.filter { lotteryKey.isBlank() || it.lotteryKey == lotteryKey },
            currentId = session.archiveId,
            onOpen = { controller.openArchive(it); showHistory = false },
            onDismiss = { showHistory = false },
        )
    }
    if (showNewConversation) {
        NewConversationDialog(
            hasHistory = session.messages.isNotEmpty(),
            onBlank = {
                controller.newConversation(
                    selectedConfig?.id.orEmpty(), selectedConfig?.displayName.orEmpty(), selectedModel,
                    lotteryKey, targetPeriod, inheritStrategy = false,
                )
                showNewConversation = false
            },
            onContinue = {
                controller.newConversation(
                    selectedConfig?.id.orEmpty(), selectedConfig?.displayName.orEmpty(), selectedModel,
                    lotteryKey, targetPeriod, inheritStrategy = true,
                )
                showNewConversation = false
            },
            onDismiss = { showNewConversation = false },
        )
    }
}

@Composable
private fun ChatTopBar(
    session: AiChatSession,
    onNew: () -> Unit,
    onHistory: () -> Unit,
    onClose: () -> Unit,
    onMore: () -> Unit,
    moreExpanded: Boolean,
    dismissMore: () -> Unit,
    onRefresh: () -> Unit,
    onClear: () -> Unit,
    onDelete: () -> Unit,
) {
    val colors = LocalTianjiColors.current
    Row(
        modifier = Modifier.fillMaxWidth().height(54.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Column(Modifier.weight(1f)) {
            Text(
                "天机",
                color = colors.text,
                fontSize = 17.sp,
                fontWeight = FontWeight.Bold,
                maxLines = 1,
            )
            Text(
                session.title.ifBlank { "新对话" },
                color = colors.textDim,
                fontSize = 9.5.sp,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
        }
        ContextUsagePill(session.contextUsagePercent)
        SmallTopAction(onClick = onNew, enabled = !session.isRunning) {
            Icon(Icons.Rounded.Add, "新建对话", tint = colors.textSoft, modifier = Modifier.size(19.dp))
        }
        SmallTopAction(onClick = onHistory, enabled = !session.isRunning) {
            Icon(Icons.Rounded.History, "对话历史", tint = colors.textSoft, modifier = Modifier.size(18.dp))
        }
        Box {
            SmallTopAction(onClick = onMore, enabled = !session.isRunning) {
                Icon(Icons.Rounded.MoreVert, "更多", tint = colors.textSoft, modifier = Modifier.size(19.dp))
            }
            DropdownMenu(expanded = moreExpanded, onDismissRequest = dismissMore) {
                DropdownMenuItem(
                    text = { Text("刷新开奖历史") },
                    leadingIcon = { Icon(Icons.Rounded.Refresh, null) },
                    onClick = { dismissMore(); onRefresh() },
                )
                DropdownMenuItem(
                    text = { Text("清空当前对话") },
                    leadingIcon = { Icon(Icons.Rounded.DeleteSweep, null) },
                    onClick = { dismissMore(); onClear() },
                )
                DropdownMenuItem(
                    text = { Text("删除当前会话") },
                    leadingIcon = { Icon(Icons.Rounded.DeleteSweep, null) },
                    onClick = { dismissMore(); onDelete() },
                )
            }
        }
        SmallTopAction(onClick = onClose) {
            Icon(Icons.Rounded.Close, "关闭", tint = colors.textSoft, modifier = Modifier.size(20.dp))
        }
    }
}

@Composable
private fun SmallTopAction(
    onClick: () -> Unit,
    enabled: Boolean = true,
    content: @Composable () -> Unit,
) {
    IconButton(onClick = onClick, enabled = enabled, modifier = Modifier.size(38.dp)) { content() }
}

@Composable
private fun ContextUsagePill(percent: Int) {
    val colors = LocalTianjiColors.current
    val tint = when {
        percent >= 80 -> colors.amber
        percent >= 55 -> colors.accent
        else -> colors.green
    }
    Surface(shape = RoundedCornerShape(10.dp), color = tint.copy(alpha = 0.08f)) {
        Text(
            "${percent.coerceIn(0, 100)}%",
            color = tint,
            fontSize = 8.5.sp,
            fontWeight = FontWeight.Bold,
            modifier = Modifier.padding(horizontal = 7.dp, vertical = 4.dp),
        )
    }
    Spacer(Modifier.width(2.dp))
}

@Composable
private fun SessionControlStrip(
    expanded: Boolean,
    onToggle: () -> Unit,
    configs: List<AiConfig>,
    selectedConfig: AiConfig?,
    models: List<String>,
    selectedModel: String,
    session: AiChatSession,
    snapshot: DrawSnapshot?,
    report: ForecastReport?,
    onConfig: (AiConfig) -> Unit,
    onModel: (String) -> Unit,
    onPersona: (String) -> Unit,
) {
    val colors = LocalTianjiColors.current
    val persona = AiChatPersona.fromId(session.personaId)
    Surface(
        modifier = Modifier.fillMaxWidth().animateContentSize(),
        shape = RoundedCornerShape(14.dp),
        color = Color.White.copy(alpha = 0.025f),
    ) {
        Column {
            Row(
                modifier = Modifier.fillMaxWidth().height(48.dp).clickable(onClick = onToggle)
                    .padding(horizontal = 12.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Icon(Icons.Rounded.Tune, null, tint = colors.accent, modifier = Modifier.size(17.dp))
                Spacer(Modifier.width(9.dp))
                Text(
                    selectedModel.ifBlank { "选择模型" },
                    color = colors.text,
                    fontSize = 11.5.sp,
                    fontWeight = FontWeight.SemiBold,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                    modifier = Modifier.weight(1f),
                )
                Text(
                    persona.displayName,
                    color = colors.accent,
                    fontSize = 8.5.sp,
                    maxLines = 1,
                    modifier = Modifier.padding(horizontal = 7.dp),
                )
                Text(
                    report?.targetPeriod?.let { "期$it" } ?: "待同步",
                    color = colors.textDim,
                    fontSize = 8.5.sp,
                    maxLines = 1,
                )
                Spacer(Modifier.width(4.dp))
                Icon(
                    if (expanded) Icons.Rounded.KeyboardArrowUp else Icons.Rounded.KeyboardArrowDown,
                    if (expanded) "收起" else "展开",
                    tint = colors.textDim,
                    modifier = Modifier.size(18.dp),
                )
            }
            if (expanded) {
                Box(Modifier.fillMaxWidth().height(1.dp).background(colors.line.copy(alpha = 0.4f)))
                Column(Modifier.padding(horizontal = 12.dp, vertical = 5.dp)) {
                    SelectorRow(
                        label = "配置",
                        value = selectedConfig?.displayName ?: "未配置",
                        options = configs.map { it.id to it.displayName },
                        selectedKey = selectedConfig?.id.orEmpty(),
                        onSelect = { id -> configs.firstOrNull { it.id == id }?.let(onConfig) },
                    )
                    SelectorRow(
                        label = "模型",
                        value = selectedModel.ifBlank { "未选择" },
                        options = models.map { it to it },
                        selectedKey = selectedModel,
                        onSelect = onModel,
                    )
                    SelectorRow(
                        label = "人设",
                        value = persona.displayName,
                        options = AiChatPersona.entries.map { it.id to it.displayName },
                        selectedKey = session.personaId,
                        onSelect = onPersona,
                    )
                    val ready = snapshot != null && report != null && selectedConfig != null
                    Text(
                        if (ready) "${snapshot!!.history.takeLast(120).size}期真实接口历史" else "请先准备开奖历史和完整AI配置",
                        color = if (ready) colors.green else colors.amber,
                        fontSize = 8.5.sp,
                        modifier = Modifier.padding(start = 62.dp, top = 2.dp, bottom = 3.dp),
                    )
                }
            }
        }
    }
}

@Composable
private fun SelectorRow(
    label: String,
    value: String,
    options: List<Pair<String, String>>,
    selectedKey: String,
    onSelect: (String) -> Unit,
) {
    val colors = LocalTianjiColors.current
    var expanded by remember { mutableStateOf(false) }
    Box {
        Row(
            modifier = Modifier.fillMaxWidth().clickable(enabled = options.isNotEmpty()) { expanded = true }
                .padding(vertical = 9.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(label, color = colors.textDim, fontSize = 11.sp, modifier = Modifier.width(62.dp))
            Text(
                value,
                color = colors.textSoft,
                fontSize = 12.sp,
                fontWeight = FontWeight.Medium,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
                modifier = Modifier.weight(1f),
            )
            Icon(Icons.Rounded.KeyboardArrowDown, null, tint = colors.textDim, modifier = Modifier.size(18.dp))
        }
        DropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
            options.forEach { (key, text) ->
                DropdownMenuItem(
                    text = {
                        Text(text, fontWeight = if (key == selectedKey) FontWeight.Bold else FontWeight.Normal)
                    },
                    onClick = { expanded = false; onSelect(key) },
                )
            }
        }
    }
}

@Composable
private fun WelcomePanel(persona: AiChatPersona, enabled: Boolean, onPrompt: (String) -> Unit) {
    val colors = LocalTianjiColors.current
    Column(
        modifier = Modifier.fillMaxWidth().padding(top = 28.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Box(
            modifier = Modifier.size(42.dp).clip(RoundedCornerShape(15.dp))
                .background(colors.accent.copy(alpha = 0.1f)),
            contentAlignment = Alignment.Center,
        ) {
            Icon(Icons.Rounded.AutoAwesome, null, tint = colors.accent, modifier = Modifier.size(20.dp))
        }
        Spacer(Modifier.height(10.dp))
        Text("开始分析", color = colors.text, fontSize = 16.sp, fontWeight = FontWeight.Bold)
        Text(
            "同一会话可以持续复盘多期开奖",
            color = colors.textDim,
            fontSize = 9.5.sp,
            modifier = Modifier.padding(top = 3.dp, bottom = 13.dp),
        )
        persona.quickPrompts.take(3).forEach { prompt ->
            Surface(
                modifier = Modifier.fillMaxWidth().padding(vertical = 3.dp)
                    .clickable(enabled = enabled) { onPrompt(prompt) },
                shape = RoundedCornerShape(14.dp),
                color = Color.White.copy(alpha = 0.025f),
            ) {
                Text(
                    prompt,
                    color = if (enabled) colors.textSoft else colors.textDim,
                    fontSize = 11.5.sp,
                    lineHeight = 17.sp,
                    modifier = Modifier.padding(horizontal = 13.dp, vertical = 10.dp),
                )
            }
        }
    }
}

@Composable
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

@Composable
private fun SystemEventChip(text: String) {
    val colors = LocalTianjiColors.current
    Box(Modifier.fillMaxWidth(), contentAlignment = Alignment.Center) {
        Text(
            text,
            color = colors.textDim,
            fontSize = 10.sp,
            lineHeight = 15.sp,
            modifier = Modifier.widthIn(max = 350.dp).clip(RoundedCornerShape(12.dp))
                .background(Color.White.copy(alpha = 0.03f))
                .padding(horizontal = 11.dp, vertical = 7.dp),
        )
    }
}

@Composable
private fun StreamingStatus(progress: String, onCancel: () -> Unit) {
    val colors = LocalTianjiColors.current
    Row(
        modifier = Modifier.fillMaxWidth().clip(RoundedCornerShape(15.dp))
            .background(colors.accent.copy(alpha = 0.055f))
            .padding(horizontal = 12.dp, vertical = 9.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        CircularProgressIndicator(modifier = Modifier.size(15.dp), color = colors.accent, strokeWidth = 2.dp)
        Spacer(Modifier.width(9.dp))
        Text(
            progress.ifBlank { "正在继续生成…" },
            color = colors.textDim,
            fontSize = 10.5.sp,
            modifier = Modifier.weight(1f),
        )
        IconButton(onClick = onCancel, modifier = Modifier.size(32.dp)) {
            Icon(Icons.Rounded.StopCircle, "停止", tint = colors.amber, modifier = Modifier.size(20.dp))
        }
    }
}

@Composable
private fun ChatPredictionCard(record: AiChatCandidateRecord) {
    val colors = LocalTianjiColors.current
    val hit = record.actualNumber?.let { it in record.prediction.top6 }
    Surface(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(15.dp),
        color = colors.accent.copy(alpha = 0.055f),
    ) {
        Column(Modifier.padding(horizontal = 12.dp, vertical = 10.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(
                    "第${record.prediction.position + 1}名",
                    color = colors.accent,
                    fontSize = 11.sp,
                    fontWeight = FontWeight.Bold,
                )
                Text(
                    " · 目标期${record.targetPeriod}",
                    color = colors.textDim,
                    fontSize = 8.5.sp,
                    modifier = Modifier.weight(1f),
                )
                hit?.let {
                    Text(
                        if (it) "命中" else "未中",
                        color = if (it) colors.green else colors.amber,
                        fontSize = 8.5.sp,
                        fontWeight = FontWeight.Bold,
                    )
                }
            }
            Spacer(Modifier.height(9.dp))
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                record.prediction.top6.forEach { number -> NumberBall(number) }
            }
            record.actualNumber?.let { actual ->
                Text(
                    "实际号码 $actual · 仅用于本对话复盘",
                    color = colors.textDim,
                    fontSize = 8.5.sp,
                    modifier = Modifier.padding(top = 7.dp),
                )
            }
        }
    }
}

@Composable
private fun NumberBall(number: Int) {
    val colors = LocalTianjiColors.current
    Box(
        modifier = Modifier.size(30.dp).clip(CircleShape)
            .background(colors.accent.copy(alpha = 0.13f)),
        contentAlignment = Alignment.Center,
    ) {
        Text(number.toString(), color = colors.text, fontSize = 11.5.sp, fontWeight = FontWeight.Bold)
    }
}

@Composable
private fun ChatComposer(
    input: String,
    onInput: (String) -> Unit,
    enabled: Boolean,
    isRunning: Boolean,
    placeholder: String,
    onSend: () -> Unit,
    onStop: () -> Unit,
) {
    val colors = LocalTianjiColors.current
    Surface(
        modifier = Modifier.fillMaxWidth().padding(bottom = 7.dp),
        shape = RoundedCornerShape(20.dp),
        color = Color.White.copy(alpha = 0.04f),
    ) {
        Row(
            modifier = Modifier.padding(start = 14.dp, top = 8.dp, end = 6.dp, bottom = 7.dp),
            verticalAlignment = Alignment.Bottom,
        ) {
            BasicTextField(
                value = input,
                onValueChange = onInput,
                enabled = enabled,
                modifier = Modifier.weight(1f).padding(bottom = 4.dp),
                textStyle = TextStyle(color = colors.text, fontSize = 13.sp, lineHeight = 19.sp),
                cursorBrush = SolidColor(colors.accent),
                minLines = 1,
                maxLines = 4,
                keyboardOptions = KeyboardOptions(imeAction = ImeAction.Send),
                keyboardActions = KeyboardActions(onSend = { if (enabled && input.isNotBlank()) onSend() }),
                decorationBox = { inner ->
                    Box {
                        if (input.isBlank()) {
                            Text(
                                placeholder,
                                color = colors.textDim,
                                fontSize = 10.5.sp,
                                lineHeight = 16.sp,
                                maxLines = 2,
                                overflow = TextOverflow.Ellipsis,
                            )
                        }
                        inner()
                    }
                },
            )
            Spacer(Modifier.width(7.dp))
            Button(
                onClick = if (isRunning) onStop else onSend,
                enabled = isRunning || (enabled && input.isNotBlank()),
                modifier = Modifier.size(40.dp),
                shape = CircleShape,
                contentPadding = PaddingValues(0.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = if (isRunning) colors.amber else colors.accent,
                ),
            ) {
                Icon(
                    if (isRunning) Icons.Rounded.StopCircle else Icons.AutoMirrored.Rounded.Send,
                    if (isRunning) "停止" else "发送",
                    tint = Color.White,
                    modifier = Modifier.size(19.dp),
                )
            }
        }
    }
}

@Composable
private fun ConversationHistoryDialog(
    items: List<AiChatArchiveSummary>,
    currentId: String,
    onOpen: (String) -> Unit,
    onDismiss: () -> Unit,
) {
    val colors = LocalTianjiColors.current
    Dialog(onDismissRequest = onDismiss) {
        Surface(
            modifier = Modifier.fillMaxWidth().heightIn(max = 660.dp),
            shape = RoundedCornerShape(26.dp),
            color = colors.page,
            border = androidx.compose.foundation.BorderStroke(1.dp, colors.line),
        ) {
            Column(Modifier.padding(18.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Column(Modifier.weight(1f)) {
                        Text("对话历史", color = colors.text, fontSize = 19.sp, fontWeight = FontWeight.Bold)
                        Text("重新打开后可继续聊天", color = colors.textDim, fontSize = 10.5.sp)
                    }
                    IconButton(onClick = onDismiss) { Icon(Icons.Rounded.Close, "关闭", tint = colors.textSoft) }
                }
                Spacer(Modifier.height(10.dp))
                LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    items(items.sortedByDescending(AiChatArchiveSummary::updatedAtEpochMs), key = AiChatArchiveSummary::id) { item ->
                        Surface(
                            modifier = Modifier.fillMaxWidth().clickable { onOpen(item.id) },
                            shape = RoundedCornerShape(17.dp),
                            color = if (item.id == currentId) colors.accent.copy(alpha = 0.09f)
                                else Color.White.copy(alpha = 0.03f),
                        ) {
                            Column(Modifier.padding(13.dp)) {
                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    Text(
                                        item.title,
                                        color = colors.text,
                                        fontSize = 13.5.sp,
                                        fontWeight = FontWeight.SemiBold,
                                        maxLines = 1,
                                        overflow = TextOverflow.Ellipsis,
                                        modifier = Modifier.weight(1f),
                                    )
                                    Text(formatTime(item.updatedAtEpochMs), color = colors.textDim, fontSize = 9.sp)
                                }
                                Text(
                                    "${item.model} · ${item.messageCount}条 · 目标期${item.targetPeriod.ifBlank { "待同步" }}",
                                    color = colors.accent,
                                    fontSize = 9.5.sp,
                                    modifier = Modifier.padding(top = 4.dp),
                                )
                                if (item.preview.isNotBlank()) {
                                    Text(
                                        item.preview,
                                        color = colors.textDim,
                                        fontSize = 10.5.sp,
                                        lineHeight = 15.sp,
                                        maxLines = 2,
                                        overflow = TextOverflow.Ellipsis,
                                        modifier = Modifier.padding(top = 5.dp),
                                    )
                                }
                            }
                        }
                    }
                    if (items.isEmpty()) {
                        item { Text("暂无对话", color = colors.textDim, modifier = Modifier.padding(24.dp)) }
                    }
                }
            }
        }
    }
}

@Composable
private fun NewConversationDialog(
    hasHistory: Boolean,
    onBlank: () -> Unit,
    onContinue: () -> Unit,
    onDismiss: () -> Unit,
) {
    val colors = LocalTianjiColors.current
    Dialog(onDismissRequest = onDismiss) {
        Surface(
            shape = RoundedCornerShape(26.dp),
            color = colors.page,
            border = androidx.compose.foundation.BorderStroke(1.dp, colors.line),
        ) {
            Column(Modifier.padding(20.dp)) {
                Text("新建对话", color = colors.text, fontSize = 19.sp, fontWeight = FontWeight.Bold)
                Text(
                    "空白开始，或只继承策略摘要与复盘结论。",
                    color = colors.textDim,
                    fontSize = 10.5.sp,
                    modifier = Modifier.padding(top = 5.dp, bottom = 14.dp),
                )
                ChoiceCard("空白新对话", "不带入任何旧上下文", onBlank)
                Spacer(Modifier.height(9.dp))
                ChoiceCard(
                    "继承策略继续",
                    "保留明确调整要求、近期候选与开奖复盘",
                    onContinue,
                    enabled = hasHistory,
                )
            }
        }
    }
}

@Composable
private fun ChoiceCard(title: String, subtitle: String, onClick: () -> Unit, enabled: Boolean = true) {
    val colors = LocalTianjiColors.current
    Surface(
        modifier = Modifier.fillMaxWidth().clickable(enabled = enabled, onClick = onClick),
        shape = RoundedCornerShape(17.dp),
        color = colors.accent.copy(alpha = if (enabled) 0.075f else 0.025f),
    ) {
        Column(Modifier.padding(14.dp)) {
            Text(
                title,
                color = if (enabled) colors.text else colors.textDim,
                fontSize = 13.5.sp,
                fontWeight = FontWeight.SemiBold,
            )
            Text(
                subtitle,
                color = colors.textDim,
                fontSize = 10.sp,
                lineHeight = 15.sp,
                modifier = Modifier.padding(top = 4.dp),
            )
        }
    }
}

private fun formatTime(epochMs: Long): String =
    SimpleDateFormat("MM-dd HH:mm", Locale.getDefault()).format(Date(epochMs))