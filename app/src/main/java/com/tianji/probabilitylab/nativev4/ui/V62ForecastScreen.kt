package com.tianji.probabilitylab.nativev4.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.AutoAwesome
import androidx.compose.material.icons.rounded.Bolt
import androidx.compose.material.icons.rounded.Psychology
import androidx.compose.material.icons.rounded.Sync
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.tianji.probabilitylab.nativev4.AppUiState
import com.tianji.probabilitylab.nativev4.ai.AiConfig
import com.tianji.probabilitylab.nativev4.ai.AiConnectionState
import com.tianji.probabilitylab.nativev4.model.ForecastDeadlineResolver
import com.tianji.probabilitylab.nativev4.model.ForecastReport
import com.tianji.probabilitylab.nativev4.model.LotteryType
import com.tianji.probabilitylab.nativev4.model.ServerCountdown
import com.tianji.probabilitylab.nativev4.ui.theme.LocalTianjiColors
import kotlinx.coroutines.delay

@Composable
fun V62ForecastScreen(
    state: AppUiState,
    aiConfigs: List<AiConfig>,
    onSelectLottery: (LotteryType) -> Unit,
    onRefresh: () -> Unit,
    onAnalyzeAllAi: () -> Unit,
    onCancelAi: (String) -> Unit,
    modifier: Modifier = Modifier,
) {
    val report = state.report
    var detailTab by rememberSaveable(state.lottery.apiKey) { mutableIntStateOf(0) }
    var selectedPosition by rememberSaveable(report?.targetPeriod) {
        mutableIntStateOf(report?.selectedPosition ?: 0)
    }

    BoxWithConstraints(modifier = modifier) {
        val wide = maxWidth >= 720.dp && state.snapshot != null && report != null
        if (wide) {
            LazyColumn(
                modifier = Modifier.fillMaxSize(),
                contentPadding = PaddingValues(16.dp, 16.dp, 16.dp, 22.dp),
                verticalArrangement = Arrangement.spacedBy(14.dp),
            ) {
                item("switcher") { CompactLotterySwitcher(state.lottery, onSelectLottery) }
                item("wide-grid") {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(14.dp),
                        verticalAlignment = Alignment.Top,
                    ) {
                        Column(
                            modifier = Modifier.weight(1.02f),
                            verticalArrangement = Arrangement.spacedBy(12.dp),
                        ) {
                            V62LiveHero(state, onRefresh)
                            V62ForecastHero(requireNotNull(report), selectedPosition) { selectedPosition = it }
                        }
                        Column(
                            modifier = Modifier.weight(0.98f),
                            verticalArrangement = Arrangement.spacedBy(12.dp),
                        ) {
                            V62AiSummary(
                                state = state,
                                configs = aiConfigs,
                                onAnalyzeAll = onAnalyzeAllAi,
                                onCancel = onCancelAi,
                            )
                            SegmentedTabs(
                                items = listOf("概率", "模型"),
                                selectedIndex = detailTab.coerceIn(0, 1),
                                onSelected = { detailTab = it },
                            )
                            if (detailTab == 0) {
                                V62ProbabilityCard(requireNotNull(report), selectedPosition)
                            } else {
                                RefinedModelCardV2(requireNotNull(report).models)
                            }
                        }
                    }
                }
            }
        } else {
            LazyColumn(
                modifier = Modifier.fillMaxSize(),
                contentPadding = PaddingValues(start = 12.dp, end = 12.dp, top = 12.dp, bottom = 18.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                item("switcher") { CompactLotterySwitcher(state.lottery, onSelectLottery) }
                if (state.snapshot == null || report == null) {
                    item("empty") {
                        EmptyState(
                            title = if (state.isLoading) "正在同步开奖数据" else "暂时无法生成预测",
                            detail = state.error ?: "数据同步完成后会自动生成结果",
                            loading = state.isLoading,
                        )
                    }
                } else {
                    item("live") { V62LiveHero(state, onRefresh) }
                    item("forecast") {
                        V62ForecastHero(report, selectedPosition) { selectedPosition = it }
                    }
                    item("ai") {
                        V62AiSummary(
                            state = state,
                            configs = aiConfigs,
                            onAnalyzeAll = onAnalyzeAllAi,
                            onCancel = onCancelAi,
                        )
                    }
                    item("tabs") {
                        SegmentedTabs(
                            items = listOf("概率", "模型"),
                            selectedIndex = detailTab.coerceIn(0, 1),
                            onSelected = { detailTab = it },
                        )
                    }
                    if (detailTab == 0) {
                        item("probability") { V62ProbabilityCard(report, selectedPosition) }
                    } else {
                        item("models") { RefinedModelCardV2(report.models) }
                    }
                }
            }
        }
    }
}

@Composable
private fun V62LiveHero(state: AppUiState, onRefresh: () -> Unit) {
    val colors = LocalTianjiColors.current
    val snapshot = state.snapshot ?: return
    val deadline = remember(
        snapshot.nextPeriod,
        snapshot.nextDrawAtEpochMs,
        snapshot.serverTimeEpochMs,
        snapshot.sourceHealth.syncedAtEpochMs,
    ) { ForecastDeadlineResolver.resolve(snapshot) }
    var remaining by remember(snapshot.nextPeriod) { mutableIntStateOf(-1) }
    var refreshIssued by remember(snapshot.nextPeriod) { androidx.compose.runtime.mutableStateOf(false) }

    LaunchedEffect(deadline?.epochMs, snapshot.nextPeriod, state.isAiAnalyzing) {
        val target = deadline?.epochMs ?: return@LaunchedEffect
        while (true) {
            remaining = ServerCountdown.remainingSeconds(
                nextDrawAtEpochMs = target,
                serverTimeAtSyncEpochMs = snapshot.serverTimeEpochMs
                    ?: snapshot.sourceHealth.syncedAtEpochMs,
                localSyncedAtEpochMs = snapshot.sourceHealth.syncedAtEpochMs,
                localNowEpochMs = System.currentTimeMillis(),
            )
            if (remaining <= 0) {
                if (!refreshIssued && !state.isAiAnalyzing) {
                    refreshIssued = true
                    delay(1_800L)
                    onRefresh()
                }
                break
            }
            delay(1_000L)
        }
    }

    val sourceTint = when {
        state.error != null -> colors.red
        snapshot.sourceHealth.isFresh -> colors.green
        else -> colors.amber
    }

    SurfaceCard(radius = 24.dp) {
        Column(
            Modifier
                .background(colors.accent.copy(alpha = 0.035f))
                .padding(17.dp),
        ) {
            Row(verticalAlignment = Alignment.Top) {
                Column(Modifier.weight(1f)) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Box(Modifier.size(7.dp).clip(CircleShape).background(sourceTint))
                        Spacer(Modifier.width(7.dp))
                        Text(
                            if (snapshot.sourceHealth.isFresh) "实时开奖已同步" else "正在使用本机缓存",
                            color = sourceTint,
                            fontSize = 12.sp,
                            fontWeight = FontWeight.Bold,
                        )
                    }
                    Spacer(Modifier.height(5.dp))
                    Text(
                        state.lottery.displayName,
                        color = colors.text,
                        fontSize = 22.sp,
                        lineHeight = 28.sp,
                        fontWeight = FontWeight.ExtraBold,
                    )
                    Text(
                        "最新 ${snapshot.latest.period}",
                        color = colors.textDim,
                        fontSize = 12.sp,
                        lineHeight = 17.sp,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
                Column(horizontalAlignment = Alignment.End) {
                    Text("下期开奖", color = colors.textDim, fontSize = 12.sp)
                    Text(
                        if (remaining < 0) "--:--" else "%02d:%02d".format(remaining / 60, remaining % 60),
                        color = colors.accent,
                        fontSize = 27.sp,
                        lineHeight = 32.sp,
                        fontWeight = FontWeight.ExtraBold,
                    )
                    Text(
                        "目标 ${snapshot.nextPeriod}",
                        color = colors.textSoft,
                        fontSize = 11.sp,
                        maxLines = 1,
                    )
                }
            }
            Spacer(Modifier.height(16.dp))
            CompactNumberRowV2(snapshot.latest.numbers, size = 30, spread = true)
            Spacer(Modifier.height(13.dp))
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(14.dp))
                    .background(colors.surfaceStrong.copy(alpha = 0.72f))
                    .border(1.dp, colors.line, RoundedCornerShape(14.dp))
                    .padding(horizontal = 12.dp, vertical = 10.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Icon(Icons.Rounded.Sync, null, tint = sourceTint, modifier = Modifier.size(17.dp))
                Spacer(Modifier.width(8.dp))
                Text(
                    snapshot.sourceHealth.message,
                    color = colors.textSoft,
                    fontSize = 12.sp,
                    lineHeight = 17.sp,
                    modifier = Modifier.weight(1f),
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                )
                Spacer(Modifier.width(8.dp))
                Text(syncAgeV2(snapshot.sourceHealth.syncedAtEpochMs), color = colors.textDim, fontSize = 11.sp)
            }
        }
    }
}

@Composable
private fun V62ForecastHero(
    report: ForecastReport,
    selectedPosition: Int,
    onPosition: (Int) -> Unit,
) {
    val colors = LocalTianjiColors.current
    val position = report.positions.getOrNull(selectedPosition) ?: report.selected
    SurfaceCard(radius = 24.dp) {
        Column(Modifier.padding(17.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Box(
                    modifier = Modifier
                        .size(42.dp)
                        .clip(RoundedCornerShape(14.dp))
                        .background(colors.accentSoft),
                    contentAlignment = Alignment.Center,
                ) {
                    Icon(Icons.Rounded.Psychology, null, tint = colors.accent, modifier = Modifier.size(22.dp))
                }
                Spacer(Modifier.width(11.dp))
                Column(Modifier.weight(1f)) {
                    Text(
                        "第 ${report.targetPeriod} 期",
                        color = colors.text,
                        fontSize = 17.sp,
                        fontWeight = FontWeight.ExtraBold,
                    )
                    Text(
                        "本地模型冻结结果 · 开奖后自动结算",
                        color = colors.textDim,
                        fontSize = 12.sp,
                        lineHeight = 17.sp,
                    )
                }
                StatusChipV2("第${positionNameV2(selectedPosition)}名", colors.accent)
            }
            Spacer(Modifier.height(14.dp))
            PositionSelectorV2(selectedPosition, onPosition)
            Spacer(Modifier.height(16.dp))
            Text("预测六码", color = colors.textDim, fontSize = 12.sp, fontWeight = FontWeight.Bold)
            Spacer(Modifier.height(10.dp))
            CompactNumberRowV2(position.top6, size = 37, spread = true)
            Spacer(Modifier.height(15.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                CompactMetricV2("覆盖概率", "${(position.coverage6 * 100).format1V2()}%", Modifier.weight(1f))
                CompactMetricV2("边界优势", "${(position.boundaryMargin * 100).format2V2()}%", Modifier.weight(1f))
            }
            Spacer(Modifier.height(9.dp))
            Text(
                "训练窗口 ${report.historySize} 期 · 概率与模型细节已下沉到详情",
                color = colors.textDim,
                fontSize = 11.sp,
                lineHeight = 16.sp,
            )
        }
    }
}

@Composable
private fun V62AiSummary(
    state: AppUiState,
    configs: List<AiConfig>,
    onAnalyzeAll: () -> Unit,
    onCancel: (String) -> Unit,
) {
    val colors = LocalTianjiColors.current
    val complete = configs.filter(AiConfig::isComplete)
    val forecasts = state.aiForecasts
    val positionSupport = forecasts.groupingBy { it.position }.eachCount()
    val lead = positionSupport.maxByOrNull { it.value }
    val running = state.aiStatuses.values.filter {
        it.state == AiConnectionState.ANALYZING || it.state == AiConnectionState.TESTING
    }
    val failed = state.aiStatuses.values.count { it.state == AiConnectionState.FAILED }

    SurfaceCard(radius = 24.dp) {
        Column(Modifier.padding(17.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Box(
                    modifier = Modifier
                        .size(42.dp)
                        .clip(RoundedCornerShape(14.dp))
                        .background(colors.violet.copy(alpha = 0.13f)),
                    contentAlignment = Alignment.Center,
                ) {
                    Icon(Icons.Rounded.AutoAwesome, null, tint = colors.violet, modifier = Modifier.size(22.dp))
                }
                Spacer(Modifier.width(11.dp))
                Column(Modifier.weight(1f)) {
                    Text("AI 联合判断", color = colors.text, fontSize = 16.sp, fontWeight = FontWeight.ExtraBold)
                    Text(
                        "固定目标 235780 · 只比较第 1～10 名位置",
                        color = colors.textDim,
                        fontSize = 12.sp,
                        lineHeight = 17.sp,
                    )
                }
                StatusChipV2(
                    when {
                        state.isAiAnalyzing -> "运行中"
                        forecasts.isNotEmpty() -> "已冻结"
                        else -> "待生成"
                    },
                    when {
                        state.isAiAnalyzing -> colors.accent
                        forecasts.isNotEmpty() -> colors.green
                        else -> colors.textDim
                    },
                )
            }

            Spacer(Modifier.height(14.dp))
            if (forecasts.isNotEmpty() && lead != null) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clip(RoundedCornerShape(16.dp))
                        .background(colors.violet.copy(alpha = 0.08f))
                        .border(1.dp, colors.violet.copy(alpha = 0.18f), RoundedCornerShape(16.dp))
                        .padding(13.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Column(Modifier.weight(1f)) {
                        Text("当前主判断", color = colors.textDim, fontSize = 12.sp)
                        Text(
                            "第${positionNameV2(lead.key)}名",
                            color = colors.violet,
                            fontSize = 24.sp,
                            fontWeight = FontWeight.ExtraBold,
                        )
                    }
                    Column(horizontalAlignment = Alignment.End) {
                        Text("模型支持", color = colors.textDim, fontSize = 12.sp)
                        Text(
                            "${lead.value}/${forecasts.size}",
                            color = colors.text,
                            fontSize = 20.sp,
                            fontWeight = FontWeight.ExtraBold,
                        )
                    }
                }
                Spacer(Modifier.height(10.dp))
                forecasts.take(4).forEach { forecast ->
                    Row(
                        modifier = Modifier.fillMaxWidth().padding(vertical = 5.dp),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Box(Modifier.size(7.dp).clip(CircleShape).background(colors.violet))
                        Spacer(Modifier.width(8.dp))
                        Text(
                            forecast.profileName.ifBlank { forecast.model },
                            color = colors.textSoft,
                            fontSize = 12.sp,
                            modifier = Modifier.weight(1f),
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis,
                        )
                        Text(
                            "第${positionNameV2(forecast.position)}名",
                            color = colors.violet,
                            fontSize = 12.sp,
                            fontWeight = FontWeight.Bold,
                        )
                    }
                }
                if (forecasts.size > 4) {
                    Spacer(Modifier.height(5.dp))
                    Text(
                        "另外 ${forecasts.size - 4} 个模型已完成 · 可在 AI 对话中查看完整判断",
                        color = colors.textDim,
                        fontSize = 11.sp,
                        lineHeight = 16.sp,
                    )
                }
            } else {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clip(RoundedCornerShape(16.dp))
                        .background(colors.surfaceStrong.copy(alpha = 0.65f))
                        .padding(13.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Icon(Icons.Rounded.Bolt, null, tint = colors.amber, modifier = Modifier.size(19.dp))
                    Spacer(Modifier.width(8.dp))
                    Text(
                        if (complete.isEmpty()) "先在设置中配置可用 AI 接口" else "尚未生成本期 AI 判断",
                        color = colors.textSoft,
                        fontSize = 12.sp,
                        modifier = Modifier.weight(1f),
                    )
                }
            }

            if (running.isNotEmpty() || failed > 0) {
                Spacer(Modifier.height(10.dp))
                Text(
                    "可用 ${complete.size} · 正在 ${running.size} · 结果 ${forecasts.size} · 失败 $failed",
                    color = if (failed > 0) colors.red else colors.textDim,
                    fontSize = 12.sp,
                    fontWeight = FontWeight.SemiBold,
                )
                running.firstOrNull()?.let { status ->
                    Button(
                        onClick = { onCancel(status.profileId) },
                        modifier = Modifier.fillMaxWidth().padding(top = 8.dp).height(48.dp),
                        shape = RoundedCornerShape(14.dp),
                        colors = ButtonDefaults.buttonColors(
                            containerColor = colors.amber.copy(alpha = 0.12f),
                            contentColor = colors.amber,
                        ),
                    ) {
                        Text("取消当前 AI 任务", fontWeight = FontWeight.Bold)
                    }
                }
            }

            Spacer(Modifier.height(13.dp))
            Button(
                onClick = onAnalyzeAll,
                enabled = complete.isNotEmpty() && !state.isAiAnalyzing,
                modifier = Modifier.fillMaxWidth().height(48.dp),
                shape = RoundedCornerShape(15.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = colors.accent,
                    contentColor = Color.White,
                    disabledContainerColor = colors.accent.copy(alpha = 0.16f),
                    disabledContentColor = colors.textDim,
                ),
            ) {
                if (state.isAiAnalyzing) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(18.dp),
                        color = Color.White,
                        strokeWidth = 2.dp,
                    )
                    Spacer(Modifier.width(8.dp))
                }
                Text(
                    if (state.isAiAnalyzing) "正在生成本期 AI 判断" else "生成本期 AI 判断",
                    fontSize = 13.sp,
                    fontWeight = FontWeight.ExtraBold,
                )
            }
        }
    }
}

@Composable
private fun V62ProbabilityCard(
    report: ForecastReport,
    selectedPosition: Int,
) {
    val colors = LocalTianjiColors.current
    val prediction = report.positions.getOrNull(selectedPosition) ?: report.selected
    val ranked = prediction.probabilities.mapIndexed { index, value -> index + 1 to value }
        .sortedByDescending { it.second }

    SurfaceCard(radius = 22.dp) {
        Column(Modifier.padding(16.dp)) {
            Text("号码概率", color = colors.text, fontSize = 16.sp, fontWeight = FontWeight.ExtraBold)
            Text(
                "第${positionNameV2(selectedPosition)}名 · 跟随上方名次选择",
                color = colors.textDim,
                fontSize = 12.sp,
                lineHeight = 17.sp,
            )
            Spacer(Modifier.height(12.dp))
            ranked.forEachIndexed { index, (number, probability) ->
                if (index == 6) {
                    Row(
                        modifier = Modifier.fillMaxWidth().padding(top = 5.dp, bottom = 7.dp),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Box(Modifier.weight(1f).height(1.dp).background(colors.lineStrong))
                        Text(
                            "六码边界",
                            color = colors.amber,
                            fontSize = 11.sp,
                            fontWeight = FontWeight.Bold,
                            modifier = Modifier.padding(horizontal = 9.dp),
                        )
                        Box(Modifier.weight(1f).height(1.dp).background(colors.lineStrong))
                    }
                }
                Row(
                    modifier = Modifier.fillMaxWidth().padding(vertical = 5.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Text(
                        (index + 1).toString(),
                        color = colors.textDim,
                        fontSize = 11.sp,
                        modifier = Modifier.width(22.dp),
                        textAlign = TextAlign.Center,
                    )
                    LotteryBall(number, size = 29.dp, muted = index >= 6)
                    Spacer(Modifier.width(9.dp))
                    LinearProgressIndicator(
                        progress = { probability.toFloat().coerceIn(0f, 1f) },
                        modifier = Modifier.weight(1f).height(6.dp).clip(CircleShape),
                        color = if (index < 6) colors.accent else colors.textDim,
                        trackColor = colors.line,
                    )
                    Spacer(Modifier.width(9.dp))
                    Text(
                        "${(probability * 100).format1V2()}%",
                        color = colors.textSoft,
                        fontSize = 12.sp,
                        modifier = Modifier.width(52.dp),
                        textAlign = TextAlign.End,
                    )
                }
            }
        }
    }
}
