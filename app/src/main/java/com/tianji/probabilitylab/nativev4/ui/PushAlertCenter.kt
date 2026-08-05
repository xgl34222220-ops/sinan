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
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.tianji.probabilitylab.nativev4.push.PushAlert
import com.tianji.probabilitylab.nativev4.push.PushConnectionStatus
import com.tianji.probabilitylab.nativev4.push.PushPreferences
import com.tianji.probabilitylab.nativev4.ui.theme.LocalTianjiColors
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

@Composable
fun PushAlertCenterScreen(
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
    val ordered = alerts.sortedWith(
        compareByDescending<PushAlert> { it.id == focusAlertId }
            .thenByDescending { it.id },
    )
    val modeTitle = if (status.instantReady) "FCM 即时推送" else "后台检查模式"
    val modeDetail = if (status.instantReady) {
        "云端检测到预警后会直接推送到当前设备"
    } else {
        "系统约每 ${status.fallbackMinutes} 分钟检查一次，并使用本地通知提醒"
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
                    modifier = Modifier.size(25.dp),
                )
            }
            Column(Modifier.weight(1f)) {
                Text(
                    "预警中心",
                    color = colors.text,
                    fontSize = 19.sp,
                    fontWeight = FontWeight.ExtraBold,
                )
                Text(
                    modeTitle,
                    color = if (status.registered) colors.green else colors.amber,
                    fontSize = 11.sp,
                    fontWeight = FontWeight.SemiBold,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
            }
            Box(
                modifier = Modifier
                    .size(48.dp)
                    .padding(2.dp)
                    .clip(RoundedCornerShape(15.dp))
                    .background(colors.glass)
                    .border(1.dp, colors.lineStrong, RoundedCornerShape(15.dp)),
                contentAlignment = Alignment.Center,
            ) {
                IconButton(onClick = onRefresh, modifier = Modifier.size(44.dp)) {
                    Icon(
                        Icons.Rounded.Refresh,
                        "刷新预警",
                        tint = colors.accent,
                        modifier = Modifier.size(21.dp),
                    )
                }
            }
        }

        LazyColumn(
            modifier = Modifier.fillMaxSize(),
            contentPadding = PaddingValues(12.dp, 12.dp, 12.dp, 28.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            item {
                SurfaceCard(radius = 21.dp) {
                    Column(
                        Modifier.padding(horizontal = 14.dp, vertical = 14.dp),
                        verticalArrangement = Arrangement.spacedBy(11.dp),
                    ) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Box(
                                Modifier
                                    .size(44.dp)
                                    .clip(RoundedCornerShape(14.dp))
                                    .background(colors.accentSoft)
                                    .border(
                                        1.dp,
                                        colors.accent.copy(alpha = 0.22f),
                                        RoundedCornerShape(14.dp),
                                    ),
                                contentAlignment = Alignment.Center,
                            ) {
                                Icon(
                                    Icons.Rounded.NotificationsActive,
                                    null,
                                    tint = colors.accent,
                                    modifier = Modifier.size(23.dp),
                                )
                            }
                            Spacer(Modifier.width(11.dp))
                            Column(Modifier.weight(1f)) {
                                Text(
                                    "预测预警",
                                    color = colors.text,
                                    fontSize = 15.sp,
                                    fontWeight = FontWeight.ExtraBold,
                                )
                                Text(
                                    modeDetail,
                                    color = colors.textDim,
                                    fontSize = 11.sp,
                                    lineHeight = 16.sp,
                                    maxLines = 2,
                                    overflow = TextOverflow.Ellipsis,
                                )
                            }
                            StatusDot(status)
                        }

                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .clip(RoundedCornerShape(14.dp))
                                .background(colors.surfaceStrong.copy(alpha = 0.78f))
                                .border(1.dp, colors.line, RoundedCornerShape(14.dp))
                                .padding(horizontal = 12.dp, vertical = 11.dp),
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            Icon(
                                if (status.instantReady) Icons.Rounded.Cloud else Icons.Rounded.Schedule,
                                contentDescription = null,
                                tint = if (status.registered) colors.green else colors.amber,
                                modifier = Modifier.size(19.dp),
                            )
                            Spacer(Modifier.width(9.dp))
                            Column(Modifier.weight(1f)) {
                                Text(
                                    modeTitle,
                                    color = colors.text,
                                    fontSize = 12.sp,
                                    fontWeight = FontWeight.Bold,
                                )
                                Text(
                                    if (status.registered) "设备已登记 · ${status.detail}" else status.detail,
                                    color = colors.textDim,
                                    fontSize = 10.sp,
                                    lineHeight = 15.sp,
                                    maxLines = 2,
                                    overflow = TextOverflow.Ellipsis,
                                )
                            }
                            Text(
                                if (status.instantReady) "即时" else "${status.fallbackMinutes} 分钟",
                                color = if (status.instantReady) colors.green else colors.accent,
                                fontSize = 10.sp,
                                fontWeight = FontWeight.ExtraBold,
                                modifier = Modifier
                                    .clip(CircleShape)
                                    .background(
                                        (if (status.instantReady) colors.green else colors.accent)
                                            .copy(alpha = 0.10f),
                                    )
                                    .padding(horizontal = 9.dp, vertical = 6.dp),
                            )
                        }

                        AlertToggleRow(
                            title = "总开关",
                            detail = "关闭后不再弹出通知，历史预警仍会保留",
                            checked = preferences.enabled,
                            onChecked = {
                                onPreferencesChange(preferences.copy(enabled = it))
                            },
                        )
                    }
                }
            }

            item {
                SurfaceCard(radius = 21.dp) {
                    Column(Modifier.padding(14.dp)) {
                        Text(
                            "接收范围",
                            color = colors.text,
                            fontSize = 14.sp,
                            fontWeight = FontWeight.ExtraBold,
                        )
                        AlertToggleRow(
                            "幸运飞艇",
                            "该彩种每个预测来源独立统计",
                            preferences.xyftEnabled,
                        ) { onPreferencesChange(preferences.copy(xyftEnabled = it)) }
                        AlertToggleRow(
                            "澳洲幸运10",
                            "该彩种每个预测来源独立统计",
                            preferences.azxy10Enabled,
                        ) { onPreferencesChange(preferences.copy(azxy10Enabled = it)) }
                        AlertToggleRow(
                            "天机云端 AI",
                            "服务器 AI 模型连续三期不中",
                            preferences.aiEnabled,
                            Icons.Rounded.Cloud,
                        ) { onPreferencesChange(preferences.copy(aiEnabled = it)) }
                        AlertToggleRow(
                            "天机云端本地",
                            "服务器本地模型连续三期不中",
                            preferences.nativeEnabled,
                            Icons.Rounded.Memory,
                        ) { onPreferencesChange(preferences.copy(nativeEnabled = it)) }
                        AlertToggleRow(
                            "升级预警",
                            "连续 4、5 期仍不中时继续提醒",
                            preferences.escalationEnabled,
                        ) { onPreferencesChange(preferences.copy(escalationEnabled = it)) }
                    }
                }
            }

            item {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Column(Modifier.weight(1f)) {
                        Text(
                            "历史预警",
                            color = colors.text,
                            fontSize = 15.sp,
                            fontWeight = FontWeight.ExtraBold,
                        )
                        Text(
                            "${alerts.count { !it.isRead }} 条未读 · 共 ${alerts.size} 条",
                            color = colors.textDim,
                            fontSize = 11.sp,
                        )
                    }
                    if (alerts.any { !it.isRead }) {
                        TextButton(onClick = onReadAll) {
                            Text("全部已读", color = colors.accent)
                        }
                    }
                }
            }

            if (ordered.isEmpty()) {
                item {
                    SurfaceCard(radius = 20.dp) {
                        Column(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(vertical = 32.dp),
                            horizontalAlignment = Alignment.CenterHorizontally,
                        ) {
                            Icon(
                                Icons.Rounded.CheckCircle,
                                null,
                                tint = colors.green,
                                modifier = Modifier.size(34.dp),
                            )
                            Text(
                                "暂无连续三期不中预警",
                                color = colors.text,
                                fontSize = 13.sp,
                                fontWeight = FontWeight.Bold,
                                modifier = Modifier.padding(top = 8.dp),
                            )
                            Text(
                                "后台检查到新预警后会自动出现在这里",
                                color = colors.textDim,
                                fontSize = 11.sp,
                            )
                        }
                    }
                }
            } else {
                items(ordered, key = PushAlert::id) { alert ->
                    AlertHistoryCard(
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
private fun AlertToggleRow(
    title: String,
    detail: String,
    checked: Boolean,
    icon: androidx.compose.ui.graphics.vector.ImageVector? = null,
    onChecked: (Boolean) -> Unit,
) {
    val colors = LocalTianjiColors.current
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .heightIn(min = 58.dp)
            .padding(top = 6.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        if (icon != null) {
            Icon(
                icon,
                null,
                tint = colors.textDim,
                modifier = Modifier.size(20.dp),
            )
            Spacer(Modifier.width(9.dp))
        }
        Column(Modifier.weight(1f)) {
            Text(title, color = colors.text, fontSize = 12.sp, fontWeight = FontWeight.Bold)
            Text(detail, color = colors.textDim, fontSize = 10.sp, lineHeight = 15.sp)
        }
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
private fun StatusDot(status: PushConnectionStatus) {
    val colors = LocalTianjiColors.current
    val tint = when {
        status.instantReady -> colors.green
        status.registered -> colors.accent
        else -> colors.amber
    }
    Box(
        Modifier
            .size(11.dp)
            .shadow(
                elevation = 3.dp,
                shape = CircleShape,
                ambientColor = tint.copy(alpha = 0.28f),
                spotColor = tint.copy(alpha = 0.28f),
            )
            .clip(CircleShape)
            .background(tint),
    )
}

@Composable
private fun AlertHistoryCard(
    alert: PushAlert,
    focused: Boolean,
    onRead: () -> Unit,
) {
    val colors = LocalTianjiColors.current
    val accent = if (alert.streak > alert.threshold) colors.red else colors.amber
    val shape = RoundedCornerShape(19.dp)
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clip(shape)
            .background(
                if (!alert.isRead || focused) accent.copy(alpha = 0.10f)
                else colors.surfaceStrong,
            )
            .border(
                if (focused) 1.5.dp else 1.dp,
                if (focused || !alert.isRead) accent.copy(alpha = 0.45f) else colors.line,
                shape,
            )
            .clickable {
                if (!alert.isRead) onRead()
            }
            .padding(14.dp),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Icon(
                Icons.Rounded.WarningAmber,
                null,
                tint = accent,
                modifier = Modifier.size(21.dp),
            )
            Spacer(Modifier.width(8.dp))
            Text(
                alert.title,
                color = accent,
                fontSize = 12.sp,
                fontWeight = FontWeight.ExtraBold,
                modifier = Modifier.weight(1f),
            )
            if (!alert.isRead) {
                Box(
                    Modifier
                        .size(7.dp)
                        .clip(CircleShape)
                        .background(accent),
                )
            }
        }
        Text(
            "${alert.lotteryName} · ${alert.sourceName}",
            color = colors.text,
            fontSize = 13.sp,
            fontWeight = FontWeight.Bold,
            modifier = Modifier.padding(top = 7.dp),
        )
        Text(
            alert.model,
            color = colors.textSoft,
            fontSize = 11.sp,
            maxLines = 2,
            overflow = TextOverflow.Ellipsis,
        )
        Text(
            "连续 ${alert.streak} 期 Top 6 未命中",
            color = colors.text,
            fontSize = 11.sp,
            modifier = Modifier.padding(top = 6.dp),
        )
        if (alert.recentPeriods.isNotEmpty()) {
            Text(
                "最近期号：${alert.recentPeriods.joinToString("、")}",
                color = colors.textDim,
                fontSize = 10.sp,
            )
        }
        Text(
            formatAlertTime(alert.createdAtEpochMs),
            color = colors.textDim,
            fontSize = 10.sp,
            modifier = Modifier.padding(top = 6.dp),
        )
    }
}

private fun formatAlertTime(epochMs: Long): String =
    SimpleDateFormat("MM-dd HH:mm", Locale.getDefault()).format(Date(epochMs))
