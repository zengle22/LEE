#!/bin/bash
# 检查 vibe-kanban 局域网访问状态

echo "======================================"
echo "Vibe Kanban 局域网访问检查"
echo "======================================"
echo ""

# 1. 获取本机 IP
LOCAL_IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || ifconfig | grep "inet " | grep -v 127.0.0.1 | awk '{print $2}' | head -1)
echo "📡 本机局域网 IP: $LOCAL_IP"
echo ""

# 2. 检查 vibe-kanban 进程
echo "🔍 检查 vibe-kanban 进程..."
if pgrep -f "vibe-kanban" > /dev/null; then
    echo "✅ vibe-kanban 正在运行"
    VK_PID=$(pgrep -f "vibe-kanban" | head -1)
    echo "   PID: $VK_PID"
else
    echo "❌ vibe-kanban 未运行"
    echo "   请运行: ./start-vibe-kanban.sh"
    exit 1
fi
echo ""

# 3. 检查端口监听状态
echo "🔍 检查端口 3000 监听状态..."
PORT_INFO=$(lsof -i :3000 -P 2>/dev/null | grep LISTEN)
if [ -n "$PORT_INFO" ]; then
    echo "✅ 端口 3000 正在监听"
    echo "$PORT_INFO" | while read line; do
        echo "   $line"
    done

    # 检查是否监听所有接口
    if echo "$PORT_INFO" | grep -q "\*:3000"; then
        echo "✅ 监听所有网络接口 (0.0.0.0:3000)"
    elif echo "$PORT_INFO" | grep -q "127.0.0.1:3000"; then
        echo "⚠️  仅监听本地接口 (127.0.0.1:3000)"
        echo "   局域网设备无法访问！"
        echo "   请使用: HOST=0.0.0.0 PORT=3000 npx vibe-kanban"
    fi
else
    echo "❌ 端口 3000 未监听"
    exit 1
fi
echo ""

# 4. 测试本地访问
echo "🔍 测试本地访问..."
if curl -s -o /dev/null -w "%{http_code}" http://localhost:3000 --connect-timeout 5 | grep -q "200"; then
    echo "✅ 本地访问成功 (http://localhost:3000)"
else
    echo "❌ 本地访问失败"
fi
echo ""

# 5. 测试局域网访问
echo "🔍 测试局域网访问..."
if [ -n "$LOCAL_IP" ]; then
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://${LOCAL_IP}:3000 --connect-timeout 5)
    if [ "$HTTP_CODE" = "200" ]; then
        echo "✅ 局域网访问成功 (http://${LOCAL_IP}:3000)"
        echo ""
        echo "📱 局域网内其他设备可通过以下地址访问："
        echo "   http://${LOCAL_IP}:3000"
    else
        echo "❌ 局域网访问失败 (HTTP ${HTTP_CODE})"
        echo "   可能原因："
        echo "   - 防火墙阻止了连接"
        echo "   - 网络配置问题"
    fi
else
    echo "⚠️  无法获取本机 IP，跳过局域网访问测试"
fi
echo ""

# 6. macOS 防火墙检查
echo "🔍 检查 macOS 防火墙状态..."
if /usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate | grep -q "enabled"; then
    echo "⚠️  macOS 防火墙已启用"
    echo "   如果遇到连接问题，请："
    echo "   1. 打开「系统设置」→「网络」→「防火墙」"
    echo "   2. 确保「允许传入连接」已启用"
    echo "   3. 或为 vibe-kanban 添加防火墙例外"
else
    echo "✅ macOS 防火墙未启用或已配置"
fi
echo ""

echo "======================================"
echo "检查完成"
echo "======================================"
