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
    GAME("跟随彩种", Color(0xFFFF9B3F)),
    MONET("系统 Monet", Color(0xFFA78BFA)),
    AMBER("曜金", Color(0xFFFF9B3F)),
    VIOLET("星紫", Color(0xFF8D7CFF)),
    JADE("青玉", Color(0xFF4EDBB3)),
    OLED("纯黑", Color(0xFF0A0A0A)),
}

@Immutable
data class TianjiColors(
    val page: Color = Color(0xFF07080D),
    val pageSoft: Color = Color(0xFF0D0F16),
    val surface: Color = Color(0xF5151821),
    val surfaceStrong: Color = Color(0xFA1B1E29),
    val surfaceSoft: Color = Color.White.copy(alpha = 0.04f),
    val glass: Color = Color(0xEC141720),
    val glassStrong: Color = Color.White.copy(alpha = 0.055f),
    val header: Color = Color(0xF707080D),
    val navSurface: Color = Color(0xF71A1D27),
    val line: Color = Color.White.copy(alpha = 0.075f),
    val lineStrong: Color = Color.White.copy(alpha = 0.13f),
    val text: Color = Color(0xFFF7F8FB),
    val textSoft: Color = Color(0xFFD1D4DD),
    val textDim: Color = Color(0xFF9299A9),
    val green: Color = Color(0xFF62DDB8),
    val red: Color = Color(0xFFFF7581),
    val amber: Color = Color(0xFFFFBD5A),
    val violet: Color = Color(0xFF8D7CFF),
    val accent: Color,
    val accentSoft: Color,
    val monetSupported: Boolean,
    val isOled: Boolean = false,
)

val LocalTianjiColors = staticCompositionLocalOf {
    TianjiColors(
        accent = Color(0xFF8D7CFF),
        accentSoft = Color(0xFF8D7CFF).copy(alpha = 0.16f),
        monetSupported = false,
    )
}

private val TianjiTypography = Typography(
    bodySmall = TextStyle(fontSize = 12.sp, lineHeight = 18.sp),
    bodyMedium = TextStyle(fontSize = 14.sp, lineHeight = 21.sp),
    bodyLarge = TextStyle(fontSize = 16.sp, lineHeight = 24.sp),
    labelSmall = TextStyle(fontSize = 10.sp, lineHeight = 15.sp, fontWeight = FontWeight.Medium),
    labelMedium = TextStyle(fontSize = 12.sp, lineHeight = 17.sp, fontWeight = FontWeight.SemiBold),
    labelLarge = TextStyle(fontSize = 13.sp, lineHeight = 18.sp, fontWeight = FontWeight.SemiBold),
    titleSmall = TextStyle(fontSize = 15.sp, lineHeight = 20.sp, fontWeight = FontWeight.Bold),
    titleMedium = TextStyle(fontSize = 18.sp, lineHeight = 24.sp, fontWeight = FontWeight.Bold),
    titleLarge = TextStyle(fontSize = 22.sp, lineHeight = 29.sp, fontWeight = FontWeight.ExtraBold),
    headlineSmall = TextStyle(fontSize = 24.sp, lineHeight = 31.sp, fontWeight = FontWeight.ExtraBold),
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
    val isOled = mode == PaletteMode.OLED
    val accent = when (mode) {
        PaletteMode.GAME -> if (lottery == LotteryType.XYFT) {
            Color(0xFFFFA447)
        } else {
            Color(0xFF9382FF)
        }
        PaletteMode.MONET -> dynamic?.primary ?: PaletteMode.MONET.preview
        PaletteMode.AMBER -> Color(0xFFFFA447)
        PaletteMode.VIOLET -> Color(0xFF9382FF)
        PaletteMode.JADE -> Color(0xFF4EDBB3)
        PaletteMode.OLED -> dynamic?.primary ?: Color(0xFF9B8AFF)
    }

    val pageBase = if (isOled) Color.Black else Color(0xFF07080D)
    val pageSoftBase = if (isOled) Color(0xFF050505) else Color(0xFF0D1017)
    val surfaceBase = if (isOled) Color(0xFF090909) else Color(0xFF141720)
    val surfaceStrongBase = if (isOled) Color(0xFF101010) else Color(0xFF1A1D27)

    val palette = TianjiColors(
        page = if (isOled) pageBase else lerp(pageBase, accent, 0.018f),
        pageSoft = if (isOled) pageSoftBase else lerp(pageSoftBase, accent, 0.030f),
        surface = lerp(surfaceBase, accent, if (isOled) 0.018f else 0.040f).copy(alpha = 0.98f),
        surfaceStrong = lerp(
            surfaceStrongBase,
            accent,
            if (isOled) 0.025f else 0.052f,
        ).copy(alpha = 0.99f),
        surfaceSoft = accent.copy(alpha = if (isOled) 0.035f else 0.045f),
        glass = lerp(surfaceBase, accent, if (isOled) 0.02f else 0.042f)
            .copy(alpha = if (isOled) 0.96f else 0.92f),
        glassStrong = accent.copy(alpha = if (isOled) 0.065f else 0.075f),
        header = lerp(pageBase, accent, if (isOled) 0.015f else 0.022f)
            .copy(alpha = if (isOled) 0.985f else 0.965f),
        navSurface = lerp(surfaceStrongBase, accent, if (isOled) 0.025f else 0.052f)
            .copy(alpha = if (isOled) 0.99f else 0.97f),
        line = (dynamic?.outlineVariant ?: Color.White).copy(alpha = if (isOled) 0.10f else 0.085f),
        lineStrong = (dynamic?.outline ?: Color.White).copy(alpha = if (isOled) 0.17f else 0.14f),
        text = dynamic?.onBackground ?: Color(0xFFF7F8FB),
        textSoft = dynamic?.onSurfaceVariant ?: Color(0xFFD1D4DD),
        textDim = lerp(
            dynamic?.onSurfaceVariant ?: Color(0xFF9299A9),
            pageBase,
            0.12f,
        ),
        accent = accent,
        accentSoft = accent.copy(alpha = if (isOled) 0.15f else 0.18f),
        violet = dynamic?.tertiary ?: Color(0xFF9382FF),
        green = dynamic?.secondary ?: Color(0xFF62DDB8),
        amber = Color(0xFFFFBD5A),
        monetSupported = Build.VERSION.SDK_INT >= Build.VERSION_CODES.S,
        isOled = isOled,
    )

    val scheme = darkColorScheme(
        primary = accent,
        onPrimary = Color.White,
        primaryContainer = accent.copy(alpha = 0.24f),
        onPrimaryContainer = palette.text,
        secondary = palette.green,
        onSecondary = Color(0xFF032019),
        tertiary = palette.violet,
        background = palette.page,
        onBackground = palette.text,
        surface = palette.surface,
        onSurface = palette.text,
        surfaceVariant = palette.surfaceStrong,
        onSurfaceVariant = palette.textSoft,
        outline = palette.lineStrong,
        outlineVariant = palette.line,
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
