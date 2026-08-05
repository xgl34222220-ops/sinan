package com.tianji.probabilitylab.nativev4.ui.theme

import android.os.Build
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.dynamicDarkColorScheme
import androidx.compose.material3.dynamicLightColorScheme
import androidx.compose.material3.lightColorScheme
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
    OLED("纯黑（旧版兼容）", Color(0xFF0A0A0A)),
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
    val green: Color = Color(0xFF36B98B),
    val red: Color = Color(0xFFE45667),
    val amber: Color = Color(0xFFE79B22),
    val violet: Color = Color(0xFF8D7CFF),
    val accent: Color,
    val accentSoft: Color,
    val monetSupported: Boolean,
    val isOled: Boolean = false,
    val isDark: Boolean = true,
)

val LocalTianjiColors = staticCompositionLocalOf {
    TianjiColors(
        accent = Color(0xFF8D7CFF),
        accentSoft = Color(0xFF8D7CFF).copy(alpha = 0.16f),
        monetSupported = false,
    )
}

private val TianjiTypography = Typography(
    bodySmall = TextStyle(fontSize = 13.sp, lineHeight = 19.sp),
    bodyMedium = TextStyle(fontSize = 15.sp, lineHeight = 22.sp),
    bodyLarge = TextStyle(fontSize = 16.sp, lineHeight = 24.sp),
    labelSmall = TextStyle(fontSize = 11.sp, lineHeight = 16.sp, fontWeight = FontWeight.Medium),
    labelMedium = TextStyle(fontSize = 13.sp, lineHeight = 18.sp, fontWeight = FontWeight.SemiBold),
    labelLarge = TextStyle(fontSize = 13.sp, lineHeight = 18.sp, fontWeight = FontWeight.SemiBold),
    titleSmall = TextStyle(fontSize = 16.sp, lineHeight = 21.sp, fontWeight = FontWeight.Bold),
    titleMedium = TextStyle(fontSize = 18.sp, lineHeight = 24.sp, fontWeight = FontWeight.Bold),
    titleLarge = TextStyle(fontSize = 22.sp, lineHeight = 29.sp, fontWeight = FontWeight.ExtraBold),
    headlineSmall = TextStyle(fontSize = 24.sp, lineHeight = 31.sp, fontWeight = FontWeight.ExtraBold),
)

@Composable
fun TianjiTheme(
    mode: PaletteMode,
    lottery: LotteryType,
    appearance: AppearanceMode = AppearanceMode.SYSTEM,
    content: @Composable () -> Unit,
) {
    val context = LocalContext.current
    val systemDark = isSystemInDarkTheme()
    val legacyOled = mode == PaletteMode.OLED
    val isOled = appearance == AppearanceMode.OLED || legacyOled
    val isDark = when (appearance) {
        AppearanceMode.SYSTEM -> systemDark
        AppearanceMode.LIGHT -> false
        AppearanceMode.DARK, AppearanceMode.OLED -> true
    } || legacyOled

    val dynamic = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
        if (isDark) dynamicDarkColorScheme(context) else dynamicLightColorScheme(context)
    } else {
        null
    }

    val accent = when (mode) {
        PaletteMode.GAME -> if (lottery == LotteryType.XYFT) {
            Color(0xFFFF9B3F)
        } else {
            Color(0xFF7C68F2)
        }
        PaletteMode.MONET -> dynamic?.primary ?: Color(0xFF7C68F2)
        PaletteMode.AMBER -> Color(0xFFE99220)
        PaletteMode.VIOLET -> Color(0xFF7C68F2)
        PaletteMode.JADE -> Color(0xFF20A97D)
        PaletteMode.OLED -> dynamic?.primary ?: Color(0xFF8F7CFF)
    }

    val base = if (isDark) {
        ThemeBases(
            page = if (isOled) Color.Black else Color(0xFF0B0D13),
            pageSoft = if (isOled) Color(0xFF050505) else Color(0xFF111520),
            surface = if (isOled) Color(0xFF090909) else Color(0xFF171B25),
            surfaceStrong = if (isOled) Color(0xFF111111) else Color(0xFF1E2330),
            text = Color(0xFFF7F8FB),
            textSoft = Color(0xFFD7DBE5),
            textDim = Color(0xFF969EAE),
            line = Color.White.copy(alpha = if (isOled) 0.11f else 0.085f),
            lineStrong = Color.White.copy(alpha = if (isOled) 0.18f else 0.14f),
        )
    } else {
        ThemeBases(
            page = Color(0xFFF4F6FB),
            pageSoft = Color(0xFFEBEFF8),
            surface = Color(0xFFFDFEFF),
            surfaceStrong = Color(0xFFF4F6FB),
            text = Color(0xFF171A23),
            textSoft = Color(0xFF3B4251),
            textDim = Color(0xFF737C8F),
            line = Color(0xFF202739).copy(alpha = 0.09f),
            lineStrong = Color(0xFF202739).copy(alpha = 0.15f),
        )
    }

    val tintAmount = if (isDark) 0.038f else 0.022f
    val palette = TianjiColors(
        page = if (isOled) base.page else lerp(base.page, accent, tintAmount * 0.55f),
        pageSoft = if (isOled) base.pageSoft else lerp(base.pageSoft, accent, tintAmount),
        surface = lerp(base.surface, accent, if (isOled) 0.016f else tintAmount)
            .copy(alpha = if (isDark) 0.985f else 1f),
        surfaceStrong = lerp(base.surfaceStrong, accent, if (isOled) 0.022f else tintAmount * 1.25f)
            .copy(alpha = 1f),
        surfaceSoft = accent.copy(alpha = if (isDark) 0.055f else 0.075f),
        glass = lerp(base.surface, accent, if (isDark) 0.04f else 0.025f)
            .copy(alpha = if (isDark) 0.93f else 0.97f),
        glassStrong = accent.copy(alpha = if (isDark) 0.075f else 0.10f),
        header = lerp(base.page, accent, if (isDark) 0.022f else 0.012f)
            .copy(alpha = if (isDark) 0.97f else 0.99f),
        navSurface = lerp(base.surface, accent, if (isDark) 0.05f else 0.025f)
            .copy(alpha = if (isDark) 0.985f else 0.99f),
        line = dynamic?.outlineVariant?.copy(alpha = if (isDark) 0.11f else 0.13f) ?: base.line,
        lineStrong = dynamic?.outline?.copy(alpha = if (isDark) 0.19f else 0.22f) ?: base.lineStrong,
        text = dynamic?.onBackground ?: base.text,
        textSoft = dynamic?.onSurfaceVariant ?: base.textSoft,
        textDim = lerp(dynamic?.onSurfaceVariant ?: base.textDim, base.page, if (isDark) 0.10f else 0.05f),
        accent = accent,
        accentSoft = accent.copy(alpha = if (isDark) 0.17f else 0.12f),
        violet = dynamic?.tertiary ?: Color(0xFF7C68F2),
        green = dynamic?.secondary ?: if (isDark) Color(0xFF5BD8AB) else Color(0xFF16865F),
        amber = if (isDark) Color(0xFFF1B354) else Color(0xFFA96800),
        red = if (isDark) Color(0xFFFF7D8C) else Color(0xFFC43A52),
        monetSupported = Build.VERSION.SDK_INT >= Build.VERSION_CODES.S,
        isOled = isOled,
        isDark = isDark,
    )

    val scheme = if (isDark) {
        darkColorScheme(
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
    } else {
        lightColorScheme(
            primary = accent,
            onPrimary = Color.White,
            primaryContainer = accent.copy(alpha = 0.14f),
            onPrimaryContainer = palette.text,
            secondary = palette.green,
            onSecondary = Color.White,
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
    }

    androidx.compose.runtime.CompositionLocalProvider(LocalTianjiColors provides palette) {
        MaterialTheme(
            colorScheme = scheme,
            typography = TianjiTypography,
            content = content,
        )
    }
}

private data class ThemeBases(
    val page: Color,
    val pageSoft: Color,
    val surface: Color,
    val surfaceStrong: Color,
    val text: Color,
    val textSoft: Color,
    val textDim: Color,
    val line: Color,
    val lineStrong: Color,
)
