"""
飞书感官 — 通过飞书听和说。
"""

import asyncio
import json
import logging
import os
import requests
from typing import Callable

log = logging.getLogger("nexus.feishu")


class FeishuSensor:
    """飞书感官"""

    def __init__(self, config: dict, message_handler: Callable):
        self.config = config
        self.handle_message = message_handler
        self.app_id = config.get("app_id", "")
        self.app_secret = config.get("app_secret", "")
        self.verify_token = config.get("verify_token", "")
        self.running = False
        self._token = None

    def start(self):
        """启动飞书感官（这个在 Nexus Core 里被管理）"""
        self.running = True
        log.info("Feishu sensor ready")

    def stop(self):
        """停止"""
        self.running = False
        log.info("Feishu sensor stopped")

    def receive_event(self, event_payload: dict) -> dict:
        """接收飞书事件"""
        # 验证 token
        if event_payload.get("token") != self.verify_token:
            return {"code": 403, "msg": "invalid token"}

        # 解析消息
        event = event_payload.get("event", {})
        msg_type = event.get("message", {}).get("message_type", "")

        if msg_type != "text":
            return {"code": 0}  # 非文本消息忽略

        text_content = event.get("message", {}).get("content", "{}")
        try:
            content = json.loads(text_content)
            user_text = content.get("text", "")
        except (json.JSONDecodeError, TypeError):
            return {"code": 400, "msg": "invalid content"}

        chat_id = event.get("message", {}).get("chat_id", "")

        # 交给消息处理器
        reply = self.handle_message("feishu", chat_id, user_text)

        # 回复
        if reply:
            self._send_reply(chat_id, reply)

        return {"code": 0}

    def _send_reply(self, chat_id: str, text: str):
        """发送飞书消息"""
        # 获取 token
        token = self._get_token()
        if not token:
            log.error("No feishu token available")
            return

        url = "https://open.feishu.cn/open-apis/im/v1/messages"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        payload = {
            "receive_id": chat_id,
            "msg_type": "text",
            "content": json.dumps({"text": text}),
        }
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=10)
            if r.status_code != 200:
                log.warning(f"Feishu send failed: {r.status_code} {r.text[:100]}")
        except requests.RequestException as e:
            log.error(f"Feishu send error: {e}")

    def _get_token(self) -> str:
        """获取飞书 token"""
        if self._token:
            return self._token

        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        payload = {
            "app_id": self.app_id,
            "app_secret": self.app_secret,
        }
        try:
            r = requests.post(url, json=payload, timeout=10)
            data = r.json()
            self._token = data.get("tenant_access_token", "")
        except (requests.RequestException, json.JSONDecodeError) as e:
            log.error(f"Feishu auth error: {e}")
            self._token = ""

        return self._token
