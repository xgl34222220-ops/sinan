package com.tianji.probabilitylab.nativev4.ui

import androidx.activity.compose.BackHandler
import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.ContentTransform
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInHorizontally
import androidx.compose.animation.slideOutHorizontally
import androidx.compose.animation.togetherWith
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.systemBars
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.unit.Density
import androidx.compose.ui.unit.dp
import com.tianji.probabilitylab.nativev4.TianjiRuntime
import com.tianji.probabilitylab.nativev4.service.AiForegroundService
import com.tianji.probabilitylab.nativev4.ui.theme.AppearanceMode
import com.tianji.probabilitylab.nativev4.ui.theme.AppearanceStore
import com.tianji.probabilitylab.nativev4.ui.theme.LocalTianjiColors
import com.tianji.probabilitylab.nativev4.ui.theme.PaletteMode
import com.tianji.probabilitylab.nativev4.ui.theme.TianjiTheme
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
    val scope = rememberCoroutineScope()
    val state = controller.state

    val refreshSafely: () -> Unit = {
        if (!state.isAiAnalyzing) controller.refresh()
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

    LaunchedEffect(state.snapshot?.latest?.period, state.snapshot?.history?.size) {
        state.snapshot?.let(chatController::settleCandidates)
    }

    val density = LocalDensity.current
    val readableDensity = remember(density.density, density.fontScale) {
        Density(
            density = density.density,
            fontScale = maxOf(density.fontScale, 1.08f),
        )
    }

    var destination by rememberSaveable { mutableStateOf(MainDestination.HOME) }
    var showChat by rememberSaveable { mutableStateOf(false) }

    BackHandler(enabled = showChat || destination != MainDestination.HOME) {
        if (showChat) showChat = false else destination = MainDestination.HOME
    }

    TianjiTheme(
        mode = paletteMode,
        lottery = state.lottery,
        appearance = appearanceMode,
    ) {
        val colors = LocalTianjiColors.current
        CompositionLocalProvider(LocalDensity provides readableDensity) {
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .background(colors.page),
            ) {
                Box(
                    modifier = Modifier
                        .fillMaxSize()
                        .windowInsetsPadding(WindowInsets.systemBars)
                        .background(
                            Brush.verticalGradient(
                                listOf(colors.page, colors.pageSoft, colors.page),
                            ),
                        ),
                ) {
                    TianjiBackdropV2()

                    Column(Modifier.fillMaxSize()) {
                        CompactAppHeader(
                            destination = destination,
                            isRefreshing = state.isRefreshing,
                            onRefresh = refreshSafely,
                        )
                        Box(Modifier.weight(1f)) {
                            AnimatedContent(
                                targetState = destination,
                                modifier = Modifier.fillMaxSize(),
                                transitionSpec = {
                                    pageTransformV2(initialState.ordinal, targetState.ordinal)
                                },
                                label = "refined-pages",
                            ) { page ->
                                when (page) {
                                    MainDestination.HOME -> RefinedForecastScreen(
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
                                    MainDestination.CHAT -> RefinedForecastScreen(
                                        state = state,
                                        aiConfigs = controller.aiConfigs,
                                        onSelectLottery = controller::selectLottery,
                                        onRefresh = refreshSafely,
                                        onAnalyzeAllAi = { controller.analyzeWithAi() },
                                        onCancelAi = controller::cancelAi,
                                        modifier = Modifier.fillMaxSize(),
                                    )
                                    MainDestination.ARCHIVE -> RefinedArchiveScreen(
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
                                        modifier = Modifier.fillMaxSize(),
                                    )
                                }
                            }

                            MainBottomBar(
                                selected = destination,
                                onSelected = { destination = it },
                                onChat = { showChat = true },
                                modifier = Modifier
                                    .align(Alignment.BottomCenter)
                                    .padding(start = 12.dp, end = 12.dp, bottom = 9.dp),
                            )
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
            }
        }
    }
}

@Composable
private fun TianjiBackdropV2() {
    val colors = LocalTianjiColors.current
    Canvas(Modifier.fillMaxSize()) {
        drawCircle(
            brush = Brush.radialGradient(
                listOf(
                    colors.accent.copy(
                        alpha = if (colors.isOled) 0.045f else if (colors.isDark) 0.085f else 0.055f,
                    ),
                    Color.Transparent,
                ),
            ),
            radius = size.width * 0.84f,
            center = Offset(size.width * 1.04f, size.height * 0.20f),
        )
        drawCircle(
            brush = Brush.radialGradient(
                listOf(
                    colors.amber.copy(
                        alpha = if (colors.isOled) 0.025f else if (colors.isDark) 0.050f else 0.035f,
                    ),
                    Color.Transparent,
                ),
            ),
            radius = size.width * 0.72f,
            center = Offset(size.width * -0.08f, size.height * 0.04f),
        )
    }
}

private fun pageTransformV2(from: Int, to: Int): ContentTransform {
    val direction = if (to >= from) 1 else -1
    return (
        slideInHorizontally(tween(230)) { it / 9 * direction } +
            fadeIn(tween(190))
        ) togetherWith (
        slideOutHorizontally(tween(170)) { -it / 11 * direction } +
            fadeOut(tween(130))
        )
}
