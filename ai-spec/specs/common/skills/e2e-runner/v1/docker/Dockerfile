# E2E Runner - Playwright Docker Image
#
# 基于官方 Playwright 镜像，预装所有浏览器和依赖
# 生产就绪，优化性能和稳定性

FROM mcr.microsoft.com/playwright:v1.57.0-jammy

# 设置工作目录
WORKDIR /work

# 安装额外工具
RUN apt-get update && apt-get install -y \
    jq \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# 设置 npm 镜像（可选，加速安装）
# RUN npm config set registry https://registry.npmmirror.com

# 预装常用 npm 包（避免每次测试重新安装）
COPY package.json package-lock.json* ./
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi

# 设置环境变量
ENV CI=true
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
ENV NODE_ENV=test

# 健康检查
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD node --version || exit 1

# 默认命令（会被 orchestrator 覆盖）
CMD ["npx", "playwright", "test", "--reporter=html,json"]
