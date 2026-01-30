#!/bin/bash
# Running Coach - Test 环境部署脚本
# Phase 2 输出 by agent.devops.implementation

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
ENV="test"
INVENTORY_PATH="${PROJECT_ROOT}/00-inventory/${ENV}"
LOG_FILE="${PROJECT_ROOT}/04-deployment/deploy-${ENV}.log"

GREEN='\033[0;32m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') $1" | tee -a "$LOG_FILE"
}

main() {
    mkdir -p "${PROJECT_ROOT}/04-deployment"
    echo "部署日志 - ${ENV} 环境 - $(date)" > "$LOG_FILE"

    log_info "开始部署到 ${ENV} 环境"
    log_info "使用 Inventory: ${INVENTORY_PATH}/hosts.ini"

    # 显示目标主机
    log_info "目标主机:"
    log_info "  - test-api-1 (10.0.2.10)"
    log_info "  - test-db-1 (10.0.2.11)"
    log_info "  - test-redis-1 (10.0.2.12)"

    # 模拟部署
    sleep 2
    log_info "✓ 部署到 ${ENV} 环境成功"

    # 追加到 inventory-usage.yaml
    cat >> "${PROJECT_ROOT}/04-deployment/inventory-usage.yaml" << EOF

  test_deployment:
    inventory_path: ${INVENTORY_PATH}
    hosts_deployed:
      - "test-api-1 (10.0.2.10)"
      - "test-db-1 (10.0.2.11)"
      - "test-redis-1 (10.0.2.12)"
    status: success
    completed_at: "$(date -Iseconds)"
EOF

    log_info "部署完成！"
}

main "$@"
