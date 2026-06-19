"""
信号板 — Nexus 各区域之间的"喊话区"

不需要中央调度，不需要分身间 API。
一个区域写在信号板上的信息，其他区域瞟一眼就知道了。
"""

import json
import os
import time
from typing import Optional

SIGNAL_FILE = os.path.expanduser("~/.nexus/run/signal_board.json")


def _ensure_board():
    os.makedirs(os.path.dirname(SIGNAL_FILE), exist_ok=True)
    if not os.path.exists(SIGNAL_FILE):
        with open(SIGNAL_FILE, "w") as f:
            json.dump({"signals": []}, f)


def post(region: str, topic: str, content: str, priority: int = 1):
    """发信号到信号板"""
    _ensure_board()
    with open(SIGNAL_FILE, "r") as f:
        board = json.load(f)
    board["signals"].append({
        "id": f"sig_{int(time.time())}_{len(board['signals'])}",
        "region": region,
        "topic": topic,
        "content": content,
        "priority": priority,
        "ts": time.time(),
        "read": False,
    })
    # 只保留最近 200 条
    if len(board["signals"]) > 200:
        board["signals"] = board["signals"][-200:]
    with open(SIGNAL_FILE, "w") as f:
        json.dump(board, f, indent=2, ensure_ascii=False)


def peek(topic: Optional[str] = None, since: Optional[float] = None, region: Optional[str] = None) -> list:
    """看一眼信号板，获取关心的信号"""
    _ensure_board()
    with open(SIGNAL_FILE, "r") as f:
        board = json.load(f)
    signals = board["signals"]
    if topic:
        signals = [s for s in signals if s["topic"] == topic]
    if since:
        signals = [s for s in signals if s["ts"] > since]
    if region:
        signals = [s for s in signals if s.get("region") == region]
    return signals[-20:]  # 最多返回最近 20 条


def mark_read(signal_id: str):
    """标记信号已读"""
    _ensure_board()
    with open(SIGNAL_FILE, "r") as f:
        board = json.load(f)
    for s in board["signals"]:
        if s["id"] == signal_id:
            s["read"] = True
            break
    with open(SIGNAL_FILE, "w") as f:
        json.dump(board, f, indent=2, ensure_ascii=False)


def clear_old(hours: int = 48):
    """清理超过指定小时的信号"""
    _ensure_board()
    cutoff = time.time() - hours * 3600
    with open(SIGNAL_FILE, "r") as f:
        board = json.load(f)
    board["signals"] = [s for s in board["signals"] if s["ts"] > cutoff]
    with open(SIGNAL_FILE, "w") as f:
        json.dump(board, f, indent=2, ensure_ascii=False)
