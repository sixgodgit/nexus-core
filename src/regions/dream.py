"""
梦境区域 — Nexus 的灵魂。

白天什么都不做。
凌晨自动醒来，复盘今天所有区域的数据，
建立跨区域关联、沉淀知识、提取模式、发现矛盾。

自进化核心：每个区域完成事情后自评的能力从这里沉淀。
"""

import asyncio
import json
import logging
import os
import time

from src.thalamus.client import ThalamusClient
from src.memory.sandglass import save_core, search, queue_pending, process_pending
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

        # 凌晨 2:00-5:00 是梦境时间
        is_dream_time = (hour >= 2 and hour < 5)
        time_since_last = time.time() - self.last_dream

        if is_dream_time and time_since_last > 3600:
            self.last_dream = time.time()
            await self._dream()
        elif not is_dream_time and time_since_last > 7200:
            # 非梦境时间，如果超过 2 小时没跑过快速复盘
            pass

    async def _dream(self):
        """执行一次完整的梦境流程"""
        self.dream_count += 1
        log.info(f"Dream #{self.dream_count} starting...")

        today = time.strftime("%Y-%m-%d")
        yesterday_ts = time.time() - 86400

        # 阶段 1: 收集数据
        signals_today = peek(since=yesterday_ts)
        memories_today = search(time.strftime("%Y-%m-%d", time.gmtime(yesterday_ts)),
                                limit=20)
        core_memories = search("nexus:", limit=30)

        # 阶段 2: 跨区域关联
        associations = self._build_associations(signals_today, memories_today)

        # 阶段 3: 提取行为模式
        patterns = self._extract_patterns(memories_today + core_memories)

        # 阶段 4: 发现矛盾
        conflicts = self._find_conflicts(memories_today + core_memories)

        # 阶段 5: 自进化建议 —— 每个区域完成事后的自评沉淀
        evolution_tips = self._evolution_advice(signals_today, memories_today)

        # 阶段 6: 沉淀梦境结果
        dream_content = {
            "dream_id": self.dream_count,
            "time": time.time(),
            "date": today,
            "associations": associations,
            "patterns": patterns,
            "conflicts": conflicts,
            "evolution": evolution_tips,
        }

        # 写入梦境日志
        dream_path = os.path.join(DREAMS_DIR, f"{today}_dream.json")
        with open(dream_path, "w") as f:
            json.dump(dream_content, f, indent=2, ensure_ascii=False)

        # 将关键发现写入共享记忆
        for p in patterns[:3]:
            save_core(f"dream:pattern:{int(time.time())}", p, source="dream")

        for c in conflicts[:2]:
            save_core(f"dream:conflict:{int(time.time())}", c, source="dream")

        for tip in evolution_tips[:3]:
            save_core(f"dream:evolution:{int(time.time())}", tip, source="dream")

        # 处理队待沉淀的记忆
        processed = process_pending()

        # 总结
        summary_parts = []
        if associations:
            summary_parts.append(f"发现 {len(associations)} 个关联")
        if patterns:
            summary_parts.append(f"提取 {len(patterns)} 个行为模式")
        if conflicts:
            summary_parts.append(f"发现 {len(conflicts)} 个矛盾")
        if evolution_tips:
            summary_parts.append(f"产生 {len(evolution_tips)} 条进化建议")
        if processed:
            summary_parts.append(f"沉淀 {processed} 条记忆")

        summary = (f"梦境 #{self.dream_count} 完成: "
                   f"{'; '.join(summary_parts) if summary_parts else '今夜无事，安眠。'}")
        post("dream", "report", summary, priority=1)
        log.info(summary)

    def _build_associations(self, signals: list, memories: list) -> list:
        """建立跨区域关联"""
        associations = []
        all_texts = []
        for s in signals:
            all_texts.append(f"[{s.get('region', '?')}] {s.get('content', '')}")
        for m in memories:
            all_texts.append(str(m.get('content', str(m))))

        # 话题共现关联
        topic_map = {
            "医疗/健康": ["质子", "逍遥丸", "医院", "手术", "治疗", "药"],
            "代码/技术": ["thalamus", "deploy", "代码", "部署", "API", "bug", "git"],
            "服务器/运维": ["磁盘", "内存", "CPU", "监控", "告警", "服务"],
            "车辆/出行": ["车", "胎压", "油价", "高速", "加油站"],
            "视频/创意": ["视频", "分镜", "Seedance", "剪映", "导演"],
            "法律/规则": ["刑法", "刑警", "法律", "公证", "合同", "画圈"],
        }

        for topic, keywords in topic_map.items():
            matched = []
            for text in all_texts:
                for kw in keywords:
                    if kw in text:
                        matched.append(text[:50])
                        break
            if len(matched) >= 2:
                associations.append(f"{topic}: {' ↔ '.join(matched[:3])}")
        return associations[:5]

    def _extract_patterns(self, memories: list) -> list:
        """从记忆提取行为模式"""
        patterns = []
        all_content = " ".join([str(m.get("content", str(m))) for m in memories])

        # 模式检测
        if "磁盘" in all_content and "告警" in all_content:
            patterns.append("磁盘告警模式：当磁盘使用率超过 85% 时，需要检查构建缓存和日志文件。")
        if "用户" in all_content and "讨厌" in all_content:
            patterns.append("用户沟通模式：用户讨厌被反问、讨厌\"当然\"类语气词、讨厌重复旧话题。")
        if "部署" in all_content or "推" in all_content:
            patterns.append("部署模式：修改代码后需验证语法，再推送 GitHub，最后部署到目标服务器。")
        if "梦" in all_content:
            patterns.append("梦境模式：用户重视\"有灵魂\"的系统——系统需要有自己的生命，不只是工具。")

        return patterns[:5]

    def _find_conflicts(self, memories: list) -> list:
        """发现记忆中的矛盾"""
        conflicts = []
        all_content = " ".join([str(m.get("content", str(m))) for m in memories])

        # 检查是否有矛盾信号
        likes = set()
        dislikes = set()
        for topic in ["MiMo", "DeepSeek", "Hermes", "Python", "设计"]:
            if f"喜欢{topic}" in all_content or f"{topic}好" in all_content:
                likes.add(topic)
            if f"不喜欢{topic}" in all_content or f"{topic}不行" in all_content:
                dislikes.add(topic)

        for topic in likes & dislikes:
            conflicts.append(f"矛盾：用户对「{topic}」既有正面表达又有负面表达，需在下轮对话中确认。")

        return conflicts[:3]

    def _evolution_advice(self, signals: list, memories: list) -> list:
        """自进化建议"""
        advice = []
        all_text = " ".join([
            str(s.get("content", "")) for s in signals
        ] + [
            str(m.get("content", "")) for m in memories
        ])

        # 根据信号和记忆提出改进建议
        if "disk" in all_text or "磁盘" in all_text:
            advice.append("运维区：磁盘告警后应自动清理系统日志和构建缓存，不等主意识区介入。")

        if "research" in all_text:
            advice.append("研究区：应增加搜索频率——用户可能已经等不急新信息了。")

        if len(memories) > 50:
            advice.append("记忆系统：核心记忆超过 50 条，建议本轮梦境后执行一次去重和合并。")

        # 如果没有特别建议，给一个通用建议
        if not advice:
            advice.append("通用：所有区域在完成操作后，应自动记录\"学到了什么\"到共享记忆。")

        return advice
