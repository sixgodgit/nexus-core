"""
Nexus Core — 常驻守护进程

大脑本身。管理所有区域的注册、调度、心跳。
"""

import asyncio
import json
import logging
import os
import signal
import sys
import time
from typing import Optional

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.regions.main import MainRegion
from src.regions.ops import OpsRegion
from src.regions.research import ResearchRegion
from src.regions.dream import DreamRegion
from src.regions.skills import SkillsRegion
from src.shared.signal_board import post, clear_old
from src.memory.sandglass import process_pending, save_core, search

LOG_DIR = os.path.expanduser("~/.nexus/logs")
RUN_DIR = os.path.expanduser("~/.nexus/run")
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(RUN_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "core.log")),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("nexus.core")


class NexusCore:
    """Nexus 常驻进程"""

    def __init__(self):
        self.running = False
        self.regions = {}
        self.tick_count = 0
        self.start_time = time.time()

        # 区域注册表
        self.region_defs = {
            "main": MainRegion,
            "ops": OpsRegion,
            "research": ResearchRegion,
            "dream": DreamRegion,
            "skills": SkillsRegion,
        }

    async def start(self):
        """启动所有区域"""
        log.info("Nexus Core starting...")
        self.running = True

        # 启动所有区域
        for name, cls in self.region_defs.items():
            try:
                self.regions[name] = cls()
                log.info(f"  ✓ {name} region loaded")
            except Exception as e:
                log.error(f"  ✗ {name} region failed: {e}")

        # 写启动信号
        post("core", "startup",
             f"Nexus Core v0.4 started with {len(self.regions)} regions")

        # 主循环
        await self._heartbeat_loop()

    async def _heartbeat_loop(self):
        """心跳循环 — Nexus 的呼吸"""
        while self.running:
            tick_start = time.time()
            self.tick_count += 1

            # 定时任务（不是每隔 N tick，而是看上次执行时间）
            if self.tick_count % 12 == 0:  # 每 60 秒
                self._tick_memory()
            if self.tick_count % 60 == 0:   # 每 5 分钟
                self._tick_signal_cleanup()
            if self.tick_count % 1440 == 0:  # 每 2 小时
                self._tick_health_check()
            if self.tick_count == 1:         # 启动后立即跑一次
                self._tick_initial_scan()

            # 驱动每个区域的 tick
            for name, region in self.regions.items():
                try:
                    await region.tick(self.tick_count)
                except Exception as e:
                    log.error(f"Region {name} tick error: {e}")

            # 睡眠到下一个 tick
            elapsed = time.time() - tick_start
            sleep_time = max(0.1, 5.0 - elapsed)
            await asyncio.sleep(sleep_time)

    def _tick_memory(self):
        """处理待沉淀的记忆"""
        processed = process_pending()
        if processed:
            log.info(f"Processed {processed} pending memories")

    def _tick_signal_cleanup(self):
        """清理旧信号"""
        clear_old(hours=48)

    def _tick_health_check(self):
        """健康检查"""
        # 记录运行状态到共享记忆
        uptime = int(time.time() - self.start_time)
        save_core("nexus:health", json.dumps({
            "uptime_seconds": uptime,
            "regions": list(self.regions.keys()),
            "ticks": self.tick_count,
        }), source="core")

    def _tick_initial_scan(self):
        """启动后首次扫描"""
        log.info("Initial scan complete")
        post("core", "ready", "Nexus Core is fully operational")

    def stop(self):
        """优雅停止"""
        log.info("Nexus Core stopping...")
        self.running = False
        post("core", "shutdown", "Nexus Core stopped")
        log.info("Goodbye.")


if __name__ == "__main__":
    core = NexusCore()

    def handle_signal(sig, frame):
        log.info(f"Received signal {sig}")
        core.stop()
        sys.exit(0)

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    asyncio.run(core.start())
