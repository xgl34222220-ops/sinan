package com.tianji.probabilitylab.nativev4.ui

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInVertically
import androidx.compose.animation.slideOutVertically
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.AutoAwesome
import androidx.compose.material.icons.rounded.Schedule
import androidx.compose.material3.Icon
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.tianji.probabilitylab.nativev4.AppUiState
import com.tianji.probabilitylab.nativev4.ui.theme.LocalTianjiColors

@Composable
fun AiReviewProgressDock(
    state: AppUiState,
    modifier: Modifier = Modifier,
) {
    val colors = LocalTianjiColors.current
    val statuses = state.aiStatuses.values.toList()
    val runningMessage = statuses.firstOrNull { status ->
        status.state.name == "ANALYZING" || status.state.name == "TESTING"
    }?.message.orEmpty()
    val failed = statuses.count { it.state.name == "FAILED" }
    val detail = when {
        runningMessage.isNotBlank() -> runningMessage
        failed > 0 -> "部分模型暂未响应，正在继续处理"
        else -> "正在分析历史数据并生成结果"
    }

    AnimatedVisibility(
        visible = state.isAiAnalyzing,
        enter = fadeIn() + slideInVertically { it / 2 },
        exit = fadeOut() + slideOutVertically { it / 2 },
        modifier = modifier,
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(18.dp))
                .background(colors.glass)
                .border(1.dp, colors.accent.copy(alpha = 0.28f), RoundedCornerShape(18.dp))
                .padding(horizontal = 13.dp, vertical = 10.dp),
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(
                    Icons.Rounded.AutoAwesome,
                    contentDescription = null,
                    tint = colors.accent,
                    modifier = Modifier.size(18.dp),
                )
                Spacer(Modifier.width(8.dp))
                Column(Modifier.weight(1f)) {
                    Text(
                        "正在生成预测",
                        color = colors.text,
                        fontSize = 12.sp,
                        fontWeight = FontWeight.ExtraBold,
                    )
                    Text(
                        detail,
                        color = colors.textDim,
                        fontSize = 11.sp,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
            }
            Spacer(Modifier.height(8.dp))
            LinearProgressIndicator(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(4.dp)
                    .clip(CircleShape),
                color = colors.accent,
                trackColor = colors.line,
            )
        }
    }
}
