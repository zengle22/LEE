#!/usr/bin/env bash
# DevOps Deploy Test Environment Script
# Usage: deploy-test-env.sh --env <env> --version <version>
set -euo pipefail

ENV=""
VERSION=""
COMPOSE_FILE="docker-compose.test.yml"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --env)      ENV="$2"; shift 2 ;;
    --version)  VERSION="$2"; shift 2 ;;
    --compose-file) COMPOSE_FILE="$2"; shift 2 ;;
    *) echo "Unknown option: $1" >&2; exit 2 ;;
  esac
done

[[ -z "$ENV" ]] && echo '{"ok":false,"error":"--env required"}' && exit 2
[[ -z "$VERSION" ]] && echo '{"ok":false,"error":"--version required"}' && exit 2

# Reuse the deploy script with test-specific compose file
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEPLOY_SCRIPT="${SCRIPT_DIR}/../../deploy/v1/scripts/deploy.sh"

if [[ -f "$DEPLOY_SCRIPT" ]]; then
  exec bash "$DEPLOY_SCRIPT" --env "$ENV" --version "$VERSION" --compose-file "$COMPOSE_FILE"
else
  # Inline fallback
  export APP_VERSION="$VERSION"
  export DEPLOY_ENV="$ENV"

  echo "Deploying test env: version=${VERSION} env=${ENV} ..."

  if ! docker compose -f "$COMPOSE_FILE" up -d --remove-orphans 2>&1; then
    echo "{\"ok\":false,\"error\":\"test env deploy failed\"}"
    exit 1
  fi

  # 构建环境 URL，供 QA 工作流使用
  # 默认格式: {env}.test.local 或从环境变量读取
  BASE_URL="${BASE_URL:-${ENV}.test.local}"
  BASE_PORT="${BASE_PORT:-8080}"

  echo "{\"ok\":true,\"status\":\"deployed\",\"env\":\"${ENV}\",\"version\":\"${VERSION}\",\"type\":\"test\",\"url\":\"${BASE_URL}\",\"port\":${BASE_PORT}}"
  exit 0
fi
