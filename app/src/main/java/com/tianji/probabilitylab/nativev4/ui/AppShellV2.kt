package com.tianji.probabilitylab.nativev4.ui

import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.spring
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.rounded.ArrowBack
import androidx.compose.material.icons.rounded.AutoAwesome
import androidx.compose.material.icons.rounded.AutoGraph
import androidx.compose.material.icons.rounded.Home
import androidx.compose.material.icons.rounded.History
import androidx.compose.material.icons.rounded.KeyboardArrowRight
import androidx.compose.material.icons.rounded.Notifications
import androidx.compose.material.icons.rounded.Refresh
import androidx.compose.material.icons.rounded.Settings
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.scale
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.tianji.probabilitylab.nativev4.R
import com.tianji.probabilitylab.nativev4.model.LotteryType
import com.tianji.probabilitylab.nativev4.ui.theme.LocalTianjiColors

enum class MainDestination(
    val label: String,
    val title: String,
    val subtitle: String,
    val icon: ImageVector,
) {
    HOME("预测", "天机预测", "开奖、冻结结果与 AI 共识", Icons.Rounded.Home),
    STRATEGY("策略", "策略与验证", "前向证据、模型表现与风险闸门", Icons.Rounded.AutoGraph),
    CHAT("AI", "天机 AI", "基于当前真实历史继续对话", Icons.Rounded.AutoAwesome),
    ARCHIVE("档案", "预测档案", "开奖前冻结，开奖后按目标期结算", Icons.Rounded.History),
    SETTINGS("设置", "设置", "模型、数据、外观与应用信息", Icons.Rounded.Settings),
}

@Composable
fun CompactAppHeader(
    destination: MainDestination,
    isRefreshing: Boolean,
    onRefresh: () -> Unit,
    canGoBack: Boolean = false,
    onBack: (() -> Unit)? = null,
    unreadAlerts: Int = 0,
    onAlerts: () -> Unit = {},
) {
    val colors = LocalTianjiColors.current
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .height(66.dp)
            .background(
                Brush.verticalGradient(
                    listOf(
                        colors.header,
                        colors.page.copy(alpha = 0.96f),
                    ),
                ),
            )
            .border(0.5.dp, colors.line)
            .padding(horizontal = 12.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        if (canGoBack && onBack != null) {
            IconButton(onClick = onBack, modifier = Modifier.size(40.dp)) {
                Icon(
                    Icons.AutoMirrored.Rounded.ArrowBack,
                    contentDescription = "返回",
                    tint = colors.textSoft,
                    modifier = Modifier.size(22.dp),
                )
            }
            Spacer(Modifier.width(3.dp))
        } else {
            Image(
                painter = painterResource(R.drawable.tianji_original_icon),
                contentDescription = "天机",
                contentScale = ContentScale.Crop,
                modifier = Modifier
                    .size(39.dp)
                    .shadow(
                        elevation = if (colors.isOled) 0.dp else 4.dp,
                        shape = RoundedCornerShape(14.dp),
                        ambientColor = colors.accent.copy(alpha = 0.18f),
                        spotColor = colors.accent.copy(alpha = 0.18f),
                    )
                    .clip(RoundedCornerShape(14.dp))
                    .border(1.dp, colors.accent.copy(alpha = 0.30f), RoundedCornerShape(14.dp)),
            )
            Spacer(Modifier.width(10.dp))
        }

        Column(Modifier.weight(1f)) {
            Text(
                destination.title,
                color = colors.text,
                fontSize = 18.sp,
                lineHeight = 21.sp,
                fontWeight = FontWeight.ExtraBold,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
            Spacer(Modifier.height(1.dp))
            Text(
                destination.subtitle,
                color = colors.textDim,
                fontSize = 10.5.sp,
                lineHeight = 14.sp,
                fontWeight = FontWeight.Medium,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
        }

        Box(
            modifier = Modifier
                .size(40.dp)
                .shadow(
                    elevation = if (colors.isOled) 0.dp else 2.dp,
                    shape = RoundedCornerShape(14.dp),
                    ambientColor = Color.Black.copy(alpha = 0.12f),
                    spotColor = Color.Black.copy(alpha = 0.12f),
                )
                .clip(RoundedCornerShape(14.dp))
                .background(
                    Brush.linearGradient(
                        listOf(colors.glassStrong, colors.glass),
                    ),
                )
                .border(1.dp, colors.lineStrong, RoundedCornerShape(14.dp))
                .clickable(onClick = onAlerts),
            contentAlignment = Alignment.Center,
        ) {
            Icon(
                Icons.Rounded.Notifications,
                contentDescription = "打开预警中心",
                tint = if (unreadAlerts > 0) colors.amber else colors.textSoft,
                modifier = Modifier.size(20.dp),
            )
            if (unreadAlerts > 0) {
                Text(
                    unreadAlerts.coerceAtMost(99).toString(),
                    color = Color.White,
                    fontSize = 7.sp,
                    fontWeight = FontWeight.ExtraBold,
                    modifier = Modifier
                        .align(Alignment.TopEnd)
                        .clip(CircleShape)
                        .background(colors.red)
                        .padding(horizontal = 3.dp, vertical = 1.dp),
                )
            }
        }
        Spacer(Modifier.width(7.dp))

        Box(
            modifier = Modifier
                .size(40.dp)
                .shadow(
                    elevation = if (colors.isOled) 0.dp else 2.dp,
                    shape = RoundedCornerShape(14.dp),
                    ambientColor = Color.Black.copy(alpha = 0.12f),
                    spotColor = Color.Black.copy(alpha = 0.12f),
                )
                .clip(RoundedCornerShape(14.dp))
                .background(
                    Brush.linearGradient(
                        listOf(colors.glassStrong, colors.glass),
                    ),
                )
                .border(1.dp, colors.lineStrong, RoundedCornerShape(14.dp))
                .clickable(enabled = !isRefreshing, onClick = onRefresh),
            contentAlignment = Alignment.Center,
        ) {
            if (isRefreshing) {
                CircularProgressIndicator(
                    modifier = Modifier.size(18.dp),
                    color = colors.accent,
                    strokeWidth = 2.dp,
                )
            } else {
                Icon(
                    Icons.Rounded.Refresh,
                    contentDescription = "刷新",
                    tint = colors.textSoft,
                    modifier = Modifier.size(20.dp),
                )
            }
        }
    }
}

@Composable
fun MainBottomBar(
    selected: MainDestination,
    onSelected: (MainDestination) -> Unit,
    onChat: () -> Unit,
    isAiRunning: Boolean = false,
    modifier: Modifier = Modifier,
) {
    val colors = LocalTianjiColors.current
    Row(
        modifier = modifier
            .fillMaxWidth()
            .heightIn(min = 76.dp)
            .shadow(
                elevation = if (colors.isOled) 0.dp else 10.dp,
                shape = RoundedCornerShape(24.dp),
                ambientColor = Color.Black.copy(alpha = 0.20f),
                spotColor = Color.Black.copy(alpha = 0.20f),
            )
            .clip(RoundedCornerShape(24.dp))
            .background(
                Brush.verticalGradient(
                    listOf(
                        colors.navSurface.copy(alpha = 0.99f),
                        colors.surfaceStrong.copy(alpha = 0.99f),
                    ),
                ),
            )
            .border(1.dp, colors.lineStrong, RoundedCornerShape(24.dp))
            .padding(horizontal = 5.dp, vertical = 6.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        listOf(
            MainDestination.HOME,
            MainDestination.STRATEGY,
            MainDestination.CHAT,
            MainDestination.ARCHIVE,
            MainDestination.SETTINGS,
        ).forEach { item ->
            if (item == MainDestination.CHAT) {
                ChatNavItem(
                    onClick = onChat,
                    isRunning = isAiRunning,
                    modifier = Modifier.weight(1f),
                )
            } else {
                StandardNavItem(
                    item = item,
                    active = selected == item,
                    onClick = { onSelected(item) },
                    modifier = Modifier.weight(1f),
                )
            }
        }
    }
}

@Composable
private fun StandardNavItem(
    item: MainDestination,
    active: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val colors = LocalTianjiColors.current
    val background by animateColorAsState(
        if (active) colors.accent.copy(alpha = 0.14f) else Color.Transparent,
        label = "main-nav-bg",
    )
    val scale by animateFloatAsState(
        if (active) 1f else 0.98f,
        animationSpec = spring(dampingRatio = 0.84f, stiffness = 520f),
        label = "main-nav-scale",
    )
    val interaction = remember { MutableInteractionSource() }
    Column(
        modifier = modifier
            .heightIn(min = 61.dp)
            .scale(scale)
            .clip(RoundedCornerShape(17.dp))
            .background(background)
            .border(
                1.dp,
                if (active) colors.accent.copy(alpha = 0.25f) else Color.Transparent,
                RoundedCornerShape(17.dp),
            )
            .clickable(
                interactionSource = interaction,
                indication = null,
                onClick = onClick,
            ),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        Box(
            modifier = Modifier
                .width(if (active) 24.dp else 8.dp)
                .height(2.dp)
                .clip(CircleShape)
                .background(if (active) colors.accent else Color.Transparent),
        )
        Spacer(Modifier.height(4.dp))
        Icon(
            item.icon,
            contentDescription = item.label,
            tint = if (active) colors.accent else colors.textDim,
            modifier = Modifier.size(if (active) 21.dp else 19.dp),
        )
        Spacer(Modifier.height(2.dp))
        Text(
            item.label,
            color = if (active) colors.accent else colors.textDim,
            fontSize = 10.sp,
            lineHeight = 14.sp,
            fontWeight = if (active) FontWeight.Bold else FontWeight.Medium,
            maxLines = 1,
        )
    }
}

@Composable
private fun ChatNavItem(
    onClick: () -> Unit,
    isRunning: Boolean,
    modifier: Modifier = Modifier,
) {
    val colors = LocalTianjiColors.current
    val interaction = remember { MutableInteractionSource() }
    Column(
        modifier = modifier
            .heightIn(min = 62.dp)
            .clip(RoundedCornerShape(17.dp))
            .padding(vertical = 1.dp)
            .clickable(
                interactionSource = interaction,
                indication = null,
                onClick = onClick,
            ),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        Box(
            modifier = Modifier.size(42.dp),
            contentAlignment = Alignment.Center,
        ) {
            if (isRunning) {
                CircularProgressIndicator(
                    modifier = Modifier.size(42.dp),
                    color = colors.accent,
                    strokeWidth = 2.dp,
                )
            }
            Box(
                modifier = Modifier
                    .size(36.dp)
                    .shadow(
                        elevation = if (colors.isOled) 0.dp else 6.dp,
                        shape = CircleShape,
                        ambientColor = colors.accent.copy(alpha = 0.28f),
                        spotColor = colors.accent.copy(alpha = 0.28f),
                    )
                    .clip(CircleShape)
                    .background(
                        Brush.linearGradient(
                            listOf(colors.accent, colors.violet),
                        ),
                    )
                    .border(1.dp, Color.White.copy(alpha = 0.18f), CircleShape),
                contentAlignment = Alignment.Center,
            ) {
                Icon(
                    Icons.Rounded.AutoAwesome,
                    contentDescription = if (isRunning) "查看正在运行的 AI 任务" else "打开 AI 对话",
                    tint = Color.White,
                    modifier = Modifier.size(18.dp),
                )
            }
        }
        Text(
            if (isRunning) "运行中" else "AI",
            color = colors.accent,
            fontSize = 10.sp,
            lineHeight = 14.sp,
            fontWeight = FontWeight.Bold,
            maxLines = 1,
        )
    }
}

@Composable
fun CompactLotterySwitcher(
    selected: LotteryType,
    onSelect: (LotteryType) -> Unit,
    modifier: Modifier = Modifier,
) {
    val colors = LocalTianjiColors.current
    Row(
        modifier = modifier
            .fillMaxWidth()
            .height(58.dp)
            .shadow(
                elevation = if (colors.isOled) 0.dp else 3.dp,
                shape = RoundedCornerShape(21.dp),
                ambientColor = Color.Black.copy(alpha = 0.12f),
                spotColor = Color.Black.copy(alpha = 0.12f),
            )
            .clip(RoundedCornerShape(21.dp))
            .background(
                Brush.verticalGradient(
                    listOf(colors.glass, colors.surface.copy(alpha = 0.98f)),
                ),
            )
            .border(1.dp, colors.lineStrong, RoundedCornerShape(21.dp))
            .padding(5.dp),
        horizontalArrangement = Arrangement.spacedBy(6.dp),
    ) {
        LotteryType.entries.forEach { lottery ->
            val active = selected == lottery
            val tint = if (lottery == LotteryType.XYFT) colors.amber else colors.violet
            val itemBackground by animateColorAsState(
                targetValue = if (active) {
                    tint.copy(alpha = 0.18f)
                } else {
                    colors.surfaceStrong.copy(alpha = 0.92f)
                },
                label = "lottery-segment-background",
            )
            val itemBorder by animateColorAsState(
                targetValue = if (active) {
                    tint.copy(alpha = 0.46f)
                } else {
                    colors.lineStrong
                },
                label = "lottery-segment-border",
            )
            val scale by animateFloatAsState(
                targetValue = if (active) 1f else 0.985f,
                animationSpec = spring(dampingRatio = 0.84f, stiffness = 540f),
                label = "lottery-segment-scale",
            )
            val shape = RoundedCornerShape(16.dp)
            val interaction = remember { MutableInteractionSource() }
            Row(
                modifier = Modifier
                    .weight(1f)
                    .fillMaxHeight()
                    .scale(scale)
                    .shadow(
                        elevation = if (active && !colors.isOled) 3.dp else 0.dp,
                        shape = shape,
                        ambientColor = tint.copy(alpha = 0.20f),
                        spotColor = tint.copy(alpha = 0.20f),
                    )
                    .clip(shape)
                    .background(itemBackground)
                    .border(1.dp, itemBorder, shape)
                    .clickable(
                        interactionSource = interaction,
                        indication = null,
                        onClick = { onSelect(lottery) },
                    )
                    .padding(horizontal = 10.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.Center,
            ) {
                Box(
                    modifier = Modifier
                        .size(14.dp)
                        .clip(CircleShape)
                        .background(
                            if (active) tint.copy(alpha = 0.16f) else colors.glassStrong,
                        )
                        .border(
                            1.dp,
                            if (active) tint.copy(alpha = 0.32f) else colors.line,
                            CircleShape,
                        ),
                    contentAlignment = Alignment.Center,
                ) {
                    Box(
                        Modifier
                            .size(6.dp)
                            .clip(CircleShape)
                            .background(if (active) tint else colors.textDim),
                    )
                }
                Spacer(Modifier.width(7.dp))
                Text(
                    lottery.displayName,
                    color = if (active) colors.text else colors.textSoft,
                    fontSize = 12.sp,
                    fontWeight = if (active) FontWeight.ExtraBold else FontWeight.SemiBold,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
            }
        }
    }
}

@Composable
fun SegmentedTabs(
    items: List<String>,
    selectedIndex: Int,
    onSelected: (Int) -> Unit,
    modifier: Modifier = Modifier,
) {
    val colors = LocalTianjiColors.current
    Row(
        modifier = modifier
            .fillMaxWidth()
            .height(55.dp)
            .shadow(
                elevation = if (colors.isOled) 0.dp else 2.dp,
                shape = RoundedCornerShape(20.dp),
                ambientColor = Color.Black.copy(alpha = 0.10f),
                spotColor = Color.Black.copy(alpha = 0.10f),
            )
            .clip(RoundedCornerShape(20.dp))
            .background(
                Brush.verticalGradient(
                    listOf(
                        colors.surfaceStrong,
                        colors.glass.copy(alpha = 0.97f),
                    ),
                ),
            )
            .border(1.dp, colors.lineStrong, RoundedCornerShape(20.dp))
            .padding(5.dp),
        horizontalArrangement = Arrangement.spacedBy(6.dp),
    ) {
        items.forEachIndexed { index, item ->
            val active = index == selectedIndex
            val tabBackground by animateColorAsState(
                targetValue = if (active) {
                    colors.accent.copy(alpha = 0.18f)
                } else {
                    colors.surface.copy(alpha = 0.78f)
                },
                label = "segmented-tab-background",
            )
            val tabBorder by animateColorAsState(
                targetValue = if (active) {
                    colors.accent.copy(alpha = 0.44f)
                } else {
                    colors.lineStrong
                },
                label = "segmented-tab-border",
            )
            val scale by animateFloatAsState(
                targetValue = if (active) 1f else 0.985f,
                animationSpec = spring(dampingRatio = 0.84f, stiffness = 540f),
                label = "segmented-tab-scale",
            )
            val shape = RoundedCornerShape(15.dp)
            val interaction = remember { MutableInteractionSource() }
            Box(
                modifier = Modifier
                    .weight(1f)
                    .fillMaxHeight()
                    .scale(scale)
                    .shadow(
                        elevation = if (active && !colors.isOled) 3.dp else 0.dp,
                        shape = shape,
                        ambientColor = colors.accent.copy(alpha = 0.18f),
                        spotColor = colors.accent.copy(alpha = 0.18f),
                    )
                    .clip(shape)
                    .background(tabBackground)
                    .border(1.dp, tabBorder, shape)
                    .clickable(
                        interactionSource = interaction,
                        indication = null,
                        onClick = { onSelected(index) },
                    ),
                contentAlignment = Alignment.Center,
            ) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Text(
                        item,
                        color = if (active) colors.accent else colors.textSoft,
                        fontSize = 12.sp,
                        fontWeight = if (active) FontWeight.ExtraBold else FontWeight.SemiBold,
                        maxLines = 1,
                    )
                    Spacer(Modifier.height(3.dp))
                    Box(
                        modifier = Modifier
                            .width(if (active) 22.dp else 8.dp)
                            .height(2.dp)
                            .clip(CircleShape)
                            .background(if (active) colors.accent else Color.Transparent),
                    )
                }
            }
        }
    }
}

@Composable
fun SettingsEntry(
    icon: ImageVector,
    title: String,
    detail: String,
    onClick: () -> Unit,
    badge: String? = null,
) {
    val colors = LocalTianjiColors.current
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .shadow(
                elevation = if (colors.isOled) 0.dp else 2.dp,
                shape = RoundedCornerShape(19.dp),
                ambientColor = Color.Black.copy(alpha = 0.10f),
                spotColor = Color.Black.copy(alpha = 0.10f),
            )
            .clip(RoundedCornerShape(19.dp))
            .background(
                Brush.linearGradient(
                    listOf(colors.surfaceStrong, colors.surface),
                ),
            )
            .border(1.dp, colors.lineStrong, RoundedCornerShape(19.dp))
            .clickable(onClick = onClick)
            .padding(horizontal = 14.dp, vertical = 13.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Box(
            modifier = Modifier
                .size(41.dp)
                .clip(RoundedCornerShape(14.dp))
                .background(colors.accentSoft)
                .border(1.dp, colors.accent.copy(alpha = 0.20f), RoundedCornerShape(14.dp)),
            contentAlignment = Alignment.Center,
        ) {
            Icon(icon, null, tint = colors.accent, modifier = Modifier.size(21.dp))
        }
        Spacer(Modifier.width(12.dp))
        Column(Modifier.weight(1f)) {
            Text(
                title,
                color = colors.text,
                fontSize = 14.sp,
                lineHeight = 19.sp,
                fontWeight = FontWeight.Bold,
            )
            Spacer(Modifier.height(2.dp))
            Text(
                detail,
                color = colors.textDim,
                fontSize = 11.sp,
                lineHeight = 16.sp,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis,
            )
        }
        badge?.let {
            Text(
                it,
                color = colors.accent,
                fontSize = 10.sp,
                fontWeight = FontWeight.Bold,
                modifier = Modifier
                    .clip(CircleShape)
                    .background(colors.accentSoft)
                    .border(1.dp, colors.accent.copy(alpha = 0.18f), CircleShape)
                    .padding(horizontal = 8.dp, vertical = 5.dp),
            )
            Spacer(Modifier.width(5.dp))
        }
        Icon(
            Icons.Rounded.KeyboardArrowRight,
            contentDescription = null,
            tint = colors.textDim,
            modifier = Modifier.size(21.dp),
        )
    }
}
