package com.tianji.probabilitylab.nativev4.ui

import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.spring
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.AutoGraph
import androidx.compose.material.icons.rounded.BarChart
import androidx.compose.material.icons.rounded.Check
import androidx.compose.material.icons.rounded.Dataset
import androidx.compose.material.icons.rounded.History
import androidx.compose.material.icons.rounded.Psychology
import androidx.compose.material.icons.rounded.Refresh
import androidx.compose.material.icons.rounded.Storage
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
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
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.tianji.probabilitylab.nativev4.R
import com.tianji.probabilitylab.nativev4.model.EvidenceMode
import com.tianji.probabilitylab.nativev4.model.LotteryType
import com.tianji.probabilitylab.nativev4.ui.theme.LocalTianjiColors

enum class NavDestination(val label: String, val icon: ImageVector) {
    FORECAST("预测", Icons.Rounded.Psychology),
    ROLLING("雪球", Icons.Rounded.AutoGraph),
    EVIDENCE("盲测", Icons.Rounded.BarChart),
    ARCHIVE("档案", Icons.Rounded.History),
    DATA("数据", Icons.Rounded.Storage),
}

@Composable
fun AppHeader(isRefreshing: Boolean, onRefresh: () -> Unit) {
    val colors = LocalTianjiColors.current
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .height(62.dp)
            .background(Color(0xF7090A0E))
            .border(width = 0.5.dp, color = colors.line)
            .padding(horizontal = 15.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.SpaceBetween,
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Image(
                painter = painterResource(R.drawable.tianji_original_icon),
                contentDescription = "天机",
                contentScale = ContentScale.Crop,
                modifier = Modifier
                    .size(38.dp)
                    .shadow(12.dp, RoundedCornerShape(14.dp), ambientColor = colors.accent)
                    .clip(RoundedCornerShape(14.dp))
                    .border(1.dp, colors.accent.copy(alpha = 0.72f), RoundedCornerShape(14.dp)),
            )
            Spacer(Modifier.width(10.dp))
            Column {
                Text(
                    text = "天机",
                    color = colors.text,
                    fontSize = 18.sp,
                    fontWeight = FontWeight.ExtraBold,
                    letterSpacing = 1.6.sp,
                )
                Spacer(Modifier.height(5.dp))
                Text(
                    text = "概率研究室 · NATIVE AI LAB",
                    color = colors.textDim,
                    fontSize = 7.sp,
                    fontWeight = FontWeight.SemiBold,
                    letterSpacing = 1.05.sp,
                )
            }
        }
        Box(
            modifier = Modifier
                .size(38.dp)
                .clip(RoundedCornerShape(13.dp))
                .background(Color.White.copy(alpha = 0.035f))
                .border(1.dp, colors.line, RoundedCornerShape(13.dp))
                .clickable(enabled = !isRefreshing, onClick = onRefresh),
            contentAlignment = Alignment.Center,
        ) {
            if (isRefreshing) {
                CircularProgressIndicator(
                    modifier = Modifier.size(18.dp),
                    color = colors.accent,
                    strokeWidth = 1.8.dp,
                )
            } else {
                Icon(Icons.Rounded.Refresh, null, tint = colors.textSoft, modifier = Modifier.size(21.dp))
            }
        }
    }
}

@Composable
fun GameSwitcher(
    selected: LotteryType,
    onSelect: (LotteryType) -> Unit,
    modifier: Modifier = Modifier,
) {
    val colors = LocalTianjiColors.current
    Row(
        modifier = modifier
            .fillMaxWidth()
            .height(70.dp)
            .clip(RoundedCornerShape(18.dp))
            .background(Color(0xBD12141B))
            .border(1.dp, colors.line, RoundedCornerShape(18.dp))
            .padding(5.dp),
        horizontalArrangement = Arrangement.spacedBy(6.dp),
    ) {
        LotteryType.entries.forEach { lottery ->
            val active = selected == lottery
            val accent = if (lottery == LotteryType.XYFT) Color(0xFFFF8A1F) else Color(0xFF7C6CFF)
            Box(
                modifier = Modifier
                    .weight(1f)
                    .fillMaxHeight()
                    .clip(RoundedCornerShape(14.dp))
                    .background(
                        if (active) Brush.linearGradient(
                            listOf(accent.copy(alpha = 0.16f), Color.White.copy(alpha = 0.035f)),
                        ) else Brush.linearGradient(listOf(Color.Transparent, Color.Transparent)),
                    )
                    .border(
                        width = 1.dp,
                        color = if (active) accent.copy(alpha = 0.32f) else Color.Transparent,
                        shape = RoundedCornerShape(14.dp),
                    )
                    .clickable { onSelect(lottery) }
                    .padding(horizontal = 9.dp, vertical = 5.dp),
                contentAlignment = Alignment.TopStart,
            ) {
                Column {
                    Text(
                        text = lottery.displayName,
                        color = colors.text,
                        fontSize = 11.sp,
                        lineHeight = 15.sp,
                        fontWeight = FontWeight.Bold,
                        maxLines = 1,
                    )
                    Spacer(Modifier.height(3.dp))
                    Text(
                        lottery.subtitle,
                        color = colors.textDim,
                        fontSize = 7.5.sp,
                        lineHeight = 11.sp,
                        maxLines = 1,
                    )
                }
                if (active) {
                    Box(
                        Modifier
                            .align(Alignment.BottomCenter)
                            .fillMaxWidth()
                            .height(2.dp)
                            .clip(CircleShape)
                            .background(accent),
                    )
                }
            }
        }
    }
}

@Composable
fun SurfaceCard(
    modifier: Modifier = Modifier,
    radius: Dp = 23.dp,
    content: @Composable ColumnScope.() -> Unit,
) {
    val colors = LocalTianjiColors.current
    Column(
        modifier = modifier
            .fillMaxWidth()
            .shadow(
                elevation = 18.dp,
                shape = RoundedCornerShape(radius),
                ambientColor = Color.Black.copy(alpha = 0.34f),
                spotColor = Color.Black.copy(alpha = 0.34f),
            )
            .clip(RoundedCornerShape(radius))
            .background(colors.surface)
            .background(
                Brush.linearGradient(
                    listOf(Color.White.copy(alpha = 0.032f), Color.Transparent),
                ),
            )
            .border(1.dp, colors.line, RoundedCornerShape(radius)),
        content = content,
    )
}

@Composable
fun SectionTitle(
    eyebrow: String,
    title: String,
    icon: ImageVector? = null,
    detail: String? = null,
    trailing: (@Composable () -> Unit)? = null,
) {
    val colors = LocalTianjiColors.current
    Row(verticalAlignment = Alignment.Top, modifier = Modifier.fillMaxWidth()) {
        if (icon != null) {
            Box(
                modifier = Modifier
                    .size(35.dp)
                    .clip(RoundedCornerShape(12.dp))
                    .background(colors.accentSoft)
                    .border(1.dp, colors.accent.copy(alpha = 0.18f), RoundedCornerShape(12.dp)),
                contentAlignment = Alignment.Center,
            ) {
                Icon(icon, null, tint = colors.accent, modifier = Modifier.size(18.dp))
            }
            Spacer(Modifier.width(10.dp))
        }
        Column(modifier = Modifier.weight(1f)) {
            Text(
                eyebrow,
                color = colors.textDim,
                fontSize = 8.sp,
                fontWeight = FontWeight.Bold,
                letterSpacing = 1.35.sp,
            )
            Spacer(Modifier.height(5.dp))
            Text(title, color = colors.text, fontSize = 18.sp, fontWeight = FontWeight.ExtraBold)
            detail?.let {
                Spacer(Modifier.height(5.dp))
                Text(it, color = colors.textDim, fontSize = 8.sp, lineHeight = 12.sp)
            }
        }
        trailing?.invoke()
    }
}

@Composable
fun LotteryBall(number: Int, modifier: Modifier = Modifier, size: Dp = 42.dp, muted: Boolean = false) {
    val pair = ballColors(number)
    val alpha = if (muted) 0.48f else 1f
    Box(
        modifier = modifier
            .size(size)
            .shadow(8.dp, CircleShape, ambientColor = pair.second.copy(alpha = 0.42f))
            .clip(CircleShape)
            .background(
                Brush.radialGradient(
                    colors = listOf(
                        Color.White.copy(alpha = 0.70f * alpha),
                        pair.first.copy(alpha = alpha),
                        pair.second.copy(alpha = alpha),
                    ),
                    radius = size.value * 1.45f,
                ),
            )
            .border(1.dp, Color.White.copy(alpha = 0.25f * alpha), CircleShape),
        contentAlignment = Alignment.Center,
    ) {
        Box(
            Modifier
                .fillMaxSize()
                .padding(3.dp)
                .border(1.dp, Color.White.copy(alpha = 0.12f * alpha), CircleShape),
        )
        Text(
            text = number.toString(),
            color = Color.White.copy(alpha = alpha),
            fontSize = when {
                size >= 42.dp -> 16.sp
                size >= 36.dp -> 14.sp
                else -> 11.sp
            },
            fontWeight = FontWeight.ExtraBold,
        )
    }
}

@Composable
fun EvidencePill(mode: EvidenceMode, text: String? = null) {
    val colors = LocalTianjiColors.current
    val positive = mode == EvidenceMode.CERTIFIED
    val tint = if (positive) colors.green else colors.textSoft
    Row(
        modifier = Modifier
            .clip(CircleShape)
            .background(if (positive) colors.green.copy(alpha = 0.08f) else Color.White.copy(alpha = 0.035f))
            .border(1.dp, if (positive) colors.green.copy(alpha = 0.24f) else colors.line, CircleShape)
            .padding(horizontal = 10.dp, vertical = 8.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Box(Modifier.size(6.dp).clip(CircleShape).background(if (positive) colors.green else colors.textDim))
        Spacer(Modifier.width(7.dp))
        Text(
            text ?: if (positive) "前向证据通过" else "影子观察 · 尚未认证",
            color = tint,
            fontSize = 8.sp,
            fontWeight = FontWeight.Bold,
        )
    }
}

@Composable
fun MetricTile(label: String, value: String, note: String, modifier: Modifier = Modifier) {
    val colors = LocalTianjiColors.current
    Column(
        modifier = modifier
            .clip(RoundedCornerShape(15.dp))
            .background(Color.White.copy(alpha = 0.028f))
            .border(1.dp, colors.line, RoundedCornerShape(15.dp))
            .padding(12.dp),
    ) {
        Text(label, color = colors.textDim, fontSize = 8.sp)
        Spacer(Modifier.height(5.dp))
        Text(value, color = colors.text, fontSize = 16.sp, fontWeight = FontWeight.ExtraBold)
        Spacer(Modifier.height(4.dp))
        Text(note, color = colors.textDim, fontSize = 7.sp, maxLines = 1, overflow = TextOverflow.Ellipsis)
    }
}

@Composable
fun BottomNavigation(
    selected: NavDestination,
    onSelected: (NavDestination) -> Unit,
    modifier: Modifier = Modifier,
) {
    val colors = LocalTianjiColors.current
    Row(
        modifier = modifier
            .fillMaxWidth()
            .height(64.dp)
            .shadow(22.dp, RoundedCornerShape(22.dp), ambientColor = Color.Black.copy(alpha = 0.65f))
            .clip(RoundedCornerShape(22.dp))
            .background(Color(0xF214161D))
            .border(1.dp, Color.White.copy(alpha = 0.09f), RoundedCornerShape(22.dp))
            .padding(5.dp),
        horizontalArrangement = Arrangement.SpaceEvenly,
    ) {
        NavDestination.entries.forEach { item ->
            val active = item == selected
            val scale by animateFloatAsState(
                targetValue = if (active) 1f else 0.94f,
                animationSpec = spring(dampingRatio = 0.72f),
                label = "nav-scale",
            )
            Column(
                modifier = Modifier
                    .weight(1f)
                    .fillMaxHeight()
                    .clip(RoundedCornerShape(17.dp))
                    .clickable { onSelected(item) }
                    .scale(scale),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.Center,
            ) {
                Box(
                    modifier = Modifier
                        .size(width = 33.dp, height = 30.dp)
                        .clip(RoundedCornerShape(12.dp))
                        .background(if (active) colors.accentSoft else Color.Transparent),
                    contentAlignment = Alignment.Center,
                ) {
                    Icon(
                        item.icon,
                        item.label,
                        tint = if (active) colors.accent else colors.textDim,
                        modifier = Modifier.size(21.dp),
                    )
                }
                Spacer(Modifier.height(3.dp))
                Text(
                    item.label,
                    color = if (active) colors.text else colors.textDim,
                    fontSize = 8.sp,
                    fontWeight = if (active) FontWeight.Bold else FontWeight.SemiBold,
                )
            }
        }
    }
}

@Composable
fun EmptyState(title: String, detail: String, loading: Boolean = false) {
    val colors = LocalTianjiColors.current
    SurfaceCard {
        Column(
            modifier = Modifier.fillMaxWidth().padding(horizontal = 20.dp, vertical = 36.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            if (loading) CircularProgressIndicator(color = colors.accent, strokeWidth = 2.dp)
            else Icon(Icons.Rounded.Dataset, null, tint = colors.textDim, modifier = Modifier.size(34.dp))
            Spacer(Modifier.height(14.dp))
            Text(title, color = colors.text, fontSize = 15.sp, fontWeight = FontWeight.Bold)
            Spacer(Modifier.height(7.dp))
            Text(detail, color = colors.textDim, fontSize = 9.sp, lineHeight = 14.sp)
        }
    }
}

@Composable
fun SelectedCheck() {
    val colors = LocalTianjiColors.current
    Icon(Icons.Rounded.Check, null, tint = colors.text, modifier = Modifier.size(13.dp))
}

private fun ballColors(number: Int): Pair<Color, Color> = when (number) {
    1 -> Color(0xFFFFD54A) to Color(0xFFC99100)
    2 -> Color(0xFF57ADFF) to Color(0xFF1768C9)
    3 -> Color(0xFF8290A8) to Color(0xFF3A4458)
    4 -> Color(0xFFFF9147) to Color(0xFFD84D18)
    5 -> Color(0xFF38D1DE) to Color(0xFF168D9D)
    6 -> Color(0xFF9365FF) to Color(0xFF5930C6)
    7 -> Color(0xFFF6F8FC) to Color(0xFFB9C1CF)
    8 -> Color(0xFFFF6370) to Color(0xFFC92036)
    9 -> Color(0xFF6CDF72) to Color(0xFF249D38)
    else -> Color(0xFF3AD9B0) to Color(0xFF118B75)
}
