"""
研究区域 — 天生好奇，天生爱搜。

不等人告诉它搜什么。
它定期扫描共享记忆，看用户最近关心什么。
然后自己去搜，搜完沉淀到共享记忆。
"""

import asyncio
import json
import logging
import os
import subprocess
import time

from src.thalamus.client import ThalamusClient
from src.memory.sandglass import save_core, search, queue_pending
from src.shared.signal_board import post, peek

log = logging.getLogger("nexus.research")

RESEARCH_DIR = os.path.expanduser("~/.nexus/research")


class ResearchRegion:
    """研究区域"""

    def __init__(self):
        self.thalamus = ThalamusClient()
        self.last_research = 0
        self.last_topics = []
        os.makedirs(RESEARCH_DIR, exist_ok=True)
        log.info("ResearchRegion initialized")

    async def tick(self, tick_count: int):
        """每个心跳周期"""
        # 每 30 分钟检查一次是否需要主动研究
        if time.time() - self.last_research < 1800:
            return
        self.last_research = time.time()

        # 只有资源充裕时才主动研究（运存 > 300MB 空闲或不检查）
        self._check_should_research()

    def _check_should_research(self):
        """判断是否需要主动研究"""
        # 看共享记忆里用户最近关心什么
        recent = search("用户关心", limit=5)
        recent += search("问题", limit=5)
        recent += search("? ？", limit=5)

        # 提取话题
        topics = set()
        for entry in recent:
            content = entry.get("content", str(entry))
            # 简单提取疑似话题的短语
            if "proton" in content.lower() or "质子" in content:
                topics.add("质子刀/重离子治疗")
            if "车" in content and ("胎压" in content or "油价" in content):
                topics.add("车辆/油价信息")
            if "刑法" in content or "刑警" in content:
                topics.add("法律/真实案件")

        if not topics:
            return

        # 如果话题跟上一次一样，跳过（已经研究过了）
        if topics == set(self.last_topics):
            return

        self.last_topics = list(topics)
        self._start_research(topics)

    def _start_research(self, topics: set):
        """针对话题主动研究"""
        for topic in list(topics)[:2]:  # 最多 2 个话题
            log.info(f"Active research on: {topic}")
            # 异步执行研究（这里简化，直接调用搜索）
            try:
                r = subprocess.run(
                    f"python3 -c \"import requests; "
                    f"print(requests.get('https://api.duckduckgo.com/?q={topic}&format=json', "
                    f"timeout=10).json().get('AbstractText', 'no results'))\"",
                    shell=True, capture_output=True, text=True, timeout=15
                )
                result = r.stdout.strip()
                if result and result != "no results":
                    save_core(f"research:{topic}", result, source="research")
                    post("research", "report",
                         f"关于「{topic}」找到了新信息，已存入共享记忆",
                         priority=1)
            except (subprocess.TimeoutExpired, Exception) as e:
                log.warning(f"Research on {topic} failed: {e}")
