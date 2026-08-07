package com.tianji.probabilitylab.nativev4.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.CheckCircle
import androidx.compose.material.icons.rounded.ErrorOutline
import androidx.compose.material3.Icon
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.role
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.tianji.probabilitylab.nativev4.model.ModelPerformance
import com.tianji.probabilitylab.nativev4.ui.theme.LocalTianjiColors
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

@Composable
internal fun PositionSelectorV2(selected: Int, onSelected: (Int) -> Unit) {
    val colors = LocalTianjiColors.current
    Row(
        Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()),
        horizontalArrangement = Arrangement.spacedBy(7.dp),
    ) {
        repeat(10) { index ->
            val active = index == selected
            Box(
                modifier = Modifier
                    .width(46.dp)
                    .heightIn(min = 52.dp)
                    .clip(RoundedCornerShape(14.dp))
                    .background(if (active) colors.accent else colors.surfaceStrong)
                    .border(
                        1.dp,
                        if (active) Color.Transparent else colors.line,
                        RoundedCornerShape(14.dp),
                    )
                    .semantics { role = Role.Tab }
                    .clickable { onSelected(index) },
                contentAlignment = Alignment.Center,
            ) {
                Text(
                    text = if (index == 0) "冠" else if (index == 1) "亚" else (index + 1).toString(),
                    color = if (active) Color.White else colors.textSoft,
                    fontSize = 12.sp,
                    fontWeight = FontWeight.Bold,
                    textAlign = TextAlign.Center,
                )
            }
        }
    }
}

@Composable
internal fun CompactNumberRowV2(
    numbers: List<Int>,
    size: Int,
    spread: Boolean = false,
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = if (spread) Arrangement.SpaceEvenly else Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        numbers.forEach { LotteryBall(it, size = size.dp) }
    }
}

@Composable
internal fun CompactMetricV2(label: String, value: String, modifier: Modifier = Modifier) {
    val colors = LocalTianjiColors.current
    Column(
        modifier = modifier
            .clip(RoundedCornerShape(14.dp))
            .background(colors.surfaceStrong.copy(alpha = 0.78f))
            .border(1.dp, colors.line, RoundedCornerShape(14.dp))
            .padding(horizontal = 11.dp, vertical = 11.dp),
    ) {
        Text(label, color = colors.textDim, fontSize = 12.sp, lineHeight = 16.sp, maxLines = 1)
        Spacer(Modifier.size(3.dp))
        Text(
            value,
            color = colors.text,
            fontSize = 16.sp,
            lineHeight = 21.sp,
            fontWeight = FontWeight.ExtraBold,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
        )
    }
}

@Composable
internal fun RefinedModelRowV2(rank: Int, model: ModelPerformance) {
    val colors = LocalTianjiColors.current
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(14.dp))
            .background(colors.surfaceStrong.copy(alpha = 0.72f))
            .border(1.dp, colors.line, RoundedCornerShape(14.dp))
            .padding(11.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Box(
            Modifier.size(34.dp).clip(RoundedCornerShape(10.dp)).background(colors.accentSoft),
            contentAlignment = Alignment.Center,
        ) {
            Text(rank.toString(), color = colors.accent, fontSize = 12.sp, fontWeight = FontWeight.Bold)
        }
        Spacer(Modifier.size(9.dp))
        Column(Modifier.weight(1f)) {
            Text(
                model.name,
                color = colors.textSoft,
                fontSize = 12.sp,
                fontWeight = FontWeight.SemiBold,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
            Spacer(Modifier.size(5.dp))
            LinearProgressIndicator(
                progress = { model.weight.toFloat().coerceIn(0f, 1f) },
                modifier = Modifier.fillMaxWidth().heightIn(min = 5.dp).clip(CircleShape),
                color = if (model.weight > 0.005) colors.accent else colors.textDim,
                trackColor = colors.line,
            )
        }
        Spacer(Modifier.size(9.dp))
        Column(horizontalAlignment = Alignment.End) {
            Text(
                "${(model.weight * 100).format1V2()}%",
                color = if (model.weight > 0.005) colors.accent else colors.textDim,
                fontSize = 12.sp,
                fontWeight = FontWeight.Bold,
            )
            Text("命中 ${(model.hitRate * 100).format1V2()}%", color = colors.textDim, fontSize = 11.sp)
        }
    }
}

@Composable
internal fun EvidenceRowV2(text: String, passed: Boolean) {
    val colors = LocalTianjiColors.current
    val tint = if (passed) colors.green else colors.amber
    Row(
        modifier = Modifier.fillMaxWidth().padding(vertical = 7.dp),
        verticalAlignment = Alignment.Top,
    ) {
        Icon(
            if (passed) Icons.Rounded.CheckCircle else Icons.Rounded.ErrorOutline,
            contentDescription = null,
            tint = tint,
            modifier = Modifier.size(18.dp),
        )
        Spacer(Modifier.size(8.dp))
        Text(text, color = colors.textSoft, fontSize = 12.sp, lineHeight = 18.sp)
    }
}

@Composable
internal fun StatusChipV2(text: String, tint: Color) {
    Text(
        text,
        color = tint,
        fontSize = 11.sp,
        lineHeight = 15.sp,
        fontWeight = FontWeight.Bold,
        modifier = Modifier
            .clip(CircleShape)
            .background(tint.copy(alpha = 0.10f))
            .border(1.dp, tint.copy(alpha = 0.18f), CircleShape)
            .padding(horizontal = 9.dp, vertical = 6.dp),
    )
}

internal fun positionNameV2(position: Int): String = when (position) {
    0 -> "一"
    1 -> "二"
    2 -> "三"
    3 -> "四"
    4 -> "五"
    5 -> "六"
    6 -> "七"
    7 -> "八"
    8 -> "九"
    else -> "十"
}

internal fun syncAgeV2(epoch: Long): String {
    val age = (System.currentTimeMillis() - epoch).coerceAtLeast(0)
    return when {
        age < 15_000 -> "刚刚"
        age < 60_000 -> "${age / 1_000} 秒前"
        age < 3_600_000 -> "${age / 60_000} 分钟前"
        else -> "${age / 3_600_000} 小时前"
    }
}

internal fun settlementLabelV2(top6: Boolean?, top7: Boolean?): String = when {
    top6 == null -> "待开奖"
    top6 -> "六码命中"
    top7 == true -> "七码命中"
    else -> "未命中"
}

@Composable
internal fun settlementTintV2(top6: Boolean?, top7: Boolean?): Color {
    val colors = LocalTianjiColors.current
    return when {
        top6 == null -> colors.amber
        top6 || top7 == true -> colors.green
        else -> colors.red
    }
}

internal fun formatTimeV2(epoch: Long): String =
    SimpleDateFormat("MM-dd HH:mm", Locale.getDefault()).format(Date(epoch))

internal fun Double.format1V2() = String.format(Locale.US, "%.1f", this)
internal fun Double.format2V2() = String.format(Locale.US, "%.2f", this)
