#!/bin/bash
# E2E Runner - 快速构建和运行脚本

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 配置
IMAGE_NAME="e2e-runner:latest"
DOCKER_DIR="$(cd "$(dirname "$0")" && pwd)"

echo -e "${GREEN}🚀 E2E Runner - Docker 构建脚本${NC}"
echo ""

# 1. 检查 Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker 未安装${NC}"
    exit 1
fi

# 2. 构建镜像
echo -e "${YELLOW}📦 构建 Docker 镜像...${NC}"
cd "$DOCKER_DIR"
docker build -t "$IMAGE_NAME" .

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ 镜像构建成功: $IMAGE_NAME${NC}"
else
    echo -e "${RED}❌ 镜像构建失败${NC}"
    exit 1
fi

# 3. 验证镜像
echo ""
echo -e "${YELLOW}🔍 验证镜像...${NC}"
docker run --rm "$IMAGE_NAME" node --version
docker run --rm "$IMAGE_NAME" npx playwright --version

echo ""
echo -e "${GREEN}✅ 所有检查通过！${NC}"
echo ""
echo "使用方法:"
echo "  docker run --rm \\"
echo "    -e BASE_URL=\"https://test.example.com\" \\"
echo "    -v \"\$PWD:/work\" -w /work \\"
echo "    $IMAGE_NAME \\"
echo "    npx playwright test"
echo ""
