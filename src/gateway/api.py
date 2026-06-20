#!/usr/bin/env python3
"""
HTTP API 感官 — 让外部系统也能跟 Nexus 对话。

GET  /status       → Nexus 状态
POST /chat         → 发消息给 Nexus（等同飞书）
GET  /signals      → 查看信号板
GET  /regions      → 查看各区域状态
"""

import json
import logging
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

log = logging.getLogger("nexus.api")


class APISensor:
    """HTTP API 感官"""

    def __init__(self, nexus):
        self.nexus = nexus

    def start(self, host: str = "127.0.0.1", port: int = 8560):
        sensor = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == "/status":
                    self._json(sensor._status())
                elif self.path == "/signals":
                    from nexus import signal_board
                    self._json(signal_board.peek(limit=50))
                elif self.path == "/regions":
                    self._json({
                        name: r.status() if hasattr(r, 'status')
                        else {"name": name, "type": type(r).__name__}
                        for name, r in sensor.nexus.regions.items()
                    })
                else:
                    self._json({"error": "not found"}, 404)

            def do_POST(self):
                if self.path == "/chat":
                    body = self._body()
                    text = body.get("text", "")
                    platform = body.get("platform", "api")
                    chat_id = body.get("chat_id", "api")
                    if text:
                        reply = sensor.nexus.handle_message(
                            text, platform, chat_id
                        )
                        self._json({"reply": reply})
                    else:
                        self._json({"error": "text required"}, 400)
                else:
                    self._json({"error": "not found"}, 404)

            def _json(self, data, code=200):
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

            def _body(self):
                length = int(self.headers.get("Content-Length", 0))
                return json.loads(self.rfile.read(length).decode()) \
                    if length else {}

            def log_message(self, fmt, *args):
                pass

        self.server = HTTPServer((host, port), Handler)
        thread = threading.Thread(
            target=self.server.serve_forever, daemon=True
        )
        thread.start()
        log.info(f"API sensor started on {host}:{port}")

    def _status(self):
        import time
        return {
            "nexus": "alive",
            "uptime": int(time.time() - self.nexus.start_time),
            "ticks": self.nexus.tick_count,
            "regions": list(self.nexus.regions.keys()),
        }
