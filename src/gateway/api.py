"""
API 感官 — HTTP API 接口，让其他系统可以跟 Nexus 对话。
"""

import asyncio
import json
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Callable

log = logging.getLogger("nexus.api")


class ApiSensor:
    """API 感官 — 提供 HTTP 接口"""

    def __init__(self, config: dict, message_handler: Callable):
        self.config = config
        self.handle_message = message_handler
        self.port = config.get("port", 8670)
        self.host = config.get("host", "127.0.0.1")
        self.server = None
        self.running = False

    def start(self):
        """启动 API 服务"""
        self.running = True
        log.info(f"API sensor ready on {self.host}:{self.port}")

    def stop(self):
        """停止 API 服务"""
        self.running = False
        if self.server:
            self.server.shutdown()
            log.info("API sensor stopped")

    def create_handler(self):
        """创建 HTTP 处理器"""
        handler = self

        class _Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                content_len = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_len)
                try:
                    payload = json.loads(body)
                    text = payload.get("message", "")
                    chat_id = payload.get("chat_id", "api")
                    reply = handler.handle_message("api", chat_id, text)
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        "reply": reply
                    }).encode())
                except (json.JSONDecodeError, Exception) as e:
                    self.send_response(400)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        "error": str(e)
                    }).encode())

            def do_GET(self):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "status": "alive",
                    "nexus": "v0.4"
                }).encode())

            def log_message(self, fmt, *args):
                pass  # 静默，避免刷日志

        return _Handler
