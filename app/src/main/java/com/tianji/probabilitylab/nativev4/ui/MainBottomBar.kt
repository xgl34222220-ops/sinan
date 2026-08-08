package com.tianji.probabilitylab.nativev4.ui

import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.animateDpAsState
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.spring
import androidx.compose.foundation.LocalIndication
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsPressedAsState
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.offset
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
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.hapticfeedback.HapticFeedbackType
import androidx.compose.ui.platform.LocalHapticFeedback
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.role
import androidx.compose.ui.semantics.semantics
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
    val selectedSlot = when (selected) {
        MainDestination.HOME -> 0
        MainDestination.STRATEGY -> 1
        MainDestination.ARCHIVE -> 3
        MainDestination.SETTINGS -> 4
    }

    BoxWithConstraints(
        modifier = modifier
            .fillMaxWidth()
            .heightIn(min = 62.dp)
            .height(76.dp),
    ) {
        val slotWidth = maxWidth / 5
        val indicatorX by animateDpAsState(
            targetValue = slotWidth * selectedSlot,
            animationSpec = spring(dampingRatio = 0.82f, stiffness = 420f),
            label = "main-nav-indicator-x",
        )
        val indicatorTint by animateColorAsState(
            targetValue = colors.accent.copy(alpha = 0.12f),
            label = "main-nav-indicator-color",
        )

        Box(
            modifier = Modifier
                .align(Alignment.BottomCenter)
                .fillMaxWidth()
                .height(64.dp)
                .shadow(
                    elevation = if (colors.isOled) 0.dp else 7.dp,
                    shape = RoundedCornerShape(24.dp),
                    ambientColor = Color.Black.copy(alpha = 0.15f),
                    spotColor = Color.Black.copy(alpha = 0.15f),
                )
                .clip(RoundedCornerShape(24.dp))
                .background(
                    Brush.verticalGradient(
                        listOf(
                            colors.navSurface.copy(alpha = 0.965f),
                            colors.surface.copy(alpha = 0.992f),
                        ),
                    ),
                )
                .border(1.dp, colors.lineStrong, RoundedCornerShape(24.dp)),
        )

        Box(
            modifier = Modifier
                .align(Alignment.BottomStart)
                .offset(x = indicatorX, y = (-6).dp)
                .width(slotWidth)
                .height(50.dp)
                .padding(horizontal = 4.dp)
                .clip(RoundedCornerShape(17.dp))
                .background(indicatorTint)
                .border(
                    width = 1.dp,
                    color = colors.accent.copy(alpha = 0.08f),
                    shape = RoundedCornerShape(17.dp),
                ),
        )

        Row(
            modifier = Modifier
                .align(Alignment.BottomCenter)
                .fillMaxWidth()
                .height(64.dp)
                .padding(horizontal = 5.dp, vertical = 4.dp),
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
}

@Composable
private fun StandardNavItem(
    item: MainDestination,
    active: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val colors = LocalTianjiColors.current
    val haptics = LocalHapticFeedback.current
    val interaction = remember { MutableInteractionSource() }
    val pressed by interaction.collectIsPressedAsState()
    val scale by animateFloatAsState(
        when {
            pressed -> 0.955f
            active -> 1f
            else -> 0.985f
        },
        animationSpec = spring(dampingRatio = 0.86f, stiffness = 520f),
        label = "main-nav-scale",
    )
    val contentTint by animateColorAsState(
        targetValue = if (active) colors.accent else colors.textDim,
        label = "main-nav-content",
    )

    Column(
        modifier = modifier
            .heightIn(min = 52.dp)
            .scale(scale)
            .clip(RoundedCornerShape(18.dp))
            .semantics { role = Role.Tab }
            .clickable(
                interactionSource = interaction,
                indication = LocalIndication.current,
            ) {
                haptics.performHapticFeedback(HapticFeedbackType.TextHandleMove)
                onClick()
            },
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        Icon(
            item.icon,
            contentDescription = item.label,
            tint = contentTint,
            modifier = Modifier.size(if (active) 21.dp else 20.dp),
        )
        Spacer(Modifier.height(2.dp))
        Text(
            item.label,
            color = contentTint,
            fontSize = 11.sp,
            lineHeight = 13.sp,
            fontWeight = if (active) FontWeight.ExtraBold else FontWeight.Medium,
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
    val interaction = remember { MutableInteractionSource() }
    val pressed by interaction.collectIsPressedAsState()
    val pressScale by animateFloatAsState(
        if (pressed) 0.94f else 1f,
        animationSpec = spring(dampingRatio = 0.82f, stiffness = 560f),
        label = "ai-nav-press",
    )
    Column(
        modifier = modifier
            .heightIn(min = 60.dp)
            .scale(pressScale)
            .clip(RoundedCornerShape(20.dp))
            .semantics { role = Role.Button }
            .clickable(
                interactionSource = interaction,
                indication = LocalIndication.current,
            ) {
                haptics.performHapticFeedback(HapticFeedbackType.TextHandleMove)
                onClick()
            },
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        Box(
            modifier = Modifier
                .size(48.dp)
                .offset(y = (-7).dp),
            contentAlignment = Alignment.Center,
        ) {
            if (isRunning) {
                CircularProgressIndicator(
                    modifier = Modifier.size(47.dp),
                    color = colors.accent,
                    trackColor = colors.accent.copy(alpha = 0.12f),
                    strokeWidth = 2.dp,
                )
            }
            Box(
                modifier = Modifier
                    .size(41.dp)
                    .shadow(
                        elevation = if (colors.isOled) 0.dp else 10.dp,
                        shape = CircleShape,
                        ambientColor = colors.accent.copy(alpha = 0.30f),
                        spotColor = colors.violet.copy(alpha = 0.24f),
                    )
                    .clip(CircleShape)
                    .background(
                        Brush.linearGradient(
                            listOf(colors.accent, colors.violet),
                        ),
                    )
                    .border(1.dp, Color.White.copy(alpha = 0.24f), CircleShape),
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
            if (isRunning) "运行中" else "问 AI",
            color = colors.accent,
            fontSize = 10.sp,
            lineHeight = 12.sp,
            fontWeight = FontWeight.ExtraBold,
            maxLines = 1,
            modifier = Modifier.offset(y = (-6).dp),
        )
    }
}