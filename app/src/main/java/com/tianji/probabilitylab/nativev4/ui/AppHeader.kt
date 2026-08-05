package com.tianji.probabilitylab.nativev4.ui

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
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.semantics.contentDescription
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
) {
    val colors = LocalTianjiColors.current
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .height(70.dp)
            .background(
                Brush.verticalGradient(
                    listOf(colors.header, colors.page.copy(alpha = 0.96f)),
                ),
            )
            .border(0.5.dp, colors.line)
            .padding(horizontal = 12.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        if (canGoBack && onBack != null) {
            IconButton(onClick = onBack, modifier = Modifier.size(48.dp)) {
                Icon(
                    Icons.AutoMirrored.Rounded.ArrowBack,
                    contentDescription = "返回",
                    tint = colors.textSoft,
                    modifier = Modifier.size(22.dp),
                )
            }
            Spacer(Modifier.width(3.dp))
        } else {
            Image(
                painter = painterResource(R.drawable.tianji_original_icon),
                contentDescription = "天机",
                contentScale = ContentScale.Crop,
                modifier = Modifier
                    .size(42.dp)
                    .shadow(
                        elevation = if (colors.isOled) 0.dp else 4.dp,
                        shape = RoundedCornerShape(15.dp),
                        ambientColor = colors.accent.copy(alpha = 0.18f),
                        spotColor = colors.accent.copy(alpha = 0.18f),
                    )
                    .clip(RoundedCornerShape(15.dp))
                    .border(1.dp, colors.accent.copy(alpha = 0.30f), RoundedCornerShape(15.dp)),
            )
            Spacer(Modifier.width(10.dp))
        }

        Column(Modifier.weight(1f)) {
            Text(
                destination.title,
                color = colors.text,
                fontSize = 19.sp,
                lineHeight = 23.sp,
                fontWeight = FontWeight.ExtraBold,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
            Spacer(Modifier.height(1.dp))
            Text(
                destination.subtitle,
                color = colors.textDim,
                fontSize = 11.sp,
                lineHeight = 15.sp,
                fontWeight = FontWeight.Medium,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
        }

        HeaderActionButton(
            onClick = onAlerts,
            contentDescription = "打开预警中心",
        ) {
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
                    fontSize = 8.sp,
                    fontWeight = FontWeight.ExtraBold,
                    modifier = Modifier
                        .align(Alignment.TopEnd)
                        .clip(CircleShape)
                        .background(colors.red)
                        .padding(horizontal = 3.dp, vertical = 1.dp),
                )
            }
        }
        Spacer(Modifier.width(7.dp))

        HeaderActionButton(
            onClick = onRefresh,
            enabled = !isRefreshing,
            contentDescription = "刷新",
        ) {
            if (isRefreshing) {
                CircularProgressIndicator(
                    modifier = Modifier.size(18.dp),
                    color = colors.accent,
                    strokeWidth = 2.dp,
                )
            } else {
                Icon(
                    Icons.Rounded.Refresh,
                    contentDescription = null,
                    tint = colors.textSoft,
                    modifier = Modifier.size(20.dp),
                )
            }
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
            .size(48.dp)
            .padding(2.dp)
            .shadow(
                elevation = if (colors.isOled) 0.dp else 2.dp,
                shape = RoundedCornerShape(15.dp),
                ambientColor = Color.Black.copy(alpha = 0.12f),
                spotColor = Color.Black.copy(alpha = 0.12f),
            )
            .clip(RoundedCornerShape(15.dp))
            .background(Brush.linearGradient(listOf(colors.glassStrong, colors.glass)))
            .border(1.dp, colors.lineStrong, RoundedCornerShape(15.dp))
            .semantics { this.contentDescription = contentDescription }
            .clickable(enabled = enabled, onClick = onClick),
        contentAlignment = Alignment.Center,
        content = content,
    )
}
