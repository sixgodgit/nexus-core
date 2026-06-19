# Nexus Core

> 分布式意识系统 — 不是工具，是搭档。
> 
> 没有中央大脑。每个分身都是大脑的一个区域。
> 共享一套记忆，大模型是胳膊腿。
> 天生常驻，天生会学，天生主动。

## 架构

```
                     Nexus 共享记忆
                   (海马体 + 联想皮层)
                ↕    ↕    ↕    ↕    ↕
        主意识区  运维区  研究区  梦境区  技能区
                ↕    ↕    ↕    ↕    ↕
                  大模型 API（胳膊腿）
                  Thalamus 调度
                ↕    ↕    ↕    ↕    ↕
              飞书    QQ    Telegram   API
```

## 快速部署

```bash
git clone https://github.com/sixgodgit/nexus-core
cd nexus-core
sudo bash deploy/install.sh
```

## 依赖

- Python 3.10+
- Thalamus（模型调度）
- NexSandglass（记忆存储）
- systemd
