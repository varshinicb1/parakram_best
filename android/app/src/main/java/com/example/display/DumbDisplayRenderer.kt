package com.example.display

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.nativeCanvas
import androidx.compose.ui.unit.dp
import kotlin.math.cos
import kotlin.math.sin

/**
 * Jetpack Compose renderer for DumbDisplay commands.
 * Consumes commands from [DumbDisplayServer] and renders them on a Canvas.
 */
@Composable
fun DumbDisplayCanvas(
    server: DumbDisplayServer,
    modifier: Modifier = Modifier
) {
    val drawCommands = remember { mutableStateListOf<DumbDisplayCommand>() }
    val lcdTexts = remember { mutableStateMapOf<String, MutableMap<String, String>>() }
    val ledGrid = remember { mutableStateMapOf<String, MutableMap<String, String>>() }
    val turtleState = remember { mutableStateMapOf<String, TurtleState>() }
    val turtleLines = remember { mutableStateListOf<TurtleLine>() }

    LaunchedEffect(server) {
        server.commands.collect { command ->
            when (command) {
                is DumbDisplayCommand.ClearAll -> {
                    drawCommands.clear()
                    lcdTexts.clear()
                    ledGrid.clear()
                    turtleState.clear()
                    turtleLines.clear()
                }
                is DumbDisplayCommand.Ping -> {
                    server.sendResponse("PONG")
                }
                is DumbDisplayCommand.Version -> {
                    server.sendResponse("Parakram DumbDisplay Server v1.0.0")
                }

                // LCD
                is DumbDisplayCommand.CreateLcdLayer -> {
                    lcdTexts.getOrPut(command.layerId) { mutableMapOf() }
                }
                is DumbDisplayCommand.LcdWriteText -> {
                    val key = "${command.row}:${command.col}"
                    lcdTexts.getOrPut(command.layerId) { mutableMapOf() }[key] = command.text
                }
                is DumbDisplayCommand.LcdClear -> {
                    lcdTexts[command.layerId]?.clear()
                }

                // LED
                is DumbDisplayCommand.CreateLedLayer -> {
                    ledGrid.getOrPut(command.layerId) { mutableMapOf() }
                }
                is DumbDisplayCommand.LedOn -> {
                    val key = "${command.x}:${command.y}"
                    ledGrid.getOrPut(command.layerId) { mutableMapOf() }[key] = command.color
                }
                is DumbDisplayCommand.LedOff -> {
                    val key = "${command.x}:${command.y}"
                    ledGrid[command.layerId]?.remove(key)
                }

                // Turtle
                is DumbDisplayCommand.CreateTurtleLayer -> {
                    turtleState[command.layerId] = TurtleState(
                        x = command.width / 2f,
                        y = command.height / 2f
                    )
                }
                is DumbDisplayCommand.TurtleForward -> {
                    turtleState[command.layerId]?.let { state ->
                        val rad = Math.toRadians(state.angle.toDouble())
                        val newX = state.x + command.distance * cos(rad).toFloat()
                        val newY = state.y + command.distance * sin(rad).toFloat()
                        if (state.penDown) {
                            turtleLines.add(TurtleLine(state.x, state.y, newX, newY, state.penColor, state.penWidth))
                        }
                        state.x = newX
                        state.y = newY
                    }
                }
                is DumbDisplayCommand.TurtleBackward -> {
                    turtleState[command.layerId]?.let { state ->
                        val rad = Math.toRadians(state.angle.toDouble())
                        val newX = state.x - command.distance * cos(rad).toFloat()
                        val newY = state.y - command.distance * sin(rad).toFloat()
                        if (state.penDown) {
                            turtleLines.add(TurtleLine(state.x, state.y, newX, newY, state.penColor, state.penWidth))
                        }
                        state.x = newX
                        state.y = newY
                    }
                }
                is DumbDisplayCommand.TurtleTurn -> {
                    turtleState[command.layerId]?.let { it.angle += command.angleDegrees }
                }
                is DumbDisplayCommand.TurtlePenUp -> {
                    turtleState[command.layerId]?.penDown = false
                }
                is DumbDisplayCommand.TurtlePenDown -> {
                    turtleState[command.layerId]?.penDown = true
                }
                is DumbDisplayCommand.TurtlePenColor -> {
                    turtleState[command.layerId]?.penColor = command.color
                }
                is DumbDisplayCommand.TurtlePenWidth -> {
                    turtleState[command.layerId]?.penWidth = command.width
                }
                is DumbDisplayCommand.TurtleHome -> {
                    turtleState[command.layerId]?.let {
                        it.x = 160f; it.y = 120f; it.angle = 0f
                    }
                }

                // Graphical commands are stored for canvas rendering
                else -> drawCommands.add(command)
            }
        }
    }

    Column(modifier = modifier.fillMaxSize()) {
        // LCD text area
        if (lcdTexts.isNotEmpty()) {
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(Color(0xFF1A1A2E))
                    .padding(8.dp)
            ) {
                Column {
                    lcdTexts.forEach { (_, texts) ->
                        texts.entries.sortedBy { it.key }.forEach { (_, text) ->
                            Text(
                                text = text,
                                color = Color(0xFF00FF41),
                                style = MaterialTheme.typography.bodyLarge,
                                fontFamily = androidx.compose.ui.text.font.FontFamily.Monospace
                            )
                        }
                    }
                }
            }
        }

        // LED grid area
        if (ledGrid.isNotEmpty()) {
            Canvas(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(120.dp)
                    .background(Color.Black)
            ) {
                val cellW = size.width / 8f
                val cellH = size.height / 8f
                ledGrid.forEach { (_, pixels) ->
                    pixels.forEach { (key, colorHex) ->
                        val (x, y) = key.split(":").map { it.toIntOrNull() ?: 0 }
                        drawRect(
                            color = parseHexColor(colorHex),
                            topLeft = Offset(x * cellW, y * cellH),
                            size = Size(cellW - 1f, cellH - 1f)
                        )
                    }
                }
            }
        }

        // Graphical + Turtle canvas
        Canvas(
            modifier = Modifier
                .fillMaxSize()
                .background(Color.Black)
        ) {
            // Render graphical commands
            for (cmd in drawCommands) {
                renderGraphicalCommand(cmd)
            }

            // Render turtle lines
            for (line in turtleLines) {
                drawLine(
                    color = parseHexColor(line.color),
                    start = Offset(line.x1, line.y1),
                    end = Offset(line.x2, line.y2),
                    strokeWidth = line.width
                )
            }
        }
    }
}

private fun DrawScope.renderGraphicalCommand(cmd: DumbDisplayCommand) {
    when (cmd) {
        is DumbDisplayCommand.GfxDrawLine -> {
            drawLine(
                color = parseHexColor(cmd.color),
                start = Offset(cmd.x1.toFloat(), cmd.y1.toFloat()),
                end = Offset(cmd.x2.toFloat(), cmd.y2.toFloat()),
                strokeWidth = 2f
            )
        }
        is DumbDisplayCommand.GfxDrawRect -> {
            if (cmd.filled) {
                drawRect(
                    color = parseHexColor(cmd.color),
                    topLeft = Offset(cmd.x.toFloat(), cmd.y.toFloat()),
                    size = Size(cmd.w.toFloat(), cmd.h.toFloat())
                )
            } else {
                drawRect(
                    color = parseHexColor(cmd.color),
                    topLeft = Offset(cmd.x.toFloat(), cmd.y.toFloat()),
                    size = Size(cmd.w.toFloat(), cmd.h.toFloat()),
                    style = Stroke(width = 2f)
                )
            }
        }
        is DumbDisplayCommand.GfxDrawCircle -> {
            if (cmd.filled) {
                drawCircle(
                    color = parseHexColor(cmd.color),
                    radius = cmd.radius.toFloat(),
                    center = Offset(cmd.cx.toFloat(), cmd.cy.toFloat())
                )
            } else {
                drawCircle(
                    color = parseHexColor(cmd.color),
                    radius = cmd.radius.toFloat(),
                    center = Offset(cmd.cx.toFloat(), cmd.cy.toFloat()),
                    style = Stroke(width = 2f)
                )
            }
        }
        is DumbDisplayCommand.GfxDrawText -> {
            drawContext.canvas.nativeCanvas.drawText(
                cmd.text,
                cmd.x.toFloat(),
                cmd.y.toFloat(),
                android.graphics.Paint().apply {
                    color = android.graphics.Color.parseColor("#${cmd.color}")
                    textSize = cmd.size.toFloat()
                    isAntiAlias = true
                }
            )
        }
        is DumbDisplayCommand.GfxClear -> {
            drawRect(
                color = parseHexColor(cmd.color),
                topLeft = Offset.Zero,
                size = size
            )
        }
        is DumbDisplayCommand.CreateGraphicalLayer,
        is DumbDisplayCommand.CreateLcdLayer,
        is DumbDisplayCommand.CreateLedLayer,
        is DumbDisplayCommand.CreateTurtleLayer -> { /* handled in LaunchedEffect */ }
        else -> { /* LCD/LED/Turtle/system commands handled elsewhere */ }
    }
}

private fun parseHexColor(hex: String): Color {
    return try {
        val h = hex.removePrefix("#")
        Color(android.graphics.Color.parseColor("#$h"))
    } catch (_: Exception) {
        Color.White
    }
}

data class TurtleLine(
    val x1: Float, val y1: Float,
    val x2: Float, val y2: Float,
    val color: String, val width: Float
)

data class TurtleState(
    var x: Float,
    var y: Float,
    var angle: Float = 0f,
    var penDown: Boolean = true,
    var penColor: String = "FFFFFF",
    var penWidth: Float = 2f
)
