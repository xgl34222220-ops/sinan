package com.tianji.probabilitylab.nativev4.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
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
import androidx.compose.material.icons.rounded.Fingerprint
import androidx.compose.material3.Icon
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.tianji.probabilitylab.nativev4.AppUiState
import com.tianji.probabilitylab.nativev4.model.LotteryType
import com.tianji.probabilitylab.nativev4.ui.theme.LocalTianjiColors

@Composable
fun RefinedArchiveScreen(
    state: AppUiState,
    onSelectLottery: (LotteryType) -> Unit,
    modifier: Modifier = Modifier,
) {
    var showAll by rememberSaveable(state.lottery.apiKey) { mutableStateOf(false) }
    val colors = LocalTianjiColors.current
    val maxItems = if (showAll) Int.MAX_VALUE else 8
    LazyColumn(
        modifier = modifier,
        contentPadding = PaddingValues(12.dp, 12.dp, 12.dp, 96.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        item { CompactLotterySwitcher(state.lottery, onSelectLottery) }
        item {
            SurfaceCard(radius = 21.dp) {
                Column(Modifier.padding(15.dp)) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(
                            Icons.Rounded.Fingerprint,
                            contentDescription = null,
                            tint = if (state.archiveIntegrity.isValid) colors.green else colors.red,
                            modifier = Modifier.size(22.dp),
                        )
                        Spacer(Modifier.size(9.dp))
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
                            )
                        }
                        Switch(
                            checked = showAll,
                            onCheckedChange = { showAll = it },
                            colors = SwitchDefaults.colors(
                                checkedThumbColor = Color.White,
                                checkedTrackColor = colors.accent,
                            ),
                        )
                    }
                    Spacer(Modifier.height(13.dp))
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        CompactMetricV2("已结算", state.liveAudit.settled.toString(), Modifier.weight(1f))
                        CompactMetricV2(
                            "本机六码",
                            "${(state.liveAudit.top6Rate * 100).format1V2()}%",
                            Modifier.weight(1f),
                        )
                        CompactMetricV2(
                            "AI 六码",
                            "${(state.aiLiveAudit.top6Rate * 100).format1V2()}%",
                            Modifier.weight(1f),
                        )
                    }
                }
            }
        }

        if (state.aiConsensusRecords.isNotEmpty()) {
            item { ArchiveLabelV2("AI 共识", "多个独立模型形成的冻结结果") }
            state.aiConsensusRecords.take(maxItems).forEach { record ->
                item("consensus-${record.id}") {
                    ArchiveRecordCompactV2(
                        title = "目标期 ${record.targetPeriod}",
                        detail = "AI 共识 · 第${positionNameV2(record.position)}名 · " +
                            "${record.supportingProfiles}/${record.totalProfiles} 模型支持",
                        numbers = record.top6,
                        status = settlementLabelV2(record.top6Hit, record.top7Hit),
                        statusTint = settlementTintV2(record.top6Hit, record.top7Hit),
                        time = formatTimeV2(record.createdAtEpochMs),
                        hash = record.consensusHash,
                    )
                }
            }
        }

        if (state.records.isNotEmpty()) {
            item { ArchiveLabelV2("本机模型", "11 模型集成冻结结果") }
            state.records.take(maxItems).forEach { record ->
                item("native-${record.id}") {
                    ArchiveRecordCompactV2(
                        title = "目标期 ${record.targetPeriod}",
                        detail = "第${positionNameV2(record.position)}名 · 训练至 ${record.trainedThroughPeriod}",
                        numbers = record.top6,
                        status = settlementLabelV2(record.top6Hit, record.top7Hit),
                        statusTint = settlementTintV2(record.top6Hit, record.top7Hit),
                        time = formatTimeV2(record.createdAtEpochMs),
                        hash = record.reportHash,
                    )
                }
            }
        }

        if (state.aiRecords.isNotEmpty()) {
            item { ArchiveLabelV2("独立 AI", "每个 AI 调用单独冻结和结算") }
            state.aiRecords.take(maxItems).forEach { record ->
                item("ai-${record.id}") {
                    ArchiveRecordCompactV2(
                        title = "目标期 ${record.targetPeriod}",
                        detail = "${record.profileName} · ${record.model} · 第${positionNameV2(record.position)}名",
                        numbers = record.top6,
                        status = settlementLabelV2(record.top6Hit, record.top7Hit),
                        statusTint = settlementTintV2(record.top6Hit, record.top7Hit),
                        time = formatTimeV2(record.createdAtEpochMs),
                        hash = record.forecastHash,
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
private fun ArchiveLabelV2(title: String, detail: String) {
    val colors = LocalTianjiColors.current
    Column(Modifier.padding(horizontal = 4.dp, vertical = 2.dp)) {
        Text(title, color = colors.text, fontSize = 13.sp, fontWeight = FontWeight.Bold)
        Text(detail, color = colors.textDim, fontSize = 10.sp)
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
) {
    val colors = LocalTianjiColors.current
    SurfaceCard(radius = 19.dp) {
        Column(Modifier.padding(13.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f)) {
                    Text(title, color = colors.text, fontSize = 13.sp, fontWeight = FontWeight.Bold)
                    Text(
                        detail,
                        color = colors.textDim,
                        fontSize = 10.sp,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
                StatusChipV2(status, statusTint)
            }
            Spacer(Modifier.height(11.dp))
            CompactNumberRowV2(numbers, size = 29, spread = true)
            Spacer(Modifier.height(10.dp))
            Row(Modifier.fillMaxWidth()) {
                Text(
                    "哈希 ${hash.take(12)}…",
                    color = colors.textDim,
                    fontSize = 9.sp,
                    modifier = Modifier.weight(1f),
                )
                Text(time, color = colors.textDim, fontSize = 9.sp)
            }
        }
    }
}
