"""
Gateway — Nexus 的感官层。

每个平台是一个"感官"：
- 飞书 = 耳朵（听你说）+ 嘴巴（回复你）
- QQ = 另一只耳朵
- Telegram = 另一只耳朵
- API = 直接神经接口

热插拔：加一个感官不影响其他感官。
"""

import asyncio
import json
import logging
import os
import sys
from typing import Callable, Optional

log = logging.getLogger("nexus.gateway")

GATEWAY_DIR = os.path.expanduser("~/.nexus/gateway")


class GatewayManager:
    """感官管理器"""

    def __init__(self, message_handler: Callable):
        """
        message_handler(platform, chat_id, content) -> reply
        """
        self.message_handler = message_handler
        self.sensors = {}  # platform_name -> sensor instance
        self.config_path = os.path.join(GATEWAY_DIR, "sensors.json")
        self._load_config()

    def _load_config(self):
        """加载感官配置"""
        os.makedirs(GATEWAY_DIR, exist_ok=True)
        if os.path.exists(self.config_path):
            with open(self.config_path) as f:
                self.config = json.load(f)
        else:
            self.config = {"sensors": {}}
            self._save_config()

    def _save_config(self):
        """保存感官配置"""
        with open(self.config_path, "w") as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)

    def list_sensors(self) -> dict:
        """列出所有感官的状态"""
        return {
            name: sensor.get("status", "unknown")
            for name, sensor in self.config.get("sensors", {}).items()
        }

    def register_sensor(self, platform: str, sensor_type: str, config: dict):
        """注册一个感官（加到配置中，但不一定启动）"""
        self.config["sensors"][platform] = {
            "type": sensor_type,
            "config": config,
            "status": "registered",
            "added_at": __import__("time").time(),
        }
        self._save_config()
        log.info(f"Sensor {platform} registered ({sensor_type})")

    def _start_sensor(self, platform: str, sensor_type: str, config: dict):
        """启动一个感官"""
        from src.gateway.feishu import FeishuSensor
        from src.gateway.api import ApiSensor

        sensor = None
        if sensor_type == "feishu":
            sensor = FeishuSensor(config, self.message_handler)
        elif sensor_type == "api":
            sensor = ApiSensor(config, self.message_handler)
        else:
            log.error(f"Unknown sensor type: {sensor_type}")
            return None

        if sensor:
            sensor.start()
            self.sensors[platform] = sensor
            self.config["sensors"][platform]["status"] = "active"
            self._save_config()
            log.info(f"Sensor {platform} started ({sensor_type})")
        return sensor

    def _stop_sensor(self, platform: str):
        """停止一个感官"""
        if platform in self.sensors:
            try:
                self.sensors[platform].stop()
            except Exception as e:
                log.warning(f"Error stopping sensor {platform}: {e}")
            del self.sensors[platform]
            self.config["sensors"][platform]["status"] = "stopped"
            self._save_config()

    def remove_sensor(self, platform: str):
        """移除一个感官（从配置中删除）"""
        self._stop_sensor(platform)
        if platform in self.config.get("sensors", {}):
            del self.config["sensors"][platform]
            self._save_config()
            log.info(f"Sensor {platform} removed")

    def reload_sensor(self, platform: str) -> bool:
        """热重启单个感官（改配置不重启整个 Nexus）"""
        if platform not in self.config.get("sensors", {}):
            log.error(f"Sensor {platform} not found")
            return False

        info = self.config["sensors"][platform]
        # 先停
        self._stop_sensor(platform)
        # 再启动
        self._start_sensor(platform, info["type"], info["config"])
        log.info(f"Sensor {platform} hot-reloaded")
        return True

    def start_all(self):
        """启动所有已注册的感官"""
        for platform, info in self.config.get("sensors", {}).items():
            if info["status"] != "active":
                self._start_sensor(platform, info["type"], info["config"])

    def stop_all(self):
        """停止所有感官"""
        for platform in list(self.sensors.keys()):
            self._stop_sensor(platform)

    def handle_event(self, platform: str, chat_id: str, content: str) -> Optional[str]:
        """处理外部平台发来的事件"""
        return self.message_handler(platform, chat_id, content)
