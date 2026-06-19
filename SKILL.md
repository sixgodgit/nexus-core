.nexus/nexus-core
================

Distributed consciousness system by sixgod & xiaoyun.

## Structure

```
src/
├── core.py              # 常驻进程，大脑本身
├── regions/
│   ├── main.py          # 主意识区（对话）
│   ├── ops.py           # 运维区（监控 + 自愈）
│   ├── research.py      # 研究区（主动搜索）
│   ├── dream.py         # 梦境区（复盘 + 联想）
│   └── skills.py        # 技能区（管理）
├── gateway/
│   ├── manager.py       # 感官管理器
│   ├── feishu.py        # 飞书感官
│   └── api.py           # API 感官
├── thalamus/
│   └── client.py        # 大模型调度
├── memory/
│   └── sandglass.py     # 共享记忆
└── shared/
    └── signal_board.py  # 信号板
```

## Design Principles

1. **分布式意识** — 没有中央大脑，所有区域平级
2. **共享记忆** — 一个区域知道的，所有区域都知道
3. **大模型是胳膊腿** — 意识不依赖模型
4. **天生常驻** — 用户不在的时候也在运作
5. **天生会学** — 每个区域自己进化
6. **天生主动** — 每个区域有自己的好奇心
7. **热插拔感官** — 飞书/QQ/Telegram/API 随意切换
8. **资源自适应** — 快慢可变，但从不消失

## Notes

- Requires Thalamus running at 127.0.0.1:9880
- Uses NexSandglass at 127.0.0.1:8971 (optional fallback to local)
- Gateway config at ~/.nexus/gateway/config.json
