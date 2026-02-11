#!/usr/bin/env bash
# DevOps Check Environment Script
# Usage: check-env.sh --env <env> [--require-docker] [--require-port <port>]
set -euo pipefail

ENV=""
REQUIRE_DOCKER=false
REQUIRE_PORT=""
CHECKS=()
ALL_OK=true

while [[ $# -gt 0 ]]; do
  case "$1" in
    --env)            ENV="$2"; shift 2 ;;
    --require-docker) REQUIRE_DOCKER=true; shift ;;
    --require-port)   REQUIRE_PORT="$2"; shift 2 ;;
    *) echo "Unknown option: $1" >&2; exit 2 ;;
  esac
done

[[ -z "$ENV" ]] && echo '{"ok":false,"error":"--env required"}' && exit 2

add_check() {
  local name="$1" ok="$2" detail="$3"
  CHECKS+=("{\"name\":\"$name\",\"ok\":$ok,\"detail\":\"$detail\"}")
  [[ "$ok" == "false" ]] && ALL_OK=false
}

# Docker check
if [[ "$REQUIRE_DOCKER" == "true" ]]; then
  if command -v docker &>/dev/null && docker info &>/dev/null; then
    add_check "docker" "true" "Docker is running"
  else
    add_check "docker" "false" "Docker not available"
  fi
fi

# Port check
if [[ -n "$REQUIRE_PORT" ]]; then
  if curl -sf --connect-timeout 3 "http://localhost:${REQUIRE_PORT}/" &>/dev/null; then
    add_check "port_${REQUIRE_PORT}" "true" "Port ${REQUIRE_PORT} is reachable"
  else
    add_check "port_${REQUIRE_PORT}" "false" "Port ${REQUIRE_PORT} not reachable"
  fi
fi

# Env-specific config check
CONFIG_FILE="deploy-configs/${ENV}.env"
if [[ -f "$CONFIG_FILE" ]]; then
  add_check "config" "true" "${CONFIG_FILE} exists"
else
  add_check "config" "false" "${CONFIG_FILE} not found"
fi

# Build JSON output
CHECKS_JSON=$(printf ",%s" "${CHECKS[@]}")
CHECKS_JSON="[${CHECKS_JSON:1}]"
echo "{\"ok\":${ALL_OK},\"env\":\"${ENV}\",\"checks\":${CHECKS_JSON}}"

[[ "$ALL_OK" == "true" ]] && exit 0 || exit 1
