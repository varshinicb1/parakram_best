package com.example.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Close
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.example.display.DumbDisplayCanvas
import com.example.display.DumbDisplayServer

@Composable
fun DisplayScreen() {
    val server = remember { DumbDisplayServer() }
    val connectionState by server.connectionState.collectAsState()
    val connectedIp by server.connectedDeviceIp.collectAsState()

    DisposableEffect(Unit) {
        onDispose { server.stop() }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(Color(0xFF0D1117))
            .padding(16.dp)
    ) {
        Text(
            text = "DumbDisplay",
            style = MaterialTheme.typography.headlineMedium,
            color = Color.White,
            fontWeight = FontWeight.Bold
        )
        Text(
            text = "Phone renders display for ESP32",
            style = MaterialTheme.typography.bodyMedium,
            color = Color(0xFF8B949E)
        )

        Spacer(modifier = Modifier.height(16.dp))

        // Status card
        Card(
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(containerColor = Color(0xFF161B22)),
            shape = RoundedCornerShape(12.dp)
        ) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(16.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Box(
                        modifier = Modifier
                            .size(12.dp)
                            .clip(CircleShape)
                            .background(
                                when (connectionState) {
                                    DumbDisplayServer.ConnectionState.CONNECTED -> Color(0xFF3FB950)
                                    DumbDisplayServer.ConnectionState.LISTENING -> Color(0xFFD29922)
                                    DumbDisplayServer.ConnectionState.ERROR -> Color(0xFFF85149)
                                    DumbDisplayServer.ConnectionState.STOPPED -> Color(0xFF484F58)
                                }
                            )
                    )
                    Text(
                        text = when (connectionState) {
                            DumbDisplayServer.ConnectionState.CONNECTED -> "Connected: $connectedIp"
                            DumbDisplayServer.ConnectionState.LISTENING -> "Listening on port ${DumbDisplayServer.DEFAULT_PORT}..."
                            DumbDisplayServer.ConnectionState.ERROR -> "Error"
                            DumbDisplayServer.ConnectionState.STOPPED -> "Stopped"
                        },
                        color = Color.White,
                        style = MaterialTheme.typography.bodyMedium,
                        modifier = Modifier.padding(start = 8.dp)
                    )
                }

                IconButton(
                    onClick = {
                        if (connectionState == DumbDisplayServer.ConnectionState.STOPPED ||
                            connectionState == DumbDisplayServer.ConnectionState.ERROR) {
                            server.start()
                        } else {
                            server.stop()
                        }
                    }
                ) {
                    Icon(
                        imageVector = if (connectionState == DumbDisplayServer.ConnectionState.STOPPED ||
                            connectionState == DumbDisplayServer.ConnectionState.ERROR)
                            Icons.Default.PlayArrow else Icons.Default.Close,
                        contentDescription = "Toggle server",
                        tint = Color.White
                    )
                }
            }
        }

        Spacer(modifier = Modifier.height(16.dp))

        // Display canvas
        Card(
            modifier = Modifier
                .fillMaxWidth()
                .weight(1f),
            colors = CardDefaults.cardColors(containerColor = Color.Black),
            shape = RoundedCornerShape(12.dp)
        ) {
            DumbDisplayCanvas(
                server = server,
                modifier = Modifier.fillMaxSize()
            )
        }
    }
}
