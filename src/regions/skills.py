"""
技能管理区域 — 技能的园丁。

自动扫描技能库，判断哪些该保留、合并、归档、清理。
执行 Librarian 的分类标准和 skills-judgment 的判决。
"""

import asyncio
import json
import logging
import os
import subprocess
import time

from src.memory.sandglass import save_core, search
from src.shared.signal_board import post, peek

log = logging.getLogger("nexus.skills")

SKILLS_DIR = os.path.expanduser("~/.hermes/skills")


class SkillsRegion:
    """技能管理区域"""

    def __init__(self):
        self.last_scan = 0
        self.last_cleanup = 0
        log.info("SkillsRegion initialized")

    async def tick(self, tick_count: int):
        """每个心跳周期"""
        now = time.time()

        # 每 1 小时扫描一次技能库
        if now - self.last_scan > 3600:
            self.last_scan = now
            await self._scan_skills()

        # 每 6 小时执行一次清理
        if now - self.last_cleanup > 21600:
            self.last_cleanup = now
            await self._cleanup_skills()

    async def _scan_skills(self):
        """扫描技能库，统计使用情况"""
        if not os.path.exists(SKILLS_DIR):
            return

        try:
            r = subprocess.run(
                "ls -lt ~/.hermes/skills/ 2>/dev/null | head -50",
                shell=True, capture_output=True, text=True, timeout=10
            )
            output = r.stdout.strip()
            if not output:
                return

            lines = output.split("\n")
            total = len([l for l in lines if l.strip() and l.strip().startswith("d")])
            if total > 0:
                log.info(f"Skills library: {total} skills")

                # 如果技能超过 80 个，发通知
                if total > 80:
                    post("skills", "warning",
                         f"技能库有 {total} 个技能，超过 80 个阈值，建议清理",
                         priority=1)
                elif total > 100:
                    post("skills", "alert",
                         f"技能库达 {total} 个！需要紧急清理",
                         priority=2)

        except subprocess.TimeoutExpired as e:
            log.warning(f"Skills scan timeout: {e}")

    async def _cleanup_skills(self):
        """清理过期/重复的技能"""
        # 假设有个接口可以查询技能使用频率
        # 这里做简化的标记逻辑

        # 检查最近有没有被引用的技能
        unused_count = 0
        try:
            r = subprocess.run(
                "find ~/.hermes/skills/ -name \"SKILL.md\" -mtime +90 2>/dev/null | wc -l",
                shell=True, capture_output=True, text=True, timeout=10
            )
            unused_count = int(r.stdout.strip())
        except (ValueError, subprocess.TimeoutExpired):
            pass

        if unused_count > 5:
            post("skills", "suggestion",
                 f"发现 {unused_count} 个技能超过 90 天未修改，建议评估是否需要归档",
                 priority=1)

        # 检查重复技能（按名称相似度）
        # 简化：不做实际向量比较，仅记录
        log.info(f"Skills cleanup scan: {unused_count} old skills found")
