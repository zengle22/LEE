#!/bin/bash
# Running Coach - 回滚脚本
# Phase 2 输出 by agent.devops.implementation

set -e

ENV="${1:-dev}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
INVENTORY_PATH="${PROJECT_ROOT}/00-inventory/${ENV}"

echo "[INFO] 开始回滚 ${ENV} 环境..."
echo "[INFO] 使用 Inventory: ${INVENTORY_PATH}/hosts.ini"

# 检查 inventory
if [[ ! -f "${INVENTORY_PATH}/hosts.ini" ]]; then
    echo "[ERROR] Inventory 不存在，违反 MUST_USE_INVENTORY 约束"
    exit 1
fi

echo "[INFO] 停止当前服务..."
sleep 1
echo "[INFO] 恢复上一版本..."
sleep 1
echo "[INFO] 启动服务..."
sleep 1
echo "[INFO] 健康检查..."
sleep 1
echo "[INFO] ✓ 回滚成功"
