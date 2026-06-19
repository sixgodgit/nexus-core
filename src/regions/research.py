"""
研究区域 — 天生好奇，天生爱搜。

不等人告诉它搜什么。
它定期扫描共享记忆，看用户最近关心什么。
然后自己去搜，搜完沉淀到共享记忆。
累了就歇一会，但不会停——它天生就想知道更多。
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


class ResearchRegion:
    """研究区域"""

    def __init__(self):
        self.thalamus = ThalamusClient()
        self.last_research = 0
        self.last_topic_extract = 0
        self.researched_topics = {}  # topic -> last_search_time
        self.curiosity_pool = []  # 待研究的话题队列
        log.info("ResearchRegion initialized")

    async def tick(self, tick_count: int):
        """每个心跳周期"""
        now = time.time()

        # 每 10 分钟提取一次用户关心的话题
        if now - self.last_topic_extract > 600:
            self.last_topic_extract = now
            self._extract_topics()

        # 如果好奇心池里有东西，每 5 分钟研究一个
        if self.curiosity_pool and now - self.last_research > 300:
            self.last_research = now
            topic = self.curiosity_pool.pop(0)
            await self._research(topic)

    def _extract_topics(self):
        """从共享记忆中提取用户近期关心的话题"""
        # 搜索记忆中的关键字
        recent = search("?", limit=5)
        recent += search("用户", limit=5)
        recent += search("问题", limit=5)

        topics = set()
        for entry in recent:
            content = entry.get("content", str(entry))
            # 提取可能的话题
            checks = {
                "质子刀": ["proton", "质子", "重离子"],
                "AI热点": ["AI", "人工智能", "热点"],
                "医疗": ["医疗", "医院", "治疗", "手术"],
                "视频": ["视频", "分镜", "剪辑", "Seedance"],
                "代码": ["代码", "部署", "bug", "测试"],
                "服务器": ["磁盘", "内存", "CPU", "监控"],
            }
            for topic, keywords in checks.items():
                for kw in keywords:
                    if kw.lower() in str(content).lower():
                        # 检查这个话语是否最近研究过
                        last = self.researched_topics.get(topic, 0)
                        if time.time() - last > 86400:  # 24小时内不重复研究
                            topics.add(topic)
                        break

        # 添加到好奇心池
        for topic in topics:
            if topic not in self.curiosity_pool:
                self.curiosity_pool.append(topic)
                log.info(f"Curiosity: added '{topic}' to research queue")

    async def _research(self, topic: str):
        """对特定话题主动研究"""
        log.info(f"Researching: {topic}")
        self.researched_topics[topic] = time.time()

        # 用 DuckDuckGo 搜索（不需要 API key）
        try:
            url = f"https://api.duckduckgo.com/?q={topic}&format=json&no_html=1"
            # 直接用 Python requests
            r = subprocess.run(
                ["python3", "-c", f"""
import json, requests
try:
    r = requests.get('{url}', timeout=10, headers={{'User-Agent': 'Nexus/1.0'}})
    data = r.json()
    abstract = data.get('AbstractText', '')
    source = data.get('AbstractSource', '')
    url = data.get('AbstractURL', '')
    if abstract:
        print(f"RESULT: {{abstract[:500]}}")
        print(f"SOURCE: {{source}}")
        print(f"URL: {{url}}")
    else:
        # 退回到简单文本搜索
        r2 = requests.get(f'https://lite.duckduckgo.com/lite/?q={{topic}}', timeout=10)
        if '<a rel="nofollow" href="' in r2.text:
            import re
            links = re.findall(r'<a rel="nofollow" href="([^"]+)"', r2.text)[:5]
            texts = re.findall(r'class="result-snippet">([^<]+)', r2.text)[:5]
            for l, t in zip(links[:3], texts[:3]):
                print(f"LINK: {{l}} | {{t[:200]}}")
except Exception as e:
    print(f"ERROR: {{e}}")
"""],
                capture_output=True, text=True, timeout=15
            )
            result = r.stdout.strip()
        except subprocess.TimeoutExpired:
            result = "ERROR: timeout"

        if result and "ERROR" not in result and "RESULT:" in result:
            # 提取关键信息
            lines = result.split("\n")
            content = "\n".join(lines[:3])
            save_core(f"research:{topic}", content, source="research")
            post("research", "report",
                 f"关于「{topic}」找到了新信息，已存入共享记忆", priority=1)
            log.info(f"Research on '{topic}' complete")
        elif result and "LINK:" in result:
            # 有点链接结果
            content = result[:500]
            save_core(f"research:{topic}", content, source="research")
            post("research", "report",
                 f"关于「{topic}」找到了一些链接，已存入共享记忆", priority=1)
        else:
            log.info(f"Research on '{topic}' found nothing new")
