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
import importlib
import json
import logging
import os
import sys
from typing import Optional

log = logging.getLogger("nexus.gateway")

GATEWAY_DIR = os.path.expanduser("~/.nexus/gateway")


class GatewayManager:
    """感官管理器"""

    def __init__(self, message_handler):
        """
        message_handler: 接收消息的回调函数
          签名: handle_message(platform: str, chat_id: str, content: str) -> str
        """
        self.message_handler = message_handler
        self.sensors = {}  # platform_name -> sensor instance
        self.config_path = os.path.join(GATEWAY_DIR, "config.json")
        self._load_config()

    def _load_config(self):
        """加载 Gateway 配置"""
        os.makedirs(GATEWAY_DIR, exist_ok=True)
        self.config = {
            "sensors": {}
        }
        if os.path.exists(self.config_path):
            with open(self.config_path) as f:
                self.config = json.load(f)

    def _save_config(self):
        """保存配置"""
        with open(self.config_path, "w") as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)

    def list_sensors(self) -> dict:
        """列出所有感官的状态"""
        return {
            name: sensor.get("status", "unknown")
            for name, sensor in self.config.get("sensors", {}).items()
        }

    def register_sensor(self, platform: str, sensor_type: str, config: dict):
        """
        注册一个感官。

        platform: 平台名（feishu, qq, telegram, api 等）
        sensor_type: 实现类型（native_feishu, native_qq 等）
        config: 平台特定配置（token, webhook 等）
        """
        self.config["sensors"][platform] = {
            "type": sensor_type,
            "config": config,
            "status": "registered",
            "added_at": __import__("time").time(),
        }
        self._save_config()
        log.info(f"Sensor {platform} registered ({sensor_type})")

    def remove_sensor(self, platform: str):
        """移除一个感官"""
        if platform in self.config.get("sensors", {}):
            self._stop_sensor(platform)
            del self.config["sensors"][platform]
            self._save_config()
            log.info(f"Sensor {platform} removed")

    def _stop_sensor(self, platform: str):
        """停止一个感官的运行"""
        if platform in self.sensors:
            try:
                self.sensors[platform].stop()
            except Exception as e:
                log.warning(f"Error stopping sensor {platform}: {e}")
            del self.sensors[platform]

    def _start_sensor(self, platform: str, sensor_type: str, config: dict):
        """启动一个感官"""
        try:
            # 动态加载感官实现
            module_path = f"src.gateway.sensors.{sensor_type}"
            if sensor_type == "feishu":
                from src.gateway.feishu import FeishuSensor
                sensor = FeishuSensor(config, self.message_handler)
            elif sensor_type == "api":
                from src.gateway.api import ApiSensor
                sensor = ApiSensor(config, self.message_handler)
            else:
                log.error(f"Unknown sensor type: {sensor_type}")
                return None

            self.sensors[platform] = sensor
            sensor.start()
            self.config["sensors"][platform]["status"] = "active"
            self._save_config()
            log.info(f"Sensor {platform} started ({sensor_type})")
            return sensor

        except Exception as e:
            log.error(f"Failed to start sensor {platform}: {e}")
            self.config["sensors"][platform]["status"] = "error"
            self._save_config()
            return None

    async def start_all(self):
        """启动所有已注册的感官"""
        for platform, info in self.config.get("sensors", {}).items():
            if info["status"] != "active":
                self._start_sensor(platform, info["type"], info["config"])

    async def stop_all(self):
        """停止所有感官"""
        for platform in list(self.sensors.keys()):
            self._stop_sensor(platform)

    def reload_sensor(self, platform: str):
        """热重启单个感官"""
        if platform not in self.config.get("sensors", {}):
            log.error(f"Sensor {platform} not found in config")
            return False

        info = self.config["sensors"][platform]
        self._stop_sensor(platform)
        self._start_sensor(platform, info["type"], info["config"])
        return True
