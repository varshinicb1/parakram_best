package com.example.ui

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
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
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.ai.*
import com.example.hardware.TinkrBleManager
import com.example.ui.theme.*
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AISheet(
    language: String,
    onDismiss: () -> Unit
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val aiService = remember { TinkrAIService.getInstance(context) }
    val bleManager = remember { TinkrBleManager.getInstance(context) }

    // Chat states
    var queryText by remember { mutableStateOf("") }
    var aiThinkingMode by remember { mutableStateOf("Builder") } // Builder, Analyst, Teacher
    var isResolvingTask by remember { mutableStateOf(false) }

    var aiReplyMessage by remember { mutableStateOf("Standby. Enter outcome trigger below in $aiThinkingMode mode:") }
    var aiReplyActions by remember { mutableStateOf<List<AgentAction>>(emptyList()) }
    var aiReplyCode by remember { mutableStateOf("") }

    Column(
        modifier = Modifier
            .fillMaxWidth()
            .background(TinkrCardDark)
            .padding(24.dp)
            .navigationBarsPadding(),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        // Drag Indicator bar
        Box(
            modifier = Modifier
                .size(40.dp, 4.dp)
                .clip(CircleShape)
                .background(Color.White.copy(alpha = 0.15f))
        )

        Spacer(modifier = Modifier.height(18.dp))

        // Title and Mode Headers
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                text = TinkrTranslations.getString("ai_sheet_title", language),
                color = Color.White,
                fontSize = 18.sp,
                fontWeight = FontWeight.Bold
            )
            IconButton(onClick = onDismiss) {
                Icon(Icons.Default.Close, contentDescription = "Close", tint = Color.White.copy(alpha = 0.5f))
            }
        }

        Spacer(modifier = Modifier.height(16.dp))

        // Selectable State Mode pills
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            listOf("Builder", "Analyst", "Teacher").forEach { mode ->
                val isSel = mode == aiThinkingMode
                Surface(
                    modifier = Modifier
                        .weight(1f)
                        .clip(RoundedCornerShape(12.dp))
                        .clickable { aiThinkingMode = mode },
                    color = if (isSel) TinkrOrange.copy(alpha = 0.15f) else Color.White.copy(alpha = 0.03f),
                    border = BorderStroke(1.dp, if (isSel) TinkrOrange else Color.White.copy(alpha = 0.05f))
                ) {
                    Text(
                        text = mode.uppercase(),
                        color = if (isSel) TinkrOrangeGlow else Color.White.copy(alpha = 0.5f),
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Bold,
                        modifier = Modifier.padding(vertical = 10.dp),
                        textAlign = TextAlign.Center,
                        letterSpacing = 1.sp
                    )
                }
            }
        }

        Spacer(modifier = Modifier.height(20.dp))

        // Output Frame
        Card(
            modifier = Modifier
                .fillMaxWidth()
                .weight(1f, fill = false),
            colors = CardDefaults.cardColors(containerColor = Color.Black),
            border = BorderStroke(1.dp, Color.White.copy(alpha = 0.05f))
        ) {
            LazyColumn(
                modifier = Modifier.padding(14.dp),
                verticalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                // Main Text Advice
                item {
                    Text(
                        text = aiReplyMessage,
                        color = Color.White,
                        fontSize = 13.sp,
                        lineHeight = 18.sp
                    )
                }

                // If actions parsed, highlight them
                if (aiReplyActions.isNotEmpty()) {
                    item {
                        Text(
                            text = "AUTONOMOUS EXECUTIONS LOGGED:",
                            color = TinkrOrangeGlow,
                            fontSize = 10.sp,
                            fontWeight = FontWeight.Bold,
                            letterSpacing = 1.sp,
                            modifier = Modifier.padding(top = 8.dp)
                        )
                    }

                    items(aiReplyActions) { act ->
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .background(TinkrCardDark, RoundedCornerShape(8.dp))
                                .padding(10.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Icon(Icons.Default.Settings, contentDescription = null, tint = TinkrGreen, modifier = Modifier.size(14.dp))
                            Spacer(modifier = Modifier.width(8.dp))
                            Column {
                                Text(act.toolName, color = TinkrGreen, fontWeight = FontWeight.Bold, fontSize = 11.sp)
                                Text(act.description, color = Color.White.copy(alpha = 0.6f), fontSize = 10.sp)
                            }
                        }
                    }
                }

                // Highlighted Sketch
                if (aiReplyCode.isNotEmpty()) {
                    item {
                        Card(
                            modifier = Modifier.fillMaxWidth().padding(top = 10.dp),
                            colors = CardDefaults.cardColors(containerColor = TinkrCardDark)
                        ) {
                            Text(
                                text = aiReplyCode,
                                color = TinkrGreen,
                                fontFamily = FontFamily.Monospace,
                                fontSize = 10.sp,
                                lineHeight = 14.sp,
                                modifier = Modifier.padding(10.dp)
                            )
                        }
                    }
                }
            }
        }

        Spacer(modifier = Modifier.height(16.dp))

        // Inputs frame
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically
        ) {
            // Camera input icon
            IconButton(
                onClick = {
                    aiReplyMessage = "Wiring camera diagnostics initiated. Scanned virtual ESP32-S3 boards. Found Pin 13 status led linked securely to GND, Pin 12 Pump closed relay linking properly."
                    bleManager.addLog("AI Image Lens: Scanned electronic wiring manifest.")
                },
                modifier = Modifier
                    .size(48.dp)
                    .clip(CircleShape)
                    .background(Color.White.copy(alpha = 0.03f))
            ) {
                Icon(Icons.Default.CameraAlt, contentDescription = "Camera detection Input", tint = TinkrOrangeGlow)
            }

            Spacer(modifier = Modifier.width(8.dp))

            OutlinedTextField(
                value = queryText,
                onValueChange = { queryText = it },
                modifier = Modifier.weight(1f),
                placeholder = { Text("How can I help you compile or configure?", color = Color.White.copy(alpha = 0.3f), fontSize = 12.sp) },
                colors = OutlinedTextFieldDefaults.colors(
                    focusedBorderColor = TinkrOrange,
                    unfocusedBorderColor = Color.White.copy(alpha = 0.08f),
                    focusedContainerColor = Color.Black,
                    unfocusedContainerColor = Color.Black
                ),
                shape = RoundedCornerShape(14.dp),
                singleLine = true
            )

            Spacer(modifier = Modifier.width(8.dp))

            IconButton(
                onClick = {
                    if (queryText.trim().isEmpty()) return@IconButton
                    val prompt = queryText
                    queryText = ""
                    isResolvingTask = true
                    aiReplyMessage = "Gemma 4 modeling deep physical outcomes..."
                    aiReplyActions = emptyList()
                    aiReplyCode = ""
                    
                    scope.launch {
                        val response = aiService.runPrompt(prompt, mode = aiThinkingMode)
                        isResolvingTask = false
                        aiReplyMessage = response.message + "\n\n" + response.explanation
                        aiReplyActions = response.actions
                        aiReplyCode = response.codePreview
                    }
                },
                modifier = Modifier
                    .size(48.dp)
                    .clip(CircleShape)
                    .background(TinkrOrange),
                enabled = !isResolvingTask
            ) {
                if (isResolvingTask) {
                    CircularProgressIndicator(modifier = Modifier.size(18.dp), color = Color.White)
                } else {
                    Icon(Icons.Default.PlayArrow, contentDescription = "Execute Prompt", tint = Color.White)
                }
            }
        }
    }
}
