package com.tianji.probabilitylab.nativev4.ui.theme

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class TianjiThemePolicyTest {
    @Test
    fun dynamicPaletteIsOnlyUsedForMonet() {
        assertTrue(shouldUseDynamicPalette(PaletteMode.MONET, supported = true))
        assertFalse(shouldUseDynamicPalette(PaletteMode.GAME, supported = true))
        assertFalse(shouldUseDynamicPalette(PaletteMode.AMBER, supported = true))
        assertFalse(shouldUseDynamicPalette(PaletteMode.VIOLET, supported = true))
        assertFalse(shouldUseDynamicPalette(PaletteMode.JADE, supported = true))
        assertFalse(shouldUseDynamicPalette(PaletteMode.OLED, supported = true))
    }

    @Test
    fun monetFallsBackWhenDynamicColorsAreUnsupported() {
        assertFalse(shouldUseDynamicPalette(PaletteMode.MONET, supported = false))
    }
}
