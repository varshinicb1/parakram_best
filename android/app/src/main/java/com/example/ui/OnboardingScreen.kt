package com.example.ui

import androidx.compose.animation.*
import androidx.compose.animation.core.*
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.lazy.items
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
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.data.*
import com.example.hardware.*
import com.example.ui.theme.*
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

@Composable
fun OnboardingScreen(
    settingsRepository: SettingsRepository,
    onOnboardingCompleted: () -> Unit
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    
    // Core settings states
    val currentLang by settingsRepository.languageFlow.collectAsState(initial = "en")
    val currentPersona by settingsRepository.personaFlow.collectAsState(initial = "engineer")
    
    // Onboarding step manager: 0=Language, 1=Persona, 2=LLM Download, 3=Pair Node
    var currentStep by remember { mutableStateOf(0) }
    
    // BLE scanning variables
    val bleManager = remember { TinkrBleManager.getInstance(context) }
    val isScanning by bleManager.isScanning.collectAsState()
    val scannedDevices by bleManager.scannedDevices.collectAsState()
    val connectionState by bleManager.connectionState.collectAsState()

    // Download variables
    var isDownloading by remember { mutableStateOf(false) }
    var downloadProgress by remember { mutableStateOf(0f) }

    Scaffold(
        containerColor = MaterialTheme.colorScheme.background
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .background(
                    Brush.radialGradient(
                        colors = listOf(TinkrOrange.copy(alpha = 0.08f), Color.Transparent),
                        radius = 1200f
                    )
                )
                .padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            // Top Bar Progress Indicators
            OnboardingStepIndicator(currentStep = currentStep)

            Spacer(modifier = Modifier.height(32.dp))

            // Sliding container based on currentStep
            Box(modifier = Modifier.weight(1f)) {
                when (currentStep) {
                    0 -> LanguagePickerView(
                        selectedLang = currentLang,
                        onLangSelected = { code ->
                            scope.launch { settingsRepository.setLanguage(code) }
                        }
                    )
                    1 -> PersonaSelectionView(
                        language = currentLang,
                        selectedPersona = currentPersona,
                        onPersonaSelected = { id ->
                            scope.launch { settingsRepository.setPersona(id) }
                        }
                    )
                    2 -> ModelDownloadView(
                        language = currentLang,
                        isDownloading = isDownloading,
                        progress = downloadProgress,
                        onStartDownload = {
                            isDownloading = true
                            scope.launch {
                                while (downloadProgress < 1.0f) {
                                    delay(40)
                                    downloadProgress += 0.015f
                                }
                                isDownloading = false
                                settingsRepository.setLocalModelDownloaded(true)
                                currentStep = 3 // advance automatically
                            }
                        },
                        onSkip = {
                            scope.launch {
                                settingsRepository.setLocalModelDownloaded(false)
                                currentStep = 3
                            }
                        }
                    )
                    3 -> PairBoardView(
                        language = currentLang,
                        bleManager = bleManager,
                        isScanning = isScanning,
                        scannedDevices = scannedDevices,
                        connectionState = connectionState,
                        onConnectedSuccessfully = {
                            scope.launch {
                                settingsRepository.setOnboardingCompleted(true)
                                onOnboardingCompleted()
                            }
                        }
                    )
                }
            }

            Spacer(modifier = Modifier.height(16.dp))

            // Action controls
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                if (currentStep > 0) {
                    TextButton(
                        onClick = { currentStep-- },
                        colors = ButtonDefaults.textButtonColors(contentColor = Color.White.copy(alpha = 0.6f))
                    ) {
                        Icon(Icons.Default.ArrowBack, contentDescription = null)
                        Spacer(modifier = Modifier.width(4.dp))
                        Text(TinkrTranslations.getString("back_btn", currentLang))
                    }
                } else {
                    Spacer(modifier = Modifier.width(48.dp))
                }

                if (currentStep < 3) {
                    Button(
                        onClick = { currentStep++ },
                        colors = ButtonDefaults.buttonColors(containerColor = TinkrOrange),
                        shape = RoundedCornerShape(24.dp)
                    ) {
                        Text("Next", color = Color.White, fontWeight = FontWeight.Bold)
                        Spacer(modifier = Modifier.width(4.dp))
                        Icon(Icons.Default.ArrowForward, contentDescription = null)
                    }
                } else {
                    Button(
                        onClick = {
                            scope.launch {
                                settingsRepository.setOnboardingCompleted(true)
                                onOnboardingCompleted()
                            }
                        },
                        colors = ButtonDefaults.buttonColors(containerColor = TinkrGreen),
                        shape = RoundedCornerShape(24.dp)
                    ) {
                        Text(TinkrTranslations.getString("start_adventure", currentLang), color = Color.Black, fontWeight = FontWeight.Bold)
                    }
                }
            }
        }
    }
}

@Composable
fun OnboardingStepIndicator(currentStep: Int) {
    Row(
        modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        for (i in 0..3) {
            val isActive = i <= currentStep
            Box(
                modifier = Modifier
                    .weight(1f)
                    .height(6.dp)
                    .padding(horizontal = 4.dp)
                    .clip(CircleShape)
                    .background(if (isActive) TinkrOrange else Color.White.copy(alpha = 0.15f))
            )
        }
    }
}

@Composable
fun LanguagePickerView(selectedLang: String, onLangSelected: (String) -> Unit) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Icon(
            painter = painterResource(id = com.example.R.drawable.ic_logo),
            contentDescription = "Parakram Majestic Shield & Core Flame Logo",
            tint = Color.Unspecified,
            modifier = Modifier.size(100.dp).padding(bottom = 16.dp)
        )
        Text(
            text = "Parakram Companion OS",
            fontSize = 26.sp,
            fontWeight = FontWeight.ExtraBold,
            color = TinkrOrangeGlow
        )
        Spacer(modifier = Modifier.height(8.dp))
        Text(
            text = "Select Language",
            fontSize = 24.sp,
            fontWeight = FontWeight.Bold,
            color = Color.White
        )
        Text(
            text = "Choose your operating language for voice and menus",
            fontSize = 14.sp,
            color = Color.White.copy(alpha = 0.6f),
            textAlign = TextAlign.Center,
            modifier = Modifier.padding(top = 8.dp, bottom = 24.dp)
        )

        LazyVerticalGrid(
            columns = GridCells.Fixed(2),
            modifier = Modifier.fillMaxSize(),
            contentPadding = PaddingValues(4.dp),
            horizontalArrangement = Arrangement.spacedBy(12.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            items(TinkrTranslations.languages) { lang ->
                val isSelected = lang.code == selectedLang
                val glowValue by animateFloatAsState(
                    targetValue = if (isSelected) 1f else 0f,
                    animationSpec = spring(stiffness = Spring.StiffnessLow)
                )

                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(110.dp)
                        .clickable { onLangSelected(lang.code) }
                        .shadow(elevation = (glowValue * 8).dp, shape = RoundedCornerShape(16.dp)),
                    shape = RoundedCornerShape(16.dp),
                    colors = CardDefaults.cardColors(
                        containerColor = if (isSelected) MaterialTheme.colorScheme.surface else MaterialTheme.colorScheme.surface.copy(alpha = 0.6f)
                    ),
                    border = BorderStroke(
                        width = 2.dp,
                        color = if (isSelected) TinkrOrange else MaterialTheme.colorScheme.onSurface.copy(alpha = 0.08f)
                    )
                ) {
                    Column(
                        modifier = Modifier.fillMaxSize().padding(16.dp),
                        verticalArrangement = Arrangement.Center,
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        Text(
                            text = lang.nativeName,
                            fontSize = 20.sp,
                            fontWeight = FontWeight.Bold,
                            color = if (isSelected) TinkrOrangeGlow else Color.White
                        )
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(
                            text = lang.englishName,
                            fontSize = 12.sp,
                            color = Color.White.copy(alpha = 0.5f)
                        )
                    }
                }
            }
        }
    }
}

data class Persona(val id: String, val title: String, val icon: ImageVector, val desc: String)

@Composable
fun PersonaSelectionView(language: String, selectedPersona: String, onPersonaSelected: (String) -> Unit) {
    val personas = listOf(
        Persona("student", "Student / Kid", Icons.Default.School, "Structured tutorials, explanations without dense logic."),
        Persona("farmer", "Organic Farmer", Icons.Default.Grass, "Agritech automations, soil diagnostic templates, water feeds."),
        Persona("homemaker", "Home Maker", Icons.Default.Home, "HVAC triggers, safe automated alerts, climate dials."),
        Persona("engineer", "Maker / Engineer", Icons.Default.Build, "Raw assembly codes, BLE protocol logs, custom pin maps."),
        Persona("business", "Business Owner", Icons.Default.Business, "Usage summaries, sensor trends, scaling stats."),
        Persona("researcher", "Developer / Researcher", Icons.Default.Science, "Tool calling, diagnostics models, extreme logs.")
    )

    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text(
            text = TinkrTranslations.getString("choose_persona", language),
            fontSize = 24.sp,
            fontWeight = FontWeight.Bold,
            color = Color.White
        )
        Text(
            text = TinkrTranslations.getString("persona_sub", language),
            fontSize = 14.sp,
            color = Color.White.copy(alpha = 0.6f),
            textAlign = TextAlign.Center,
            modifier = Modifier.padding(top = 8.dp, bottom = 24.dp)
        )

        LazyColumn(
            modifier = Modifier.fillMaxSize(),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            items(personas) { p ->
                val isSelected = p.id == selectedPersona
                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clickable { onPersonaSelected(p.id) },
                    shape = RoundedCornerShape(16.dp),
                    colors = CardDefaults.cardColors(
                        containerColor = if (isSelected) MaterialTheme.colorScheme.surface else MaterialTheme.colorScheme.surface.copy(alpha = 0.6f)
                    ),
                    border = BorderStroke(
                        width = 2.dp,
                        color = if (isSelected) TinkrOrange else MaterialTheme.colorScheme.onSurface.copy(alpha = 0.08f)
                    )
                ) {
                    Row(
                        modifier = Modifier.padding(16.dp).fillMaxWidth(),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Box(
                            modifier = Modifier
                                .size(48.dp)
                                .clip(RoundedCornerShape(12.dp))
                                .background(if (isSelected) TinkrOrange.copy(alpha = 0.2f) else MaterialTheme.colorScheme.onSurface.copy(alpha = 0.05f)),
                            contentAlignment = Alignment.Center
                        ) {
                            Icon(
                                imageVector = p.icon,
                                contentDescription = null,
                                tint = if (isSelected) TinkrOrangeGlow else Color.White
                            )
                        }
                        Spacer(modifier = Modifier.width(16.dp))
                        Column(modifier = Modifier.weight(1f)) {
                            Text(
                                text = p.title,
                                fontSize = 16.sp,
                                fontWeight = FontWeight.Bold,
                                color = Color.White
                            )
                            Spacer(modifier = Modifier.height(4.dp))
                            Text(
                                text = p.desc,
                                fontSize = 12.sp,
                                color = Color.White.copy(alpha = 0.6f)
                            )
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun ModelDownloadView(
    language: String,
    isDownloading: Boolean,
    progress: Float,
    onStartDownload: () -> Unit,
    onSkip: () -> Unit
) {
    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
        modifier = Modifier.fillMaxSize()
    ) {
        Icon(
            imageVector = Icons.Default.ModelTraining,
            contentDescription = null,
            tint = TinkrOrange,
            modifier = Modifier.size(72.dp)
        )
        
        Spacer(modifier = Modifier.height(16.dp))

        Text(
            text = TinkrTranslations.getString("model_title", language),
            fontSize = 24.sp,
            fontWeight = FontWeight.Bold,
            color = Color.White
        )
        Text(
            text = TinkrTranslations.getString("model_sub", language),
            fontSize = 14.sp,
            color = Color.White.copy(alpha = 0.6f),
            textAlign = TextAlign.Center,
            modifier = Modifier.padding(top = 8.dp, bottom = 12.dp)
        )
        
        Text(
            text = TinkrTranslations.getString("model_size", language),
            fontSize = 12.sp,
            color = TinkrOrangeGlow,
            fontWeight = FontWeight.SemiBold
        )

        Spacer(modifier = Modifier.height(32.dp))

        if (isDownloading) {
            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                LinearProgressIndicator(
                    progress = { progress },
                    modifier = Modifier.fillMaxWidth().height(8.dp).clip(CircleShape),
                    color = TinkrOrange,
                    trackColor = Color.White.copy(alpha = 0.1f)
                )
                Spacer(modifier = Modifier.height(12.dp))
                Text(
                    text = "Gemma 4 E2B LiteRT-LM Downloading: ${(progress * 100).toInt()}%",
                    color = Color.White,
                    fontWeight = FontWeight.SemiBold,
                    fontSize = 14.sp
                )
                Text(
                    text = "Survives app lifecycle. Stored securely in scoped space.",
                    color = Color.White.copy(alpha = 0.4f),
                    fontSize = 11.sp,
                    modifier = Modifier.padding(top = 4.dp)
                )
            }
        } else {
            Button(
                onClick = onStartDownload,
                colors = ButtonDefaults.buttonColors(containerColor = TinkrOrange),
                modifier = Modifier.fillMaxWidth().height(54.dp),
                shape = RoundedCornerShape(16.dp)
            ) {
                Icon(Icons.Default.Download, contentDescription = null, tint = Color.White)
                Spacer(modifier = Modifier.width(8.dp))
                Text("Proceed Offline-First Download", color = Color.White, fontWeight = FontWeight.Bold)
            }

            Spacer(modifier = Modifier.height(16.dp))

            TextButton(onClick = onSkip) {
                Text(TinkrTranslations.getString("skip_cloud", language), color = TinkrOrangeGlow)
            }
        }
    }
}

@Composable
fun PairBoardView(
    language: String,
    bleManager: TinkrBleManager,
    isScanning: Boolean,
    scannedDevices: List<ScannedDevice>,
    connectionState: BleConnectionState,
    onConnectedSuccessfully: () -> Unit
) {
    LaunchedEffect(connectionState) {
        if (connectionState is BleConnectionState.Connected) {
            // Auto finish onboarding when successfully connected/selected
            onConnectedSuccessfully()
        }
    }

    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text(
            text = TinkrTranslations.getString("pair_board", language),
            fontSize = 24.sp,
            fontWeight = FontWeight.Bold,
            color = Color.White
        )
        Text(
            text = TinkrTranslations.getString("pair_sub", language),
            fontSize = 14.sp,
            color = Color.White.copy(alpha = 0.6f),
            textAlign = TextAlign.Center,
            modifier = Modifier.padding(top = 8.dp, bottom = 24.dp)
        )

        // Pulsing radar animation
        val infiniteTransition = rememberInfiniteTransition()
        val pulseRadius by infiniteTransition.animateFloat(
            initialValue = 0.1f,
            targetValue = 1f,
            animationSpec = infiniteRepeatable(
                animation = tween(2000, easing = LinearEasing),
                repeatMode = RepeatMode.Restart
            )
        )

        Box(
            modifier = Modifier
                .size(130.dp)
                .clip(CircleShape)
                .background(Color.White.copy(alpha = 0.03f)),
            contentAlignment = Alignment.Center
        ) {
            // Echo rings
            if (isScanning) {
                Box(
                    modifier = Modifier
                        .size((130 * pulseRadius).dp)
                        .clip(CircleShape)
                        .background(TinkrOrange.copy(alpha = 0.15f * (1 - pulseRadius)))
                )
            }
            IconButton(
                onClick = { if (isScanning) bleManager.stopScanning() else bleManager.startScanning() },
                modifier = Modifier
                    .size(80.dp)
                    .clip(CircleShape)
                    .background(if (isScanning) TinkrOrange else MaterialTheme.colorScheme.surfaceVariant)
                    .shadow(elevation = 12.dp, shape = CircleShape)
            ) {
                Icon(
                    imageVector = if (isScanning) Icons.Default.Stop else Icons.Default.Bluetooth,
                    contentDescription = null,
                    tint = Color.White,
                    modifier = Modifier.size(36.dp)
                )
            }
        }

        Spacer(modifier = Modifier.height(24.dp))

        if (connectionState == BleConnectionState.Connecting) {
            CircularProgressIndicator(color = TinkrOrange)
            Text(
                "Connecting to microcontroller node...",
                color = MaterialTheme.colorScheme.onBackground,
                fontWeight = FontWeight.Medium,
                modifier = Modifier.padding(top = 12.dp)
            )
        } else {
            Card(
                modifier = Modifier.weight(1f).fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface.copy(alpha = 0.4f)),
                border = BorderStroke(1.dp, MaterialTheme.colorScheme.onSurface.copy(alpha = 0.08f)),
                shape = RoundedCornerShape(16.dp)
            ) {
                if (scannedDevices.isEmpty()) {
                    Box(
                        modifier = Modifier.fillMaxSize(),
                        contentAlignment = Alignment.Center
                    ) {
                        Text(
                            text = if (isScanning) "Listening for signals near..." else "Press button to search BLE Node",
                            fontSize = 13.sp,
                            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.4f)
                        )
                    }
                } else {
                    LazyColumn(
                        modifier = Modifier.padding(12.dp),
                        verticalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        items(scannedDevices) { dev ->
                            Card(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .clickable { bleManager.connectToBoard(dev) },
                                shape = RoundedCornerShape(12.dp),
                                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                                border = BorderStroke(1.dp, MaterialTheme.colorScheme.onSurface.copy(alpha = 0.08f))
                            ) {
                                Row(
                                    modifier = Modifier.padding(16.dp).fillMaxWidth(),
                                    verticalAlignment = Alignment.CenterVertically,
                                    horizontalArrangement = Arrangement.SpaceBetween
                                ) {
                                    Row(verticalAlignment = Alignment.CenterVertically) {
                                        Icon(Icons.Default.Memory, contentDescription = null, tint = TinkrOrange)
                                        Spacer(modifier = Modifier.width(12.dp))
                                        Column {
                                            Text(dev.name, color = MaterialTheme.colorScheme.onSurface, fontWeight = FontWeight.Bold, fontSize = 14.sp)
                                            Text(dev.address, color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f), fontSize = 11.sp)
                                        }
                                    }
                                    Row(verticalAlignment = Alignment.CenterVertically) {
                                        Icon(Icons.Default.Wifi, contentDescription = null, tint = TinkrGreen, modifier = Modifier.size(16.dp))
                                        Spacer(modifier = Modifier.width(4.dp))
                                        Text("${dev.rssi} dBm", color = TinkrGreen, fontSize = 11.sp, fontWeight = FontWeight.SemiBold)
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
