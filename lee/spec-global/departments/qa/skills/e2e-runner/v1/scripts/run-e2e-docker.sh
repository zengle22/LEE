#!/bin/bash
# run-e2e-docker.sh - E2E Test Runner Script v1.0
#
# Exit codes:
#   0 - Success
#   1 - Test failures
#   2 - Infrastructure error

set -euo pipefail

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Default values
BASE_URL="${BASE_URL:-http://localhost:3000}"
HEADLESS="${HEADLESS:-true}"
TIMEOUT="${TIMEOUT:-30000}"
WORK_DIR="${WORK_DIR:-/tmp/e2e-work}"
DOCKER_IMAGE="${DOCKER_IMAGE:-lee-e2e-runner:latest}"

log_info "Starting E2E test execution..."
log_info "BASE_URL: $BASE_URL"
log_info "HEADLESS: $HEADLESS"
log_info "TIMEOUT: ${TIMEOUT}ms"
log_info "WORK_DIR: $WORK_DIR"

# Create work directory
mkdir -p "$WORK_DIR"

# Find test scripts
TEST_SCRIPTS=()
if [ -d "$WORK_DIR/scripts" ]; then
    while IFS= read -r -d '' script; do
        TEST_SCRIPTS+=("$script")
    done < <(find "$WORK_DIR/scripts" -name "test_*.py" -print0)
fi

if [ ${#TEST_SCRIPTS[@]} -eq 0 ]; then
    log_error "No test scripts found in $WORK_DIR/scripts"
    exit 2
fi

log_info "Found ${#TEST_SCRIPTS[@]} test script(s)"

# Create output directory
OUTPUT_DIR="$WORK_DIR/output"
mkdir -p "$OUTPUT_DIR"

# Run tests with pytest
log_info "Running tests..."

# Set up pytest command
PYTEST_ARGS=(
    -v
    --tb=short
    --timeout="${TIMEOUT}"
    -o "base_url=$BASE_URL"
    -o "headless=$HEADLESS"
)

# Run pytest
if pytest "${PYTEST_ARGS[@]}" "${TEST_SCRIPTS[@]}" \
    --json-report \
    --json-report-file="$OUTPUT_DIR/e2e-report.json" \
    > "$OUTPUT_DIR/pytest.log" 2>&1; then
    EXIT_CODE=$?
else
    EXIT_CODE=$?
fi

# Check exit code
if [ $EXIT_CODE -eq 0 ]; then
    log_info "All tests passed!"
elif [ $EXIT_CODE -eq 1 ]; then
    log_warn "Some tests failed"
else
    log_error "Test execution failed with exit code $EXIT_CODE"
    cat "$OUTPUT_DIR/pytest.log"
    exit 2
fi

# Generate summary
if [ -f "$OUTPUT_DIR/e2e-report.json" ]; then
    log_info "Test report: $OUTPUT_DIR/e2e-report.json"

    # Extract summary if jq is available
    if command -v jq &> /dev/null; then
        TOTAL=$(jq '.summary.total // 0' "$OUTPUT_DIR/e2e-report.json")
        PASSED=$(jq '.summary.passed // 0' "$OUTPUT_DIR/e2e-report.json")
        FAILED=$(jq '.summary.failed // 0' "$OUTPUT_DIR/e2e-report.json")
        log_info "Summary: $TOTAL total, $PASSED passed, $FAILED failed"
    fi
fi

exit $EXIT_CODE
