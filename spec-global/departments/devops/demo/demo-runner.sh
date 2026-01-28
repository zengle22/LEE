#!/bin/bash
#
# DevOps 主流程演示运行器
#
# 使用方法：
#   ./demo-runner.sh
#
# 说明：
#   这是一个交互式演示脚本，展示 DevOps L2 Workflow 的执行过程

set -u

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 当前阶段
CURRENT_PHASE=0

# ============================================
# 辅助函数
# ============================================

print_header() {
    clear
    echo -e "${CYAN}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC}        ${GREEN}DevOps 主流程演示${NC}                           ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}        ${YELLOW}Task Manager v1.0.0${NC}                         ${CYAN}║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

print_menu() {
    print_header
    echo -e "${BLUE}当前阶段:${NC} Phase ${CURRENT_PHASE}/6"
    echo ""
    echo -e "${GREEN}可用操作:${NC}"
    echo "  1. 查看 Phase 1: 架构设计"
    echo "  2. 查看 Phase 2: 实施代码生成"
    echo "  3. 查看 Phase 3: 配置注入"
    echo "  4. 查看 Phase 4: 部署到 dev/test"
    echo "  5. 查看 Phase 5: 环境验收"
    echo "  6. 查看 Phase 6: 版本冻结"
    echo "  7. 查看完整执行日志"
    echo "  8. 查看执行统计"
    echo "  9. 查看项目结构"
    echo "  0. 退出"
    echo ""
    echo -ne "${YELLOW}请选择 [0-9]:${NC} "
}

show_phase_1() {
    clear
    print_header
    echo -e "${MAGENTA}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${MAGENTA}Phase 1: p1_architecture (架构设计)${NC}"
    echo -e "${MAGENTA}═══════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${GREEN}执行者:${NC} agent.devops.architect"
    echo -e "${GREEN}执行时间:${NC} 2026-01-29 10:00:00 - 10:07:00 (7 分钟)"
    echo ""
    echo -e "${BLUE}───────────────────────────────────────────────────────────────${NC}"
    echo -e "${BLUE}输出文件${NC}"
    echo -e "${BLUE}───────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo "1. infra-architecture.yaml (8.2 KB)"
    echo "   - 基础设施架构设计"
    echo "   - 服务拓扑、网络、存储、监控架构"
    echo ""
    echo "2. env-matrix.yaml (6.8 KB)"
    echo "   - 环境配置矩阵"
    echo "   - Dev/Test 环境差异"
    echo ""
    echo "3. gate-approval.yaml (2.1 KB)"
    echo "   - Human Gate 审批记录"
    echo ""
    echo -e "${BLUE}───────────────────────────────────────────────────────────────${NC}"
    echo -e "${BLUE}架构概览${NC}"
    echo -e "${BLUE}───────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo "┌─────────────────────────────────────────────────────────────┐"
    echo "│                    nginx (反向代理)                          │"
    echo "│                         │                                   │"
    echo "│                         ↓                                   │"
    echo "│                    app (应用服务)                           │"
    echo "│                         │                                   │"
    echo "│              ┌────────────┴────────────┐                    │"
    echo "│              ↓                         ↓                    │"
    echo "│           db (PostgreSQL)        redis (缓存)              │"
    echo "└─────────────────────────────────────────────────────────────┘"
    echo ""
    echo -e "${BLUE}───────────────────────────────────────────────────────────────${NC}"
    echo -e "${BLUE}审批结果${NC}"
    echo -e "${BLUE}───────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "${GREEN}✓ devops_lead:${NC} 架构设计合理，环境隔离清晰"
    echo -e "${GREEN}✓ tech_lead:${NC} 技术选型符合项目需求"
    echo ""
    read -p "按 Enter 继续查看详细文件..."
}

show_phase_2() {
    clear
    print_header
    echo -e "${MAGENTA}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${MAGENTA}Phase 2: p2_infra_code (实施代码生成)${NC}"
    echo -e "${MAGENTA}═══════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${GREEN}执行者:${NC} agent.devops.implementation"
    echo -e "${GREEN}执行时间:${NC} 2026-01-29 10:07:00 - 10:20:00 (13 分钟)"
    echo ""
    echo -e "${BLUE}───────────────────────────────────────────────────────────────${NC}"
    echo -e "${BLUE}生成的代码${NC}"
    echo -e "${BLUE}───────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo "1. docker-compose.yml (180 行)"
    echo "   ✓ 4 个服务定义（app、db、redis、nginx）"
    echo "   ✓ 健康检查配置"
    echo "   ✓ 网络和卷定义"
    echo "   ✓ 环境变量占位符"
    echo ""
    echo "2. deploy-dev-test.sh (220 行)"
    echo "   ✓ 完整的部署脚本"
    echo "   ✓ 前置检查（7 项）"
    echo "   ✓ 备份和恢复逻辑"
    echo "   ✓ 健康检查和验证"
    echo ""
    echo "3. rollback-dev-test.sh (150 行)"
    echo "   ✓ 回滚脚本"
    echo "   ✓ 状态记录和恢复"
    echo "   ✓ 验证和报告生成"
    echo ""
    echo "4. github-actions.yaml (350 行)"
    echo "   ✓ 11 个 CI/CD Jobs"
    echo "   ✓ 代码质量、测试、安全扫描"
    echo "   ✓ 多环境部署"
    echo "   ✓ 人工审批 Gate"
    echo ""
    echo -e "${BLUE}───────────────────────────────────────────────────────────────${NC}"
    echo -e "${BLUE}代码统计${NC}"
    echo -e "${BLUE}───────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo "类型        文件数    行数    说明"
    echo "────────────────────────────────────────"
    echo "YAML        2         530     Docker Compose + CI/CD"
    echo "Shell       2         370     部署 + 回滚脚本"
    echo "────────────────────────────────────────"
    echo "总计        4         900     实施代码"
    echo ""
    echo -e "${GREEN}✓ Phase 2 完成，无需 Human Gate${NC}"
    echo ""
    read -p "按 Enter 继续查看详细文件..."
}

show_phase_3() {
    clear
    print_header
    echo -e "${MAGENTA}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${MAGENTA}Phase 3: p3_env_config (配置注入) ⏸️${NC}"
    echo -e "${MAGENTA}═══════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${GREEN}执行者:${NC} Human (devops_lead)"
    echo -e "${GREEN}执行时间:${NC} 2026-01-29 10:20:00 - 10:45:00 (25 分钟)"
    echo ""
    echo -e "${YELLOW}⚠️  这是 Human Gate 阶段，必须由人类操作${NC}"
    echo ""
    echo -e "${BLUE}───────────────────────────────────────────────────────────────${NC}"
    echo -e "${BLUE}人类操作步骤${NC}"
    echo -e "${BLUE}───────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo "1. ✓ 检查环境配置模板"
    echo "2. ✓ 填写 dev 环境配置"
    echo "   - DB_NAME=task_manager_dev"
    echo "   - DB_USER=dev_user"
    echo "   - DB_PASSWORD=*** (敏感)"
    echo "   - REDIS_PASSWORD=*** (敏感)"
    echo "   - SECRET_KEY=*** (敏感)"
    echo ""
    echo "3. ✓ 填写 test 环境配置"
    echo "   - DB_NAME=task_manager_test"
    echo "   - DB_USER=test_user"
    echo "   - DB_PASSWORD=*** (敏感)"
    echo "   - REDIS_PASSWORD=*** (敏感)"
    echo "   - API_KEY=*** (敏感)"
    echo "   - SECRET_KEY=*** (敏感)"
    echo ""
    echo "4. ✓ 验证配置格式"
    echo "5. ✓ 提交审批"
    echo ""
    echo -e "${BLUE}───────────────────────────────────────────────────────────────${NC}"
    echo -e "${BLUE}配置示例${NC}"
    echo -e "${BLUE}───────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo "# dev 环境配置片段"
    echo "database_config:"
    echo "  db_name: \"task_manager_dev\""
    echo "  db_user: \"dev_user\""
    echo "  db_password: \"\${DB_PASSWORD}\"  # 人类填写真实值"
    echo ""
    echo -e "${BLUE}───────────────────────────────────────────────────────────────${NC}"
    echo -e "${BLUE}审批结果${NC}"
    echo -e "${BLUE}───────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "${GREEN}✓ devops_lead:${NC} 环境配置已验证，dev 和 test 配置正确"
    echo ""
    echo "检查项状态:"
    echo "  ✓ env_scope - 环境范围确认"
    echo "  ✓ credentials - 敏感凭证已填写"
    echo "  ✓ rollback - 回滚脚本已准备"
    echo ""
    read -p "按 Enter 继续查看详细文件..."
}

show_phase_4() {
    clear
    print_header
    echo -e "${MAGENTA}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${MAGENTA}Phase 4: p4_deploy_dev_test (部署到 dev/test)${NC}"
    echo -e "${MAGENTA}═══════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${GREEN}执行者:${NC} Shell Runner"
    echo -e "${GREEN}执行时间:${NC} 2026-01-29 10:45:00 - 11:00:00 (15 分钟)"
    echo ""
    echo -e "${BLUE}───────────────────────────────────────────────────────────────${NC}"
    echo -e "${BLUE}部署流程${NC}"
    echo -e "${BLUE}───────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo "Dev 环境部署 (5m 10s):"
    echo "  1. ✓ 检查前置条件"
    echo "  2. ✓ 备份当前部署"
    echo "  3. ✓ 加载环境配置"
    echo "  4. ✓ 停止现有服务"
    echo "  5. ✓ 启动新服务"
    echo "  6. ✓ 等待服务健康"
    echo "  7. ✓ 运行数据库迁移"
    echo "  8. ✓ 验证部署"
    echo ""
    echo "Test 环境部署 (9m 45s):"
    echo "  (类似流程...)"
    echo ""
    echo -e "${BLUE}───────────────────────────────────────────────────────────────${NC}"
    echo -e "${BLUE}部署结果${NC}"
    echo -e "${BLUE}───────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo "Dev 环境:"
    echo "  状态:  ✓ Success"
    echo "  时长:  5m 10s"
    echo "  服务:  4 个服务运行中"
    echo "    - app (task-manager:1.0.0)"
    echo "    - db (postgres:15-alpine)"
    echo "    - redis (redis:7-alpine)"
    echo "    - nginx (nginx:alpine)"
    echo "  健康:  ✓ 所有服务健康"
    echo ""
    echo "Test 环境:"
    echo "  状态:  ✓ Success"
    echo "  时长:  9m 45s"
    echo "  服务:  4 个服务运行中"
    echo "  健康:  ✓ 所有服务健康"
    echo ""
    echo -e "${GREEN}✓ Phase 4 完成，自动部署成功${NC}"
    echo ""
    read -p "按 Enter 继续查看详细文件..."
}

show_phase_5() {
    clear
    print_header
    echo -e "${MAGENTA}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${MAGENTA}Phase 5: p5_verification (环境验收) ⏸️${NC}"
    echo -e "${MAGENTA}═══════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${GREEN}执行者:${NC} agent.devops.verification"
    echo -e "${GREEN}执行时间:${NC} 2026-01-29 11:00:00 - 11:15:00 (15 分钟)"
    echo ""
    echo -e "${BLUE}───────────────────────────────────────────────────────────────${NC}"
    echo -e "${BLUE}验证检查结果${NC}"
    echo -e "${BLUE}───────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo "检查项              Dev        Test"
    echo "────────────────────────────────────────"
    echo "服务运行状态        ✓ 4/4      ✓ 4/4"
    echo "健康检查            ✓ 通过     ✓ 通过"
    echo "数据库连接          ✓ 正常     ✓ 正常"
    echo "API 响应            ✓ < 200ms  ✓ < 200ms"
    echo "日志收集            ✓ 正常     ✓ 正常"
    echo "配置正确性          ✓ 通过     ✓ 通过"
    echo "资源使用            ✓ 正常     ✓ 正常"
    echo "网络连通性          ✓ 正常     ✓ 正常"
    echo "────────────────────────────────────────"
    echo "总计: 15 项检查，15 项通过，0 项失败"
    echo ""
    echo -e "${BLUE}───────────────────────────────────────────────────────────────${NC}"
    echo -e "${BLUE}审批结果${NC}"
    echo -e "${BLUE}───────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "${GREEN}✓ devops_lead:${NC} Dev 环境验收通过，服务运行正常"
    echo -e "${GREEN}✓ qa_lead:${NC} Test 环境验收通过，可以进行自动化测试"
    echo ""
    read -p "按 Enter 继续查看详细文件..."
}

show_phase_6() {
    clear
    print_header
    echo -e "${MAGENTA}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${MAGENTA}Phase 6: p6_release_freeze (版本冻结) ⏸️${NC}"
    echo -e "${MAGENTA}═══════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${GREEN}执行者:${NC} agent.devops.verification"
    echo -e "${GREEN}执行时间:${NC} 2026-01-29 11:15:00 - 11:30:00 (15 分钟)"
    echo ""
    echo -e "${BLUE}───────────────────────────────────────────────────────────────${NC}"
    echo -e "${BLUE}冻结内容${NC}"
    echo -e "${BLUE}───────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo "Release Bundle 包含:"
    echo "  1. ✓ 架构设计文档"
    echo "  2. ✓ 环境配置矩阵"
    echo "  3. ✓ Docker Compose 配置"
    echo "  4. ✓ 部署脚本"
    echo "  5. ✓ 回滚脚本"
    echo "  6. ✓ CI/CD Pipeline"
    echo "  7. ✓ 环境配置（dev + test）"
    echo "  8. ✓ 部署验收清单"
    echo "  9. ✓ 发布清单"
    echo " 10. ✓ 冻结报告"
    echo "  11. ✓ 审计跟踪"
    echo ""
    echo "文件统计:"
    echo "  - 总文件数: 20"
    echo "  - 总大小: ~100 KB"
    echo "  - 总行数: ~1,670 行"
    echo ""
    echo -e "${BLUE}───────────────────────────────────────────────────────────────${NC}"
    echo -e "${BLUE}审批结果${NC}"
    echo -e "${BLUE}───────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "${GREEN}✓ devops_lead:${NC} 版本 1.0.0 冻结，部署验收通过"
    echo -e "${GREEN}✓ tech_lead:${NC} 技术实现符合规范，可以发布"
    echo -e "${GREEN}✓ product_owner:${NC} 功能完整，批准发布 v1.0.0"
    echo ""
    echo -e "${GREEN}✓✓✓ WORKFLOW COMPLETED ✓✓✓${NC}"
    echo ""
    echo -e "最终状态: ${GREEN}SUCCESS${NC}"
    echo -e "版本: ${GREEN}1.0.0${NC}"
    echo -e "总执行时间: ${GREEN}88 分钟${NC}"
    echo ""
    read -p "按 Enter 继续查看详细文件..."
}

show_execution_log() {
    clear
    print_header
    echo -e "${MAGENTA}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${MAGENTA}完整执行日志${NC}"
    echo -e "${MAGENTA}═══════════════════════════════════════════════════════════${NC}"
    echo ""

    if [ -f "execution-log.md" ]; then
        head -100 execution-log.md
        echo ""
        echo -e "${YELLOW}... (日志已截断，完整日志请查看 execution-log.md)${NC}"
    else
        echo -e "${RED}错误: 找不到 execution-log.md${NC}"
    fi
    echo ""
    read -p "按 Enter 返回主菜单..."
}

show_statistics() {
    clear
    print_header
    echo -e "${MAGENTA}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${MAGENTA}执行统计${NC}"
    echo -e "${MAGENTA}═══════════════════════════════════════════════════════════${NC}"
    echo ""

    echo -e "${BLUE}执行指标${NC}"
    echo "──────────────────────────────────────────"
    echo "总执行时间:        88 分钟"
    echo "Agent 执行时间:    48 分钟 (55%)"
    echo "Human Gate 时间:   40 分钟 (45%)"
    echo "Shell 执行时间:    15 分钟"
    echo ""

    echo -e "${BLUE}阶段时间分布${NC}"
    echo "──────────────────────────────────────────"
    echo "Phase 1 (Architecture)    7 min   (8%)"
    echo "Phase 2 (Implementation)  13 min  (15%)"
    echo "Phase 3 (Config)          25 min  (28%)"
    echo "Phase 4 (Deploy)          15 min  (17%)"
    echo "Phase 5 (Verification)    15 min  (17%)"
    echo "Phase 6 (Freeze)          15 min  (17%)"
    echo ""

    echo -e "${BLUE}输出统计${NC}"
    echo "──────────────────────────────────────────"
    echo "总文件数:           20"
    echo "总大小:             ~100 KB"
    echo "总行数:             ~1,670 行"
    echo ""

    echo -e "${BLUE}成功率${NC}"
    echo "──────────────────────────────────────────"
    echo "审批通过率:         100% (4/4)"
    echo "检查通过率:         100% (15/15)"
    echo "错误数:             0"
    echo "警告数:             0"
    echo ""

    read -p "按 Enter 返回主菜单..."
}

show_structure() {
    clear
    print_header
    echo -e "${MAGENTA}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${MAGENTA}项目结构${NC}"
    echo -e "${MAGENTA}═══════════════════════════════════════════════════════════${NC}"
    echo ""

    tree -L 3 2>/dev/null || find . -maxdepth 3 -print | sed -e 's;[^/]*/;|____;g'

    echo ""
    read -p "按 Enter 返回主菜单..."
}

# ============================================
# 主循环
# ============================================

main() {
    while true; do
        print_menu
        read -r choice

        case $choice in
            1)
                CURRENT_PHASE=1
                show_phase_1
                ;;
            2)
                CURRENT_PHASE=2
                show_phase_2
                ;;
            3)
                CURRENT_PHASE=3
                show_phase_3
                ;;
            4)
                CURRENT_PHASE=4
                show_phase_4
                ;;
            5)
                CURRENT_PHASE=5
                show_phase_5
                ;;
            6)
                CURRENT_PHASE=6
                show_phase_6
                ;;
            7)
                show_execution_log
                ;;
            8)
                show_statistics
                ;;
            9)
                show_structure
                ;;
            0)
                echo ""
                echo -e "${GREEN}感谢使用 DevOps 主流程演示！${NC}"
                echo ""
                exit 0
                ;;
            *)
                echo ""
                echo -e "${RED}无效选择，请重新输入${NC}"
                sleep 1
                ;;
        esac
    done
}

# 脚本入口
cd "$(dirname "$0")" || exit 1
main
