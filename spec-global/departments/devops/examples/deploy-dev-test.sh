#!/bin/bash
#
# Dev/Test 环境部署脚本
#
# **重要**: 此脚本由 AI 生成，人类可以修改
# 使用前请确保环境配置文件已正确填写
#
# 使用方法：
#   ./deploy/deploy-dev-test.sh <environment>
#
# 参数：
#   <environment>: dev 或 test
#
# 示例：
#   ./deploy/deploy-dev-test.sh dev
#   ./deploy/deploy-dev-test.sh test

set -e  # 遇到错误立即退出
set -u  # 使用未定义的变量时报错
set -o pipefail  # 管道中任一命令失败则整个管道失败

# ============================================
# 配置
# ============================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV="${1:-dev}"

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
# 前置检查
# ============================================
check_prerequisites() {
    log_step "检查前置条件..."

    # 检查 Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装，请先安装 Docker"
        exit 1
    fi

    # 检查 Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose 未安装，请先安装 Docker Compose"
        exit 1
    fi

    # 检查环境参数
    if [[ "$ENV" != "dev" && "$ENV" != "test" ]]; then
        log_error "无效的环境参数: $ENV (必须是 dev 或 test)"
        exit 1
    fi

    # 检查环境配置文件
    ENV_CONFIG_FILE="$PROJECT_ROOT/env/env-config.$ENV.yaml"
    if [[ ! -f "$ENV_CONFIG_FILE" ]]; then
        log_error "环境配置文件不存在: $ENV_CONFIG_FILE"
        log_info "请先创建并填写环境配置文件"
        exit 1
    fi

    # 检查 docker-compose.yml
    DOCKER_COMPOSE_FILE="$PROJECT_ROOT/docker-compose.yml"
    if [[ ! -f "$DOCKER_COMPOSE_FILE" ]]; then
        log_error "Docker Compose 文件不存在: $DOCKER_COMPOSE_FILE"
        exit 1
    fi

    # 检查回滚脚本
    ROLLBACK_SCRIPT="$PROJECT_ROOT/deploy/rollback-$ENV.sh"
    if [[ ! -f "$ROLLBACK_SCRIPT" ]]; then
        log_warn "回滚脚本不存在: $ROLLBACK_SCRIPT"
        log_info "建议在部署前准备回滚脚本"
    fi

    log_info "前置检查通过"
}

# ============================================
# 备份当前部署
# ============================================
backup_current_deployment() {
    log_step "备份当前部署..."

    BACKUP_DIR="$PROJECT_ROOT/backup/$ENV/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$BACKUP_DIR"

    # 备份环境配置
    if [[ -f "$PROJECT_ROOT/env/.env.$ENV" ]]; then
        cp "$PROJECT_ROOT/env/.env.$ENV" "$BACKUP_DIR/.env.$ENV.bak"
        log_info "已备份环境配置到 $BACKUP_DIR"
    fi

    # 备份数据库（如果启用）
    # TODO: 实现数据库备份逻辑

    log_info "备份完成"
}

# ============================================
# 加载环境配置
# ============================================
load_environment_config() {
    log_step "加载环境配置..."

    # 从 YAML 配置文件导出环境变量
    # 注意：这里需要使用 yq 或类似工具解析 YAML
    # 为简化，这里假设已经生成了 .env 文件

    ENV_FILE="$PROJECT_ROOT/env/.env.$ENV"
    if [[ -f "$ENV_FILE" ]]; then
        set -a
        source "$ENV_FILE"
        set +a
        log_info "已加载环境配置: $ENV_FILE"
    else
        log_warn ".env 文件不存在: $ENV_FILE"
        log_info "将使用 docker-compose.yml 中的默认值"
    fi
}

# ============================================
# 验证配置
# ============================================
validate_configuration() {
    log_step "验证配置..."

    # 检查必需的环境变量
    REQUIRED_VARS=("APP_NAME" "DB_NAME" "DB_USER" "DB_PASSWORD")
    MISSING_VARS=()

    for var in "${REQUIRED_VARS[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            MISSING_VARS+=("$var")
        fi
    done

    if [[ ${#MISSING_VARS[@]} -gt 0 ]]; then
        log_error "缺少必需的环境变量: ${MISSING_VARS[*]}"
        exit 1
    fi

    # 验证 Docker 镜像
    if [[ -n "${DOCKER_REGISTRY:-}" && -n "${APP_NAME:-}" && -n "${APP_VERSION:-}" ]]; then
        FULL_IMAGE="${DOCKER_REGISTRY}/${APP_NAME}:${APP_VERSION}"
        log_info "将使用镜像: $FULL_IMAGE"

        # 检查镜像是否存在（可选）
        # docker pull "$FULL_IMAGE" || log_warn "无法拉取镜像 $FULL_IMAGE"
    fi

    log_info "配置验证通过"
}

# ============================================
# 停止现有服务
# ============================================
stop_existing_services() {
    log_step "停止现有服务..."

    cd "$PROJECT_ROOT"

    if docker-compose ps | grep -q "Up"; then
        log_info "正在停止现有服务..."
        docker-compose down
        log_info "现有服务已停止"
    else
        log_info "没有运行中的服务"
    fi
}

# ============================================
# 拉取最新镜像
# ============================================
pull_latest_images() {
    log_step "拉取最新镜像..."

    cd "$PROJECT_ROOT"

    # 如果配置了镜像仓库，则拉取镜像
    if [[ -n "${DOCKER_REGISTRY:-}" ]]; then
        docker-compose pull
        log_info "镜像拉取完成"
    else
        log_info "使用本地构建，跳过镜像拉取"
    fi
}

# ============================================
# 启动服务
# ============================================
start_services() {
    log_step "启动服务..."

    cd "$PROJECT_ROOT"

    # 启动服务
    docker-compose up -d

    log_info "服务启动中..."
}

# ============================================
# 等待服务健康
# ============================================
wait_for_services_healthy() {
    log_step "等待服务健康检查..."

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
        log_info "所有服务健康检查通过"
    else
        log_error "服务健康检查超时"
        docker-compose ps
        exit 1
    fi
}

# ============================================
# 运行数据库迁移
# ============================================
run_database_migrations() {
    log_step "运行数据库迁移..."

    # TODO: 实现数据库迁移逻辑
    # 示例：
    # docker-compose exec -T app python manage.py migrate

    log_info "数据库迁移完成（暂未实现）"
}

# ============================================
# 验证部署
# ============================================
verify_deployment() {
    log_step "验证部署..."

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

    # 检查日志
    log_info "最近的应用日志："
    docker-compose logs --tail=20 app
}

# ============================================
# 生成部署报告
# ============================================
generate_deployment_report() {
    log_step "生成部署报告..."

    local report_file="$PROJECT_ROOT/logs/deployment-${ENV}-$(date +%Y%m%d_%H%M%S).log"
    mkdir -p "$(dirname "$report_file")"

    {
        echo "=== 部署报告 ==="
        echo "环境: $ENV"
        echo "时间: $(date)"
        echo "版本: ${APP_VERSION:-unknown}"
        echo ""
        echo "=== 服务状态 ==="
        docker-compose ps
        echo ""
        echo "=== 镜像信息 ==="
        docker images | grep "$APP_NAME"
    } > "$report_file"

    log_info "部署报告已保存: $report_file"
}

# ============================================
# 回滚函数
# ============================================
rollback_deployment() {
    log_error "部署失败，准备回滚..."

    local rollback_script="$PROJECT_ROOT/deploy/rollback-$ENV.sh"

    if [[ -f "$rollback_script" ]]; then
        log_info "执行回滚脚本: $rollback_script"
        bash "$rollback_script"
    else
        log_error "回滚脚本不存在，请手动回滚"
        log_info "回滚步骤："
        log_info "1. docker-compose down"
        log_info "2. 恢复之前的配置"
        log_info "3. docker-compose up -d"
    fi

    exit 1
}

# ============================================
# 主流程
# ============================================
main() {
    log_info "开始部署到 $ENV 环境..."
    log_info "项目根目录: $PROJECT_ROOT"

    # 捕获错误并回滚
    trap 'rollback_deployment' ERR

    # 执行部署步骤
    check_prerequisites
    backup_current_deployment
    load_environment_config
    validate_configuration
    stop_existing_services
    pull_latest_images
    start_services
    wait_for_services_healthy
    run_database_migrations
    verify_deployment
    generate_deployment_report

    log_info "部署到 $ENV 环境成功！"
    log_info "访问地址: http://localhost:${APP_PORT:-8000}"

    # 取消错误捕获
    trap - ERR
}

# ============================================
# 脚本入口
# ============================================
# 显示帮助信息
if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    echo "Dev/Test 环境部署脚本"
    echo ""
    echo "使用方法："
    echo "  $0 <environment>"
    echo ""
    echo "参数："
    echo "  <environment>  dev 或 test"
    echo ""
    echo "示例："
    echo "  $0 dev"
    echo "  $0 test"
    echo ""
    exit 0
fi

# 执行主流程
main
