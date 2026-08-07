package com.tianji.probabilitylab.nativev4.ui

import android.Manifest
import android.content.pm.PackageManager
import android.os.Build
import androidx.activity.compose.BackHandler
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.ContentTransform
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInHorizontally
import androidx.compose.animation.slideOutHorizontally
import androidx.compose.animation.togetherWith
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import com.tianji.probabilitylab.nativev4.TianjiRuntime
import com.tianji.probabilitylab.nativev4.model.LotteryType
import com.tianji.probabilitylab.nativev4.push.PushAlertCoordinator
import com.tianji.probabilitylab.nativev4.push.PushAlertNavigation
import com.tianji.probabilitylab.nativev4.service.AiForegroundService
import com.tianji.probabilitylab.nativev4.ui.theme.AppearanceMode
import com.tianji.probabilitylab.nativev4.ui.theme.AppearanceStore
import com.tianji.probabilitylab.nativev4.ui.theme.LocalTianjiColors
import com.tianji.probabilitylab.nativev4.ui.theme.PaletteMode
import com.tianji.probabilitylab.nativev4.ui.theme.TianjiTheme
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

@Composable
fun TianjiApp() {
    val context = LocalContext.current
    val runtime = remember(context.applicationContext) {
        TianjiRuntime.from(context.applicationContext)
    }
    val controller = runtime.appController
    val chatController = runtime.chatController
    val appearanceStore = remember { AppearanceStore(context.applicationContext) }
    val paletteMode by appearanceStore.palette.collectAsState(initial = PaletteMode.MONET)
    val appearanceMode by appearanceStore.appearance.collectAsState(initial = AppearanceMode.SYSTEM)
    val pushAlerts by PushAlertCoordinator.alerts.collectAsState()
    val pushPreferences by PushAlertCoordinator.preferences.collectAsState()
    val pushStatus by PushAlertCoordinator.status.collectAsState()
    val pendingAlertId by PushAlertNavigation.pendingAlertId.collectAsState()
    val pendingPrediction by PushAlertNavigation.pendingPrediction.collectAsState()
    val scope = rememberCoroutineScope()
    val state = controller.state

    val refreshSafely: () -> Unit = {
        if (!state.isAiAnalyzing) controller.refreshCurrentLottery()
    }
    val chatRunning = chatController.session.isRunning

    LaunchedEffect(state.isAiAnalyzing, chatRunning, chatController.session.progress) {
        if (state.isAiAnalyzing || chatRunning) {
            val title = when {
                state.isAiAnalyzing && chatRunning -> "天机 AI 任务正在运行"
                state.isAiAnalyzing -> "天机正式预测正在运行"
                else -> "天机分析对话正在运行"
            }
            val detail = if (chatRunning) {
                chatController.session.progress.ifBlank { "切出页面后仍会继续生成" }
            } else {
                state.aiStatuses.values.firstOrNull { it.state.name == "ANALYZING" }
                    ?.message.orEmpty().ifBlank { "切出页面后仍会继续预测" }
            }
            AiForegroundService.show(context, title, detail)
        } else {
            AiForegroundService.hide(context)
        }
    }

    LaunchedEffect(
        state.snapshot?.nextDrawAtEpochMs,
        state.snapshot?.latest?.period,
        state.isAiAnalyzing,
        chatRunning,
    ) {
        while (true) {
            val remaining = state.snapshot?.nextDrawAtEpochMs?.minus(System.currentTimeMillis())
            val waitMs = when {
                state.isAiAnalyzing || chatRunning -> 30_000L
                remaining == null -> 30_000L
                remaining in -90_000L..60_000L -> 3_000L
                remaining in 60_001L..180_000L -> 8_000L
                else -> 30_000L
            }
            delay(waitMs)
            if (!state.isAiAnalyzing && !chatRunning) {
                controller.refreshCurrentLottery()
            }
        }
    }

    LaunchedEffect(state.snapshot?.latest?.period, state.snapshot?.history?.size) {
        state.snapshot?.let(chatController::settleCandidates)
    }

    var destination by rememberSaveable { mutableStateOf(MainDestination.HOME) }
    var showChat by rememberSaveable { mutableStateOf(false) }
    var showAlertCenter by rememberSaveable { mutableStateOf(false) }
    var focusedAlertId by rememberSaveable { mutableStateOf<Long?>(null) }

    val notificationPermissionLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestPermission(),
    ) {
        PushAlertCoordinator.refresh()
    }

    LaunchedEffect(showAlertCenter, pushPreferences.enabled) {
        if (
            showAlertCenter &&
            pushPreferences.enabled &&
            Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&
            ContextCompat.checkSelfPermission(
                context,
                Manifest.permission.POST_NOTIFICATIONS,
            ) != PackageManager.PERMISSION_GRANTED
        ) {
            notificationPermissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
        }
    }

    LaunchedEffect(pendingPrediction) {
        pendingPrediction?.let { target ->
            LotteryType.entries.firstOrNull { it.apiKey == target.lottery }
                ?.let(controller::selectLottery)
            destination = MainDestination.HOME
            showAlertCenter = false
            focusedAlertId = null
            PushAlertNavigation.consumePrediction()
        }
    }

    LaunchedEffect(pendingAlertId) {
        pendingAlertId?.let { alertId ->
            focusedAlertId = alertId.takeIf { it > 0L }
            showAlertCenter = true
            PushAlertNavigation.consume()
        }
    }

    BackHandler(enabled = showAlertCenter || showChat || destination != MainDestination.HOME) {
        when {
            showAlertCenter -> {
                showAlertCenter = false
                focusedAlertId = null
            }
            showChat -> showChat = false
            else -> destination = MainDestination.HOME
        }
    }

    TianjiTheme(
        mode = paletteMode,
        lottery = state.lottery,
        appearance = appearanceMode,
    ) {
        val colors = LocalTianjiColors.current
        Box(
            modifier = Modifier.fillMaxSize().background(colors.page),
        ) {
            V62AdaptiveScaffold(
                selected = destination,
                onSelected = { destination = it },
                onChat = { showChat = true },
                isAiRunning = state.isAiAnalyzing || chatRunning,
                compactBottomBar = {
                    Column {
                        AiReviewProgressDock(
                            state = state,
                            modifier = Modifier.padding(start = 18.dp, end = 18.dp, bottom = 6.dp),
                        )
                        MainBottomBar(
                            selected = destination,
                            onSelected = { destination = it },
                            onChat = { showChat = true },
                            isAiRunning = state.isAiAnalyzing || chatRunning,
                            modifier = Modifier.padding(start = 12.dp, end = 12.dp, bottom = 8.dp),
                        )
                    }
                },
            ) {
                Column(Modifier.fillMaxSize()) {
                    CompactAppHeader(
                        destination = destination,
                        isRefreshing = state.isRefreshing,
                        onRefresh = refreshSafely,
                        unreadAlerts = pushAlerts.count { !it.isRead },
                        onAlerts = {
                            focusedAlertId = null
                            showAlertCenter = true
                        },
                    )
                    Box(Modifier.weight(1f)) {
                        AnimatedContent(
                            targetState = destination,
                            modifier = Modifier.fillMaxSize(),
                            transitionSpec = {
                                pageTransformV2(initialState.ordinal, targetState.ordinal)
                            },
                            label = "v62-pages",
                        ) { page ->
                            when (page) {
                                MainDestination.HOME -> V62ForecastScreen(
                                    state = state,
                                    aiConfigs = controller.aiConfigs,
                                    onSelectLottery = controller::selectLottery,
                                    onRefresh = refreshSafely,
                                    onAnalyzeAllAi = { controller.analyzeWithAi() },
                                    onCancelAi = controller::cancelAi,
                                    modifier = Modifier.fillMaxSize(),
                                )
                                MainDestination.STRATEGY -> StrategyAndEvidenceScreen(
                                    state = state,
                                    onSelectLottery = controller::selectLottery,
                                    modifier = Modifier.fillMaxSize(),
                                )
                                MainDestination.ARCHIVE -> V62ArchiveScreen(
                                    state = state,
                                    onSelectLottery = controller::selectLottery,
                                    modifier = Modifier.fillMaxSize(),
                                )
                                MainDestination.SETTINGS -> SettingsHubScreen(
                                    state = state,
                                    paletteMode = paletteMode,
                                    appearanceMode = appearanceMode,
                                    aiConfigs = controller.aiConfigs,
                                    aiAvailableModels = controller.aiAvailableModels,
                                    onPaletteChanged = { mode ->
                                        scope.launch { appearanceStore.setPalette(mode) }
                                    },
                                    onAppearanceChanged = { mode ->
                                        scope.launch { appearanceStore.setAppearance(mode) }
                                    },
                                    onSaveAiConfig = controller::saveAiConfig,
                                    onDeleteAiConfig = controller::deleteAiConfig,
                                    onTestAiConnection = controller::testAiConnection,
                                    onLoadAiModels = controller::loadAiModels,
                                    onSelectAiModel = controller::selectAiModel,
                                    onSelectAiMode = controller::selectAiAnalysisMode,
                                    onSelectAiReasoningMode = controller::selectAiReasoningMode,
                                    onAiConcurrencyChanged = controller::setAiConcurrency,
                                    onAnalyzeAi = { id -> controller.analyzeWithAi(id) },
                                    pushUnreadCount = pushAlerts.count { !it.isRead },
                                    onOpenPushAlerts = {
                                        focusedAlertId = null
                                        showAlertCenter = true
                                    },
                                    modifier = Modifier.fillMaxSize(),
                                )
                            }
                        }
                    }
                }
            }

            if (showChat) {
                AiChatDialog(
                    controller = chatController,
                    configs = controller.aiConfigs,
                    modelCatalogs = controller.aiAvailableModels,
                    snapshot = state.snapshot,
                    report = state.report,
                    onRefresh = refreshSafely,
                    onDismiss = { showChat = false },
                )
            }

            if (showAlertCenter) {
                V62PushAlertCenterScreen(
                    alerts = pushAlerts,
                    preferences = pushPreferences,
                    status = pushStatus,
                    focusAlertId = focusedAlertId,
                    onPreferencesChange = PushAlertCoordinator::updatePreferences,
                    onRead = PushAlertCoordinator::markRead,
                    onReadAll = PushAlertCoordinator::markAllRead,
                    onRefresh = PushAlertCoordinator::refresh,
                    onClose = {
                        showAlertCenter = false
                        focusedAlertId = null
                    },
                    modifier = Modifier.fillMaxSize(),
                )
            }
        }
    }
}

private fun pageTransformV2(from: Int, to: Int): ContentTransform {
    val direction = if (to >= from) 1 else -1
    return (
        slideInHorizontally(tween(210)) { it / 10 * direction } + fadeIn(tween(170))
        ) togetherWith (
        slideOutHorizontally(tween(160)) { -it / 12 * direction } + fadeOut(tween(120))
        )
}
