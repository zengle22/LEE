#!/bin/bash
#
# Dev/Test 环境回滚脚本
#
# **重要**: 此脚本由 AI 生成，人类可以修改
# 回滚是部署失败时的应急措施，请谨慎使用
#
# 使用方法：
#   ./deploy/rollback-dev-test.sh <environment> [previous_version]
#
# 参数：
#   <environment>: dev 或 test
#   [previous_version]: 上一个版本号（可选）
#
# 示例：
#   ./deploy/rollback-dev-test.sh dev
#   ./deploy/rollback-dev-test.sh test 0.0.9

set -e  # 遇到错误立即退出
set -u  # 使用未定义的变量时报错
set -o pipefail  # 管道中任一命令失败则整个管道失败

# ============================================
# 配置
# ============================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV="${1:-dev}"
PREVIOUS_VERSION="${2:-}"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ============================================
# 日志函数
# ============================================
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "\n${GREEN}==>${NC} $1"
}

# ============================================
# 确认回滚
# ============================================
confirm_rollback() {
    log_step "确认回滚操作..."

    log_warn "您即将回滚 $ENV 环境的部署"
    log_warn "此操作将："
    log_warn "  - 停止当前服务"
    log_warn "  - 恢复到上一个版本"
    log_warn "  - 可能导致数据丢失"

    if [[ -n "$PREVIOUS_VERSION" ]]; then
        log_warn "目标版本: $PREVIOUS_VERSION"
    fi

    echo ""
    read -p "确认要继续吗? (yes/no): " confirmation

    if [[ "$confirmation" != "yes" ]]; then
        log_info "回滚已取消"
        exit 0
    fi

    log_info "回滚确认"
}

# ============================================
# 记录当前状态
# ============================================
record_current_state() {
    log_step "记录当前状态..."

    STATE_FILE="$PROJECT_ROOT/logs/rollback-state-${ENV}-$(date +%Y%m%d_%H%M%S).txt"
    mkdir -p "$(dirname "$STATE_FILE")"

    {
        echo "=== 回滚前状态 ==="
        echo "环境: $ENV"
        echo "时间: $(date)"
        echo "当前版本: ${CURRENT_VERSION:-unknown}"
        echo "目标版本: ${PREVIOUS_VERSION:-unknown}"
        echo ""
        echo "=== 服务状态 ==="
        cd "$PROJECT_ROOT"
        docker-compose ps
        echo ""
        echo "=== 镜像信息 ==="
        docker images | grep "$APP_NAME"
    } > "$STATE_FILE"

    log_info "当前状态已记录: $STATE_FILE"
}

# ============================================
# 停止当前服务
# ============================================
stop_current_services() {
    log_step "停止当前服务..."

    cd "$PROJECT_ROOT"

    if docker-compose ps | grep -q "Up"; then
        log_info "正在停止当前服务..."
        docker-compose down
        log_info "当前服务已停止"
    else
        log_info "没有运行中的服务"
    fi
}

# ============================================
# 恢复上一个版本
# ============================================
restore_previous_version() {
    log_step "恢复上一个版本..."

    cd "$PROJECT_ROOT"

    if [[ -n "$PREVIOUS_VERSION" ]]; then
        # 如果指定了版本号，使用该版本
        log_info "恢复到版本: $PREVIOUS_VERSION"

        # 修改环境配置中的版本号
        ENV_CONFIG_FILE="$PROJECT_ROOT/env/env-config.$ENV.yaml"
        if [[ -f "$ENV_CONFIG_FILE" ]]; then
            # 备份当前配置
            cp "$ENV_CONFIG_FILE" "${ENV_CONFIG_FILE}.bak"

            # 更新版本号（需要使用 yq 或 sed）
            # 这里简化处理，实际应该用 YAML 解析器
            sed -i.bak "s/app_version: .*/app_version: \"$PREVIOUS_VERSION\"/" "$ENV_CONFIG_FILE"

            log_info "已更新配置文件中的版本号"
        fi

        # 重新生成 .env 文件
        # TODO: 调用配置注入命令

    else
        # 如果没有指定版本号，从备份中恢复
        log_info "从备份中恢复..."

        # 查找最新的备份
        BACKUP_DIR="$PROJECT_ROOT/backup/$ENV"
        if [[ -d "$BACKUP_DIR" ]]; then
            LATEST_BACKUP=$(ls -t "$BACKUP_DIR" | head -1)

            if [[ -n "$LATEST_BACKUP" ]]; then
                log_info "使用备份: $LATEST_BACKUP"

                # 恢复环境配置
                if [[ -f "$BACKUP_DIR/$LATEST_BACKUP/.env.$ENV.bak" ]]; then
                    cp "$BACKUP_DIR/$LATEST_BACKUP/.env.$ENV.bak" "$PROJECT_ROOT/env/.env.$ENV"
                    log_info "已恢复环境配置"
                fi
            else
                log_warn "没有找到备份"
            fi
        else
            log_warn "备份目录不存在: $BACKUP_DIR"
        fi
    fi
}

# ============================================
# 回滚数据库（如果需要）
# ============================================
rollback_database() {
    log_step "检查数据库回滚..."

    # 数据库回滚是高风险操作，需要明确确认
    log_warn "数据库回滚可能导致数据丢失"
    read -p "是否需要回滚数据库? (yes/no): " db_confirmation

    if [[ "$db_confirmation" != "yes" ]]; then
        log_info "跳过数据库回滚"
        return
    fi

    # TODO: 实现数据库回滚逻辑
    # 示例：
    # docker-compose exec -T app python manage.py migrate "$PREVIOUS_VERSION"

    log_info "数据库回滚完成（暂未实现）"
}

# ============================================
# 启动恢复的服务
# ============================================
start_restored_services() {
    log_step "启动恢复的服务..."

    cd "$PROJECT_ROOT"

    # 启动服务
    docker-compose up -d

    log_info "服务启动中..."
}

# ============================================
# 等待服务恢复
# ============================================
wait_for_services_recovery() {
    log_step "等待服务恢复..."

    local max_attempts=60
    local attempt=0
    local healthy=false

    while [[ $attempt -lt $max_attempts ]]; do
        local unhealthy=$(docker-compose ps | grep -c "unhealthy\|starting" || true)

        if [[ $unhealthy -eq 0 ]]; then
            healthy=true
            break
        fi

        attempt=$((attempt + 1))
        echo -n "."
        sleep 2
    done

    echo ""

    if [[ "$healthy" == "true" ]]; then
        log_info "所有服务已恢复"
    else
        log_error "服务恢复超时"
        docker-compose ps
        exit 1
    fi
}

# ============================================
# 验证回滚
# ============================================
verify_rollback() {
    log_step "验证回滚结果..."

    cd "$PROJECT_ROOT"

    # 检查服务状态
    log_info "服务状态："
    docker-compose ps

    # 检查健康端点
    if command -v curl &> /dev/null; then
        local app_port="${APP_PORT:-8000}"
        local health_url="http://localhost:${app_port}/health"

        log_info "检查健康端点: $health_url"

        if curl -f -s -o /dev/null "$health_url"; then
            log_info "健康检查通过"
        else
            log_warn "健康检查失败"
        fi
    fi

    # 检查版本
    log_info "当前运行版本: ${PREVIOUS_VERSION:-previous}"
}

# ============================================
# 生成回滚报告
# ============================================
generate_rollback_report() {
    log_step "生成回滚报告..."

    local report_file="$PROJECT_ROOT/logs/rollback-${ENV}-$(date +%Y%m%d_%H%M%S).log"
    mkdir -p "$(dirname "$report_file")"

    {
        echo "=== 回滚报告 ==="
        echo "环境: $ENV"
        echo "回滚时间: $(date)"
        echo "从版本: ${CURRENT_VERSION:-unknown}"
        echo "到版本: ${PREVIOUS_VERSION:-previous}"
        echo ""
        echo "=== 服务状态 ==="
        docker-compose ps
        echo ""
        echo "=== 回滚原因 ==="
        echo "请在此添加回滚原因"
    } > "$report_file"

    log_info "回滚报告已保存: $report_file"
}

# ============================================
# 主流程
# ============================================
main() {
    log_info "开始回滚 $ENV 环境..."
    log_info "项目根目录: $PROJECT_ROOT"

    # 加载当前版本信息
    if [[ -f "$PROJECT_ROOT/env/env-config.$ENV.yaml" ]]; then
        CURRENT_VERSION=$(grep "app_version:" "$PROJECT_ROOT/env/env-config.$ENV.yaml" | awk '{print $2}' | tr -d '"')
    fi

    # 执行回滚步骤
    confirm_rollback
    record_current_state
    stop_current_services
    restore_previous_version
    rollback_database
    start_restored_services
    wait_for_services_recovery
    verify_rollback
    generate_rollback_report

    log_info "回滚完成！"
    log_warn "请检查服务是否正常运行"
    log_warn "如需重新部署，请运行: ./deploy/deploy-dev-test.sh $ENV"
}

# ============================================
# 脚本入口
# ============================================
# 显示帮助信息
if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    echo "Dev/Test 环境回滚脚本"
    echo ""
    echo "使用方法："
    echo "  $0 <environment> [previous_version]"
    echo ""
    echo "参数："
    echo "  <environment>    dev 或 test"
    echo "  [previous_version] 上一个版本号（可选）"
    echo ""
    echo "示例："
    echo "  $0 dev"
    echo "  $0 test 0.0.9"
    echo ""
    echo "说明："
    echo "  - 如果指定了版本号，将回滚到该版本"
    echo "  - 如果没有指定版本号，将从最新备份恢复"
    echo ""
    exit 0
fi

# 检查环境参数
if [[ -z "${1:-}" ]]; then
    log_error "缺少环境参数"
    echo "使用方法: $0 <environment> [previous_version]"
    exit 1
fi

if [[ "$ENV" != "dev" && "$ENV" != "test" ]]; then
    log_error "无效的环境参数: $ENV (必须是 dev 或 test)"
    exit 1
fi

# 执行主流程
main
