#!/bin/bash
# E2E Docker Runner - Wrapper Script for Claude Code
# 这个脚本将 Docker 命令的输出保存到文件，解决 Bash tool 输出捕获问题

set -e

# 配置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORK_DIR="${WORK_DIR:-$(pwd)}"
OUTPUT_DIR="${WORK_DIR}/output"
LOG_FILE="${OUTPUT_DIR}/docker-execution.log"
TEST_RESULT_FILE="${OUTPUT_DIR}/test-result.txt"
DOCKER_IMAGE="e2e-runner:latest"
TEST_SPEC="${TEST_SPEC:-e2e/quick-test.spec.ts}"

# 环境变量
BASE_URL="${BASE_URL:-http://localhost:3002}"
API_URL="${API_URL:-http://localhost:8081/v1}"

# 创建输出目录
mkdir -p "${OUTPUT_DIR}"

# 日志函数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "${LOG_FILE}"
}

# 开始执行
log "=========================================="
log "  E2E Docker Runner"
log "=========================================="
log ""
log "配置:"
log "  工作目录: ${WORK_DIR}"
log "  测试用例: ${TEST_SPEC}"
log "  Base URL: ${BASE_URL}"
log "  API URL: ${API_URL}"
log "  Docker 镜像: ${DOCKER_IMAGE}"
log ""

# 检查 Docker 镜像
log "检查 Docker 镜像..."
if ! docker images | grep -q "${DOCKER_IMAGE}"; then
    log "❌ Docker 镜像不存在: ${DOCKER_IMAGE}"
    echo "ERROR: Docker image not found" > "${TEST_RESULT_FILE}"
    exit 1
fi
log "✅ Docker 镜像存在"

# 检查测试文件
log "检查测试文件..."
if [ ! -f "${WORK_DIR}/${TEST_SPEC}" ]; then
    log "❌ 测试文件不存在: ${WORK_DIR}/${TEST_SPEC}"
    echo "ERROR: Test file not found" > "${TEST_RESULT_FILE}"
    exit 1
fi
log "✅ 测试文件存在"

# 执行测试
log ""
log "开始执行测试..."
log "=========================================="

# 运行 Docker 容器，将输出保存到文件
docker run --rm --network host \
    -e BASE_URL="${BASE_URL}" \
    -e API_URL="${API_URL}" \
    -v "${WORK_DIR}:/work" -w /work \
    "${DOCKER_IMAGE}" \
    npx playwright test "${TEST_SPEC}" --reporter=list \
    2>&1 | tee "${OUTPUT_DIR}/test-output.raw"

# 保存退出码
EXIT_CODE=${PIPESTATUS[0]}

log ""
log "=========================================="
log "测试执行完成"
log "退出码: ${EXIT_CODE}"
log "=========================================="

# 保存结果摘要
{
    echo "E2E_TEST_EXIT_CODE=${EXIT_CODE}"
    echo "E2E_TEST_TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "E2E_TEST_SPEC=${TEST_SPEC}"
    echo "E2E_BASE_URL=${BASE_URL}"
} > "${TEST_RESULT_FILE}"

# 判定结果
if [ ${EXIT_CODE} -eq 0 ]; then
    log "✅ 测试通过"
    echo "E2E_TEST_STATUS=PASS" >> "${TEST_RESULT_FILE}"
else
    log "⚠️ 测试失败或存在错误"
    echo "E2E_TEST_STATUS=FAIL" >> "${TEST_RESULT_FILE}"
fi

# 列出生成的文件
log ""
log "生成的文件:"
if [ -d "${OUTPUT_DIR}/test-results" ]; then
    ls -la "${OUTPUT_DIR}/test-results/" 2>/dev/null | tail -n +2 | while read -r line; do
        log "  ${line}"
    done
fi

if [ -f "${OUTPUT_DIR}/playwright-report/index.html" ]; then
    log "  HTML 报告: ${OUTPUT_DIR}/playwright-report/index.html"
fi

log ""
log "=========================================="
log "执行完成"
log "详细日志: ${LOG_FILE}"
log "原始输出: ${OUTPUT_DIR}/test-output.raw"
log "结果文件: ${TEST_RESULT_FILE}"
log "=========================================="

# 输出结果摘要（用于 Claude Code 捕获）
echo ""
echo "=== E2E TEST RESULT ==="
cat "${TEST_RESULT_FILE}"
echo "=== END RESULT ==="

exit ${EXIT_CODE}
