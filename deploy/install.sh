#!/bin/bash
# Nexus Core 一键部署脚本
# 用法: bash deploy/install.sh [server]
#   server: 可选，目标服务器 SSH 地址（如 root@162.0.225.252）
#   不传参数则在本地安装

set -e

TARGET="${1:-local}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "🚀 Nexus Core v0.4 部署"
echo "========================"
echo "目标: $TARGET"
echo ""

# 本地安装函数
install_local() {
    echo "📁 创建数据目录..."
    mkdir -p /root/.nexus/{run,logs,memory,research,dreams,gateway,memory/working}

    echo "📦 安装依赖..."
    pip3 install requests pyyaml --quiet 2>/dev/null || true

    echo "⚙️ 安装 systemd 服务..."
    cp "$REPO_DIR/deploy/nexus.service" /etc/systemd/system/nexus-core.service
    systemctl daemon-reload

    echo "🔍 验证代码..."
    cd "$REPO_DIR"
    python3 -m py_compile src/core.py
    python3 -m py_compile src/shared/signal_board.py
    python3 -m py_compile src/memory/sandglass.py
    python3 -m py_compile src/thalamus/client.py
    python3 -m py_compile src/gateway/manager.py
    python3 -m py_compile src/regions/main.py
    python3 -m py_compile src/regions/ops.py
    python3 -m py_compile src/regions/research.py
    python3 -m py_compile src/regions/dream.py
    python3 -m py_compile src/regions/skills.py

    echo ""
    echo "✅ Nexus Core 已安装到本机！"
    echo ""
    echo "启动: sudo systemctl start nexus-core"
    echo "状态: sudo systemctl status nexus-core"
    echo "日志: tail -f /root/.nexus/logs/core.log"
    echo "停止: sudo systemctl stop nexus-core"
}

# 美服部署函数
install_remote() {
    echo "🌐 部署到远程服务器: $TARGET"

    # 1. 测试 SSH 连接
    echo "   测试连接..."
    ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no "$TARGET" "echo OK && python3 --version" || {
        echo "❌ 无法连接到 $TARGET"
        exit 1
    }

    # 2. 远程创建目录并传输文件
    echo "   传输代码..."
    ssh "$TARGET" "mkdir -p /root/nexus"
    scp -r "$REPO_DIR/src" "$REPO_DIR/deploy" "$REPO_DIR/requirements.txt" "$REPO_DIR/README.md" "$TARGET:/root/nexus/"

    # 3. 远程运行安装
    echo "   远程安装..."
    ssh -t "$TARGET" "cd /root/nexus && bash deploy/install.sh"

    echo ""
    echo "✅ Nexus Core 已部署到 $TARGET！"
    echo ""
    echo "远程操作: ssh $TARGET"
    echo "启动: ssh $TARGET 'systemctl start nexus-core'"
    echo "日志: ssh $TARGET 'tail -f /root/.nexus/logs/core.log'"
}

# 执行
if [ "$TARGET" = "local" ]; then
    install_local
else
    install_remote
fi

echo ""
echo "📋 后续步骤:"
echo "  - 检查飞书配置: /root/.nexus/gateway/sensors.json"
echo "  - 查看运行状态: systemctl status nexus-core"
echo "  - 查看日志: tail -f /root/.nexus/logs/core.log"
echo "  - API 接口: http://127.0.0.1:8670"
echo ""
echo "========================================"
