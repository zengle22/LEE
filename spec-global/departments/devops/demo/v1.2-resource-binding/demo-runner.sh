#!/bin/bash
# DevOps Workflow v1.2 交互式演示脚本
# 演示 resource_binding 资源绑定机制

set -e

DEMO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# 打印函数
print_header() {
    echo ""
    echo -e "${BOLD}${BLUE}════════════════════════════════════════════════════════════════${NC}"
    echo -e "${BOLD}${BLUE}  $1${NC}"
    echo -e "${BOLD}${BLUE}════════════════════════════════════════════════════════════════${NC}"
    echo ""
}

print_phase() {
    echo -e "${BOLD}${CYAN}▶ Phase $1: $2${NC}"
}

print_info() {
    echo -e "${GREEN}  [INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}  [v1.2]${NC} $1"
}

print_gate() {
    echo -e "${YELLOW}  ⏸️  [HUMAN GATE]${NC} $1"
}

wait_key() {
    echo ""
    echo -e "${BOLD}按 Enter 继续...${NC}"
    read -r
}

# 演示开始
clear
print_header "DevOps Deployment Workflow v1.2 Demo"

echo -e "${BOLD}演示场景:${NC}"
echo "  项目: running-coach (AI跑步教练)"
echo "  目标: 部署到 dev + test 环境"
echo "  版本: 1.0.0"
echo ""
echo -e "${BOLD}v1.2 核心变化:${NC}"
echo -e "  ${YELLOW}• resource_binding - 显式声明 inventory 绑定${NC}"
echo -e "  ${YELLOW}• uses_inventory - 部署只能通过指定 inventory${NC}"
echo -e "  ${YELLOW}• NO_RESOURCE_PROVISIONING - 禁止创建云资源${NC}"
echo -e "  ${YELLOW}• MUST_USE_INVENTORY - 必须通过 inventory 引用服务器${NC}"

wait_key

# ============================================
# Phase 0: 展示 Inventory 结构
# ============================================
print_header "Phase 0: 资源绑定 (v1.2 新增)"

print_warn "v1.2 核心: 部署只能通过 inventory 触达机器"
echo ""

echo -e "${BOLD}resource-binding.yaml:${NC}"
echo "----------------------------------------"
head -30 "$DEMO_DIR/00-inventory/resource-binding.yaml"
echo "..."
echo "----------------------------------------"

echo ""
print_warn "Dev 环境 Inventory:"
echo "----------------------------------------"
cat "$DEMO_DIR/00-inventory/dev/hosts.ini"
echo "----------------------------------------"

wait_key

# ============================================
# Phase 1: 架构设计
# ============================================
print_header "Phase 1: 环境与发布架构设计"

print_phase "1" "架构设计"
print_info "Agent: agent.devops.architect"
print_info "输出: infra-architecture.yaml, env-matrix.yaml, release-strategy.md"
echo ""

echo -e "${BOLD}infra-architecture.yaml (摘要):${NC}"
echo "----------------------------------------"
head -40 "$DEMO_DIR/01-architecture/infra-architecture.yaml"
echo "..."
echo "----------------------------------------"

print_warn "注意 resource_management 部分: hardware_managed_by: human"

print_gate "等待 devops_lead + tech_lead 审批..."
sleep 1
print_info "✅ Human Gate 已通过"

wait_key

# ============================================
# Phase 2: 实施代码生成
# ============================================
print_header "Phase 2: 基础设施与 CI/CD 实现"

print_phase "2" "代码生成"
print_info "Agent: agent.devops.implementation"
print_info "输出: docker-compose.yml, deploy/*.sh, ansible/playbooks/"
echo ""

echo -e "${BOLD}deploy-dev.sh (关键部分):${NC}"
echo "----------------------------------------"
sed -n '1,20p' "$DEMO_DIR/02-implementation/deploy/deploy-dev.sh"
echo "..."
sed -n '45,60p' "$DEMO_DIR/02-implementation/deploy/deploy-dev.sh"
echo "..."
echo "----------------------------------------"

print_warn "注意: 脚本通过 INVENTORY_PATH 引用服务器，满足 MUST_USE_INVENTORY"

wait_key

# ============================================
# Phase 3: 配置注入
# ============================================
print_header "Phase 3: 人类注入环境配置与凭证"

print_phase "3" "配置注入"
print_gate "这是安全边界 - AI 不生成任何真实凭证"
echo ""

echo -e "${BOLD}env-config.dev.yaml:${NC}"
echo "----------------------------------------"
cat "$DEMO_DIR/03-env-config/env-config.dev.yaml"
echo "----------------------------------------"

print_gate "等待 devops_lead 审批..."
sleep 1
print_info "✅ Human Gate 已通过"

wait_key

# ============================================
# Phase 4: 部署
# ============================================
print_header "Phase 4: 部署到 dev/test"

print_phase "4" "部署 dev/test"
print_info "Runner: shell"
print_warn "uses_inventory: [dev, test]"
echo ""

print_info "执行: ./deploy/deploy-dev.sh"
echo ""

# 模拟部署输出
echo -e "${GREEN}[INFO]${NC} 开始部署到 dev 环境..."
echo -e "${GREEN}[INFO]${NC} 使用 Inventory: ./00-inventory/dev/hosts.ini"
sleep 0.5
echo -e "${GREEN}[INFO]${NC} 目标主机:"
echo "         - dev-api-1 (10.0.1.10)"
echo "         - dev-db-1 (10.0.1.11)"
echo "         - dev-redis-1 (10.0.1.12)"
sleep 0.5
echo -e "${GREEN}[INFO]${NC} 执行 Ansible Playbook..."
sleep 0.5
echo -e "${GREEN}[INFO]${NC}   → 连接到 dev-api-1..."
sleep 0.3
echo -e "${GREEN}[INFO]${NC}   → 启动服务..."
sleep 0.3
echo -e "${GREEN}[INFO]${NC}   → 健康检查通过"
sleep 0.3
echo -e "${GREEN}[INFO]${NC} ✅ 部署到 dev 环境成功"
echo ""
echo -e "${GREEN}[INFO]${NC} ✅ 部署到 test 环境成功"

print_warn "约束验证: NO_RESOURCE_PROVISIONING ✓, MUST_USE_INVENTORY ✓"

wait_key

# ============================================
# Phase 5: 验收
# ============================================
print_header "Phase 5: 环境与发布包验收"

print_phase "5" "环境验收"
print_info "Agent: agent.devops.verification"
echo ""

echo -e "${BOLD}deployment-checklist.md (摘要):${NC}"
echo "----------------------------------------"
head -35 "$DEMO_DIR/05-verification/deployment-checklist.md"
echo "..."
echo "----------------------------------------"

print_gate "等待 devops_lead + qa_lead 审批..."
sleep 1
print_info "✅ Human Gate 已通过"

wait_key

# ============================================
# Phase 6: 冻结
# ============================================
print_header "Phase 6: 版本冻结"

print_phase "6" "版本冻结"
print_info "Agent: agent.devops.verification"
print_gate "最终审批: devops_lead + tech_lead + product_owner"
echo ""

echo -e "${BOLD}audit-trail.yaml (v1.2 约束验证):${NC}"
echo "----------------------------------------"
sed -n '/constraints_verification/,/resource_management/p' "$DEMO_DIR/06-release-freeze/audit-trail.yaml"
echo "----------------------------------------"

print_gate "等待最终审批..."
sleep 1
print_info "✅ devops_lead 批准"
print_info "✅ tech_lead 批准"
print_info "✅ product_owner 批准"

echo ""
print_info "🎉 版本 1.0.0 冻结成功！"

# ============================================
# 总结
# ============================================
print_header "Demo 完成"

echo -e "${BOLD}执行摘要:${NC}"
echo "  Phase 1: 架构设计     ✅ (agent.devops.architect)"
echo "  Phase 2: 代码生成     ✅ (agent.devops.implementation)"
echo "  Phase 3: 配置注入     ✅ (Human)"
echo "  Phase 4: 部署 dev/test ✅ (Shell Runner)"
echo "  Phase 5: 环境验收     ✅ (agent.devops.verification)"
echo "  Phase 6: 版本冻结     ✅ (agent.devops.verification)"
echo ""
echo -e "${BOLD}v1.2 资源绑定验证:${NC}"
echo -e "  ${GREEN}✓${NC} NO_RESOURCE_PROVISIONING - 未创建云资源"
echo -e "  ${GREEN}✓${NC} MUST_USE_INVENTORY - 全部通过 inventory 部署"
echo -e "  ${GREEN}✓${NC} 硬件资源由人类管理"
echo ""
echo -e "${BOLD}产物目录:${NC}"
echo "  00-inventory/    - Inventory 和资源绑定"
echo "  01-architecture/ - 架构设计"
echo "  02-implementation/ - 实施代码"
echo "  03-env-config/   - 环境配置"
echo "  04-deployment/   - 部署日志"
echo "  05-verification/ - 验收报告"
echo "  06-release-freeze/ - 冻结报告"
echo ""
echo -e "${CYAN}Demo 结束。${NC}"
