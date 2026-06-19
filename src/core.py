"""
Nexus Core v2 — 常驻守护进程

这次真的连接到外部世界了。
启动时启动感官管理器。
"""

import asyncio
import json
import logging
import os
import signal
import sys
import time
import threading
from http.server import HTTPServer

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.regions.main import MainRegion
from src.regions.ops import OpsRegion
from src.regions.research import ResearchRegion
from src.regions.dream import DreamRegion
from src.regions.skills import SkillsRegion
from src.shared.signal_board import post, clear_old
from src.memory.sandglass import process_pending, save_core, search
from src.gateway.manager import GatewayManager
from src.gateway.api import ApiSensor

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
    """Nexus 常驻进程 — 这次是活的"""

    def __init__(self):
        self.running = False
        self.regions = {}
        self.tick_count = 0
        self.start_time = time.time()
        self.gateway = None
        self.api_server = None
        self._api_thread = None

        # 区域注册表
        self.region_defs = {
            "main": MainRegion,
            "ops": OpsRegion,
            "research": ResearchRegion,
            "dream": DreamRegion,
            "skills": SkillsRegion,
        }

    def _global_message_handler(self, platform: str, chat_id: str, content: str) -> str:
        """
        全局消息处理入口。
        任何感官接收到的消息，都通过这里进入主意识区。
        """
        log.info(f"MSG [{platform}:{chat_id[:20]}]: {content[:60]}")

        if "main" in self.regions:
            reply = self.regions["main"].handle_message(content, platform, chat_id)
            return reply or ""
        return "（Nexus 主意识区尚未就绪）"

    async def start(self):
        """启动 Nexus"""
        log.info("=" * 50)
        log.info("Nexus Core v0.4 — 分布式意识系统")
        log.info("=" * 50)
        self.running = True

        # 1. 启动所有区域
        for name, cls in self.region_defs.items():
            try:
                self.regions[name] = cls()
                log.info(f"  ✓ {name} region loaded")
            except Exception as e:
                log.error(f"  ✗ {name} region failed: {e}")

        # 2. 启动感官管理器
        self.gateway = GatewayManager(self._global_message_handler)
        log.info("  ✓ Gateway manager loaded")

        # 3. 注册默认感官
        # 飞书（从 Hermes 网关配置读取）
        feishu_config = self._load_feishu_config()
        if feishu_config:
            self.gateway.register_sensor("feishu", "feishu", feishu_config)
            self.gateway._start_sensor("feishu", "feishu", feishu_config)
            log.info("  ✓ Feishu sensor registered")
        else:
            log.warning("  ⚠ Feishu config not found, skipping")

        # 4. 启动 API 感官（HTTP 接口）
        api_config = {"port": 8670, "host": "127.0.0.1"}
        self.gateway.register_sensor("api", "api", api_config)
        self._start_api_server(api_config)
        log.info("  ✓ API sensor started on 127.0.0.1:8670")

        # 写启动信号
        post("core", "startup",
             f"Nexus Core v0.4 started with {len(self.regions)} regions")

        log.info(f"\n{'='*50}")
        log.info(f"Nexus is alive. {len(self.regions)} regions, "
                 f"{len(self.gateway.sensors)} sensors active")
        log.info(f"{'='*50}")

        # 主循环
        await self._heartbeat_loop()

    def _load_feishu_config(self) -> dict:
        """从 Hermes 配置加载飞书凭证"""
        import configparser
        config = configparser.ConfigParser()
        config_path = os.path.expanduser("~/.hermes/config.yaml")
        if not os.path.exists(config_path):
            return {}

        # 从 YAML 中尝试读取飞书配置
        try:
            import yaml
            with open(config_path) as f:
                hermes_config = yaml.safe_load(f)
            feishu = hermes_config.get("gateway", {}).get("feishu", {})
            if feishu.get("app_id") and feishu.get("app_secret"):
                return {
                    "app_id": feishu["app_id"],
                    "app_secret": feishu["app_secret"],
                    "verify_token": feishu.get("verify_token", ""),
                }
        except Exception as e:
            log.warning(f"Could not load feishu config: {e}")

        return {}

    def _start_api_server(self, config: dict):
        """启动 API HTTP 服务（在线程中）"""
        handler = self.gateway.sensors.get("api")
        if not handler:
            return
        handler_class = handler.create_handler()
        self.api_server = HTTPServer(
            (config.get("host", "127.0.0.1"), config.get("port", 8670)),
            handler_class
        )
        self._api_thread = threading.Thread(
            target=self.api_server.serve_forever,
            daemon=True
        )
        self._api_thread.start()

    async def _heartbeat_loop(self):
        """心跳循环 — Nexus 的呼吸"""
        while self.running:
            tick_start = time.time()
            self.tick_count += 1

            # 定时任务
            if self.tick_count % 12 == 0:
                self._tick_memory()
            if self.tick_count % 60 == 0:
                self._tick_signal_cleanup()
            if self.tick_count % 1440 == 0:
                self._tick_health_check()
            if self.tick_count == 1:
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
        if self.api_server:
            self.api_server.shutdown()
        post("core", "shutdown", "Nexus Core stopped")
        log.info("Goodbye, for now.")


if __name__ == "__main__":
    core = NexusCore()

    def handle_signal(sig, frame):
        log.info(f"Received signal {sig}")
        core.stop()
        sys.exit(0)

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    asyncio.run(core.start())
