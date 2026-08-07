package com.tianji.probabilitylab.nativev4.ui

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
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBars
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.rounded.ArrowBack
import androidx.compose.material.icons.rounded.AutoAwesome
import androidx.compose.material.icons.rounded.CheckCircle
import androidx.compose.material.icons.rounded.CloudDone
import androidx.compose.material.icons.rounded.FilterList
import androidx.compose.material.icons.rounded.NotificationsActive
import androidx.compose.material.icons.rounded.Refresh
import androidx.compose.material.icons.rounded.Settings
import androidx.compose.material.icons.rounded.WarningAmber
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.tianji.probabilitylab.nativev4.push.PushAlert
import com.tianji.probabilitylab.nativev4.push.PushConnectionStatus
import com.tianji.probabilitylab.nativev4.push.PushPreferences
import com.tianji.probabilitylab.nativev4.push.PushProtocol
import com.tianji.probabilitylab.nativev4.ui.theme.LocalTianjiColors
import java.time.Instant
import java.time.LocalDate
import java.time.ZoneId

private enum class V62AlertFilter(val label: String) {
    ALL("全部"), UNREAD("未读"), PREDICTION("预测"), RISK("预警"), RECOVERY("恢复"),
}

private enum class V62AlertLottery(val label: String, val key: String) {
    ALL("全部彩种", ""), XYFT("幸运飞艇", "xyft"), AZXY10("澳洲幸运10", "azxy10"),
}

@Composable
fun V62PushAlertCenterScreen(
    alerts: List<PushAlert>,
    preferences: PushPreferences,
    status: PushConnectionStatus,
    focusAlertId: Long?,
    onPreferencesChange: (PushPreferences) -> Unit,
    onRead: (Long) -> Unit,
    onReadAll: () -> Unit,
    onRefresh: () -> Unit,
    onClose: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val colors = LocalTianjiColors.current
    var filterName by rememberSaveable { mutableStateOf(V62AlertFilter.ALL.name) }
    var lotteryName by rememberSaveable { mutableStateOf(V62AlertLottery.ALL.name) }
    var showFilters by rememberSaveable { mutableStateOf(false) }
    var showPreferences by rememberSaveable { mutableStateOf(false) }
    val filter = V62AlertFilter.entries.firstOrNull { it.name == filterName } ?: V62AlertFilter.ALL
    val lottery = V62AlertLottery.entries.firstOrNull { it.name == lotteryName } ?: V62AlertLottery.ALL

    val filtered = remember(alerts, filter, lottery, focusAlertId) {
        alerts.asSequence()
            .filter { alert ->
                when (filter) {
                    V62AlertFilter.ALL -> true
                    V62AlertFilter.UNREAD -> !alert.isRead
                    V62AlertFilter.PREDICTION -> alert.eventType == PushProtocol.EVENT_PREDICTION_READY
                    V62AlertFilter.RISK -> alert.isRiskAlert
                    V62AlertFilter.RECOVERY -> alert.eventType == PushProtocol.EVENT_HIT_RECOVERY
                }
            }
            .filter { lottery.key.isBlank() || it.lottery == lottery.key }
            .sortedWith(
                compareByDescending<PushAlert> { it.id == focusAlertId }
                    .thenByDescending(PushAlert::createdAtEpochMs),
            )
            .toList()
    }
    val sections = remember(filtered) {
        val grouped = linkedMapOf<String, MutableList<PushAlert>>()
        filtered.forEach { alert -> grouped.getOrPut(v62AlertDayLabel(alert.createdAtEpochMs)) { mutableListOf() }.add(alert) }
        grouped
    }

    Column(
        modifier = modifier.fillMaxSize().background(colors.page),
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .windowInsetsPadding(WindowInsets.statusBars)
                .heightIn(min = 62.dp)
                .background(Brush.verticalGradient(listOf(colors.header, colors.page.copy(alpha = 0.95f))))
                .border(0.5.dp, colors.line)
                .padding(horizontal = 6.dp, vertical = 5.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            IconButton(onClick = onClose, modifier = Modifier.size(48.dp)) {
                Icon(Icons.AutoMirrored.Rounded.ArrowBack, contentDescription = "返回", tint = colors.textSoft)
            }
            Column(Modifier.weight(1f)) {
                Text("通知中心", color = colors.text, fontSize = 18.sp, fontWeight = FontWeight.ExtraBold)
                Text(
                    v62ConnectionTitle(status),
                    color = if (status.instantReady) colors.green else if (status.registered) colors.accent else colors.amber,
                    fontSize = 12.sp,
                    fontWeight = FontWeight.SemiBold,
                )
            }
            IconButton(onClick = { showPreferences = !showPreferences }, modifier = Modifier.size(48.dp)) {
                Icon(Icons.Rounded.Settings, contentDescription = "通知设置", tint = if (showPreferences) colors.accent else colors.textSoft)
            }
            IconButton(onClick = onRefresh, modifier = Modifier.size(48.dp)) {
                Icon(Icons.Rounded.Refresh, contentDescription = "刷新通知", tint = colors.textSoft)
            }
        }

        LazyColumn(
            modifier = Modifier.fillMaxSize(),
            contentPadding = PaddingValues(start = 12.dp, end = 12.dp, top = 10.dp, bottom = 26.dp),
            verticalArrangement = Arrangement.spacedBy(9.dp),
        ) {
            item("connection") {
                V62AlertConnectionStrip(
                    status = status,
                    preferences = preferences,
                    expanded = showPreferences,
                    onPreferencesChange = onPreferencesChange,
                )
            }
            item("filters") {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Column(Modifier.weight(1f)) {
                            Text("通知历史", color = colors.text, fontSize = 16.sp, fontWeight = FontWeight.ExtraBold)
                            Text(
                                "${filtered.size} 条结果 · ${alerts.count { !it.isRead }} 条未读",
                                color = colors.textDim,
                                fontSize = 12.sp,
                            )
                        }
                        if (alerts.any { !it.isRead }) {
                            TextButton(onClick = onReadAll) { Text("全部已读", color = colors.accent, fontWeight = FontWeight.Bold) }
                        }
                        Row(
                            modifier = Modifier
                                .heightIn(min = 44.dp)
                                .clip(CircleShape)
                                .background(if (showFilters) colors.accentSoft else colors.surfaceStrong.copy(alpha = 0.7f))
                                .border(1.dp, if (showFilters) colors.accent.copy(alpha = 0.22f) else colors.line, CircleShape)
                                .clickable { showFilters = !showFilters }
                                .padding(horizontal = 12.dp),
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            Icon(Icons.Rounded.FilterList, contentDescription = "筛选通知", tint = if (showFilters) colors.accent else colors.textSoft, modifier = Modifier.size(18.dp))
                            Spacer(Modifier.width(5.dp))
                            Text("筛选", color = if (showFilters) colors.accent else colors.textSoft, fontSize = 12.sp, fontWeight = FontWeight.Bold)
                        }
                    }
                    if (showFilters) {
                        V62AlertChipRow(V62AlertFilter.entries, filter, V62AlertFilter::label) { filterName = it.name }
                        V62AlertChipRow(V62AlertLottery.entries, lottery, V62AlertLottery::label) { lotteryName = it.name }
                    }
                }
            }
            if (filtered.isEmpty()) {
                item("empty") {
                    EmptyState("当前没有匹配通知", "切换筛选条件可查看预测、预警和恢复记录", false)
                }
            } else {
                sections.forEach { (label, sectionAlerts) ->
                    item("section-$label") {
                        Text(
                            label,
                            color = colors.textDim,
                            fontSize = 12.sp,
                            fontWeight = FontWeight.Bold,
                            modifier = Modifier.padding(horizontal = 3.dp, top = 5.dp, bottom = 1.dp),
                        )
                    }
                    sectionAlerts.forEach { alert ->
                        item("alert-${alert.id}") {
                            V62AlertCard(
                                alert = alert,
                                focused = alert.id == focusAlertId,
                                onRead = { onRead(alert.id) },
                            )
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun V62AlertConnectionStrip(
    status: PushConnectionStatus,
    preferences: PushPreferences,
    expanded: Boolean,
    onPreferencesChange: (PushPreferences) -> Unit,
) {
    val colors = LocalTianjiColors.current
    val tint = if (status.instantReady) colors.green else if (status.registered) colors.accent else colors.amber
    SurfaceCard(radius = 20.dp) {
        Column(Modifier.padding(horizontal = 14.dp, vertical = 12.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Box(
                    modifier = Modifier.size(38.dp).clip(RoundedCornerShape(13.dp)).background(tint.copy(alpha = 0.11f)),
                    contentAlignment = Alignment.Center,
                ) {
                    Icon(
                        if (status.instantReady) Icons.Rounded.CloudDone else Icons.Rounded.NotificationsActive,
                        contentDescription = null,
                        tint = tint,
                        modifier = Modifier.size(20.dp),
                    )
                }
                Spacer(Modifier.width(10.dp))
                Column(Modifier.weight(1f)) {
                    Text(v62ConnectionTitle(status), color = colors.text, fontSize = 14.sp, fontWeight = FontWeight.Bold)
                    Text(
                        if (status.instantReady) "FCM 即时到达 · 后台增量检查兜底" else status.detail,
                        color = colors.textDim,
                        fontSize = 12.sp,
                        lineHeight = 17.sp,
                        maxLines = 2,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
                Switch(
                    checked = preferences.enabled,
                    onCheckedChange = { onPreferencesChange(preferences.copy(enabled = it)) },
                    colors = SwitchDefaults.colors(
                        checkedThumbColor = Color.White,
                        checkedTrackColor = colors.accent,
                        uncheckedTrackColor = colors.lineStrong,
                    ),
                )
            }
            if (expanded) {
                Spacer(Modifier.size(8.dp))
                V62PreferenceRow("幸运飞艇", preferences.xyftEnabled) { onPreferencesChange(preferences.copy(xyftEnabled = it)) }
                V62PreferenceRow("澳洲幸运10", preferences.azxy10Enabled) { onPreferencesChange(preferences.copy(azxy10Enabled = it)) }
                V62PreferenceRow("云端 AI", preferences.aiEnabled) { onPreferencesChange(preferences.copy(aiEnabled = it)) }
                V62PreferenceRow("云端本地", preferences.nativeEnabled) { onPreferencesChange(preferences.copy(nativeEnabled = it)) }
                V62PreferenceRow("升级预警", preferences.escalationEnabled) { onPreferencesChange(preferences.copy(escalationEnabled = it)) }
            }
        }
    }
}

@Composable
private fun V62PreferenceRow(label: String, checked: Boolean, onChecked: (Boolean) -> Unit) {
    val colors = LocalTianjiColors.current
    Row(
        modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(label, color = colors.textSoft, fontSize = 12.sp, fontWeight = FontWeight.SemiBold, modifier = Modifier.weight(1f))
        Switch(
            checked = checked,
            onCheckedChange = onChecked,
            colors = SwitchDefaults.colors(
                checkedThumbColor = Color.White,
                checkedTrackColor = colors.accent,
                uncheckedTrackColor = colors.lineStrong,
            ),
        )
    }
}

@Composable
private fun <T> V62AlertChipRow(values: List<T>, selected: T, label: (T) -> String, onSelected: (T) -> Unit) {
    val colors = LocalTianjiColors.current
    Row(
        modifier = Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()),
        horizontalArrangement = Arrangement.spacedBy(7.dp),
    ) {
        values.forEach { value ->
            val active = value == selected
            Text(
                label(value),
                color = if (active) colors.accent else colors.textSoft,
                fontSize = 12.sp,
                fontWeight = if (active) FontWeight.ExtraBold else FontWeight.Medium,
                modifier = Modifier
                    .heightIn(min = 44.dp)
                    .clip(CircleShape)
                    .background(if (active) colors.accentSoft else colors.surfaceStrong.copy(alpha = 0.65f))
                    .border(1.dp, if (active) colors.accent.copy(alpha = 0.22f) else colors.line, CircleShape)
                    .clickable { onSelected(value) }
                    .padding(horizontal = 14.dp, vertical = 12.dp),
            )
        }
    }
}

@Composable
private fun V62AlertCard(alert: PushAlert, focused: Boolean, onRead: () -> Unit) {
    val colors = LocalTianjiColors.current
    val tint = when {
        alert.severity == PushProtocol.SEVERITY_CRITICAL -> colors.red
        alert.isRiskAlert -> colors.amber
        alert.eventType == PushProtocol.EVENT_HIT_RECOVERY -> colors.green
        else -> colors.accent
    }
    val icon = when {
        alert.isRiskAlert -> Icons.Rounded.WarningAmber
        alert.eventType == PushProtocol.EVENT_HIT_RECOVERY -> Icons.Rounded.CheckCircle
        else -> Icons.Rounded.AutoAwesome
    }
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(19.dp))
            .background(if (focused) tint.copy(alpha = 0.11f) else colors.surface.copy(alpha = 0.82f))
            .border(1.dp, if (focused) tint.copy(alpha = 0.28f) else colors.line, RoundedCornerShape(19.dp))
            .clickable {
                if (!alert.isRead) onRead()
            }
            .padding(14.dp),
    ) {
        Row(verticalAlignment = Alignment.Top) {
            Box(
                modifier = Modifier.size(39.dp).clip(RoundedCornerShape(13.dp)).background(tint.copy(alpha = 0.11f)),
                contentAlignment = Alignment.Center,
            ) {
                Icon(icon, null, tint = tint, modifier = Modifier.size(20.dp))
            }
            Spacer(Modifier.width(10.dp))
            Column(Modifier.weight(1f)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(
                        alert.title,
                        color = colors.text,
                        fontSize = 14.sp,
                        fontWeight = if (alert.isRead) FontWeight.Bold else FontWeight.ExtraBold,
                        modifier = Modifier.weight(1f),
                        maxLines = 2,
                        overflow = TextOverflow.Ellipsis,
                    )
                    if (!alert.isRead) {
                        Spacer(Modifier.width(7.dp))
                        Box(Modifier.size(8.dp).clip(CircleShape).background(tint))
                    }
                }
                Text(
                    listOf(alert.lotteryName, alert.sourceName).filter(String::isNotBlank).joinToString(" · "),
                    color = tint,
                    fontSize = 11.sp,
                    fontWeight = FontWeight.Bold,
                )
            }
        }
        Spacer(Modifier.size(9.dp))
        Text(
            alert.body,
            color = colors.textSoft,
            fontSize = 12.sp,
            lineHeight = 18.sp,
            maxLines = 4,
            overflow = TextOverflow.Ellipsis,
        )
        Row(
            modifier = Modifier.fillMaxWidth().padding(top = 9.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            if (alert.latestTargetPeriod.isNotBlank()) {
                Text("目标 ${alert.latestTargetPeriod}", color = colors.textDim, fontSize = 11.sp, modifier = Modifier.weight(1f))
            } else {
                Spacer(Modifier.weight(1f))
            }
            Text(formatTimeV2(alert.createdAtEpochMs), color = colors.textDim, fontSize = 11.sp)
        }
    }
}

private fun v62ConnectionTitle(status: PushConnectionStatus): String = when {
    status.instantReady -> "即时推送已就绪"
    status.registered -> "推送已注册，使用轮询兜底"
    status.firebaseConfigured || status.serverConfigured -> "推送正在连接"
    else -> "推送服务待配置"
}

private fun v62AlertDayLabel(epochMs: Long): String {
    val zone = ZoneId.systemDefault()
    val date = Instant.ofEpochMilli(epochMs).atZone(zone).toLocalDate()
    val today = LocalDate.now(zone)
    return when (date) {
        today -> "今天"
        today.minusDays(1) -> "昨天"
        else -> "%02d-%02d".format(date.monthValue, date.dayOfMonth)
    }
}
