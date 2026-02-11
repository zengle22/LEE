#!/usr/bin/env bash
# DevOps Deploy Script
# Usage: deploy.sh --env <env> --version <version> [--compose-file <path>]
set -euo pipefail

ENV=""
VERSION=""
COMPOSE_FILE="docker-compose.yml"

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

LOG_DIR="deploy-logs/${ENV}"
mkdir -p "$LOG_DIR"
LOG_FILE="${LOG_DIR}/deploy-${VERSION}-$(date +%Y%m%d%H%M%S).log"

echo "Deploying version=${VERSION} to env=${ENV} ..." | tee "$LOG_FILE"

# Pull image
if ! docker compose -f "$COMPOSE_FILE" pull 2>&1 | tee -a "$LOG_FILE"; then
  echo '{"ok":false,"error":"docker pull failed","log":"'"$LOG_FILE"'"}' 
  exit 1
fi

# Deploy
export APP_VERSION="$VERSION"
export DEPLOY_ENV="$ENV"
if ! docker compose -f "$COMPOSE_FILE" up -d --remove-orphans 2>&1 | tee -a "$LOG_FILE"; then
  echo '{"ok":false,"error":"docker compose up failed","log":"'"$LOG_FILE"'"}'
  exit 1
fi

echo '{"ok":true,"env":"'"$ENV"'","version":"'"$VERSION"'","log":"'"$LOG_FILE"'"}'
exit 0
