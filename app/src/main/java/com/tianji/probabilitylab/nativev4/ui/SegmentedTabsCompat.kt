package com.tianji.probabilitylab.nativev4.ui

import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier

/** Allows the idiomatic trailing-lambda form while preserving named-argument calls. */
@Composable
internal fun SegmentedTabs(
    items: List<String>,
    selectedIndex: Int,
    modifier: Modifier = Modifier,
    selectionHandler: (Int) -> Unit,
) {
    SegmentedTabs(
        items = items,
        selectedIndex = selectedIndex,
        onSelected = selectionHandler,
        modifier = modifier,
    )
}
