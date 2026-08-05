package com.tianji.probabilitylab.nativev4.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
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
import androidx.compose.material.icons.rounded.Psychology
import androidx.compose.material.icons.rounded.QueryStats
import androidx.compose.material.icons.rounded.Security
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
import androidx.compose.runtime.mutableStateOf
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
import com.tianji.probabilitylab.nativev4.ai.AiConsensusEngine
import com.tianji.probabilitylab.nativev4.model.EvidenceMode
import com.tianji.probabilitylab.nativev4.model.ForecastDeadlineResolver
import com.tianji.probabilitylab.nativev4.model.ForecastReport
import com.tianji.probabilitylab.nativev4.model.LotteryType
import com.tianji.probabilitylab.nativev4.model.ModelPerformance
import com.tianji.probabilitylab.nativev4.model.ServerCountdown
import com.tianji.probabilitylab.nativev4.ui.theme.LocalTianjiColors
import kotlinx.coroutines.delay

@Composable
fun RefinedForecastScreen(
    state: AppUiState,
    aiConfigs: List<AiConfig>,
    onSelectLottery: (LotteryType) -> Unit,
    onRefresh: () -> Unit,
    onAnalyzeAllAi: () -> Unit,
    onCancelAi: (String) -> Unit,
    modifier: Modifier = Modifier,
) {
    var section by rememberSaveable(state.lottery.apiKey) { mutableIntStateOf(0) }
    var selectedPosition by rememberSaveable(state.report?.targetPeriod) {
        mutableIntStateOf(state.report?.selectedPosition ?: 0)
    }

    LazyColumn(
        modifier = modifier,
        contentPadding = PaddingValues(start = 12.dp, end = 12.dp, top = 12.dp, bottom = 96.dp),
        verticalArrangement = Arrangement.spacedBy(11.dp),
    ) {
        item("lottery-switch") { CompactLotterySwitcher(state.lottery, onSelectLottery) }

        if (state.snapshot == null || state.report == null) {
            item("empty") {
                EmptyState(
                    title = if (state.isLoading) "正在同步真实开奖" else "暂时无法生成预测",
                    detail = state.error ?: "同步完成后会执行本机模型与前向验证",
                    loading = state.isLoading,
                )
            }
        } else {
            val report = state.report
            item("live-summary") { RefinedLiveCard(state, onRefresh) }
            item("tabs") {
                SegmentedTabs(
                    items = listOf("概览", "概率", "模型"),
                    selectedIndex = section,
                    onSelected = { section = it },
                )
            }
            when (section) {
                0 -> {
                    item("forecast") {
                        RefinedForecastCard(report, selectedPosition) { selectedPosition = it }
                    }
                    item("ai") {
                        RefinedAiPanel(
                            state = state,
                            configs = aiConfigs,
                            onAnalyzeAll = onAnalyzeAllAi,
                            onCancel = onCancelAi,
                        )
                    }
                }
                1 -> item("probability") {
                    RefinedProbabilityCard(report, selectedPosition) { selectedPosition = it }
                }
                else -> item("models") { RefinedModelCardV2(report.models) }
            }
        }
    }
}

@Composable
private fun RefinedLiveCard(state: AppUiState, onRefresh: () -> Unit) {
    val colors = LocalTianjiColors.current
    val snapshot = state.snapshot ?: return
    val deadline = remember(
        snapshot.nextPeriod,
        snapshot.nextDrawAtEpochMs,
        snapshot.serverTimeEpochMs,
        snapshot.sourceHealth.syncedAtEpochMs,
    ) { ForecastDeadlineResolver.resolve(snapshot) }
    var remaining by remember(snapshot.nextPeriod) { mutableIntStateOf(-1) }
    var refreshIssued by remember(snapshot.nextPeriod) { mutableStateOf(false) }

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
                    delay(2_000)
                    onRefresh()
                }
                break
            }
            delay(1_000)
        }
    }

    val sourceTint = when {
        state.error != null -> colors.red
        snapshot.sourceHealth.isFresh -> colors.green
        else -> colors.amber
    }
    SurfaceCard(radius = 21.dp) {
        Column(Modifier.padding(15.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f)) {
                    Text(
                        state.lottery.displayName,
                        color = colors.text,
                        fontSize = 17.sp,
                        fontWeight = FontWeight.ExtraBold,
                    )
                    Text(
                        "最新 ${snapshot.latest.period} · ${snapshot.latest.drawTime.ifBlank { "真实开奖已入库" }}",
                        color = colors.textDim,
                        fontSize = 10.sp,
                        lineHeight = 15.sp,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
                Column(horizontalAlignment = Alignment.End) {
                    Text(
                        if (remaining < 0) "--:--" else "%02d:%02d".format(remaining / 60, remaining % 60),
                        color = colors.accent,
                        fontSize = 18.sp,
                        fontWeight = FontWeight.ExtraBold,
                    )
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Box(Modifier.size(6.dp).clip(CircleShape).background(sourceTint))
                        Spacer(Modifier.width(5.dp))
                        Text(
                            if (snapshot.sourceHealth.isFresh) "接口已同步" else "本机缓存",
                            color = sourceTint,
                            fontSize = 10.sp,
                            fontWeight = FontWeight.Bold,
                        )
                    }
                }
            }
            Spacer(Modifier.height(13.dp))
            CompactNumberRowV2(snapshot.latest.numbers, size = 29)
            Spacer(Modifier.height(12.dp))
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(13.dp))
                    .background(colors.surfaceStrong)
                    .border(1.dp, colors.line, RoundedCornerShape(13.dp))
                    .padding(horizontal = 11.dp, vertical = 9.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Icon(Icons.Rounded.Sync, null, tint = sourceTint, modifier = Modifier.size(16.dp))
                Spacer(Modifier.width(7.dp))
                Text(
                    snapshot.sourceHealth.message,
                    color = colors.textSoft,
                    fontSize = 10.sp,
                    lineHeight = 15.sp,
                    modifier = Modifier.weight(1f),
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                )
                Text(syncAgeV2(snapshot.sourceHealth.syncedAtEpochMs), color = colors.textDim, fontSize = 10.sp)
            }
        }
    }
}

@Composable
private fun RefinedForecastCard(
    report: ForecastReport,
    selectedPosition: Int,
    onPosition: (Int) -> Unit,
) {
    val colors = LocalTianjiColors.current
    val position = report.positions.getOrNull(selectedPosition) ?: report.selected
    SurfaceCard(radius = 21.dp) {
        Column(Modifier.padding(15.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Box(
                    modifier = Modifier
                        .size(39.dp)
                        .clip(RoundedCornerShape(13.dp))
                        .background(colors.accentSoft),
                    contentAlignment = Alignment.Center,
                ) {
                    Icon(Icons.Rounded.Psychology, null, tint = colors.accent, modifier = Modifier.size(21.dp))
                }
                Spacer(Modifier.width(10.dp))
                Column(Modifier.weight(1f)) {
                    Text(
                        "第 ${report.targetPeriod} 期",
                        color = colors.text,
                        fontSize = 16.sp,
                        fontWeight = FontWeight.ExtraBold,
                    )
                    Text(
                        if (report.mode == EvidenceMode.CERTIFIED) "前向证据通过" else "观察模式 · 暂未认证",
                        color = if (report.mode == EvidenceMode.CERTIFIED) colors.green else colors.amber,
                        fontSize = 10.sp,
                        fontWeight = FontWeight.Bold,
                    )
                }
                StatusChipV2("第${positionNameV2(selectedPosition)}名", colors.accent)
            }
            Spacer(Modifier.height(13.dp))
            PositionSelectorV2(selectedPosition, onPosition)
            Spacer(Modifier.height(15.dp))
            Text(
                if (report.displayUsesShadow) "影子实验六码" else "本机集成六码",
                color = colors.textDim,
                fontSize = 11.sp,
                fontWeight = FontWeight.Bold,
            )
            Spacer(Modifier.height(10.dp))
            CompactNumberRowV2(position.top6, size = 36, spread = true)
            Spacer(Modifier.height(14.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                CompactMetricV2(
                    label = "覆盖概率",
                    value = "${(position.coverage6 * 100).format1V2()}%",
                    modifier = Modifier.weight(1f),
                )
                CompactMetricV2(
                    label = "边界优势",
                    value = "${(position.boundaryMargin * 100).format2V2()}%",
                    modifier = Modifier.weight(1f),
                )
                CompactMetricV2("训练历史", report.historySize.toString(), Modifier.weight(1f))
            }
        }
    }
}

@Composable
private fun RefinedAiPanel(
    state: AppUiState,
    configs: List<AiConfig>,
    onAnalyzeAll: () -> Unit,
    onCancel: (String) -> Unit,
) {
    val colors = LocalTianjiColors.current
    val complete = configs.filter(AiConfig::isComplete)
    val evaluation = remember(state.aiForecasts, state.aiProfileAudits) {
        AiConsensusEngine.evaluateForecasts(state.aiForecasts, state.aiProfileAudits)
    }
    SurfaceCard(radius = 21.dp) {
        Column(Modifier.padding(15.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Box(
                    modifier = Modifier
                        .size(39.dp)
                        .clip(RoundedCornerShape(13.dp))
                        .background(colors.violet.copy(alpha = 0.13f)),
                    contentAlignment = Alignment.Center,
                ) {
                    Icon(Icons.Rounded.AutoAwesome, null, tint = colors.violet, modifier = Modifier.size(21.dp))
                }
                Spacer(Modifier.width(10.dp))
                Column(Modifier.weight(1f)) {
                    Text("AI 联合分析", color = colors.text, fontSize = 15.sp, fontWeight = FontWeight.ExtraBold)
                    Text(
                        "${complete.size} 个可用配置 · 独立分析后再形成共识",
                        color = colors.textDim,
                        fontSize = 10.sp,
                    )
                }
                val tint = when {
                    state.isAiAnalyzing -> colors.accent
                    evaluation.stable -> colors.green
                    state.aiForecasts.isNotEmpty() -> colors.amber
                    else -> colors.textDim
                }
                Text(
                    when {
                        state.isAiAnalyzing -> "分析中"
                        evaluation.stable -> "已形成共识"
                        state.aiForecasts.isNotEmpty() -> "模型有分歧"
                        else -> "等待分析"
                    },
                    color = tint,
                    fontSize = 10.sp,
                    fontWeight = FontWeight.Bold,
                )
            }

            if (state.aiStatuses.isNotEmpty()) {
                Spacer(Modifier.height(12.dp))
                state.aiStatuses.values.take(3).forEach { status ->
                    val tint = when (status.state) {
                        AiConnectionState.CONNECTED -> colors.green
                        AiConnectionState.FAILED -> colors.red
                        AiConnectionState.ANALYZING, AiConnectionState.TESTING -> colors.accent
                        else -> colors.amber
                    }
                    Row(
                        modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Box(Modifier.size(7.dp).clip(CircleShape).background(tint))
                        Spacer(Modifier.width(8.dp))
                        Text(
                            status.message,
                            color = colors.textSoft,
                            fontSize = 10.sp,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis,
                            modifier = Modifier.weight(1f),
                        )
                        if (status.state == AiConnectionState.ANALYZING ||
                            status.state == AiConnectionState.TESTING
                        ) {
                            Text(
                                "取消",
                                color = colors.amber,
                                fontSize = 10.sp,
                                fontWeight = FontWeight.Bold,
                                modifier = Modifier
                                    .clip(CircleShape)
                                    .clickable { onCancel(status.profileId) }
                                    .padding(horizontal = 8.dp, vertical = 5.dp),
                            )
                        }
                    }
                }
            }

            evaluation.consensus?.takeIf { evaluation.stable }?.let { consensus ->
                Spacer(Modifier.height(12.dp))
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clip(RoundedCornerShape(16.dp))
                        .background(colors.accentSoft)
                        .border(1.dp, colors.accent.copy(alpha = 0.20f), RoundedCornerShape(16.dp))
                        .padding(12.dp),
                ) {
                    Text(
                        "AI 共识 · 第${positionNameV2(consensus.position)}名",
                        color = colors.accent,
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Bold,
                    )
                    Spacer(Modifier.height(9.dp))
                    CompactNumberRowV2(consensus.top6, size = 32, spread = true)
                    Spacer(Modifier.height(8.dp))
                    Text(
                        "${consensus.supportingProfiles}/${consensus.totalProfiles} 个独立模型支持 · " +
                            "边界 ${(consensus.confidenceMargin * 100).format2V2()}%",
                        color = colors.textDim,
                        fontSize = 10.sp,
                    )
                }
            }

            Spacer(Modifier.height(13.dp))
            Button(
                onClick = onAnalyzeAll,
                enabled = complete.isNotEmpty() && !state.isAiAnalyzing,
                modifier = Modifier.fillMaxWidth().height(45.dp),
                shape = RoundedCornerShape(14.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = colors.accent,
                    contentColor = Color.White,
                    disabledContainerColor = colors.accent.copy(alpha = 0.16f),
                    disabledContentColor = colors.textDim,
                ),
            ) {
                if (state.isAiAnalyzing) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(17.dp),
                        color = Color.White,
                        strokeWidth = 2.dp,
                    )
                    Spacer(Modifier.width(8.dp))
                }
                Text(
                    if (state.isAiAnalyzing) "多个 AI 正在独立分析" else "开始全部 AI 分析",
                    fontSize = 12.sp,
                    fontWeight = FontWeight.Bold,
                )
            }
        }
    }
}

@Composable
private fun RefinedProbabilityCard(
    report: ForecastReport,
    selectedPosition: Int,
    onPosition: (Int) -> Unit,
) {
    val colors = LocalTianjiColors.current
    val prediction = report.positions.getOrNull(selectedPosition) ?: report.selected
    val ranked = prediction.probabilities.mapIndexed { index, value -> index + 1 to value }
        .sortedByDescending { it.second }
    SurfaceCard(radius = 21.dp) {
        Column(Modifier.padding(15.dp)) {
            Text("号码概率", color = colors.text, fontSize = 16.sp, fontWeight = FontWeight.ExtraBold)
            Text(
                "第${positionNameV2(selectedPosition)}名 · 只显示模型输出，不代表确定结果",
                color = colors.textDim,
                fontSize = 10.sp,
            )
            Spacer(Modifier.height(12.dp))
            PositionSelectorV2(selectedPosition, onPosition)
            Spacer(Modifier.height(13.dp))
            ranked.forEachIndexed { index, (number, probability) ->
                Row(
                    modifier = Modifier.fillMaxWidth().padding(vertical = 5.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Text(
                        (index + 1).toString(),
                        color = colors.textDim,
                        fontSize = 10.sp,
                        modifier = Modifier.width(22.dp),
                        textAlign = TextAlign.Center,
                    )
                    LotteryBall(number, size = 28.dp, muted = index >= 6)
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
                        fontSize = 10.sp,
                        modifier = Modifier.width(48.dp),
                        textAlign = TextAlign.End,
                    )
                }
            }
        }
    }
}

@Composable
internal fun RefinedModelCardV2(models: List<ModelPerformance>) {
    val colors = LocalTianjiColors.current
    SurfaceCard(radius = 21.dp) {
        Column(Modifier.padding(15.dp)) {
            Text("11 模型前向竞赛", color = colors.text, fontSize = 16.sp, fontWeight = FontWeight.ExtraBold)
            Text(
                "正式权重来自时间切分验证，没有优势的模型权重为 0",
                color = colors.textDim,
                fontSize = 10.sp,
            )
            Spacer(Modifier.height(12.dp))
            models.forEachIndexed { index, model ->
                RefinedModelRowV2(index + 1, model)
                if (index != models.lastIndex) Spacer(Modifier.height(7.dp))
            }
        }
    }
}

@Composable
fun StrategyAndEvidenceScreen(
    state: AppUiState,
    onSelectLottery: (LotteryType) -> Unit,
    modifier: Modifier = Modifier,
) {
    var tab by rememberSaveable(state.lottery.apiKey) { mutableIntStateOf(0) }
    val report = state.report
    LazyColumn(
        modifier = modifier,
        contentPadding = PaddingValues(12.dp, 12.dp, 12.dp, 96.dp),
        verticalArrangement = Arrangement.spacedBy(11.dp),
    ) {
        item { CompactLotterySwitcher(state.lottery, onSelectLottery) }
        item { SegmentedTabs(listOf("策略", "验证"), tab) { tab = it } }
        if (report == null) {
            item { EmptyState("策略等待模型", state.error ?: "请先同步真实历史", state.isLoading) }
        } else if (tab == 0) {
            item { RefinedStrategyCard(report, state) }
        } else {
            item { RefinedEvidenceCard(report, state) }
            item { RefinedModelCardV2(report.models) }
        }
    }
}

@Composable
private fun RefinedStrategyCard(report: ForecastReport, state: AppUiState) {
    val colors = LocalTianjiColors.current
    val selected = report.selected
    SurfaceCard(radius = 21.dp) {
        Column(Modifier.padding(15.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Box(
                    Modifier.size(39.dp).clip(RoundedCornerShape(13.dp)).background(colors.accentSoft),
                    contentAlignment = Alignment.Center,
                ) {
                    Icon(Icons.Rounded.Security, null, tint = colors.accent, modifier = Modifier.size(21.dp))
                }
                Spacer(Modifier.width(10.dp))
                Column(Modifier.weight(1f)) {
                    Text("七码三段观察", color = colors.text, fontSize = 16.sp, fontWeight = FontWeight.ExtraBold)
                    Text(
                        "第${positionNameV2(report.selectedPosition)}名 · 目标期 ${report.targetPeriod}",
                        color = colors.textDim,
                        fontSize = 10.sp,
                    )
                }
                StatusChipV2(
                    if (report.mode == EvidenceMode.CERTIFIED) "证据通过" else "观察模式",
                    if (report.mode == EvidenceMode.CERTIFIED) colors.green else colors.amber,
                )
            }
            Spacer(Modifier.height(15.dp))
            CompactNumberRowV2(selected.top7, size = 33, spread = true)
            Spacer(Modifier.height(14.dp))
            val excluded = (1..10).filterNot { it in selected.top7 }
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text("排除", color = colors.textDim, fontSize = 10.sp, modifier = Modifier.width(42.dp))
                excluded.forEach {
                    LotteryBall(it, size = 27.dp, muted = true)
                    Spacer(Modifier.width(6.dp))
                }
            }
            Spacer(Modifier.height(14.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                listOf("第一段" to "3 单位", "第二段" to "5 单位", "第三段" to "7 单位").forEach {
                    CompactMetricV2(it.first, it.second, Modifier.weight(1f))
                }
            }
            Spacer(Modifier.height(9.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                CompactMetricV2(
                    "留出七码",
                    "${(report.top7HitRate * 100).format1V2()}%",
                    Modifier.weight(1f),
                )
                CompactMetricV2(
                    "盈亏门槛",
                    "${(report.breakEvenTop7 * 100).format1V2()}%",
                    Modifier.weight(1f),
                )
                CompactMetricV2("真实前向", state.liveAudit.settled.toString(), Modifier.weight(1f))
            }
            Spacer(Modifier.height(11.dp))
            Text(
                "仅用于统计实验和证据观察，不承诺盈利或必中。",
                color = colors.textDim,
                fontSize = 10.sp,
                lineHeight = 15.sp,
            )
        }
    }
}

@Composable
private fun RefinedEvidenceCard(report: ForecastReport, state: AppUiState) {
    val colors = LocalTianjiColors.current
    SurfaceCard(radius = 21.dp) {
        Column(Modifier.padding(15.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Rounded.QueryStats, null, tint = colors.accent, modifier = Modifier.size(22.dp))
                Spacer(Modifier.width(9.dp))
                Text("时间切分留出验证", color = colors.text, fontSize = 16.sp, fontWeight = FontWeight.ExtraBold)
            }
            Spacer(Modifier.height(12.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                CompactMetricV2(
                    "六码命中",
                    "${(report.top6HitRate * 100).format1V2()}%",
                    Modifier.weight(1f),
                )
                CompactMetricV2(
                    "七码命中",
                    "${(report.top7HitRate * 100).format1V2()}%",
                    Modifier.weight(1f),
                )
                CompactMetricV2("留出期数", report.validationDraws.toString(), Modifier.weight(1f))
            }
            Spacer(Modifier.height(8.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                CompactMetricV2(
                    "六码下界",
                    "${(report.top6Interval.low * 100).format1V2()}%",
                    Modifier.weight(1f),
                )
                CompactMetricV2(
                    "七码下界",
                    "${(report.top7Interval.low * 100).format1V2()}%",
                    Modifier.weight(1f),
                )
                CompactMetricV2("LogLoss", report.averageLogLoss.format2V2(), Modifier.weight(1f))
            }
            Spacer(Modifier.height(14.dp))
            Text("证据闸门", color = colors.textSoft, fontSize = 12.sp, fontWeight = FontWeight.Bold)
            Spacer(Modifier.height(5.dp))
            if (report.blockedReasons.isEmpty()) {
                EvidenceRowV2("全部证据闸门已通过", true)
            } else {
                report.blockedReasons.forEach { EvidenceRowV2(it, false) }
            }
            Spacer(Modifier.height(8.dp))
            EvidenceRowV2(
                if (state.archiveIntegrity.isValid) "预测档案完整性链正常" else "预测档案完整性链异常",
                state.archiveIntegrity.isValid,
            )
        }
    }
}
