package com.example.ui

import androidx.compose.animation.animateContentSize
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
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.data.BackendStatus
import com.example.data.GoldenBlock
import com.example.data.GoldenBlocksRepository
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class, ExperimentalLayoutApi::class)
@Composable
fun DriversScreen(lang: String = "en") {
    val repository = remember { GoldenBlocksRepository.getInstance() }
    val blocks by repository.blocks.collectAsState()
    val status by repository.backendStatus.collectAsState()
    val isLoading by repository.isLoading.collectAsState()
    val scope = rememberCoroutineScope()

    var selectedCategory by remember { mutableStateOf<String?>(null) }
    var searchQuery by remember { mutableStateOf("") }

    LaunchedEffect(Unit) {
        repository.refreshAll()
    }

    val filteredBlocks = blocks.filter { block ->
        val matchesCategory = selectedCategory == null || block.driverType == selectedCategory
        val matchesSearch = searchQuery.isEmpty() ||
                block.displayName.contains(searchQuery, ignoreCase = true) ||
                block.name.contains(searchQuery, ignoreCase = true) ||
                block.capabilities.any { it.contains(searchQuery, ignoreCase = true) }
        matchesCategory && matchesSearch
    }

    val categories = blocks.map { it.driverType }.distinct().sorted()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background)
            .padding(16.dp)
    ) {
        // Header
        Text(
            text = TinkrTranslations.getString("drivers_title", lang),
            style = MaterialTheme.typography.headlineMedium,
            fontWeight = FontWeight.Bold,
            color = MaterialTheme.colorScheme.onBackground
        )
        Spacer(modifier = Modifier.height(4.dp))
        Text(
            text = TinkrTranslations.getString("drivers_subtitle", lang),
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )

        Spacer(modifier = Modifier.height(12.dp))

        // Backend status card
        BackendStatusCard(status = status)

        Spacer(modifier = Modifier.height(12.dp))

        // Search bar
        OutlinedTextField(
            value = searchQuery,
            onValueChange = { searchQuery = it },
            placeholder = { Text("Search drivers...") },
            leadingIcon = { Icon(Icons.Default.Search, contentDescription = null) },
            trailingIcon = {
                if (searchQuery.isNotEmpty()) {
                    IconButton(onClick = { searchQuery = "" }) {
                        Icon(Icons.Default.Clear, contentDescription = "Clear")
                    }
                }
            },
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(12.dp),
            singleLine = true
        )

        Spacer(modifier = Modifier.height(8.dp))

        // Category chips
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            FilterChip(
                selected = selectedCategory == null,
                onClick = { selectedCategory = null },
                label = { Text("All (${blocks.size})") }
            )
            categories.forEach { cat ->
                val count = blocks.count { it.driverType == cat }
                FilterChip(
                    selected = selectedCategory == cat,
                    onClick = { selectedCategory = if (selectedCategory == cat) null else cat },
                    label = { Text("${cat.replaceFirstChar { it.uppercase() }} ($count)") },
                    leadingIcon = {
                        Icon(
                            imageVector = driverTypeIcon(cat),
                            contentDescription = null,
                            modifier = Modifier.size(16.dp)
                        )
                    }
                )
            }
        }

        Spacer(modifier = Modifier.height(8.dp))

        // Driver list
        if (isLoading) {
            Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                CircularProgressIndicator()
            }
        } else if (filteredBlocks.isEmpty() && blocks.isEmpty()) {
            Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Icon(
                        Icons.Default.CloudOff,
                        contentDescription = null,
                        modifier = Modifier.size(48.dp),
                        tint = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        text = "Connect to backend to load drivers",
                        style = MaterialTheme.typography.bodyLarge,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    Button(onClick = { scope.launch { repository.refreshAll() } }) {
                        Text("Retry")
                    }
                }
            }
        } else {
            LazyColumn(
                verticalArrangement = Arrangement.spacedBy(8.dp),
                modifier = Modifier.fillMaxSize()
            ) {
                items(filteredBlocks, key = { it.name }) { block ->
                    DriverCard(block = block)
                }
            }
        }
    }
}

@Composable
private fun BackendStatusCard(status: BackendStatus) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(
            containerColor = if (status.connected) {
                Color(0xFF1B5E20).copy(alpha = 0.15f)
            } else {
                Color(0xFFB71C1C).copy(alpha = 0.15f)
            }
        )
    ) {
        Row(
            modifier = Modifier.padding(12.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Box(
                modifier = Modifier
                    .size(10.dp)
                    .clip(CircleShape)
                    .background(if (status.connected) Color(0xFF4CAF50) else Color(0xFFF44336))
            )
            Spacer(modifier = Modifier.width(8.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = if (status.connected) "Backend Connected" else "Backend Offline",
                    style = MaterialTheme.typography.titleSmall,
                    fontWeight = FontWeight.Bold
                )
                if (status.connected) {
                    Text(
                        text = "v${status.version} | ${status.driverCount} drivers | DB: ${status.database}",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }
            if (status.connected && status.llmAvailable) {
                AssistChip(
                    onClick = {},
                    label = { Text("LLM", style = MaterialTheme.typography.labelSmall) },
                    leadingIcon = {
                        Icon(Icons.Default.AutoAwesome, contentDescription = null, modifier = Modifier.size(14.dp))
                    }
                )
            }
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun DriverCard(block: GoldenBlock) {
    var expanded by remember { mutableStateOf(false) }

    Card(
        modifier = Modifier
            .fillMaxWidth()
            .animateContentSize()
            .clickable { expanded = !expanded },
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
    ) {
        Column(modifier = Modifier.padding(12.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(
                    imageVector = driverTypeIcon(block.driverType),
                    contentDescription = null,
                    tint = driverTypeColor(block.driverType),
                    modifier = Modifier.size(28.dp)
                )
                Spacer(modifier = Modifier.width(10.dp))
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = block.displayName,
                        style = MaterialTheme.typography.titleSmall,
                        fontWeight = FontWeight.Bold
                    )
                    Text(
                        text = block.name,
                        style = MaterialTheme.typography.bodySmall,
                        fontFamily = FontFamily.Monospace,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
                AssistChip(
                    onClick = {},
                    label = {
                        Text(
                            block.driverType.replaceFirstChar { it.uppercase() },
                            style = MaterialTheme.typography.labelSmall
                        )
                    }
                )
            }

            if (expanded) {
                Spacer(modifier = Modifier.height(8.dp))
                HorizontalDivider()
                Spacer(modifier = Modifier.height(8.dp))

                if (block.description.isNotEmpty()) {
                    Text(
                        text = block.description,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                }

                // Bus types
                Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                    Text("Bus:", style = MaterialTheme.typography.labelSmall, fontWeight = FontWeight.Bold)
                    block.busTypes.forEach { bus ->
                        SuggestionChip(
                            onClick = {},
                            label = { Text(bus.uppercase(), style = MaterialTheme.typography.labelSmall) }
                        )
                    }
                }

                Spacer(modifier = Modifier.height(4.dp))

                // Capabilities
                Text(
                    text = "Capabilities:",
                    style = MaterialTheme.typography.labelSmall,
                    fontWeight = FontWeight.Bold
                )
                Spacer(modifier = Modifier.height(2.dp))
                FlowRow(
                    horizontalArrangement = Arrangement.spacedBy(4.dp),
                    verticalArrangement = Arrangement.spacedBy(4.dp)
                ) {
                    block.capabilities.forEach { cap ->
                        SuggestionChip(
                            onClick = {},
                            label = { Text(cap, style = MaterialTheme.typography.labelSmall) }
                        )
                    }
                }
            }
        }
    }
}

private fun driverTypeIcon(type: String): ImageVector = when (type) {
    "sensor" -> Icons.Default.Sensors
    "actuator" -> Icons.Default.Settings
    "display" -> Icons.Default.Monitor
    "combo" -> Icons.Default.Hub
    "communication" -> Icons.Default.Wifi
    else -> Icons.Default.Memory
}

private fun driverTypeColor(type: String): Color = when (type) {
    "sensor" -> Color(0xFF2196F3)
    "actuator" -> Color(0xFFFF9800)
    "display" -> Color(0xFF9C27B0)
    "combo" -> Color(0xFF4CAF50)
    "communication" -> Color(0xFF00BCD4)
    else -> Color(0xFF607D8B)
}
