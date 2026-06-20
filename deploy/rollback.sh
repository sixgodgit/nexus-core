#!/bin/bash
# rollback.sh — 一键回滚 Nexus 切换
# 用法: bash rollback.sh <backup_dir>
# 恢复 Hermes Gateway，停掉 Nexus feishu sensor

set -e

BACKUP_DIR="${1:-/root/.nexus/backups/20260620_1520_pre-switch}"

echo "=== Nexus 切换回滚 ==="
echo "Backup: $BACKUP_DIR"

# 1. 停止 Nexus 飞书感官
echo "[1/4] Stopping feishu sensor..."
pkill -f "feishu_sensor.py" 2>/dev/null || true

# 2. 停止 Nexus 主进程
echo "[2/4] Stopping nexus..."
pkill -f "python3 src/nexus.py" 2>/dev/null || true
sleep 2

# 3. 恢复 Hermes Gateway
echo "[3/4] Restoring Hermes Gateway..."
cp "$BACKUP_DIR/hermes/config.yaml" ~/.hermes/config.yaml 2>/dev/null || true
cp "$BACKUP_DIR/hermes/.env" ~/.hermes/.env 2>/dev/null || true
cp "$BACKUP_DIR/gateway/feishu.json" ~/.nexus/gateway/ 2>/dev/null || true

# 4. 启动 Hermes Gateway
echo "[4/4] Starting Hermes Gateway..."
systemctl restart hermes 2>/dev/null || echo "Note: 'hermes' service may not exist, try 'hermes gateway' manually"

echo "=== 回滚完成 ==="
echo ""
echo "等待 5 秒确认 Gateway 运行中..."
sleep 5
if tail -3 ~/.hermes/logs/gateway.log 2>/dev/null | grep -q "feishu connected"; then
    echo "✅ Feishu Gateway 重连成功"
else
    echo "⚠️ Gateway 状态待确认，请检查: tail -20 ~/.hermes/logs/gateway.log"
fi
