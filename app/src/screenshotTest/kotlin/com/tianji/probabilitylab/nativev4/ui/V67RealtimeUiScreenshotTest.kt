package com.tianji.probabilitylab.nativev4.ui

import android.content.res.Configuration
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.tooling.preview.Preview
import com.android.tools.screenshot.PreviewTest
import com.tianji.probabilitylab.nativev4.AppUiState
import com.tianji.probabilitylab.nativev4.ai.AiAnalysisMode
import com.tianji.probabilitylab.nativev4.ai.AiForecast
import com.tianji.probabilitylab.nativev4.ai.AiLiveAudit
import com.tianji.probabilitylab.nativev4.ai.AiReasoningMode
import com.tianji.probabilitylab.nativev4.ai.AiReasoningProtocol
import com.tianji.probabilitylab.nativev4.ai.AiReasoningState
import com.tianji.probabilitylab.nativev4.data.CloudRealtimeLottery
import com.tianji.probabilitylab.nativev4.model.ConfidenceInterval
import com.tianji.probabilitylab.nativev4.model.Draw
import com.tianji.probabilitylab.nativev4.model.DrawSnapshot
import com.tianji.probabilitylab.nativev4.model.EvidenceMode
import com.tianji.probabilitylab.nativev4.model.ForecastReport
import com.tianji.probabilitylab.nativev4.model.LotteryType
import com.tianji.probabilitylab.nativev4.model.PositionPrediction
import com.tianji.probabilitylab.nativev4.model.SourceHealth
import com.tianji.probabilitylab.nativev4.ui.theme.AppearanceMode
import com.tianji.probabilitylab.nativev4.ui.theme.LocalTianjiColors
import com.tianji.probabilitylab.nativev4.ui.theme.PaletteMode
import com.tianji.probabilitylab.nativev4.ui.theme.TianjiTheme

private const val PREVIEW_SYNC_EPOCH = 9_000_000_000_000L

@PreviewTest
@Preview(
    name = "V67 Realtime Phone Dark 412x980",
    widthDp = 412,
    heightDp = 980,
    uiMode = Configuration.UI_MODE_NIGHT_YES,
    showBackground = true,
)
@Composable
fun V67RealtimePhoneScreenshot() {
    V67PreviewTheme {
        Box(Modifier.fillMaxSize().background(LocalTianjiColors.current.page)) {
            V67ForecastScreen(
                state = v67PreviewState(),
                aiConfigs = emptyList(),
                realtime = v67PreviewRealtime(),
                onSelectLottery = {},
                onRefreshAll = {},
                onAnalyzeAllAi = {},
                onCancelAi = {},
                modifier = Modifier.fillMaxSize(),
            )
        }
    }
}

@PreviewTest
@Preview(
    name = "V67 Realtime Tablet Dark 840x980",
    widthDp = 840,
    heightDp = 980,
    uiMode = Configuration.UI_MODE_NIGHT_YES,
    showBackground = true,
)
@Composable
fun V67RealtimeTabletScreenshot() {
    V67PreviewTheme {
        Box(Modifier.fillMaxSize().background(LocalTianjiColors.current.page)) {
            V67ForecastScreen(
                state = v67PreviewState(),
                aiConfigs = emptyList(),
                realtime = v67PreviewRealtime(),
                onSelectLottery = {},
                onRefreshAll = {},
                onAnalyzeAllAi = {},
                onCancelAi = {},
                modifier = Modifier.fillMaxSize(),
            )
        }
    }
}

private fun v67PreviewState(): AppUiState {
    val lottery = LotteryType.AZXY10
    val localProbabilities = listOf(0.17, 0.15, 0.13, 0.11, 0.10, 0.09, 0.08, 0.07, 0.06, 0.04)
    val positions = List(10) { position ->
        PositionPrediction(
            position = position,
            probabilities = localProbabilities,
            top6 = listOf(1, 2, 3, 4, 5, 6),
            top7 = listOf(1, 2, 3, 4, 5, 6, 7),
            coverage6 = 0.75,
            coverage7 = 0.83,
            boundaryMargin = 0.018,
        )
    }
    val latest = Draw(
        lottery = lottery,
        period = "202608080201",
        numbers = listOf(4, 9, 2, 7, 1, 10, 5, 8, 3, 6),
        drawTime = "2026-08-08 09:20:00",
    )
    val report = ForecastReport(
        algorithmVersion = "v6.7-preview",
        trainedThroughPeriod = latest.period,
        targetPeriod = "202608080202",
        historySize = 3_000,
        validationDraws = 180,
        mode = EvidenceMode.CERTIFIED,
        displayUsesShadow = false,
        selectedPosition = 0,
        positions = positions,
        models = emptyList(),
        top6HitRate = 0.63,
        top7HitRate = 0.72,
        top6Interval = ConfidenceInterval(0.58, 0.68),
        top7Interval = ConfidenceInterval(0.67, 0.77),
        randomTop6Baseline = 0.60,
        randomTop7Baseline = 0.70,
        breakEvenTop7 = 0.70,
        averageLogLoss = 2.08,
        randomLogLoss = 2.30,
        dataAdequacy = 100,
        blockedReasons = emptyList(),
    )
    val aiForecast = AiForecast(
        profileId = "cloud:ai:deepseek-v4-pro",
        profileName = "天机云端 AI",
        targetPeriod = report.targetPeriod,
        position = 0,
        top6 = listOf(1, 3, 4, 6, 8, 9),
        top7 = listOf(1, 3, 4, 6, 8, 9, 10),
        probabilities = listOf(0.16, 0.06, 0.15, 0.14, 0.05, 0.13, 0.07, 0.10, 0.09, 0.05),
        analysis = "动态联合评审结果",
        riskNote = "仅用于前向验证",
        selfRating = 0.74,
        model = "deepseek-v4-pro",
        analysisMode = AiAnalysisMode.DEEP,
        reasoningMode = AiReasoningMode.AUTO,
        reasoningProtocol = AiReasoningProtocol.AUTO,
        reasoningState = AiReasoningState.VERIFIED,
        reasoningTokens = 1_024,
        inputTokens = 2_048,
        outputTokens = 1_200,
        estimatedCost = null,
        executionNote = "云端 AI v2",
        createdAtEpochMs = PREVIEW_SYNC_EPOCH,
        latencyMs = 3_200,
        responseId = "preview-ai-v67",
    )
    return AppUiState(
        lottery = lottery,
        snapshot = DrawSnapshot(
            lottery = lottery,
            history = listOf(latest),
            latest = latest,
            nextPeriod = report.targetPeriod,
            sourceHealth = SourceHealth(
                label = "天机云端实时",
                isFresh = true,
                independentSources = 1,
                message = "双彩种实时同步",
                syncedAtEpochMs = PREVIEW_SYNC_EPOCH,
            ),
            serverTimeEpochMs = null,
            nextDrawAtEpochMs = null,
        ),
        report = report,
        aiForecasts = listOf(aiForecast),
        aiLiveAudit = AiLiveAudit(
            settled = 50,
            targetPeriods = 50,
            top6Hits = 32,
            top7Hits = 37,
        ),
        isLoading = false,
        isRefreshing = false,
    )
}

private fun v67PreviewRealtime(): Map<LotteryType, CloudRealtimeLottery> = mapOf(
    LotteryType.XYFT to CloudRealtimeLottery(
        lottery = LotteryType.XYFT,
        latestPeriod = "202608080101",
        numbers = listOf(10, 2, 6, 8, 1, 4, 9, 3, 7, 5),
        nextPeriod = "202608080102",
        nextDrawAtEpochMs = null,
        syncedAtEpochMs = PREVIEW_SYNC_EPOCH,
        fetchedAtEpochMs = PREVIEW_SYNC_EPOCH,
    ),
    LotteryType.AZXY10 to CloudRealtimeLottery(
        lottery = LotteryType.AZXY10,
        latestPeriod = "202608080201",
        numbers = listOf(4, 9, 2, 7, 1, 10, 5, 8, 3, 6),
        nextPeriod = "202608080202",
        nextDrawAtEpochMs = null,
        syncedAtEpochMs = PREVIEW_SYNC_EPOCH,
        fetchedAtEpochMs = PREVIEW_SYNC_EPOCH,
    ),
)

@Composable
private fun V67PreviewTheme(content: @Composable () -> Unit) {
    TianjiTheme(
        mode = PaletteMode.VIOLET,
        lottery = LotteryType.AZXY10,
        appearance = AppearanceMode.DARK,
        content = content,
    )
}
