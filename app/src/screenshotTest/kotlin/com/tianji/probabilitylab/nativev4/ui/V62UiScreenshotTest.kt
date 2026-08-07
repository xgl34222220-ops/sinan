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
import com.tianji.probabilitylab.nativev4.model.LotteryType
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
