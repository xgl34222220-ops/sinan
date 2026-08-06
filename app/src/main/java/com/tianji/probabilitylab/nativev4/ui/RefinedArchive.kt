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
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.AutoAwesome
import androidx.compose.material.icons.rounded.ContentCopy
import androidx.compose.material.icons.rounded.Cloud
import androidx.compose.material.icons.rounded.Fingerprint
import androidx.compose.material.icons.rounded.KeyboardArrowDown
import androidx.compose.material.icons.rounded.KeyboardArrowUp
import androidx.compose.material.icons.rounded.Memory
import androidx.compose.material.icons.rounded.PhoneAndroid
import androidx.compose.material.icons.rounded.Psychology
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.Icon
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.AnnotatedString
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

private enum class ArchiveSettlementFilter(val label: String) {
    ALL("全部"),
    PENDING("待开奖"),
    HIT("已命中"),
    MISSED("未命中"),
}

private enum class ArchiveSourceFilter(val label: String) {
    ALL("全部来源"),
    CONSENSUS("AI 共识"),
    DEVICE_AI("手机独立 AI"),
    CLOUD_AI("天机云端 AI"),
    CLOUD_LOCAL("天机云端本地"),
    NATIVE("手机本地模型"),
}

private enum class AiArchiveOrigin {
    DEVICE,
    CLOUD_AI,
    CLOUD_LOCAL,
}

private fun aiArchiveOrigin(profileId: String): AiArchiveOrigin = when {
    profileId.startsWith("cloud:ai:", ignoreCase = true) -> AiArchiveOrigin.CLOUD_AI
    profileId.startsWith("cloud:", ignoreCase = true) -> AiArchiveOrigin.CLOUD_LOCAL
    else -> AiArchiveOrigin.DEVICE
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
    var settlementFilterName by rememberSaveable(state.lottery.apiKey) {
        mutableStateOf(ArchiveSettlementFilter.ALL.name)
    }
    var sourceFilterName by rememberSaveable(state.lottery.apiKey) {
        mutableStateOf(ArchiveSourceFilter.ALL.name)
    }
    var periodQuery by rememberSaveable(state.lottery.apiKey) { mutableStateOf("") }
    val selectedLimit = ArchiveDisplayLimit.entries.firstOrNull { it.name == selectedLimitName }
        ?: ArchiveDisplayLimit.RECENT_8
    val maxItems = selectedLimit.count ?: Int.MAX_VALUE
    val settlementFilter = ArchiveSettlementFilter.entries.firstOrNull {
        it.name == settlementFilterName
    } ?: ArchiveSettlementFilter.ALL
    val sourceFilter = ArchiveSourceFilter.entries.firstOrNull {
        it.name == sourceFilterName
    } ?: ArchiveSourceFilter.ALL
    val periodNeedle = periodQuery.trim()
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
    val consensusRecords = state.aiConsensusRecords.filter {
        (sourceFilter == ArchiveSourceFilter.ALL ||
            sourceFilter == ArchiveSourceFilter.CONSENSUS) &&
            archiveMatchesFilter(settlementFilter, it.top6Hit, it.top7Hit) &&
            (periodNeedle.isEmpty() ||
                it.targetPeriod.contains(periodNeedle, ignoreCase = true))
    }
    val deviceAiRecords = state.aiRecords.filter {
        (sourceFilter == ArchiveSourceFilter.ALL ||
            sourceFilter == ArchiveSourceFilter.DEVICE_AI) &&
            aiArchiveOrigin(it.profileId) == AiArchiveOrigin.DEVICE &&
            archiveMatchesFilter(settlementFilter, it.top6Hit, it.top7Hit) &&
            (periodNeedle.isEmpty() ||
                it.targetPeriod.contains(periodNeedle, ignoreCase = true))
    }
    val cloudAiRecords = state.aiRecords.filter {
        (sourceFilter == ArchiveSourceFilter.ALL ||
            sourceFilter == ArchiveSourceFilter.CLOUD_AI) &&
            aiArchiveOrigin(it.profileId) == AiArchiveOrigin.CLOUD_AI &&
            archiveMatchesFilter(settlementFilter, it.top6Hit, it.top7Hit) &&
            (periodNeedle.isEmpty() ||
                it.targetPeriod.contains(periodNeedle, ignoreCase = true))
    }
    val cloudLocalRecords = state.aiRecords.filter {
        (sourceFilter == ArchiveSourceFilter.ALL ||
            sourceFilter == ArchiveSourceFilter.CLOUD_LOCAL) &&
            aiArchiveOrigin(it.profileId) == AiArchiveOrigin.CLOUD_LOCAL &&
            archiveMatchesFilter(settlementFilter, it.top6Hit, it.top7Hit) &&
            (periodNeedle.isEmpty() ||
                it.targetPeriod.contains(periodNeedle, ignoreCase = true))
    }
    val nativeRecords = state.records.filter {

        (sourceFilter == ArchiveSourceFilter.ALL ||
            sourceFilter == ArchiveSourceFilter.NATIVE) &&
            archiveMatchesFilter(settlementFilter, it.top6Hit, it.top7Hit) &&
            (periodNeedle.isEmpty() ||
                it.targetPeriod.contains(periodNeedle, ignoreCase = true))
    }

    LazyColumn(
        modifier = modifier,
        contentPadding = PaddingValues(12.dp, 10.dp, 12.dp, 16.dp),
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

        item("archive-filters") {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedTextField(
                    value = periodQuery,
                    onValueChange = { periodQuery = it },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                    placeholder = { Text("搜索目标期，例如 20260805123") },
                    shape = RoundedCornerShape(14.dp),
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedBorderColor = colors.accent,
                        unfocusedBorderColor = colors.lineStrong,
                        focusedTextColor = colors.text,
                        unfocusedTextColor = colors.text,
                        focusedContainerColor = colors.surfaceStrong,
                        unfocusedContainerColor = colors.surfaceStrong,
                    ),
                )
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .horizontalScroll(rememberScrollState()),
                    horizontalArrangement = Arrangement.spacedBy(7.dp),
                ) {
                    ArchiveSourceFilter.entries.forEach { option ->
                        ArchiveFilterChipV594(
                            label = option.label,
                            active = option == sourceFilter,
                            onClick = { sourceFilterName = option.name },
                        )
                    }
                }
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .horizontalScroll(rememberScrollState()),
                    horizontalArrangement = Arrangement.spacedBy(7.dp),
                ) {
                    ArchiveSettlementFilter.entries.forEach { option ->
                        ArchiveFilterChipV594(
                            label = option.label,
                            active = option == settlementFilter,
                            onClick = { settlementFilterName = option.name },
                        )
                    }
                }
            }
        }

        if (consensusRecords.isNotEmpty()) {
            item {
                ArchiveLabelV2(
                    title = "AI 共识",
                    detail = "多个独立模型共同支持的冻结结果",
                    count = consensusRecords.size,
                    tint = colors.violet,
                    icon = Icons.Rounded.AutoAwesome,
                )
            }
            consensusRecords.take(maxItems).forEach { record ->
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

        if (deviceAiRecords.isNotEmpty()) {
            item {
                ArchiveLabelV2(
                    title = "手机独立 AI",
                    detail = "手机端配置的 AI 接口，每个模型单独冻结并结算",
                    count = deviceAiRecords.size,
                    tint = colors.accent,
                    icon = Icons.Rounded.PhoneAndroid,
                )
            }
            deviceAiRecords.take(maxItems).forEach { record ->
                item("device-ai-${record.forecastHash}") {
                    ArchiveRecordCompactV2(
                        title = "目标期 ${record.targetPeriod}",
                        detail = "${record.profileName} · ${record.model} · 第${positionNameV2(record.position)}名",
                        numbers = record.top6,
                        status = settlementLabelV2(record.top6Hit, record.top7Hit),
                        statusTint = settlementTintV2(record.top6Hit, record.top7Hit),
                        time = formatTimeV2(record.createdAtEpochMs),
                        hash = record.forecastHash,
                        sourceLabel = "手机独立 AI",
                        sourceTint = colors.accent,
                        sourceIcon = Icons.Rounded.PhoneAndroid,
                    )
                }
            }
        }

        if (cloudAiRecords.isNotEmpty()) {
            item {
                ArchiveLabelV2(
                    title = "天机云端 AI",
                    detail = "服务器后台调用 AI 模型生成的独立冻结结果",
                    count = cloudAiRecords.size,
                    tint = colors.violet,
                    icon = Icons.Rounded.Cloud,
                )
            }
            cloudAiRecords.take(maxItems).forEach { record ->
                item("cloud-ai-${record.forecastHash}") {
                    ArchiveRecordCompactV2(
                        title = "目标期 ${record.targetPeriod}",
                        detail = "${record.model} · 第${positionNameV2(record.position)}名",
                        numbers = record.top6,
                        status = settlementLabelV2(record.top6Hit, record.top7Hit),
                        statusTint = settlementTintV2(record.top6Hit, record.top7Hit),
                        time = formatTimeV2(record.createdAtEpochMs),
                        hash = record.forecastHash,
                        sourceLabel = "天机云端 AI",
                        sourceTint = colors.violet,
                        sourceIcon = Icons.Rounded.Cloud,
                    )
                }
            }
        }

        if (cloudLocalRecords.isNotEmpty()) {
            val cloudLocalTint = Color(0xFF35C3D2)
            item {
                ArchiveLabelV2(
                    title = "天机云端本地",
                    detail = "服务器本地算法后台生成，不调用外部 AI 接口",
                    count = cloudLocalRecords.size,
                    tint = cloudLocalTint,
                    icon = Icons.Rounded.Memory,
                )
            }
            cloudLocalRecords.take(maxItems).forEach { record ->
                item("cloud-local-${record.forecastHash}") {
                    ArchiveRecordCompactV2(
                        title = "目标期 ${record.targetPeriod}",
                        detail = "${record.model} · 第${positionNameV2(record.position)}名",
                        numbers = record.top6,
                        status = settlementLabelV2(record.top6Hit, record.top7Hit),
                        statusTint = settlementTintV2(record.top6Hit, record.top7Hit),
                        time = formatTimeV2(record.createdAtEpochMs),
                        hash = record.forecastHash,
                        sourceLabel = "天机云端本地",
                        sourceTint = cloudLocalTint,
                        sourceIcon = Icons.Rounded.Memory,
                    )
                }
            }
        }

        if (nativeRecords.isNotEmpty()) {
            val nativeTint = Color(0xFF35C3D2)
            item {
                ArchiveLabelV2(
                    title = "手机本地模型",
                    detail = "手机端 11 模型集成冻结结果，作为本地算法对照",
                    count = nativeRecords.size,
                    tint = nativeTint,
                    icon = Icons.Rounded.Psychology,
                )
            }
            nativeRecords.take(maxItems).forEach { record ->
                item("native-${record.reportHash}") {
                    ArchiveRecordCompactV2(
                        title = "目标期 ${record.targetPeriod}",
                        detail = "第${positionNameV2(record.position)}名 · 训练至 ${record.trainedThroughPeriod}",
                        numbers = record.top6,
                        status = settlementLabelV2(record.top6Hit, record.top7Hit),
                        statusTint = settlementTintV2(record.top6Hit, record.top7Hit),
                        time = formatTimeV2(record.createdAtEpochMs),
                        hash = record.reportHash,
                        sourceLabel = "手机本地模型",
                        sourceTint = nativeTint,
                        sourceIcon = Icons.Rounded.Psychology,
                    )
                }
            }
        }

        if (nativeRecords.isEmpty() && deviceAiRecords.isEmpty() &&
            cloudAiRecords.isEmpty() && cloudLocalRecords.isEmpty() &&
            consensusRecords.isEmpty()
        ) {
            item {
                EmptyState(
                    if (settlementFilter == ArchiveSettlementFilter.ALL) "暂无冻结档案" else "当前筛选暂无档案",
                    if (settlementFilter == ArchiveSettlementFilter.ALL) {
                        "完成一次预测后会在开奖前自动锁定"
                    } else {
                        "切换筛选条件可查看其他结算状态"
                    },
                    false,
                )
            }
        }
    }
}

@Composable
private fun ArchiveFilterChipV594(
    label: String,
    active: Boolean,
    onClick: () -> Unit,
) {
    val colors = LocalTianjiColors.current
    Text(
        label,
        color = if (active) colors.accent else colors.textSoft,
        fontSize = 11.sp,
        fontWeight = if (active) FontWeight.Bold else FontWeight.Medium,
        modifier = Modifier
            .clip(RoundedCornerShape(12.dp))
            .background(if (active) colors.accentSoft else colors.surfaceStrong)
            .border(
                1.dp,
                if (active) colors.accent.copy(alpha = 0.24f) else colors.line,
                RoundedCornerShape(12.dp),
            )
            .clickable(onClick = onClick)
            .padding(horizontal = 12.dp, vertical = 8.dp),
    )
}

private fun archiveMatchesFilter(
    filter: ArchiveSettlementFilter,
    top6Hit: Boolean?,
    top7Hit: Boolean?,
): Boolean = when (filter) {
    ArchiveSettlementFilter.ALL -> true
    ArchiveSettlementFilter.PENDING -> top6Hit == null && top7Hit == null
    ArchiveSettlementFilter.HIT -> top6Hit == true || top7Hit == true
    ArchiveSettlementFilter.MISSED -> top6Hit == false && top7Hit == false
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
    val clipboard = LocalClipboardManager.current
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
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text(
                            sourceLabel,
                            color = sourceTint,
                            fontSize = 9.sp,
                            fontWeight = FontWeight.Bold,
                            modifier = Modifier
                                .clip(RoundedCornerShape(8.dp))
                                .background(sourceTint.copy(alpha = 0.10f))
                                .padding(horizontal = 6.dp, vertical = 3.dp),
                        )
                        Spacer(Modifier.size(6.dp))
                        Text(
                            detail,
                            color = colors.textDim,
                            fontSize = 10.sp,
                            lineHeight = 14.sp,
                            maxLines = 2,
                            overflow = TextOverflow.Ellipsis,
                            modifier = Modifier.weight(1f),
                        )
                    }
                }
                StatusChipV2(status, statusTint)
            }
            Spacer(Modifier.height(10.dp))
            CompactNumberRowV2(numbers, size = 29, spread = true)
            Spacer(Modifier.height(9.dp))
            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                Text(
                    if (hashExpanded) "验证信息已展开" else "查看验证信息",
                    color = if (hashExpanded) colors.textSoft else colors.textDim,
                    fontSize = 11.sp,
                    fontWeight = FontWeight.Medium,
                    modifier = Modifier.weight(1f),
                )
                Text(time, color = colors.textDim, fontSize = 10.sp)
                Spacer(Modifier.size(5.dp))
                Icon(
                    if (hashExpanded) Icons.Rounded.KeyboardArrowUp else Icons.Rounded.KeyboardArrowDown,
                    contentDescription = if (hashExpanded) "收起验证信息" else "展开验证信息",
                    tint = colors.textDim,
                    modifier = Modifier.size(18.dp),
                )
            }
            if (hashExpanded) {
                Spacer(Modifier.height(9.dp))
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clip(RoundedCornerShape(12.dp))
                        .background(colors.surfaceStrong)
                        .border(1.dp, colors.line, RoundedCornerShape(12.dp))
                        .padding(horizontal = 10.dp, vertical = 9.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Text(
                        "哈希 $hash",
                        color = colors.textSoft,
                        fontSize = 10.sp,
                        lineHeight = 15.sp,
                        modifier = Modifier.weight(1f),
                    )
                    Icon(
                        Icons.Rounded.ContentCopy,
                        contentDescription = "复制完整哈希",
                        tint = colors.accent,
                        modifier = Modifier
                            .size(30.dp)
                            .clip(CircleShape)
                            .clickable { clipboard.setText(AnnotatedString(hash)) }
                            .padding(6.dp),
                    )
                }
            }
        }
    }
}
