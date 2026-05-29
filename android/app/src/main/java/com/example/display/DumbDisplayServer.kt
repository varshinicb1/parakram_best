package com.example.display

import android.util.Log
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancelAndJoin
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.BufferedReader
import java.io.InputStreamReader
import java.io.PrintWriter
import java.net.ServerSocket
import java.net.Socket

/**
 * DumbDisplay TCP server — listens on port 10201 for draw commands from ESP32.
 *
 * Protocol: The board sends text-based directives (one per line) that describe
 * display operations. This server parses them into [DumbDisplayCommand] objects
 * and emits them via a SharedFlow for the Compose UI renderer to consume.
 *
 * Based on the DumbDisplay protocol from trevorwslee/Arduino-DumbDisplay.
 */
class DumbDisplayServer {

    companion object {
        private const val TAG = "DumbDisplayServer"
        const val DEFAULT_PORT = 10201
    }

    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private var serverJob: Job? = null
    private var serverSocket: ServerSocket? = null
    private var clientSocket: Socket? = null

    private val _commands = MutableSharedFlow<DumbDisplayCommand>(extraBufferCapacity = 256)
    val commands: SharedFlow<DumbDisplayCommand> = _commands.asSharedFlow()

    private val _connectionState = MutableStateFlow(ConnectionState.STOPPED)
    val connectionState: StateFlow<ConnectionState> = _connectionState.asStateFlow()

    private val _connectedDeviceIp = MutableStateFlow<String?>(null)
    val connectedDeviceIp: StateFlow<String?> = _connectedDeviceIp.asStateFlow()

    enum class ConnectionState {
        STOPPED, LISTENING, CONNECTED, ERROR
    }

    fun start(port: Int = DEFAULT_PORT) {
        if (serverJob?.isActive == true) return

        serverJob = scope.launch {
            try {
                serverSocket = ServerSocket(port)
                _connectionState.value = ConnectionState.LISTENING
                Log.i(TAG, "Listening on port $port")

                while (isActive) {
                    val socket = serverSocket?.accept() ?: break
                    clientSocket = socket
                    _connectedDeviceIp.value = socket.inetAddress.hostAddress
                    _connectionState.value = ConnectionState.CONNECTED
                    Log.i(TAG, "Board connected: ${socket.inetAddress.hostAddress}")

                    handleClient(socket)

                    _connectionState.value = ConnectionState.LISTENING
                    _connectedDeviceIp.value = null
                    Log.i(TAG, "Board disconnected, waiting for reconnect...")
                }
            } catch (e: Exception) {
                if (isActive) {
                    Log.e(TAG, "Server error: ${e.message}")
                    _connectionState.value = ConnectionState.ERROR
                }
            }
        }
    }

    fun stop() {
        scope.launch {
            try {
                clientSocket?.close()
                serverSocket?.close()
                serverJob?.cancelAndJoin()
            } catch (e: Exception) {
                Log.w(TAG, "Error stopping server: ${e.message}")
            }
            _connectionState.value = ConnectionState.STOPPED
            _connectedDeviceIp.value = null
        }
    }

    fun sendResponse(response: String) {
        scope.launch {
            withContext(Dispatchers.IO) {
                try {
                    clientSocket?.let { socket ->
                        if (!socket.isClosed) {
                            val writer = PrintWriter(socket.getOutputStream(), true)
                            writer.println(response)
                        }
                    }
                } catch (e: Exception) {
                    Log.w(TAG, "Failed to send response: ${e.message}")
                }
            }
        }
    }

    private suspend fun handleClient(socket: Socket) {
        withContext(Dispatchers.IO) {
            try {
                val reader = BufferedReader(InputStreamReader(socket.getInputStream()))
                var line: String?

                while (socket.isConnected && !socket.isClosed) {
                    line = reader.readLine() ?: break
                    val command = parseCommand(line)
                    if (command != null) {
                        _commands.emit(command)
                    }
                }
            } catch (e: Exception) {
                Log.w(TAG, "Client read error: ${e.message}")
            } finally {
                try { socket.close() } catch (_: Exception) {}
            }
        }
    }

    private fun parseCommand(line: String): DumbDisplayCommand? {
        if (line.isBlank()) return null
        val parts = line.trim().split("|")
        if (parts.isEmpty()) return null

        return when (parts[0]) {
            // Layer creation
            "LCD" -> DumbDisplayCommand.CreateLcdLayer(
                layerId = parts.getOrNull(1) ?: "0",
                cols = parts.getOrNull(2)?.toIntOrNull() ?: 16,
                rows = parts.getOrNull(3)?.toIntOrNull() ?: 2
            )
            "LED" -> DumbDisplayCommand.CreateLedLayer(
                layerId = parts.getOrNull(1) ?: "0",
                cols = parts.getOrNull(2)?.toIntOrNull() ?: 8,
                rows = parts.getOrNull(3)?.toIntOrNull() ?: 8
            )
            "GFX" -> DumbDisplayCommand.CreateGraphicalLayer(
                layerId = parts.getOrNull(1) ?: "0",
                width = parts.getOrNull(2)?.toIntOrNull() ?: 320,
                height = parts.getOrNull(3)?.toIntOrNull() ?: 240
            )
            "TRT" -> DumbDisplayCommand.CreateTurtleLayer(
                layerId = parts.getOrNull(1) ?: "0",
                width = parts.getOrNull(2)?.toIntOrNull() ?: 320,
                height = parts.getOrNull(3)?.toIntOrNull() ?: 240
            )

            // LCD operations
            "LT" -> DumbDisplayCommand.LcdWriteText(
                layerId = parts.getOrNull(1) ?: "0",
                col = parts.getOrNull(2)?.toIntOrNull() ?: 0,
                row = parts.getOrNull(3)?.toIntOrNull() ?: 0,
                text = parts.getOrNull(4) ?: ""
            )
            "LC" -> DumbDisplayCommand.LcdClear(
                layerId = parts.getOrNull(1) ?: "0"
            )

            // LED operations
            "LO" -> DumbDisplayCommand.LedOn(
                layerId = parts.getOrNull(1) ?: "0",
                x = parts.getOrNull(2)?.toIntOrNull() ?: 0,
                y = parts.getOrNull(3)?.toIntOrNull() ?: 0,
                color = parts.getOrNull(4) ?: "FFFFFF"
            )
            "LF" -> DumbDisplayCommand.LedOff(
                layerId = parts.getOrNull(1) ?: "0",
                x = parts.getOrNull(2)?.toIntOrNull() ?: 0,
                y = parts.getOrNull(3)?.toIntOrNull() ?: 0
            )

            // Graphical operations
            "GL" -> DumbDisplayCommand.GfxDrawLine(
                layerId = parts.getOrNull(1) ?: "0",
                x1 = parts.getOrNull(2)?.toIntOrNull() ?: 0,
                y1 = parts.getOrNull(3)?.toIntOrNull() ?: 0,
                x2 = parts.getOrNull(4)?.toIntOrNull() ?: 0,
                y2 = parts.getOrNull(5)?.toIntOrNull() ?: 0,
                color = parts.getOrNull(6) ?: "FFFFFF"
            )
            "GR" -> DumbDisplayCommand.GfxDrawRect(
                layerId = parts.getOrNull(1) ?: "0",
                x = parts.getOrNull(2)?.toIntOrNull() ?: 0,
                y = parts.getOrNull(3)?.toIntOrNull() ?: 0,
                w = parts.getOrNull(4)?.toIntOrNull() ?: 0,
                h = parts.getOrNull(5)?.toIntOrNull() ?: 0,
                color = parts.getOrNull(6) ?: "FFFFFF",
                filled = parts.getOrNull(7) == "1"
            )
            "GC" -> DumbDisplayCommand.GfxDrawCircle(
                layerId = parts.getOrNull(1) ?: "0",
                cx = parts.getOrNull(2)?.toIntOrNull() ?: 0,
                cy = parts.getOrNull(3)?.toIntOrNull() ?: 0,
                radius = parts.getOrNull(4)?.toIntOrNull() ?: 0,
                color = parts.getOrNull(5) ?: "FFFFFF",
                filled = parts.getOrNull(6) == "1"
            )
            "GT" -> DumbDisplayCommand.GfxDrawText(
                layerId = parts.getOrNull(1) ?: "0",
                x = parts.getOrNull(2)?.toIntOrNull() ?: 0,
                y = parts.getOrNull(3)?.toIntOrNull() ?: 0,
                text = parts.getOrNull(4) ?: "",
                size = parts.getOrNull(5)?.toIntOrNull() ?: 12,
                color = parts.getOrNull(6) ?: "FFFFFF"
            )
            "GX" -> DumbDisplayCommand.GfxClear(
                layerId = parts.getOrNull(1) ?: "0",
                color = parts.getOrNull(2) ?: "000000"
            )

            // Turtle operations
            "TF" -> DumbDisplayCommand.TurtleForward(
                layerId = parts.getOrNull(1) ?: "0",
                distance = parts.getOrNull(2)?.toFloatOrNull() ?: 0f
            )
            "TB" -> DumbDisplayCommand.TurtleBackward(
                layerId = parts.getOrNull(1) ?: "0",
                distance = parts.getOrNull(2)?.toFloatOrNull() ?: 0f
            )
            "TR" -> DumbDisplayCommand.TurtleTurn(
                layerId = parts.getOrNull(1) ?: "0",
                angleDegrees = parts.getOrNull(2)?.toFloatOrNull() ?: 0f
            )
            "TU" -> DumbDisplayCommand.TurtlePenUp(
                layerId = parts.getOrNull(1) ?: "0"
            )
            "TD" -> DumbDisplayCommand.TurtlePenDown(
                layerId = parts.getOrNull(1) ?: "0"
            )
            "TC" -> DumbDisplayCommand.TurtlePenColor(
                layerId = parts.getOrNull(1) ?: "0",
                color = parts.getOrNull(2) ?: "FFFFFF"
            )
            "TW" -> DumbDisplayCommand.TurtlePenWidth(
                layerId = parts.getOrNull(1) ?: "0",
                width = parts.getOrNull(2)?.toFloatOrNull() ?: 2f
            )
            "TH" -> DumbDisplayCommand.TurtleHome(
                layerId = parts.getOrNull(1) ?: "0"
            )

            // System
            "CLR" -> DumbDisplayCommand.ClearAll
            "PNG" -> DumbDisplayCommand.Ping
            "VER" -> DumbDisplayCommand.Version

            else -> {
                Log.d(TAG, "Unknown command: $line")
                null
            }
        }
    }
}
