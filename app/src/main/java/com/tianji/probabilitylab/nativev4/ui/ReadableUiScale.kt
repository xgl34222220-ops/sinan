package com.tianji.probabilitylab.nativev4.ui

import androidx.compose.runtime.Composable

/**
 * Compatibility wrapper retained for older screens.
 *
 * v6.7 removes page-specific font-scale multiplication: every screen now follows the same
 * system font scale. Readability is handled by component typography instead of secretly making
 * Settings/AI chat larger than Forecast/Strategy/Archive.
 */
@Composable
internal fun ReadableUiScale(
    @Suppress("UNUSED_PARAMETER") minFontScale: Float = 1f,
    content: @Composable () -> Unit,
) {
    content()
}
