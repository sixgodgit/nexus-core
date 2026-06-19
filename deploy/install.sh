#!/bin/bash
# Nexus Core 部署脚本
# 用法: sudo bash deploy/install.sh

set -e

echo "🚀 Nexus Core 部署开始"
echo "======================"

# 1. 检查 Python
PYTHON=$(which python3)
if [ -z "$PYTHON" ]; then
    echo "❌ Python3 未安装"
    exit 1
fi
echo "✓ Python3: $($PYTHON --version)"

# 2. 创建数据目录
echo "📁 创建数据目录..."
mkdir -p /root/.nexus/{run,logs,memory,research,dreams,gateway,memory/working}

# 3. 安装 Python 依赖
echo "📦 安装依赖..."
pip3 install requests --quiet 2>/dev/null

# 4. 安装 systemd 服务
echo "⚙️ 安装 systemd 服务..."
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cp "$SCRIPT_DIR/nexus.service" /etc/systemd/system/nexus-core.service
systemctl daemon-reload

# 5. 验证代码
echo "🔍 验证代码..."
$PYTHON -m py_compile /root/nexus/src/core.py 2>/dev/null && echo "✓ core.py" || echo "⚠️ core.py 有语法警告"
$PYTHON -m py_compile /root/nexus/src/shared/signal_board.py 2>/dev/null && echo "✓ signal_board.py"
$PYTHON -m py_compile /root/nexus/src/memory/sandglass.py 2>/dev/null && echo "✓ sandglass.py"
$PYTHON -m py_compile /root/nexus/src/thalamus/client.py 2>/dev/null && echo "✓ thalamus client"
$PYTHON -m py_compile /root/nexus/src/gateway/manager.py 2>/dev/null && echo "✓ gateway manager"

echo ""
echo "✅ Nexus Core 已安装！"
echo ""
echo "启动: sudo systemctl start nexus-core"
echo "状态: sudo systemctl status nexus-core"
echo "日志: tail -f /root/.nexus/logs/core.log"
echo "停止: sudo systemctl stop nexus-core"
echo ""
echo "Nexus 数据目录: /root/.nexus/"
echo "======================"
