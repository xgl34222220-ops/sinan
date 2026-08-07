package com.tianji.probabilitylab.nativev4.ui

import android.content.res.Configuration
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.ColorLens
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import com.android.tools.screenshot.PreviewTest
import com.tianji.probabilitylab.nativev4.AppUiState
import com.tianji.probabilitylab.nativev4.model.ConfidenceInterval
import com.tianji.probabilitylab.nativev4.model.Draw
import com.tianji.probabilitylab.nativev4.model.DrawSnapshot
import com.tianji.probabilitylab.nativev4.model.EvidenceMode
import com.tianji.probabilitylab.nativev4.model.ForecastReport
import com.tianji.probabilitylab.nativev4.model.LotteryType
import com.tianji.probabilitylab.nativev4.model.PositionPrediction
import com.tianji.probabilitylab.nativev4.model.SourceHealth
import com.tianji.probabilitylab.nativev4.push.PushAlert
import com.tianji.probabilitylab.nativev4.push.PushConnectionStatus
import com.tianji.probabilitylab.nativev4.push.PushPreferences
import com.tianji.probabilitylab.nativev4.push.PushProtocol
import com.tianji.probabilitylab.nativev4.ui.theme.AppearanceMode
import com.tianji.probabilitylab.nativev4.ui.theme.LocalTianjiColors
import com.tianji.probabilitylab.nativev4.ui.theme.PaletteMode
import com.tianji.probabilitylab.nativev4.ui.theme.TianjiTheme

@PreviewTest
@Preview(
    name = "Header Dark 412",
    widthDp = 412,
    heightDp = 96,
    uiMode = Configuration.UI_MODE_NIGHT_YES,
    showBackground = true,
)
@Composable
fun V62HeaderDarkScreenshot() {
    PreviewTheme(AppearanceMode.DARK) {
        CompactAppHeader(
            destination = MainDestination.HOME,
            isRefreshing = false,
            onRefresh = {},
            unreadAlerts = 3,
            onAlerts = {},
        )
    }
}

@PreviewTest
@Preview(
    name = "Liquid Dock OLED 412",
    widthDp = 412,
    heightDp = 124,
    uiMode = Configuration.UI_MODE_NIGHT_YES,
    showBackground = true,
)
@Composable
fun V62DockOledScreenshot() {
    PreviewTheme(AppearanceMode.OLED) {
        Box(
            modifier = Modifier
                .fillMaxSize()
                .background(LocalTianjiColors.current.page)
                .padding(12.dp),
        ) {
            MainBottomBar(
                selected = MainDestination.HOME,
                onSelected = {},
                onChat = {},
                isAiRunning = true,
            )
        }
    }
}

@PreviewTest
@Preview(
    name = "Settings Row Light 412",
    widthDp = 412,
    heightDp = 110,
    uiMode = Configuration.UI_MODE_NIGHT_NO,
    showBackground = true,
)
@Composable
fun V62SettingsRowLightScreenshot() {
    PreviewTheme(AppearanceMode.LIGHT) {
        Box(
            modifier = Modifier
                .fillMaxSize()
                .background(LocalTianjiColors.current.page)
                .padding(12.dp),
        ) {
            SettingsEntry(
                icon = Icons.Rounded.ColorLens,
                title = "外观与主题",
                detail = "跟随系统、浅色、深色、OLED 和强调色",
                onClick = {},
                badge = "跟随系统",
            )
        }
    }
}

@PreviewTest
@Preview(
    name = "Home Empty Dark 412x820",
    widthDp = 412,
    heightDp = 820,
    uiMode = Configuration.UI_MODE_NIGHT_YES,
    showBackground = true,
)
@Composable
fun V62HomeEmptyScreenshot() {
    PreviewTheme(AppearanceMode.DARK) {
        V62ForecastScreen(
            state = AppUiState(
                lottery = LotteryType.AZXY10,
                isLoading = false,
                error = "等待首批真实开奖数据",
            ),
            aiConfigs = emptyList(),
            onSelectLottery = {},
            onRefresh = {},
            onAnalyzeAllAi = {},
            onCancelAi = {},
            modifier = Modifier.fillMaxSize(),
        )
    }
}

@PreviewTest
@Preview(
    name = "Home Data Dark 412x900",
    widthDp = 412,
    heightDp = 900,
    uiMode = Configuration.UI_MODE_NIGHT_YES,
    showBackground = true,
)
@Composable
fun V62HomeDataScreenshot() {
    PreviewTheme(AppearanceMode.DARK) {
        V62ForecastScreen(
            state = previewForecastState(),
            aiConfigs = emptyList(),
            onSelectLottery = {},
            onRefresh = {},
            onAnalyzeAllAi = {},
            onCancelAi = {},
            modifier = Modifier.fillMaxSize(),
        )
    }
}

@PreviewTest
@Preview(
    name = "Home Tablet Dark 840x900",
    widthDp = 840,
    heightDp = 900,
    uiMode = Configuration.UI_MODE_NIGHT_YES,
    showBackground = true,
)
@Composable
fun V62HomeTabletScreenshot() {
    PreviewTheme(AppearanceMode.DARK) {
        V62ForecastScreen(
            state = previewForecastState(),
            aiConfigs = emptyList(),
            onSelectLottery = {},
            onRefresh = {},
            onAnalyzeAllAi = {},
            onCancelAi = {},
            modifier = Modifier.fillMaxSize(),
        )
    }
}

@PreviewTest
@Preview(
    name = "Notification Center Dark 412x900",
    widthDp = 412,
    heightDp = 900,
    uiMode = Configuration.UI_MODE_NIGHT_YES,
    showBackground = true,
)
@Composable
fun V62NotificationCenterScreenshot() {
    PreviewTheme(AppearanceMode.DARK) {
        V62PushAlertCenterScreen(
            alerts = listOf(
                PushAlert(
                    id = 3,
                    eventKey = "risk-3",
                    lottery = "azxy10",
                    lotteryName = "澳洲幸运10",
                    source = "ai",
                    sourceName = "天机云端 AI",
                    model = "deepseek-chat",
                    streak = 3,
                    threshold = 3,
                    latestTargetPeriod = "20260807123",
                    recentPeriods = listOf("20260807121", "20260807122", "20260807123"),
                    title = "连续三期未命中",
                    body = "当前 AI 走势判断连续三期未进入目标边界，建议查看最近档案与模型变化。",
                    createdAtEpochMs = 1_775_000_000_000,
                    isRead = false,
                    eventType = PushProtocol.EVENT_MISS_ALERT,
                    severity = PushProtocol.SEVERITY_CRITICAL,
                ),
                PushAlert(
                    id = 2,
                    eventKey = "prediction-2",
                    lottery = "xyft",
                    lotteryName = "幸运飞艇",
                    source = "ai",
                    sourceName = "AI 共识",
                    model = "consensus",
                    streak = 0,
                    threshold = 3,
                    latestTargetPeriod = "20260807122",
                    recentPeriods = emptyList(),
                    title = "本期预测已完成",
                    body = "多路 AI 已完成本期判断，可直接进入预测页查看正式结果。",
                    createdAtEpochMs = 1_774_999_600_000,
                    isRead = true,
                    eventType = PushProtocol.EVENT_PREDICTION_READY,
                    severity = PushProtocol.SEVERITY_INFO,
                ),
            ),
            preferences = PushPreferences(),
            status = PushConnectionStatus(
                registered = true,
                firebaseConfigured = true,
                serverConfigured = true,
                fcmTokenPresent = true,
                detail = "FCM 即时推送正常",
                protocolVersion = 2,
            ),
            focusAlertId = 3,
            onPreferencesChange = {},
            onRead = {},
            onReadAll = {},
            onOpenAlert = {},
            onRefresh = {},
            onClose = {},
            modifier = Modifier.fillMaxSize(),
        )
    }
}

private fun previewForecastState(): AppUiState {
    val lottery = LotteryType.AZXY10
    val probabilities = listOf(0.16, 0.14, 0.12, 0.11, 0.10, 0.09, 0.08, 0.07, 0.07, 0.06)
    val positions = List(10) { position ->
        PositionPrediction(
            position = position,
            probabilities = probabilities,
            top6 = listOf(1, 2, 3, 4, 5, 6),
            top7 = listOf(1, 2, 3, 4, 5, 6, 7),
            coverage6 = 0.72,
            coverage7 = 0.80,
            boundaryMargin = 0.012,
        )
    }
    val latest = Draw(
        lottery = lottery,
        period = "20260807122",
        numbers = (1..10).toList(),
        drawTime = "2026-08-07 16:15:00",
    )
    return AppUiState(
        lottery = lottery,
        snapshot = DrawSnapshot(
            lottery = lottery,
            history = listOf(latest),
            latest = latest,
            nextPeriod = "20260807123",
            sourceHealth = SourceHealth(
                label = "network",
                isFresh = true,
                independentSources = 1,
                message = "实时开奖源已同步",
                syncedAtEpochMs = 1_775_000_000_000,
            ),
            serverTimeEpochMs = null,
            nextDrawAtEpochMs = null,
        ),
        report = ForecastReport(
            algorithmVersion = "v6.2-preview",
            trainedThroughPeriod = latest.period,
            targetPeriod = "20260807123",
            historySize = 240,
            validationDraws = 120,
            mode = EvidenceMode.CERTIFIED,
            displayUsesShadow = false,
            selectedPosition = 0,
            positions = positions,
            models = emptyList(),
            top6HitRate = 0.61,
            top7HitRate = 0.70,
            top6Interval = ConfidenceInterval(0.55, 0.67),
            top7Interval = ConfidenceInterval(0.64, 0.76),
            randomTop6Baseline = 0.60,
            randomTop7Baseline = 0.70,
            breakEvenTop7 = 0.70,
            averageLogLoss = 2.10,
            randomLogLoss = 2.30,
            dataAdequacy = 100,
            blockedReasons = emptyList(),
        ),
        isLoading = false,
    )
}

@Composable
private fun PreviewTheme(
    appearance: AppearanceMode,
    content: @Composable () -> Unit,
) {
    TianjiTheme(
        mode = PaletteMode.VIOLET,
        lottery = LotteryType.AZXY10,
        appearance = appearance,
        content = content,
    )
}
