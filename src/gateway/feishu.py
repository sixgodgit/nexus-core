#!/usr/bin/env python3
"""
飞书感官 — Nexus 的耳朵和嘴巴。

直接通过飞书 API 接收消息、回复消息。
写在单独进程里，不阻塞 Nexus 主循环。
"""

import asyncio
import json
import logging
import os
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional

log = logging.getLogger("nexus.feishu")

GATEWAY_DIR = os.path.expanduser("~/.nexus/gateway")
os.makedirs(GATEWAY_DIR, exist_ok=True)
CONFIG_PATH = os.path.join(GATEWAY_DIR, "feishu.json")


def load_config() -> dict:
    """从配置文件加载飞书凭证"""
    config_paths = [
        CONFIG_PATH,
        os.path.expanduser("~/.hermes/config.yaml"),
    ]
    for path in config_paths:
        if not os.path.exists(path):
            continue
        try:
            if path.endswith(".json"):
                with open(path) as f:
                    return json.load(f)
            elif path.endswith(".yaml") or path.endswith(".yml"):
                import yaml
                with open(path) as f:
                    cfg = yaml.safe_load(f)
                feishu = cfg.get("gateway", {}).get("feishu", {})
                if feishu.get("app_id"):
                    return feishu
        except Exception:
            continue
    return {}


class FeishuSensor:
    """飞书感官"""

    def __init__(self, message_handler):
        """
        message_handler(msg_text, platform, chat_id) -> reply
        """
        self.config = load_config()
        self.message_handler = message_handler
        self.server = None
        self.thread = None
        self.access_token = None
        self.token_expires = 0

        if self.config.get("app_id"):
            log.info("Feishu config loaded: "
                     f"app_id={self.config['app_id'][:10]}...")
        else:
            log.warning("No feishu config found. "
                        "Create ~/.nexus/gateway/feishu.json")

    def _get_token(self) -> Optional[str]:
        """获取飞书 access_token"""
        if time.time() < self.token_expires:
            return self.access_token

        import requests
        try:
            r = requests.post(
                "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
                json={
                    "app_id": self.config.get("app_id"),
                    "app_secret": self.config.get("app_secret"),
                },
                timeout=10
            )
            if r.status_code == 200:
                data = r.json()
                self.access_token = data.get("tenant_access_token")
                self.token_expires = time.time() + data.get("expire", 7200) - 60
                return self.access_token
        except Exception as e:
            log.warning(f"Feishu token error: {e}")
        return None

    def send_message(self, chat_id: str, text: str) -> bool:
        """发送飞书消息"""
        token = self._get_token()
        if not token:
            return False

        import requests
        try:
            r = requests.post(
                "https://open.feishu.cn/open-apis/im/v1/messages",
                params={"receive_id_type": "open_id"},
                json={
                    "receive_id": chat_id,
                    "msg_type": "text",
                    "content": json.dumps({"text": text}),
                },
                headers={"Authorization": f"Bearer {token}"},
                timeout=10
            )
            return r.status_code == 200
        except Exception as e:
            log.warning(f"Feishu send error: {e}")
        return False

    def start_webhook(self, host: str = "0.0.0.0", port: int = 7560):
        """启动 webhook HTTP 服务器"""
        handler = self._create_handler()

        class FeishuHandler(BaseHTTPRequestHandler):
            sensor = self

            def do_POST(self):
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length).decode()
                try:
                    data = json.loads(body)
                    event = data.get("event", {})

                    # 只处理文本消息
                    msg_type = event.get("message", {}).get("message_type", "")
                    if msg_type != "text":
                        self._ok()
                        return

                    msg_content = json.loads(
                        event.get("message", {}).get("content", "{}")
                    )
                    text = msg_content.get("text", "")
                    chat_id = event.get("message", {}).get("chat_id", "")

                    if text and chat_id:
                        # 回复需要处理验证 challenge
                        reply = self.sensor.message_handler(
                            text, "feishu", chat_id
                        )
                        if reply:
                            self.sensor.send_message(chat_id, reply)

                except Exception as e:
                    log.warning(f"Feishu webhook error: {e}")

                self._ok()

            def do_GET(self):
                """飞书验证 URL 时用 GET"""
                self._ok()

            def _ok(self):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "challenge": json.loads(
                        self.rfile.read(
                            int(self.headers.get("Content-Length", 0))
                        ).decode()
                    ).get("challenge", "") if False else ""
                }).encode()) if False else None

            def log_message(self, fmt, *args):
                pass

        self.server = HTTPServer((host, port), FeishuHandler)
        self.thread = threading.Thread(
            target=self.server.serve_forever, daemon=True
        )
        self.thread.start()
        log.info(f"Feishu webhook started on {host}:{port}")

    def _create_handler(self):
        return self
