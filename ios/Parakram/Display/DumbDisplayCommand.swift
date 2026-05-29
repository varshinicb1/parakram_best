import Foundation
import SwiftUI

/// All DumbDisplay protocol commands.
/// The board sends these as pipe-delimited text over TCP (port 10201).
/// The iOS app parses them and renders via SwiftUI Canvas.
enum DumbDisplayCommand {
    // Layer creation
    case createLcdLayer(layerId: String, cols: Int, rows: Int)
    case createLedLayer(layerId: String, cols: Int, rows: Int)
    case createGraphicalLayer(layerId: String, width: Int, height: Int)
    case createTurtleLayer(layerId: String, width: Int, height: Int)

    // LCD operations
    case lcdWriteText(layerId: String, col: Int, row: Int, text: String)
    case lcdClear(layerId: String)

    // LED grid operations
    case ledOn(layerId: String, x: Int, y: Int, color: String)
    case ledOff(layerId: String, x: Int, y: Int)

    // Graphical operations
    case gfxDrawLine(layerId: String, x1: Int, y1: Int, x2: Int, y2: Int, color: String)
    case gfxDrawRect(layerId: String, x: Int, y: Int, w: Int, h: Int, color: String, filled: Bool)
    case gfxDrawCircle(layerId: String, cx: Int, cy: Int, radius: Int, color: String, filled: Bool)
    case gfxDrawText(layerId: String, x: Int, y: Int, text: String, size: Int, color: String)
    case gfxClear(layerId: String, color: String)

    // Turtle graphics
    case turtleForward(layerId: String, distance: Float)
    case turtleBackward(layerId: String, distance: Float)
    case turtleTurn(layerId: String, angleDegrees: Float)
    case turtlePenUp(layerId: String)
    case turtlePenDown(layerId: String)
    case turtlePenColor(layerId: String, color: String)
    case turtlePenWidth(layerId: String, width: Float)
    case turtleHome(layerId: String)

    // System
    case clearAll
    case ping
    case version
}

/// Parse a pipe-delimited DumbDisplay protocol line into a command.
func parseDumbDisplayCommand(_ line: String) -> DumbDisplayCommand? {
    let parts = line.split(separator: "|").map(String.init)
    guard let verb = parts.first else { return nil }

    switch verb {
    case "HELLO":
        return .version
    case "PING":
        return .ping
    case "CLEAR_ALL":
        return .clearAll
    case "CREATE_LCD" where parts.count >= 4:
        return .createLcdLayer(
            layerId: parts[1],
            cols: Int(parts[2]) ?? 16,
            rows: Int(parts[3]) ?? 2
        )
    case "CREATE_LED" where parts.count >= 4:
        return .createLedLayer(
            layerId: parts[1],
            cols: Int(parts[2]) ?? 8,
            rows: Int(parts[3]) ?? 8
        )
    case "CREATE_GFX" where parts.count >= 4:
        return .createGraphicalLayer(
            layerId: parts[1],
            width: Int(parts[2]) ?? 320,
            height: Int(parts[3]) ?? 240
        )
    case "CREATE_TURTLE" where parts.count >= 4:
        return .createTurtleLayer(
            layerId: parts[1],
            width: Int(parts[2]) ?? 320,
            height: Int(parts[3]) ?? 240
        )
    case "LCD_TEXT" where parts.count >= 5:
        return .lcdWriteText(
            layerId: parts[1],
            col: Int(parts[2]) ?? 0,
            row: Int(parts[3]) ?? 0,
            text: parts[4]
        )
    case "LCD_CLEAR" where parts.count >= 2:
        return .lcdClear(layerId: parts[1])
    case "LED_ON" where parts.count >= 5:
        return .ledOn(
            layerId: parts[1],
            x: Int(parts[2]) ?? 0,
            y: Int(parts[3]) ?? 0,
            color: parts.count > 4 ? parts[4] : "FF0000"
        )
    case "LED_OFF" where parts.count >= 4:
        return .ledOff(
            layerId: parts[1],
            x: Int(parts[2]) ?? 0,
            y: Int(parts[3]) ?? 0
        )
    case "GFX_LINE" where parts.count >= 7:
        return .gfxDrawLine(
            layerId: parts[1],
            x1: Int(parts[2]) ?? 0, y1: Int(parts[3]) ?? 0,
            x2: Int(parts[4]) ?? 0, y2: Int(parts[5]) ?? 0,
            color: parts[6]
        )
    case "GFX_RECT" where parts.count >= 8:
        return .gfxDrawRect(
            layerId: parts[1],
            x: Int(parts[2]) ?? 0, y: Int(parts[3]) ?? 0,
            w: Int(parts[4]) ?? 0, h: Int(parts[5]) ?? 0,
            color: parts[6],
            filled: parts[7] == "1"
        )
    case "GFX_CIRCLE" where parts.count >= 7:
        return .gfxDrawCircle(
            layerId: parts[1],
            cx: Int(parts[2]) ?? 0, cy: Int(parts[3]) ?? 0,
            radius: Int(parts[4]) ?? 0,
            color: parts[5],
            filled: parts[6] == "1"
        )
    case "GFX_TEXT" where parts.count >= 7:
        return .gfxDrawText(
            layerId: parts[1],
            x: Int(parts[2]) ?? 0, y: Int(parts[3]) ?? 0,
            text: parts[4],
            size: Int(parts[5]) ?? 14,
            color: parts[6]
        )
    case "GFX_CLEAR" where parts.count >= 3:
        return .gfxClear(layerId: parts[1], color: parts[2])
    case "TRT_FWD" where parts.count >= 3:
        return .turtleForward(layerId: parts[1], distance: Float(parts[2]) ?? 10)
    case "TRT_BWD" where parts.count >= 3:
        return .turtleBackward(layerId: parts[1], distance: Float(parts[2]) ?? 10)
    case "TRT_TURN" where parts.count >= 3:
        return .turtleTurn(layerId: parts[1], angleDegrees: Float(parts[2]) ?? 90)
    case "TRT_PU" where parts.count >= 2:
        return .turtlePenUp(layerId: parts[1])
    case "TRT_PD" where parts.count >= 2:
        return .turtlePenDown(layerId: parts[1])
    case "TRT_PC" where parts.count >= 3:
        return .turtlePenColor(layerId: parts[1], color: parts[2])
    case "TRT_PW" where parts.count >= 3:
        return .turtlePenWidth(layerId: parts[1], width: Float(parts[2]) ?? 2)
    case "TRT_HOME" where parts.count >= 2:
        return .turtleHome(layerId: parts[1])
    default:
        return nil
    }
}

/// Parse a hex color string to SwiftUI Color.
func colorFromHex(_ hex: String) -> Color {
    let clean = hex.trimmingCharacters(in: CharacterSet(charactersIn: "#"))
    guard clean.count == 6, let val = UInt64(clean, radix: 16) else {
        return .white
    }
    return Color(
        red: Double((val >> 16) & 0xFF) / 255.0,
        green: Double((val >> 8) & 0xFF) / 255.0,
        blue: Double(val & 0xFF) / 255.0
    )
}
