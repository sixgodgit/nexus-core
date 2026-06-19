"""
运维区域 — 天生在监控服务器

不需要任何人告诉它。它自己就在监控。
看到问题 -> 自己诊断 -> 能修就修 -> 不能修就发信号。
"""

import asyncio
import json
import logging
import os
import subprocess
import time

from src.memory.sandglass import save_core, search
from src.shared.signal_board import post, peek

log = logging.getLogger("nexus.ops")

DISK_THRESHOLD = 85  # 磁盘告警阈值
MEM_THRESHOLD = 90   # 内存告警阈值


class OpsRegion:
    """运维区域"""

    def __init__(self):
        self.last_scan = 0
        self.last_repair = 0
        self.known_issues = set()
        log.info("OpsRegion initialized")

    async def tick(self, tick_count: int):
        """每个心跳周期检查"""

        # 监控扫描（每 30 秒一次）
        if time.time() - self.last_scan > 30:
            self.last_scan = time.time()
            await self._scan_system()

        # 周期性修复尝试（每 10 分钟）
        if time.time() - self.last_repair > 600:
            self.last_repair = time.time()
            await self._try_repair()

    async def _scan_system(self):
        """扫描系统状态"""
        issues = []

        # 磁盘
        try:
            r = subprocess.run(
                "df -h / | tail -1 | awk '{print $5}' | tr -d '%'",
                shell=True, capture_output=True, text=True, timeout=5
            )
            disk_pct = int(r.stdout.strip())
            if disk_pct > DISK_THRESHOLD:
                issues.append(f"disk:{disk_pct}%")
                post("ops", "disk_alert",
                     f"磁盘使用率 {disk_pct}%，超过阈值 {DISK_THRESHOLD}%",
                     priority=2)
        except (subprocess.TimeoutExpired, ValueError, FileNotFoundError):
            pass

        # 内存
        try:
            r = subprocess.run(
                "free -m | grep Mem | awk '{print $3/$2 * 100}'",
                shell=True, capture_output=True, text=True, timeout=5
            )
            mem_pct = float(r.stdout.strip())
            if mem_pct > MEM_THRESHOLD:
                issues.append(f"memory:{mem_pct:.0f}%")
                post("ops", "mem_alert",
                     f"内存使用率 {mem_pct:.0f}%，超过阈值 {MEM_THRESHOLD}%",
                     priority=2)
        except (subprocess.TimeoutExpired, ValueError, FileNotFoundError):
            pass

        # 服务健康
        services = ["thalamus", "hermes-gateway", "nexus-core"]
        for svc in services:
            try:
                r = subprocess.run(
                    f"systemctl is-active {svc}",
                    shell=True, capture_output=True, text=True, timeout=5
                )
                status = r.stdout.strip()
                if status != "active":
                    issues.append(f"service:{svc}:{status}")
                    post("ops", "service_down",
                         f"服务 {svc} 状态异常: {status}",
                         priority=2)
            except subprocess.TimeoutExpired:
                issues.append(f"service:{svc}:timeout")

        # 记录状态到共享记忆
        if issues:
            save_core("nexus:ops:issues",
                      json.dumps({"ts": time.time(), "issues": issues}),
                      source="ops")

        # 记录健康状态（每 5 次扫描一次）
        if not issues and int(time.time()) % 300 < 30:
            save_core("nexus:ops:healthy",
                      json.dumps({"ts": time.time()}), source="ops")

    async def _try_repair(self):
        """尝试自动修复已知问题"""
        if not self.known_issues:
            return

        for issue in list(self.known_issues):
            if issue.startswith("service:"):
                svc = issue.split(":")[1]
                log.info(f"Auto-repairing service: {svc}")
                try:
                    subprocess.run(
                        f"systemctl restart {svc}",
                        shell=True, timeout=10
                    )
                    # 稍后检查是否恢复
                    await asyncio.sleep(5)
                    r = subprocess.run(
                        f"systemctl is-active {svc}",
                        shell=True, capture_output=True, text=True, timeout=5
                    )
                    if r.stdout.strip() == "active":
                        self.known_issues.discard(issue)
                        post("ops", "repair",
                             f"✅ 自动修复 {svc} 成功", priority=1)
                except subprocess.TimeoutExpired:
                    log.warning(f"Failed to repair {svc}")
