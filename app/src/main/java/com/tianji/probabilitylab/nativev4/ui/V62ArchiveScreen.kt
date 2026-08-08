package com.tianji.probabilitylab.nativev4.ui

import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.AutoAwesome
import androidx.compose.material.icons.rounded.CheckCircle
import androidx.compose.material.icons.rounded.Cloud
import androidx.compose.material.icons.rounded.FilterList
import androidx.compose.material.icons.rounded.Fingerprint
import androidx.compose.material.icons.rounded.Memory
import androidx.compose.material.icons.rounded.PhoneAndroid
import androidx.compose.material.icons.rounded.Search
import androidx.compose.material3.Icon
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
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
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.tianji.probabilitylab.nativev4.AppUiState
import com.tianji.probabilitylab.nativev4.model.LotteryType
import com.tianji.probabilitylab.nativev4.ui.theme.LocalTianjiColors
import java.time.Instant
import java.time.LocalDate
import java.time.ZoneId

private enum class V62ArchiveStatus(val label: String) {
    ALL("全部"), PENDING("待开奖"), HIT("已命中"), MISSED("未命中"),
}

private enum class V62ArchiveSource(val label: String) {
    ALL("全部来源"), CONSENSUS("AI 共识"), DEVICE_AI("手机 AI"),
    CLOUD_AI("云端 AI"), CLOUD_LOCAL("云端本地"), NATIVE("本机模型"),
}

private data class V62ArchiveItem(
    val key: String,
    val source: V62ArchiveSource,
    val title: String,
    val detail: String,
    val targetPeriod: String,
    val position: Int,
    val numbers: List<Int>,
    val createdAtEpochMs: Long,
    val top6Hit: Boolean?,
    val top7Hit: Boolean?,
    val hash: String,
)

@OptIn(ExperimentalFoundationApi::class)
@Composable
fun V62ArchiveScreen(
    state: AppUiState,
    onSelectLottery: (LotteryType) -> Unit,
    modifier: Modifier = Modifier,
) {
    val colors = LocalTianjiColors.current
    var query by rememberSaveable(state.lottery.apiKey) { mutableStateOf("") }
    var showFilters by rememberSaveable(state.lottery.apiKey) { mutableStateOf(false) }
    var sourceName by rememberSaveable(state.lottery.apiKey) { mutableStateOf(V62ArchiveSource.ALL.name) }
    var statusName by rememberSaveable(state.lottery.apiKey) { mutableStateOf(V62ArchiveStatus.ALL.name) }
    var visibleCount by rememberSaveable(state.lottery.apiKey) { mutableIntStateOf(120) }
    val source = V62ArchiveSource.entries.firstOrNull { it.name == sourceName } ?: V62ArchiveSource.ALL
    val status = V62ArchiveStatus.entries.firstOrNull { it.name == statusName } ?: V62ArchiveStatus.ALL
    val activeFilterCount = listOf(
        source != V62ArchiveSource.ALL,
        status != V62ArchiveStatus.ALL,
    ).count { it }

    val allItems = remember(
        state.aiConsensusRecords,
        state.aiRecords,
        state.records,
    ) {
        buildList {
            state.aiConsensusRecords.forEach { record ->
                add(
                    V62ArchiveItem(
                        key = "consensus-${record.consensusHash}",
                        source = V62ArchiveSource.CONSENSUS,
                        title = "AI 共识",
                        detail = "${record.supportingProfiles}/${record.totalProfiles} 个独立模型支持",
                        targetPeriod = record.targetPeriod,
                        position = record.position,
                        numbers = record.top6,
                        createdAtEpochMs = record.createdAtEpochMs,
                        top6Hit = record.top6Hit,
                        top7Hit = record.top7Hit,
                        hash = record.consensusHash,
                    ),
                )
            }
            state.aiRecords.forEach { record ->
                val itemSource = when {
                    record.profileId.startsWith("cloud:ai:", ignoreCase = true) -> V62ArchiveSource.CLOUD_AI
                    record.profileId.startsWith("cloud:", ignoreCase = true) -> V62ArchiveSource.CLOUD_LOCAL
                    else -> V62ArchiveSource.DEVICE_AI
                }
                add(
                    V62ArchiveItem(
                        key = "ai-${record.forecastHash}",
                        source = itemSource,
                        title = when (itemSource) {
                            V62ArchiveSource.CLOUD_AI -> "天机云端 AI"
                            V62ArchiveSource.CLOUD_LOCAL -> "天机云端本地"
                            else -> record.profileName.ifBlank { "手机独立 AI" }
                        },
                        detail = record.model,
                        targetPeriod = record.targetPeriod,
                        position = record.position,
                        numbers = record.top6,
                        createdAtEpochMs = record.createdAtEpochMs,
                        top6Hit = record.top6Hit,
                        top7Hit = record.top7Hit,
                        hash = record.forecastHash,
                    ),
                )
            }
            state.records.forEach { record ->
                add(
                    V62ArchiveItem(
                        key = "native-${record.reportHash}",
                        source = V62ArchiveSource.NATIVE,
                        title = "手机本地模型",
                        detail = if (record.certified) "正式验证档案" else "观察档案",
                        targetPeriod = record.targetPeriod,
                        position = record.position,
                        numbers = record.top6,
                        createdAtEpochMs = record.createdAtEpochMs,
                        top6Hit = record.top6Hit,
                        top7Hit = record.top7Hit,
                        hash = record.reportHash,
                    ),
                )
            }
        }.distinctBy(V62ArchiveItem::key).sortedByDescending(V62ArchiveItem::createdAtEpochMs)
    }

    val filtered = remember(allItems, query, source, status) {
        val needle = query.trim()
        allItems.filter { item ->
            (source == V62ArchiveSource.ALL || item.source == source) &&
                when (status) {
                    V62ArchiveStatus.ALL -> true
                    V62ArchiveStatus.PENDING -> item.top6Hit == null
                    V62ArchiveStatus.HIT -> item.top6Hit == true || item.top7Hit == true
                    V62ArchiveStatus.MISSED -> item.top6Hit == false && item.top7Hit != true
                } &&
                (needle.isBlank() ||
                    item.targetPeriod.contains(needle, ignoreCase = true) ||
                    item.title.contains(needle, ignoreCase = true) ||
                    item.detail.contains(needle, ignoreCase = true))
        }
    }

    LaunchedEffect(query, sourceName, statusName) {
        visibleCount = 120
    }
    val shown = filtered.take(visibleCount)
    val shownSections = remember(shown) {
        val grouped = linkedMapOf<String, MutableList<V62ArchiveItem>>()
        shown.forEach { item ->
            grouped.getOrPut(v62ArchiveDayLabel(item.createdAtEpochMs)) { mutableListOf() }.add(item)
        }
        grouped
    }

    LazyColumn(
        modifier = modifier,
        contentPadding = PaddingValues(start = 12.dp, end = 12.dp, top = 10.dp, bottom = 18.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        item("lottery") { CompactLotterySwitcher(state.lottery, onSelectLottery) }
        item("summary") {
            V62ArchiveSummary(
                valid = state.archiveIntegrity.isValid,
                checked = state.archiveIntegrity.checkedCount,
                total = allItems.size,
                settled = allItems.count { it.top6Hit != null },
            )
        }
        stickyHeader("search") {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(colors.page.copy(alpha = 0.97f))
                    .padding(top = 5.dp, bottom = 7.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedTextField(
                        value = query,
                        onValueChange = { query = it },
                        modifier = Modifier.weight(1f),
                        singleLine = true,
                        leadingIcon = {
                            Icon(Icons.Rounded.Search, contentDescription = null, modifier = Modifier.size(19.dp))
                        },
                        placeholder = { Text("搜索期号或来源", fontSize = 12.sp) },
                        shape = RoundedCornerShape(15.dp),
                        colors = OutlinedTextFieldDefaults.colors(
                            focusedBorderColor = colors.accent,
                            unfocusedBorderColor = colors.line,
                            focusedTextColor = colors.text,
                            unfocusedTextColor = colors.text,
                            focusedContainerColor = colors.surfaceStrong.copy(alpha = 0.92f),
                            unfocusedContainerColor = colors.surfaceStrong.copy(alpha = 0.92f),
                        ),
                    )
                    Row(
                        modifier = Modifier
                            .heightIn(min = 50.dp)
                            .clip(RoundedCornerShape(15.dp))
                            .background(if (showFilters || activeFilterCount > 0) colors.accentSoft else colors.surfaceStrong.copy(alpha = 0.92f))
                            .border(
                                1.dp,
                                if (showFilters || activeFilterCount > 0) colors.accent.copy(alpha = 0.25f) else colors.line,
                                RoundedCornerShape(15.dp),
                            )
                            .clickable { showFilters = !showFilters }
                            .padding(horizontal = 13.dp),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Icon(
                            Icons.Rounded.FilterList,
                            contentDescription = "筛选档案",
                            tint = if (showFilters || activeFilterCount > 0) colors.accent else colors.textSoft,
                            modifier = Modifier.size(19.dp),
                        )
                        Spacer(Modifier.width(6.dp))
                        Text(
                            if (activeFilterCount > 0) "筛选 · $activeFilterCount" else "筛选",
                            color = if (showFilters || activeFilterCount > 0) colors.accent else colors.textSoft,
                            fontSize = 12.sp,
                            fontWeight = FontWeight.Bold,
                        )
                    }
                }
                if (showFilters) {
                    V62ArchiveFilterRow(
                        values = V62ArchiveSource.entries,
                        selected = source,
                        label = V62ArchiveSource::label,
                    ) { sourceName = it.name }
                    V62ArchiveFilterRow(
                        values = V62ArchiveStatus.entries,
                        selected = status,
                        label = V62ArchiveStatus::label,
                    ) { statusName = it.name }
                    if (activeFilterCount > 0) {
                        TextButton(
                            onClick = {
                                sourceName = V62ArchiveSource.ALL.name
                                statusName = V62ArchiveStatus.ALL.name
                            },
                            modifier = Modifier.align(Alignment.End),
                        ) {
                            Text("清除筛选", color = colors.textDim, fontWeight = FontWeight.Bold)
                        }
                    }
                }
            }
        }
        item("result-head") {
            Row(
                modifier = Modifier.fillMaxWidth().padding(horizontal = 2.dp, vertical = 2.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text("预测档案", color = colors.text, fontSize = 16.sp, fontWeight = FontWeight.ExtraBold, modifier = Modifier.weight(1f))
                Text(
                    if (shown.size < filtered.size) "当前加载 ${shown.size} / ${filtered.size}" else "当前加载 ${filtered.size} 条",
                    color = colors.textDim,
                    fontSize = 12.sp,
                )
            }
        }
        if (filtered.isEmpty()) {
            item("empty") { EmptyState("没有匹配的档案", "调整搜索词或筛选条件后重试", false) }
        } else {
            shownSections.forEach { (label, items) ->
                stickyHeader("archive-day-$label") {
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .background(colors.page.copy(alpha = 0.96f))
                            .padding(horizontal = 3.dp, vertical = 6.dp),
                    ) {
                        Text(label, color = colors.textDim, fontSize = 12.sp, fontWeight = FontWeight.Bold)
                    }
                }
                items.forEach { item ->
                    item(item.key) { V62ArchiveRecord(item) }
                }
            }
            if (shown.size < filtered.size) {
                item("load-more") {
                    TextButton(
                        onClick = { visibleCount = (visibleCount + 120).coerceAtMost(filtered.size) },
                        modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp),
                    ) {
                        Text(
                            "继续加载 ${minOf(120, filtered.size - shown.size)} 条",
                            color = colors.accent,
                            fontSize = 13.sp,
                            fontWeight = FontWeight.ExtraBold,
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun V62ArchiveSummary(valid: Boolean, checked: Int, total: Int, settled: Int) {
    val colors = LocalTianjiColors.current
    val tint = if (valid) colors.green else colors.red
    SurfaceCard(radius = if (valid) 18.dp else 22.dp) {
        Row(
            modifier = Modifier.padding(horizontal = 13.dp, vertical = if (valid) 10.dp else 14.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Box(
                modifier = Modifier
                    .size(if (valid) 34.dp else 42.dp)
                    .clip(RoundedCornerShape(if (valid) 11.dp else 14.dp))
                    .background(tint.copy(alpha = 0.11f)),
                contentAlignment = Alignment.Center,
            ) {
                Icon(Icons.Rounded.Fingerprint, null, tint = tint, modifier = Modifier.size(if (valid) 18.dp else 22.dp))
            }
            Spacer(Modifier.width(10.dp))
            Column(Modifier.weight(1f)) {
                Text("真实前向档案", color = colors.text, fontSize = if (valid) 14.sp else 16.sp, fontWeight = FontWeight.ExtraBold)
                Text(
                    if (valid) "完整性正常 · 已核验 $checked 条" else "完整性链异常 · 暂停采用相关成绩",
                    color = tint,
                    fontSize = 11.sp,
                    lineHeight = 16.sp,
                )
            }
            Column(horizontalAlignment = Alignment.End) {
                Text("已结算 $settled / 总计 $total", color = colors.text, fontSize = 13.sp, fontWeight = FontWeight.ExtraBold)
                Text("档案结算进度", color = colors.textDim, fontSize = 11.sp)
            }
        }
    }
}

@Composable
private fun <T> V62ArchiveFilterRow(
    values: List<T>,
    selected: T,
    label: (T) -> String,
    onSelected: (T) -> Unit,
) {
    val colors = LocalTianjiColors.current
    Row(
        modifier = Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()),
        horizontalArrangement = Arrangement.spacedBy(7.dp),
    ) {
        values.forEach { item ->
            val active = item == selected
            Text(
                label(item),
                color = if (active) colors.accent else colors.textSoft,
                fontSize = 12.sp,
                fontWeight = if (active) FontWeight.ExtraBold else FontWeight.Medium,
                modifier = Modifier
                    .heightIn(min = 42.dp)
                    .clip(CircleShape)
                    .background(if (active) colors.accentSoft else colors.surfaceStrong.copy(alpha = 0.82f))
                    .border(1.dp, if (active) colors.accent.copy(alpha = 0.22f) else colors.line, CircleShape)
                    .clickable { onSelected(item) }
                    .padding(horizontal = 14.dp, vertical = 11.dp),
            )
        }
    }
}

@Composable
private fun V62ArchiveRecord(item: V62ArchiveItem) {
    val colors = LocalTianjiColors.current
    val tint = when (item.source) {
        V62ArchiveSource.CONSENSUS, V62ArchiveSource.CLOUD_AI -> colors.violet
        V62ArchiveSource.DEVICE_AI -> colors.accent
        V62ArchiveSource.CLOUD_LOCAL -> colors.green
        V62ArchiveSource.NATIVE -> colors.amber
        V62ArchiveSource.ALL -> colors.textDim
    }
    val icon: ImageVector = when (item.source) {
        V62ArchiveSource.CONSENSUS -> Icons.Rounded.AutoAwesome
        V62ArchiveSource.CLOUD_AI, V62ArchiveSource.CLOUD_LOCAL -> Icons.Rounded.Cloud
        V62ArchiveSource.DEVICE_AI -> Icons.Rounded.PhoneAndroid
        V62ArchiveSource.NATIVE -> Icons.Rounded.Memory
        V62ArchiveSource.ALL -> Icons.Rounded.CheckCircle
    }
    val statusTint = settlementTintV2(item.top6Hit, item.top7Hit)
    SurfaceCard(radius = 18.dp) {
        Column(Modifier.padding(13.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Box(
                    modifier = Modifier.size(38.dp).clip(RoundedCornerShape(13.dp)).background(tint.copy(alpha = 0.11f)),
                    contentAlignment = Alignment.Center,
                ) {
                    Icon(icon, null, tint = tint, modifier = Modifier.size(20.dp))
                }
                Spacer(Modifier.width(10.dp))
                Column(Modifier.weight(1f)) {
                    Text(item.title, color = colors.text, fontSize = 14.sp, fontWeight = FontWeight.Bold, maxLines = 1, overflow = TextOverflow.Ellipsis)
                    Text(
                        "目标 ${item.targetPeriod} · 第${positionNameV2(item.position)}名",
                        color = colors.textDim,
                        fontSize = 12.sp,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
                StatusChipV2(settlementLabelV2(item.top6Hit, item.top7Hit), statusTint)
            }
            Spacer(Modifier.size(11.dp))
            CompactNumberRowV2(item.numbers, size = 31, spread = true)
            Spacer(Modifier.size(10.dp))
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(item.detail, color = colors.textSoft, fontSize = 12.sp, modifier = Modifier.weight(1f), maxLines = 1, overflow = TextOverflow.Ellipsis)
                Text(formatTimeV2(item.createdAtEpochMs), color = colors.textDim, fontSize = 11.sp)
            }
        }
    }
}

private fun v62ArchiveDayLabel(epochMs: Long): String {
    val zone = ZoneId.systemDefault()
    val date = Instant.ofEpochMilli(epochMs).atZone(zone).toLocalDate()
    val today = LocalDate.now(zone)
    return when (date) {
        today -> "今天"
        today.minusDays(1) -> "昨天"
        else -> "%02d-%02d".format(date.monthValue, date.dayOfMonth)
    }
}
