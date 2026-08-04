package com.tianji.probabilitylab.nativev4.ui

import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.spring
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
            .height(68.dp)
            .background(
                Brush.verticalGradient(
                    listOf(colors.header, colors.header.copy(alpha = 0.94f)),
                ),
            )
            .border(width = 0.5.dp, color = colors.line)
            .padding(horizontal = 16.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.SpaceBetween,
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Image(
                painter = painterResource(R.drawable.tianji_original_icon),
                contentDescription = "天机",
                contentScale = ContentScale.Crop,
                modifier = Modifier
                    .size(40.dp)
                    .shadow(
                        elevation = 10.dp,
                        shape = RoundedCornerShape(14.dp),
                        ambientColor = colors.accent.copy(alpha = 0.35f),
                        spotColor = colors.accent.copy(alpha = 0.35f),
                    )
                    .clip(RoundedCornerShape(14.dp))
                    .border(
                        1.dp,
                        colors.accent.copy(alpha = 0.48f),
                        RoundedCornerShape(14.dp),
                    ),
            )
            Spacer(Modifier.width(11.dp))
            Column {
                Text(
                    text = "天机",
                    color = colors.text,
                    fontSize = 19.sp,
                    fontWeight = FontWeight.ExtraBold,
                    letterSpacing = 1.2.sp,
                )
                Spacer(Modifier.height(2.dp))
                Text(
                    text = "开奖概率实验室",
                    color = colors.textDim,
                    fontSize = 10.sp,
                    fontWeight = FontWeight.Medium,
                    letterSpacing = 0.25.sp,
                )
            }
        }
        Box(
            modifier = Modifier
                .size(42.dp)
                .clip(RoundedCornerShape(15.dp))
                .background(colors.glassStrong)
                .border(1.dp, colors.lineStrong, RoundedCornerShape(15.dp))
                .clickable(enabled = !isRefreshing, onClick = onRefresh),
            contentAlignment = Alignment.Center,
        ) {
            if (isRefreshing) {
                CircularProgressIndicator(
                    modifier = Modifier.size(19.dp),
                    color = colors.accent,
                    strokeWidth = 2.dp,
                )
            } else {
                Icon(
                    Icons.Rounded.Refresh,
                    contentDescription = "刷新",
                    tint = colors.textSoft,
                    modifier = Modifier.size(22.dp),
                )
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
            .height(66.dp)
            .clip(RoundedCornerShape(20.dp))
            .background(colors.glass)
            .border(1.dp, colors.line, RoundedCornerShape(20.dp))
            .padding(5.dp),
        horizontalArrangement = Arrangement.spacedBy(6.dp),
    ) {
        LotteryType.entries.forEach { lottery ->
            val active = selected == lottery
            val accent = if (lottery == LotteryType.XYFT) colors.amber else colors.violet
            Box(
                modifier = Modifier
                    .weight(1f)
                    .fillMaxHeight()
                    .clip(RoundedCornerShape(16.dp))
                    .background(
                        if (active) {
                            Brush.linearGradient(
                                listOf(
                                    accent.copy(alpha = 0.22f),
                                    colors.glassStrong,
                                ),
                            )
                        } else {
                            Brush.linearGradient(listOf(Color.Transparent, Color.Transparent))
                        },
                    )
                    .border(
                        width = 1.dp,
                        color = if (active) accent.copy(alpha = 0.34f) else Color.Transparent,
                        shape = RoundedCornerShape(16.dp),
                    )
                    .clickable { onSelect(lottery) }
                    .padding(horizontal = 11.dp, vertical = 7.dp),
                contentAlignment = Alignment.CenterStart,
            ) {
                Column {
                    Text(
                        text = lottery.displayName,
                        color = if (active) colors.text else colors.textSoft,
                        fontSize = 12.sp,
                        lineHeight = 16.sp,
                        fontWeight = FontWeight.Bold,
                        maxLines = 1,
                    )
                    Spacer(Modifier.height(2.dp))
                    Text(
                        lottery.subtitle,
                        color = if (active) accent else colors.textDim,
                        fontSize = 9.sp,
                        lineHeight = 12.sp,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
                if (active) {
                    Box(
                        Modifier
                            .align(Alignment.BottomCenter)
                            .fillMaxWidth(0.62f)
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
    radius: Dp = 22.dp,
    content: @Composable ColumnScope.() -> Unit,
) {
    val colors = LocalTianjiColors.current
    Column(
        modifier = modifier
            .fillMaxWidth()
            .shadow(
                elevation = 10.dp,
                shape = RoundedCornerShape(radius),
                ambientColor = Color.Black.copy(alpha = 0.20f),
                spotColor = Color.Black.copy(alpha = 0.20f),
            )
            .clip(RoundedCornerShape(radius))
            .background(
                Brush.linearGradient(
                    listOf(colors.surfaceStrong, colors.surface),
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
                    .size(38.dp)
                    .clip(RoundedCornerShape(13.dp))
                    .background(colors.accentSoft)
                    .border(
                        1.dp,
                        colors.accent.copy(alpha = 0.20f),
                        RoundedCornerShape(13.dp),
                    ),
                contentAlignment = Alignment.Center,
            ) {
                Icon(icon, null, tint = colors.accent, modifier = Modifier.size(19.dp))
            }
            Spacer(Modifier.width(11.dp))
        }
        Column(modifier = Modifier.weight(1f)) {
            Text(
                localizedSectionEyebrow(eyebrow),
                color = colors.accent,
                fontSize = 9.sp,
                fontWeight = FontWeight.Bold,
                letterSpacing = 0.6.sp,
            )
            Spacer(Modifier.height(4.dp))
            Text(
                title,
                color = colors.text,
                fontSize = 18.sp,
                lineHeight = 23.sp,
                fontWeight = FontWeight.ExtraBold,
            )
            detail?.let {
                Spacer(Modifier.height(5.dp))
                Text(
                    it,
                    color = colors.textDim,
                    fontSize = 10.sp,
                    lineHeight = 15.sp,
                )
            }
        }
        trailing?.invoke()
    }
}

@Composable
fun LotteryBall(
    number: Int,
    modifier: Modifier = Modifier,
    size: Dp = 42.dp,
    muted: Boolean = false,
) {
    val pair = ballColors(number)
    val alpha = if (muted) 0.46f else 1f
    Box(
        modifier = modifier
            .size(size)
            .shadow(
                elevation = if (muted) 2.dp else 7.dp,
                shape = CircleShape,
                ambientColor = pair.second.copy(alpha = 0.30f),
                spotColor = pair.second.copy(alpha = 0.30f),
            )
            .clip(CircleShape)
            .background(
                Brush.radialGradient(
                    colors = listOf(
                        Color.White.copy(alpha = 0.64f * alpha),
                        pair.first.copy(alpha = alpha),
                        pair.second.copy(alpha = alpha),
                    ),
                    radius = size.value * 1.5f,
                ),
            )
            .border(1.dp, Color.White.copy(alpha = 0.24f * alpha), CircleShape),
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
            .background(
                if (positive) colors.green.copy(alpha = 0.10f) else colors.glassStrong,
            )
            .border(
                1.dp,
                if (positive) colors.green.copy(alpha = 0.25f) else colors.line,
                CircleShape,
            )
            .padding(horizontal = 11.dp, vertical = 8.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Box(
            Modifier
                .size(7.dp)
                .clip(CircleShape)
                .background(if (positive) colors.green else colors.textDim),
        )
        Spacer(Modifier.width(7.dp))
        Text(
            text ?: if (positive) "前向证据通过" else "影子观察 · 尚未认证",
            color = tint,
            fontSize = 10.sp,
            fontWeight = FontWeight.Bold,
        )
    }
}

@Composable
fun MetricTile(label: String, value: String, note: String, modifier: Modifier = Modifier) {
    val colors = LocalTianjiColors.current
    Column(
        modifier = modifier
            .clip(RoundedCornerShape(16.dp))
            .background(colors.glassStrong)
            .border(1.dp, colors.line, RoundedCornerShape(16.dp))
            .padding(horizontal = 12.dp, vertical = 13.dp),
    ) {
        Text(label, color = colors.textDim, fontSize = 10.sp)
        Spacer(Modifier.height(5.dp))
        Text(
            value,
            color = colors.text,
            fontSize = 17.sp,
            fontWeight = FontWeight.ExtraBold,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
        )
        Spacer(Modifier.height(4.dp))
        Text(
            note,
            color = colors.textDim,
            fontSize = 9.sp,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
        )
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
            .height(70.dp)
            .shadow(
                elevation = 20.dp,
                shape = RoundedCornerShape(25.dp),
                ambientColor = Color.Black.copy(alpha = 0.48f),
                spotColor = Color.Black.copy(alpha = 0.48f),
            )
            .clip(RoundedCornerShape(25.dp))
            .background(
                Brush.linearGradient(
                    listOf(colors.navSurface, colors.navSurface.copy(alpha = 0.94f)),
                ),
            )
            .border(1.dp, colors.lineStrong, RoundedCornerShape(25.dp))
            .padding(6.dp),
        horizontalArrangement = Arrangement.SpaceEvenly,
    ) {
        NavDestination.entries.forEach { item ->
            val active = item == selected
            val scale by animateFloatAsState(
                targetValue = if (active) 1f else 0.95f,
                animationSpec = spring(dampingRatio = 0.75f),
                label = "nav-scale",
            )
            Column(
                modifier = Modifier
                    .weight(1f)
                    .fillMaxHeight()
                    .clip(RoundedCornerShape(18.dp))
                    .background(
                        if (active) {
                            Brush.linearGradient(
                                listOf(
                                    colors.accent.copy(alpha = 0.20f),
                                    colors.accentSoft.copy(alpha = 0.70f),
                                ),
                            )
                        } else {
                            Brush.linearGradient(listOf(Color.Transparent, Color.Transparent))
                        },
                    )
                    .border(
                        1.dp,
                        if (active) colors.accent.copy(alpha = 0.20f) else Color.Transparent,
                        RoundedCornerShape(18.dp),
                    )
                    .clickable { onSelected(item) }
                    .scale(scale),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.Center,
            ) {
                Icon(
                    item.icon,
                    item.label,
                    tint = if (active) colors.accent else colors.textDim,
                    modifier = Modifier.size(if (active) 22.dp else 20.dp),
                )
                Spacer(Modifier.height(4.dp))
                Text(
                    item.label,
                    color = if (active) colors.text else colors.textDim,
                    fontSize = 10.sp,
                    fontWeight = if (active) FontWeight.Bold else FontWeight.Medium,
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
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 22.dp, vertical = 38.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            if (loading) {
                CircularProgressIndicator(
                    modifier = Modifier.size(30.dp),
                    color = colors.accent,
                    strokeWidth = 2.dp,
                )
            } else {
                Box(
                    modifier = Modifier
                        .size(48.dp)
                        .clip(RoundedCornerShape(17.dp))
                        .background(colors.glassStrong),
                    contentAlignment = Alignment.Center,
                ) {
                    Icon(
                        Icons.Rounded.Dataset,
                        null,
                        tint = colors.textDim,
                        modifier = Modifier.size(27.dp),
                    )
                }
            }
            Spacer(Modifier.height(15.dp))
            Text(title, color = colors.text, fontSize = 16.sp, fontWeight = FontWeight.Bold)
            Spacer(Modifier.height(6.dp))
            Text(
                detail,
                color = colors.textDim,
                fontSize = 11.sp,
                lineHeight = 17.sp,
            )
        }
    }
}

@Composable
fun SelectedCheck() {
    val colors = LocalTianjiColors.current
    Icon(Icons.Rounded.Check, null, tint = colors.text, modifier = Modifier.size(14.dp))
}

private fun localizedSectionEyebrow(value: String): String = when (value) {
    "NEXT DRAW FORECAST" -> "下期预测"
    "MULTI-PROVIDER AI" -> "多模型 AI"
    "PROBABILITY MATRIX" -> "概率矩阵"
    "MODEL COMPETITION" -> "模型竞赛"
    "ROLLING LAB" -> "滚动实验"
    "LOCKED TICKET" -> "冻结结果"
    "RISK GATE" -> "风险闸门"
    "TIME HOLDOUT TEST" -> "时间留出验证"
    "EVIDENCE GATES" -> "证据闸门"
    "ALL MODELS" -> "全部模型"
    "FORWARD ARCHIVE" -> "前向档案"
    "DATA HEALTH" -> "数据健康"
    "MIUIX APPEARANCE" -> "界面外观"
    "RECENT HISTORY" -> "最近开奖"
    "AI PROFILES" -> "AI 配置"
    else -> value
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
