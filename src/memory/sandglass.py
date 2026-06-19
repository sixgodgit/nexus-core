"""
共享记忆 — Nexus 所有区域的共同记忆空间。

封装 NexSandglass（海马体）的 save + search，
同时提供联想层和自动沉淀队列。
"""

import json
import os
import time
import requests
from typing import Optional

MEMORY_DIR = os.path.expanduser("~/.nexus/memory")
SANDGLASS_API = "http://127.0.0.1:8971"  # NexSandglass 默认端口
PENDING_FILE = os.path.expanduser("~/.nexus/run/pending_memories.json")


# ──────────────────────────────────────────────
# 核心层记忆
# ──────────────────────────────────────────────

def save_core(key: str, content: str, source: str = "main"):
    """写入核心层记忆（重要且持久的信息）"""
    # 先写入 NexSandglass
    try:
        r = requests.post(
            f"{SANDGLASS_API}/save",
            json={"key": key, "content": content, "source": f"nexus:{source}"},
            timeout=5,
        )
        if r.status_code == 200:
            return True
    except requests.RequestException:
        pass
    # 降级：写入本地文件
    os.makedirs(MEMORY_DIR, exist_ok=True)
    with open(os.path.join(MEMORY_DIR, "core.jsonl"), "a") as f:
        f.write(json.dumps({
            "key": key, "content": content, "ts": time.time(), "source": source
        }) + "\n")
    return True


def search(query: str, limit: int = 5) -> list:
    """搜索共享记忆"""
    # 先查 NexSandglass
    try:
        r = requests.get(
            f"{SANDGLASS_API}/search",
            params={"q": query, "limit": limit},
            timeout=5,
        )
        if r.status_code == 200:
            return r.json().get("results", [])
    except requests.RequestException:
        pass
    # 降级：本地全文搜索
    results = []
    path = os.path.join(MEMORY_DIR, "core.jsonl")
    if os.path.exists(path):
        with open(path) as f:
            for line in f:
                entry = json.loads(line)
                if query.lower() in str(entry).lower():
                    results.append(entry)
                    if len(results) >= limit:
                        break
    return results


# ──────────────────────────────────────────────
# 工作层记忆（临时任务状态）
# ──────────────────────────────────────────────

WORKING_DIR = os.path.expanduser("~/.nexus/memory/working")


def save_working(region: str, key: str, content: str):
    """写入工作层记忆，各区域独立"""
    os.makedirs(WORKING_DIR, exist_ok=True)
    path = os.path.join(WORKING_DIR, f"{region}.jsonl")
    with open(path, "a") as f:
        f.write(json.dumps({
            "key": key, "content": content, "ts": time.time()
        }) + "\n")


def get_working(region: str, key: str) -> Optional[str]:
    """读取工作层记忆"""
    path = os.path.join(WORKING_DIR, f"{region}.jsonl")
    if not os.path.exists(path):
        return None
    with open(path) as f:
        last = None
        for line in f:
            entry = json.loads(line)
            if entry["key"] == key:
                last = entry
    return last["content"] if last else None


# ──────────────────────────────────────────────
# 自动沉淀队列
# ──────────────────────────────────────────────

def queue_pending(content: str, source: str = "main", priority: int = 1):
    """添加待沉淀的记忆（对话结束后自动提取的）"""
    os.makedirs(os.path.dirname(PENDING_FILE), exist_ok=True)
    with open(PENDING_FILE, "a") as f:
        f.write(json.dumps({
            "content": content, "source": source, "priority": priority,
            "ts": time.time(), "processed": False
        }) + "\n")


def process_pending():
    """处理待沉淀的记忆"""
    if not os.path.exists(PENDING_FILE):
        return 0
    pending = []
    with open(PENDING_FILE) as f:
        for line in f:
            entry = json.loads(line)
            if not entry.get("processed"):
                pending.append(entry)
    if not pending:
        return 0
    processed = 0
    for entry in pending:
        key = f"auto_{int(entry['ts'])}_{entry['source']}"
        save_core(key, entry["content"], source=entry["source"])
        entry["processed"] = True
        processed += 1
    # 重写文件
    with open(PENDING_FILE, "w") as f:
        for line in open(PENDING_FILE):
            entry = json.loads(line)
            if entry["ts"] in [e["ts"] for e in pending]:
                entry["processed"] = True
            f.write(json.dumps(entry) + "\n")
    return processed
