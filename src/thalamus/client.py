"""
Thalamus 客户端 — Nexus 调用大模型 API 的唯一通道。

各区域声明自己的模型偏好，Thalamus 负责执行。
不关心路由规则，只做连接 + 健康检测 + fallback。
"""

import json
import requests
from typing import Optional

THALAMUS_API = "http://127.0.0.1:9880"


class ThalamusClient:
    """Thalamus 客户端"""

    def __init__(self):
        self.healthy = False
        self._check_health()

    def _check_health(self):
        try:
            r = requests.get(f"{THALAMUS_API}/health", timeout=3)
            self.healthy = r.status_code == 200
        except requests.RequestException:
            self.healthy = False

    def chat(self, messages: list, model: Optional[str] = None,
             provider: Optional[str] = None) -> Optional[str]:
        """发送聊天请求"""
        if not self.healthy:
            self._check_health()
            if not self.healthy:
                return None

        payload = {"messages": messages}
        if model:
            payload["model"] = model
        if provider:
            payload["provider"] = provider

        try:
            r = requests.post(f"{THALAMUS_API}/v1/chat/completions",
                              json=payload, timeout=60)
            if r.status_code == 200:
                data = r.json()
                return data.get("choices", [{}])[0].get("message", {}).get("content")
        except (requests.RequestException, json.JSONDecodeError, IndexError):
            pass
        return None

    def status(self) -> dict:
        """获取 Thalamus 状态"""
        try:
            r = requests.get(f"{THALAMUS_API}/health", timeout=3)
            return {"healthy": r.status_code == 200}
        except requests.RequestException:
            return {"healthy": False, "error": "unreachable"}
