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
) {
    val colors = LocalTianjiColors.current
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .height(54.dp)
            .background(colors.header)
            .border(0.5.dp, colors.line)
            .padding(horizontal = 11.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        if (canGoBack && onBack != null) {
            IconButton(onClick = onBack, modifier = Modifier.size(38.dp)) {
                Icon(
                    Icons.AutoMirrored.Rounded.ArrowBack,
                    contentDescription = "返回",
                    tint = colors.textSoft,
                    modifier = Modifier.size(21.dp),
                )
            }
            Spacer(Modifier.width(3.dp))
        } else {
            Image(
                painter = painterResource(R.drawable.tianji_original_icon),
                contentDescription = "天机",
                contentScale = ContentScale.Crop,
                modifier = Modifier
                    .size(35.dp)
                    .clip(RoundedCornerShape(12.dp))
                    .border(1.dp, colors.accent.copy(alpha = 0.22f), RoundedCornerShape(12.dp)),
            )
            Spacer(Modifier.width(9.dp))
        }

        Column(Modifier.weight(1f)) {
            Text(
                destination.title,
                color = colors.text,
                fontSize = 17.sp,
                lineHeight = 20.sp,
                fontWeight = FontWeight.ExtraBold,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
            Text(
                destination.subtitle,
                color = colors.textDim,
                fontSize = 10.sp,
                lineHeight = 13.sp,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
        }

        Box(
            modifier = Modifier
                .size(36.dp)
                .clip(RoundedCornerShape(12.dp))
                .background(colors.glass)
                .border(1.dp, colors.lineStrong, RoundedCornerShape(12.dp))
                .clickable(enabled = !isRefreshing, onClick = onRefresh),
            contentAlignment = Alignment.Center,
        ) {
            if (isRefreshing) {
                CircularProgressIndicator(
                    modifier = Modifier.size(17.dp),
                    color = colors.accent,
                    strokeWidth = 2.dp,
                )
            } else {
                Icon(
                    Icons.Rounded.Refresh,
                    contentDescription = "刷新",
                    tint = colors.textSoft,
                    modifier = Modifier.size(19.dp),
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
    modifier: Modifier = Modifier,
) {
    val colors = LocalTianjiColors.current
    Row(
        modifier = modifier
            .fillMaxWidth()
            .height(60.dp)
            .shadow(
                elevation = if (colors.isOled) 0.dp else 7.dp,
                shape = RoundedCornerShape(21.dp),
                ambientColor = Color.Black.copy(alpha = 0.16f),
                spotColor = Color.Black.copy(alpha = 0.16f),
            )
            .clip(RoundedCornerShape(21.dp))
            .background(colors.navSurface.copy(alpha = 0.98f))
            .border(1.dp, colors.lineStrong, RoundedCornerShape(21.dp))
            .padding(horizontal = 4.dp, vertical = 4.dp),
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
                ChatNavItem(onClick = onChat, modifier = Modifier.weight(1f))
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
        if (active) colors.accent.copy(alpha = 0.10f) else Color.Transparent,
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
            .fillMaxHeight()
            .scale(scale)
            .clip(RoundedCornerShape(15.dp))
            .background(background)
            .border(
                1.dp,
                if (active) colors.accent.copy(alpha = 0.12f) else Color.Transparent,
                RoundedCornerShape(15.dp),
            )
            .clickable(
                interactionSource = interaction,
                indication = null,
                onClick = onClick,
            ),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        Icon(
            item.icon,
            contentDescription = item.label,
            tint = if (active) colors.accent else colors.textDim,
            modifier = Modifier.size(if (active) 20.dp else 18.dp),
        )
        Spacer(Modifier.height(2.dp))
        Text(
            item.label,
            color = if (active) colors.accent else colors.textDim,
            fontSize = 9.sp,
            fontWeight = if (active) FontWeight.Bold else FontWeight.Medium,
        )
    }
}

@Composable
private fun ChatNavItem(onClick: () -> Unit, modifier: Modifier = Modifier) {
    val colors = LocalTianjiColors.current
    val interaction = remember { MutableInteractionSource() }
    Column(
        modifier = modifier
            .fillMaxHeight()
            .clip(RoundedCornerShape(16.dp))
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
                .size(34.dp)
                .shadow(
                    elevation = if (colors.isOled) 0.dp else 5.dp,
                    shape = CircleShape,
                    ambientColor = colors.accent.copy(alpha = 0.22f),
                    spotColor = colors.accent.copy(alpha = 0.22f),
                )
                .clip(CircleShape)
                .background(
                    Brush.linearGradient(
                        listOf(colors.accent, colors.violet),
                    ),
                ),
            contentAlignment = Alignment.Center,
        ) {
            Icon(
                Icons.Rounded.AutoAwesome,
                contentDescription = "打开 AI 对话",
                tint = Color.White,
                modifier = Modifier.size(18.dp),
            )
        }
        Text(
            "AI",
            color = colors.accent,
            fontSize = 8.sp,
            fontWeight = FontWeight.Bold,
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
            .height(44.dp)
            .clip(RoundedCornerShape(16.dp))
            .background(colors.glass)
            .border(1.dp, colors.line, RoundedCornerShape(16.dp))
            .padding(4.dp),
        horizontalArrangement = Arrangement.spacedBy(5.dp),
    ) {
        LotteryType.entries.forEach { lottery ->
            val active = selected == lottery
            val tint = if (lottery == LotteryType.XYFT) colors.amber else colors.violet
            Row(
                modifier = Modifier
                    .weight(1f)
                    .fillMaxHeight()
                    .clip(RoundedCornerShape(12.dp))
                    .background(if (active) tint.copy(alpha = 0.12f) else Color.Transparent)
                    .border(
                        1.dp,
                        if (active) tint.copy(alpha = 0.22f) else Color.Transparent,
                        RoundedCornerShape(12.dp),
                    )
                    .clickable { onSelect(lottery) }
                    .padding(horizontal = 9.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.Center,
            ) {
                Box(
                    Modifier
                        .size(6.dp)
                        .clip(CircleShape)
                        .background(if (active) tint else colors.textDim),
                )
                Spacer(Modifier.width(6.dp))
                Text(
                    lottery.displayName,
                    color = if (active) colors.text else colors.textSoft,
                    fontSize = 11.sp,
                    fontWeight = if (active) FontWeight.Bold else FontWeight.Medium,
                    maxLines = 1,
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
            .height(43.dp)
            .clip(RoundedCornerShape(15.dp))
            .background(colors.surfaceStrong)
            .border(1.dp, colors.line, RoundedCornerShape(15.dp))
            .padding(4.dp),
        horizontalArrangement = Arrangement.spacedBy(4.dp),
    ) {
        items.forEachIndexed { index, item ->
            val active = index == selectedIndex
            Box(
                modifier = Modifier
                    .weight(1f)
                    .fillMaxHeight()
                    .clip(RoundedCornerShape(11.dp))
                    .background(if (active) colors.accentSoft else Color.Transparent)
                    .clickable { onSelected(index) },
                contentAlignment = Alignment.Center,
            ) {
                Text(
                    item,
                    color = if (active) colors.accent else colors.textDim,
                    fontSize = 11.sp,
                    fontWeight = if (active) FontWeight.Bold else FontWeight.Medium,
                )
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
            .clip(RoundedCornerShape(17.dp))
            .background(colors.surfaceStrong)
            .border(1.dp, colors.line, RoundedCornerShape(17.dp))
            .clickable(onClick = onClick)
            .padding(horizontal = 14.dp, vertical = 13.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Box(
            modifier = Modifier
                .size(39.dp)
                .clip(RoundedCornerShape(13.dp))
                .background(colors.accentSoft),
            contentAlignment = Alignment.Center,
        ) {
            Icon(icon, null, tint = colors.accent, modifier = Modifier.size(20.dp))
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
