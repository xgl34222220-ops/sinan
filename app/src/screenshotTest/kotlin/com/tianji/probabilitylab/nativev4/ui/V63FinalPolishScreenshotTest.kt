package com.tianji.probabilitylab.nativev4.ui

import android.content.res.Configuration
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.ColorLens
import androidx.compose.material.icons.rounded.NotificationsActive
import androidx.compose.material.icons.rounded.Psychology
import androidx.compose.material.icons.rounded.Storage
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
import com.tianji.probabilitylab.nativev4.push.PushConnectionStatus
import com.tianji.probabilitylab.nativev4.push.PushPreferences
import com.tianji.probabilitylab.nativev4.ui.theme.AppearanceMode
import com.tianji.probabilitylab.nativev4.ui.theme.LocalTianjiColors
import com.tianji.probabilitylab.nativev4.ui.theme.PaletteMode
import com.tianji.probabilitylab.nativev4.ui.theme.TianjiTheme

@PreviewTest
@Preview(
    name = "Home Small Dark 360x800",
    widthDp = 360,
    heightDp = 800,
    uiMode = Configuration.UI_MODE_NIGHT_YES,
    showBackground = true,
)
@Composable
fun V63HomeSmallDarkScreenshot() {
    V63PreviewTheme(AppearanceMode.DARK) {
        V62ForecastScreen(
            state = v63PreviewForecastState(),
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
    name = "Home Light 412x900",
    widthDp = 412,
    heightDp = 900,
    uiMode = Configuration.UI_MODE_NIGHT_NO,
    showBackground = true,
)
@Composable
fun V63HomeLightScreenshot() {
    V63PreviewTheme(AppearanceMode.LIGHT) {
        V62ForecastScreen(
            state = v63PreviewForecastState(),
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
    name = "Archive Empty Dark 412x900",
    widthDp = 412,
    heightDp = 900,
    uiMode = Configuration.UI_MODE_NIGHT_YES,
    showBackground = true,
)
@Composable
fun V63ArchiveEmptyScreenshot() {
    V63PreviewTheme(AppearanceMode.DARK) {
        V62ArchiveScreen(
            state = AppUiState(lottery = LotteryType.AZXY10),
            onSelectLottery = {},
            modifier = Modifier.fillMaxSize(),
        )
    }
}

@PreviewTest
@Preview(
    name = "Notification Fallback Dark 412x900",
    widthDp = 412,
    heightDp = 900,
    uiMode = Configuration.UI_MODE_NIGHT_YES,
    showBackground = true,
)
@Composable
fun V63NotificationFallbackScreenshot() {
    V63PreviewTheme(AppearanceMode.DARK) {
        V62PushAlertCenterScreen(
            alerts = emptyList(),
            preferences = PushPreferences(),
            status = PushConnectionStatus(
                registered = true,
                firebaseConfigured = false,
                serverConfigured = true,
                fcmTokenPresent = false,
                detail = "即时推送暂不可用，后台增量同步兜底",
                protocolVersion = 2,
            ),
            focusAlertId = null,
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

@PreviewTest
@Preview(
    name = "Settings Semantic Rows Light 412x390",
    widthDp = 412,
    heightDp = 390,
    uiMode = Configuration.UI_MODE_NIGHT_NO,
    showBackground = true,
)
@Composable
fun V63SettingsSemanticRowsScreenshot() {
    V63PreviewTheme(AppearanceMode.LIGHT) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .background(LocalTianjiColors.current.page)
                .padding(12.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            SettingsEntry(Icons.Rounded.Psychology, "AI 模型与接口", "模型、推理模式和并发", {}, "3 个可用")
            SettingsEntry(Icons.Rounded.Storage, "数据与同步", "接口状态、档案和后台同步", {}, "240 期")
            SettingsEntry(Icons.Rounded.NotificationsActive, "预警与推送", "接收范围和历史预警", {}, "2 条未读")
            SettingsEntry(Icons.Rounded.ColorLens, "外观与主题", "浅色、深色、OLED 和强调色", {}, "跟随系统")
        }
    }
}

private fun v63PreviewForecastState(): AppUiState {
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
            algorithmVersion = "v6.3-preview",
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
private fun V63PreviewTheme(
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
