package com.example.display

/**
 * Sealed class representing all DumbDisplay protocol commands.
 * The board sends these as pipe-delimited text over TCP (port 10201).
 * The phone app parses them and renders via Jetpack Compose Canvas.
 */
sealed class DumbDisplayCommand {

    // Layer creation
    data class CreateLcdLayer(val layerId: String, val cols: Int, val rows: Int) : DumbDisplayCommand()
    data class CreateLedLayer(val layerId: String, val cols: Int, val rows: Int) : DumbDisplayCommand()
    data class CreateGraphicalLayer(val layerId: String, val width: Int, val height: Int) : DumbDisplayCommand()
    data class CreateTurtleLayer(val layerId: String, val width: Int, val height: Int) : DumbDisplayCommand()

    // LCD operations
    data class LcdWriteText(val layerId: String, val col: Int, val row: Int, val text: String) : DumbDisplayCommand()
    data class LcdClear(val layerId: String) : DumbDisplayCommand()

    // LED grid operations
    data class LedOn(val layerId: String, val x: Int, val y: Int, val color: String) : DumbDisplayCommand()
    data class LedOff(val layerId: String, val x: Int, val y: Int) : DumbDisplayCommand()

    // Graphical operations
    data class GfxDrawLine(
        val layerId: String, val x1: Int, val y1: Int, val x2: Int, val y2: Int, val color: String
    ) : DumbDisplayCommand()
    data class GfxDrawRect(
        val layerId: String, val x: Int, val y: Int, val w: Int, val h: Int,
        val color: String, val filled: Boolean
    ) : DumbDisplayCommand()
    data class GfxDrawCircle(
        val layerId: String, val cx: Int, val cy: Int, val radius: Int,
        val color: String, val filled: Boolean
    ) : DumbDisplayCommand()
    data class GfxDrawText(
        val layerId: String, val x: Int, val y: Int, val text: String,
        val size: Int, val color: String
    ) : DumbDisplayCommand()
    data class GfxClear(val layerId: String, val color: String) : DumbDisplayCommand()

    // Turtle graphics operations
    data class TurtleForward(val layerId: String, val distance: Float) : DumbDisplayCommand()
    data class TurtleBackward(val layerId: String, val distance: Float) : DumbDisplayCommand()
    data class TurtleTurn(val layerId: String, val angleDegrees: Float) : DumbDisplayCommand()
    data class TurtlePenUp(val layerId: String) : DumbDisplayCommand()
    data class TurtlePenDown(val layerId: String) : DumbDisplayCommand()
    data class TurtlePenColor(val layerId: String, val color: String) : DumbDisplayCommand()
    data class TurtlePenWidth(val layerId: String, val width: Float) : DumbDisplayCommand()
    data class TurtleHome(val layerId: String) : DumbDisplayCommand()

    // System commands
    data object ClearAll : DumbDisplayCommand()
    data object Ping : DumbDisplayCommand()
    data object Version : DumbDisplayCommand()
}
