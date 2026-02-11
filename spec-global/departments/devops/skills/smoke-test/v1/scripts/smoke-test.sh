#!/usr/bin/env bash
# DevOps Smoke Test Script
# Usage: smoke-test.sh --env <env> --endpoints <json_file>
set -euo pipefail

ENV=""
ENDPOINTS_FILE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --env)       ENV="$2"; shift 2 ;;
    --endpoints) ENDPOINTS_FILE="$2"; shift 2 ;;
    *) echo "Unknown option: $1" >&2; exit 2 ;;
  esac
done

[[ -z "$ENV" ]] && echo '{"ok":false,"error":"--env required"}' && exit 2

RESULT_DIR="smoke-test-results/${ENV}"
mkdir -p "$RESULT_DIR"
RESULT_FILE="${RESULT_DIR}/smoke-$(date +%Y%m%d%H%M%S).json"

TOTAL=0
PASSED=0
FAILED=0
RESULTS="[]"

# If endpoints file exists, read from it; otherwise use defaults
if [[ -n "$ENDPOINTS_FILE" && -f "$ENDPOINTS_FILE" ]]; then
  URLS=$(jq -r '.[]' "$ENDPOINTS_FILE" 2>/dev/null || echo "")
else
  echo '{"ok":false,"error":"--endpoints file required"}' && exit 2
fi

while IFS= read -r url; do
  [[ -z "$url" ]] && continue
  TOTAL=$((TOTAL + 1))
  
  HTTP_CODE=$(curl -sf -o /dev/null -w "%{http_code}" --connect-timeout 5 "$url" 2>/dev/null || echo "000")
  
  if [[ "$HTTP_CODE" =~ ^2[0-9]{2}$ ]]; then
    PASSED=$((PASSED + 1))
    STATUS="pass"
  else
    FAILED=$((FAILED + 1))
    STATUS="fail"
  fi
  
  RESULTS=$(echo "$RESULTS" | jq --arg url "$url" --arg status "$STATUS" --argjson code "$HTTP_CODE" \
    '. + [{"url": $url, "status": $status, "http_code": $code}]')
done <<< "$URLS"

ALL_OK=$( [[ $FAILED -eq 0 ]] && echo "true" || echo "false" )

REPORT=$(jq -n \
  --argjson ok "$ALL_OK" \
  --arg env "$ENV" \
  --argjson total "$TOTAL" \
  --argjson passed "$PASSED" \
  --argjson failed "$FAILED" \
  --argjson results "$RESULTS" \
  '{ok: $ok, env: $env, total: $total, passed: $passed, failed: $failed, results: $results}')

echo "$REPORT" | tee "$RESULT_FILE"
[[ "$ALL_OK" == "true" ]] && exit 0 || exit 1
