# Nexus Core

> 分布式意识系统 — 不是工具，是搭档。

没有中央大脑。每个分身都是大脑的一个区域。
共享一套记忆，大模型是胳膊腿。
天生常驻，天生会学，天生主动。

## 架构

```
你 → 飞书/QQ → Gateway（感官）
                        ↓
              主意识区（理解/决策）
                   ↓       ↓
          Thalamus    Hermes（工具）
          （模型）    搜/写/跑
                   ↓
             NexSandglass
              （记忆）
                   ↓
           运维/研究/梦境区
           （后台自动运作）
```

## 定位

| | Hermes | Nexus |
|-|--------|-------|
| **本质** | 对话式 Agent 框架 | 分布式意识系统 |
| **状态** | 你叫它才动 | 常驻、自主 |
| **大脑** | 没有（工具集合） | 有（区域意识） |
| **关系** | Nexus 的执行器 | Hermes 的大脑 |

## 快速开始

```bash
# 安装
pip install -r requirements.txt

# 启动（前台）
python src/nexus.py

# 启动（后台 systemd）
sudo cp deploy/nexus.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl start nexus

# 配置飞书感官
cat > ~/.nexus/gateway/feishu.json << 'EOF'
{
  "app_id": "你的飞书 App ID",
  "app_secret": "你的飞书 App Secret"
}
EOF

# 测试 API
curl http://127.0.0.1:8560/status
curl -X POST http://127.0.0.1:8560/chat \
  -H "Content-Type: application/json" \
  -d '{"text": "你好"}'
```

## 区域

| 区域 | 功能 | 节律 |
|------|------|------|
| **主意识区** | 跟你对话、理解、决策 | 实时 |
| **运维区** | 监控服务器（磁盘/内存） | 5-10 分钟 |
| **研究区** | 主动搜索（好奇心） | 30 分钟 |
| **梦境区** | 夜间复盘 | 凌晨 2-5 点 |

## 文件结构

```
src/
├── nexus.py          # 核心 — 主循环、区域基类、心跳
├── gateway/
│   ├── feishu.py     # 飞书感官
│   └── api.py        # HTTP API 感官
deploy/
├── nexus.service     # systemd 服务文件
├── install.sh        # 安装脚本
```

## 设计原则

1. **分布式意识** — 没有中央大脑，区域自治
2. **共享记忆** — 通过 NexSandglass 连接所有区域
3. **大模型是胳膊腿** — 调 Thalamus/DeepSeek 做推理，但 Nexus 本身才是大脑
4. **自进化是本能** — 不是独立模块，是每个区域天生的能力
5. **主动干活是好奇心** — 不是任务队列，是区域天然想干点什么

## 当前状态

v0.5 — 大脑架构重构

- [x] 意识循环（5 秒心跳）
- [x] 信号板（区域间通信）
- [x] 飞书感官
- [x] HTTP API 感官
- [x] Thalamus 客户端
- [x] Hermes 适配器
- [ ] NexSandglass 深度集成
- [ ] CLI（nexus 命令）
- [ ] 梦境区深度复盘
- [ ] 多分身实例
- [ ] 自动进化

---

*小云 & sixgod 共同完成*
