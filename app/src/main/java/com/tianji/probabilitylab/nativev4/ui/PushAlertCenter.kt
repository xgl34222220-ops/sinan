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
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
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
    Column(
        modifier = modifier
            .fillMaxSize()
            .background(colors.page),
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .background(colors.header)
                .border(0.5.dp, colors.line)
                .padding(horizontal = 8.dp, vertical = 8.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            IconButton(onClick = onClose) {
                Icon(
                    Icons.AutoMirrored.Rounded.ArrowBack,
                    contentDescription = "返回",
                    tint = colors.textSoft,
                )
            }
            Column(Modifier.weight(1f)) {
                Text(
                    "预警中心",
                    color = colors.text,
                    fontSize = 18.sp,
                    fontWeight = FontWeight.ExtraBold,
                )
                Text(
                    status.detail,
                    color = colors.textDim,
                    fontSize = 10.sp,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
            }
            IconButton(onClick = onRefresh) {
                Icon(Icons.Rounded.Refresh, "刷新预警", tint = colors.accent)
            }
        }

        LazyColumn(
            modifier = Modifier.fillMaxSize(),
            contentPadding = PaddingValues(12.dp, 12.dp, 12.dp, 28.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            item {
                SurfaceCard(radius = 20.dp) {
                    Column(
                        Modifier.padding(horizontal = 14.dp, vertical = 13.dp),
                        verticalArrangement = Arrangement.spacedBy(8.dp),
                    ) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Box(
                                Modifier
                                    .size(40.dp)
                                    .clip(RoundedCornerShape(13.dp))
                                    .background(colors.accentSoft),
                                contentAlignment = Alignment.Center,
                            ) {
                                Icon(
                                    Icons.Rounded.NotificationsActive,
                                    null,
                                    tint = colors.accent,
                                )
                            }
                            Spacer(Modifier.width(11.dp))
                            Column(Modifier.weight(1f)) {
                                Text(
                                    "预测预警推送",
                                    color = colors.text,
                                    fontSize = 14.sp,
                                    fontWeight = FontWeight.Bold,
                                )
                                Text(
                                    when {
                                        status.firebaseConfigured && status.fcmTokenPresent ->
                                            "FCM 即时推送已连接，15 分钟后台检查兜底"
                                        status.firebaseConfigured ->
                                            "Firebase 已配置，等待设备令牌"
                                        else ->
                                            "尚未配置 FCM，当前使用 15 分钟后台检查"
                                    },
                                    color = colors.textDim,
                                    fontSize = 10.sp,
                                )
                            }
                            StatusDot(ok = status.registered)
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
                SurfaceCard(radius = 20.dp) {
                    Column(Modifier.padding(14.dp)) {
                        Text(
                            "接收范围",
                            color = colors.text,
                            fontSize = 13.sp,
                            fontWeight = FontWeight.Bold,
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
                            fontSize = 14.sp,
                            fontWeight = FontWeight.Bold,
                        )
                        Text(
                            "${alerts.count { !it.isRead }} 条未读 · 共 ${alerts.size} 条",
                            color = colors.textDim,
                            fontSize = 10.sp,
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
                                "云端检测到新预警后会自动出现在这里",
                                color = colors.textDim,
                                fontSize = 10.sp,
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
            .padding(top = 9.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        if (icon != null) {
            Icon(
                icon,
                null,
                tint = colors.textDim,
                modifier = Modifier.size(19.dp),
            )
            Spacer(Modifier.width(9.dp))
        }
        Column(Modifier.weight(1f)) {
            Text(title, color = colors.text, fontSize = 12.sp, fontWeight = FontWeight.Bold)
            Text(detail, color = colors.textDim, fontSize = 9.sp)
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
private fun StatusDot(ok: Boolean) {
    val colors = LocalTianjiColors.current
    Box(
        Modifier
            .size(10.dp)
            .clip(CircleShape)
            .background(if (ok) colors.green else colors.amber),
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
            fontSize = 9.sp,
            modifier = Modifier.padding(top = 6.dp),
        )
    }
}

private fun formatAlertTime(epochMs: Long): String =
    SimpleDateFormat("MM-dd HH:mm", Locale.getDefault()).format(Date(epochMs))
