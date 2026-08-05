package com.tianji.probabilitylab.nativev4.ui

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxScope
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.safeDrawing
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import com.tianji.probabilitylab.nativev4.ui.theme.LocalTianjiColors

/**
 * Single system-inset owner for normal App pages.
 * Full-screen overlays such as chat and the alert center stay outside this container
 * and are responsible for IME handling only once.
 */
@Composable
internal fun TianjiRootScaffold(
    content: @Composable BoxScope.() -> Unit,
) {
    val colors = LocalTianjiColors.current
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(colors.page),
    ) {
        Box(
            modifier = Modifier
                .fillMaxSize()
                .background(
                    Brush.verticalGradient(
                        listOf(colors.page, colors.pageSoft, colors.page),
                    ),
                ),
        ) {
            TianjiBackdrop()
        }
        Box(
            modifier = Modifier
                .fillMaxSize()
                .windowInsetsPadding(WindowInsets.safeDrawing),
            content = content,
        )
    }
}

@Composable
private fun TianjiBackdrop() {
    val colors = LocalTianjiColors.current
    Canvas(Modifier.fillMaxSize()) {
        drawCircle(
            brush = Brush.radialGradient(
                listOf(
                    colors.accent.copy(
                        alpha = if (colors.isOled) 0.035f else if (colors.isDark) 0.075f else 0.045f,
                    ),
                    Color.Transparent,
                ),
            ),
            radius = size.width * 0.84f,
            center = Offset(size.width * 1.04f, size.height * 0.20f),
        )
        drawCircle(
            brush = Brush.radialGradient(
                listOf(
                    colors.amber.copy(
                        alpha = if (colors.isOled) 0.018f else if (colors.isDark) 0.042f else 0.028f,
                    ),
                    Color.Transparent,
                ),
            ),
            radius = size.width * 0.72f,
            center = Offset(size.width * -0.08f, size.height * 0.04f),
        )
    }
}
