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
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.AutoAwesome
import androidx.compose.material.icons.rounded.Fingerprint
import androidx.compose.material.icons.rounded.KeyboardArrowDown
import androidx.compose.material.icons.rounded.Psychology
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.tianji.probabilitylab.nativev4.AppUiState
import com.tianji.probabilitylab.nativev4.model.LotteryType
import com.tianji.probabilitylab.nativev4.ui.theme.LocalTianjiColors

private enum class ArchiveDisplayLimit(val label: String, val count: Int?) {
    RECENT_8("最近 8 条", 8),
    RECENT_20("最近 20 条", 20),
    ALL("显示全部", null),
}

@Composable
fun RefinedArchiveScreen(
    state: AppUiState,
    onSelectLottery: (LotteryType) -> Unit,
    modifier: Modifier = Modifier,
) {
    var selectedLimitName by rememberSaveable(state.lottery.apiKey) {
        mutableStateOf(ArchiveDisplayLimit.RECENT_8.name)
    }
    var limitMenuExpanded by rememberSaveable { mutableStateOf(false) }
    val selectedLimit = ArchiveDisplayLimit.entries.firstOrNull { it.name == selectedLimitName }
        ?: ArchiveDisplayLimit.RECENT_8
    val maxItems = selectedLimit.count ?: Int.MAX_VALUE
    val colors = LocalTianjiColors.current
    val localRate = if (state.liveAudit.settled > 0) {
        "${(state.liveAudit.top6Rate * 100).format1V2()}%"
    } else {
        "暂无"
    }
    val aiSettled = state.aiRecords.count { it.top6Hit != null }
    val aiRate = if (aiSettled > 0) {
        "${(state.aiLiveAudit.top6Rate * 100).format1V2()}%"
    } else {
        "暂无"
    }

    LazyColumn(
        modifier = modifier,
        contentPadding = PaddingValues(12.dp, 10.dp, 12.dp, 88.dp),
        verticalArrangement = Arrangement.spacedBy(9.dp),
    ) {
        item { CompactLotterySwitcher(state.lottery, onSelectLottery) }
        item {
            SurfaceCard(radius = 20.dp) {
                Column(Modifier.padding(14.dp)) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Box(
                            modifier = Modifier
                                .size(39.dp)
                                .clip(RoundedCornerShape(13.dp))
                                .background(
                                    if (state.archiveIntegrity.isValid) {
                                        colors.green.copy(alpha = 0.11f)
                                    } else {
                                        colors.red.copy(alpha = 0.11f)
                                    },
                                )
                                .border(
                                    1.dp,
                                    if (state.archiveIntegrity.isValid) {
                                        colors.green.copy(alpha = 0.20f)
                                    } else {
                                        colors.red.copy(alpha = 0.20f)
                                    },
                                    RoundedCornerShape(13.dp),
                                ),
                            contentAlignment = Alignment.Center,
                        ) {
                            Icon(
                                Icons.Rounded.Fingerprint,
                                contentDescription = null,
                                tint = if (state.archiveIntegrity.isValid) colors.green else colors.red,
                                modifier = Modifier.size(21.dp),
                            )
                        }
                        Spacer(Modifier.size(10.dp))
                        Column(Modifier.weight(1f)) {
                            Text(
                                "真实前向档案",
                                color = colors.text,
                                fontSize = 16.sp,
                                fontWeight = FontWeight.ExtraBold,
                            )
                            Text(
                                if (state.archiveIntegrity.isValid) {
                                    "完整性链正常 · 已核验 ${state.archiveIntegrity.checkedCount} 条"
                                } else {
                                    "完整性链异常 · 请停止采用相关成绩"
                                },
                                color = if (state.archiveIntegrity.isValid) colors.green else colors.red,
                                fontSize = 10.sp,
                                lineHeight = 14.sp,
                            )
                        }
                        Box {
                            Row(
                                modifier = Modifier
                                    .clip(RoundedCornerShape(12.dp))
                                    .background(colors.surfaceStrong)
                                    .border(1.dp, colors.line, RoundedCornerShape(12.dp))
                                    .clickable { limitMenuExpanded = true }
                                    .padding(horizontal = 10.dp, vertical = 8.dp),
                                verticalAlignment = Alignment.CenterVertically,
                            ) {
                                Text(
                                    selectedLimit.label,
                                    color = colors.textSoft,
                                    fontSize = 10.sp,
                                    fontWeight = FontWeight.Bold,
                                )
                                Spacer(Modifier.size(3.dp))
                                Icon(
                                    Icons.Rounded.KeyboardArrowDown,
                                    contentDescription = "选择显示数量",
                                    tint = colors.textDim,
                                    modifier = Modifier.size(17.dp),
                                )
                            }
                            DropdownMenu(
                                expanded = limitMenuExpanded,
                                onDismissRequest = { limitMenuExpanded = false },
                            ) {
                                ArchiveDisplayLimit.entries.forEach { option ->
                                    DropdownMenuItem(
                                        text = {
                                            Text(
                                                option.label,
                                                fontWeight = if (option == selectedLimit) {
                                                    FontWeight.Bold
                                                } else {
                                                    FontWeight.Normal
                                                },
                                            )
                                        },
                                        onClick = {
                                            selectedLimitName = option.name
                                            limitMenuExpanded = false
                                        },
                                    )
                                }
                            }
                        }
                    }
                    Spacer(Modifier.height(12.dp))
                    Row(horizontalArrangement = Arrangement.spacedBy(7.dp)) {
                        CompactMetricV2("已结算", state.liveAudit.settled.toString(), Modifier.weight(1f))
                        CompactMetricV2("独立 AI", aiRate, Modifier.weight(1f))
                        CompactMetricV2("本地模型", localRate, Modifier.weight(1f))
                    }
                }
            }
        }

        if (state.aiConsensusRecords.isNotEmpty()) {
            item {
                ArchiveLabelV2(
                    title = "AI 共识",
                    detail = "多个独立模型共同支持的冻结结果",
                    count = state.aiConsensusRecords.size,
                    tint = colors.violet,
                    icon = Icons.Rounded.AutoAwesome,
                )
            }
            state.aiConsensusRecords.take(maxItems).forEach { record ->
                item("consensus-${record.consensusHash}") {
                    ArchiveRecordCompactV2(
                        title = "目标期 ${record.targetPeriod}",
                        detail = "第${positionNameV2(record.position)}名 · " +
                            "${record.supportingProfiles}/${record.totalProfiles} 模型支持",
                        numbers = record.top6,
                        status = settlementLabelV2(record.top6Hit, record.top7Hit),
                        statusTint = settlementTintV2(record.top6Hit, record.top7Hit),
                        time = formatTimeV2(record.createdAtEpochMs),
                        hash = record.consensusHash,
                        sourceLabel = "AI 共识",
                        sourceTint = colors.violet,
                        sourceIcon = Icons.Rounded.AutoAwesome,
                    )
                }
            }
        }

        if (state.aiRecords.isNotEmpty()) {
            item {
                ArchiveLabelV2(
                    title = "独立 AI",
                    detail = "每个 AI 调用单独冻结并按目标期结算",
                    count = state.aiRecords.size,
                    tint = colors.accent,
                    icon = Icons.Rounded.AutoAwesome,
                )
            }
            state.aiRecords.take(maxItems).forEach { record ->
                item("ai-${record.forecastHash}") {
                    ArchiveRecordCompactV2(
                        title = "目标期 ${record.targetPeriod}",
                        detail = "${record.profileName} · ${record.model} · 第${positionNameV2(record.position)}名",
                        numbers = record.top6,
                        status = settlementLabelV2(record.top6Hit, record.top7Hit),
                        statusTint = settlementTintV2(record.top6Hit, record.top7Hit),
                        time = formatTimeV2(record.createdAtEpochMs),
                        hash = record.forecastHash,
                        sourceLabel = "独立 AI",
                        sourceTint = colors.accent,
                        sourceIcon = Icons.Rounded.AutoAwesome,
                    )
                }
            }
        }

        if (state.records.isNotEmpty()) {
            val nativeTint = Color(0xFF35C3D2)
            item {
                ArchiveLabelV2(
                    title = "本地模型",
                    detail = "11 模型集成冻结结果，作为本地算法对照",
                    count = state.records.size,
                    tint = nativeTint,
                    icon = Icons.Rounded.Psychology,
                )
            }
            state.records.take(maxItems).forEach { record ->
                item("native-${record.reportHash}") {
                    ArchiveRecordCompactV2(
                        title = "目标期 ${record.targetPeriod}",
                        detail = "第${positionNameV2(record.position)}名 · 训练至 ${record.trainedThroughPeriod}",
                        numbers = record.top6,
                        status = settlementLabelV2(record.top6Hit, record.top7Hit),
                        statusTint = settlementTintV2(record.top6Hit, record.top7Hit),
                        time = formatTimeV2(record.createdAtEpochMs),
                        hash = record.reportHash,
                        sourceLabel = "本地模型",
                        sourceTint = nativeTint,
                        sourceIcon = Icons.Rounded.Psychology,
                    )
                }
            }
        }

        if (state.records.isEmpty() && state.aiRecords.isEmpty() && state.aiConsensusRecords.isEmpty()) {
            item { EmptyState("暂无冻结档案", "完成一次预测后会在开奖前自动锁定", false) }
        }
    }
}

@Composable
private fun ArchiveLabelV2(
    title: String,
    detail: String,
    count: Int,
    tint: Color,
    icon: ImageVector,
) {
    val colors = LocalTianjiColors.current
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 4.dp, vertical = 3.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Box(
            modifier = Modifier
                .size(31.dp)
                .clip(RoundedCornerShape(11.dp))
                .background(tint.copy(alpha = 0.11f))
                .border(1.dp, tint.copy(alpha = 0.18f), RoundedCornerShape(11.dp)),
            contentAlignment = Alignment.Center,
        ) {
            Icon(icon, contentDescription = null, tint = tint, modifier = Modifier.size(17.dp))
        }
        Spacer(Modifier.size(9.dp))
        Column(Modifier.weight(1f)) {
            Text(title, color = colors.text, fontSize = 14.sp, fontWeight = FontWeight.Bold)
            Text(detail, color = colors.textDim, fontSize = 10.sp, lineHeight = 14.sp)
        }
        Text(
            "$count 条",
            color = tint,
            fontSize = 10.sp,
            fontWeight = FontWeight.Bold,
            modifier = Modifier
                .clip(RoundedCornerShape(10.dp))
                .background(tint.copy(alpha = 0.10f))
                .padding(horizontal = 8.dp, vertical = 5.dp),
        )
    }
}

@Composable
private fun ArchiveRecordCompactV2(
    title: String,
    detail: String,
    numbers: List<Int>,
    status: String,
    statusTint: Color,
    time: String,
    hash: String,
    sourceLabel: String,
    sourceTint: Color,
    sourceIcon: ImageVector,
) {
    var hashExpanded by rememberSaveable(hash) { mutableStateOf(false) }
    val colors = LocalTianjiColors.current
    SurfaceCard(
        modifier = Modifier.clickable { hashExpanded = !hashExpanded },
        radius = 18.dp,
    ) {
        Column(Modifier.padding(13.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Box(
                    modifier = Modifier
                        .size(34.dp)
                        .clip(RoundedCornerShape(11.dp))
                        .background(sourceTint.copy(alpha = 0.11f))
                        .border(1.dp, sourceTint.copy(alpha = 0.18f), RoundedCornerShape(11.dp)),
                    contentAlignment = Alignment.Center,
                ) {
                    Icon(
                        sourceIcon,
                        contentDescription = null,
                        tint = sourceTint,
                        modifier = Modifier.size(18.dp),
                    )
                }
                Spacer(Modifier.size(9.dp))
                Column(Modifier.weight(1f)) {
                    Text(title, color = colors.text, fontSize = 14.sp, fontWeight = FontWeight.Bold)
                    Text(
                        "$sourceLabel · $detail",
                        color = colors.textDim,
                        fontSize = 10.sp,
                        lineHeight = 14.sp,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
                StatusChipV2(status, statusTint)
            }
            Spacer(Modifier.height(10.dp))
            CompactNumberRowV2(numbers, size = 29, spread = true)
            Spacer(Modifier.height(9.dp))
            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.Top) {
                Text(
                    if (hashExpanded) "哈希 $hash" else "点击卡片查看完整哈希",
                    color = if (hashExpanded) colors.textSoft else colors.textDim,
                    fontSize = 10.sp,
                    lineHeight = 14.sp,
                    maxLines = if (hashExpanded) 3 else 1,
                    overflow = TextOverflow.Ellipsis,
                    modifier = Modifier.weight(1f),
                )
                Spacer(Modifier.size(8.dp))
                Text(time, color = colors.textDim, fontSize = 10.sp)
            }
        }
    }
}
