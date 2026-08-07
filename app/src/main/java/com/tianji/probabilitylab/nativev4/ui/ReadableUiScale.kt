package com.tianji.probabilitylab.nativev4.ui

import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.unit.Density

/**
 * Applies a minimum readable font scale without multiplying the user's system font scale.
 * Large-text users keep their configured scale unchanged; only the default/smaller scale is
 * gently lifted for dense utility surfaces such as Settings and AI chat.
 */
@Composable
internal fun ReadableUiScale(
    minFontScale: Float = 1.16f,
    content: @Composable () -> Unit,
) {
    val density = LocalDensity.current
    val targetFontScale = maxOf(density.fontScale, minFontScale)
    if (targetFontScale == density.fontScale) {
        content()
    } else {
        CompositionLocalProvider(
            LocalDensity provides Density(
                density = density.density,
                fontScale = targetFontScale,
            ),
            content = content,
        )
    }
}
