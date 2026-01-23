# E2E Runner - 端到端 UI 测试技能

## 快速开始

### 1. 构建 Docker 镜像

```bash
cd docker/
docker build -t e2e-runner:latest .
```

### 2. 运行示例测试

```bash
# 复制示例测试到你的项目
cp -r examples/smoke-test ./your-project/test-cases/e2e/

# 运行测试
docker run --rm \
  -e BASE_URL="http://localhost:3000" \
  -v "$PWD:/work" -w /work \
  e2e-runner:latest \
  npx playwright test
```

### 3. 查看报告

```bash
# 打开 HTML 报告
npx playwright show-report output/playwright-report

# 查看失败的 trace
npx playwright show-trace output/test-results/{test-name}/trace.zip
```

## 目录结构

```
e2e-runner/
├── skill.yaml              # Skill 规范
├── docker/                 # Docker 镜像
│   ├── Dockerfile
│   ├── package.json
│   └── playwright.config.ts
├── examples/               # 示例测试
│   └── smoke-test/
│       ├── login.spec.ts
│       ├── home.spec.ts
│       └── accessibility.spec.ts
└── README.md              # 本文件
```

## 核心特性

- ✅ **生产就绪**: 基于官方 Playwright 镜像
- ✅ **多浏览器**: Chrome、Firefox、Safari
- ✅ **并行执行**: 最多 16 个 worker
- ✅ **失败重试**: 自动重试不稳定用例
- ✅ **丰富证据**: 截图、视频、trace
- ✅ **可访问性**: WCAG 2.1 AA 检查
- ✅ **CI 友好**: JSON/JUnit 报告

## 配置文件

### playwright.config.ts

核心配置项：

- `timeout`: 单个测试超时（默认 30s）
- `retries`: 重试次数（CI 中默认 2 次）
- `workers`: 并行数（CI 中默认 4）
- `reporter`: 报告格式（HTML + JSON + JUnit）

### 环境变量

- `BASE_URL`: 被测应用地址（必需）
- `CI`: 是否在 CI 环境（自动检测）
- `HEADED`: 是否有头模式（调试用）

## 最佳实践

### 1. 使用 data-testid

```typescript
// ✅ 稳定
await page.getByTestId('btn-login').click();

// ❌ 脆弱
await page.click('.MuiButton-root');
```

### 2. 显式等待

```typescript
// ✅ 正确
await expect(page.getByTestId('loading')).toBeVisible();
await expect(page.getByTestId('loading')).toBeHidden();

// ❌ 错误
await page.waitForTimeout(3000);
```

### 3. Mock API

```typescript
await page.route('/api/trainings', route => {
  route.fulfill({
    status: 200,
    body: JSON.stringify({ data: [] }),
  });
});
```

## 调试技巧

### 查看 Trace

Trace 是最强大的调试工具，包含：
- 每一步操作
- 网络请求
- 控制台日志
- DOM 快照

```bash
npx playwright show-trace output/test-results/{test-name}/trace.zip
```

### 本地调试模式

```bash
docker run --rm \
  -e BASE_URL="http://localhost:3000" \
  -e HEADED=true \
  -v "$PWD:/work" -w /work \
  e2e-runner:latest \
  npx playwright test --headed --debug
```

## 相关资源

- [Playwright 文档](https://playwright.dev)
- [Agent 规范](../../../agents/e2e-test-executor/v1/agent.yaml)
- [输入契约](../../../contracts/e2e-test-input/v1/input.schema.json)
- [输出契约](../../../contracts/e2e-test-result/v1/output.schema.json)
