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
    val appearance = remember { AppearanceStore(context.applicationContext) }
    val paletteMode by appearance.palette.collectAsState(initial = PaletteMode.MONET)
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
            fontScale = maxOf(density.fontScale, 1.10f),
        )
    }

    var destination by rememberSaveable { mutableStateOf(NavDestination.FORECAST) }
    var showChat by rememberSaveable { mutableStateOf(false) }

    BackHandler(enabled = showChat || destination != NavDestination.FORECAST) {
        if (showChat) showChat = false else destination = NavDestination.FORECAST
    }

    TianjiTheme(mode = paletteMode, lottery = state.lottery) {
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
                                listOf(
                                    colors.page,
                                    colors.pageSoft,
                                    colors.page,
                                ),
                            ),
                        ),
                ) {
                    TianjiBackdrop()

                    Column(Modifier.fillMaxSize()) {
                        AppHeader(
                            isRefreshing = state.isRefreshing,
                            onRefresh = refreshSafely,
                        )
                        Box(Modifier.weight(1f)) {
                            AnimatedContent(
                                targetState = destination,
                                modifier = Modifier.fillMaxSize(),
                                transitionSpec = {
                                    pageTransform(initialState.ordinal, targetState.ordinal)
                                },
                                label = "native-pages",
                            ) { page ->
                                when (page) {
                                    NavDestination.FORECAST -> ForecastScreen(
                                        state = state,
                                        aiConfigs = controller.aiConfigs,
                                        onSelectLottery = controller::selectLottery,
                                        onRefresh = refreshSafely,
                                        onAnalyzeAllAi = { controller.analyzeWithAi() },
                                        onCancelAi = controller::cancelAi,
                                        modifier = Modifier.fillMaxSize(),
                                    )

                                    NavDestination.ROLLING -> RollingScreen(
                                        state = state,
                                        onSelectLottery = controller::selectLottery,
                                        modifier = Modifier.fillMaxSize(),
                                    )

                                    NavDestination.EVIDENCE -> EvidenceScreen(
                                        state = state,
                                        onSelectLottery = controller::selectLottery,
                                        modifier = Modifier.fillMaxSize(),
                                    )

                                    NavDestination.ARCHIVE -> ArchiveScreen(
                                        state = state,
                                        onSelectLottery = controller::selectLottery,
                                        modifier = Modifier.fillMaxSize(),
                                    )

                                    NavDestination.DATA -> DataScreen(
                                        state = state,
                                        paletteMode = paletteMode,
                                        aiConfigs = controller.aiConfigs,
                                        aiAvailableModels = controller.aiAvailableModels,
                                        onPaletteChanged = { mode ->
                                            scope.launch { appearance.setPalette(mode) }
                                        },
                                        onSelectLottery = controller::selectLottery,
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

                            BottomNavigation(
                                selected = destination,
                                onSelected = { destination = it },
                                modifier = Modifier
                                    .align(Alignment.BottomCenter)
                                    .padding(start = 13.dp, end = 13.dp, bottom = 11.dp),
                            )

                            AiChatFloatingButton(
                                onClick = { showChat = true },
                                modifier = Modifier
                                    .align(Alignment.BottomEnd)
                                    .padding(end = 18.dp, bottom = 91.dp),
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
private fun TianjiBackdrop() {
    val colors = LocalTianjiColors.current
    Canvas(Modifier.fillMaxSize()) {
        drawCircle(
            brush = Brush.radialGradient(
                listOf(
                    colors.amber.copy(alpha = if (colors.isOled) 0.035f else 0.070f),
                    Color.Transparent,
                ),
            ),
            radius = size.width * 0.82f,
            center = Offset(size.width * -0.05f, size.height * 0.04f),
        )
        drawCircle(
            brush = Brush.radialGradient(
                listOf(
                    colors.accent.copy(alpha = if (colors.isOled) 0.055f else 0.095f),
                    Color.Transparent,
                ),
            ),
            radius = size.width * 0.78f,
            center = Offset(size.width * 1.04f, size.height * 0.30f),
        )
        drawCircle(
            brush = Brush.radialGradient(
                listOf(
                    colors.green.copy(alpha = if (colors.isOled) 0.018f else 0.035f),
                    Color.Transparent,
                ),
            ),
            radius = size.width * 0.70f,
            center = Offset(size.width * 0.40f, size.height * 1.02f),
        )
    }
}

private fun pageTransform(from: Int, to: Int): ContentTransform {
    val direction = if (to >= from) 1 else -1
    return (
        slideInHorizontally(tween(260)) { it / 7 * direction } +
            fadeIn(tween(220))
        ) togetherWith (
        slideOutHorizontally(tween(190)) { -it / 9 * direction } +
            fadeOut(tween(150))
        )
}
