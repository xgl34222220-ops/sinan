package com.tianji.probabilitylab.nativev4.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.Analytics
import androidx.compose.material.icons.rounded.AutoAwesome
import androidx.compose.material.icons.rounded.AutoGraph
import androidx.compose.material.icons.rounded.CheckCircle
import androidx.compose.material.icons.rounded.CloudDone
import androidx.compose.material.icons.rounded.ColorLens
import androidx.compose.material.icons.rounded.ErrorOutline
import androidx.compose.material.icons.rounded.Fingerprint
import androidx.compose.material.icons.rounded.Info
import androidx.compose.material.icons.rounded.LockClock
import androidx.compose.material.icons.rounded.Memory
import androidx.compose.material.icons.rounded.QueryStats
import androidx.compose.material.icons.rounded.Schedule
import androidx.compose.material.icons.rounded.Science
import androidx.compose.material.icons.rounded.Security
import androidx.compose.material.icons.rounded.Storage
import androidx.compose.material.icons.rounded.Wifi
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.tianji.probabilitylab.nativev4.AppUiState
import com.tianji.probabilitylab.nativev4.BuildConfig
import com.tianji.probabilitylab.nativev4.ai.AiAnalysisMode
import com.tianji.probabilitylab.nativev4.ai.AiConfig
import com.tianji.probabilitylab.nativev4.ai.AiConnectionState
import com.tianji.probabilitylab.nativev4.ai.AiConsensusEngine
import com.tianji.probabilitylab.nativev4.ai.AiConsensusRecord
import com.tianji.probabilitylab.nativev4.ai.AiForecastRecord
import com.tianji.probabilitylab.nativev4.ai.AiProfileAudit
import com.tianji.probabilitylab.nativev4.ai.AiProvider
import com.tianji.probabilitylab.nativev4.ai.AiReasoningEngine
import com.tianji.probabilitylab.nativev4.ai.AiReasoningMode
import com.tianji.probabilitylab.nativev4.ai.AiReasoningProtocol
import com.tianji.probabilitylab.nativev4.ai.AiReasoningState
import com.tianji.probabilitylab.nativev4.model.Draw
import com.tianji.probabilitylab.nativev4.model.EvidenceMode
import com.tianji.probabilitylab.nativev4.model.ForecastDeadline
import com.tianji.probabilitylab.nativev4.model.ForecastDeadlineResolver
import com.tianji.probabilitylab.nativev4.model.ForecastReport
import com.tianji.probabilitylab.nativev4.model.LockedForecast
import com.tianji.probabilitylab.nativev4.model.LotteryType
import com.tianji.probabilitylab.nativev4.model.ModelPerformance
import com.tianji.probabilitylab.nativev4.model.ServerCountdown
import com.tianji.probabilitylab.nativev4.ui.theme.LocalTianjiColors
import com.tianji.probabilitylab.nativev4.ui.theme.PaletteMode
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import kotlinx.coroutines.delay
import kotlin.math.min

@Composable
fun ForecastScreen(
    state: AppUiState,
    aiConfigs: List<AiConfig>,
    onSelectLottery: (LotteryType) -> Unit,
    onRefresh: () -> Unit,
    onAnalyzeAllAi: () -> Unit,
    onCancelAi: (String) -> Unit,
    modifier: Modifier = Modifier,
) {
    LazyColumn(
        modifier = modifier,
        contentPadding = androidx.compose.foundation.layout.PaddingValues(
            start = 12.dp,
            end = 12.dp,
            top = 14.dp,
            bottom = 124.dp,
        ),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item(key = "game-switcher") { GameSwitcher(state.lottery, onSelectLottery) }
        when {
            state.snapshot != null && state.report != null -> {
                item(key = "live-draw") {
                    LiveDrawCard(
                        snapshot = state.snapshot,
                        lottery = state.lottery,
                        isRefreshing = state.isRefreshing,
                        error = state.error,
                        onRefresh = onRefresh,
                    )
                }
                item(key = "native-forecast") { ForecastHero(state.report) }
                item(key = "ai-analysis") {
                    AiAnalysisPanel(state, aiConfigs, onAnalyzeAllAi, onCancelAi)
                }
                item(key = "probability-matrix") { ProbabilityPanel(state.report) }
                item(key = "model-panel") { CompactModelPanel(state.report.models) }
            }
            state.isLoading -> item {
                EmptyState(
                    "正在同步真实开奖",
                    "同步完成后在本机训练 11 模型并执行时间切分验证",
                    true,
                )
            }
            else -> item {
                EmptyState("暂时无法生成预测", state.error ?: "没有足够的真实历史数据")
            }
        }
    }
}

@Composable
private fun LiveDrawCard(
    snapshot: com.tianji.probabilitylab.nativev4.model.DrawSnapshot,
    lottery: LotteryType,
    isRefreshing: Boolean,
    error: String?,
    onRefresh: () -> Unit,
) {
    val colors = LocalTianjiColors.current
    val deadline = remember(
        snapshot.nextPeriod,
        snapshot.nextDrawAtEpochMs,
        snapshot.latest.drawTime,
        snapshot.serverTimeEpochMs,
        snapshot.sourceHealth.syncedAtEpochMs,
    ) { ForecastDeadlineResolver.resolve(snapshot) }
    val sourceTint = when {
        error != null -> colors.red
        snapshot.sourceHealth.isFresh -> colors.green
        else -> colors.amber
    }
    val sourceLabel = when {
        error != null -> "同步异常"
        snapshot.sourceHealth.isFresh -> "接口已同步"
        else -> "本机缓存"
    }
    SurfaceCard {
        Column(Modifier.padding(18.dp)) {
            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.Top) {
                Column(Modifier.weight(1f)) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Box(Modifier.size(6.dp).clip(CircleShape).background(sourceTint))
                        Spacer(Modifier.width(7.dp))
                        Text(
                            "LIVE DRAW",
                            color = colors.textDim,
                            fontSize = 9.sp,
                            fontWeight = FontWeight.Bold,
                            letterSpacing = 2.sp,
                        )
                    }
                    Spacer(Modifier.height(9.dp))
                    Text(
                        lottery.displayName,
                        color = colors.text,
                        fontSize = 21.sp,
                        fontWeight = FontWeight.ExtraBold,
                    )
                }
                Row(
                    modifier = Modifier
                        .clip(CircleShape)
                        .background(sourceTint.copy(alpha = 0.07f))
                        .border(1.dp, sourceTint.copy(alpha = 0.22f), CircleShape)
                        .padding(horizontal = 10.dp, vertical = 8.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Icon(
                        Icons.Rounded.Wifi,
                        null,
                        tint = sourceTint,
                        modifier = Modifier.size(14.dp),
                    )
                    Spacer(Modifier.width(5.dp))
                    Text(
                        sourceLabel,
                        color = sourceTint,
                        fontSize = 9.sp,
                        fontWeight = FontWeight.Bold,
                    )
                }
            }
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = 18.dp)
                    .clip(RoundedCornerShape(14.dp))
                    .background(Color.Black.copy(alpha = 0.13f))
                    .border(1.dp, colors.line, RoundedCornerShape(14.dp))
                    .padding(horizontal = 14.dp, vertical = 11.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Column(Modifier.weight(1f)) {
                    Text("最新期号", color = colors.textDim, fontSize = 8.sp)
                    Spacer(Modifier.height(4.dp))
                    Text(
                        snapshot.latest.period,
                        color = colors.textSoft,
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Bold,
                    )
                }
                Box(Modifier.width(1.dp).height(24.dp).background(colors.line))
                NextDrawCountdown(
                    snapshot = snapshot,
                    deadline = deadline,
                    isRefreshing = isRefreshing,
                    onRefresh = onRefresh,
                    modifier = Modifier.weight(1f),
                )
            }
            Spacer(Modifier.height(20.dp))
            DrawBallGrid(snapshot.latest.numbers)
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = 17.dp)
                    .border(width = 0.dp, color = Color.Transparent)
                    .padding(top = 12.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                Text(
                    snapshot.latest.drawTime.ifBlank { "真实开奖已入库" },
                    color = colors.textDim,
                    fontSize = 8.sp,
                )
                SyncAgeText(
                    syncedAtEpochMs = snapshot.sourceHealth.syncedAtEpochMs,
                    tint = sourceTint,
                )
            }
        }
    }
}

@Composable
private fun NextDrawCountdown(
    snapshot: com.tianji.probabilitylab.nativev4.model.DrawSnapshot,
    deadline: ForecastDeadline?,
    isRefreshing: Boolean,
    onRefresh: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val colors = LocalTianjiColors.current
    var remaining by remember(snapshot.nextPeriod) { mutableIntStateOf(-1) }
    var postDrawPollAttempt by remember(snapshot.nextPeriod) { mutableIntStateOf(0) }
    LaunchedEffect(
        snapshot.nextPeriod,
        deadline?.epochMs,
        snapshot.serverTimeEpochMs,
        snapshot.sourceHealth.syncedAtEpochMs,
        isRefreshing,
    ) {
        val target = deadline?.epochMs
        if (target == null) {
            remaining = -1
            return@LaunchedEffect
        }
        while (true) {
            remaining = ServerCountdown.remainingSeconds(
                nextDrawAtEpochMs = target,
                serverTimeAtSyncEpochMs = snapshot.serverTimeEpochMs
                    ?: snapshot.sourceHealth.syncedAtEpochMs,
                localSyncedAtEpochMs = snapshot.sourceHealth.syncedAtEpochMs,
                localNowEpochMs = System.currentTimeMillis(),
            )
            if (remaining <= 0) {
                val delays = listOf(
                    2_000L,
                    3_000L,
                    5_000L,
                    8_000L,
                    13_000L,
                    20_000L,
                    30_000L,
                    45_000L,
                    60_000L,
                )
                if (!isRefreshing && postDrawPollAttempt < delays.size) {
                    delay(delays[postDrawPollAttempt])
                    postDrawPollAttempt++
                    onRefresh()
                }
                break
            }
            delay(1_000L)
        }
    }
    Column(modifier, horizontalAlignment = Alignment.End) {
        Text("下期开奖", color = colors.textDim, fontSize = 8.sp)
        Spacer(Modifier.height(4.dp))
        Text(
            if (remaining < 0) "--:--" else "%02d:%02d".format(
                remaining / 60,
                remaining % 60,
            ),
            color = colors.accent,
            fontSize = 12.sp,
            fontWeight = FontWeight.ExtraBold,
            letterSpacing = 1.sp,
        )
        deadline?.let {
            Spacer(Modifier.height(2.dp))
            Text(
                if (it.source == ForecastDeadline.Source.API) {
                    "接口 ${formatApiTime(it.epochMs)}"
                } else {
                    "按最近开奖周期推算 ${formatApiTime(it.epochMs)}"
                },
                color = colors.textDim,
                fontSize = 6.5.sp,
            )
        }
        if (remaining == 0 && postDrawPollAttempt > 0) {
            Spacer(Modifier.height(2.dp))
            Text(
                if (isRefreshing) {
                    "正在核验开奖…"
                } else if (postDrawPollAttempt >= 9) {
                    "接口仍未更新 · 可手动刷新"
                } else {
                    "等待接口更新 · 第${postDrawPollAttempt}次"
                },
                color = colors.amber,
                fontSize = 6.5.sp,
            )
        }
    }
}

@Composable
private fun SyncAgeText(
    syncedAtEpochMs: Long,
    tint: Color,
) {
    var nowEpochMs by remember(syncedAtEpochMs) { mutableLongStateOf(System.currentTimeMillis()) }
    LaunchedEffect(syncedAtEpochMs) {
        while (true) {
            nowEpochMs = System.currentTimeMillis()
            delay(1_000L)
        }
    }
    Text(
        formatSyncAge(nowEpochMs - syncedAtEpochMs),
        color = tint,
        fontSize = 8.sp,
    )
}

@Composable
private fun DrawBallGrid(numbers: List<Int>) {
    val colors = LocalTianjiColors.current
    val labels = listOf("冠", "亚", "3", "4", "5", "6", "7", "8", "9", "10")
    Column(verticalArrangement = Arrangement.spacedBy(16.dp)) {
        repeat(2) { row ->
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                repeat(5) { column ->
                    val index = row * 5 + column
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Text(
                            labels[index],
                            color = colors.textDim,
                            fontSize = 8.sp,
                            fontWeight = FontWeight.SemiBold,
                        )
                        Spacer(Modifier.height(7.dp))
                        LotteryBall(numbers[index], size = 42.dp)
                    }
                }
            }
        }
    }
}

@Composable
private fun ForecastHero(report: ForecastReport) {
    val colors = LocalTianjiColors.current
    var selectedPosition by remember(report.targetPeriod) {
        mutableIntStateOf(report.selectedPosition)
    }
    val prediction = report.positions[selectedPosition]
    SurfaceCard {
        Column(
            Modifier
                .background(colors.accent.copy(alpha = 0.055f))
                .padding(18.dp),
        ) {
            SectionTitle(
                eyebrow = "NEXT DRAW FORECAST",
                title = "第 ${report.targetPeriod} 期 · 第${positionName(selectedPosition)}",
                icon = Icons.Rounded.Science,
            )
            Spacer(Modifier.height(13.dp))
            EvidencePill(
                report.mode,
                if (report.displayUsesShadow) "影子预测 · 正式权重未认证" else null,
            )
            if (report.mode == EvidenceMode.OBSERVE) {
                Spacer(Modifier.height(10.dp))
                Text(
                    "本期不形成正式建议：${report.blockedReasons.joinToString("；").ifBlank { "未发现可验证优势" }}",
                    color = colors.amber,
                    fontSize = 8.sp,
                    lineHeight = 13.sp,
                    fontWeight = FontWeight.Bold,
                    modifier = Modifier
                        .fillMaxWidth()
                        .clip(RoundedCornerShape(12.dp))
                        .background(colors.amber.copy(alpha = 0.08f))
                        .border(1.dp, colors.amber.copy(alpha = 0.2f), RoundedCornerShape(12.dp))
                        .padding(10.dp),
                )
            }
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = 18.dp)
                    .horizontalScroll(rememberScrollState()),
                horizontalArrangement = Arrangement.spacedBy(7.dp),
            ) {
                repeat(10) { position ->
                    val active = selectedPosition == position
                    Column(
                        modifier = Modifier
                            .size(width = 48.dp, height = 54.dp)
                            .clip(RoundedCornerShape(14.dp))
                            .background(
                                if (active) colors.accentSoft
                                else Color.White.copy(alpha = 0.025f),
                            )
                            .border(
                                1.dp,
                                if (active) colors.accent.copy(alpha = 0.35f) else colors.line,
                                RoundedCornerShape(14.dp),
                            )
                            .clickable { selectedPosition = position },
                        horizontalAlignment = Alignment.CenterHorizontally,
                        verticalArrangement = Arrangement.Center,
                    ) {
                        Text(
                            (position + 1).toString(),
                            color = if (active) colors.text else colors.textSoft,
                            fontSize = 13.sp,
                            fontWeight = FontWeight.Bold,
                        )
                        Spacer(Modifier.height(4.dp))
                        Text(
                            "第${positionName(position)}",
                            color = if (active) colors.accent else colors.textDim,
                            fontSize = 7.sp,
                        )
                    }
                }
            }
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = 14.dp)
                    .clip(RoundedCornerShape(20.dp))
                    .background(Color.Black.copy(alpha = 0.14f))
                    .border(1.dp, colors.accent.copy(alpha = 0.18f), RoundedCornerShape(20.dp))
                    .padding(horizontal = 12.dp, vertical = 17.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
            ) {
                Text(
                    when {
                        report.mode == EvidenceMode.CERTIFIED -> "认证集成六码"
                        report.displayUsesShadow -> "影子实验六码"
                        else -> "观察实验六码"
                    },
                    color = colors.accent,
                    fontSize = 9.sp,
                    fontWeight = FontWeight.Bold,
                )
                Spacer(Modifier.height(12.dp))
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceEvenly) {
                    prediction.top6.forEach { LotteryBall(it, size = 37.dp) }
                }
                Spacer(Modifier.height(11.dp))
                Text(
                    "覆盖概率 ${(prediction.coverage6 * 100).format1()}% · 边界 ${(prediction.boundaryMargin * 100).format2()}%",
                    color = colors.textDim,
                    fontSize = 8.sp,
                )
            }
            Row(
                Modifier.fillMaxWidth().padding(top = 12.dp),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                MetricTile(
                    "训练历史",
                    report.historySize.toString(),
                    "真实开奖记录",
                    Modifier.weight(1f),
                )
                MetricTile(
                    "时间留出",
                    report.validationDraws.toString(),
                    "不参与调权",
                    Modifier.weight(1f),
                )
                MetricTile("模型数量", "11", "竞争集成", Modifier.weight(1f))
            }
        }
    }
}

@Composable
private fun AiAnalysisPanel(
    state: AppUiState,
    configs: List<AiConfig>,
    onAnalyzeAll: () -> Unit,
    onCancelAi: (String) -> Unit,
) {
    val colors = LocalTianjiColors.current
    val completeConfigs = configs.filter(AiConfig::isComplete)
    var showComparison by remember(state.report?.targetPeriod) { mutableStateOf(false) }
    SurfaceCard {
        Column(Modifier.padding(18.dp)) {
            SectionTitle(
                eyebrow = "MULTI-PROVIDER AI",
                title = "多 AI 独立分析",
                icon = Icons.Rounded.AutoAwesome,
                detail = "每次分析先强制同步开奖接口历史；首次有效结果开奖前冻结，目标期开奖后自动验证。",
            )
            Spacer(Modifier.height(14.dp))
            if (configs.isEmpty()) {
                Text("还没有 AI 配置，请先到数据页添加", color = colors.amber, fontSize = 9.sp)
            } else {
                val distinctModels = completeConfigs.map { it.model.trim().lowercase() }
                    .filter(String::isNotBlank)
                    .distinct()
                    .size
                if (distinctModels < completeConfigs.size) {
                    Text(
                        "${completeConfigs.size} 个配置中有 $distinctModels 个独立模型；重复模型不重复计入共识。",
                        color = colors.amber,
                        fontSize = 7.2.sp,
                    )
                    Spacer(Modifier.height(8.dp))
                }
                configs.forEach { config ->
                    AiStatusRow(config, state, onCancelAi)
                    Spacer(Modifier.height(7.dp))
                }
            }
            Spacer(Modifier.height(6.dp))
            Button(
                onClick = onAnalyzeAll,
                enabled = completeConfigs.isNotEmpty() && !state.isAiAnalyzing,
                modifier = Modifier.fillMaxWidth().height(46.dp),
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
                        modifier = Modifier.size(17.dp),
                        color = Color.White,
                        strokeWidth = 2.dp,
                    )
                    Spacer(Modifier.width(8.dp))
                }
                Text(
                    if (state.isAiAnalyzing) {
                        "多个 AI 正在独立分析…"
                    } else {
                        "全部 AI 同时独立分析"
                    },
                    fontSize = 10.sp,
                    fontWeight = FontWeight.Bold,
                )
            }
            state.aiError?.let { message ->
                Spacer(Modifier.height(10.dp))
                Text(message, color = colors.red, fontSize = 8.sp, lineHeight = 13.sp)
            }
            if (state.aiForecasts.isNotEmpty()) {
                Spacer(Modifier.height(12.dp))
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    MiniActionButton(
                        "独立结果",
                        Modifier.weight(1f),
                        tint = if (!showComparison) colors.accent else colors.textDim,
                    ) { showComparison = false }
                    MiniActionButton(
                        "概率对比",
                        Modifier.weight(1f),
                        tint = if (showComparison) colors.accent else colors.textDim,
                    ) { showComparison = true }
                }
            }
            if (state.aiForecasts.size >= 2) {
                Spacer(Modifier.height(15.dp))
                AiConsensusCard(state.aiForecasts, state.aiProfileAudits)
            }
            if (showComparison && state.aiForecasts.isNotEmpty()) {
                Spacer(Modifier.height(12.dp))
                AiProbabilityComparison(state.aiForecasts)
            } else {
                state.aiForecasts.forEach { result ->
                    Spacer(Modifier.height(12.dp))
                    AiForecastCard(result)
                }
            }
        }
    }
}

@Composable
private fun AiStatusRow(
    config: AiConfig,
    state: AppUiState,
    onCancelAi: (String) -> Unit,
) {
    val colors = LocalTianjiColors.current
    val status = state.aiStatuses[config.id]
    val currentState = status?.state ?: AiConnectionState.UNTESTED
    val tint = when (currentState) {
        AiConnectionState.CONNECTED -> colors.green
        AiConnectionState.FAILED -> colors.red
        AiConnectionState.CANCELLED -> colors.amber
        AiConnectionState.TESTING, AiConnectionState.ANALYZING -> colors.accent
        AiConnectionState.UNTESTED -> colors.amber
    }
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(14.dp))
            .background(tint.copy(alpha = 0.065f))
            .border(1.dp, tint.copy(alpha = 0.2f), RoundedCornerShape(14.dp))
            .padding(horizontal = 11.dp, vertical = 9.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        if (currentState == AiConnectionState.TESTING || currentState == AiConnectionState.ANALYZING) {
            CircularProgressIndicator(Modifier.size(14.dp), color = tint, strokeWidth = 1.8.dp)
        } else {
            Icon(
                if (currentState == AiConnectionState.CONNECTED) {
                    Icons.Rounded.CheckCircle
                } else {
                    Icons.Rounded.Info
                },
                null,
                tint = tint,
                modifier = Modifier.size(14.dp),
            )
        }
        Spacer(Modifier.width(7.dp))
        Column(Modifier.weight(1f)) {
            Text(
                config.displayName,
                color = colors.textSoft,
                fontSize = 8.5.sp,
                fontWeight = FontWeight.Bold,
            )
            Text(
                "${config.analysisMode.label} · ${AiReasoningEngine.resolve(config).displayLabel}",
                color = colors.textDim,
                fontSize = 6.5.sp,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
            Text(
                status?.message ?: "配置已保存，尚未测试",
                color = tint,
                fontSize = 7.sp,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
        }
        if (currentState == AiConnectionState.ANALYZING || currentState == AiConnectionState.TESTING) {
            MiniActionButton("取消", Modifier.width(48.dp), tint = colors.amber) {
                onCancelAi(config.id)
            }
        } else {
            status?.latencyMs?.let { Text("${it}ms", color = tint, fontSize = 8.sp) }
        }
    }
}

@Composable
private fun AiConsensusCard(
    results: List<com.tianji.probabilitylab.nativev4.ai.AiForecast>,
    audits: List<AiProfileAudit>,
) {
    val colors = LocalTianjiColors.current
    val evaluation = AiConsensusEngine.evaluateForecasts(results, audits)
    val consensus = evaluation.consensus
    Column(
        Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(18.dp))
            .background(colors.accent.copy(alpha = 0.065f))
            .border(1.dp, colors.accent.copy(alpha = 0.22f), RoundedCornerShape(18.dp))
            .padding(14.dp),
    ) {
        Text(
            if (evaluation.stable) {
                "AI 加权共识 · 第${positionName(consensus!!.position)}"
            } else {
                "本期不形成稳定 AI 共识"
            },
            color = if (evaluation.stable) colors.accent else colors.amber,
            fontSize = 10.sp,
            fontWeight = FontWeight.Bold,
        )
        Spacer(Modifier.height(11.dp))
        if (!evaluation.stable || consensus == null) {
            Text(
                evaluation.reasons.joinToString("；").ifBlank { "模型分歧不足以形成正式建议" },
                color = colors.textSoft,
                fontSize = 8.sp,
                lineHeight = 13.sp,
            )
        } else {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceEvenly) {
                consensus.top6.forEach { LotteryBall(it, size = 32.dp) }
            }
            Spacer(Modifier.height(8.dp))
            Text(
                "同名次 ${consensus.supportingProfiles}/${consensus.totalProfiles} 个独立模型" +
                    " · 边界 ${(consensus.confidenceMargin * 100).format2()}%" +
                    " · 分歧 ${(consensus.disagreement * 100).format1()}%",
                color = colors.textDim,
                fontSize = 8.sp,
            )
        }
    }
}

@Composable
private fun AiProbabilityComparison(
    results: List<com.tianji.probabilitylab.nativev4.ai.AiForecast>,
) {
    val colors = LocalTianjiColors.current
    val horizontalScrollState = rememberScrollState()
    Column(
        Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(18.dp))
            .background(Color.Black.copy(alpha = 0.14f))
            .border(1.dp, colors.line, RoundedCornerShape(18.dp))
            .padding(13.dp),
    ) {
        Text("10号码概率矩阵", color = colors.text, fontSize = 11.sp, fontWeight = FontWeight.Bold)
        Spacer(Modifier.height(4.dp))
        Text(
            "每列独立归一化；进度条按真实 0–100% 比例显示",
            color = colors.textDim,
            fontSize = 8.sp,
        )
        Spacer(Modifier.height(10.dp))
        Row(Modifier.fillMaxWidth().horizontalScroll(horizontalScrollState)) {
            Spacer(Modifier.width(38.dp))
            results.forEach { result ->
                Text(
                    result.profileName.take(10),
                    color = colors.accent,
                    fontSize = 8.sp,
                    fontWeight = FontWeight.Bold,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                    modifier = Modifier.width(94.dp).padding(horizontal = 4.dp),
                )
            }
        }
        Spacer(Modifier.height(7.dp))
        (1..10).forEach { number ->
            Row(
                Modifier
                    .fillMaxWidth()
                    .horizontalScroll(horizontalScrollState)
                    .padding(vertical = 3.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                LotteryBall(number, size = 28.dp)
                Spacer(Modifier.width(10.dp))
                results.forEach { result ->
                    val probability = result.probabilities.getOrNull(number - 1) ?: 0.0
                    Column(Modifier.width(94.dp).padding(horizontal = 4.dp)) {
                        Text(
                            "${(probability * 100).format1()}%",
                            color = if (number in result.top6) colors.text else colors.textDim,
                            fontSize = 8.sp,
                            fontWeight = if (number in result.top6) {
                                FontWeight.Bold
                            } else {
                                FontWeight.Normal
                            },
                        )
                        LinearProgressIndicator(
                            progress = { probability.toFloat().coerceIn(0f, 1f) },
                            modifier = Modifier.fillMaxWidth().height(3.dp).clip(CircleShape),
                            color = if (number in result.top6) colors.accent else colors.textDim,
                            trackColor = colors.line,
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun AiForecastCard(result: com.tianji.probabilitylab.nativev4.ai.AiForecast) {
    val colors = LocalTianjiColors.current
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(18.dp))
            .background(Color.Black.copy(alpha = 0.14f))
            .border(1.dp, colors.accent.copy(alpha = 0.2f), RoundedCornerShape(18.dp))
            .padding(14.dp),
    ) {
        Text(
            result.profileName,
            color = colors.accent,
            fontSize = 9.sp,
            fontWeight = FontWeight.Bold,
        )
        Spacer(Modifier.height(5.dp))
        Text(
            "第 ${result.targetPeriod} 期 · 第${positionName(result.position)}",
            color = colors.text,
            fontSize = 14.sp,
            fontWeight = FontWeight.ExtraBold,
        )
        Spacer(Modifier.height(4.dp))
        Text(
            "${result.executionNote} · 已接入 · ${result.latencyMs}ms · " +
                "${result.responseId.takeLast(10).ifBlank { "无响应ID" }} · " +
                formatTime(result.createdAtEpochMs),
            color = colors.green,
            fontSize = 7.sp,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
        )
        Spacer(Modifier.height(8.dp))
        ReasoningBadge(result.reasoningState, result.reasoningTokens)
        Spacer(Modifier.height(13.dp))
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceEvenly) {
            result.top6.forEach { LotteryBall(it, size = 34.dp) }
        }
        result.top7.firstOrNull { it !in result.top6 }?.let { supplement ->
            Spacer(Modifier.height(10.dp))
            Text(
                "七码补充：$supplement",
                color = colors.accent,
                fontSize = 8.sp,
                fontWeight = FontWeight.Bold,
            )
        }
        Spacer(Modifier.height(12.dp))
        Text(result.analysis, color = colors.textSoft, fontSize = 9.sp, lineHeight = 15.sp)
        Spacer(Modifier.height(8.dp))
        Text(
            "风险提示：${result.riskNote}",
            color = colors.amber,
            fontSize = 8.sp,
            lineHeight = 13.sp,
        )
        Spacer(Modifier.height(8.dp))
        Text(
            "矩阵集中度 ${(result.selfRating * 100).format1()}%（不是命中概率）" +
                result.estimatedCost?.let {
                    " · 本次约 \$${"%.6f".format(Locale.US, it)}"
                }.orEmpty(),
            color = colors.textDim,
            fontSize = 8.sp,
        )
    }
}

@Composable
private fun ReasoningBadge(state: AiReasoningState, reasoningTokens: Int?) {
    val colors = LocalTianjiColors.current
    val (message, tint) = when (state) {
        AiReasoningState.VERIFIED ->
            "已验证推理${reasoningTokens?.let { " · $it tokens" }.orEmpty()}" to colors.green
        AiReasoningState.REQUESTED ->
            "已请求推理 · 供应商未返回可核验用量" to colors.amber
        AiReasoningState.FALLBACK ->
            "推理未完成 · 当前为关闭推理后的重试结果（不代表本期好坏）" to colors.amber
        AiReasoningState.DISABLED -> "可控推理已关闭" to colors.textDim
        AiReasoningState.DEFAULT -> "模型默认推理" to colors.textDim
        AiReasoningState.UNSUPPORTED -> "普通分析接口 · 未检测到可控推理" to colors.textDim
    }
    Text(
        message,
        color = tint,
        fontSize = 7.2.sp,
        fontWeight = FontWeight.Bold,
        modifier = Modifier
            .clip(CircleShape)
            .background(tint.copy(alpha = 0.08f))
            .border(1.dp, tint.copy(alpha = 0.2f), CircleShape)
            .padding(horizontal = 9.dp, vertical = 6.dp),
    )
}

@Composable
private fun ProbabilityPanel(report: ForecastReport) {
    val colors = LocalTianjiColors.current
    val prediction = report.selected
    SurfaceCard {
        Column(Modifier.padding(18.dp)) {
            SectionTitle(
                eyebrow = "PROBABILITY MATRIX",
                title = "第${positionName(report.selectedPosition)}概率",
                icon = Icons.Rounded.Analytics,
                detail = if (report.displayUsesShadow) {
                    "观察模式使用影子模型排序；条形图按真实概率显示，不代表已验证优势"
                } else {
                    "完整概率矩阵经排列约束投影；条形图按真实 0–100% 比例显示"
                },
            )
            Spacer(Modifier.height(17.dp))
            prediction.probabilities
                .mapIndexed { index, value -> index + 1 to value }
                .sortedByDescending { it.second }
                .forEachIndexed { rank, (number, value) ->
                    Row(
                        modifier = Modifier.fillMaxWidth().height(38.dp),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Text(
                            "${rank + 1}",
                            color = colors.textDim,
                            fontSize = 8.sp,
                            modifier = Modifier.width(20.dp),
                            textAlign = TextAlign.Center,
                        )
                        LotteryBall(number, size = 29.dp, muted = rank >= 6)
                        Spacer(Modifier.width(9.dp))
                        LinearProgressIndicator(
                            progress = { value.toFloat().coerceIn(0f, 1f) },
                            modifier = Modifier.weight(1f).height(5.dp).clip(CircleShape),
                            color = colors.accent,
                            trackColor = Color.White.copy(alpha = 0.05f),
                        )
                        Spacer(Modifier.width(9.dp))
                        Text(
                            "${(value * 100).format1()}%",
                            color = colors.textSoft,
                            fontSize = 8.sp,
                            modifier = Modifier.width(42.dp),
                            textAlign = TextAlign.End,
                        )
                    }
                }
        }
    }
}

@Composable
private fun CompactModelPanel(models: List<ModelPerformance>) {
    val colors = LocalTianjiColors.current
    SurfaceCard {
        Column(Modifier.padding(18.dp)) {
            SectionTitle(
                eyebrow = "MODEL COMPETITION",
                title = "11 模型前向竞赛",
                icon = Icons.Rounded.Memory,
                detail = "正式权重只来自时间切分验证；无优势时回退均匀随机基线",
            )
            Spacer(Modifier.height(15.dp))
            models.take(5).forEachIndexed { index, model ->
                ModelRow(index + 1, model)
                if (index != min(4, models.lastIndex)) Spacer(Modifier.height(8.dp))
            }
            if (models.size > 5) {
                Spacer(Modifier.height(10.dp))
                Text("其余 6 个模型请在“验证”页查看", color = colors.textDim, fontSize = 8.sp)
            }
        }
    }
}

@Composable
fun RollingScreen(
    state: AppUiState,
    onSelectLottery: (LotteryType) -> Unit,
    modifier: Modifier = Modifier,
) {
    val report = state.report
    val colors = LocalTianjiColors.current
    LazyColumn(
        modifier = modifier,
        contentPadding = androidx.compose.foundation.layout.PaddingValues(12.dp, 14.dp, 12.dp, 124.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item { GameSwitcher(state.lottery, onSelectLottery) }
        if (report == null) {
            item { EmptyState("雪球策略等待模型", state.error ?: "请先同步真实历史", state.isLoading) }
        } else {
            item {
                SurfaceCard {
                    Column(Modifier.background(colors.accent.copy(alpha = 0.05f)).padding(18.dp)) {
                        SectionTitle(
                            "ROLLING LAB",
                            "七码三段观察",
                            Icons.Rounded.AutoGraph,
                            "只模拟证据闸门，不提供投注承诺",
                        )
                        Spacer(Modifier.height(13.dp))
                        EvidencePill(
                            report.mode,
                            if (report.mode == EvidenceMode.CERTIFIED) {
                                "策略证据通过"
                            } else {
                                "观察模式 · 禁止正式滚动"
                            },
                        )
                        Spacer(Modifier.height(18.dp))
                        Row(
                            Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.spacedBy(7.dp),
                        ) {
                            listOf(
                                "第一段" to "3 单位",
                                "第二段" to "5 单位",
                                "第三段" to "7 单位",
                            ).forEachIndexed { index, stage ->
                                Column(
                                    Modifier
                                        .weight(1f)
                                        .clip(RoundedCornerShape(15.dp))
                                        .background(
                                            if (index == 0) colors.accentSoft
                                            else Color.White.copy(alpha = 0.025f),
                                        )
                                        .border(
                                            1.dp,
                                            if (index == 0) {
                                                colors.accent.copy(alpha = 0.3f)
                                            } else {
                                                colors.line
                                            },
                                            RoundedCornerShape(15.dp),
                                        )
                                        .padding(11.dp),
                                ) {
                                    Text(
                                        stage.first,
                                        color = if (index == 0) colors.accent else colors.textDim,
                                        fontSize = 8.sp,
                                    )
                                    Spacer(Modifier.height(5.dp))
                                    Text(
                                        stage.second,
                                        color = colors.text,
                                        fontSize = 13.sp,
                                        fontWeight = FontWeight.Bold,
                                    )
                                }
                            }
                        }
                    }
                }
            }
            item {
                SurfaceCard {
                    Column(Modifier.padding(18.dp)) {
                        SectionTitle(
                            "LOCKED TICKET",
                            "第${positionName(report.selectedPosition)} · 七码",
                            Icons.Rounded.LockClock,
                            "目标期 ${report.targetPeriod}",
                        )
                        Spacer(Modifier.height(17.dp))
                        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceEvenly) {
                            report.selected.top7.forEach { LotteryBall(it, size = 36.dp) }
                        }
                        Spacer(Modifier.height(17.dp))
                        val excluded = (1..10).filterNot { it in report.selected.top7 }
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Text("排除号码", color = colors.textDim, fontSize = 8.sp)
                            Spacer(Modifier.width(10.dp))
                            excluded.forEach {
                                LotteryBall(it, size = 29.dp, muted = true)
                                Spacer(Modifier.width(6.dp))
                            }
                        }
                    }
                }
            }
            item {
                SurfaceCard {
                    Column(Modifier.padding(18.dp)) {
                        SectionTitle("RISK GATE", "策略证据", Icons.Rounded.Security)
                        Spacer(Modifier.height(15.dp))
                        Row(
                            Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.spacedBy(8.dp),
                        ) {
                            MetricTile(
                                "留出七码",
                                "${(report.top7HitRate * 100).format1()}%",
                                "随机 70%",
                                Modifier.weight(1f),
                            )
                            MetricTile(
                                "盈亏门槛",
                                "${(report.breakEvenTop7 * 100).format1()}%",
                                "按 9.8 倍",
                                Modifier.weight(1f),
                            )
                            MetricTile(
                                "真实前向",
                                state.liveAudit.settled.toString(),
                                "已结算",
                                Modifier.weight(1f),
                            )
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun EvidenceScreen(
    state: AppUiState,
    onSelectLottery: (LotteryType) -> Unit,
    modifier: Modifier = Modifier,
) {
    val report = state.report
    val colors = LocalTianjiColors.current
    LazyColumn(
        modifier = modifier,
        contentPadding = androidx.compose.foundation.layout.PaddingValues(12.dp, 14.dp, 12.dp, 124.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item { GameSwitcher(state.lottery, onSelectLottery) }
        if (report == null) {
            item { EmptyState("验证报告等待数据", state.error ?: "正在同步", state.isLoading) }
        } else {
            item {
                SurfaceCard {
                    Column(Modifier.padding(18.dp)) {
                        SectionTitle(
                            "TIME HOLDOUT TEST",
                            "时间切分留出验证",
                            Icons.Rounded.QueryStats,
                            "历史尾段不参与训练和权重拟合；真实前向成绩请查看档案页",
                        )
                        Spacer(Modifier.height(13.dp))
                        EvidencePill(report.mode)
                        Spacer(Modifier.height(15.dp))
                        Row(
                            Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.spacedBy(8.dp),
                        ) {
                            MetricTile(
                                "六码命中",
                                "${(report.top6HitRate * 100).format1()}%",
                                "下界 ${(report.top6Interval.low * 100).format1()}%",
                                Modifier.weight(1f),
                            )
                            MetricTile(
                                "七码命中",
                                "${(report.top7HitRate * 100).format1()}%",
                                "下界 ${(report.top7Interval.low * 100).format1()}%",
                                Modifier.weight(1f),
                            )
                        }
                        Spacer(Modifier.height(8.dp))
                        Row(
                            Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.spacedBy(8.dp),
                        ) {
                            MetricTile(
                                "概率损失",
                                report.averageLogLoss.format2(),
                                "随机 ${report.randomLogLoss.format2()}",
                                Modifier.weight(1f),
                            )
                            MetricTile(
                                "留出期数",
                                report.validationDraws.toString(),
                                "最低认证 96",
                                Modifier.weight(1f),
                            )
                        }
                    }
                }
            }
            item {
                SurfaceCard {
                    Column(Modifier.padding(18.dp)) {
                        SectionTitle("EVIDENCE GATES", "未通过原因", Icons.Rounded.ErrorOutline)
                        Spacer(Modifier.height(13.dp))
                        if (report.blockedReasons.isEmpty()) {
                            GateRow("全部证据闸门已通过", true)
                        } else {
                            report.blockedReasons.forEach { GateRow(it, false) }
                        }
                    }
                }
            }
            item {
                SurfaceCard {
                    Column(Modifier.padding(18.dp)) {
                        SectionTitle(
                            "ALL MODELS",
                            "模型权重与成绩",
                            Icons.Rounded.Memory,
                            "正式权重为 0 表示该模型没有通过证据筛选",
                        )
                        Spacer(Modifier.height(15.dp))
                        report.models.forEachIndexed { index, model ->
                            ModelRow(index + 1, model)
                            if (index != report.models.lastIndex) Spacer(Modifier.height(8.dp))
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun ArchiveScreen(
    state: AppUiState,
    onSelectLottery: (LotteryType) -> Unit,
    modifier: Modifier = Modifier,
) {
    val colors = LocalTianjiColors.current
    LazyColumn(
        modifier = modifier,
        contentPadding = androidx.compose.foundation.layout.PaddingValues(12.dp, 14.dp, 12.dp, 124.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item { GameSwitcher(state.lottery, onSelectLottery) }
        item {
            SurfaceCard {
                Column(Modifier.padding(18.dp)) {
                    SectionTitle(
                        "FORWARD ARCHIVE",
                        "真实前向冻结验证",
                        Icons.Rounded.Fingerprint,
                        "开奖前锁定，开奖后按目标期结算；SHA-256 链用于检测本机档案误改",
                    )
                    Spacer(Modifier.height(10.dp))
                    val integrityTint = if (state.archiveIntegrity.isValid) colors.green else colors.red
                    Text(
                        if (state.archiveIntegrity.isValid) {
                            "档案链完整 · 已重新计算 ${state.archiveIntegrity.checkedCount} 条"
                        } else {
                            "档案链校验异常 · 请停止采用相关成绩"
                        },
                        color = integrityTint,
                        fontSize = 8.sp,
                        fontWeight = FontWeight.Bold,
                    )
                    Spacer(Modifier.height(15.dp))
                    Text(
                        "按开奖期统计 · 本地 11 模型",
                        color = colors.textSoft,
                        fontSize = 9.sp,
                        fontWeight = FontWeight.Bold,
                    )
                    Spacer(Modifier.height(8.dp))
                    Row(
                        Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                    ) {
                        MetricTile(
                            "已结算期数",
                            state.liveAudit.settled.toString(),
                            "每目标期一次",
                            Modifier.weight(1f),
                        )
                        MetricTile(
                            "六码命中",
                            "${(state.liveAudit.top6Rate * 100).format1()}%",
                            "${state.liveAudit.top6Hits} 次",
                            Modifier.weight(1f),
                        )
                        MetricTile(
                            "七码命中",
                            "${(state.liveAudit.top7Rate * 100).format1()}%",
                            "${state.liveAudit.top7Hits} 次",
                            Modifier.weight(1f),
                        )
                    }
                    Spacer(Modifier.height(14.dp))
                    Text(
                        "按 AI 调用记录统计",
                        color = colors.textSoft,
                        fontSize = 9.sp,
                        fontWeight = FontWeight.Bold,
                    )
                    Spacer(Modifier.height(4.dp))
                    Text(
                        "同一期多个独立 AI 会分别计为记录；记录数不等于开奖期数。",
                        color = colors.textDim,
                        fontSize = 7.sp,
                    )
                    Spacer(Modifier.height(8.dp))
                    Row(
                        Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                    ) {
                        MetricTile(
                            "已结算记录",
                            state.aiLiveAudit.settled.toString(),
                            "覆盖 ${state.aiLiveAudit.targetPeriods} 个目标期",
                            Modifier.weight(1f),
                        )
                        MetricTile(
                            "六码命中",
                            "${(state.aiLiveAudit.top6Rate * 100).format1()}%",
                            "${state.aiLiveAudit.top6Hits} 次",
                            Modifier.weight(1f),
                        )
                        MetricTile(
                            "七码命中",
                            "${(state.aiLiveAudit.top7Rate * 100).format1()}%",
                            "${state.aiLiveAudit.top7Hits} 次",
                            Modifier.weight(1f),
                        )
                    }
                    if (state.aiProfileAudits.isNotEmpty()) {
                        Spacer(Modifier.height(11.dp))
                        Text(
                            "按模型配置分组（模型、窗口、推理强度和协议分别统计）",
                            color = colors.textDim,
                            fontSize = 7.5.sp,
                        )
                        Spacer(Modifier.height(7.dp))
                        state.aiProfileAudits.forEach { audit ->
                            AiProfileAuditRow(audit)
                            Spacer(Modifier.height(6.dp))
                        }
                    }
                    Spacer(Modifier.height(12.dp))
                    Text(
                        "按目标期统计 · AI 同名次共识",
                        color = colors.textSoft,
                        fontSize = 9.sp,
                        fontWeight = FontWeight.Bold,
                    )
                    Spacer(Modifier.height(8.dp))
                    Row(
                        Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                    ) {
                        MetricTile(
                            "已结算期数",
                            state.aiConsensusAudit.settled.toString(),
                            "每目标期最多一次",
                            Modifier.weight(1f),
                        )
                        MetricTile(
                            "六码命中",
                            "${(state.aiConsensusAudit.top6Rate * 100).format1()}%",
                            "${state.aiConsensusAudit.top6Hits} 次",
                            Modifier.weight(1f),
                        )
                        MetricTile(
                            "七码命中",
                            "${(state.aiConsensusAudit.top7Rate * 100).format1()}%",
                            "${state.aiConsensusAudit.top7Hits} 次",
                            Modifier.weight(1f),
                        )
                    }
                }
            }
        }
        if (state.aiConsensusRecords.isNotEmpty()) {
            item {
                ArchiveSectionLabel(
                    "AI 共识档案",
                    "仅同一名次至少两个 AI 达成共识时冻结，每目标期一次",
                )
            }
            items(state.aiConsensusRecords, key = { "consensus-${it.id}" }) { record ->
                AiConsensusArchiveRecordCard(record)
            }
        }
        if (state.aiRecords.isNotEmpty()) {
            item {
                ArchiveSectionLabel(
                    "AI 冻结预测",
                    "首次有效返回入档，目标期开奖后自动验证",
                )
            }
            items(state.aiRecords, key = { "ai-${it.id}" }) { record ->
                AiArchiveRecordCard(record)
            }
        }
        if (state.records.isNotEmpty()) {
            item {
                ArchiveSectionLabel(
                    "本地模型预测",
                    "每个目标期只锁定一次，不会用最新期替代结算",
                )
            }
            items(state.records, key = { "native-${it.id}" }) { record ->
                ArchiveRecordCard(record)
            }
        }
        if (
            state.records.isEmpty() &&
            state.aiRecords.isEmpty() &&
            state.aiConsensusRecords.isEmpty()
        ) {
            item { EmptyState("还没有前向档案", "同步或 AI 分析成功后，会在开奖前自动冻结预测") }
        }
    }
}

@Composable
private fun AiProfileAuditRow(audit: AiProfileAudit) {
    val colors = LocalTianjiColors.current
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(11.dp))
            .background(Color.White.copy(alpha = 0.025f))
            .border(1.dp, colors.line, RoundedCornerShape(11.dp))
            .padding(horizontal = 10.dp, vertical = 9.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Column(Modifier.weight(1f)) {
            Text(
                audit.profileName,
                color = colors.textSoft,
                fontSize = 8.5.sp,
                fontWeight = FontWeight.Bold,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
            Spacer(Modifier.height(3.dp))
            Text(
                "${audit.model} · ${audit.analysisMode.label} · ${audit.reasoningMode.label}",
                color = colors.textDim,
                fontSize = 6.9.sp,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
            Spacer(Modifier.height(2.dp))
            Text(
                "协议：${audit.reasoningProtocol.label}",
                color = colors.textDim,
                fontSize = 6.7.sp,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
        }
        Spacer(Modifier.width(8.dp))
        Column(horizontalAlignment = Alignment.End) {
            Text(
                "${audit.settled}期 · 六码 ${(audit.top6Rate * 100).format1()}%",
                color = colors.accent,
                fontSize = 7.6.sp,
                fontWeight = FontWeight.Bold,
            )
            Spacer(Modifier.height(3.dp))
            Text(
                if (audit.settled < 100) {
                    "前向 ${audit.settled}/100 · 基础权重"
                } else {
                    "LogLoss ${audit.meanLogLoss?.format2() ?: "--"} · 权重 ${audit.forwardWeight.format2()}"
                },
                color = colors.textDim,
                fontSize = 6.8.sp,
            )
        }
    }
}

@Composable
private fun AiConsensusArchiveRecordCard(record: AiConsensusRecord) {
    val colors = LocalTianjiColors.current
    SurfaceCard(radius = 19.dp) {
        Column(Modifier.padding(16.dp)) {
            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f)) {
                    Text(
                        "目标期 ${record.targetPeriod}",
                        color = colors.text,
                        fontSize = 13.sp,
                        fontWeight = FontWeight.Bold,
                    )
                    Spacer(Modifier.height(4.dp))
                    Text(
                        "第${positionName(record.position)} · 同名次 " +
                            "${record.supportingProfiles}/${record.totalProfiles} 个 AI" +
                            (record.actualNumber?.let { " · 实际 $it" } ?: ""),
                        color = colors.textDim,
                        fontSize = 8.sp,
                    )
                }
                val tint = when {
                    record.top6Hit == null -> colors.amber
                    record.top6Hit == true || record.top7Hit == true -> colors.green
                    else -> colors.red
                }
                Text(
                    settlementLabel(record.top6Hit, record.top7Hit),
                    color = tint,
                    fontSize = 8.sp,
                    fontWeight = FontWeight.Bold,
                    modifier = Modifier
                        .clip(CircleShape)
                        .background(tint.copy(alpha = 0.09f))
                        .padding(horizontal = 9.dp, vertical = 7.dp),
                )
            }
            Spacer(Modifier.height(13.dp))
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceEvenly) {
                record.top6.forEach { LotteryBall(it, size = 34.dp) }
            }
            record.actualRank?.let { rank ->
                Spacer(Modifier.height(8.dp))
                Text(
                    "实际号码矩阵排名：第$rank · LogLoss ${record.logLoss?.format2() ?: "--"}",
                    color = colors.textDim,
                    fontSize = 8.sp,
                )
            }
            Spacer(Modifier.height(12.dp))
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text(
                    "哈希 ${record.consensusHash.take(12)}…",
                    color = colors.textDim,
                    fontSize = 7.sp,
                )
                Text(formatTime(record.createdAtEpochMs), color = colors.textDim, fontSize = 7.sp)
            }
        }
    }
}

@Composable
private fun ArchiveSectionLabel(title: String, detail: String) {
    val colors = LocalTianjiColors.current
    Column(Modifier.padding(horizontal = 5.dp, vertical = 2.dp)) {
        Text(title, color = colors.text, fontSize = 11.sp, fontWeight = FontWeight.Bold)
        Spacer(Modifier.height(3.dp))
        Text(detail, color = colors.textDim, fontSize = 7.5.sp)
    }
}

@Composable
private fun ArchiveRecordCard(record: LockedForecast) {
    val colors = LocalTianjiColors.current
    SurfaceCard(radius = 19.dp) {
        Column(Modifier.padding(16.dp)) {
            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f)) {
                    Text(
                        "目标期 ${record.targetPeriod}",
                        color = colors.text,
                        fontSize = 13.sp,
                        fontWeight = FontWeight.Bold,
                    )
                    Spacer(Modifier.height(4.dp))
                    Text(
                        "第${positionName(record.position)} · 训练至 ${record.trainedThroughPeriod}" +
                            (record.actualNumber?.let { " · 实际 $it" } ?: ""),
                        color = colors.textDim,
                        fontSize = 8.sp,
                    )
                }
                val tint = when {
                    record.top6Hit == null -> colors.amber
                    record.top6Hit == true || record.top7Hit == true -> colors.green
                    else -> colors.red
                }
                Text(
                    settlementLabel(record.top6Hit, record.top7Hit),
                    color = tint,
                    fontSize = 8.sp,
                    fontWeight = FontWeight.Bold,
                    modifier = Modifier
                        .clip(CircleShape)
                        .background(tint.copy(alpha = 0.09f))
                        .padding(horizontal = 9.dp, vertical = 7.dp),
                )
            }
            Spacer(Modifier.height(13.dp))
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceEvenly) {
                record.top6.forEach { LotteryBall(it, size = 34.dp) }
            }
            Spacer(Modifier.height(12.dp))
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text(
                    "哈希 ${record.reportHash.take(12)}…",
                    color = colors.textDim,
                    fontSize = 7.sp,
                )
                Text(formatTime(record.createdAtEpochMs), color = colors.textDim, fontSize = 7.sp)
            }
        }
    }
}

@Composable
private fun AiArchiveRecordCard(record: AiForecastRecord) {
    val colors = LocalTianjiColors.current
    SurfaceCard(radius = 19.dp) {
        Column(Modifier.padding(16.dp)) {
            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f)) {
                    Text(
                        "目标期 ${record.targetPeriod}",
                        color = colors.text,
                        fontSize = 13.sp,
                        fontWeight = FontWeight.Bold,
                    )
                    Spacer(Modifier.height(4.dp))
                    Text(
                        "${record.profileName} · 第${positionName(record.position)} · " +
                            "${record.analysisMode.label} · ${record.reasoningState.label}" +
                            (record.actualNumber?.let { " · 实际 $it" } ?: ""),
                        color = colors.textDim,
                        fontSize = 8.sp,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
                val tint = when {
                    record.top6Hit == null -> colors.amber
                    record.top6Hit == true || record.top7Hit == true -> colors.green
                    else -> colors.red
                }
                Text(
                    settlementLabel(record.top6Hit, record.top7Hit),
                    color = tint,
                    fontSize = 8.sp,
                    fontWeight = FontWeight.Bold,
                    modifier = Modifier
                        .clip(CircleShape)
                        .background(tint.copy(alpha = 0.09f))
                        .padding(horizontal = 9.dp, vertical = 7.dp),
                )
            }
            Spacer(Modifier.height(13.dp))
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceEvenly) {
                record.top6.forEach { LotteryBall(it, size = 34.dp) }
            }
            record.actualRank?.let { rank ->
                Spacer(Modifier.height(8.dp))
                Text(
                    "实际号码矩阵排名：第$rank · Brier " +
                        "${record.brierScore?.format2() ?: "--"} · LogLoss " +
                        (record.logLoss?.format2() ?: "--"),
                    color = colors.textDim,
                    fontSize = 8.sp,
                )
            }
            Spacer(Modifier.height(12.dp))
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text(
                    "哈希 ${record.forecastHash.take(12)}…",
                    color = colors.textDim,
                    fontSize = 7.sp,
                )
                Text(formatTime(record.createdAtEpochMs), color = colors.textDim, fontSize = 7.sp)
            }
        }
    }
}

private fun settlementLabel(top6Hit: Boolean?, top7Hit: Boolean?): String = when {
    top6Hit == null -> "待开奖"
    top6Hit -> "六码命中"
    top7Hit == true -> "七码命中"
    else -> "未命中"
}

@Composable
fun DataScreen(
    state: AppUiState,
    paletteMode: PaletteMode,
    aiConfigs: List<AiConfig>,
    aiAvailableModels: Map<String, List<String>>,
    onPaletteChanged: (PaletteMode) -> Unit,
    onSelectLottery: (LotteryType) -> Unit,
    onSaveAiConfig: (AiConfig) -> Unit,
    onDeleteAiConfig: (String) -> Unit,
    onTestAiConnection: (String) -> Unit,
    onLoadAiModels: (String) -> Unit,
    onSelectAiModel: (String, String) -> Unit,
    onSelectAiMode: (String, AiAnalysisMode) -> Unit,
    onSelectAiReasoningMode: (String, AiReasoningMode) -> Unit,
    onAnalyzeAi: (String) -> Unit,
    onAiConcurrencyChanged: (Int) -> Unit,
    modifier: Modifier = Modifier,
) {
    val colors = LocalTianjiColors.current
    LazyColumn(
        modifier = modifier,
        contentPadding = androidx.compose.foundation.layout.PaddingValues(12.dp, 14.dp, 12.dp, 124.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item { GameSwitcher(state.lottery, onSelectLottery) }
        item {
            SurfaceCard {
                Column(Modifier.padding(18.dp)) {
                    SectionTitle("DATA HEALTH", "原生数据状态", Icons.Rounded.Storage)
                    Spacer(Modifier.height(15.dp))
                    GateRow("原生 SQLite 持久化", true)
                    GateRow("断网只读真实历史，不生成假开奖", true)
                    GateRow("本地模型只使用接口连续历史窗口", true)
                    GateRow("本地与 AI 档案均按目标期精确结算", true)
                    GateRow(
                        state.snapshot?.sourceHealth?.message ?: state.error ?: "等待首次同步",
                        state.snapshot?.sourceHealth?.isFresh == true,
                    )
                    Spacer(Modifier.height(12.dp))
                    Row(
                        Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                    ) {
                        MetricTile(
                            "接口历史",
                            (state.snapshot?.history?.size ?: 0).toString(),
                            "连续期已核验",
                            Modifier.weight(1f),
                        )
                        MetricTile(
                            "预测档案",
                            (
                                state.records.size +
                                    state.aiRecords.size +
                                    state.aiConsensusRecords.size
                                ).toString(),
                            "本地＋AI＋共识",
                            Modifier.weight(1f),
                        )
                        MetricTile(
                            "正式版本",
                            BuildConfig.VERSION_NAME,
                            "矩阵审计",
                            Modifier.weight(1f),
                        )
                    }
                }
            }
        }
        item {
            AiConfigPanel(
                saved = aiConfigs,
                availableModels = aiAvailableModels,
                state = state,
                onSave = onSaveAiConfig,
                onDelete = onDeleteAiConfig,
                onTest = onTestAiConnection,
                onLoadModels = onLoadAiModels,
                onSelectModel = onSelectAiModel,
                onSelectMode = onSelectAiMode,
                onSelectReasoningMode = onSelectAiReasoningMode,
                onAnalyze = onAnalyzeAi,
                onConcurrencyChanged = onAiConcurrencyChanged,
            )
        }
        item {
            SurfaceCard {
                Column(Modifier.padding(18.dp)) {
                    SectionTitle(
                        "MIUIX APPEARANCE",
                        "动态取色",
                        Icons.Rounded.ColorLens,
                        if (colors.monetSupported) {
                            "已直接连接 Android 系统 Monet 色板"
                        } else {
                            "当前 Android 版本不支持 Monet，使用稳定后备色"
                        },
                    )
                    Spacer(Modifier.height(13.dp))
                    val monetTint = if (colors.monetSupported) colors.green else colors.amber
                    Row(
                        modifier = Modifier
                            .clip(CircleShape)
                            .background(monetTint.copy(alpha = 0.08f))
                            .border(1.dp, monetTint.copy(alpha = 0.22f), CircleShape)
                            .padding(horizontal = 10.dp, vertical = 8.dp),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Icon(
                            if (colors.monetSupported) {
                                Icons.Rounded.CheckCircle
                            } else {
                                Icons.Rounded.Info
                            },
                            null,
                            tint = monetTint,
                            modifier = Modifier.size(14.dp),
                        )
                        Spacer(Modifier.width(6.dp))
                        Text(
                            if (colors.monetSupported) "系统 Monet 已连接" else "系统 Monet 不可用",
                            color = monetTint,
                            fontSize = 8.sp,
                            fontWeight = FontWeight.Bold,
                        )
                    }
                    Spacer(Modifier.height(14.dp))
                    PaletteMode.entries.chunked(2).forEach { row ->
                        Row(
                            Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.spacedBy(8.dp),
                        ) {
                            row.forEach { mode ->
                                PaletteButton(
                                    mode,
                                    paletteMode == mode,
                                    Modifier.weight(1f),
                                ) { onPaletteChanged(mode) }
                            }
                            if (row.size == 1) Spacer(Modifier.weight(1f))
                        }
                        Spacer(Modifier.height(8.dp))
                    }
                }
            }
        }
        item {
            SurfaceCard {
                Column(Modifier.padding(18.dp)) {
                    SectionTitle("RECENT HISTORY", "最近开奖", Icons.Rounded.Storage)
                    Spacer(Modifier.height(14.dp))
                    state.snapshot?.history?.takeLast(12)?.asReversed()?.forEach { HistoryRow(it) }
                }
            }
        }
    }
}

@Composable
private fun AiConfigPanel(
    saved: List<AiConfig>,
    availableModels: Map<String, List<String>>,
    state: AppUiState,
    onSave: (AiConfig) -> Unit,
    onDelete: (String) -> Unit,
    onTest: (String) -> Unit,
    onLoadModels: (String) -> Unit,
    onSelectModel: (String, String) -> Unit,
    onSelectMode: (String, AiAnalysisMode) -> Unit,
    onSelectReasoningMode: (String, AiReasoningMode) -> Unit,
    onAnalyze: (String) -> Unit,
    onConcurrencyChanged: (Int) -> Unit,
) {
    val colors = LocalTianjiColors.current
    var editingId by remember { mutableStateOf("") }
    var name by remember { mutableStateOf("") }
    var provider by remember { mutableStateOf(AiProvider.DEEPSEEK) }
    var endpoint by remember { mutableStateOf(AiProvider.DEEPSEEK.defaultEndpoint) }
    var model by remember { mutableStateOf(AiProvider.DEEPSEEK.defaultModel) }
    var apiKey by remember { mutableStateOf("") }
    var analysisMode by remember { mutableStateOf(AiAnalysisMode.FAST) }
    var reasoningMode by remember { mutableStateOf(AiReasoningMode.LOW) }
    var reasoningProtocol by remember { mutableStateOf(AiReasoningProtocol.AUTO) }
    var inputPrice by remember { mutableStateOf("") }
    var outputPrice by remember { mutableStateOf("") }
    var editorOpen by remember { mutableStateOf(saved.isEmpty()) }
    val draft = AiConfig(
        id = editingId,
        name = name.trim(),
        provider = provider,
        endpoint = endpoint.trim(),
        model = model.trim(),
        apiKey = apiKey.trim(),
        analysisMode = analysisMode,
        reasoningMode = reasoningMode,
        reasoningProtocol = reasoningProtocol,
        inputPricePerMillion = inputPrice.toDoubleOrNull()?.takeIf { it >= 0.0 },
        outputPricePerMillion = outputPrice.toDoubleOrNull()?.takeIf { it >= 0.0 },
        capability = saved.firstOrNull { it.id == editingId }?.capability,
    )
    val fieldColors = OutlinedTextFieldDefaults.colors(
        focusedBorderColor = colors.accent,
        unfocusedBorderColor = colors.line,
        focusedLabelColor = colors.accent,
        unfocusedLabelColor = colors.textDim,
        focusedTextColor = colors.text,
        unfocusedTextColor = colors.text,
        cursorColor = colors.accent,
    )
    fun resetEditor() {
        editingId = ""
        name = ""
        provider = AiProvider.DEEPSEEK
        endpoint = AiProvider.DEEPSEEK.defaultEndpoint
        model = AiProvider.DEEPSEEK.defaultModel
        apiKey = ""
        analysisMode = AiAnalysisMode.FAST
        reasoningMode = AiReasoningMode.LOW
        reasoningProtocol = AiReasoningProtocol.AUTO
        inputPrice = ""
        outputPrice = ""
    }
    SurfaceCard {
        Column(Modifier.padding(18.dp)) {
            SectionTitle(
                eyebrow = "AI PROFILES",
                title = "多 AI 配置",
                icon = Icons.Rounded.AutoAwesome,
                detail = "各模型独立输出 1–10 概率矩阵；本机验算、前向计分并决定是否形成共识。",
            )
            Spacer(Modifier.height(14.dp))
            Text("同时请求上限", color = colors.textSoft, fontSize = 8.sp, fontWeight = FontWeight.Bold)
            Spacer(Modifier.height(7.dp))
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                (1..3).forEach { count ->
                    MiniActionButton(
                        text = (if (state.aiConcurrency == count) "✓ " else "") + "$count 路",
                        modifier = Modifier.weight(1f),
                        tint = if (state.aiConcurrency == count) colors.accent else colors.textDim,
                    ) { onConcurrencyChanged(count) }
                }
            }
            Spacer(Modifier.height(6.dp))
            Text(
                "默认 3 路并发；遇到供应商限流可降至 1–2 路。相同模型不会重复计入共识，同一目标期不会重复付费调用。",
                color = colors.textDim,
                fontSize = 7.sp,
                lineHeight = 11.sp,
            )
            if (saved.isNotEmpty() && !editorOpen) {
                Spacer(Modifier.height(14.dp))
                val duplicateModelKeys = saved
                    .filter { it.model.isNotBlank() }
                    .groupingBy { it.model.trim().lowercase() }
                    .eachCount()
                    .filterValues { it > 1 }
                    .keys
                if (duplicateModelKeys.isNotEmpty()) {
                    Text(
                        "检测到相同模型的重复配置：仍可分别分析，但只按 1 个独立模型计入共识。",
                        color = colors.amber,
                        fontSize = 7.5.sp,
                        lineHeight = 12.sp,
                    )
                    Spacer(Modifier.height(10.dp))
                }
                saved.forEach { config ->
                    val status = state.aiStatuses[config.id]
                    val statusState = status?.state ?: AiConnectionState.UNTESTED
                    val tint = when (statusState) {
                        AiConnectionState.CONNECTED -> colors.green
                        AiConnectionState.FAILED -> colors.red
                        AiConnectionState.CANCELLED -> colors.amber
                        AiConnectionState.TESTING, AiConnectionState.ANALYZING -> colors.accent
                        AiConnectionState.UNTESTED -> colors.amber
                    }
                    Column(
                        Modifier
                            .fillMaxWidth()
                            .padding(bottom = 9.dp)
                            .clip(RoundedCornerShape(16.dp))
                            .background(Color.White.copy(alpha = 0.024f))
                            .border(1.dp, tint.copy(alpha = 0.24f), RoundedCornerShape(16.dp))
                            .padding(12.dp),
                    ) {
                        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                            Column(Modifier.weight(1f)) {
                                Text(
                                    config.displayName,
                                    color = colors.text,
                                    fontSize = 10.sp,
                                    fontWeight = FontWeight.Bold,
                                )
                                Spacer(Modifier.height(3.dp))
                                Text(
                                    "${config.analysisMode.label} · ${AiReasoningEngine.resolve(config).displayLabel}",
                                    color = colors.textDim,
                                    fontSize = 6.8.sp,
                                    maxLines = 1,
                                    overflow = TextOverflow.Ellipsis,
                                )
                                Text(
                                    status?.message ?: "尚未进行真实接口测试",
                                    color = tint,
                                    fontSize = 7.5.sp,
                                    maxLines = 1,
                                    overflow = TextOverflow.Ellipsis,
                                )
                                config.capability?.let { capability ->
                                    Spacer(Modifier.height(3.dp))
                                    Text(
                                        buildString {
                                            append("能力：矩阵格式 ")
                                            append(if (capability.structuredOutput) "✓" else "×")
                                            append(" · 推理控制 ")
                                            append(if (capability.reasoningControl) "✓" else "×")
                                            append(" · 推理验证 ")
                                            append(if (capability.reasoningVerified) "✓" else "×")
                                            append(" · 用量 ")
                                            append(if (capability.usageReturned) "✓" else "×")
                                        },
                                        color = colors.textSoft,
                                        fontSize = 6.8.sp,
                                        lineHeight = 10.sp,
                                    )
                                }
                            }
                            status?.latencyMs?.let {
                                Text(
                                    "${it}ms",
                                    color = tint,
                                    fontSize = 8.sp,
                                    fontWeight = FontWeight.Bold,
                                )
                            }
                        }
                        Spacer(Modifier.height(9.dp))
                        Row(
                            Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.spacedBy(7.dp),
                        ) {
                            AiAnalysisMode.entries.forEach { mode ->
                                val active = config.analysisMode == mode
                                MiniActionButton(
                                    text = (if (active) "✓ " else "") + mode.label,
                                    modifier = Modifier.weight(1f),
                                    tint = if (active) colors.accent else colors.textDim,
                                ) { onSelectMode(config.id, mode) }
                            }
                        }
                        Spacer(Modifier.height(7.dp))
                        Row(
                            Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.spacedBy(7.dp),
                        ) {
                            AiReasoningMode.entries.forEach { mode ->
                                val active = config.reasoningMode == mode
                                MiniActionButton(
                                    text = (if (active) "✓ " else "") + mode.label,
                                    modifier = Modifier.weight(1f),
                                    tint = if (active) colors.accent else colors.textDim,
                                ) { onSelectReasoningMode(config.id, mode) }
                            }
                        }
                        Spacer(Modifier.height(6.dp))
                        Text(
                            "历史窗口决定发送多少期；推理强度单独控制。120期不等于深度思考。",
                            color = colors.textDim,
                            fontSize = 6.8.sp,
                        )
                        Spacer(Modifier.height(10.dp))
                        Row(
                            Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.spacedBy(6.dp),
                        ) {
                            MiniActionButton(
                                "能力",
                                Modifier.weight(1f),
                                statusState != AiConnectionState.TESTING,
                            ) { onTest(config.id) }
                            MiniActionButton(
                                "模型",
                                Modifier.weight(1f),
                                statusState != AiConnectionState.TESTING,
                            ) { onLoadModels(config.id) }
                            MiniActionButton(
                                "分析",
                                Modifier.weight(1f),
                                !state.isAiAnalyzing,
                            ) { onAnalyze(config.id) }
                            MiniActionButton("编辑", Modifier.weight(1f)) {
                                editingId = config.id
                                name = config.name
                                provider = config.provider
                                endpoint = config.endpoint
                                model = config.model
                                apiKey = config.apiKey
                                analysisMode = config.analysisMode
                                reasoningMode = config.reasoningMode
                                reasoningProtocol = config.reasoningProtocol
                                inputPrice = config.inputPricePerMillion?.toString().orEmpty()
                                outputPrice = config.outputPricePerMillion?.toString().orEmpty()
                                editorOpen = true
                            }
                            MiniActionButton("删除", Modifier.weight(1f), tint = colors.red) {
                                onDelete(config.id)
                                if (editingId == config.id) {
                                    resetEditor()
                                    editorOpen = false
                                }
                            }
                        }
                        val choices = (
                            config.provider.fallbackModels +
                                availableModels[config.id].orEmpty()
                            ).distinct()
                        if (choices.isNotEmpty()) {
                            Spacer(Modifier.height(9.dp))
                            ModelChoiceRow(
                                models = choices,
                                selected = config.model,
                                onSelected = { onSelectModel(config.id, it) },
                            )
                        }
                    }
                }
                MiniActionButton("＋ 新增另一个 AI", Modifier.fillMaxWidth()) {
                    resetEditor()
                    editorOpen = true
                }
            }
            if (editorOpen) {
                Spacer(Modifier.height(16.dp))
                if (saved.isNotEmpty()) {
                    MiniActionButton(
                        "← 返回配置列表",
                        Modifier.fillMaxWidth(),
                        tint = colors.textSoft,
                    ) {
                        resetEditor()
                        editorOpen = false
                    }
                    Spacer(Modifier.height(12.dp))
                }
                Text(
                    if (editingId.isBlank()) "新增 AI 配置" else "编辑 AI 配置",
                    color = colors.text,
                    fontSize = 11.sp,
                    fontWeight = FontWeight.Bold,
                )
                Spacer(Modifier.height(11.dp))
                AiProvider.entries.forEach { item ->
                    val selected = provider == item
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(bottom = 7.dp)
                            .clip(RoundedCornerShape(14.dp))
                            .background(
                                if (selected) colors.accentSoft
                                else Color.White.copy(alpha = 0.022f),
                            )
                            .border(
                                1.dp,
                                if (selected) colors.accent.copy(alpha = 0.35f) else colors.line,
                                RoundedCornerShape(14.dp),
                            )
                            .clickable {
                                provider = item
                                endpoint = item.defaultEndpoint
                                model = item.defaultModel
                                reasoningProtocol = AiReasoningProtocol.AUTO
                            }
                            .padding(horizontal = 12.dp, vertical = 11.dp),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Text(
                            item.label,
                            color = if (selected) colors.text else colors.textSoft,
                            fontSize = 9.sp,
                            modifier = Modifier.weight(1f),
                        )
                        if (selected) SelectedCheck()
                    }
                }
                Spacer(Modifier.height(4.dp))
                Text(
                    "接口历史窗口",
                    color = colors.textSoft,
                    fontSize = 8.sp,
                    fontWeight = FontWeight.Bold,
                )
                Spacer(Modifier.height(7.dp))
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    AiAnalysisMode.entries.forEach { mode ->
                        MiniActionButton(
                            text = mode.label,
                            modifier = Modifier.weight(1f),
                            tint = if (analysisMode == mode) colors.accent else colors.textDim,
                        ) { analysisMode = mode }
                    }
                }
                Spacer(Modifier.height(6.dp))
                Text(analysisMode.detail, color = colors.textDim, fontSize = 7.sp)
                Spacer(Modifier.height(12.dp))
                Text(
                    "推理强度",
                    color = colors.textSoft,
                    fontSize = 8.sp,
                    fontWeight = FontWeight.Bold,
                )
                Spacer(Modifier.height(7.dp))
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(7.dp)) {
                    AiReasoningMode.entries.forEach { mode ->
                        MiniActionButton(
                            text = mode.label,
                            modifier = Modifier.weight(1f),
                            tint = if (reasoningMode == mode) colors.accent else colors.textDim,
                        ) { reasoningMode = mode }
                    }
                }
                Spacer(Modifier.height(6.dp))
                Text(reasoningMode.detail, color = colors.textDim, fontSize = 7.sp)
                if (provider == AiProvider.COMPATIBLE) {
                    Spacer(Modifier.height(12.dp))
                    Text(
                        "兼容接口推理协议",
                        color = colors.textSoft,
                        fontSize = 8.sp,
                        fontWeight = FontWeight.Bold,
                    )
                    Spacer(Modifier.height(7.dp))
                    AiReasoningProtocol.entries.chunked(2).forEach { row ->
                        Row(
                            Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.spacedBy(7.dp),
                        ) {
                            row.forEach { protocol ->
                                MiniActionButton(
                                    text = protocol.label,
                                    modifier = Modifier.weight(1f),
                                    tint = if (reasoningProtocol == protocol) {
                                        colors.accent
                                    } else {
                                        colors.textDim
                                    },
                                ) { reasoningProtocol = protocol }
                            }
                            if (row.size == 1) Spacer(Modifier.weight(1f))
                        }
                        Spacer(Modifier.height(7.dp))
                    }
                }
                Spacer(Modifier.height(6.dp))
                Text(
                    AiReasoningEngine.resolve(draft).displayLabel,
                    color = colors.accent,
                    fontSize = 7.2.sp,
                    lineHeight = 12.sp,
                )
                Spacer(Modifier.height(10.dp))
                OutlinedTextField(
                    value = name,
                    onValueChange = { name = it },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                    label = { Text("配置名称（可选）", fontSize = 8.sp) },
                    placeholder = { Text("例如：DeepSeek 主力", fontSize = 8.sp) },
                    textStyle = androidx.compose.ui.text.TextStyle(fontSize = 9.sp),
                    colors = fieldColors,
                    shape = RoundedCornerShape(14.dp),
                )
                Spacer(Modifier.height(9.dp))
                OutlinedTextField(
                    value = endpoint,
                    onValueChange = { endpoint = it },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                    label = { Text("完整 HTTPS Responses / Chat Completions 地址", fontSize = 8.sp) },
                    textStyle = androidx.compose.ui.text.TextStyle(fontSize = 9.sp),
                    colors = fieldColors,
                    shape = RoundedCornerShape(14.dp),
                )
                Spacer(Modifier.height(9.dp))
                OutlinedTextField(
                    value = model,
                    onValueChange = { model = it },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                    label = { Text("模型名", fontSize = 8.sp) },
                    textStyle = androidx.compose.ui.text.TextStyle(fontSize = 9.sp),
                    colors = fieldColors,
                    shape = RoundedCornerShape(14.dp),
                )
                val editorModels = (
                    provider.fallbackModels + availableModels[editingId].orEmpty()
                    ).distinct()
                if (editorModels.isNotEmpty()) {
                    Spacer(Modifier.height(8.dp))
                    ModelChoiceRow(editorModels, model) { model = it }
                }
                Spacer(Modifier.height(9.dp))
                OutlinedTextField(
                    value = apiKey,
                    onValueChange = { apiKey = it },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                    visualTransformation = PasswordVisualTransformation(),
                    label = { Text("API Key（Keystore 加密保存）", fontSize = 8.sp) },
                    textStyle = androidx.compose.ui.text.TextStyle(fontSize = 9.sp),
                    colors = fieldColors,
                    shape = RoundedCornerShape(14.dp),
                )
                Spacer(Modifier.height(9.dp))
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedTextField(
                        value = inputPrice,
                        onValueChange = {
                            inputPrice = it.filter { char -> char.isDigit() || char == '.' }
                        },
                        modifier = Modifier.weight(1f),
                        singleLine = true,
                        label = { Text("输入价/百万", fontSize = 7.sp) },
                        placeholder = { Text("可选", fontSize = 7.sp) },
                        textStyle = androidx.compose.ui.text.TextStyle(fontSize = 9.sp),
                        colors = fieldColors,
                        shape = RoundedCornerShape(14.dp),
                    )
                    OutlinedTextField(
                        value = outputPrice,
                        onValueChange = {
                            outputPrice = it.filter { char -> char.isDigit() || char == '.' }
                        },
                        modifier = Modifier.weight(1f),
                        singleLine = true,
                        label = { Text("输出价/百万", fontSize = 7.sp) },
                        placeholder = { Text("可选", fontSize = 7.sp) },
                        textStyle = androidx.compose.ui.text.TextStyle(fontSize = 9.sp),
                        colors = fieldColors,
                        shape = RoundedCornerShape(14.dp),
                    )
                }
                Spacer(Modifier.height(5.dp))
                Text(
                    "价格按供应商账单币种填写，仅用于本机估算单次调用成本。",
                    color = colors.textDim,
                    fontSize = 6.8.sp,
                )
                Spacer(Modifier.height(13.dp))
                Button(
                    onClick = {
                        onSave(draft)
                        resetEditor()
                        editorOpen = false
                    },
                    enabled = draft.canQueryModels,
                    modifier = Modifier.fillMaxWidth().height(46.dp),
                    shape = RoundedCornerShape(15.dp),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = colors.accent,
                        contentColor = Color.White,
                        disabledContainerColor = colors.accent.copy(alpha = 0.16f),
                        disabledContentColor = colors.textDim,
                    ),
                ) {
                    Text(
                        when {
                            editingId.isNotBlank() -> "保存修改"
                            draft.model.isBlank() -> "保存并读取模型"
                            else -> "保存并添加 AI"
                        },
                        fontSize = 10.sp,
                        fontWeight = FontWeight.Bold,
                    )
                }
                Spacer(Modifier.height(10.dp))
                Text(
                    "模型列表来自当前供应商的真实 /models 接口；“配置已保存”不代表分析接口成功，仍需测试或完成一次分析。",
                    color = colors.textDim,
                    fontSize = 7.5.sp,
                    lineHeight = 12.sp,
                )
            }
        }
    }
}

@Composable
private fun ModelChoiceRow(
    models: List<String>,
    selected: String,
    onSelected: (String) -> Unit,
) {
    val colors = LocalTianjiColors.current
    Row(
        Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()),
        horizontalArrangement = Arrangement.spacedBy(7.dp),
    ) {
        models.forEach { item ->
            val active = item == selected
            Text(
                text = item,
                color = if (active) colors.text else colors.textSoft,
                fontSize = 7.5.sp,
                fontWeight = if (active) FontWeight.Bold else FontWeight.Medium,
                modifier = Modifier
                    .clip(CircleShape)
                    .background(
                        if (active) colors.accentSoft else Color.White.copy(alpha = 0.025f),
                    )
                    .border(
                        1.dp,
                        if (active) colors.accent.copy(alpha = 0.4f) else colors.line,
                        CircleShape,
                    )
                    .clickable { onSelected(item) }
                    .padding(horizontal = 10.dp, vertical = 8.dp),
            )
        }
    }
}

@Composable
private fun MiniActionButton(
    text: String,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
    tint: Color = LocalTianjiColors.current.accent,
    onClick: () -> Unit,
) {
    val colors = LocalTianjiColors.current
    Box(
        modifier = modifier
            .height(34.dp)
            .clip(RoundedCornerShape(11.dp))
            .background(tint.copy(alpha = if (enabled) 0.1f else 0.035f))
            .border(
                1.dp,
                tint.copy(alpha = if (enabled) 0.24f else 0.08f),
                RoundedCornerShape(11.dp),
            )
            .clickable(enabled = enabled, onClick = onClick),
        contentAlignment = Alignment.Center,
    ) {
        Text(
            text,
            color = if (enabled) tint else colors.textDim,
            fontSize = 7.5.sp,
            fontWeight = FontWeight.Bold,
        )
    }
}

@Composable
private fun PaletteButton(
    mode: PaletteMode,
    selected: Boolean,
    modifier: Modifier,
    onClick: () -> Unit,
) {
    val colors = LocalTianjiColors.current
    Row(
        modifier = modifier
            .height(45.dp)
            .clip(RoundedCornerShape(14.dp))
            .background(
                if (selected) colors.accentSoft else Color.White.copy(alpha = 0.025f),
            )
            .border(
                1.dp,
                if (selected) colors.accent.copy(alpha = 0.34f) else colors.line,
                RoundedCornerShape(14.dp),
            )
            .clickable(onClick = onClick)
            .padding(horizontal = 11.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Box(
            Modifier
                .size(17.dp)
                .clip(CircleShape)
                .background(mode.preview)
                .border(1.dp, Color.White.copy(alpha = 0.22f), CircleShape),
        )
        Spacer(Modifier.width(9.dp))
        Text(
            mode.label,
            color = if (selected) colors.text else colors.textSoft,
            fontSize = 9.sp,
            modifier = Modifier.weight(1f),
        )
        if (selected) SelectedCheck()
    }
}

@Composable
private fun HistoryRow(draw: Draw) {
    val colors = LocalTianjiColors.current
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .height(44.dp)
            .border(width = 0.dp, color = Color.Transparent),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(
            draw.period.takeLast(7),
            color = colors.textDim,
            fontSize = 8.sp,
            modifier = Modifier.width(58.dp),
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
        )
        Row(Modifier.weight(1f), horizontalArrangement = Arrangement.spacedBy(4.dp)) {
            draw.numbers.forEach { LotteryBall(it, size = 24.dp) }
        }
    }
}

@Composable
private fun GateRow(text: String, passed: Boolean) {
    val colors = LocalTianjiColors.current
    Row(
        modifier = Modifier.fillMaxWidth().padding(vertical = 7.dp),
        verticalAlignment = Alignment.Top,
    ) {
        Icon(
            if (passed) Icons.Rounded.CheckCircle else Icons.Rounded.ErrorOutline,
            null,
            tint = if (passed) colors.green else colors.amber,
            modifier = Modifier.size(15.dp),
        )
        Spacer(Modifier.width(9.dp))
        Text(text, color = colors.textSoft, fontSize = 9.sp, lineHeight = 14.sp)
    }
}

@Composable
private fun ModelRow(rank: Int, model: ModelPerformance) {
    val colors = LocalTianjiColors.current
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(14.dp))
            .background(Color.White.copy(alpha = 0.024f))
            .border(1.dp, colors.line, RoundedCornerShape(14.dp))
            .padding(10.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Box(
            Modifier.size(26.dp).clip(RoundedCornerShape(9.dp)).background(colors.accentSoft),
            contentAlignment = Alignment.Center,
        ) {
            Text(
                rank.toString(),
                color = colors.accent,
                fontSize = 9.sp,
                fontWeight = FontWeight.Bold,
            )
        }
        Spacer(Modifier.width(9.dp))
        Column(Modifier.weight(1f)) {
            Text(
                model.name,
                color = colors.textSoft,
                fontSize = 9.sp,
                fontWeight = FontWeight.SemiBold,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
            Spacer(Modifier.height(5.dp))
            LinearProgressIndicator(
                progress = { model.weight.toFloat().coerceIn(0f, 1f) },
                modifier = Modifier.fillMaxWidth().height(4.dp).clip(CircleShape),
                color = if (model.weight > 0.005) colors.accent else colors.textDim,
                trackColor = Color.White.copy(alpha = 0.045f),
            )
        }
        Spacer(Modifier.width(9.dp))
        Column(horizontalAlignment = Alignment.End) {
            Text(
                "${(model.weight * 100).format1()}%",
                color = if (model.weight > 0.005) colors.accent else colors.textDim,
                fontSize = 9.sp,
                fontWeight = FontWeight.Bold,
            )
            Spacer(Modifier.height(4.dp))
            Text(
                "命中 ${(model.hitRate * 100).format1()}%",
                color = colors.textDim,
                fontSize = 7.sp,
            )
        }
    }
}

private fun positionName(position: Int): String = when (position) {
    0 -> "一"
    1 -> "二"
    2 -> "三"
    3 -> "四"
    4 -> "五"
    5 -> "六"
    6 -> "七"
    7 -> "八"
    8 -> "九"
    else -> "十"
}

private fun Double.format1() = String.format(Locale.US, "%.1f", this)
private fun Double.format2() = String.format(Locale.US, "%.2f", this)
private fun formatTime(epoch: Long) =
    SimpleDateFormat("MM-dd HH:mm", Locale.getDefault()).format(Date(epoch))

private fun formatApiTime(epoch: Long): String =
    SimpleDateFormat("HH:mm:ss", Locale.US).apply {
        timeZone = java.util.TimeZone.getTimeZone("Asia/Shanghai")
    }.format(Date(epoch))

private fun formatSyncAge(ageMs: Long): String = when {
    ageMs < 15_000 -> "同步于刚刚"
    ageMs < 60_000 -> "同步于${ageMs.coerceAtLeast(0) / 1_000}秒前"
    ageMs < 3_600_000 -> "同步于${ageMs / 60_000}分钟前"
    else -> "同步于${ageMs / 3_600_000}小时前"
}
