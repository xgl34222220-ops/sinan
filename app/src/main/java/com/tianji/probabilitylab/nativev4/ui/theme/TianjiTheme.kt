package com.tianji.probabilitylab.nativev4.ui.theme

import android.content.Context
import android.os.Build
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.dynamicDarkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.Immutable
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import com.tianji.probabilitylab.nativev4.model.LotteryType

enum class PaletteMode(val label: String, val preview: Color) {
    GAME("跟随彩种", Color(0xFFFF8A1F)),
    MONET("系统 Monet", Color(0xFFA78BFA)),
    AMBER("曜金", Color(0xFFFF8A1F)),
    VIOLET("星紫", Color(0xFF7C6CFF)),
    JADE("青玉", Color(0xFF43D6A8)),
}

@Immutable
data class TianjiColors(
    val page: Color = Color(0xFF090A0E),
    val pageSoft: Color = Color(0xFF0E1016),
    val surface: Color = Color(0xFF161820),
    val surfaceStrong: Color = Color(0xFF171922),
    val surfaceSoft: Color = Color.White.copy(alpha = 0.035f),
    val line: Color = Color.White.copy(alpha = 0.075f),
    val lineStrong: Color = Color.White.copy(alpha = 0.12f),
    val text: Color = Color(0xFFF6F7FA),
    val textSoft: Color = Color(0xFFA9ADBA),
    val textDim: Color = Color(0xFF696E7D),
    val green: Color = Color(0xFF62DDB8),
    val red: Color = Color(0xFFFF6D77),
    val amber: Color = Color(0xFFFFBD5A),
    val accent: Color,
    val accentSoft: Color,
    val monetSupported: Boolean,
)

val LocalTianjiColors = staticCompositionLocalOf {
    TianjiColors(
        accent = Color(0xFF7C6CFF),
        accentSoft = Color(0xFF7C6CFF).copy(alpha = 0.16f),
        monetSupported = false,
    )
}

@Composable
fun TianjiTheme(
    mode: PaletteMode,
    lottery: LotteryType,
    content: @Composable () -> Unit,
) {
    val context = LocalContext.current
    val dynamic = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
        dynamicDarkColorScheme(context)
    } else null
    val accent = when (mode) {
        PaletteMode.GAME -> if (lottery == LotteryType.XYFT) Color(0xFFFF8A1F) else Color(0xFF7C6CFF)
        PaletteMode.MONET -> dynamic?.primary ?: PaletteMode.MONET.preview
        PaletteMode.AMBER -> PaletteMode.AMBER.preview
        PaletteMode.VIOLET -> PaletteMode.VIOLET.preview
        PaletteMode.JADE -> PaletteMode.JADE.preview
    }
    val palette = TianjiColors(
        accent = accent,
        accentSoft = accent.copy(alpha = 0.16f),
        monetSupported = Build.VERSION.SDK_INT >= Build.VERSION_CODES.S,
    )
    val scheme = darkColorScheme(
        primary = accent,
        onPrimary = Color.White,
        primaryContainer = accent.copy(alpha = 0.22f),
        onPrimaryContainer = palette.text,
        secondary = dynamic?.secondary ?: palette.green,
        tertiary = dynamic?.tertiary ?: palette.amber,
        background = palette.page,
        onBackground = palette.text,
        surface = palette.surface,
        onSurface = palette.text,
        surfaceVariant = palette.surfaceStrong,
        onSurfaceVariant = palette.textSoft,
        outline = palette.lineStrong,
        error = palette.red,
    )
    androidx.compose.runtime.CompositionLocalProvider(LocalTianjiColors provides palette) {
        MaterialTheme(colorScheme = scheme, content = content)
    }
}
