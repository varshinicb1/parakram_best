package com.example

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.animation.*
import androidx.compose.animation.core.*
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.data.SettingsRepository
import com.example.ui.*
import com.example.ui.theme.*

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            val context = LocalContext.current
            val settingsRepository = remember { SettingsRepository(context) }
            val currentIsDarkTheme by settingsRepository.isDarkThemeFlow.collectAsState(initial = true)
            
            MyApplicationTheme(darkTheme = currentIsDarkTheme) {
                TinkrMainApp(settingsRepository = settingsRepository, currentIsDarkTheme = currentIsDarkTheme)
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun TinkrMainApp(
    settingsRepository: SettingsRepository,
    currentIsDarkTheme: Boolean
) {
    val context = LocalContext.current
    
    val currentLang by settingsRepository.languageFlow.collectAsState(initial = "en")
    val isOnboardingFinished by settingsRepository.isOnboardingCompletedFlow.collectAsState(initial = false)

    var currentSelectedTab by remember { mutableStateOf("home") }
    var showAICompanionSheet by remember { mutableStateOf(false) }

    if (!isOnboardingFinished) {
        OnboardingScreen(
            settingsRepository = settingsRepository,
            onOnboardingCompleted = {
                // Done on finish triggers is propagated automatically from repo flow
            }
        )
    } else {
        Scaffold(
            containerColor = MaterialTheme.colorScheme.background,
            bottomBar = {
                BottomAppBar(
                    containerColor = MaterialTheme.colorScheme.surface,
                    tonalElevation = 10.dp,
                    contentPadding = PaddingValues(horizontal = 8.dp),
                    modifier = Modifier
                        .background(MaterialTheme.colorScheme.surface)
                        .clip(RoundedCornerShape(topStart = 24.dp, topEnd = 24.dp))
                ) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceAround,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        // Home Tab
                        BottomBarItem(
                            icon = Icons.Default.Home,
                            label = TinkrTranslations.getString("home_tab", currentLang),
                            isActive = currentSelectedTab == "home",
                            onClick = { currentSelectedTab = "home" }
                        )

                        // Build Tab
                        BottomBarItem(
                            icon = Icons.Default.Build,
                            label = TinkrTranslations.getString("build_tab", currentLang),
                            isActive = currentSelectedTab == "build",
                            onClick = { currentSelectedTab = "build" }
                        )

                        // Placeholder for Center Orb
                        Spacer(modifier = Modifier.width(56.dp))

                        // Drivers Tab
                        BottomBarItem(
                            icon = Icons.Default.Memory,
                            label = TinkrTranslations.getString("drivers_tab", currentLang),
                            isActive = currentSelectedTab == "drivers",
                            onClick = { currentSelectedTab = "drivers" }
                        )

                        // Projects Tab
                        BottomBarItem(
                            icon = Icons.Default.FolderOpen,
                            label = TinkrTranslations.getString("projects_tab", currentLang),
                            isActive = currentSelectedTab == "projects",
                            onClick = { currentSelectedTab = "projects" }
                        )
                    }
                }
            },
            floatingActionButton = {
                // center AI pulsing glowing Orange Orb FAB
                Box(
                    modifier = Modifier.offset(y = 50.dp),
                    contentAlignment = Alignment.Center
                ) {
                    // Pulsing Glow aura
                    val infiniteTransition = rememberInfiniteTransition()
                    val pulseScale by infiniteTransition.animateFloat(
                        initialValue = 1f,
                        targetValue = 1.25f,
                        animationSpec = infiniteRepeatable(
                            animation = tween(1800, easing = EaseInOutBack),
                            repeatMode = RepeatMode.Reverse
                        )
                    )

                    Box(
                        modifier = Modifier
                            .size((64 * pulseScale).dp)
                            .shadow(24.dp, shape = CircleShape)
                            .clip(CircleShape)
                            .background(
                                Brush.radialGradient(
                                    colors = listOf(TinkrOrangeGlow.copy(alpha = 0.45f), Color.Transparent)
                                )
                            )
                    )

                    IconButton(
                        onClick = { showAICompanionSheet = true },
                        modifier = Modifier
                            .size(60.dp)
                            .clip(CircleShape)
                            .background(
                                Brush.linearGradient(
                                    colors = listOf(TinkrOrange, TinkrOrangeGlow)
                                )
                            )
                            .border(BorderStroke(1.dp, Color.White.copy(alpha = 0.2f)), CircleShape)
                            .shadow(elevation = 12.dp, shape = CircleShape)
                    ) {
                        Icon(
                            imageVector = Icons.Default.OfflineBolt,
                            contentDescription = "Pulsing AI Orb",
                            tint = Color.White,
                            modifier = Modifier.size(32.dp)
                        )
                    }
                }
            },
            floatingActionButtonPosition = FabPosition.Center
        ) { innerPadding ->
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(innerPadding)
            ) {
                // Switch subviews
                AnimatedContent(
                    targetState = currentSelectedTab,
                    transitionSpec = {
                        fadeIn(animationSpec = tween(220)) togetherWith fadeOut(animationSpec = tween(220))
                    }
                ) { targetTab ->
                    when (targetTab) {
                        "home" -> HomeScreen(settingsRepository = settingsRepository, onNavigateToTab = { currentSelectedTab = it })
                        "build" -> BuildScreen(settingsRepository = settingsRepository)
                        "drivers" -> DriversScreen(lang = currentLang)
                        "projects" -> ProjectsScreen(settingsRepository = settingsRepository)
                    }
                }

                // AI Sliding modal Sheet
                if (showAICompanionSheet) {
                    ModalBottomSheet(
                        onDismissRequest = { showAICompanionSheet = false },
                        sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true),
                        containerColor = MaterialTheme.colorScheme.surface,
                        shape = RoundedCornerShape(topStart = 28.dp, topEnd = 28.dp)
                    ) {
                        AISheet(
                            language = currentLang,
                            onDismiss = { showAICompanionSheet = false }
                        )
                    }
                }
            }
        }
    }
}

@Composable
fun BottomBarItem(
    icon: ImageVector,
    label: String,
    isActive: Boolean,
    onClick: () -> Unit
) {
    Column(
        modifier = Modifier
            .clickable { onClick() }
            .padding(vertical = 4.dp, horizontal = 12.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        val scale by animateFloatAsState(targetValue = if (isActive) 1.2f else 1f)
        val color = if (isActive) TinkrOrangeGlow else MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f)
        
        Icon(
            imageVector = icon,
            contentDescription = label,
            tint = color,
            modifier = Modifier.size((24 * scale).dp)
        )
        Spacer(modifier = Modifier.height(4.dp))
        Text(
            text = label,
            color = color,
            fontSize = 9.sp,
            fontWeight = if (isActive) FontWeight.Bold else FontWeight.Normal
        )
    }
}
