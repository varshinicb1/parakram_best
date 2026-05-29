package com.example.ui.theme

import androidx.compose.ui.graphics.Color

val TinkrOrange = Color(0xFFFF5C22) // Saffron Core
val TinkrOrangeGlow = Color(0xFFFF7844) // Saffron Glow
val TinkrSlateDarkBg = Color(0xFF090A0C) // Space Carbon deep background
val TinkrCardDark = Color(0xFF16181D) // Graphite Space Dark Card
val TinkrCardHeader = Color(0xFF21242C) // Graphite Deep Header Toolbar
val TinkrGreen = Color(0xFF00E676) // Active Safe Signal
val TinkrBlue = Color(0xFF00E5FF) // Volt Electric Blue Signal
val TinkrYellow = Color(0xFFFFCA28) // Gilded Gold Accent
val TinkrPurple = Color(0xFF9575CD) // Purple telemetry Accent

val DarkColorSchemeColors = androidx.compose.material3.darkColorScheme(
    primary = TinkrOrange,
    onPrimary = Color.White,
    secondary = TinkrBlue,
    onSecondary = Color.White,
    tertiary = TinkrGreen,
    background = TinkrSlateDarkBg,
    surface = TinkrCardDark,
    surfaceVariant = TinkrCardHeader,
    onBackground = Color.White,
    onSurface = Color.White,
    onSurfaceVariant = Color.White.copy(alpha = 0.6f)
)

val LightColorSchemeColors = androidx.compose.material3.lightColorScheme(
    primary = TinkrOrange,
    onPrimary = Color.White,
    secondary = Color(0xFF0097A7), // Teal
    onSecondary = Color.White,
    tertiary = Color(0xFF2E7D32), // Green
    background = Color(0xFFF4F6FC), // Sleek off-white light cloud background
    surface = Color(0xFFFFFFFF), // Pure crisp white for cards
    surfaceVariant = Color(0xFFE9EBF2), // Light slate header / secondary panels
    onBackground = Color(0xFF13141C), // Deep graphite charcoal text
    onSurface = Color(0xFF13141C), // Deep graphite charcoal card text
    onSurfaceVariant = Color(0xFF5C6173) // High contrast grey secondary subtext
)
