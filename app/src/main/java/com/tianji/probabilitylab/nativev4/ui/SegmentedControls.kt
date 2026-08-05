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
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
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
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.tianji.probabilitylab.nativev4.model.LotteryType
import com.tianji.probabilitylab.nativev4.ui.theme.LocalTianjiColors

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
            .height(60.dp)
            .shadow(
                elevation = if (colors.isOled) 0.dp else 3.dp,
                shape = RoundedCornerShape(21.dp),
                ambientColor = Color.Black.copy(alpha = 0.12f),
                spotColor = Color.Black.copy(alpha = 0.12f),
            )
            .clip(RoundedCornerShape(21.dp))
            .background(Brush.verticalGradient(listOf(colors.glass, colors.surface.copy(alpha = 0.98f))))
            .border(1.dp, colors.lineStrong, RoundedCornerShape(21.dp))
            .padding(5.dp),
        horizontalArrangement = Arrangement.spacedBy(6.dp),
    ) {
        LotteryType.entries.forEach { lottery ->
            val active = selected == lottery
            val tint = if (lottery == LotteryType.XYFT) colors.amber else colors.violet
            val itemBackground by animateColorAsState(
                targetValue = if (active) tint.copy(alpha = 0.18f) else colors.surfaceStrong.copy(alpha = 0.92f),
                label = "lottery-segment-background",
            )
            val itemBorder by animateColorAsState(
                targetValue = if (active) tint.copy(alpha = 0.46f) else colors.lineStrong,
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
                        .background(if (active) tint.copy(alpha = 0.16f) else colors.glassStrong)
                        .border(1.dp, if (active) tint.copy(alpha = 0.32f) else colors.line, CircleShape),
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
            .height(58.dp)
            .shadow(
                elevation = if (colors.isOled) 0.dp else 2.dp,
                shape = RoundedCornerShape(20.dp),
                ambientColor = Color.Black.copy(alpha = 0.10f),
                spotColor = Color.Black.copy(alpha = 0.10f),
            )
            .clip(RoundedCornerShape(20.dp))
            .background(Brush.verticalGradient(listOf(colors.surfaceStrong, colors.glass.copy(alpha = 0.97f))))
            .border(1.dp, colors.lineStrong, RoundedCornerShape(20.dp))
            .padding(5.dp),
        horizontalArrangement = Arrangement.spacedBy(6.dp),
    ) {
        items.forEachIndexed { index, item ->
            val active = index == selectedIndex
            val tabBackground by animateColorAsState(
                targetValue = if (active) colors.accent.copy(alpha = 0.18f) else colors.surface.copy(alpha = 0.78f),
                label = "segmented-tab-background",
            )
            val tabBorder by animateColorAsState(
                targetValue = if (active) colors.accent.copy(alpha = 0.44f) else colors.lineStrong,
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
