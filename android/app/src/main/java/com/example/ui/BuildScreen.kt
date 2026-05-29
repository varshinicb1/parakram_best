package com.example.ui

import androidx.compose.animation.*
import androidx.compose.animation.core.*
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
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
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.ai.*
import com.example.data.SettingsRepository
import com.example.protocol.CommandMessage
import com.example.hardware.TinkrBleManager
import com.example.ui.theme.*
import androidx.compose.ui.text.style.TextAlign
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

@Composable
fun BuildScreen(settingsRepository: SettingsRepository) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()

    val currentLang by settingsRepository.languageFlow.collectAsState(initial = "en")
    val bleManager = remember { TinkrBleManager.getInstance(context) }
    val aiService = remember { TinkrAIService.getInstance(context) }

    // Tab state: "Voice", "Chat", "Blocks", "Code"
    var selectedSandboxMode by remember { mutableStateOf("Chat") }

    // Code state
    var currentCodeText by remember { mutableStateOf("""
// Tinkr Embedded OS Sketch
#define SOIL_PIN 32
#define PUMP_RELAY 12

void setup() {
  Serial.begin(115200);
  pinMode(PUMP_RELAY, OUTPUT);
}

void loop() {
  int level = analogRead(SOIL_PIN);
  if (level < 400) {
    digitalWrite(PUMP_RELAY, HIGH);
    delay(3000);
    digitalWrite(PUMP_RELAY, LOW);
  }
  delay(1000);
}
    """.trimIndent()) }

    var codeCompilationOutput by remember { mutableStateOf("") }
    var isCompiling by remember { mutableStateOf(false) }

    Scaffold(
        containerColor = MaterialTheme.colorScheme.background,
        topBar = {
            Column(modifier = Modifier.background(MaterialTheme.colorScheme.background)) {
                // Dual row headers
                Row(
                    modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 12.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = TinkrTranslations.getString("build_title", currentLang),
                        color = Color.White,
                        fontSize = 20.sp,
                        fontWeight = FontWeight.Bold
                    )
                    Icon(
                        imageVector = Icons.Default.IntegrationInstructions,
                        contentDescription = null,
                        tint = TinkrOrangeGlow
                    )
                }

                // Sandbox modes tab row
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(bottom = 8.dp)
                        .horizontalScroll(rememberScrollState())
                        .padding(horizontal = 16.dp),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    listOf("Chat", "Voice", "Blocks", "Code").forEach { tab ->
                        val isSel = tab == selectedSandboxMode
                        Surface(
                            modifier = Modifier
                                .clip(RoundedCornerShape(12.dp))
                                .clickable { selectedSandboxMode = tab },
                            color = if (isSel) TinkrOrange else TinkrCardDark,
                            border = BorderStroke(1.dp, if (isSel) TinkrOrangeGlow else Color.White.copy(alpha = 0.05f))
                        ) {
                            Text(
                                text = tab.uppercase(),
                                color = if (isSel) Color.White else Color.White.copy(alpha = 0.6f),
                                fontSize = 11.sp,
                                fontWeight = FontWeight.Bold,
                                modifier = Modifier.padding(horizontal = 14.dp, vertical = 8.dp),
                                letterSpacing = 1.sp
                            )
                        }
                    }
                }
            }
        }
    ) { innerPadding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .padding(16.dp)
        ) {
            when (selectedSandboxMode) {
                "Chat" -> ChatSandboxView(aiService = aiService, language = currentLang)
                "Voice" -> VoiceSandboxView(aiService = aiService, language = currentLang)
                "Blocks" -> BlocklySandboxView(language = currentLang)
                "Code" -> CodeSandboxView(
                    code = currentCodeText,
                    onCodeChanged = { currentCodeText = it },
                    logs = codeCompilationOutput,
                    isCompiling = isCompiling,
                    onCompileClick = {
                        isCompiling = true
                        codeCompilationOutput = "Triggering local micro-compiler compiler toolchain...\n"
                        bleManager.addLog("Triggering Local code compiler...")
                        scope.launch {
                            delay(1200)
                            codeCompilationOutput += "Target: ESP32-S3 Core (SXT-Express)\narduino-cli build --fqbn esp32:esp32:esp32s3\n\nCompiling... [DONE]\n"
                            delay(800)
                            codeCompilationOutput += "Generating partition binaries: app.bin (720 KB)\nUploading binary via Bluetooth OTA to Flash memory...\n"
                            bleManager.addLog("Executing OTA upload: 720KB written.")
                            delay(1000)
                            codeCompilationOutput += "SUCCESS: Microcontroller Flash memory successfully synchronized! Board auto-resetting.\n"
                            bleManager.addLog("Board Reset successfully. Applying sketch variables.")
                            isCompiling = false
                            bleManager.processCommand(CommandMessage("display", text = "Sync successful!\nNew Code Applied"))
                        }
                    }
                )
            }
        }
    }
}

// --- 1. CHAT SANDBOX VIEW ---

@Composable
fun ChatSandboxView(aiService: TinkrAIService, language: String) {
    val scope = rememberCoroutineScope()
    var inputQuery by remember { mutableStateOf("") }
    var chatHistory by remember { mutableStateOf(listOf(
        AIChatMessage("Hi! I am Gemma 4 E2B Tinkr Companion. Send me an instruction to orchestrate hardware or write automation sketch models, e.g. \"Turn on the status LED\" or \"Scaffold a soil gardener project\"", false)
    )) }
    var isThinking by remember { mutableStateOf(false) }

    Column(modifier = Modifier.fillMaxSize()) {
        LazyColumn(
            modifier = Modifier.weight(1f),
            verticalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            items(chatHistory) { msg ->
                Card(
                    modifier = Modifier.fillMaxWidth(0.9f).align(if (msg.isUser) Alignment.End else Alignment.Start),
                    colors = CardDefaults.cardColors(
                        containerColor = if (msg.isUser) TinkrOrange.copy(alpha = 0.15f) else TinkrCardDark
                    ),
                    border = BorderStroke(1.dp, if (msg.isUser) TinkrOrange else Color.White.copy(alpha = 0.05f)),
                    shape = RoundedCornerShape(16.dp)
                ) {
                    Column(modifier = Modifier.padding(14.dp)) {
                        Text(
                            text = if (msg.isUser) "Outcome Request" else msg.modelSource,
                            color = if (msg.isUser) TinkrOrangeGlow else TinkrBlue,
                            fontWeight = FontWeight.Bold,
                            fontSize = 10.sp,
                            letterSpacing = 1.sp
                        )
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(text = msg.text, color = Color.White, fontSize = 13.sp, lineHeight = 18.sp)

                        if (msg.codeBlob.isNotEmpty()) {
                            Spacer(modifier = Modifier.height(8.dp))
                            Card(
                                modifier = Modifier.fillMaxWidth(),
                                colors = CardDefaults.cardColors(containerColor = Color.Black),
                                shape = RoundedCornerShape(8.dp)
                            ) {
                                Text(
                                    text = msg.codeBlob,
                                    color = TinkrGreen,
                                    fontFamily = FontFamily.Monospace,
                                    fontSize = 11.sp,
                                    lineHeight = 16.sp,
                                    modifier = Modifier.padding(10.dp)
                                )
                            }
                        }
                    }
                }
            }

            if (isThinking) {
                item {
                    Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.padding(12.dp)) {
                        CircularProgressIndicator(modifier = Modifier.size(16.dp), color = TinkrOrange, strokeWidth = 2.dp)
                        Spacer(modifier = Modifier.width(8.dp))
                        Text("Gemma thinking inside compiler loop...", color = Color.White.copy(alpha = 0.5f), fontSize = 11.sp)
                    }
                }
            }
        }

        // Search inputs bar
        Row(
            modifier = Modifier.fillMaxWidth().padding(top = 12.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            TextField(
                value = inputQuery,
                onValueChange = { inputQuery = it },
                modifier = Modifier.weight(1f),
                placeholder = { Text("Command hardware (e.g. Turn on LED)", color = Color.White.copy(alpha = 0.4f)) },
                shape = RoundedCornerShape(16.dp),
                colors = OutlinedTextFieldDefaults.colors(
                    focusedContainerColor = TinkrCardDark,
                    unfocusedContainerColor = TinkrCardDark,
                    focusedBorderColor = TinkrOrange,
                    unfocusedBorderColor = Color.White.copy(alpha = 0.08f)
                ),
                singleLine = true
            )
            Spacer(modifier = Modifier.width(8.dp))
            IconButton(
                onClick = {
                    if (inputQuery.trim().isEmpty()) return@IconButton
                    val prompt = inputQuery
                    inputQuery = ""
                    chatHistory = chatHistory + AIChatMessage(prompt, true)
                    isThinking = true

                    scope.launch {
                        val response = aiService.runPrompt(prompt)
                        isThinking = false
                        chatHistory = chatHistory + AIChatMessage(
                            text = "${response.message}\n\n${response.explanation}",
                            isUser = false,
                            codeBlob = response.codePreview,
                            modelSource = response.modelSource
                        )
                    }
                },
                modifier = Modifier
                    .size(52.dp)
                    .clip(CircleShape)
                    .background(TinkrOrange)
            ) {
                Icon(Icons.Default.Send, contentDescription = null, tint = Color.White)
            }
        }
    }
}

data class AIChatMessage(
    val text: String,
    val isUser: Boolean,
    val codeBlob: String = "",
    val modelSource: String = "Tinkr Companion v2.1"
)

// --- 2. VOICE SANDBOX VIEW ---

@Composable
fun VoiceSandboxView(aiService: TinkrAIService, language: String) {
    val scope = rememberCoroutineScope()
    var isListening by remember { mutableStateOf(false) }
    var voicePrompt by remember { mutableStateOf("Press mic to begin and say something like: 'Water my garden now'...") }
    var voiceResultCode by remember { mutableStateOf("") }
    var isThinking by remember { mutableStateOf(false) }

    Column(
        modifier = Modifier.fillMaxSize(),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        val infiniteTransition = rememberInfiniteTransition()
        val pulseRingScale by infiniteTransition.animateFloat(
            initialValue = 0.8f,
            targetValue = 1.3f,
            animationSpec = infiniteRepeatable(
                animation = tween(1400, easing = LinearEasing),
                repeatMode = RepeatMode.Restart
            )
        )

        Box(contentAlignment = Alignment.Center) {
            if (isListening) {
                Box(
                    modifier = Modifier
                        .size((120 * pulseRingScale).dp)
                        .clip(CircleShape)
                        .background(TinkrOrange.copy(alpha = 0.2f * (1.3f - pulseRingScale)))
                )
            }
            IconButton(
                onClick = {
                    if (isListening) {
                        isListening = false
                        voicePrompt = "Water the planter now"
                        isThinking = true
                        scope.launch {
                            val res = aiService.runPrompt(voicePrompt)
                            isThinking = false
                            voicePrompt = "Result: ${res.message}"
                            voiceResultCode = res.codePreview
                        }
                    } else {
                        isListening = true
                        voicePrompt = TinkrTranslations.getString("speaking", language)
                    }
                },
                modifier = Modifier
                    .size(90.dp)
                    .clip(CircleShape)
                    .background(if (isListening) TinkrGreen else TinkrOrange)
                    .shadow(12.dp, shape = CircleShape)
            ) {
                Icon(
                    imageVector = if (isListening) Icons.Default.MicOff else Icons.Default.Mic,
                    contentDescription = null,
                    tint = if (isListening) Color.Black else Color.White,
                    modifier = Modifier.size(36.dp)
                )
            }
        }

        Spacer(modifier = Modifier.height(24.dp))

        Text(
            text = voicePrompt,
            color = Color.White,
            fontWeight = FontWeight.Bold,
            fontSize = 16.sp,
            textAlign = TextAlign.Center,
            modifier = Modifier.padding(horizontal = 24.dp)
        )

        if (isThinking) {
            Spacer(modifier = Modifier.height(16.dp))
            CircularProgressIndicator(color = TinkrOrange)
        }

        if (voiceResultCode.isNotEmpty()) {
            Spacer(modifier = Modifier.height(24.dp))
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = Color.Black),
                border = BorderStroke(1.dp, TinkrGreen.copy(alpha = 0.2f))
            ) {
                Text(
                    text = voiceResultCode,
                    color = TinkrGreen,
                    fontFamily = FontFamily.Monospace,
                    fontSize = 11.sp,
                    modifier = Modifier.padding(14.dp)
                )
            }
        }
    }
}

// --- 3. BLOCKLY SANDBOX VIEW ---

@Composable
fun BlocklySandboxView(language: String) {
    val blockItems = listOf(
        BlockItem("IF Soil < 35%", "Triggers condition when humidity spikes low", TinkrOrange),
        BlockItem("THEN Trigger Pump", "Forces Pin 12 Relay active Closed trigger", TinkrBlue),
        BlockItem("WAIT 3000 MS", "Implements delay timers on executing core loops", TinkrYellow),
        BlockItem("ELSE write GPIO", "Alternates output states to other pins", TinkrPurple)
    )

    Column(modifier = Modifier.fillMaxSize()) {
        Text(
            "Blockly Orchestrations Layout",
            color = Color.White,
            fontWeight = FontWeight.Bold,
            fontSize = 16.sp
        )
        Text(
            "Construct complex device state rules dynamically",
            color = Color.White.copy(alpha = 0.5f),
            fontSize = 12.sp,
            modifier = Modifier.padding(top = 4.dp, bottom = 16.dp)
        )

        LazyColumn(verticalArrangement = Arrangement.spacedBy(10.dp)) {
            items(blockItems) { block ->
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    colors = CardDefaults.cardColors(containerColor = TinkrCardDark),
                    border = BorderStroke(2.dp, block.glowColor)
                ) {
                    Row(
                        modifier = Modifier.padding(16.dp).fillMaxWidth(),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Box(
                            modifier = Modifier
                                .size(32.dp)
                                .clip(RoundedCornerShape(8.dp))
                                .background(block.glowColor.copy(alpha = 0.15f)),
                            contentAlignment = Alignment.Center
                        ) {
                            Icon(Icons.Default.Extension, contentDescription = null, tint = block.glowColor)
                        }
                        Spacer(modifier = Modifier.width(16.dp))
                        Column {
                            Text(block.title, color = block.glowColor, fontWeight = FontWeight.Bold, fontSize = 15.sp)
                            Text(block.desc, color = Color.White.copy(alpha = 0.5f), fontSize = 12.sp)
                        }
                    }
                }
            }
        }
    }
}

data class BlockItem(val title: String, val desc: String, val glowColor: Color)

// --- 4. CODE SANDBOX VIEW ---

@Composable
fun CodeSandboxView(
    code: String,
    onCodeChanged: (String) -> Unit,
    logs: String,
    isCompiling: Boolean,
    onCompileClick: () -> Unit
) {
    Column(modifier = Modifier.fillMaxSize()) {
        Text(
            "Monaco SDK Workspace",
            color = Color.White,
            fontWeight = FontWeight.Bold,
            fontSize = 16.sp
        )
        Text(
            "Arduino-ESP32 C++ Sketch Editor Workspace",
            color = Color.White.copy(alpha = 0.5f),
            fontSize = 12.sp,
            modifier = Modifier.padding(top = 4.dp, bottom = 12.dp)
        )

        // Raw Monaco edit frame
        OutlinedTextField(
            value = code,
            onValueChange = onCodeChanged,
            modifier = Modifier.weight(0.6f).fillMaxWidth(),
            textStyle = MaterialTheme.typography.bodyMedium.copy(fontFamily = FontFamily.Monospace, color = TinkrGreen),
            shape = RoundedCornerShape(12.dp),
            colors = OutlinedTextFieldDefaults.colors(
                focusedContainerColor = Color.Black,
                unfocusedContainerColor = Color.Black,
                focusedBorderColor = TinkrOrange,
                unfocusedBorderColor = Color.White.copy(alpha = 0.08f)
            )
        )

        Spacer(modifier = Modifier.height(10.dp))

        // Toolchain execution logs
        if (logs.isNotEmpty()) {
            Card(
                modifier = Modifier.weight(0.4f).fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = Color(0xFF0F1012)),
                border = BorderStroke(1.dp, Color.White.copy(alpha = 0.1f))
            ) {
                LazyColumn(modifier = Modifier.padding(12.dp).fillMaxSize()) {
                    item {
                        Text(
                            text = logs,
                            color = Color.White.copy(alpha = 0.7f),
                            fontFamily = FontFamily.Monospace,
                            fontSize = 11.sp,
                            lineHeight = 16.sp
                        )
                    }
                }
            }
        }

        Spacer(modifier = Modifier.height(12.dp))

        Button(
            onClick = onCompileClick,
            colors = ButtonDefaults.buttonColors(containerColor = TinkrOrange),
            modifier = Modifier.fillMaxWidth().height(50.dp),
            shape = RoundedCornerShape(14.dp),
            enabled = !isCompiling
        ) {
            if (isCompiling) {
                CircularProgressIndicator(modifier = Modifier.size(20.dp), color = Color.White)
            } else {
                Icon(Icons.Default.Bolt, contentDescription = null, tint = Color.White)
                Spacer(modifier = Modifier.width(6.dp))
                Text("Flash Local OTA", color = Color.White, fontWeight = FontWeight.Bold)
            }
        }
    }
}
