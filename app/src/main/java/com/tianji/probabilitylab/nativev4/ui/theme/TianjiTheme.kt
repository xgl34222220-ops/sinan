package com.tianji.probabilitylab.nativev4.ui.theme

import android.os.Build
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.dynamicDarkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.Immutable
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.lerp
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp
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
    val page: Color = Color(0xFF080A0F),
    val pageSoft: Color = Color(0xFF0D1017),
    val surface: Color = Color(0xF2161922),
    val surfaceStrong: Color = Color(0xF51B1E29),
    val surfaceSoft: Color = Color.White.copy(alpha = 0.04f),
    val glass: Color = Color(0xDE151821),
    val glassStrong: Color = Color.White.copy(alpha = 0.045f),
    val header: Color = Color(0xF5080A0F),
    val navSurface: Color = Color(0xF51A1D27),
    val line: Color = Color.White.copy(alpha = 0.08f),
    val lineStrong: Color = Color.White.copy(alpha = 0.12f),
    val text: Color = Color(0xFFF7F8FB),
    val textSoft: Color = Color(0xFFC5C9D4),
    val textDim: Color = Color(0xFF858C9E),
    val green: Color = Color(0xFF62DDB8),
    val red: Color = Color(0xFFFF7581),
    val amber: Color = Color(0xFFFFBD5A),
    val violet: Color = Color(0xFF8D7CFF),
    val accent: Color,
    val accentSoft: Color,
    val monetSupported: Boolean,
)

val LocalTianjiColors = staticCompositionLocalOf {
    TianjiColors(
        accent = Color(0xFF8D7CFF),
        accentSoft = Color(0xFF8D7CFF).copy(alpha = 0.16f),
        monetSupported = false,
    )
}

private val TianjiTypography = Typography(
    bodySmall = TextStyle(fontSize = 11.sp, lineHeight = 16.sp),
    bodyMedium = TextStyle(fontSize = 13.sp, lineHeight = 19.sp),
    bodyLarge = TextStyle(fontSize = 15.sp, lineHeight = 22.sp),
    labelSmall = TextStyle(fontSize = 10.sp, lineHeight = 14.sp, fontWeight = FontWeight.Medium),
    labelMedium = TextStyle(fontSize = 11.sp, lineHeight = 16.sp, fontWeight = FontWeight.Medium),
    titleSmall = TextStyle(fontSize = 14.sp, lineHeight = 19.sp, fontWeight = FontWeight.Bold),
    titleMedium = TextStyle(fontSize = 17.sp, lineHeight = 22.sp, fontWeight = FontWeight.Bold),
    titleLarge = TextStyle(fontSize = 21.sp, lineHeight = 27.sp, fontWeight = FontWeight.ExtraBold),
)

@Composable
fun TianjiTheme(
    mode: PaletteMode,
    lottery: LotteryType,
    content: @Composable () -> Unit,
) {
    val context = LocalContext.current
    val dynamic = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
        dynamicDarkColorScheme(context)
    } else {
        null
    }
    val accent = when (mode) {
        PaletteMode.GAME -> if (lottery == LotteryType.XYFT) {
            Color(0xFFFF9B3F)
        } else {
            Color(0xFF8D7CFF)
        }
        PaletteMode.MONET -> dynamic?.primary ?: PaletteMode.MONET.preview
        PaletteMode.AMBER -> Color(0xFFFF9B3F)
        PaletteMode.VIOLET -> Color(0xFF8D7CFF)
        PaletteMode.JADE -> Color(0xFF4EDBB3)
    }
    val page = lerp(Color(0xFF07090D), accent, 0.025f)
    val pageSoft = lerp(Color(0xFF0D1017), accent, 0.035f)
    val surface = lerp(Color(0xFF141720), accent, 0.045f).copy(alpha = 0.96f)
    val surfaceStrong = lerp(Color(0xFF1A1D27), accent, 0.055f).copy(alpha = 0.97f)
    val palette = TianjiColors(
        page = page,
        pageSoft = pageSoft,
        surface = surface,
        surfaceStrong = surfaceStrong,
        glass = lerp(Color(0xFF131620), accent, 0.045f).copy(alpha = 0.90f),
        glassStrong = accent.copy(alpha = 0.055f),
        header = lerp(Color(0xFF07090D), accent, 0.02f).copy(alpha = 0.97f),
        navSurface = lerp(Color(0xFF181B25), accent, 0.055f).copy(alpha = 0.97f),
        accent = accent,
        accentSoft = accent.copy(alpha = 0.17f),
        violet = dynamic?.tertiary ?: Color(0xFF8D7CFF),
        green = dynamic?.secondary ?: Color(0xFF62DDB8),
        amber = Color(0xFFFFBD5A),
        monetSupported = Build.VERSION.SDK_INT >= Build.VERSION_CODES.S,
    )
    val scheme = darkColorScheme(
        primary = accent,
        onPrimary = Color.White,
        primaryContainer = accent.copy(alpha = 0.22f),
        onPrimaryContainer = palette.text,
        secondary = palette.green,
        tertiary = palette.violet,
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
        MaterialTheme(
            colorScheme = scheme,
            typography = TianjiTypography,
            content = content,
        )
    }
}
