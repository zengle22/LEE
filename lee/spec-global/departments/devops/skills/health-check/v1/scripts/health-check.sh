#!/usr/bin/env bash
# DevOps Health Check Script
# Usage: health-check.sh --env <env> --url <health_url> [--retries <n>] [--interval <sec>]
set -euo pipefail

ENV=""
URL=""
RETRIES=5
INTERVAL=3

while [[ $# -gt 0 ]]; do
  case "$1" in
    --env)      ENV="$2"; shift 2 ;;
    --url)      URL="$2"; shift 2 ;;
    --retries)  RETRIES="$2"; shift 2 ;;
    --interval) INTERVAL="$2"; shift 2 ;;
    *) echo "Unknown option: $1" >&2; exit 2 ;;
  esac
done

[[ -z "$ENV" ]] && echo '{"ok":false,"error":"--env required"}' && exit 2
[[ -z "$URL" ]] && echo '{"ok":false,"error":"--url required"}' && exit 2

RESULT_DIR="health-check-results/${ENV}"
mkdir -p "$RESULT_DIR"
RESULT_FILE="${RESULT_DIR}/health-$(date +%Y%m%d%H%M%S).json"

for i in $(seq 1 "$RETRIES"); do
  HTTP_CODE=$(curl -sf -o /dev/null -w "%{http_code}" --connect-timeout 5 "$URL" 2>/dev/null || echo "000")
  if [[ "$HTTP_CODE" =~ ^2[0-9]{2}$ ]]; then
    # 输出兼容 QA 工作流的格式: status 字段为 "healthy" 或 "unhealthy"
    RESULT="{\"ok\":true,\"status\":\"healthy\",\"env\":\"$ENV\",\"url\":\"$URL\",\"http_code\":$HTTP_CODE,\"attempt\":$i,\"result_path\":\"$RESULT_FILE\"}"
    echo "$RESULT" | tee "$RESULT_FILE"
    exit 0
  fi
  echo "Attempt $i/$RETRIES: HTTP $HTTP_CODE, retrying in ${INTERVAL}s..." >&2
  sleep "$INTERVAL"
done

RESULT="{\"ok\":false,\"status\":\"unhealthy\",\"env\":\"$ENV\",\"url\":\"$URL\",\"http_code\":$HTTP_CODE,\"attempts\":$RETRIES,\"result_path\":\"$RESULT_FILE\"}"
echo "$RESULT" | tee "$RESULT_FILE"
exit 1
