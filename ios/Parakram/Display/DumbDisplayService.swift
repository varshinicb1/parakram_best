import Foundation
import Network
import Combine
import os.log

/// TCP server that listens on port 10201 for DumbDisplay commands from ESP32.
/// The board sends pipe-delimited draw directives; this service parses them
/// and publishes DumbDisplayCommand objects for the SwiftUI renderer.
@MainActor
final class DumbDisplayService: ObservableObject {

    static let defaultPort: UInt16 = 10201
    private let logger = Logger(subsystem: "com.vidyuthlabs.parakram", category: "DumbDisplay")

    enum ConnectionState: String {
        case stopped, listening, connected, error
    }

    @Published var state: ConnectionState = .stopped
    @Published var connectedDeviceIP: String?

    let commandSubject = PassthroughSubject<DumbDisplayCommand, Never>()

    private var listener: NWListener?
    private var connection: NWConnection?
    private var buffer = Data()

    func start(port: UInt16 = defaultPort) {
        guard listener == nil else { return }

        do {
            let params = NWParameters.tcp
            params.allowLocalEndpointReuse = true
            let nwPort = NWEndpoint.Port(rawValue: port)!
            listener = try NWListener(using: params, on: nwPort)
        } catch {
            logger.error("Failed to create listener: \(error.localizedDescription)")
            state = .error
            return
        }

        listener?.stateUpdateHandler = { [weak self] newState in
            Task { @MainActor in
                guard let self else { return }
                switch newState {
                case .ready:
                    self.state = .listening
                    self.logger.info("Listening on port \(port)")
                case .failed(let err):
                    self.logger.error("Listener failed: \(err.localizedDescription)")
                    self.state = .error
                default:
                    break
                }
            }
        }

        listener?.newConnectionHandler = { [weak self] conn in
            Task { @MainActor in
                self?.handleNewConnection(conn)
            }
        }

        listener?.start(queue: .global(qos: .userInitiated))
        state = .listening
    }

    func stop() {
        connection?.cancel()
        listener?.cancel()
        connection = nil
        listener = nil
        state = .stopped
        connectedDeviceIP = nil
    }

    func sendResponse(_ text: String) {
        guard let conn = connection else { return }
        let data = Data((text + "\n").utf8)
        conn.send(content: data, completion: .contentProcessed { error in
            if let error {
                self.logger.warning("Send failed: \(error.localizedDescription)")
            }
        })
    }

    private func handleNewConnection(_ conn: NWConnection) {
        connection?.cancel()
        connection = conn

        if case .hostPort(let host, _) = conn.endpoint {
            connectedDeviceIP = "\(host)"
        }

        conn.stateUpdateHandler = { [weak self] newState in
            Task { @MainActor in
                guard let self else { return }
                switch newState {
                case .ready:
                    self.state = .connected
                    self.logger.info("Board connected: \(self.connectedDeviceIP ?? "unknown")")
                    self.receiveLoop(conn)
                case .failed, .cancelled:
                    self.state = .listening
                    self.connectedDeviceIP = nil
                    self.logger.info("Board disconnected")
                default:
                    break
                }
            }
        }

        conn.start(queue: .global(qos: .userInitiated))
    }

    private func receiveLoop(_ conn: NWConnection) {
        conn.receive(minimumIncompleteLength: 1, maximumLength: 4096) { [weak self] data, _, isComplete, error in
            guard let self else { return }

            if let data {
                self.buffer.append(data)
                self.processBuffer()
            }

            if isComplete || error != nil {
                Task { @MainActor in
                    self.state = .listening
                    self.connectedDeviceIP = nil
                }
                return
            }

            self.receiveLoop(conn)
        }
    }

    private func processBuffer() {
        while let newlineIndex = buffer.firstIndex(of: UInt8(ascii: "\n")) {
            let lineData = buffer[buffer.startIndex..<newlineIndex]
            buffer.removeSubrange(buffer.startIndex...newlineIndex)

            guard let line = String(data: lineData, encoding: .utf8)?
                    .trimmingCharacters(in: .whitespacesAndNewlines),
                  !line.isEmpty else { continue }

            if let cmd = parseDumbDisplayCommand(line) {
                commandSubject.send(cmd)
            }
        }
    }
}
