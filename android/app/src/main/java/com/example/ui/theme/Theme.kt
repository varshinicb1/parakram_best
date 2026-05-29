package com.example.ui.theme

import android.os.Build
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.dynamicDarkColorScheme
import androidx.compose.material3.dynamicLightColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext

private val DarkColorScheme = DarkColorSchemeColors

private val LightColorScheme = LightColorSchemeColors

@Composable
fun MyApplicationTheme(
  darkTheme: Boolean = true,
  dynamicColor: Boolean = false, // Let's use our custom color scheme consistently
  content: @Composable () -> Unit,
) {
  val colorScheme = if (darkTheme) DarkColorScheme else LightColorScheme

  MaterialTheme(colorScheme = colorScheme, typography = Typography, content = content)
}

object TinkrTheme {
    val cardBg: Color @Composable get() = MaterialTheme.colorScheme.surface
    val headerBg: Color @Composable get() = MaterialTheme.colorScheme.surfaceVariant
    val textPrimary: Color @Composable get() = MaterialTheme.colorScheme.onSurface
    val textSecondary: Color @Composable get() = MaterialTheme.colorScheme.onSurfaceVariant
    val dividerColor: Color @Composable get() = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.08f)
    val rootBg: Color @Composable get() = MaterialTheme.colorScheme.background
}
