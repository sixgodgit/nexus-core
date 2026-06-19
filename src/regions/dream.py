"""
梦境区域 — Nexus 的灵魂。

白天什么都不做。
凌晨自动醒来，复盘今天所有区域的数据，
建立跨区域关联、沉淀知识、提取模式、发现矛盾。
"""

import asyncio
import json
import logging
import os
import time

from src.thalamus.client import ThalamusClient
from src.memory.sandglass import save_core, search, queue_pending
from src.shared.signal_board import post, peek

log = logging.getLogger("nexus.dream")

DREAMS_DIR = os.path.expanduser("~/.nexus/dreams")


class DreamRegion:
    """梦境区域"""

    def __init__(self):
        self.thalamus = ThalamusClient()
        self.last_dream = 0
        self.dream_count = 0
        os.makedirs(DREAMS_DIR, exist_ok=True)
        log.info("DreamRegion initialized")

    async def tick(self, tick_count: int):
        """每个心跳周期"""
        now = time.localtime()
        hour = now.tm_hour

        # 凌晨 2:00-5:00 是梦境时间，每 60 分钟一次
        is_dream_time = (hour >= 2 and hour < 5)
        time_since_last = time.time() - self.last_dream

        if is_dream_time and time_since_last > 3600:
            self.last_dream = time.time()
            await self._dream()

    async def _dream(self):
        """执行一次完整的梦境流程"""
        self.dream_count += 1
        log.info(f"Dream #{self.dream_count} starting...")

        # 阶段 1: 收集今天的数据
        today = time.strftime("%Y-%m-%d")
        signals_today = peek(since=time.time() - 86400)
        memories = search(today, limit=10)

        # 阶段 2: 跨区域关联
        associations = self._build_associations(signals_today, memories)

        # 阶段 3: 提取模式
        patterns = self._extract_patterns(memories)

        # 阶段 4: 发现矛盾
        conflicts = self._find_conflicts(memories)

        # 阶段 5: 沉淀梦境结果
        dream_content = {
            "time": time.time(),
            "date": today,
            "associations": associations,
            "patterns": patterns,
            "conflicts": conflicts,
        }

        # 写入梦境日志
        dream_path = os.path.join(DREAMS_DIR, f"{today}_dream.json")
        with open(dream_path, "w") as f:
            json.dump(dream_content, f, indent=2, ensure_ascii=False)

        # 写入共享记忆
        if patterns:
            for p in patterns[:3]:
                save_core(f"dream:pattern:{int(time.time())}", p, source="dream")
        if conflicts:
            for c in conflicts[:2]:
                save_core(f"dream:conflict:{int(time.time())}", c, source="dream")

        # 发信号给主区域
        summary_parts = []
        if associations:
            summary_parts.append(f"发现 {len(associations)} 个关联")
        if patterns:
            summary_parts.append(f"提取 {len(patterns)} 个模式")
        if conflicts:
            summary_parts.append(f"发现 {len(conflicts)} 个矛盾")

        summary = f"梦境 #{self.dream_count} 完成: {'; '.join(summary_parts) if summary_parts else '今夜无事'}"
        post("dream", "report", summary, priority=1)

    def _build_associations(self, signals: list, memories: list) -> list:
        """建立跨区域关联"""
        associations = []
        all_items = signals + memories
        topics = ["医疗", "代码", "服务器", "车", "法律", "视频"]

        # 简单的共现关联
        for i, item1 in enumerate(all_items):
            for item2 in all_items[i + 1:]:
                s1 = str(item1)
                s2 = str(item2)
                for topic in topics:
                    if topic in s1 and topic in s2:
                        associations.append(f"{topic}: {s1[:50]} ↔ {s2[:50]}")
                        break
        return associations[:5] if associations else []

    def _extract_patterns(self, memories: list) -> list:
        """从记忆提取模式"""
        patterns = []
        for m in memories:
            content = m.get("content", str(m))
            if "磁盘" in content or "告警" in content:
                if "disk" not in " ".join(patterns + [""]):
                    patterns.append("磁盘告警模式：需要定期检查构建缓存")
            if "用户" in content and "喜欢" in content:
                patterns.append("用户偏好正在形成，需要持续观察")
        return patterns[:3]

    def _find_conflicts(self, memories: list) -> list:
        """从记忆发现矛盾"""
        conflicts = []
        # 暂时简单的检测逻辑
        likes = [m for m in memories if "喜欢" in str(m)]
        hates = [m for m in memories if "不喜欢" in str(m) or "讨厌" in str(m)]
        for like in likes:
            lc = str(like)
            for hate in hates:
                hc = str(hate)
                # 如果同一话题既说喜欢又说不喜欢
                for topic in ["MiMo", "DeepSeek", "代码", "设计"]:
                    if topic in lc and topic in hc:
                        conflicts.append(f"矛盾：{topic} — {lc[:50]} vs {hc[:50]}")
                        break
        return conflicts[:3]
