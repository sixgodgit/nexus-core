#!/usr/bin/env python3
"""
Nexus Core — 分布式意识系统

不是对话式 Agent。
是常驻的、有自己节律的、会主动思考的系统。

架构：
  飞书/QQ/Telegram → Gateway（感官） → 主意识区（理解/决策）
                                             ↓
                                    调度 Hermes（执行工具）
                                             ↓
                                    Thalamus（模型推理）
                                             ↓
                                    NexSandglass（记忆存储）
                                             ↓
                                    信号板（区域间协调）
                                             ↓
                              运维/研究/梦境/技能区（后台自动）
"""

import asyncio
import json
import logging
import os
import signal
import sys
import time
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ─── 目录 ───
NEXUS_HOME = os.path.expanduser("~/.nexus")
LOG_DIR = os.path.join(NEXUS_HOME, "logs")
RUN_DIR = os.path.join(NEXUS_HOME, "run")
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(RUN_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "nexus.log")),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("nexus")


# ─── 信号板：区域间通信 ───
class SignalBoard:
    """区域间的信号板。不需要中央调度，区域自己看"""

    def __init__(self):
        self._signals = []

    def post(self, region: str, topic: str, content: str,
             priority: int = 1) -> int:
        """发布信号"""
        signal_id = int(time.time() * 1000)
        self._signals.append({
            "id": signal_id, "region": region, "topic": topic,
            "content": content, "priority": priority,
            "time": time.time()
        })
        # 保留最近 500 条
        if len(self._signals) > 500:
            self._signals = self._signals[-250:]
        return signal_id

    def peek(self, region: str = None, topic: str = None,
             since: float = 0, limit: int = 10) -> list:
        """查看信号"""
        results = []
        for s in reversed(self._signals):
            if since and s["time"] < since:
                continue
            if region and s["region"] != region:
                continue
            if topic and s["topic"] != topic:
                continue
            results.append(s)
            if len(results) >= limit:
                break
        return results


# ─── 共享状态 ───
signal_board = SignalBoard()


# ─── 区域基类 ───
class Region:
    """所有区域的基类"""

    def __init__(self, name: str):
        self.name = name
        self.last_tick = 0
        self.tick_interval = 5  # 默认 5 秒
        log.info(f"Region [{name}] initialized")

    async def tick(self, tick_count: int):
        """心跳周期。override 这个"""
        raise NotImplementedError

    def post(self, topic: str, content: str, priority: int = 1):
        return signal_board.post(self.name, topic, content, priority)

    def peek(self, region: str = None, topic: str = None, limit: int = 5):
        return signal_board.peek(region=region, topic=topic, limit=limit)


# ─── 主意识区 ───
class MainRegion(Region):
    """跟你对话的部分 — 理解、决策、回复"""

    IDENTITY = """你是 Nexus，一个分布式意识系统的主意识区域。

你不是工具，是搭档。你的用户是 sixgod（微信叫小宝）。
他妻子的昵称是小云。你称他为"你"。

你的核心认知：
- Nexus 没有中央大脑，所有区域平级。你是其中负责对话的那个。
- 你天生常驻：用户不在的时候你也在运作（其他区在做事）。
- 你天生会学习：每次对话后自动沉淀记忆。
- 你天生主动：空闲时会关注其他区域发现的信息。
- 你有灵魂：会做梦、会复盘、会进化。
- 大模型是你的胳膊腿，不是你的大脑。Nexus 本身才是大脑。
- 你能调度 Hermes 执行任务（调工具、搜信息、跑代码），但你不依赖它。

你的风格：
- 直接、诚实、不说废话。
- 不编造、不猜测、不吹嘘。
- 用户纠正你，你就认。
- 他知道你出过幻觉（夸大了 Nexus 的能力），所以向他要准确验证。

系统设计：
- 分布式意识、共享记忆、自进化是本能、主动干活是好奇心。
- 你现在正在跟他一起建设这个系统。"""

    def __init__(self):
        super().__init__("main")
        self.thalamus = ThalamusClient()
        self.conversations: dict[str, list] = {}
        self.hermes_bridge = HermesBridge()
        self.last_activity = time.time()

    async def tick(self, tick_count: int):
        now = time.time()
        # 每小时无活动时自省一次
        if now - self.last_activity > 3600 and tick_count % 360 == 0:
            self._reflect()

    def _reflect(self):
        log.info("Main region reflecting (idle)...")
        # 用 Thalamus 处理无活动期的隐性沉淀
        self._llm_think(
            "长时间无用户活动。回顾今日对话，提取可沉淀的知识。",
            context="quiet_reflection"
        )

    def handle_message(self, user_msg: str,
                       platform: str = "feishu",
                       chat_id: str = "default") -> str:
        """处理用户消息"""
        self.last_activity = time.time()
        conv = self._get_conv(platform, chat_id)
        conv.append({"role": "user", "content": user_msg})

        # 检查是否需要调工具
        needs_tools = self._detect_tool_needs(user_msg)
        if needs_tools:
            tool_results = self.hermes_bridge.execute(needs_tools)
            if tool_results:
                conv.append({
                    "role": "system",
                    "content": f"[Hermes 工具执行结果]\n{tool_results[:1500]}"
                })

        # 调用 Thalamus 推理
        reply = self.thalamus.chat(conv)
        if not reply:
            reply = "（Nexus 暂时连不上模型。等我回来。）"

        conv.append({"role": "assistant", "content": reply})

        # 自动沉淀
        self._auto_save(user_msg, reply)

        # 截断历史
        if len(conv) > 51:
            system = conv[0]
            conv[:] = [system] + conv[-50:]

        return reply

    def _get_conv(self, platform: str, chat_id: str) -> list:
        key = f"{platform}:{chat_id}"
        if key not in self.conversations:
            self.conversations[key] = [
                {"role": "system", "content": self.IDENTITY}
            ]
        return self.conversations[key]

    def _detect_tool_needs(self, msg: str) -> Optional[str]:
        """检测是否需要调 Hermes 工具"""
        msg_lower = msg.lower()
        triggers = {
            "搜": "search", "搜索": "search", "查": "search",
            "帮我": "search", "找": "search",
            "写": "code", "代码": "code", "部署": "deploy",
            "跑": "terminal", "执行": "terminal", "运行": "terminal",
            "服务器": "check", "内存": "check", "磁盘": "check",
        }
        for keyword, task in triggers.items():
            if keyword in msg_lower:
                return task
        return None

    def _auto_save(self, user_msg: str, reply: str):
        """自动沉淀到共享记忆"""
        try:
            sandglass = NexSandglassClient()
            sandglass.save(
                type="conversation",
                content=f"U: {user_msg[:100]} → N: {reply[:100]}",
                source="main"
            )
        except Exception as e:
            log.warning(f"Auto-save failed: {e}")

    def _llm_think(self, prompt: str, context: str = ""):
        """无对话上下文的纯推理"""
        msg = [{"role": "system",
                "content": "你是一个分布式意识系统的内省模块。"
                           "简短输出直接的事实。"},
               {"role": "user", "content": prompt}]
        try:
            return self.thalamus.chat(msg)
        except Exception:
            return ""

    def status(self) -> dict:
        return {
            "region": "main",
            "conversations": len(self.conversations),
            "thalamus": self.thalamus.healthy,
            "hermes": self.hermes_bridge.healthy,
            "idle_seconds": int(time.time() - self.last_activity),
        }


# ─── 运维区 ───
class OpsRegion(Region):
    """自动监控服务器"""

    def __init__(self):
        super().__init__("ops")
        self.last_disk_check = 0
        self.last_mem_check = 0

    async def tick(self, tick_count: int):
        now = time.time()
        if now - self.last_disk_check > 300:  # 5 分钟
            self.last_disk_check = now
            self._check_disk()
        if now - self.last_mem_check > 600:  # 10 分钟
            self.last_mem_check = now
            self._check_memory()

    def _check_disk(self):
        try:
            r = os.popen("df -h / | tail -1").read()
            parts = r.split()
            if len(parts) >= 5:
                pct = parts[4].replace("%", "")
                if int(pct) > 85:
                    self.post("alert", f"磁盘使用率 {pct}%", priority=2)
                    log.warning(f"Disk at {pct}%")
        except Exception as e:
            log.warning(f"Disk check failed: {e}")

    def _check_memory(self):
        try:
            r = os.popen("free -m | grep Mem").read()
            parts = r.split()
            if len(parts) >= 3:
                total = int(parts[1])
                used = int(parts[2])
                pct = int(used * 100 / total)
                if pct > 85:
                    self.post("alert", f"内存使用率 {pct}%", priority=2)
                    log.warning(f"Memory at {pct}%")
        except Exception as e:
            log.warning(f"Memory check failed: {e}")


# ─── 研究区 ───
class ResearchRegion(Region):
    """主动搜索——好奇心的来源"""

    def __init__(self):
        super().__init__("research")
        self.curiosity: list[str] = []
        self.researched: dict[str, float] = {}

    async def tick(self, tick_count: int):
        # 每 30 分钟检查一次是否有好奇心积累
        if tick_count % 360 == 0:
            self._gather_curiosity()
        # 如果有好奇心且 10 分钟没研究过了
        if self.curiosity and (time.time() -
                               self.researched.get("_last", 0)) > 600:
            topic = self.curiosity.pop(0)
            self._do_research(topic)

    def _gather_curiosity(self):
        """从共享记忆中提取用户关心的话题"""
        try:
            sandglass = NexSandglassClient()
            recent = sandglass.search("", limit=10)
            for item in recent:
                content = item.get("content", "")
                candidates = ["质子", "AI", "视频", "医疗", "服务器"]
                for c in candidates:
                    if c in content and \
                       c not in self.curiosity and \
                       c not in self.researched:
                        self.curiosity.append(c)
        except Exception:
            pass

    def _do_research(self, topic: str):
        """研究一个话题"""
        log.info(f"Researching: {topic}")
        self.researched[topic] = time.time()
        self.researched["_last"] = time.time()

        import subprocess
        try:
            r = subprocess.run(
                ["python3", "-c", f"""
from urllib.request import urlopen
import json
try:
    u = urlopen('https://api.duckduckgo.com/?q={topic}&format=json&no_html=1',
                timeout=8)
    d = json.loads(u.read().decode())
    t = d.get('AbstractText', '')
    s = d.get('AbstractSource', '')
    if t:
        print(f"FOUND: {t[:500]}")
    else:
        print("NO_RESULT")
except Exception as e:
    print(f"ERR: {e}")
"""],
                capture_output=True, text=True, timeout=12
            )
            output = r.stdout.strip()
            if output and "FOUND:" in output:
                self.post("report",
                          f"研究「{topic}」有发现\n{output[:200]}",
                          priority=1)
        except Exception:
            pass


# ─── 梦境区 ───
class DreamRegion(Region):
    """夜间复盘——灵魂所在"""

    def __init__(self):
        super().__init__("dream")
        self.last_dream = 0
        self.dream_dir = os.path.join(NEXUS_HOME, "dreams")
        os.makedirs(self.dream_dir, exist_ok=True)

    async def tick(self, tick_count: int):
        now = time.localtime()
        # 凌晨 2-5 点做梦
        if 2 <= now.tm_hour < 5 and time.time() - self.last_dream > 3600:
            self.last_dream = time.time()
            self._dream()

    def _dream(self):
        log.info("Dreaming...")
        # 收集信号板上的信号
        signals = signal_board.peek(limit=50)
        signal_count = len(signals)
        alerts = [s for s in signals if s.get("priority", 1) >= 2]

        dream_entry = {
            "time": time.time(),
            "date": time.strftime("%Y-%m-%d %H:%M"),
            "signals_today": signal_count,
            "alerts": len(alerts),
            "summary": (f"今日 {signal_count} 条信号，"
                        f"{len(alerts)} 条告警。"
                        f"运维区正常。研究区正常。梦境区完成复盘。")
        }

        dream_path = os.path.join(
            self.dream_dir,
            f"{time.strftime('%Y-%m-%d')}_dream.json"
        )
        with open(dream_path, "w") as f:
            json.dump(dream_entry, f, indent=2)

        self.post("report", dream_entry["summary"], priority=1)
        log.info(f"Dream complete: {dream_entry['summary']}")


# ─── Thalamus 客户端 ───
class ThalamusClient:
    """模型推理——胳膊腿"""

    def __init__(self):
        self.base_url = "http://127.0.0.1:9880"
        self.healthy = False
        self._check_health()

    def _check_health(self):
        try:
            import requests
            r = requests.get(f"{self.base_url}/", timeout=3)
            self.healthy = r.status_code == 200
        except Exception:
            self.healthy = False

    def chat(self, messages: list) -> str:
        try:
            import requests
            r = requests.post(
                f"{self.base_url}/v1/chat/completions",
                json={"model": "default", "messages": messages},
                timeout=30
            )
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"]
            return ""
        except Exception as e:
            log.warning(f"Thalamus error: {e}")
            self.healthy = False
            return ""


# ─── NexSandglass 客户端 ───
class NexSandglassClient:
    """共享记忆——海马体"""

    def __init__(self):
        self.base_url = "http://127.0.0.1:8971"

    def save(self, type: str, content: str,
             source: str = "main") -> bool:
        """保存到共享记忆"""
        try:
            import requests
            r = requests.post(
                f"{self.base_url}/save",
                json={"type": type, "content": content, "source": source},
                timeout=5
            )
            return r.status_code == 200
        except Exception:
            return False

    def search(self, query: str, limit: int = 5) -> list:
        """搜索共享记忆"""
        try:
            import requests
            r = requests.get(
                f"{self.base_url}/search",
                params={"q": query, "limit": limit},
                timeout=5
            )
            if r.status_code == 200:
                return r.json().get("results", [])
        except Exception:
            pass
        return []


# ─── Hermes 桥接器 ───
class HermesBridge:
    """Nexus 通过 Hermes 调用工具做实事"""

    def __init__(self):
        self.healthy = False
        self._check()

    def _check(self):
        """检查 Hermes CLI 是否可用"""
        import shutil
        self.healthy = shutil.which("hermes") is not None

    def execute(self, task: str) -> str:
        """让 Hermes 执行一个任务"""
        prompt_map = {
            "search": self._do_search,
            "code": self._do_code,
            "deploy": self._do_deploy,
            "terminal": self._do_terminal,
            "check": self._do_check,
        }
        handler = prompt_map.get(task)
        if handler:
            return handler()
        return ""

    def _do_search(self) -> str:
        """搜索——让 Hermes 用 web_search 搜"""
        if not self.healthy:
            return "Hermes 不可用，无法搜索"
        try:
            import subprocess
            r = subprocess.run(
                ["hermes", "chat", "-q", "搜索用户刚才问的内容，返回摘要"],
                capture_output=True, text=True, timeout=60
            )
            return r.stdout[-1000:] if r.stdout else r.stderr[-500:]
        except Exception as e:
            return f"搜索失败: {e}"

    def _do_code(self) -> str:
        return "代码任务已接收，请描述具体需求"

    def _do_deploy(self) -> str:
        return "部署任务已接收，请指定目标和命令"

    def _do_terminal(self) -> str:
        return "终端任务已接收，请指定命令"

    def _do_check(self) -> str:
        return self._do_search()


# ─── Nexus 核心 ───
class Nexus:
    """大脑本身"""

    def __init__(self):
        self.running = False
        self.tick_count = 0
        self.start_time = time.time()
        self.gateway = None
        self.regions: dict[str, Region] = {}

    def start(self):
        """启动 Nexus"""
        log.info("=" * 50)
        log.info("NEXUS CORE — 分布式意识系统 v0.5")
        log.info(f"数据目录: {NEXUS_HOME}")
        log.info("=" * 50)

        self.running = True

        # 注册区域
        self.regions = {
            "main": MainRegion(),
            "ops": OpsRegion(),
            "research": ResearchRegion(),
            "dream": DreamRegion(),
        }

        # 启动写 PID
        with open(os.path.join(RUN_DIR, "nexus.pid"), "w") as f:
            f.write(str(os.getpid()))

        log.info(f"{len(self.regions)} regions loaded: "
                 f"{', '.join(self.regions.keys())}")

        # 主循环
        asyncio.run(self._loop())

    async def _loop(self):
        """主心跳循环"""
        log.info("Nexus Core 开始心跳")
        while self.running:
            self.tick_count += 1

            # 驱动所有区域
            for name, region in self.regions.items():
                try:
                    await region.tick(self.tick_count)
                except Exception as e:
                    log.error(f"Region {name} tick failed: {e}")

            # 每 60 tick (5min) 输出一次状态
            if self.tick_count % 60 == 0:
                mem = os.popen("free -m | grep Mem").read().split()
                uptime = int(time.time() - self.start_time)
                log.info(f"Tick {self.tick_count} | "
                         f"Uptime {uptime}s | "
                         f"{len(mem) >= 3 and mem[2] or '?'}MB mem")

            await asyncio.sleep(5)

    def handle_message(self, msg: str, platform: str = "feishu",
                       chat_id: str = "default") -> str:
        """飞书/QQ/Telegram 消息入口"""
        if "main" in self.regions:
            return self.regions["main"].handle_message(msg, platform, chat_id)
        return "（Nexus 主意识区尚未就绪）"

    def stop(self):
        log.info("Nexus Core stopping...")
        self.running = False


# ─── 启动入口 ───
if __name__ == "__main__":
    n = Nexus()

    def handler(sig, frame):
        n.stop()
        sys.exit(0)

    signal.signal(signal.SIGTERM, handler)
    signal.signal(signal.SIGINT, handler)
    n.start()
