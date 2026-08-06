package com.tianji.probabilitylab.nativev4.ui

import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.spring
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.AutoAwesome
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
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
import androidx.compose.ui.hapticfeedback.HapticFeedbackType
import androidx.compose.ui.platform.LocalHapticFeedback
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.tianji.probabilitylab.nativev4.ui.theme.LocalTianjiColors

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
            .heightIn(min = 78.dp)
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
        StandardNavItem(
            item = MainDestination.HOME,
            active = selected == MainDestination.HOME,
            onClick = { onSelected(MainDestination.HOME) },
            modifier = Modifier.weight(1f),
        )
        StandardNavItem(
            item = MainDestination.STRATEGY,
            active = selected == MainDestination.STRATEGY,
            onClick = { onSelected(MainDestination.STRATEGY) },
            modifier = Modifier.weight(1f),
        )
        ChatNavItem(
            onClick = onChat,
            isRunning = isAiRunning,
            modifier = Modifier.weight(1f),
        )
        StandardNavItem(
            item = MainDestination.ARCHIVE,
            active = selected == MainDestination.ARCHIVE,
            onClick = { onSelected(MainDestination.ARCHIVE) },
            modifier = Modifier.weight(1f),
        )
        StandardNavItem(
            item = MainDestination.SETTINGS,
            active = selected == MainDestination.SETTINGS,
            onClick = { onSelected(MainDestination.SETTINGS) },
            modifier = Modifier.weight(1f),
        )
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
    val haptics = LocalHapticFeedback.current
    Column(
        modifier = modifier
            .heightIn(min = 64.dp)
            .scale(scale)
            .clip(RoundedCornerShape(17.dp))
            .background(background)
            .border(
                1.dp,
                if (active) colors.accent.copy(alpha = 0.25f) else Color.Transparent,
                RoundedCornerShape(17.dp),
            )
            .clickable {
                haptics.performHapticFeedback(HapticFeedbackType.TextHandleMove)
                onClick()
            },
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
            fontSize = 11.sp,
            lineHeight = 15.sp,
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
    val haptics = LocalHapticFeedback.current
    Column(
        modifier = modifier
            .heightIn(min = 64.dp)
            .clip(RoundedCornerShape(17.dp))
            .padding(vertical = 1.dp)
            .clickable {
                haptics.performHapticFeedback(HapticFeedbackType.TextHandleMove)
                onClick()
            },
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        Box(
            modifier = Modifier.size(44.dp),
            contentAlignment = Alignment.Center,
        ) {
            if (isRunning) {
                CircularProgressIndicator(
                    modifier = Modifier.size(44.dp),
                    color = colors.accent,
                    strokeWidth = 2.dp,
                )
            }
            Box(
                modifier = Modifier
                    .size(38.dp)
                    .shadow(
                        elevation = if (colors.isOled) 0.dp else 6.dp,
                        shape = CircleShape,
                        ambientColor = colors.accent.copy(alpha = 0.28f),
                        spotColor = colors.accent.copy(alpha = 0.28f),
                    )
                    .clip(CircleShape)
                    .background(Brush.linearGradient(listOf(colors.accent, colors.violet)))
                    .border(1.dp, Color.White.copy(alpha = 0.18f), CircleShape),
                contentAlignment = Alignment.Center,
            ) {
                Icon(
                    Icons.Rounded.AutoAwesome,
                    contentDescription = if (isRunning) "查看正在运行的 AI 任务" else "打开 AI 对话",
                    tint = Color.White,
                    modifier = Modifier.size(19.dp),
                )
            }
        }
        Text(
            if (isRunning) "运行中" else "AI",
            color = colors.accent,
            fontSize = 11.sp,
            lineHeight = 15.sp,
            fontWeight = FontWeight.Bold,
            maxLines = 1,
        )
    }
}
