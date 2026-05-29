import SwiftUI
import Combine

/// SwiftUI view that renders DumbDisplay commands from the ESP32 board.
/// Acts as a "GPU" for the microcontroller — the board sends draw commands
/// over TCP (port 10201) and this view renders them in real time.
struct DisplayView: View {
    @StateObject private var service = DumbDisplayService()
    @State private var drawOps: [DrawOp] = []
    @State private var lcdLines: [String: [String]] = [:]
    @State private var cancellables = Set<AnyCancellable>()

    var body: some View {
        VStack(spacing: 0) {
            headerBar
            displayCanvas
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            statusBar
        }
        .background(Color.black)
        .onAppear { startService() }
        .onDisappear { service.stop() }
    }

    private var headerBar: some View {
        HStack {
            Image(systemName: "display")
                .foregroundColor(.cyan)
            Text("DumbDisplay")
                .font(.headline)
                .foregroundColor(.white)
            Spacer()
            statusIndicator
        }
        .padding(.horizontal)
        .padding(.vertical, 8)
        .background(Color(white: 0.1))
    }

    private var statusIndicator: some View {
        HStack(spacing: 6) {
            Circle()
                .fill(statusColor)
                .frame(width: 8, height: 8)
            Text(service.state.rawValue.capitalized)
                .font(.caption)
                .foregroundColor(.gray)
        }
    }

    private var statusColor: Color {
        switch service.state {
        case .stopped: return .gray
        case .listening: return .yellow
        case .connected: return .green
        case .error: return .red
        }
    }

    private var displayCanvas: some View {
        Canvas { context, size in
            // Draw background
            context.fill(Path(CGRect(origin: .zero, size: size)), with: .color(.black))

            // Render all draw operations
            for op in drawOps {
                renderOp(op, in: &context, size: size)
            }

            // Render LCD text layers
            for (_, lines) in lcdLines {
                for (row, text) in lines.enumerated() {
                    let point = CGPoint(x: 10, y: 20 + row * 20)
                    context.draw(
                        Text(text).font(.system(size: 14, design: .monospaced)).foregroundColor(.green),
                        at: point,
                        anchor: .topLeading
                    )
                }
            }
        }
    }

    private var statusBar: some View {
        HStack {
            if let ip = service.connectedDeviceIP {
                Label(ip, systemImage: "wifi")
                    .font(.caption2)
                    .foregroundColor(.green)
            } else {
                Label("Port 10201", systemImage: "antenna.radiowaves.left.and.right")
                    .font(.caption2)
                    .foregroundColor(.gray)
            }
            Spacer()
            Text("\(drawOps.count) ops")
                .font(.caption2)
                .foregroundColor(.gray)
        }
        .padding(.horizontal)
        .padding(.vertical, 6)
        .background(Color(white: 0.1))
    }

    private func startService() {
        service.start()
        service.commandSubject
            .receive(on: DispatchQueue.main)
            .sink { cmd in handleCommand(cmd) }
            .store(in: &cancellables)
    }

    private func handleCommand(_ cmd: DumbDisplayCommand) {
        switch cmd {
        case .clearAll:
            drawOps.removeAll()
            lcdLines.removeAll()

        case .lcdWriteText(let id, _, let row, let text):
            if lcdLines[id] == nil { lcdLines[id] = [] }
            while lcdLines[id]!.count <= row { lcdLines[id]!.append("") }
            lcdLines[id]![row] = text

        case .lcdClear(let id):
            lcdLines[id] = []

        case .gfxDrawLine(_, let x1, let y1, let x2, let y2, let color):
            drawOps.append(.line(
                from: CGPoint(x: x1, y: y1),
                to: CGPoint(x: x2, y: y2),
                color: colorFromHex(color)
            ))

        case .gfxDrawRect(_, let x, let y, let w, let h, let color, let filled):
            drawOps.append(.rect(
                rect: CGRect(x: x, y: y, width: w, height: h),
                color: colorFromHex(color),
                filled: filled
            ))

        case .gfxDrawCircle(_, let cx, let cy, let r, let color, let filled):
            drawOps.append(.circle(
                center: CGPoint(x: cx, y: cy),
                radius: CGFloat(r),
                color: colorFromHex(color),
                filled: filled
            ))

        case .gfxDrawText(_, let x, let y, let text, let size, let color):
            drawOps.append(.text(
                position: CGPoint(x: x, y: y),
                content: text,
                size: CGFloat(size),
                color: colorFromHex(color)
            ))

        case .gfxClear(let id, let color):
            drawOps.removeAll()
            drawOps.append(.rect(
                rect: CGRect(x: 0, y: 0, width: 9999, height: 9999),
                color: colorFromHex(color),
                filled: true
            ))

        default:
            break
        }
    }

    private func renderOp(_ op: DrawOp, in context: inout GraphicsContext, size: CGSize) {
        switch op {
        case .line(let from, let to, let color):
            var path = Path()
            path.move(to: from)
            path.addLine(to: to)
            context.stroke(path, with: .color(color), lineWidth: 2)

        case .rect(let rect, let color, let filled):
            let path = Path(rect)
            if filled {
                context.fill(path, with: .color(color))
            } else {
                context.stroke(path, with: .color(color), lineWidth: 1)
            }

        case .circle(let center, let radius, let color, let filled):
            let rect = CGRect(
                x: center.x - radius, y: center.y - radius,
                width: radius * 2, height: radius * 2
            )
            let path = Path(ellipseIn: rect)
            if filled {
                context.fill(path, with: .color(color))
            } else {
                context.stroke(path, with: .color(color), lineWidth: 1)
            }

        case .text(let pos, let content, let fontSize, let color):
            context.draw(
                Text(content).font(.system(size: fontSize)).foregroundColor(color),
                at: pos,
                anchor: .topLeading
            )
        }
    }
}

private enum DrawOp {
    case line(from: CGPoint, to: CGPoint, color: Color)
    case rect(rect: CGRect, color: Color, filled: Bool)
    case circle(center: CGPoint, radius: CGFloat, color: Color, filled: Bool)
    case text(position: CGPoint, content: String, size: CGFloat, color: Color)
}
