package com.example.ui

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
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
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.data.*
import com.example.hardware.TinkrBleManager
import com.example.ui.theme.*
import kotlinx.coroutines.launch

@Composable
fun ProjectsScreen(settingsRepository: SettingsRepository) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()

    val currentLang by settingsRepository.languageFlow.collectAsState(initial = "en")
    val database = remember { TinkrDatabase.getDatabase(context) }
    val bleManager = remember { TinkrBleManager.getInstance(context) }

    // Live Room query for custom projects
    val customProjects by database.projectDao().getAllProjects().collectAsState(initial = emptyList())

    // Dialog state
    var showCreateDialog by remember { mutableStateOf(false) }
    var newProjName by remember { mutableStateOf("") }
    var newProjDesc by remember { mutableStateOf("") }

    // Prebuilt premium hardware templates
    val templates = listOf(
        PremiumTemplate("Smart Planter", "Intelligent Soil DHT22 & irrigation relay config.", Icons.Default.Grass, TinkrGreen),
        PremiumTemplate("Weather Node", "Full-bleed outdoor Lux, temperature and pressure terminal.", Icons.Default.WbSunny, TinkrYellow),
        PremiumTemplate("Factory Monitor", "CO2 gas alert triggers and acoustic piezo sirens.", Icons.Default.Factory, TinkrOrangeGlow),
        PremiumTemplate("HVAC Sentinel", "Climate dials, ambient fans, and DeX notifications.", Icons.Default.Thermostat, TinkrBlue)
    )

    Scaffold(
        containerColor = MaterialTheme.colorScheme.background,
        floatingActionButton = {
            FloatingActionButton(
                onClick = { showCreateDialog = true },
                containerColor = TinkrOrange,
                contentColor = Color.White,
                shape = CircleShape
            ) {
                Icon(Icons.Default.Add, contentDescription = "Add Custom Project")
            }
        }
    ) { innerPadding ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            // 1. HEADER TITLE
            item {
                Row(
                    modifier = Modifier.fillMaxWidth().padding(bottom = 8.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column {
                        Text(
                            text = TinkrTranslations.getString("projects_title", currentLang),
                            color = Color.White,
                            fontSize = 22.sp,
                            fontWeight = FontWeight.Bold
                        )
                        Text(
                            text = "Manage configurations and custom sketches",
                            color = Color.White.copy(alpha = 0.5f),
                            fontSize = 12.sp,
                            modifier = Modifier.padding(top = 2.dp)
                        )
                    }
                    Icon(Icons.Default.FolderZip, contentDescription = null, tint = TinkrOrangeGlow)
                }
            }

            // 2. PREMIUM HARDWARE PRESET CARDS (HORIZONTAL ROW)
            item {
                Text(
                    text = "PRESETS TEMPLATES",
                    color = Color.White.copy(alpha = 0.5f),
                    fontSize = 11.sp,
                    fontWeight = FontWeight.Bold,
                    letterSpacing = 1.sp
                )
            }

            item {
                LazyRow(
                    horizontalArrangement = Arrangement.spacedBy(12.dp),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    items(templates) { temp ->
                        Card(
                            modifier = Modifier
                                .width(180.dp)
                                .height(160.dp)
                                .clickable {
                                    scope.launch {
                                        database.projectDao().insertProject(
                                            ProjectEntity(
                                                name = temp.title,
                                                description = temp.desc,
                                                templateType = temp.title,
                                                codeContent = "// Auto preconfigured boilerplate\nvoid setup() {\n  Serial.begin(115200);\n}"
                                            )
                                        )
                                        bleManager.addLog("Deployed Template Project: ${temp.title}")
                                    }
                                },
                            colors = CardDefaults.cardColors(containerColor = TinkrCardDark),
                            border = BorderStroke(1.dp, temp.borderTheme.copy(alpha = 0.3f)),
                            shape = RoundedCornerShape(16.dp)
                        ) {
                            Column(modifier = Modifier.padding(14.dp).fillMaxSize(), verticalArrangement = Arrangement.SpaceBetween) {
                                Box(
                                    modifier = Modifier
                                        .size(36.dp)
                                        .clip(RoundedCornerShape(8.dp))
                                        .background(temp.borderTheme.copy(alpha = 0.15f)),
                                    contentAlignment = Alignment.Center
                                ) {
                                    Icon(imageVector = temp.icon, contentDescription = null, tint = temp.borderTheme)
                                }
                                Column {
                                    Text(text = temp.title, color = Color.White, fontWeight = FontWeight.Bold, fontSize = 14.sp)
                                    Spacer(modifier = Modifier.height(4.dp))
                                    Text(text = temp.desc, color = Color.White.copy(alpha = 0.5f), fontSize = 11.sp, lineHeight = 14.sp)
                                }
                            }
                        }
                    }
                }
            }

            // 3. SECURED PROJECTS STORAGE DATABASE
            item {
                Text(
                    text = "LOCAL DEPLOYED ARTIFACTS",
                    color = Color.White.copy(alpha = 0.5f),
                    fontSize = 11.sp,
                    fontWeight = FontWeight.Bold,
                    letterSpacing = 1.sp,
                    modifier = Modifier.padding(top = 10.dp)
                )
            }

            if (customProjects.isEmpty()) {
                item {
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        colors = CardDefaults.cardColors(containerColor = TinkrCardDark),
                        border = BorderStroke(1.dp, Color.White.copy(alpha = 0.05f))
                    ) {
                        Box(modifier = Modifier.padding(24.dp).fillMaxWidth(), contentAlignment = Alignment.Center) {
                            Text("No custom sketch deployed yet. Deploy presets or click + to instantiate.", color = Color.White.copy(alpha = 0.4f), fontSize = 12.sp)
                        }
                    }
                }
            } else {
                items(customProjects) { proj ->
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        colors = CardDefaults.cardColors(containerColor = TinkrCardDark),
                        border = BorderStroke(1.dp, Color.White.copy(alpha = 0.05f))
                    ) {
                        Row(
                            modifier = Modifier.padding(16.dp).fillMaxWidth(),
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Icon(Icons.Default.Dns, contentDescription = null, tint = TinkrOrangeGlow)
                                Spacer(modifier = Modifier.width(16.dp))
                                Column {
                                    Text(text = proj.name, color = Color.White, fontWeight = FontWeight.Bold, fontSize = 14.sp)
                                    Text(text = proj.description, color = Color.White.copy(alpha = 0.5f), fontSize = 11.sp)
                                }
                            }
                            IconButton(
                                onClick = {
                                    scope.launch {
                                        database.projectDao().deleteProject(proj)
                                        bleManager.addLog("Deleted custom workspace: ${proj.name}")
                                    }
                                }
                            ) {
                                Icon(Icons.Default.Delete, contentDescription = "Delete", tint = TinkrOrange)
                            }
                        }
                    }
                }
            }
        }

        // 4. NEW WORKSPACE CREATOR DIALOG
        if (showCreateDialog) {
            AlertDialog(
                onDismissRequest = { showCreateDialog = false },
                containerColor = TinkrCardDark,
                title = { Text("Scaffold Custom Workspace", color = Color.White, fontWeight = FontWeight.Bold) },
                text = {
                    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                        TextField(
                            value = newProjName,
                            onValueChange = { newProjName = it },
                            placeholder = { Text("Workspace Name (e.g., Plant Guardian)") },
                            colors = OutlinedTextFieldDefaults.colors(focusedBorderColor = TinkrOrange, unfocusedBorderColor = Color.White.copy(alpha = 0.1f))
                        )
                        TextField(
                            value = newProjDesc,
                            onValueChange = { newProjDesc = it },
                            placeholder = { Text("Brief description of physical automations") },
                            colors = OutlinedTextFieldDefaults.colors(focusedBorderColor = TinkrOrange, unfocusedBorderColor = Color.White.copy(alpha = 0.1f))
                        )
                    }
                },
                confirmButton = {
                    Button(
                        onClick = {
                            if (newProjName.isNotEmpty()) {
                                scope.launch {
                                    database.projectDao().insertProject(
                                        ProjectEntity(name = newProjName, description = newProjDesc)
                                    )
                                    bleManager.addLog("Custom workspace '$newProjName' successfully initialized.")
                                }
                                newProjName = ""
                                newProjDesc = ""
                                showCreateDialog = false
                            }
                        },
                        colors = ButtonDefaults.buttonColors(containerColor = TinkrOrange)
                    ) {
                        Text("Create Workspace", color = Color.White)
                    }
                },
                dismissButton = {
                    TextButton(onClick = { showCreateDialog = false }) {
                        Text("Cancel", color = Color.White.copy(alpha = 0.5f))
                    }
                }
            )
        }
    }
}

data class PremiumTemplate(val title: String, val desc: String, val icon: androidx.compose.ui.graphics.vector.ImageVector, val borderTheme: Color)
