#!/bin/bash
# install.sh — 安装 Nexus Core
set -e

NEXUS_HOME="${NEXUS_HOME:-$HOME/.nexus}"
NEXUS_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "=== Nexus Core Installer ==="
echo "Source: $NEXUS_DIR"
echo "Data:   $NEXUS_HOME"

# 1. 创建数据目录
mkdir -p "$NEXUS_HOME"/{logs,run,gateway,dreams}

# 2. 安装依赖
echo "[1/3] Installing dependencies..."
pip3 install -q -r "$NEXUS_DIR/requirements.txt"

# 3. 安装 systemd 服务
echo "[2/3] Installing systemd service..."
sudo cp "$NEXUS_DIR/deploy/nexus.service" /etc/systemd/system/
sudo systemctl daemon-reload

# 4. 启动
echo "[3/3] Starting Nexus..."
sudo systemctl enable nexus
sudo systemctl start nexus

echo ""
echo "✓ Nexus Core installed and started"
echo "  Status: systemctl status nexus"
echo "  Logs:   tail -f $NEXUS_HOME/logs/nexus.log"
echo "  API:    curl http://127.0.0.1:8560/status"
