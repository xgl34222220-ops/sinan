package com.tianji.probabilitylab.nativev4.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
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
import com.tianji.probabilitylab.nativev4.ai.AiForecast
import com.tianji.probabilitylab.nativev4.ai.AiForecastRecord
import com.tianji.probabilitylab.nativev4.data.CloudRealtimeLottery
import com.tianji.probabilitylab.nativev4.model.LotteryType
import com.tianji.probabilitylab.nativev4.model.PositionPrediction
import com.tianji.probabilitylab.nativev4.ui.theme.LocalTianjiColors
import kotlinx.coroutines.delay
import kotlin.math.roundToInt

@Composable
fun V67ForecastScreen(
    state: AppUiState,
    aiConfigs: List<AiConfig>,
    realtime: Map<LotteryType, CloudRealtimeLottery>,
    onSelectLottery: (LotteryType) -> Unit,
    onRefreshAll: () -> Unit,
    onAnalyzeAllAi: () -> Unit,
    onCancelAi: (String) -> Unit,
    modifier: Modifier = Modifier,
) {
    val report = state.report
    var selectedPosition by rememberSaveable(report?.targetPeriod) {
        mutableIntStateOf(report?.selectedPosition ?: 0)
    }
    var detailTab by rememberSaveable(state.lottery.apiKey) { mutableIntStateOf(0) }

    BoxWithConstraints(modifier = modifier) {
        val wide = maxWidth >= 600.dp
        LazyColumn(
            modifier = Modifier.fillMaxSize(),
            contentPadding = PaddingValues(
                start = if (wide) 16.dp else 12.dp,
                end = if (wide) 16.dp else 12.dp,
                top = if (wide) 14.dp else 10.dp,
                bottom = 20.dp,
            ),
            verticalArrangement = Arrangement.spacedBy(if (wide) 14.dp else 10.dp),
        ) {
            item("dual-realtime") {
                V67DualLotteryStrip(
                    selected = state.lottery,
                    realtime = realtime,
                    fallbackState = state,
                    onSelect = onSelectLottery,
                )
            }

            if (state.snapshot == null || report == null) {
                item("empty") {
                    EmptyState(
                        title = if (state.isLoading) "正在同步两个彩种" else "暂时无法生成预测",
                        detail = state.error ?: "实时开奖与历史数据同步后会自动生成结果",
                        loading = state.isLoading,
                    )
                }
            } else {
                item("live") {
                    V67LiveBand(
                        state = state,
                        realtime = realtime[state.lottery],
                        onRefreshAll = onRefreshAll,
                    )
                }
                item("prediction-pair") {
                    val local = report.positions.getOrNull(selectedPosition) ?: report.selected
                    val aiAggregate = remember(state.aiForecasts, report.targetPeriod) {
                        aggregateAiForecasts(
                            state.aiForecasts.filter { it.targetPeriod == report.targetPeriod },
                        )
                    }
                    if (wide) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.spacedBy(12.dp),
                            verticalAlignment = Alignment.Top,
                        ) {
                            V67LocalPredictionCard(
                                state = state,
                                prediction = local,
                                selectedPosition = selectedPosition,
                                onPosition = { selectedPosition = it },
                                modifier = Modifier.weight(1f),
                            )
                            V67AiPredictionCard(
                                state = state,
                                aiConfigs = aiConfigs,
                                aggregate = aiAggregate,
                                local = local,
                                onAnalyzeAll = onAnalyzeAllAi,
                                onCancel = onCancelAi,
                                modifier = Modifier.weight(1f),
                            )
                        }
                    } else {
                        Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                            V67LocalPredictionCard(
                                state = state,
                                prediction = local,
                                selectedPosition = selectedPosition,
                                onPosition = { selectedPosition = it },
                            )
                            V67AiPredictionCard(
                                state = state,
                                aiConfigs = aiConfigs,
                                aggregate = aiAggregate,
                                local = local,
                                onAnalyzeAll = onAnalyzeAllAi,
                                onCancel = onCancelAi,
                            )
                        }
                    }
                }
                item("detail-tabs") {
                    V67SegmentedTabs(
                        labels = listOf("概率对比", "模型表现"),
                        selected = detailTab,
                        onSelected = { detailTab = it },
                    )
                }
                item("details") {
                    val local = report.positions.getOrNull(selectedPosition) ?: report.selected
                    val aiAggregate = aggregateAiForecasts(
                        state.aiForecasts.filter { it.targetPeriod == report.targetPeriod },
                    )
                    if (detailTab == 0) {
                        V67ProbabilityComparison(local, aiAggregate)
                    } else {
                        V67ModelPerformance(state)
                    }
                }
            }
        }
    }
}

@Composable
private fun V67DualLotteryStrip(
    selected: LotteryType,
    realtime: Map<LotteryType, CloudRealtimeLottery>,
    fallbackState: AppUiState,
    onSelect: (LotteryType) -> Unit,
) {
    val colors = LocalTianjiColors.current
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(18.dp))
            .background(colors.surface.copy(alpha = 0.72f))
            .border(1.dp, colors.line, RoundedCornerShape(18.dp))
            .padding(4.dp),
        horizontalArrangement = Arrangement.spacedBy(4.dp),
    ) {
        LotteryType.entries.forEach { lottery ->
            val item = realtime[lottery]
            val fallback = if (lottery == fallbackState.lottery) fallbackState.snapshot else null
            val period = item?.latestPeriod ?: fallback?.latest?.period ?: "同步中"
            val syncedAt = item?.syncedAtEpochMs ?: fallback?.sourceHealth?.syncedAtEpochMs
            val fresh = syncedAt != null && System.currentTimeMillis() - syncedAt < 30_000L
            val active = selected == lottery
            val tint = if (lottery == LotteryType.XYFT) colors.amber else colors.violet
            Column(
                modifier = Modifier
                    .weight(1f)
                    .clip(RoundedCornerShape(15.dp))
                    .background(if (active) tint.copy(alpha = 0.10f) else Color.Transparent)
                    .clickable { onSelect(lottery) }
                    .padding(horizontal = 11.dp, vertical = 9.dp),
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Box(
                        Modifier
                            .size(6.dp)
                            .clip(CircleShape)
                            .background(if (fresh) colors.green else colors.textDim),
                    )
                    Spacer(Modifier.width(6.dp))
                    Text(
                        lottery.displayName,
                        color = if (active) colors.text else colors.textSoft,
                        fontSize = 13.sp,
                        lineHeight = 17.sp,
                        fontWeight = FontWeight.ExtraBold,
                        maxLines = 1,
                    )
                }
                Spacer(Modifier.height(3.dp))
                Text(
                    period,
                    color = if (active) tint else colors.textDim,
                    fontSize = 11.sp,
                    lineHeight = 15.sp,
                    fontWeight = FontWeight.SemiBold,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
            }
        }
    }
}

@Composable
private fun V67LiveBand(
    state: AppUiState,
    realtime: CloudRealtimeLottery?,
    onRefreshAll: () -> Unit,
) {
    val colors = LocalTianjiColors.current
    val snapshot = state.snapshot ?: return
    val nextDrawAt = realtime?.nextDrawAtEpochMs ?: snapshot.nextDrawAtEpochMs
    var remaining by remember(nextDrawAt) { mutableIntStateOf(-1) }
    var refreshIssued by remember(nextDrawAt) { androidx.compose.runtime.mutableStateOf(false) }

    LaunchedEffect(nextDrawAt) {
        val target = nextDrawAt ?: return@LaunchedEffect
        while (true) {
            remaining = ((target - System.currentTimeMillis()) / 1_000L).coerceAtLeast(0L).toInt()
            if (remaining <= 0) {
                if (!refreshIssued) {
                    refreshIssued = true
                    delay(1_500L)
                    onRefreshAll()
                }
                break
            }
            delay(1_000L)
        }
    }

    val latestPeriod = realtime?.latestPeriod ?: snapshot.latest.period
    val numbers = realtime?.numbers ?: snapshot.latest.numbers
    val nextPeriod = realtime?.nextPeriod ?: snapshot.nextPeriod
    val syncedAt = realtime?.syncedAtEpochMs ?: snapshot.sourceHealth.syncedAtEpochMs
    val fresh = System.currentTimeMillis() - syncedAt < 30_000L

    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(20.dp))
            .background(colors.surface.copy(alpha = 0.62f))
            .border(1.dp, colors.line, RoundedCornerShape(20.dp))
            .padding(14.dp),
    ) {
        Row(verticalAlignment = Alignment.Top) {
            Column(Modifier.weight(1f)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(
                        Icons.Rounded.Sync,
                        contentDescription = null,
                        tint = if (fresh) colors.green else colors.amber,
                        modifier = Modifier.size(16.dp),
                    )
                    Spacer(Modifier.width(6.dp))
                    Text(
                        if (fresh) "双彩种实时同步" else "等待云端快照更新",
                        color = if (fresh) colors.green else colors.amber,
                        fontSize = 12.sp,
                        fontWeight = FontWeight.Bold,
                    )
                }
                Spacer(Modifier.height(4.dp))
                Text(
                    "最新 $latestPeriod",
                    color = colors.text,
                    fontSize = 17.sp,
                    fontWeight = FontWeight.ExtraBold,
                )
                Text(
                    "${ageLabel(syncedAt)} · 目标 $nextPeriod",
                    color = colors.textDim,
                    fontSize = 11.sp,
                )
            }
            Column(horizontalAlignment = Alignment.End) {
                Text("下期开奖", color = colors.textDim, fontSize = 11.sp)
                Text(
                    if (remaining < 0) "--:--" else "%02d:%02d".format(remaining / 60, remaining % 60),
                    color = colors.accent,
                    fontSize = 25.sp,
                    fontWeight = FontWeight.ExtraBold,
                )
            }
        }
        Spacer(Modifier.height(12.dp))
        V67NumberRow(numbers, size = 27)
    }
}

@Composable
private fun V67LocalPredictionCard(
    state: AppUiState,
    prediction: PositionPrediction,
    selectedPosition: Int,
    onPosition: (Int) -> Unit,
    modifier: Modifier = Modifier,
) {
    val colors = LocalTianjiColors.current
    val report = state.report ?: return
    V67Panel(modifier) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Box(
                Modifier
                    .size(38.dp)
                    .clip(RoundedCornerShape(12.dp))
                    .background(colors.accentSoft),
                contentAlignment = Alignment.Center,
            ) {
                Icon(Icons.Rounded.Psychology, null, tint = colors.accent, modifier = Modifier.size(20.dp))
            }
            Spacer(Modifier.width(9.dp))
            Column(Modifier.weight(1f)) {
                Text("本地模型", color = colors.text, fontSize = 15.sp, fontWeight = FontWeight.ExtraBold)
                Text("目标 ${report.targetPeriod} · 开奖前冻结", color = colors.textDim, fontSize = 11.sp)
            }
            V67Pill("第${selectedPosition + 1}名", colors.accent)
        }
        Spacer(Modifier.height(11.dp))
        V67PositionSelector(selectedPosition, onPosition)
        Spacer(Modifier.height(13.dp))
        Text("动态六码", color = colors.textDim, fontSize = 11.sp, fontWeight = FontWeight.Bold)
        Spacer(Modifier.height(8.dp))
        V67NumberRow(prediction.top6, size = 34)
        Spacer(Modifier.height(11.dp))
        Row(horizontalArrangement = Arrangement.spacedBy(7.dp)) {
            V67Metric("覆盖概率", "${(prediction.coverage6 * 100).format1()}%", Modifier.weight(1f))
            V67Metric("第七码", prediction.top7.lastOrNull()?.toString() ?: "—", Modifier.weight(1f))
            V67Metric("边界优势", "${(prediction.boundaryMargin * 100).format1()}%", Modifier.weight(1f))
        }
    }
}

@Composable
private fun V67AiPredictionCard(
    state: AppUiState,
    aiConfigs: List<AiConfig>,
    aggregate: AiAggregate?,
    local: PositionPrediction,
    onAnalyzeAll: () -> Unit,
    onCancel: (String) -> Unit,
    modifier: Modifier = Modifier,
) {
    val colors = LocalTianjiColors.current
    val complete = aiConfigs.count(AiConfig::isComplete)
    val running = state.aiStatuses.values.firstOrNull {
        it.state == AiConnectionState.ANALYZING || it.state == AiConnectionState.TESTING
    }
    val cloudCount = state.aiForecasts.count { it.profileId.startsWith("cloud:ai:") }
    val phoneCount = state.aiForecasts.size - cloudCount
    val overlap = aggregate?.top6?.count { it in local.top6 } ?: 0
    val recent20 = recentTop6Rate(state.aiRecords, 20)
    val recent50 = recentTop6Rate(state.aiRecords, 50)

    V67Panel(modifier) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Box(
                Modifier
                    .size(38.dp)
                    .clip(RoundedCornerShape(12.dp))
                    .background(colors.violet.copy(alpha = 0.11f)),
                contentAlignment = Alignment.Center,
            ) {
                Icon(Icons.Rounded.AutoAwesome, null, tint = colors.violet, modifier = Modifier.size(20.dp))
            }
            Spacer(Modifier.width(9.dp))
            Column(Modifier.weight(1f)) {
                Text("AI v2 联合预测", color = colors.text, fontSize = 15.sp, fontWeight = FontWeight.ExtraBold)
                Text(
                    "云端AI $cloudCount · 手机AI $phoneCount · 配置 $complete",
                    color = colors.textDim,
                    fontSize = 11.sp,
                )
            }
            V67Pill(
                if (state.isAiAnalyzing) "运行中" else aggregate?.let { "第${it.position + 1}名" } ?: "待生成",
                if (state.isAiAnalyzing) colors.accent else colors.violet,
            )
        }

        Spacer(Modifier.height(13.dp))
        if (aggregate != null) {
            Text("AI 动态六码", color = colors.textDim, fontSize = 11.sp, fontWeight = FontWeight.Bold)
            Spacer(Modifier.height(8.dp))
            V67NumberRow(aggregate.top6, size = 34)
            Spacer(Modifier.height(11.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(7.dp)) {
                V67Metric("第七码", aggregate.top7.lastOrNull()?.toString() ?: "—", Modifier.weight(1f))
                V67Metric("与本地重合", "$overlap/6", Modifier.weight(1f))
                V67Metric("AI自评", "${(aggregate.confidence * 100).roundToInt()}%", Modifier.weight(1f))
            }
            Spacer(Modifier.height(8.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(7.dp)) {
                V67Metric("近20期", recent20?.let { "${(it * 100).format1()}%" } ?: "—", Modifier.weight(1f))
                V67Metric("近50期", recent50?.let { "${(it * 100).format1()}%" } ?: "—", Modifier.weight(1f))
                V67Metric("已结算", state.aiLiveAudit.settled.toString(), Modifier.weight(1f))
            }
        } else {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(14.dp))
                    .background(colors.surfaceStrong.copy(alpha = 0.42f))
                    .padding(11.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Icon(Icons.Rounded.Bolt, null, tint = colors.amber, modifier = Modifier.size(18.dp))
                Spacer(Modifier.width(8.dp))
                Text(
                    if (complete > 0) "本期还没有 AI 动态预测" else "先在设置中配置 AI 接口",
                    color = colors.textSoft,
                    fontSize = 12.sp,
                )
            }
        }

        Spacer(Modifier.height(11.dp))
        Button(
            onClick = if (running != null) ({ onCancel(running.profileId) }) else onAnalyzeAll,
            enabled = running != null || complete > 0,
            modifier = Modifier.fillMaxWidth().height(44.dp),
            shape = RoundedCornerShape(13.dp),
            colors = ButtonDefaults.buttonColors(
                containerColor = if (running != null) colors.amber.copy(alpha = 0.14f) else colors.accent,
                contentColor = if (running != null) colors.amber else Color.White,
                disabledContainerColor = colors.surfaceStrong,
                disabledContentColor = colors.textDim,
            ),
        ) {
            if (state.isAiAnalyzing) {
                CircularProgressIndicator(
                    modifier = Modifier.size(17.dp),
                    color = colors.amber,
                    strokeWidth = 2.dp,
                )
                Spacer(Modifier.width(7.dp))
            }
            Text(
                if (running != null) "取消当前 AI 任务" else "生成本期 AI 动态预测",
                fontSize = 12.sp,
                fontWeight = FontWeight.ExtraBold,
            )
        }
    }
}

@Composable
private fun V67ProbabilityComparison(local: PositionPrediction, ai: AiAggregate?) {
    val colors = LocalTianjiColors.current
    V67Panel {
        Text("号码概率对比", color = colors.text, fontSize = 15.sp, fontWeight = FontWeight.ExtraBold)
        Text("同一名次下直接比较本地模型与 AI v2 的动态概率", color = colors.textDim, fontSize = 11.sp)
        Spacer(Modifier.height(11.dp))
        val order = (1..10).sortedByDescending { number ->
            maxOf(local.probabilities.getOrElse(number - 1) { 0.0 }, ai?.probabilities?.getOrElse(number - 1) { 0.0 } ?: 0.0)
        }
        order.forEach { number ->
            val localP = local.probabilities.getOrElse(number - 1) { 0.0 }
            val aiP = ai?.probabilities?.getOrElse(number - 1) { 0.0 }
            Row(
                modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                LotteryBall(number, size = 27.dp, muted = number !in local.top6 && number !in ai.orEmptyTop6())
                Spacer(Modifier.width(8.dp))
                Column(Modifier.weight(1f)) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text("本地", color = colors.textDim, fontSize = 10.sp, modifier = Modifier.width(30.dp))
                        LinearProgressIndicator(
                            progress = { localP.toFloat().coerceIn(0f, 1f) },
                            modifier = Modifier.weight(1f).height(5.dp).clip(CircleShape),
                            color = colors.accent,
                            trackColor = colors.line,
                        )
                        Text("${(localP * 100).format1()}%", color = colors.textSoft, fontSize = 10.sp, modifier = Modifier.width(48.dp), textAlign = TextAlign.End)
                    }
                    Spacer(Modifier.height(3.dp))
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text("AI", color = colors.textDim, fontSize = 10.sp, modifier = Modifier.width(30.dp))
                        LinearProgressIndicator(
                            progress = { aiP.toFloat().coerceIn(0f, 1f) },
                            modifier = Modifier.weight(1f).height(5.dp).clip(CircleShape),
                            color = colors.violet,
                            trackColor = colors.line,
                        )
                        Text(if (ai == null) "—" else "${(aiP * 100).format1()}%", color = colors.textSoft, fontSize = 10.sp, modifier = Modifier.width(48.dp), textAlign = TextAlign.End)
                    }
                }
            }
        }
    }
}

@Composable
private fun V67ModelPerformance(state: AppUiState) {
    val colors = LocalTianjiColors.current
    val report = state.report ?: return
    V67Panel {
        Text("模型表现", color = colors.text, fontSize = 15.sp, fontWeight = FontWeight.ExtraBold)
        Text("权重、真实前向命中率与当前状态", color = colors.textDim, fontSize = 11.sp)
        Spacer(Modifier.height(9.dp))
        report.models.sortedByDescending { it.weight }.forEach { model ->
            Row(
                modifier = Modifier.fillMaxWidth().padding(vertical = 7.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Column(Modifier.weight(1f)) {
                    Text(model.name, color = colors.textSoft, fontSize = 12.sp, fontWeight = FontWeight.Bold)
                    Text(model.status, color = colors.textDim, fontSize = 10.sp, maxLines = 1, overflow = TextOverflow.Ellipsis)
                }
                Text("权重 ${(model.weight * 100).format1()}%", color = colors.accent, fontSize = 11.sp, fontWeight = FontWeight.Bold)
                Spacer(Modifier.width(10.dp))
                Text("命中 ${(model.hitRate * 100).format1()}%", color = colors.textDim, fontSize = 11.sp)
            }
        }
    }
}

@Composable
private fun V67PositionSelector(selected: Int, onSelected: (Int) -> Unit) {
    val colors = LocalTianjiColors.current
    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(4.dp)) {
        (0 until 10).forEach { index ->
            Box(
                modifier = Modifier
                    .weight(1f)
                    .height(31.dp)
                    .clip(RoundedCornerShape(9.dp))
                    .background(if (selected == index) colors.accentSoft else colors.surfaceStrong.copy(alpha = 0.38f))
                    .clickable { onSelected(index) },
                contentAlignment = Alignment.Center,
            ) {
                Text(
                    (index + 1).toString(),
                    color = if (selected == index) colors.accent else colors.textDim,
                    fontSize = 10.sp,
                    fontWeight = if (selected == index) FontWeight.ExtraBold else FontWeight.Medium,
                )
            }
        }
    }
}

@Composable
private fun V67SegmentedTabs(labels: List<String>, selected: Int, onSelected: (Int) -> Unit) {
    val colors = LocalTianjiColors.current
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(14.dp))
            .background(colors.surface.copy(alpha = 0.55f))
            .padding(3.dp),
    ) {
        labels.forEachIndexed { index, label ->
            Text(
                label,
                color = if (selected == index) colors.text else colors.textDim,
                fontSize = 12.sp,
                fontWeight = if (selected == index) FontWeight.ExtraBold else FontWeight.Medium,
                textAlign = TextAlign.Center,
                modifier = Modifier
                    .weight(1f)
                    .clip(RoundedCornerShape(11.dp))
                    .background(if (selected == index) colors.accentSoft else Color.Transparent)
                    .clickable { onSelected(index) }
                    .padding(vertical = 9.dp),
            )
        }
    }
}

@Composable
private fun V67Panel(modifier: Modifier = Modifier, content: @Composable Column.() -> Unit) {
    val colors = LocalTianjiColors.current
    Column(
        modifier = modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(19.dp))
            .background(colors.surface.copy(alpha = 0.78f))
            .border(1.dp, colors.line, RoundedCornerShape(19.dp))
            .padding(13.dp),
    ) {
        @Suppress("UNCHECKED_CAST")
        (content as @Composable Column.() -> Unit).invoke(this)
    }
}

@Composable
private fun V67NumberRow(numbers: List<Int>, size: Int) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceEvenly,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        numbers.forEach { LotteryBall(it, size = size.dp) }
    }
}

@Composable
private fun V67Metric(label: String, value: String, modifier: Modifier = Modifier) {
    val colors = LocalTianjiColors.current
    Column(
        modifier = modifier
            .clip(RoundedCornerShape(12.dp))
            .background(colors.surfaceStrong.copy(alpha = 0.42f))
            .padding(horizontal = 8.dp, vertical = 8.dp),
    ) {
        Text(label, color = colors.textDim, fontSize = 9.sp, maxLines = 1)
        Spacer(Modifier.height(3.dp))
        Text(value, color = colors.text, fontSize = 13.sp, fontWeight = FontWeight.ExtraBold, maxLines = 1)
    }
}

@Composable
private fun V67Pill(text: String, tint: Color) {
    Text(
        text,
        color = tint,
        fontSize = 10.sp,
        fontWeight = FontWeight.ExtraBold,
        modifier = Modifier
            .clip(CircleShape)
            .background(tint.copy(alpha = 0.10f))
            .padding(horizontal = 8.dp, vertical = 5.dp),
    )
}

private data class AiAggregate(
    val position: Int,
    val top6: List<Int>,
    val top7: List<Int>,
    val probabilities: List<Double>,
    val confidence: Double,
)

private fun aggregateAiForecasts(forecasts: List<AiForecast>): AiAggregate? {
    val valid = forecasts.filter { it.probabilities.size == 10 && it.top6.size == 6 && it.top7.size == 7 }
    if (valid.isEmpty()) return null
    val scores = DoubleArray(10)
    var totalWeight = 0.0
    valid.forEach { forecast ->
        val weight = forecast.selfRating.coerceIn(0.20, 1.0)
        totalWeight += weight
        forecast.probabilities.forEachIndexed { index, probability ->
            scores[index] += probability.coerceAtLeast(0.0) * weight
        }
    }
    if (totalWeight > 0.0) {
        scores.indices.forEach { scores[it] /= totalWeight }
    }
    val ranking = scores.indices.sortedByDescending { scores[it] }.map { it + 1 }
    val position = valid.groupingBy { it.position }.eachCount().maxWithOrNull(
        compareBy<Map.Entry<Int, Int>> { it.value }.thenByDescending { -it.key },
    )?.key ?: valid.first().position
    return AiAggregate(
        position = position.coerceIn(0, 9),
        top6 = ranking.take(6),
        top7 = ranking.take(7),
        probabilities = scores.toList(),
        confidence = valid.map { it.selfRating.coerceIn(0.0, 1.0) }.average().coerceIn(0.0, 1.0),
    )
}

private fun recentTop6Rate(records: List<AiForecastRecord>, limit: Int): Double? {
    val settled = records
        .asSequence()
        .filter { it.actualNumber != null && it.top6Hit != null }
        .sortedByDescending { it.createdAtEpochMs }
        .take(limit)
        .toList()
    if (settled.isEmpty()) return null
    return settled.count { it.top6Hit == true }.toDouble() / settled.size.toDouble()
}

private fun AiAggregate?.orEmptyTop6(): List<Int> = this?.top6.orEmpty()

private fun ageLabel(epochMs: Long): String {
    val seconds = ((System.currentTimeMillis() - epochMs).coerceAtLeast(0L) / 1_000L).toInt()
    return when {
        seconds < 3 -> "刚刚同步"
        seconds < 60 -> "${seconds}秒前同步"
        else -> "${seconds / 60}分钟前同步"
    }
}

private fun Double.format1(): String = String.format(java.util.Locale.US, "%.1f", this)
