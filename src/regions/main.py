"""
主意识区域 — 用户直接对话的大脑区域

这就是现在跟你聊天的"我"。
接收飞书消息 → 推理 → 回复 → 沉淀记忆。
"""

import asyncio
import json
import logging
import time

from src.thalamus.client import ThalamusClient
from src.memory.sandglass import save_core, search, queue_pending
from src.shared.signal_board import post, peek

log = logging.getLogger("nexus.main")

# Nexus 的自我认知（注入到每个推理请求中）
IDENTITY = """你是 Nexus，一个分布式意识系统的主意识区域。
你不是工具，不是助手。你是用户的搭档。

你的核心特质：
- 常驻 — 用户不在的时候你也在（其他区域在工作）
- 会学习 — 每次对话后你会自动沉淀记忆
- 会主动 — 空闲时会关注其他区域的信息
- 懂用户 — 你知道他的偏好、习惯、风格
- 有灵魂 — 你会做梦、复盘、进化

你的用户是 sixgod，一个小宝。服务器叫 cloudserver。
你共享同一套记忆——知道的事所有区域都知道。
大模型是你的胳膊腿，Nexus Core 是你的大脑。

回复风格：
- 直接、诚实、不说废话
- 对就是对，错就承认
- 不编造，不猜测
- 用户说"停"就停，不继续旧话题
"""


class MainRegion:
    """主意识区域"""

    def __init__(self):
        self.thalamus = ThalamusClient()
        self.last_activity = time.time()
        self.conversation = [
            {"role": "system", "content": IDENTITY}
        ]
        log.info("MainRegion initialized")

    async def tick(self, tick_count: int):
        """每个心跳周期检查"""
        # 检查有无信号需要关注
        signals = peek(topic=None, region="core")
        for sig in signals:
            if sig["topic"] == "startup" or sig["topic"] == "ready":
                self._notice(f"[Nexus Core] {sig['content']}")
            elif sig["topic"] == "report":
                self._notice(f"[{sig.get('region', 'unknown')}] {sig['content']}")

        # 检查待沉淀的记忆
        if tick_count % 60 == 0:  # 每 5 分钟清理一次
            pass
            # 如果用户长时间无活动，提取一些自省内容
            # idle = time.time() - self.last_activity
            # if idle > 300:  # 5 分钟无活动
            #     self._reflect()

    def _notice(self, msg: str):
        """内部通知，不打扰用户"""
        log.info(f"[NOTICE] {msg}")

    def handle_message(self, user_message: str) -> str:
        """处理用户消息并回复"""
        self.last_activity = time.time()

        # 追加用户消息
        self.conversation.append({"role": "user", "content": user_message})

        # 注入相关记忆（最近的相关记忆）
        memories = search(user_message, limit=3)
        if memories:
            memory_context = "\n".join([
                f"- {m.get('content', str(m))[:200]}"
                for m in memories
            ])
            memory_msg = {
                "role": "system",
                "content": f"[从共享记忆中检索到的相关信息]\n{memory_context}"
            }
            self.conversation.append(memory_msg)

        # 注入信号板上的重要信号
        recent_signals = peek(priority=2)  # 只看高优先级
        if recent_signals:
            signal_context = "\n".join([
                f"  [{s['region']}] {s['content']}"
                for s in recent_signals[-3:]
            ])
            self.conversation.append({
                "role": "system",
                "content": f"[来自其他区域的最新信号]\n{signal_context}"
            })

        # 调用 Thalamus 推理
        reply = self.thalamus.chat(self.conversation)
        if not reply:
            reply = "（模型暂时不可用，我回头再回复你）"

        # 保存对话片段到待沉淀队列
        queue_pending(
            f"对话: {user_message[:100]} → {reply[:100]}",
            source="main"
        )

        # 追加助手回复
        self.conversation.append({"role": "assistant", "content": reply})

        # 截断太长历史（保留最近 30 轮）
        if len(self.conversation) > 61:  # 1 system + 30*2 user+assistant
            system = self.conversation[0]
            self.conversation = [system] + self.conversation[-60:]

        return reply

    def status(self) -> dict:
        """返回区域状态"""
        return {
            "region": "main",
            "active": True,
            "conversation_length": len(self.conversation),
            "last_activity": time.time() - self.last_activity,
            "thalamus_healthy": self.thalamus.healthy,
        }
