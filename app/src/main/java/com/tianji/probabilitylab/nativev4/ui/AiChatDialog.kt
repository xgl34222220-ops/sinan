package com.tianji.probabilitylab.nativev4.ui

import android.speech.tts.TextToSpeech
import android.widget.Toast
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.animateContentSize
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInVertically
import androidx.compose.animation.slideOutVertically
import androidx.compose.foundation.BorderStroke
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
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.text.selection.SelectionContainer
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.rounded.ArrowBack
import androidx.compose.material.icons.automirrored.rounded.Send
import androidx.compose.material.icons.rounded.Add
import androidx.compose.material.icons.rounded.AutoAwesome
import androidx.compose.material.icons.rounded.ChatBubble
import androidx.compose.material.icons.rounded.Close
import androidx.compose.material.icons.rounded.ContentCopy
import androidx.compose.material.icons.rounded.DeleteSweep
import androidx.compose.material.icons.rounded.History
import androidx.compose.material.icons.rounded.KeyboardArrowDown
import androidx.compose.material.icons.rounded.KeyboardArrowUp
import androidx.compose.material.icons.rounded.MoreVert
import androidx.compose.material.icons.rounded.Refresh
import androidx.compose.material.icons.rounded.Replay
import androidx.compose.material.icons.rounded.StopCircle
import androidx.compose.material.icons.rounded.Tune
import androidx.compose.material.icons.rounded.VolumeUp
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.derivedStateOf
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.AnnotatedString
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
import com.tianji.probabilitylab.nativev4.ai.AiJudgementMode
import com.tianji.probabilitylab.nativev4.model.DrawSnapshot
import com.tianji.probabilitylab.nativev4.model.ForecastReport
import com.tianji.probabilitylab.nativev4.ui.theme.LocalTianjiColors
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import kotlinx.coroutines.launch

@Composable
fun AiChatFloatingButton(
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val colors = LocalTianjiColors.current
    Surface(
        modifier = modifier
            .height(52.dp)
            .shadow(
                elevation = if (colors.isOled) 0.dp else 10.dp,
                shape = RoundedCornerShape(19.dp),
                ambientColor = colors.accent.copy(alpha = 0.25f),
                spotColor = colors.accent.copy(alpha = 0.25f),
            )
            .clickable(onClick = onClick),
        shape = RoundedCornerShape(19.dp),
        color = colors.accent,
        contentColor = Color.White,
        border = BorderStroke(1.dp, Color.White.copy(alpha = 0.16f)),
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 15.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Icon(
                imageVector = Icons.Rounded.ChatBubble,
                contentDescription = "打开分析对话",
                modifier = Modifier.size(20.dp),
            )
            Spacer(Modifier.width(8.dp))
            Text(
                text = "AI 对话",
                fontSize = 12.sp,
                fontWeight = FontWeight.Bold,
            )
        }
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
    val context = LocalContext.current
    val clipboard = LocalClipboardManager.current
    val scope = rememberCoroutineScope()

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
    val session = controller.session
    val selectedConfig = completeConfigs.firstOrNull { it.id == session.profileId }
        ?: completeConfigs.firstOrNull()

    fun modelOptions(config: AiConfig?): List<String> = buildList {
        if (config != null) {
            config.model.trim().takeIf(String::isNotBlank)?.let(::add)
            addAll(modelCatalogs[config.id].orEmpty())
            addAll(config.provider.fallbackModels)
        }
        if (session.profileId == config?.id) {
            session.model.takeIf(String::isNotBlank)?.let(::add)
        }
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
    var followLatest by rememberSaveable { mutableStateOf(true) }

    val listState = rememberLazyListState()
    val isNearBottom by remember {
        derivedStateOf {
            val layout = listState.layoutInfo
            val lastVisible = layout.visibleItemsInfo.lastOrNull()?.index ?: -1
            layout.totalItemsCount == 0 || lastVisible >= layout.totalItemsCount - 2
        }
    }

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
        modelCatalogs.entries.sortedBy { it.key }
            .joinToString("|") { it.value.joinToString(",") }

    LaunchedEffect(signature, lotteryKey, targetPeriod, snapshot?.latest?.period) {
        openContext(selectedConfig, selectedModel)
    }

    LaunchedEffect(listState.isScrollInProgress, isNearBottom) {
        if (listState.isScrollInProgress) followLatest = isNearBottom
    }

    LaunchedEffect(session.messages.size, session.candidates.size) {
        val last = listState.layoutInfo.totalItemsCount - 1
        if (last >= 0 && (followLatest || session.messages.lastOrNull()?.role == AiChatRole.USER)) {
            followLatest = true
            listState.animateScrollToItem(last)
        }
    }

    LaunchedEffect(
        session.messages.lastOrNull()?.content?.length,
        session.isRunning,
        session.progress,
    ) {
        val last = listState.layoutInfo.totalItemsCount - 1
        if (last >= 0 && followLatest && isNearBottom) {
            listState.scrollToItem(last)
        }
    }

    fun submit(value: String) {
        val config = completeConfigs.firstOrNull { it.id == controller.session.profileId }
            ?: selectedConfig
        val activeSnapshot = snapshot
        val activeReport = report
        val question = value.trim()
        if (
            config == null ||
            activeSnapshot == null ||
            activeReport == null ||
            question.isBlank() ||
            controller.session.isRunning
        ) {
            return
        }
        input = ""
        followLatest = true
        controller.send(
            config = config.copy(
                model = controller.session.model.ifBlank { selectedModel },
            ),
            snapshot = activeSnapshot,
            report = activeReport,
            question = question,
        )
    }

    fun repeatMessage(message: AiChatMessage) {
        if (controller.session.isRunning) return
        val prompt = repeatPromptFor(controller.session.messages, message.id)
        if (prompt.isNullOrBlank()) {
            Toast.makeText(context, "找不到这条回答对应的问题", Toast.LENGTH_SHORT).show()
            return
        }
        submit(prompt)
    }

    val ready = selectedConfig != null && snapshot != null && report != null
    val persona = AiChatPersona.fromId(session.personaId)

    Dialog(
        onDismissRequest = onDismiss,
        properties = DialogProperties(
            usePlatformDefaultWidth = false,
            decorFitsSystemWindows = false,
        ),
    ) {
        Surface(
            modifier = Modifier
                .fillMaxSize()
                .windowInsetsPadding(WindowInsets.systemBars),
            color = colors.page,
        ) {
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .background(
                        Brush.verticalGradient(
                            listOf(
                                colors.page,
                                colors.pageSoft,
                                colors.page,
                            ),
                        ),
                    ),
            ) {
                Column(
                    modifier = Modifier
                        .fillMaxSize()
                        .imePadding(),
                ) {
                    ChatTopBar(
                        session = session,
                        selectedModel = selectedModel,
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

                    SessionControlCard(
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
                        onJudgementMode = controller::selectJudgementMode,
                    )

                    val candidatesByMessage = session.candidates.groupBy(
                        AiChatCandidateRecord::messageId,
                    )

                    Box(
                        modifier = Modifier
                            .weight(1f)
                            .fillMaxWidth(),
                    ) {
                        LazyColumn(
                            state = listState,
                            modifier = Modifier.fillMaxSize(),
                            contentPadding = PaddingValues(
                                start = 14.dp,
                                end = 14.dp,
                                top = 14.dp,
                                bottom = 18.dp,
                            ),
                            verticalArrangement = Arrangement.spacedBy(
                                13.dp,
                                Alignment.Bottom,
                            ),
                        ) {
                            if (session.messages.isEmpty()) {
                                item("welcome") {
                                    WelcomePanel(
                                        persona = persona,
                                        enabled = ready,
                                        onPrompt = ::submit,
                                    )
                                }
                            }

                            items(
                                items = session.messages,
                                key = AiChatMessage::id,
                            ) { message ->
                                ChatMessageBubble(
                                    message = message,
                                    model = selectedModel,
                                    isStreaming = message.id == session.streamingMessageId &&
                                        session.isRunning,
                                    canRepeat = !session.isRunning,
                                    onCopy = { copyMessage(message) },
                                    onSpeak = { speakMessage(message) },
                                    onRepeat = { repeatMessage(message) },
                                )
                                candidatesByMessage[message.id].orEmpty().forEach { record ->
                                    Spacer(Modifier.height(8.dp))
                                    ChatPredictionCard(record)
                                }
                            }

                            val detached = session.candidates.filter { it.messageId.isBlank() }
                            items(
                                items = detached,
                                key = AiChatCandidateRecord::id,
                            ) { record ->
                                ChatPredictionCard(record)
                            }

                            val streamingMessage = session.messages.firstOrNull {
                                it.id == session.streamingMessageId
                            }
                            if (session.isRunning && streamingMessage?.content.isNullOrBlank()) {
                                item("running") {
                                    StreamingStatus(
                                        progress = session.progress,
                                        onCancel = controller::cancel,
                                    )
                                }
                            }

                            session.rolloverNotice?.let { notice ->
                                item("rollover") { SystemEventChip(notice) }
                            }

                            session.error?.let { error ->
                                item("error") {
                                    ErrorMessage(text = error)
                                }
                            }
                        }

                        AnimatedVisibility(
                            visible = !isNearBottom &&
                                listState.layoutInfo.totalItemsCount > 0,
                            modifier = Modifier
                                .align(Alignment.BottomEnd)
                                .padding(end = 18.dp, bottom = 14.dp),
                            enter = fadeIn() + slideInVertically { it / 2 },
                            exit = fadeOut() + slideOutVertically { it / 2 },
                        ) {
                            Surface(
                                modifier = Modifier
                                    .size(42.dp)
                                    .shadow(
                                        elevation = 6.dp,
                                        shape = CircleShape,
                                        ambientColor = Color.Black.copy(alpha = 0.20f),
                                        spotColor = Color.Black.copy(alpha = 0.20f),
                                    )
                                    .clickable {
                                        followLatest = true
                                        val last = listState.layoutInfo.totalItemsCount - 1
                                        if (last >= 0) {
                                            scope.launch { listState.animateScrollToItem(last) }
                                        }
                                    },
                                shape = CircleShape,
                                color = colors.surfaceStrong,
                                border = BorderStroke(1.dp, colors.lineStrong),
                            ) {
                                Box(contentAlignment = Alignment.Center) {
                                    Icon(
                                        imageVector = Icons.Rounded.KeyboardArrowDown,
                                        contentDescription = "回到底部",
                                        tint = colors.textSoft,
                                    )
                                }
                            }
                        }
                    }

                    ChatComposer(
                        input = input,
                        onInput = { input = it },
                        ready = ready,
                        isRunning = session.isRunning,
                        placeholder = persona.quickPrompts.firstOrNull()
                            ?: "继续追问，或告诉它上一期哪里需要调整",
                        suggestions = persona.quickPrompts.take(3),
                        onSuggestion = ::submit,
                        onSend = { submit(input) },
                        onStop = controller::cancel,
                    )
                }
            }
        }
    }

    if (showHistory) {
        ConversationHistoryDialog(
            items = controller.archives.filter {
                lotteryKey.isBlank() || it.lotteryKey == lotteryKey
            },
            currentId = session.archiveId,
            onOpen = {
                controller.openArchive(it)
                showHistory = false
            },
            onDismiss = { showHistory = false },
        )
    }

    if (showNewConversation) {
        NewConversationDialog(
            hasHistory = session.messages.isNotEmpty(),
            onBlank = {
                controller.newConversation(
                    selectedConfig?.id.orEmpty(),
                    selectedConfig?.displayName.orEmpty(),
                    selectedModel,
                    lotteryKey,
                    targetPeriod,
                    inheritStrategy = false,
                )
                showNewConversation = false
            },
            onContinue = {
                controller.newConversation(
                    selectedConfig?.id.orEmpty(),
                    selectedConfig?.displayName.orEmpty(),
                    selectedModel,
                    lotteryKey,
                    targetPeriod,
                    inheritStrategy = true,
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
    selectedModel: String,
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
        modifier = Modifier
            .fillMaxWidth()
            .height(70.dp)
            .background(
                Brush.verticalGradient(
                    listOf(
                        colors.header,
                        colors.page.copy(alpha = 0.96f),
                    ),
                ),
            )
            .border(width = 0.5.dp, color = colors.line)
            .padding(horizontal = 8.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        IconButton(
            onClick = onClose,
            modifier = Modifier.size(42.dp),
        ) {
            Icon(
                imageVector = Icons.AutoMirrored.Rounded.ArrowBack,
                contentDescription = "返回",
                tint = colors.textSoft,
                modifier = Modifier.size(23.dp),
            )
        }

        Box(
            modifier = Modifier
                .size(42.dp)
                .shadow(
                    elevation = if (colors.isOled) 0.dp else 5.dp,
                    shape = RoundedCornerShape(15.dp),
                    ambientColor = colors.accent.copy(alpha = 0.20f),
                    spotColor = colors.accent.copy(alpha = 0.20f),
                )
                .clip(RoundedCornerShape(15.dp))
                .background(
                    Brush.linearGradient(
                        listOf(
                            colors.accent.copy(alpha = 0.24f),
                            colors.violet.copy(alpha = 0.16f),
                        ),
                    ),
                )
                .border(
                    width = 1.dp,
                    color = colors.accent.copy(alpha = 0.28f),
                    shape = RoundedCornerShape(15.dp),
                ),
            contentAlignment = Alignment.Center,
        ) {
            Icon(
                imageVector = Icons.Rounded.AutoAwesome,
                contentDescription = null,
                tint = colors.accent,
                modifier = Modifier.size(20.dp),
            )
        }

        Spacer(Modifier.width(10.dp))

        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = session.title.ifBlank { "新对话" },
                color = colors.text,
                fontSize = 16.sp,
                lineHeight = 21.sp,
                fontWeight = FontWeight.ExtraBold,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
            Surface(
                shape = CircleShape,
                color = colors.accent.copy(alpha = 0.09f),
            ) {
                Text(
                    text = selectedModel.ifBlank { "请选择模型" },
                    color = colors.accent,
                    fontSize = 9.5.sp,
                    lineHeight = 13.sp,
                    fontWeight = FontWeight.SemiBold,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                    modifier = Modifier.padding(horizontal = 7.dp, vertical = 2.dp),
                )
            }
        }

        ChatTopActionButton(
            icon = Icons.Rounded.History,
            description = "对话历史",
            enabled = !session.isRunning,
            onClick = onHistory,
        )
        Spacer(Modifier.width(5.dp))
        ChatTopActionButton(
            icon = Icons.Rounded.Add,
            description = "新建对话",
            enabled = !session.isRunning,
            onClick = onNew,
        )
        Spacer(Modifier.width(5.dp))
        Box {
            ChatTopActionButton(
                icon = Icons.Rounded.MoreVert,
                description = "更多",
                enabled = !session.isRunning,
                onClick = onMore,
            )
            DropdownMenu(
                expanded = moreExpanded,
                onDismissRequest = dismissMore,
            ) {
                DropdownMenuItem(
                    text = { Text("刷新开奖历史") },
                    leadingIcon = {
                        Icon(Icons.Rounded.Refresh, contentDescription = null)
                    },
                    onClick = {
                        dismissMore()
                        onRefresh()
                    },
                )
                DropdownMenuItem(
                    text = { Text("清空当前对话") },
                    leadingIcon = {
                        Icon(Icons.Rounded.DeleteSweep, contentDescription = null)
                    },
                    onClick = {
                        dismissMore()
                        onClear()
                    },
                )
                DropdownMenuItem(
                    text = { Text("删除当前会话") },
                    leadingIcon = {
                        Icon(Icons.Rounded.Close, contentDescription = null)
                    },
                    onClick = {
                        dismissMore()
                        onDelete()
                    },
                )
            }
        }
    }
}

@Composable
private fun ChatTopActionButton(
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    description: String,
    enabled: Boolean,
    onClick: () -> Unit,
) {
    val colors = LocalTianjiColors.current
    Surface(
        modifier = Modifier
            .size(38.dp)
            .shadow(
                elevation = if (colors.isOled) 0.dp else 2.dp,
                shape = RoundedCornerShape(13.dp),
                ambientColor = Color.Black.copy(alpha = 0.12f),
                spotColor = Color.Black.copy(alpha = 0.12f),
            )
            .clickable(enabled = enabled, onClick = onClick),
        shape = RoundedCornerShape(13.dp),
        color = colors.glass,
        border = BorderStroke(1.dp, colors.lineStrong),
    ) {
        Box(contentAlignment = Alignment.Center) {
            Icon(
                imageVector = icon,
                contentDescription = description,
                tint = if (enabled) colors.textSoft else colors.textDim.copy(alpha = 0.35f),
                modifier = Modifier.size(19.dp),
            )
        }
    }
}

@Composable
private fun SessionControlCard(
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
    onJudgementMode: (AiJudgementMode) -> Unit,
) {
    val colors = LocalTianjiColors.current
    val persona = AiChatPersona.fromId(session.personaId)
    Surface(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 14.dp, vertical = 9.dp)
            .shadow(
                elevation = if (colors.isOled) 0.dp else 3.dp,
                shape = RoundedCornerShape(21.dp),
                ambientColor = Color.Black.copy(alpha = 0.10f),
                spotColor = Color.Black.copy(alpha = 0.10f),
            )
            .animateContentSize(),
        shape = RoundedCornerShape(21.dp),
        color = colors.glass,
        border = BorderStroke(1.dp, colors.lineStrong),
    ) {
        Column {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .clickable(onClick = onToggle)
                    .padding(horizontal = 13.dp, vertical = 11.dp),
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Box(
                        modifier = Modifier
                            .size(38.dp)
                            .clip(RoundedCornerShape(13.dp))
                            .background(
                                Brush.linearGradient(
                                    listOf(
                                        colors.accent.copy(alpha = 0.20f),
                                        colors.violet.copy(alpha = 0.12f),
                                    ),
                                ),
                            )
                            .border(
                                1.dp,
                                colors.accent.copy(alpha = 0.20f),
                                RoundedCornerShape(13.dp),
                            ),
                        contentAlignment = Alignment.Center,
                    ) {
                        Icon(
                            imageVector = Icons.Rounded.Tune,
                            contentDescription = null,
                            tint = colors.accent,
                            modifier = Modifier.size(19.dp),
                        )
                    }
                    Spacer(Modifier.width(10.dp))
                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            text = selectedModel.ifBlank { "选择模型" },
                            color = colors.text,
                            fontSize = 12.5.sp,
                            lineHeight = 17.sp,
                            fontWeight = FontWeight.Bold,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis,
                        )
                        Text(
                            text = "${session.judgementMode.label} · ${persona.displayName}",
                            color = colors.textDim,
                            fontSize = 9.5.sp,
                            lineHeight = 14.sp,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis,
                        )
                    }
                    Icon(
                        imageVector = if (expanded) {
                            Icons.Rounded.KeyboardArrowUp
                        } else {
                            Icons.Rounded.KeyboardArrowDown
                        },
                        contentDescription = if (expanded) "收起" else "展开",
                        tint = colors.textDim,
                        modifier = Modifier.size(20.dp),
                    )
                }

                Spacer(Modifier.height(9.dp))

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Surface(
                        shape = CircleShape,
                        color = colors.surfaceSoft,
                        border = BorderStroke(1.dp, colors.line),
                    ) {
                        Text(
                            text = report?.targetPeriod?.let { "目标期  $it" } ?: "目标期待同步",
                            color = colors.textSoft,
                            fontSize = 9.5.sp,
                            fontWeight = FontWeight.SemiBold,
                            maxLines = 1,
                            modifier = Modifier.padding(horizontal = 10.dp, vertical = 5.dp),
                        )
                    }
                    Spacer(Modifier.width(7.dp))
                    Surface(
                        shape = CircleShape,
                        color = colors.accent.copy(alpha = 0.08f),
                    ) {
                        Text(
                            text = selectedConfig?.displayName ?: "未配置",
                            color = colors.accent,
                            fontSize = 9.5.sp,
                            fontWeight = FontWeight.SemiBold,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis,
                            modifier = Modifier
                                .widthIn(max = 142.dp)
                                .padding(horizontal = 9.dp, vertical = 5.dp),
                        )
                    }
                    Spacer(Modifier.weight(1f))
                    Text(
                        text = "上下文",
                        color = colors.textDim,
                        fontSize = 9.sp,
                    )
                    Spacer(Modifier.width(5.dp))
                    ContextUsagePill(session.contextUsagePercent)
                }
            }

            AnimatedVisibility(visible = expanded) {
                Column {
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(1.dp)
                            .background(colors.line),
                    )
                    Column(
                        modifier = Modifier.padding(
                            start = 13.dp,
                            end = 13.dp,
                            top = 6.dp,
                            bottom = 12.dp,
                        ),
                    ) {
                        SelectorRow(
                            label = "配置",
                            value = selectedConfig?.displayName ?: "未配置",
                            options = configs.map { it.id to it.displayName },
                            selectedKey = selectedConfig?.id.orEmpty(),
                            onSelect = { id ->
                                configs.firstOrNull { it.id == id }?.let(onConfig)
                            },
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
                        SelectorRow(
                            label = "判断",
                            value = session.judgementMode.label,
                            options = AiJudgementMode.entries.map { it.name to it.label },
                            selectedKey = session.judgementMode.name,
                            onSelect = { value ->
                                onJudgementMode(AiJudgementMode.fromId(value))
                            },
                        )

                        val ready = snapshot != null && report != null && selectedConfig != null
                        val learning = session.learningProfile
                        Surface(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(top = 7.dp),
                            shape = RoundedCornerShape(15.dp),
                            color = colors.surfaceSoft,
                            border = BorderStroke(1.dp, colors.line),
                        ) {
                            Column(
                                modifier = Modifier.padding(horizontal = 12.dp, vertical = 10.dp),
                            ) {
                                Text(
                                    text = if (ready) {
                                        "${snapshot!!.history.takeLast(120).size} 期真实接口历史已准备"
                                    } else {
                                        "请先准备开奖历史和完整 AI 配置"
                                    },
                                    color = if (ready) colors.green else colors.amber,
                                    fontSize = 10.sp,
                                    lineHeight = 15.sp,
                                    fontWeight = FontWeight.SemiBold,
                                )
                                Spacer(Modifier.height(4.dp))
                                Text(
                                    text = "持续学习 ${learning.settled} 期 · 六码 " +
                                        "${(learning.top6Rate * 100).toInt()}% · 连续未中 " +
                                        "${learning.missStreak} 期",
                                    color = if (learning.missStreak >= 3) {
                                        colors.amber
                                    } else {
                                        colors.textSoft
                                    },
                                    fontSize = 10.sp,
                                    lineHeight = 15.sp,
                                )
                                if (learning.lastChange.isNotBlank()) {
                                    Spacer(Modifier.height(3.dp))
                                    Text(
                                        text = learning.lastChange,
                                        color = colors.textDim,
                                        fontSize = 10.sp,
                                        lineHeight = 15.sp,
                                    )
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun ContextUsagePill(percent: Int) {
    val colors = LocalTianjiColors.current
    val tint = when {
        percent >= 80 -> colors.amber
        percent >= 55 -> colors.accent
        else -> colors.green
    }
    Surface(
        shape = RoundedCornerShape(10.dp),
        color = tint.copy(alpha = 0.08f),
    ) {
        Text(
            text = "${percent.coerceIn(0, 100)}%",
            color = tint,
            fontSize = 9.sp,
            fontWeight = FontWeight.Bold,
            modifier = Modifier.padding(horizontal = 7.dp, vertical = 5.dp),
        )
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
            modifier = Modifier
                .fillMaxWidth()
                .clickable(enabled = options.isNotEmpty()) { expanded = true }
                .padding(vertical = 10.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(
                text = label,
                color = colors.textDim,
                fontSize = 11.sp,
                modifier = Modifier.width(54.dp),
            )
            Text(
                text = value,
                color = colors.textSoft,
                fontSize = 12.sp,
                lineHeight = 17.sp,
                fontWeight = FontWeight.Medium,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
                modifier = Modifier.weight(1f),
            )
            Icon(
                imageVector = Icons.Rounded.KeyboardArrowDown,
                contentDescription = null,
                tint = colors.textDim,
                modifier = Modifier.size(18.dp),
            )
        }
        DropdownMenu(
            expanded = expanded,
            onDismissRequest = { expanded = false },
        ) {
            options.forEach { (key, text) ->
                DropdownMenuItem(
                    text = {
                        Text(
                            text = text,
                            fontWeight = if (key == selectedKey) {
                                FontWeight.Bold
                            } else {
                                FontWeight.Normal
                            },
                        )
                    },
                    onClick = {
                        expanded = false
                        onSelect(key)
                    },
                )
            }
        }
    }
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
            .padding(top = 18.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Box(
            modifier = Modifier
                .size(54.dp)
                .clip(RoundedCornerShape(19.dp))
                .background(
                    Brush.linearGradient(
                        listOf(
                            colors.accent.copy(alpha = 0.18f),
                            colors.accentSoft,
                        ),
                    ),
                )
                .border(
                    width = 1.dp,
                    color = colors.accent.copy(alpha = 0.20f),
                    shape = RoundedCornerShape(19.dp),
                ),
            contentAlignment = Alignment.Center,
        ) {
            Icon(
                imageVector = Icons.Rounded.AutoAwesome,
                contentDescription = null,
                tint = colors.accent,
                modifier = Modifier.size(25.dp),
            )
        }
        Spacer(Modifier.height(13.dp))
        Text(
            text = "和天机一起分析",
            color = colors.text,
            fontSize = 19.sp,
            lineHeight = 25.sp,
            fontWeight = FontWeight.ExtraBold,
        )
        Text(
            text = "基于真实开奖历史独立分析，并持续记录前向结果",
            color = colors.textDim,
            fontSize = 11.sp,
            lineHeight = 17.sp,
            modifier = Modifier.padding(top = 5.dp, bottom = 17.dp),
        )

        persona.quickPrompts.take(3).forEach { prompt ->
            Surface(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(vertical = 4.dp)
                    .clickable(enabled = enabled) { onPrompt(prompt) },
                shape = RoundedCornerShape(17.dp),
                color = colors.glass,
                border = BorderStroke(1.dp, colors.line),
            ) {
                Row(
                    modifier = Modifier.padding(horizontal = 14.dp, vertical = 12.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Icon(
                        imageVector = Icons.Rounded.AutoAwesome,
                        contentDescription = null,
                        tint = if (enabled) colors.accent else colors.textDim,
                        modifier = Modifier.size(17.dp),
                    )
                    Spacer(Modifier.width(10.dp))
                    Text(
                        text = prompt,
                        color = if (enabled) colors.textSoft else colors.textDim,
                        fontSize = 12.sp,
                        lineHeight = 18.sp,
                        modifier = Modifier.weight(1f),
                    )
                }
            }
        }

        if (!enabled) {
            Text(
                text = "请先同步开奖数据并配置可用的 AI 模型",
                color = colors.amber,
                fontSize = 10.sp,
                lineHeight = 15.sp,
                modifier = Modifier.padding(top = 12.dp),
            )
        }
    }
}

@Composable
private fun ChatMessageBubble(
    message: AiChatMessage,
    model: String,
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
        Column(
            modifier = Modifier.fillMaxWidth(),
            horizontalAlignment = Alignment.End,
        ) {
            SelectionContainer {
                Text(
                    text = message.content,
                    color = colors.text,
                    fontSize = 13.sp,
                    lineHeight = 20.sp,
                    modifier = Modifier
                        .widthIn(max = 310.dp)
                        .clip(RoundedCornerShape(19.dp, 19.dp, 7.dp, 19.dp))
                        .background(
                            Brush.linearGradient(
                                listOf(
                                    colors.accent.copy(alpha = 0.22f),
                                    colors.accent.copy(alpha = 0.12f),
                                ),
                            ),
                        )
                        .border(
                            width = 1.dp,
                            color = colors.accent.copy(alpha = 0.16f),
                            shape = RoundedCornerShape(19.dp, 19.dp, 7.dp, 19.dp),
                        )
                        .padding(horizontal = 14.dp, vertical = 11.dp),
                )
            }
            ChatMessageActions(
                role = message.role,
                enabled = canRepeat,
                onCopy = onCopy,
                onSpeak = onSpeak,
                onRepeat = onRepeat,
                alignEnd = true,
            )
        }
        return
    }

    Surface(
        modifier = Modifier
            .fillMaxWidth()
            .animateContentSize(),
        shape = RoundedCornerShape(20.dp, 20.dp, 20.dp, 8.dp),
        color = colors.surface,
        border = BorderStroke(1.dp, colors.line),
    ) {
        Column(
            modifier = Modifier.padding(horizontal = 14.dp, vertical = 13.dp),
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Box(
                    modifier = Modifier
                        .size(28.dp)
                        .clip(RoundedCornerShape(10.dp))
                        .background(colors.accentSoft),
                    contentAlignment = Alignment.Center,
                ) {
                    Icon(
                        imageVector = Icons.Rounded.AutoAwesome,
                        contentDescription = null,
                        tint = colors.accent,
                        modifier = Modifier.size(15.dp),
                    )
                }
                Spacer(Modifier.width(8.dp))
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = "天机",
                        color = colors.text,
                        fontSize = 12.sp,
                        lineHeight = 16.sp,
                        fontWeight = FontWeight.Bold,
                    )
                    Text(
                        text = model.ifBlank { "AI 分析" },
                        color = colors.textDim,
                        fontSize = 9.sp,
                        lineHeight = 13.sp,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
                if (isStreaming) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        CircularProgressIndicator(
                            modifier = Modifier.size(13.dp),
                            color = colors.accent,
                            strokeWidth = 1.8.dp,
                        )
                        Spacer(Modifier.width(6.dp))
                        Text(
                            text = "生成中",
                            color = colors.accent,
                            fontSize = 9.sp,
                            fontWeight = FontWeight.Bold,
                        )
                    }
                } else {
                    message.latencyMs?.let {
                        Text(
                            text = "${it / 1_000.0}s",
                            color = colors.textDim,
                            fontSize = 9.sp,
                        )
                    }
                }
            }

            Spacer(Modifier.height(11.dp))

            val visible = when {
                message.content.isNotBlank() && isStreaming -> message.content + " ▍"
                message.content.isNotBlank() -> message.content
                isStreaming -> "正在整理分析结果…"
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
}

@Composable
private fun ChatMessageActions(
    role: AiChatRole,
    enabled: Boolean,
    onCopy: () -> Unit,
    onSpeak: () -> Unit,
    onRepeat: () -> Unit,
    alignEnd: Boolean = false,
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(top = 6.dp),
        horizontalArrangement = if (alignEnd) {
            Arrangement.End
        } else {
            Arrangement.Start
        },
        verticalAlignment = Alignment.CenterVertically,
    ) {
        ChatMessageAction(
            icon = Icons.Rounded.ContentCopy,
            label = "复制",
            enabled = true,
            onClick = onCopy,
        )
        Spacer(Modifier.width(4.dp))
        ChatMessageAction(
            icon = Icons.Rounded.VolumeUp,
            label = "朗读",
            enabled = true,
            onClick = onSpeak,
        )
        Spacer(Modifier.width(4.dp))
        ChatMessageAction(
            icon = Icons.Rounded.Replay,
            label = if (role == AiChatRole.USER) "再次提问" else "重新回答",
            enabled = enabled,
            onClick = onRepeat,
        )
    }
}

@Composable
private fun ChatMessageAction(
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    label: String,
    enabled: Boolean,
    onClick: () -> Unit,
) {
    val colors = LocalTianjiColors.current
    Surface(
        modifier = Modifier
            .clip(RoundedCornerShape(10.dp))
            .clickable(enabled = enabled, onClick = onClick),
        shape = RoundedCornerShape(10.dp),
        color = Color.Transparent,
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 7.dp, vertical = 5.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Icon(
                imageVector = icon,
                contentDescription = label,
                tint = if (enabled) colors.textDim else colors.textDim.copy(alpha = 0.35f),
                modifier = Modifier.size(14.dp),
            )
            Spacer(Modifier.width(4.dp))
            Text(
                text = label,
                color = if (enabled) colors.textDim else colors.textDim.copy(alpha = 0.35f),
                fontSize = 9.sp,
                fontWeight = FontWeight.Medium,
            )
        }
    }
}

@Composable
private fun SystemEventChip(text: String) {
    val colors = LocalTianjiColors.current
    Surface(
        modifier = Modifier
            .fillMaxWidth()
            .widthIn(max = 390.dp),
        shape = RoundedCornerShape(17.dp),
        color = colors.surfaceSoft,
        border = BorderStroke(1.dp, colors.lineStrong),
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 12.dp, vertical = 10.dp),
            verticalAlignment = Alignment.Top,
        ) {
            Box(
                modifier = Modifier
                    .size(30.dp)
                    .clip(RoundedCornerShape(10.dp))
                    .background(colors.accent.copy(alpha = 0.10f)),
                contentAlignment = Alignment.Center,
            ) {
                Icon(
                    imageVector = Icons.Rounded.Refresh,
                    contentDescription = null,
                    tint = colors.accent,
                    modifier = Modifier.size(16.dp),
                )
            }
            Spacer(Modifier.width(9.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = "期次更新",
                    color = colors.textSoft,
                    fontSize = 10.sp,
                    lineHeight = 14.sp,
                    fontWeight = FontWeight.Bold,
                )
                Spacer(Modifier.height(2.dp))
                Text(
                    text = text,
                    color = colors.textDim,
                    fontSize = 10.5.sp,
                    lineHeight = 16.sp,
                )
            }
        }
    }
}

@Composable
private fun StreamingStatus(
    progress: String,
    onCancel: () -> Unit,
) {
    val colors = LocalTianjiColors.current
    Surface(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(18.dp),
        color = colors.accent.copy(alpha = 0.06f),
        border = BorderStroke(1.dp, colors.accent.copy(alpha = 0.14f)),
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 13.dp, vertical = 11.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            CircularProgressIndicator(
                modifier = Modifier.size(16.dp),
                color = colors.accent,
                strokeWidth = 2.dp,
            )
            Spacer(Modifier.width(10.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = "天机正在分析",
                    color = colors.text,
                    fontSize = 11.sp,
                    fontWeight = FontWeight.SemiBold,
                )
                Text(
                    text = progress.ifBlank { "正在读取历史并整理回答…" },
                    color = colors.textDim,
                    fontSize = 10.sp,
                    lineHeight = 15.sp,
                )
            }
            IconButton(
                onClick = onCancel,
                modifier = Modifier.size(34.dp),
            ) {
                Icon(
                    imageVector = Icons.Rounded.StopCircle,
                    contentDescription = "停止",
                    tint = colors.amber,
                    modifier = Modifier.size(21.dp),
                )
            }
        }
    }
}

@Composable
private fun ErrorMessage(text: String) {
    val colors = LocalTianjiColors.current
    Surface(
        shape = RoundedCornerShape(17.dp),
        color = colors.red.copy(alpha = 0.08f),
        border = BorderStroke(1.dp, colors.red.copy(alpha = 0.16f)),
    ) {
        Text(
            text = text,
            color = colors.red,
            fontSize = 12.sp,
            lineHeight = 18.sp,
            modifier = Modifier.padding(horizontal = 14.dp, vertical = 11.dp),
        )
    }
}

@Composable
private fun ChatPredictionCard(record: AiChatCandidateRecord) {
    val colors = LocalTianjiColors.current
    val hit = record.actualNumber?.let { it in record.prediction.top6 }
    Surface(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(18.dp),
        color = colors.accent.copy(alpha = 0.055f),
        border = BorderStroke(1.dp, colors.accent.copy(alpha = 0.13f)),
    ) {
        Column(
            modifier = Modifier.padding(horizontal = 13.dp, vertical = 12.dp),
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = "第${record.prediction.position + 1}名候选",
                        color = colors.text,
                        fontSize = 12.sp,
                        fontWeight = FontWeight.Bold,
                    )
                    Text(
                        text = "目标期 ${record.targetPeriod}",
                        color = colors.textDim,
                        fontSize = 9.sp,
                    )
                }
                hit?.let {
                    Surface(
                        shape = CircleShape,
                        color = (if (it) colors.green else colors.amber).copy(alpha = 0.10f),
                    ) {
                        Text(
                            text = if (it) "命中" else "未中",
                            color = if (it) colors.green else colors.amber,
                            fontSize = 9.sp,
                            fontWeight = FontWeight.Bold,
                            modifier = Modifier.padding(horizontal = 9.dp, vertical = 5.dp),
                        )
                    }
                }
            }
            Spacer(Modifier.height(11.dp))
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceEvenly,
            ) {
                record.prediction.top6.forEach { number ->
                    LotteryBall(number = number, size = 32.dp)
                }
            }
            record.actualNumber?.let { actual ->
                Text(
                    text = "实际号码 $actual · 仅用于本对话复盘",
                    color = colors.textDim,
                    fontSize = 9.sp,
                    lineHeight = 14.sp,
                    modifier = Modifier.padding(top = 9.dp),
                )
            }
        }
    }
}

@Composable
private fun ChatComposer(
    input: String,
    onInput: (String) -> Unit,
    ready: Boolean,
    isRunning: Boolean,
    placeholder: String,
    suggestions: List<String>,
    onSuggestion: (String) -> Unit,
    onSend: () -> Unit,
    onStop: () -> Unit,
) {
    val colors = LocalTianjiColors.current
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .background(
                Brush.verticalGradient(
                    listOf(
                        colors.header.copy(alpha = 0.96f),
                        colors.page.copy(alpha = 0.99f),
                    ),
                ),
            )
            .border(width = 0.5.dp, color = colors.line)
            .padding(top = 8.dp, bottom = 8.dp),
    ) {
        if (input.isBlank() && !isRunning && ready && suggestions.isNotEmpty()) {
            LazyRow(
                contentPadding = PaddingValues(horizontal = 14.dp),
                horizontalArrangement = Arrangement.spacedBy(7.dp),
            ) {
                items(suggestions) { suggestion ->
                    Surface(
                        modifier = Modifier.clickable { onSuggestion(suggestion) },
                        shape = CircleShape,
                        color = colors.accent.copy(alpha = 0.07f),
                        border = BorderStroke(1.dp, colors.accent.copy(alpha = 0.15f)),
                    ) {
                        Text(
                            text = suggestion,
                            color = colors.textSoft,
                            fontSize = 10.sp,
                            fontWeight = FontWeight.Medium,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis,
                            modifier = Modifier
                                .widthIn(max = 220.dp)
                                .padding(horizontal = 11.dp, vertical = 7.dp),
                        )
                    }
                }
            }
            Spacer(Modifier.height(8.dp))
        }

        Surface(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 12.dp)
                .shadow(
                    elevation = if (colors.isOled) 0.dp else 7.dp,
                    shape = RoundedCornerShape(24.dp),
                    ambientColor = Color.Black.copy(alpha = 0.16f),
                    spotColor = Color.Black.copy(alpha = 0.16f),
                ),
            shape = RoundedCornerShape(24.dp),
            color = colors.glass,
            border = BorderStroke(1.dp, colors.lineStrong),
        ) {
            Row(
                modifier = Modifier.padding(
                    start = 15.dp,
                    top = 8.dp,
                    end = 7.dp,
                    bottom = 8.dp,
                ),
                verticalAlignment = Alignment.Bottom,
            ) {
                BasicTextField(
                    value = input,
                    onValueChange = onInput,
                    enabled = ready,
                    modifier = Modifier
                        .weight(1f)
                        .heightIn(min = 42.dp, max = 132.dp)
                        .padding(vertical = 9.dp),
                    textStyle = TextStyle(
                        color = colors.text,
                        fontSize = 13.sp,
                        lineHeight = 20.sp,
                    ),
                    cursorBrush = SolidColor(colors.accent),
                    minLines = 1,
                    maxLines = 6,
                    keyboardOptions = KeyboardOptions(imeAction = ImeAction.Send),
                    keyboardActions = KeyboardActions(
                        onSend = {
                            if (ready && !isRunning && input.isNotBlank()) onSend()
                        },
                    ),
                    decorationBox = { inner ->
                        Box(contentAlignment = Alignment.CenterStart) {
                            if (input.isBlank()) {
                                Text(
                                    text = when {
                                        !ready -> "请先同步数据并配置 AI"
                                        isRunning -> "可先输入下一条问题，生成结束后发送"
                                        else -> placeholder
                                    },
                                    color = colors.textDim,
                                    fontSize = 11.sp,
                                    lineHeight = 16.sp,
                                    maxLines = 2,
                                    overflow = TextOverflow.Ellipsis,
                                )
                            }
                            inner()
                        }
                    },
                )
                Spacer(Modifier.width(8.dp))
                val sendEnabled = isRunning || (ready && input.isNotBlank())
                Box(
                    modifier = Modifier
                        .size(44.dp)
                        .shadow(
                            elevation = if (sendEnabled && !colors.isOled) 5.dp else 0.dp,
                            shape = CircleShape,
                            ambientColor = colors.accent.copy(alpha = 0.24f),
                            spotColor = colors.accent.copy(alpha = 0.24f),
                        )
                        .clip(CircleShape)
                        .background(
                            when {
                                isRunning -> Brush.linearGradient(
                                    listOf(colors.amber, colors.red.copy(alpha = 0.85f)),
                                )
                                ready && input.isNotBlank() -> Brush.linearGradient(
                                    listOf(colors.accent, colors.violet),
                                )
                                else -> Brush.linearGradient(
                                    listOf(colors.surfaceSoft, colors.surfaceSoft),
                                )
                            },
                        )
                        .border(
                            1.dp,
                            if (sendEnabled) Color.White.copy(alpha = 0.16f) else colors.line,
                            CircleShape,
                        )
                        .clickable(
                            enabled = sendEnabled,
                            onClick = if (isRunning) onStop else onSend,
                        ),
                    contentAlignment = Alignment.Center,
                ) {
                    Icon(
                        imageVector = if (isRunning) {
                            Icons.Rounded.StopCircle
                        } else {
                            Icons.AutoMirrored.Rounded.Send
                        },
                        contentDescription = if (isRunning) "停止" else "发送",
                        tint = if (sendEnabled) Color.White else colors.textDim,
                        modifier = Modifier.size(21.dp),
                    )
                }
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
            modifier = Modifier
                .fillMaxWidth()
                .heightIn(max = 680.dp),
            shape = RoundedCornerShape(28.dp),
            color = colors.surfaceStrong,
            border = BorderStroke(1.dp, colors.lineStrong),
        ) {
            Column(modifier = Modifier.padding(18.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Box(
                        modifier = Modifier
                            .size(40.dp)
                            .clip(RoundedCornerShape(14.dp))
                            .background(colors.accentSoft),
                        contentAlignment = Alignment.Center,
                    ) {
                        Icon(
                            imageVector = Icons.Rounded.History,
                            contentDescription = null,
                            tint = colors.accent,
                            modifier = Modifier.size(20.dp),
                        )
                    }
                    Spacer(Modifier.width(11.dp))
                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            text = "对话历史",
                            color = colors.text,
                            fontSize = 19.sp,
                            fontWeight = FontWeight.Bold,
                        )
                        Text(
                            text = "打开后可继续追问和复盘",
                            color = colors.textDim,
                            fontSize = 10.sp,
                        )
                    }
                    IconButton(onClick = onDismiss) {
                        Icon(
                            imageVector = Icons.Rounded.Close,
                            contentDescription = "关闭",
                            tint = colors.textSoft,
                        )
                    }
                }

                Spacer(Modifier.height(14.dp))

                LazyColumn(
                    verticalArrangement = Arrangement.spacedBy(9.dp),
                ) {
                    items(
                        items = items.sortedByDescending(
                            AiChatArchiveSummary::updatedAtEpochMs,
                        ),
                        key = AiChatArchiveSummary::id,
                    ) { item ->
                        Surface(
                            modifier = Modifier
                                .fillMaxWidth()
                                .clickable { onOpen(item.id) },
                            shape = RoundedCornerShape(18.dp),
                            color = if (item.id == currentId) {
                                colors.accent.copy(alpha = 0.10f)
                            } else {
                                colors.surface
                            },
                            border = BorderStroke(
                                1.dp,
                                if (item.id == currentId) {
                                    colors.accent.copy(alpha = 0.20f)
                                } else {
                                    colors.line
                                },
                            ),
                        ) {
                            Column(
                                modifier = Modifier.padding(horizontal = 14.dp, vertical = 12.dp),
                            ) {
                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    Text(
                                        text = item.title,
                                        color = colors.text,
                                        fontSize = 13.sp,
                                        lineHeight = 18.sp,
                                        fontWeight = FontWeight.SemiBold,
                                        maxLines = 1,
                                        overflow = TextOverflow.Ellipsis,
                                        modifier = Modifier.weight(1f),
                                    )
                                    Text(
                                        text = formatTime(item.updatedAtEpochMs),
                                        color = colors.textDim,
                                        fontSize = 9.sp,
                                    )
                                }
                                Text(
                                    text = "${item.model} · ${item.messageCount} 条 · " +
                                        "目标期 ${item.targetPeriod.ifBlank { "待同步" }}",
                                    color = colors.accent,
                                    fontSize = 9.sp,
                                    lineHeight = 14.sp,
                                    modifier = Modifier.padding(top = 4.dp),
                                )
                                if (item.preview.isNotBlank()) {
                                    Text(
                                        text = item.preview,
                                        color = colors.textDim,
                                        fontSize = 10.sp,
                                        lineHeight = 15.sp,
                                        maxLines = 2,
                                        overflow = TextOverflow.Ellipsis,
                                        modifier = Modifier.padding(top = 6.dp),
                                    )
                                }
                            }
                        }
                    }

                    if (items.isEmpty()) {
                        item {
                            Text(
                                text = "暂无对话记录",
                                color = colors.textDim,
                                modifier = Modifier.padding(24.dp),
                            )
                        }
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
            shape = RoundedCornerShape(28.dp),
            color = colors.surfaceStrong,
            border = BorderStroke(1.dp, colors.lineStrong),
        ) {
            Column(modifier = Modifier.padding(20.dp)) {
                Text(
                    text = "新建对话",
                    color = colors.text,
                    fontSize = 20.sp,
                    fontWeight = FontWeight.Bold,
                )
                Text(
                    text = "选择从零开始，或只继承策略摘要与复盘结论。",
                    color = colors.textDim,
                    fontSize = 11.sp,
                    lineHeight = 17.sp,
                    modifier = Modifier.padding(top = 6.dp, bottom = 15.dp),
                )
                ChoiceCard(
                    title = "空白新对话",
                    subtitle = "不带入任何旧上下文",
                    onClick = onBlank,
                )
                Spacer(Modifier.height(9.dp))
                ChoiceCard(
                    title = "继承策略继续",
                    subtitle = "保留明确调整要求、近期候选与开奖复盘",
                    onClick = onContinue,
                    enabled = hasHistory,
                )
            }
        }
    }
}

@Composable
private fun ChoiceCard(
    title: String,
    subtitle: String,
    onClick: () -> Unit,
    enabled: Boolean = true,
) {
    val colors = LocalTianjiColors.current
    Surface(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(enabled = enabled, onClick = onClick),
        shape = RoundedCornerShape(18.dp),
        color = colors.accent.copy(alpha = if (enabled) 0.075f else 0.025f),
        border = BorderStroke(
            1.dp,
            if (enabled) colors.accent.copy(alpha = 0.13f) else colors.line,
        ),
    ) {
        Row(
            modifier = Modifier.padding(14.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Box(
                modifier = Modifier
                    .size(36.dp)
                    .clip(RoundedCornerShape(13.dp))
                    .background(colors.accentSoft),
                contentAlignment = Alignment.Center,
            ) {
                Icon(
                    imageVector = Icons.Rounded.Add,
                    contentDescription = null,
                    tint = if (enabled) colors.accent else colors.textDim,
                    modifier = Modifier.size(18.dp),
                )
            }
            Spacer(Modifier.width(11.dp))
            Column {
                Text(
                    text = title,
                    color = if (enabled) colors.text else colors.textDim,
                    fontSize = 13.sp,
                    fontWeight = FontWeight.SemiBold,
                )
                Text(
                    text = subtitle,
                    color = colors.textDim,
                    fontSize = 10.sp,
                    lineHeight = 15.sp,
                    modifier = Modifier.padding(top = 3.dp),
                )
            }
        }
    }
}

private fun formatTime(epochMs: Long): String =
    SimpleDateFormat("MM-dd HH:mm", Locale.getDefault()).format(Date(epochMs))
