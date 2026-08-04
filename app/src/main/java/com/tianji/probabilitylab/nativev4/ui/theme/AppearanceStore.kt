package com.tianji.probabilitylab.nativev4.ui.theme

import android.content.Context
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

private val Context.appearanceDataStore by preferencesDataStore(name = "appearance")

enum class AppearanceMode(val label: String) {
    SYSTEM("跟随系统"),
    LIGHT("浅色"),
    DARK("深色"),
    OLED("OLED 纯黑"),
}

class AppearanceStore(private val context: Context) {
    private val paletteKey = stringPreferencesKey("palette")
    private val appearanceKey = stringPreferencesKey("appearance_mode")

    val palette: Flow<PaletteMode> = context.appearanceDataStore.data.map { preferences ->
        runCatching { PaletteMode.valueOf(preferences[paletteKey] ?: PaletteMode.MONET.name) }
            .getOrDefault(PaletteMode.MONET)
    }

    val appearance: Flow<AppearanceMode> = context.appearanceDataStore.data.map { preferences ->
        runCatching {
            AppearanceMode.valueOf(preferences[appearanceKey] ?: AppearanceMode.SYSTEM.name)
        }.getOrDefault(AppearanceMode.SYSTEM)
    }

    suspend fun setPalette(mode: PaletteMode) {
        context.appearanceDataStore.edit { it[paletteKey] = mode.name }
    }

    suspend fun setAppearance(mode: AppearanceMode) {
        context.appearanceDataStore.edit { it[appearanceKey] = mode.name }
    }
}
