package com.tianji.probabilitylab.nativev4.ui

import androidx.compose.animation.EnterTransition
import androidx.compose.animation.ExitTransition
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxScope
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier

/**
 * Stable visibility helper for content nested in a Box inside a Column.
 *
 * Compose also exposes a ColumnScope.AnimatedVisibility overload. When both
 * receivers are implicit, the Kotlin compiler can select the Column overload
 * and reject a Box-aligned modifier. This BoxScope overload makes the intended
 * receiver explicit while keeping the call site and behavior predictable.
 */
@Suppress("UNUSED_PARAMETER")
@Composable
internal fun BoxScope.AnimatedVisibility(
    visible: Boolean,
    modifier: Modifier,
    enter: EnterTransition,
    exit: ExitTransition,
    content: @Composable () -> Unit,
) {
    if (visible) {
        Box(modifier = modifier) {
            content()
        }
    }
}
