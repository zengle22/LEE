#!/usr/bin/env bash
# DevOps Validate Version Script
# Usage: validate-version.sh --version <version> [--registry <url>] [--image <name>]
set -euo pipefail

VERSION=""
REGISTRY=""
IMAGE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --version)  VERSION="$2"; shift 2 ;;
    --registry) REGISTRY="$2"; shift 2 ;;
    --image)    IMAGE="$2"; shift 2 ;;
    *) echo "Unknown option: $1" >&2; exit 2 ;;
  esac
done

[[ -z "$VERSION" ]] && echo '{"ok":false,"error":"--version required"}' && exit 2

# Validate version format (semver-like)
if ! echo "$VERSION" | grep -qE '^v?[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.]+)?$'; then
  echo "{\"ok\":false,\"error\":\"Invalid version format: ${VERSION}\",\"expected\":\"semver (e.g. v1.2.3)\"}"
  exit 1
fi

# Check if image exists in registry
if [[ -n "$IMAGE" ]]; then
  FULL_TAG="${REGISTRY:+${REGISTRY}/}${IMAGE}:${VERSION}"
  if docker manifest inspect "$FULL_TAG" &>/dev/null; then
    echo "{\"ok\":true,\"version\":\"${VERSION}\",\"image\":\"${FULL_TAG}\",\"exists\":true}"
    exit 0
  else
    echo "{\"ok\":false,\"version\":\"${VERSION}\",\"image\":\"${FULL_TAG}\",\"exists\":false,\"error\":\"Image not found\"}"
    exit 1
  fi
fi

echo "{\"ok\":true,\"version\":\"${VERSION}\",\"format_valid\":true}"
exit 0
