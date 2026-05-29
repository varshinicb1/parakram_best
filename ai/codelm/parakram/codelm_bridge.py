"""API layer for Parakram frontend integration.

Exposes CodeLM as a local HTTP service that the Parakram backend
can call for block-token firmware generation.
"""

import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

from model.inference import generate_firmware, FirmwareResult


class CodeLMHandler(BaseHTTPRequestHandler):
    """HTTP handler for CodeLM bridge API."""

    def do_POST(self) -> None:
        path = urlparse(self.path).path

        if path == "/api/codelm/generate":
            self._handle_generate()
        elif path == "/api/codelm/health":
            self._respond_json({"status": "ok", "model": "codelm-v1"})
        else:
            self._respond_json({"error": "not found"}, 404)

    def do_GET(self) -> None:
        path = urlparse(self.path).path

        if path == "/api/codelm/health":
            self._respond_json({"status": "ok", "model": "codelm-v1"})
        else:
            self._respond_json({"error": "not found"}, 404)

    def _handle_generate(self) -> None:
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            data = json.loads(body)

            intent = data.get("intent", "")
            target_mcu = data.get("target_mcu", "esp32s3")

            if not intent:
                self._respond_json({"error": "intent is required"}, 400)
                return

            result = generate_firmware(intent=intent, target_mcu=target_mcu)
            self._respond_json({
                "block_sequence": result.block_sequence,
                "source_code": result.source_code,
                "target_mcu": result.target_mcu,
                "confidence": result.confidence,
                "constraint_scores": result.constraint_scores,
            })

        except Exception as e:
            self._respond_json({"error": str(e)}, 500)

    def _respond_json(self, data: dict, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def log_message(self, format: str, *args) -> None:
        pass  # Suppress default logging


def start_bridge_server(port: int = 8401) -> None:
    """Start the CodeLM bridge HTTP server."""
    server = HTTPServer(("0.0.0.0", port), CodeLMHandler)
    print(f"CodeLM bridge server running on port {port}")
    print(f"  POST /api/codelm/generate  — generate firmware")
    print(f"  GET  /api/codelm/health    — health check")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()
        print("\nServer stopped.")
