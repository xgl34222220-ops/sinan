package com.tianji.probabilitylab.nativev4.ui

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxScope
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawing
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.material3.Scaffold
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import com.tianji.probabilitylab.nativev4.ui.theme.LocalTianjiColors

/**
 * Single system-inset and bottom-navigation owner for normal App pages.
 * v6.7 keeps one restrained accent glow instead of stacking decorative gradients behind every card.
 */
@Composable
internal fun TianjiRootScaffold(
    bottomBar: @Composable () -> Unit = {},
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
        Scaffold(
            modifier = Modifier
                .fillMaxSize()
                .windowInsetsPadding(WindowInsets.safeDrawing),
            containerColor = Color.Transparent,
            contentWindowInsets = WindowInsets(0, 0, 0, 0),
            bottomBar = bottomBar,
        ) { scaffoldPadding ->
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(scaffoldPadding),
                content = content,
            )
        }
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
                        alpha = if (colors.isOled) 0.018f else if (colors.isDark) 0.040f else 0.026f,
                    ),
                    Color.Transparent,
                ),
            ),
            radius = size.width * 0.90f,
            center = Offset(size.width * 1.06f, size.height * 0.16f),
        )
    }
}
