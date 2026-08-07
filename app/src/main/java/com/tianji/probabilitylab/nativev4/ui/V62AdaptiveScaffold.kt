package com.tianji.probabilitylab.nativev4.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxScope
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawing
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.AutoAwesome
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.material3.adaptive.currentWindowAdaptiveInfo
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
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
internal fun V62AdaptiveScaffold(
    selected: MainDestination,
    onSelected: (MainDestination) -> Unit,
    onChat: () -> Unit,
    isAiRunning: Boolean,
    compactBottomBar: @Composable () -> Unit,
    content: @Composable BoxScope.() -> Unit,
) {
    val adaptiveInfo = currentWindowAdaptiveInfo(supportLargeAndXLargeWidth = true)
    val useRail = adaptiveInfo.windowSizeClass.isWidthAtLeastBreakpoint(600)
    val colors = LocalTianjiColors.current

    if (!useRail) {
        TianjiRootScaffold(bottomBar = compactBottomBar, content = content)
        return
    }

    Row(
        modifier = Modifier
            .fillMaxSize()
            .background(
                Brush.verticalGradient(listOf(colors.page, colors.pageSoft, colors.page)),
            )
            .windowInsetsPadding(WindowInsets.safeDrawing),
    ) {
        V62NavigationRail(
            selected = selected,
            onSelected = onSelected,
            onChat = onChat,
            isAiRunning = isAiRunning,
        )
        Box(
            modifier = Modifier
                .weight(1f)
                .fillMaxHeight(),
            content = content,
        )
    }
}

@Composable
private fun V62NavigationRail(
    selected: MainDestination,
    onSelected: (MainDestination) -> Unit,
    onChat: () -> Unit,
    isAiRunning: Boolean,
) {
    val colors = LocalTianjiColors.current
    Column(
        modifier = Modifier
            .width(92.dp)
            .fillMaxHeight()
            .padding(start = 10.dp, top = 10.dp, bottom = 10.dp)
            .shadow(
                elevation = if (colors.isOled) 0.dp else 10.dp,
                shape = RoundedCornerShape(27.dp),
                ambientColor = Color.Black.copy(alpha = 0.14f),
                spotColor = Color.Black.copy(alpha = 0.14f),
            )
            .clip(RoundedCornerShape(27.dp))
            .background(colors.navSurface.copy(alpha = 0.975f))
            .border(1.dp, colors.lineStrong, RoundedCornerShape(27.dp))
            .padding(horizontal = 7.dp, vertical = 12.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        MainDestination.entries.take(2).forEach { destination ->
            RailItem(destination, selected == destination) { onSelected(destination) }
        }
        Spacer(Modifier.weight(1f))
        RailAiItem(isAiRunning = isAiRunning, onClick = onChat)
        Spacer(Modifier.weight(1f))
        MainDestination.entries.drop(2).forEach { destination ->
            RailItem(destination, selected == destination) { onSelected(destination) }
        }
    }
}

@Composable
private fun RailItem(
    destination: MainDestination,
    active: Boolean,
    onClick: () -> Unit,
) {
    val colors = LocalTianjiColors.current
    val haptics = LocalHapticFeedback.current
    val interaction = remember { MutableInteractionSource() }
    Column(
        modifier = Modifier
            .size(width = 70.dp, height = 62.dp)
            .clip(RoundedCornerShape(19.dp))
            .background(if (active) colors.accentSoft else Color.Transparent)
            .semantics { role = Role.Tab }
            .clickable(
                interactionSource = interaction,
                indication = null,
            ) {
                haptics.performHapticFeedback(HapticFeedbackType.TextHandleMove)
                onClick()
            },
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        Icon(
            destination.icon,
            contentDescription = destination.label,
            tint = if (active) colors.accent else colors.textDim,
            modifier = Modifier.size(22.dp),
        )
        Text(
            destination.label,
            color = if (active) colors.accent else colors.textDim,
            fontSize = 11.sp,
            fontWeight = if (active) FontWeight.ExtraBold else FontWeight.Medium,
        )
    }
}

@Composable
private fun RailAiItem(isAiRunning: Boolean, onClick: () -> Unit) {
    val colors = LocalTianjiColors.current
    val haptics = LocalHapticFeedback.current
    val interaction = remember { MutableInteractionSource() }
    Column(
        modifier = Modifier
            .size(width = 70.dp, height = 68.dp)
            .clip(RoundedCornerShape(20.dp))
            .semantics { role = Role.Button }
            .clickable(
                interactionSource = interaction,
                indication = null,
            ) {
                haptics.performHapticFeedback(HapticFeedbackType.TextHandleMove)
                onClick()
            },
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        Box(Modifier.size(43.dp), contentAlignment = Alignment.Center) {
            if (isAiRunning) {
                CircularProgressIndicator(
                    modifier = Modifier.size(43.dp),
                    color = colors.accent,
                    strokeWidth = 2.dp,
                )
            }
            Box(
                modifier = Modifier
                    .size(37.dp)
                    .clip(CircleShape)
                    .background(Brush.linearGradient(listOf(colors.accent, colors.violet))),
                contentAlignment = Alignment.Center,
            ) {
                Icon(
                    Icons.Rounded.AutoAwesome,
                    contentDescription = "AI 对话",
                    tint = Color.White,
                    modifier = Modifier.size(19.dp),
                )
            }
        }
        Text(
            if (isAiRunning) "运行中" else "AI",
            color = colors.accent,
            fontSize = 11.sp,
            fontWeight = FontWeight.ExtraBold,
        )
    }
}
