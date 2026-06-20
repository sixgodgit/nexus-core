#!/usr/bin/env python3
"""
飞书感官独立进程 — Nexus 的耳朵和嘴巴
在独立进程里跑，通过 HTTP 调 Nexus 的 API。

用法：
  python3 feishu_sensor.py

自动从 ~/.nexus/gateway/feishu.json 加载配置
收到飞书消息 -> POST http://127.0.0.1:8560/chat -> 回复
"""

import json
import logging
import os
import sys
import time

import lark_oapi as lark

NEXUS_API = os.environ.get("NEXUS_API_URL", "http://127.0.0.1:8560")
GATEWAY_DIR = os.path.expanduser("~/.nexus/gateway")
os.makedirs(GATEWAY_DIR, exist_ok=True)
LOG_DIR = os.path.expanduser("~/.nexus/logs")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [feishu] %(levelname)s: %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "feishu_sensor.log")),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("feishu_sensor")


def load_config() -> dict:
    path = os.path.join(GATEWAY_DIR, "feishu.json")
    with open(path) as f:
        return json.load(f)


def _get_domain() -> str:
    """根据环境变量选择飞书域名"""
    from lark_oapi.core.const import FEISHU_DOMAIN, LARK_DOMAIN
    domain_name = os.environ.get("FEISHU_DOMAIN", "feishu").strip().lower()
    return LARK_DOMAIN if domain_name == "lark" else FEISHU_DOMAIN


def handle_event(event):
    """收到飞书消息 -> 调 Nexus API"""
    try:
        msg = event.event.message
        chat_id = msg.chat_id
        msg_type = msg.message_type

        if msg_type != "text":
            return

        content = json.loads(msg.content)
        text = content.get("text", "")
        if not text:
            return

        log.info(f"FROM {chat_id}: {text[:60]}...")

        # 调 Nexus API
        import requests
        r = requests.post(
            f"{NEXUS_API}/chat",
            json={"text": text, "platform": "feishu", "chat_id": chat_id},
            timeout=60,
        )
        if r.status_code == 200:
            reply = r.json().get("reply", "")
            if reply:
                _send_message(chat_id, reply)
                log.info(f"REPLIED: {reply[:60]}...")
        else:
            log.warning(f"Nexus API error: {r.status_code} {r.text[:100]}")

    except Exception as e:
        log.warning(f"Handle event error: {e}")


def _send_message(chat_id: str, text: str):
    """用飞书 API 发消息"""
    cfg = load_config()
    domain = _get_domain().replace("open.", "open.")

    import requests
    r = requests.post(
        f"{domain}/open-apis/auth/v3/tenant_access_token/internal",
        json={"app_id": cfg["app_id"], "app_secret": cfg["app_secret"]},
        timeout=10,
    )
    token = r.json()["tenant_access_token"]

    requests.post(
        f"{domain}/open-apis/im/v1/messages",
        params={"receive_id_type": "chat_id"},
        json={
            "receive_id": chat_id,
            "msg_type": "text",
            "content": json.dumps({"text": text}),
        },
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )


def main():
    """主函数 — 纯同步，不走 asyncio"""
    cfg = load_config()
    if not cfg.get("app_id") or not cfg.get("app_secret"):
        log.error("Missing feishu credentials")
        sys.exit(1)

    domain = _get_domain()
    log.info(f"Domain: {domain}")

    handler = (
        lark.EventDispatcherHandler.builder(cfg["app_id"], cfg["app_secret"])
        .register_p2_im_message_receive_v1(handle_event)
        .build()
    )

    client = lark.ws.Client(
        app_id=cfg["app_id"],
        app_secret=cfg["app_secret"],
        event_handler=handler,
        auto_reconnect=True,
        domain=domain,
    )

    log.info(f"Feishu sensor starting (Nexus API: {NEXUS_API})")
    client.start()


if __name__ == "__main__":
    main()
