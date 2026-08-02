package com.tianji.probabilitylab.nativev4.ui.theme

import android.content.Context
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

private val Context.appearanceDataStore by preferencesDataStore(name = "appearance")

class AppearanceStore(private val context: Context) {
    private val paletteKey = stringPreferencesKey("palette")

    val palette: Flow<PaletteMode> = context.appearanceDataStore.data.map { preferences ->
        runCatching { PaletteMode.valueOf(preferences[paletteKey] ?: PaletteMode.MONET.name) }
            .getOrDefault(PaletteMode.MONET)
    }

    suspend fun setPalette(mode: PaletteMode) {
        context.appearanceDataStore.edit { it[paletteKey] = mode.name }
    }
}
