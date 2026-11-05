import os
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable

from core.ai import AzureContentSafety, AzureOpenAIIntentParser
from core.config import AppConfig
from core.database import CosmosAtomicLedger
from core.kernel.handshake import LoomKernel
from core.security import AuthorityVerifier


def create_kernel_from_config(config: AppConfig) -> LoomKernel:
    mode = config.mode.strip().lower()
    intent_parser = None
    safety_checker = None
    db = None

    if mode == "azure":
        intent_parser = AzureOpenAIIntentParser(
            endpoint=config.azure_openai_endpoint,
            api_key=config.azure_openai_api_key,
            api_version=config.azure_openai_api_version,
            deployment=config.azure_openai_deployment,
        )
        safety_checker = AzureContentSafety(
            endpoint=config.content_safety_endpoint,
            key=config.content_safety_key,
            block_threshold=config.content_safety_block_threshold,
        )
        db = CosmosAtomicLedger(
            endpoint=config.cosmos_endpoint,
            key=config.cosmos_key,
            database_name=config.cosmos_database,
            container_name=config.cosmos_container,
        )
    elif mode != "local":
        raise ValueError("LOOM_MODE must be either 'local' or 'azure'")

    return LoomKernel(
        db=db,
        intent_parser=intent_parser,
        safety_checker=safety_checker,
        authority_verifier=AuthorityVerifier(
            shared_secret=config.shared_secret,
            require_signature=config.require_signature,
        )
    )


def create_handler(kernel: LoomKernel) -> Callable:
    class LoomRequestHandler(BaseHTTPRequestHandler):
        server_version = "LoomATP/1.0"

        def do_GET(self):
            if self.path == "/health":
                self._send_json(200, {"status": "ok", "service": "loom-atp"})
                return
            self._send_json(404, {"error": "not_found"})

        def do_OPTIONS(self):
            self.send_response(204)
            self._send_cors_headers()
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Access-Control-Max-Age", "600")
            self.end_headers()

        def do_POST(self):
            if self.path != "/v1/handshake":
                self._send_json(404, {"error": "not_found"})
                return

            try:
                payload = self._read_json()
            except ValueError as exc:
                self._send_json(400, {"status": 400, "message": str(exc)})
                return

            response = kernel.process_handshake(payload)
            self._send_json(response["status"], response)

        def log_message(self, format, *args):
            return

        def _read_json(self):
            content_length = int(self.headers.get("Content-Length", "0"))
            if content_length <= 0:
                raise ValueError("request body must contain a JSON ATP packet")
            raw_body = self.rfile.read(content_length)
            try:
                payload = json.loads(raw_body.decode("utf-8"))
            except json.JSONDecodeError as exc:
                raise ValueError("request body must be valid JSON") from exc
            if not isinstance(payload, dict):
                raise ValueError("request body must be a JSON object")
            return payload

        def _send_json(self, status_code, payload):
            encoded = json.dumps(payload).encode("utf-8")
            self.send_response(status_code)
            self._send_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def _send_cors_headers(self):
            origin = self.headers.get("Origin")
            allowed_origins = {
                "http://127.0.0.1:5500",
                "http://localhost:5500",
            }
            extra = os.getenv("LOOM_ALLOWED_ORIGINS", "")
            allowed_origins.update(
                item.strip() for item in extra.split(",") if item.strip()
            )
            if origin in allowed_origins:
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Vary", "Origin")

    return LoomRequestHandler


class LoomAPIServer:
    def __init__(self, host: str, port: int, kernel: LoomKernel):
        self.host = host
        self.port = port
        self.kernel = kernel
        self.httpd = ThreadingHTTPServer((host, port), create_handler(kernel))

    def serve_forever(self):
        print(f"[Loom API] Serving ATP gateway on http://{self.host}:{self.port}")
        print("[Loom API] POST /v1/handshake with an ATP packet to reserve a resource.")
        self.httpd.serve_forever()


def main():
    config = AppConfig.from_env()
    server = LoomAPIServer(
        host=config.host,
        port=config.port,
        kernel=create_kernel_from_config(config),
    )
    server.serve_forever()


if __name__ == "__main__":
    main()
