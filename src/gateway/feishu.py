#!/usr/bin/env python3
"""
飞书感官 v2 — Nexus 的耳朵和嘴巴。
用 lark_oapi 官方 SDK 的 WebSocket 长连接。

不经过 Hermes Gateway，直接接收飞书事件。
"""

import asyncio
import json
import logging
import os
import threading
import time
from typing import Callable, Optional

import lark_oapi as lark

log = logging.getLogger("nexus.feishu")

GATEWAY_DIR = os.path.expanduser("~/.nexus/gateway")
os.makedirs(GATEWAY_DIR, exist_ok=True)
CONFIG_PATH = os.path.join(GATEWAY_DIR, "feishu.json")


def load_config() -> dict:
    if not os.path.exists(CONFIG_PATH):
        return {}
    with open(CONFIG_PATH) as f:
        return json.load(f)


class FeishuHandler:
    """
    飞书事件处理器。
    按 lark_oapi 的 EventDispatcherHandler 约定，接收事件对象。
    """

    def __init__(self, on_message: Callable[[str, str, str], Optional[str]]):
        """
        on_message(text, platform, chat_id) -> reply 或 None
        """
        self.on_message = on_message

    def handle_p2_im_message_receive_v1(self, event):
        """
        P2 版本 im.message.receive_v1 事件。
        收到消息后解析文本内容，交给回调处理。
        """
        try:
            msg = event.event.message
            chat_id = msg.chat_id
            msg_type = msg.message_type

            if msg_type == "text":
                content = json.loads(msg.content)
                text = content.get("text", "")
                if not text:
                    return

                log.info(f"Feishu msg from {chat_id}: {text[:60]}...")

                reply = self.on_message(text, "feishu", chat_id)
                if reply:
                    self._reply(chat_id, reply)
            elif msg_type == "image":
                log.info(f"Feishu image from {chat_id}, ignoring")
        except Exception as e:
            log.warning(f"Feishu handler error: {e}")

    def _reply(self, chat_id: str, text: str):
        """简单发送飞书消息"""
        try:
            import requests
            # 取 token
            cfg = load_config()
            r = requests.post(
                "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
                json={"app_id": cfg["app_id"], "app_secret": cfg["app_secret"]},
                timeout=10,
            )
            token = r.json()["tenant_access_token"]

            # 发消息
            requests.post(
                "https://open.feishu.cn/open-apis/im/v1/messages",
                params={"receive_id_type": "chat_id"},
                json={
                    "receive_id": chat_id,
                    "msg_type": "text",
                    "content": json.dumps({"text": text}),
                },
                headers={"Authorization": f"Bearer {token}"},
                timeout=10,
            )
        except Exception as e:
            log.warning(f"Feishu reply error: {e}")


class FeishuSensor:
    """
    飞书感官 —— 长连接监听飞书消息。

    用法:
        sensor = FeishuSensor(my_handler_func)
        sensor.start()
        # sensor 在后台线程运行
        # 收到飞书消息 → my_handler_func(text, "feishu", chat_id) → 回复
    """

    def __init__(self, message_handler):
        """
        message_handler(text, platform, chat_id) -> str or None
        """
        self.config = load_config()
        self.running = False
        self._client = None
        self._thread = None

        self._handler = FeishuHandler(message_handler)

        if not self.config.get("app_id") or not self.config.get("app_secret"):
            log.warning(
                f"Feishu credentials missing. Create {CONFIG_PATH}"
            )
        else:
            log.info(f"Feishu config OK: app_id={self.config['app_id'][:10]}...")

    def start(self) -> bool:
        cfg = self.config
        if not cfg.get("app_id") or not cfg.get("app_secret"):
            log.error("Cannot start Feishu sensor: missing credentials")
            return False

        self.running = True

        def _run():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self._run_ws())
            except Exception as e:
                log.error(f"Feishu WS loop died: {e}")
            finally:
                loop.close()

        self._thread = threading.Thread(target=_run, daemon=True)
        self._thread.start()
        log.info("Feishu sensor started (daemon thread)")
        return True

    async def _run_ws(self):
        cfg = self.config

        # 创建事件处理器
        handler = (
            lark.EventDispatcherHandler.builder(cfg["app_id"], cfg["app_secret"])
            .register_p2_im_message_receive_v1(
                self._handler.handle_p2_im_message_receive_v1
            )
            .build()
        )

        # 创建 ws client
        client = lark.ws.Client(
            app_id=cfg["app_id"],
            app_secret=cfg["app_secret"],
            event_handler=handler,
            auto_reconnect=True,
        )

        log.info("Feishu WS connecting...")
        await client.start()

    def stop(self):
        self.running = False
        log.info("Feishu sensor stopping")
