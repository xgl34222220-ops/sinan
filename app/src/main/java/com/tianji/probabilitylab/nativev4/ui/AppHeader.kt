package com.tianji.probabilitylab.nativev4.ui

import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxScope
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
import androidx.compose.material.icons.automirrored.rounded.ArrowBack
import androidx.compose.material.icons.rounded.Notifications
import androidx.compose.material.icons.rounded.Refresh
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.rotate
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.role
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.tianji.probabilitylab.nativev4.R
import com.tianji.probabilitylab.nativev4.ui.theme.LocalTianjiColors

@Composable
fun CompactAppHeader(
    destination: MainDestination,
    isRefreshing: Boolean,
    onRefresh: () -> Unit,
    canGoBack: Boolean = false,
    onBack: (() -> Unit)? = null,
    unreadAlerts: Int = 0,
    onAlerts: () -> Unit = {},
    homeSubtitle: String? = null,
) {
    val colors = LocalTianjiColors.current
    val refreshRotation by animateFloatAsState(
        targetValue = if (isRefreshing) 360f else 0f,
        animationSpec = tween(durationMillis = if (isRefreshing) 650 else 180),
        label = "header-refresh-rotation",
    )

    Row(
        modifier = Modifier
            .fillMaxWidth()
            .height(54.dp)
            .background(
                Brush.verticalGradient(
                    listOf(colors.header, colors.page.copy(alpha = 0.94f)),
                ),
            )
            .border(0.5.dp, colors.line)
            .padding(horizontal = 8.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        if (canGoBack && onBack != null) {
            HeaderActionButton(onClick = onBack, contentDescription = "返回") {
                Icon(
                    Icons.AutoMirrored.Rounded.ArrowBack,
                    contentDescription = null,
                    tint = colors.textSoft,
                    modifier = Modifier.size(21.dp),
                )
            }
            Spacer(Modifier.width(7.dp))
        } else if (destination == MainDestination.HOME) {
            Image(
                painter = painterResource(R.drawable.tianji_original_icon),
                contentDescription = "天机",
                contentScale = ContentScale.Crop,
                modifier = Modifier
                    .size(34.dp)
                    .clip(RoundedCornerShape(11.dp))
                    .border(1.dp, colors.accent.copy(alpha = 0.20f), RoundedCornerShape(11.dp)),
            )
            Spacer(Modifier.width(9.dp))
        }

        Column(Modifier.weight(1f)) {
            Text(
                if (destination == MainDestination.HOME) "天机" else destination.title,
                color = colors.text,
                fontSize = 17.sp,
                lineHeight = 21.sp,
                fontWeight = FontWeight.ExtraBold,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
            Text(
                if (destination == MainDestination.HOME) {
                    homeSubtitle?.takeIf(String::isNotBlank) ?: "双彩种实时同步 · 前向验证"
                } else {
                    destination.subtitle
                },
                color = colors.textDim,
                fontSize = 11.sp,
                lineHeight = 15.sp,
                fontWeight = FontWeight.Medium,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
        }

        HeaderActionButton(onClick = onAlerts, contentDescription = "打开通知中心") {
            Icon(
                Icons.Rounded.Notifications,
                contentDescription = null,
                tint = if (unreadAlerts > 0) colors.amber else colors.textSoft,
                modifier = Modifier.size(20.dp),
            )
            if (unreadAlerts > 0) {
                Text(
                    unreadAlerts.coerceAtMost(99).toString(),
                    color = Color.White,
                    fontSize = 10.sp,
                    lineHeight = 11.sp,
                    fontWeight = FontWeight.ExtraBold,
                    modifier = Modifier
                        .align(Alignment.TopEnd)
                        .clip(CircleShape)
                        .background(colors.red)
                        .padding(horizontal = 4.dp, vertical = 1.dp),
                )
            }
        }
        Spacer(Modifier.width(4.dp))
        HeaderActionButton(
            onClick = onRefresh,
            enabled = !isRefreshing,
            contentDescription = if (isRefreshing) "正在同步全部彩种" else "同步全部彩种",
        ) {
            Icon(
                Icons.Rounded.Refresh,
                contentDescription = null,
                tint = if (isRefreshing) colors.accent else colors.textSoft,
                modifier = Modifier.size(20.dp).rotate(refreshRotation),
            )
        }
    }
}

@Composable
private fun HeaderActionButton(
    onClick: () -> Unit,
    contentDescription: String,
    enabled: Boolean = true,
    content: @Composable BoxScope.() -> Unit,
) {
    val colors = LocalTianjiColors.current
    Box(
        modifier = Modifier
            .size(42.dp)
            .padding(2.dp)
            .clip(RoundedCornerShape(13.dp))
            .background(colors.glassStrong)
            .border(1.dp, colors.line, RoundedCornerShape(13.dp))
            .semantics {
                this.contentDescription = contentDescription
                role = Role.Button
            }
            .clickable(enabled = enabled, onClick = onClick),
        contentAlignment = Alignment.Center,
        content = content,
    )
}