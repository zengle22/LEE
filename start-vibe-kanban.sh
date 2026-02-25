#!/bin/bash
# Vibe Kanban 局域网访问启动脚本
# 此脚本启动 vibe-kanban 并允许局域网其他机器访问

# 设置监听所有网络接口
export HOST=0.0.0.0

# 指定固定端口
export PORT=3000

# 可选：如果你通过反向代理访问，设置允许的源
# export VK_ALLOWED_ORIGINS=http://192.168.0.113:3000

# 获取本机局域网 IP
LOCAL_IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || ifconfig | grep "inet " | grep -v 127.0.0.1 | awk '{print $2}' | head -1)

echo "==================================="
echo "启动 Vibe Kanban (局域网模式)"
echo "==================================="

# 检查并停止正在运行的 vibe-kanban 进程
if pgrep -f "vibe-kanban" > /dev/null; then
    echo ""
    echo "⚠️  检测到正在运行的 vibe-kanban 进程"
    echo "正在停止..."
    pkill -f "vibe-kanban"
    sleep 2

    # 强制杀死残留进程
    if pgrep -f "vibe-kanban" > /dev/null; then
        echo "强制停止残留进程..."
        pkill -9 -f "vibe-kanban"
        sleep 1
    fi

    echo "✅ 已停止旧进程"
fi

echo ""
echo "本机访问: http://localhost:3000"
echo "局域网访问: http://${LOCAL_IP}:3000"
echo ""
echo "局域网内其他设备可通过以下地址访问："
echo "  http://${LOCAL_IP}:3000"
echo ""
echo "按 Ctrl+C 停止服务"
echo "==================================="
echo ""

# 启动 vibe-kanban
npx vibe-kanban
