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
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.rounded.ArrowBack
import androidx.compose.material.icons.rounded.CheckCircle
import androidx.compose.material.icons.rounded.Cloud
import androidx.compose.material.icons.rounded.Memory
import androidx.compose.material.icons.rounded.NotificationsActive
import androidx.compose.material.icons.rounded.Refresh
import androidx.compose.material.icons.rounded.Schedule
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
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.tianji.probabilitylab.nativev4.push.PushAlert
import com.tianji.probabilitylab.nativev4.push.PushConnectionStatus
import com.tianji.probabilitylab.nativev4.push.PushPreferences
import com.tianji.probabilitylab.nativev4.push.PushProtocol
import com.tianji.probabilitylab.nativev4.ui.theme.LocalTianjiColors
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

private enum class AlertKindFilter(val label: String) {
    ALL("全部"),
    UNREAD("未读"),
    PREDICTION("预测"),
    RISK("预警"),
    RECOVERY("恢复"),
}

private enum class AlertLotteryFilter(val label: String, val key: String) {
    ALL("全部彩种", ""),
    XYFT("幸运飞艇", "xyft"),
    AZXY10("澳洲幸运10", "azxy10"),
}

private enum class AlertSourceFilter(val label: String, val key: String) {
    ALL("全部来源", ""),
    AI("云端 AI", "ai"),
    NATIVE("云端本地", "native"),
}

@Composable
fun RefinedPushAlertCenterScreen(
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
    var kind by rememberSaveable { mutableStateOf(AlertKindFilter.ALL) }
    var lottery by rememberSaveable { mutableStateOf(AlertLotteryFilter.ALL) }
    var source by rememberSaveable { mutableStateOf(AlertSourceFilter.ALL) }
    var showSettings by rememberSaveable { mutableStateOf(false) }

    val filtered = remember(alerts, kind, lottery, source, focusAlertId) {
        alerts
            .asSequence()
            .filter { alert ->
                when (kind) {
                    AlertKindFilter.ALL -> true
                    AlertKindFilter.UNREAD -> !alert.isRead
                    AlertKindFilter.PREDICTION -> alert.eventType == PushProtocol.EVENT_PREDICTION_READY
                    AlertKindFilter.RISK -> alert.isRiskAlert
                    AlertKindFilter.RECOVERY -> alert.eventType == PushProtocol.EVENT_HIT_RECOVERY
                }
            }
            .filter { lottery.key.isBlank() || it.lottery == lottery.key }
            .filter { source.key.isBlank() || it.source == source.key }
            .sortedWith(
                compareByDescending<PushAlert> { it.id == focusAlertId }
                    .thenByDescending { it.id },
            )
            .toList()
    }

    Column(
        modifier = modifier
            .fillMaxSize()
            .background(colors.page),
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .windowInsetsPadding(WindowInsets.statusBars)
                .heightIn(min = 68.dp)
                .background(
                    Brush.verticalGradient(
                        listOf(colors.header, colors.page.copy(alpha = 0.97f)),
                    ),
                )
                .border(0.5.dp, colors.line)
                .padding(horizontal = 6.dp, vertical = 7.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            IconButton(onClick = onClose, modifier = Modifier.size(48.dp)) {
                Icon(
                    Icons.AutoMirrored.Rounded.ArrowBack,
                    contentDescription = "返回",
                    tint = colors.textSoft,
                    modifier = Modifier.size(24.dp),
                )
            }
            Column(Modifier.weight(1f)) {
                Text(
                    "通知中心",
                    color = colors.text,
                    fontSize = 19.sp,
                    fontWeight = FontWeight.ExtraBold,
                )
                Text(
                    connectionTitle(status),
                    color = if (status.registered) colors.green else colors.amber,
                    fontSize = 11.sp,
                    fontWeight = FontWeight.SemiBold,
                )
            }
            IconButton(onClick = onRefresh, modifier = Modifier.size(48.dp)) {
                Icon(
                    Icons.Rounded.Refresh,
                    contentDescription = "刷新通知",
                    tint = colors.accent,
                    modifier = Modifier.size(21.dp),
                )
            }
        }

        LazyColumn(
            modifier = Modifier.fillMaxSize(),
            contentPadding = PaddingValues(12.dp, 12.dp, 12.dp, 30.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            item("connection") {
                AlertConnectionCard(
                    status = status,
                    preferences = preferences,
                    expanded = showSettings,
                    onExpandedChange = { showSettings = !showSettings },
                    onPreferencesChange = onPreferencesChange,
                )
            }

            item("filters") {
                SurfaceCard(radius = 20.dp) {
                    Column(
                        Modifier.padding(horizontal = 12.dp, vertical = 12.dp),
                        verticalArrangement = Arrangement.spacedBy(9.dp),
                    ) {
                        FilterRow(
                            values = AlertKindFilter.entries,
                            selected = kind,
                            label = AlertKindFilter::label,
                            onSelected = { kind = it },
                        )
                        FilterRow(
                            values = AlertLotteryFilter.entries,
                            selected = lottery,
                            label = AlertLotteryFilter::label,
                            onSelected = { lottery = it },
                        )
                        FilterRow(
                            values = AlertSourceFilter.entries,
                            selected = source,
                            label = AlertSourceFilter::label,
                            onSelected = { source = it },
                        )
                    }
                }
            }

            item("history-head") {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Column(Modifier.weight(1f)) {
                        Text(
                            "通知历史",
                            color = colors.text,
                            fontSize = 15.sp,
                            fontWeight = FontWeight.ExtraBold,
                        )
                        Text(
                            "显示 ${filtered.size} 条 · ${alerts.count { !it.isRead }} 条未读",
                            color = colors.textDim,
                            fontSize = 11.sp,
                        )
                    }
                    if (alerts.any { !it.isRead }) {
                        TextButton(onClick = onReadAll) {
                            Text("全部已读", color = colors.accent, fontWeight = FontWeight.Bold)
                        }
                    }
                }
            }

            if (filtered.isEmpty()) {
                item("empty") {
                    SurfaceCard(radius = 20.dp) {
                        Column(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(vertical = 34.dp, horizontal = 18.dp),
                            horizontalAlignment = Alignment.CenterHorizontally,
                        ) {
                            Icon(
                                Icons.Rounded.CheckCircle,
                                contentDescription = null,
                                tint = colors.green,
                                modifier = Modifier.size(36.dp),
                            )
                            Text(
                                "当前筛选没有通知",
                                color = colors.text,
                                fontSize = 13.sp,
                                fontWeight = FontWeight.Bold,
                                modifier = Modifier.padding(top = 9.dp),
                            )
                            Text(
                                "切换筛选条件可查看预测、预警和恢复记录",
                                color = colors.textDim,
                                fontSize = 11.sp,
                            )
                        }
                    }
                }
            } else {
                items(filtered, key = PushAlert::id) { alert ->
                    CompactAlertCard(
                        alert = alert,
                        focused = alert.id == focusAlertId,
                        onRead = { onRead(alert.id) },
                    )
                }
            }
        }
    }
}

@Composable
private fun AlertConnectionCard(
    status: PushConnectionStatus,
    preferences: PushPreferences,
    expanded: Boolean,
    onExpandedChange: () -> Unit,
    onPreferencesChange: (PushPreferences) -> Unit,
) {
    val colors = LocalTianjiColors.current
    val tint = if (status.instantReady) colors.green else if (status.registered) colors.accent else colors.amber
    SurfaceCard(radius = 21.dp) {
        Column(Modifier.padding(14.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Box(
                    modifier = Modifier
                        .size(42.dp)
                        .clip(RoundedCornerShape(14.dp))
                        .background(tint.copy(alpha = 0.12f)),
                    contentAlignment = Alignment.Center,
                ) {
                    Icon(
                        if (status.instantReady) Icons.Rounded.Cloud else Icons.Rounded.Schedule,
                        contentDescription = null,
                        tint = tint,
                        modifier = Modifier.size(22.dp),
                    )
                }
                Spacer(Modifier.width(10.dp))
                Column(Modifier.weight(1f)) {
                    Text(
                        connectionTitle(status),
                        color = colors.text,
                        fontSize = 14.sp,
                        fontWeight = FontWeight.ExtraBold,
                    )
                    Text(
                        status.detail,
                        color = colors.textDim,
                        fontSize = 10.sp,
                        lineHeight = 15.sp,
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
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = 11.dp)
                    .clip(RoundedCornerShape(13.dp))
                    .background(colors.surfaceStrong)
                    .border(1.dp, colors.line, RoundedCornerShape(13.dp))
                    .clickable(onClick = onExpandedChange)
                    .padding(horizontal = 11.dp, vertical = 9.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(
                    if (status.instantReady) "FCM 即时" else "${status.fallbackMinutes} 分钟增量检查",
                    color = tint,
                    fontSize = 10.sp,
                    fontWeight = FontWeight.ExtraBold,
                    modifier = Modifier.weight(1f),
                )
                Text(
                    if (expanded) "收起接收范围" else "管理接收范围",
                    color = colors.accent,
                    fontSize = 10.sp,
                    fontWeight = FontWeight.Bold,
                )
            }
            if (expanded) {
                Spacer(Modifier.size(5.dp))
                CompactPreferenceRow("幸运飞艇", preferences.xyftEnabled) {
                    onPreferencesChange(preferences.copy(xyftEnabled = it))
                }
                CompactPreferenceRow("澳洲幸运10", preferences.azxy10Enabled) {
                    onPreferencesChange(preferences.copy(azxy10Enabled = it))
                }
                CompactPreferenceRow("云端 AI", preferences.aiEnabled) {
                    onPreferencesChange(preferences.copy(aiEnabled = it))
                }
                CompactPreferenceRow("云端本地", preferences.nativeEnabled) {
                    onPreferencesChange(preferences.copy(nativeEnabled = it))
                }
                CompactPreferenceRow("升级预警", preferences.escalationEnabled) {
                    onPreferencesChange(preferences.copy(escalationEnabled = it))
                }
            }
        }
    }
}

@Composable
private fun CompactPreferenceRow(
    label: String,
    checked: Boolean,
    onChecked: (Boolean) -> Unit,
) {
    val colors = LocalTianjiColors.current
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .heightIn(min = 48.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(
            label,
            color = colors.textSoft,
            fontSize = 12.sp,
            fontWeight = FontWeight.SemiBold,
            modifier = Modifier.weight(1f),
        )
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
private fun <T> FilterRow(
    values: List<T>,
    selected: T,
    label: (T) -> String,
    onSelected: (T) -> Unit,
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .horizontalScroll(rememberScrollState()),
        horizontalArrangement = Arrangement.spacedBy(7.dp),
    ) {
        values.forEach { value ->
            FilterChipText(
                text = label(value),
                active = value == selected,
                onClick = { onSelected(value) },
            )
        }
    }
}

@Composable
private fun FilterChipText(text: String, active: Boolean, onClick: () -> Unit) {
    val colors = LocalTianjiColors.current
    Text(
        text,
        color = if (active) Color.White else colors.textSoft,
        fontSize = 10.sp,
        fontWeight = FontWeight.Bold,
        modifier = Modifier
            .clip(CircleShape)
            .background(if (active) colors.accent else colors.surfaceStrong)
            .border(
                1.dp,
                if (active) colors.accent else colors.line,
                CircleShape,
            )
            .clickable(onClick = onClick)
            .padding(horizontal = 11.dp, vertical = 7.dp),
    )
}

@Composable
private fun CompactAlertCard(
    alert: PushAlert,
    focused: Boolean,
    onRead: () -> Unit,
) {
    val colors = LocalTianjiColors.current
    var expanded by rememberSaveable(alert.id) { mutableStateOf(focused) }
    val visual = alertVisual(alert)
    val shape = RoundedCornerShape(19.dp)
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clip(shape)
            .background(
                if (!alert.isRead || focused) visual.accent.copy(alpha = 0.09f)
                else colors.surface,
            )
            .border(
                if (focused) 1.5.dp else 1.dp,
                if (focused || !alert.isRead) visual.accent.copy(alpha = 0.42f) else colors.line,
                shape,
            )
            .clickable {
                if (!alert.isRead) onRead()
                expanded = !expanded
            }
            .padding(13.dp),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Box(
                modifier = Modifier
                    .size(35.dp)
                    .clip(RoundedCornerShape(11.dp))
                    .background(visual.accent.copy(alpha = 0.12f)),
                contentAlignment = Alignment.Center,
            ) {
                Icon(
                    visual.icon,
                    contentDescription = null,
                    tint = visual.accent,
                    modifier = Modifier.size(20.dp),
                )
            }
            Spacer(Modifier.width(9.dp))
            Column(Modifier.weight(1f)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(
                        visual.label,
                        color = visual.accent,
                        fontSize = 10.sp,
                        fontWeight = FontWeight.ExtraBold,
                    )
                    if (alert.lotteryName.isNotBlank()) {
                        Text(
                            " · ${alert.lotteryName}",
                            color = colors.textDim,
                            fontSize = 10.sp,
                            fontWeight = FontWeight.SemiBold,
                        )
                    }
                }
                Text(
                    alert.title,
                    color = colors.text,
                    fontSize = 13.sp,
                    fontWeight = FontWeight.ExtraBold,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
            }
            if (!alert.isRead) {
                Box(
                    Modifier
                        .size(7.dp)
                        .clip(CircleShape)
                        .background(visual.accent),
                )
            }
        }

        if (alert.body.isNotBlank()) {
            Text(
                alert.body,
                color = colors.textSoft,
                fontSize = 11.sp,
                lineHeight = 17.sp,
                maxLines = if (expanded) 8 else 2,
                overflow = TextOverflow.Ellipsis,
                modifier = Modifier.padding(top = 8.dp),
            )
        }

        Row(
            modifier = Modifier.padding(top = 8.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            val period = alert.latestTargetPeriod.ifBlank { "无目标期" }
            Text(
                "目标期 $period",
                color = colors.textSoft,
                fontSize = 10.sp,
                fontWeight = FontWeight.Bold,
                modifier = Modifier.weight(1f),
            )
            Text(
                formatAlertTimeV2(alert.createdAtEpochMs),
                color = colors.textDim,
                fontSize = 10.sp,
            )
        }

        if (expanded) {
            val sourceLine = listOf(alert.sourceName, alert.model)
                .filter(String::isNotBlank)
                .joinToString(" · ")
            if (sourceLine.isNotBlank()) {
                Text(
                    sourceLine,
                    color = colors.textDim,
                    fontSize = 10.sp,
                    lineHeight = 15.sp,
                    modifier = Modifier.padding(top = 6.dp),
                )
            }
            if (alert.recentPeriods.isNotEmpty() && alert.isRiskAlert) {
                Text(
                    "最近期号：${alert.recentPeriods.joinToString("、")}",
                    color = colors.textDim,
                    fontSize = 10.sp,
                    modifier = Modifier.padding(top = 3.dp),
                )
            }
        }
    }
}

private fun connectionTitle(status: PushConnectionStatus): String = when {
    status.instantReady -> "FCM 即时推送"
    status.registered -> "后台增量检查"
    else -> "等待连接"
}

private data class AlertVisualV2(
    val icon: ImageVector,
    val accent: Color,
    val label: String,
)

@Composable
private fun alertVisual(alert: PushAlert): AlertVisualV2 {
    val colors = LocalTianjiColors.current
    return when (alert.eventType) {
        PushProtocol.EVENT_PREDICTION_READY -> AlertVisualV2(
            Icons.Rounded.Cloud,
            colors.accent,
            "预测完成",
        )
        PushProtocol.EVENT_HIT_RECOVERY -> AlertVisualV2(
            Icons.Rounded.CheckCircle,
            colors.green,
            "恢复命中",
        )
        PushProtocol.EVENT_MISS_PREALERT -> AlertVisualV2(
            Icons.Rounded.WarningAmber,
            colors.amber,
            "提前预警",
        )
        PushProtocol.EVENT_MISS_ESCALATION -> AlertVisualV2(
            Icons.Rounded.WarningAmber,
            colors.red,
            "升级预警",
        )
        PushProtocol.EVENT_SERVICE_WARNING -> AlertVisualV2(
            Icons.Rounded.WarningAmber,
            colors.red,
            "服务异常",
        )
        PushProtocol.EVENT_SYSTEM_NOTICE -> AlertVisualV2(
            Icons.Rounded.NotificationsActive,
            colors.violet,
            "系统通知",
        )
        else -> AlertVisualV2(
            if (alert.source == "native") Icons.Rounded.Memory else Icons.Rounded.WarningAmber,
            if (alert.streak > alert.threshold) colors.red else colors.amber,
            "风险预警",
        )
    }
}

private fun formatAlertTimeV2(epochMs: Long): String =
    SimpleDateFormat("MM-dd HH:mm", Locale.getDefault()).format(Date(epochMs))
