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
import androidx.compose.runtime.DisposableEffect
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
import com.tianji.probabilitylab.nativev4.AppController
import com.tianji.probabilitylab.nativev4.ai.AiChatController
import com.tianji.probabilitylab.nativev4.ui.theme.AppearanceStore
import com.tianji.probabilitylab.nativev4.ui.theme.LocalTianjiColors
import com.tianji.probabilitylab.nativev4.ui.theme.PaletteMode
import com.tianji.probabilitylab.nativev4.ui.theme.TianjiTheme
import kotlinx.coroutines.launch

@Composable
fun TianjiApp() {
    val context = LocalContext.current
    val controller = remember { AppController(context) }
    val chatController = remember { AiChatController() }
    val appearance = remember { AppearanceStore(context.applicationContext) }
    val paletteMode by appearance.palette.collectAsState(initial = PaletteMode.MONET)
    val scope = rememberCoroutineScope()
    val state = controller.state
    var destination by rememberSaveable { mutableStateOf(NavDestination.FORECAST) }
    var showChat by rememberSaveable { mutableStateOf(false) }
    val density = LocalDensity.current
    val accessibleDensity = remember(density.density, density.fontScale) {
        Density(density.density, density.fontScale)
    }

    DisposableEffect(controller, chatController) {
        onDispose {
            chatController.close()
            controller.close()
        }
    }
    BackHandler(enabled = showChat || destination != NavDestination.FORECAST) {
        if (showChat) showChat = false else destination = NavDestination.FORECAST
    }

    TianjiTheme(mode = paletteMode, lottery = state.lottery) {
        val colors = LocalTianjiColors.current
        CompositionLocalProvider(LocalDensity provides accessibleDensity) {
            Box(Modifier.fillMaxSize().background(colors.page)) {
                Box(
                    modifier = Modifier
                        .fillMaxSize()
                        .windowInsetsPadding(WindowInsets.systemBars)
                        .background(colors.page),
                ) {
                    Canvas(Modifier.fillMaxSize()) {
                        drawCircle(
                            brush = Brush.radialGradient(
                                listOf(Color(0xFFFF8A1F).copy(alpha = 0.07f), Color.Transparent),
                            ),
                            radius = size.width * 0.75f,
                            center = Offset(size.width * 0.05f, 0f),
                        )
                        drawCircle(
                            brush = Brush.radialGradient(
                                listOf(colors.accent.copy(alpha = 0.065f), Color.Transparent),
                            ),
                            radius = size.width * 0.72f,
                            center = Offset(size.width * 1.08f, size.height * 0.34f),
                        )
                    }
                    Column(Modifier.fillMaxSize()) {
                        AppHeader(state.isRefreshing, controller::refresh)
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
                                        onRefresh = controller::refresh,
                                        onAnalyzeAllAi = { controller.analyzeWithAi() },
                                        onCancelAi = controller::cancelAi,
                                        modifier = Modifier.fillMaxSize(),
                                    )
                                    NavDestination.ROLLING -> RollingScreen(
                                        state,
                                        controller::selectLottery,
                                        Modifier.fillMaxSize(),
                                    )
                                    NavDestination.EVIDENCE -> EvidenceScreen(
                                        state,
                                        controller::selectLottery,
                                        Modifier.fillMaxSize(),
                                    )
                                    NavDestination.ARCHIVE -> ArchiveScreen(
                                        state,
                                        controller::selectLottery,
                                        Modifier.fillMaxSize(),
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
                                    .padding(start = 12.dp, end = 12.dp, bottom = 10.dp),
                            )
                            AiChatFloatingButton(
                                onClick = { showChat = true },
                                modifier = Modifier
                                    .align(Alignment.BottomEnd)
                                    .padding(end = 18.dp, bottom = 84.dp),
                            )
                        }
                    }
                }
                if (showChat) {
                    AiChatDialog(
                        controller = chatController,
                        configs = controller.aiConfigs,
                        snapshot = state.snapshot,
                        report = state.report,
                        onRefresh = controller::refresh,
                        onDismiss = { showChat = false },
                    )
                }
            }
        }
    }
}

private fun pageTransform(from: Int, to: Int): ContentTransform {
    val direction = if (to >= from) 1 else -1
    return (
        slideInHorizontally(tween(280)) { it / 5 * direction } + fadeIn(tween(220))
        ) togetherWith (
        slideOutHorizontally(tween(220)) { -it / 7 * direction } + fadeOut(tween(170))
        )
}
