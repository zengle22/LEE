# E2E Runner Skill

> E2E UI 测试执行技能 - 使用 Docker + Playwright 实现真正的端到端 UI 自动化测试

## 概述

这个 Skill 提供生产就绪的 E2E UI 测试能力，基于：

- **Playwright** - 现代化浏览器自动化框架
- **Docker** - 容器化执行环境，确保一致性
- **Headless Browser** - 无头 Chromium/Firefox/WebKit
- **Rich Evidence** - 截图、视频、trace、日志

**核心特性**:
- ✅ 在 CI 里跑"点按钮、输入文字"的真实 UI 测试
- ✅ 失败时自动保存截图、录屏、交互轨迹（trace.zip）
- ✅ 支持多浏览器（Chrome/Firefox/Safari）
- ✅ 并行执行，快速反馈
- ✅ 可访问性测试（WCAG 2.1 AA）

---

## 快速开始

### 1. 构建 Docker 镜像

```bash
# 进入镜像目录
cd ai-spec/specs/common/skills/e2e-runner/v1/docker

# 构建镜像
docker build -t e2e-runner:latest .
```

### 2. 运行测试

```bash
# 基础用法
docker run --rm \
  -e BASE_URL="https://test.example.com" \
  -v "$PWD:/work" -w /work \
  e2e-runner:latest \
  npx playwright test

# 查看报告
npx playwright show-report output/playwright-report
```

### 3. 在 Orchestrator 中使用

```bash
# 执行 E2E 测试步骤
python -m orchestrator start ./project/测试项目/testing t4_1_e2e_chrome_execution --agent e2e_test_executor
```

---

## 输入参数

```yaml
test_suite_path: "test-cases/e2e/chrome/"  # 测试套件路径（必需）
base_url: "https://test.example.com"       # 被测应用 URL（必需）
browser: "chromium"                        # 浏览器类型（可选，默认 chromium）
workers: 4                                 # 并行数（可选，默认 4）
retries: 2                                 # 重试次数（可选，默认 2）
timeout: 30000                             # 超时（毫秒，可选，默认 30000）
headed: false                              # 是否有头模式（可选，默认 false）
env_vars:                                  # 额外环境变量（可选）
  AUTH_TOKEN: "test_token_123"
```

---

## 输出结构

### JSON 报告（机器可读）

```json
{
  "status": "PASS",
  "exit_code": 0,
  "report_path": "output/playwright-report/index.html",
  "json_report_path": "output/e2e-report.json",
  "evidence_dir": "output/test-results",
  "summary": {
    "total": 12,
    "passed": 11,
    "failed": 1,
    "skipped": 0,
    "flaky": 1,
    "duration_ms": 45230,
    "pass_rate": 91.67
  },
  "failed_tests": [
    {
      "test_id": "login.spec.ts:15",
      "title": "登录 - 错误密码应该显示提示",
      "error": "Timeout 30000ms exceeded waiting for selector...",
      "screenshot": "output/test-results/login-错误密码-failed.png",
      "video": "output/test-results/login-错误密码-video.webm",
      "trace": "output/test-results/login-错误密码-trace.zip"
    }
  ]
}
```

### HTML 报告（人类可读）

在 `output/playwright-report/index.html`，包含：
- 每个用例的执行状态
- 失败截图预览
- 交互式 trace 查看器
- 执行时长统计

### 证据目录结构

```
output/
├── playwright-report/          # HTML 报告（人类可读）
│   ├── index.html
│   └── data/
├── e2e-report.json             # JSON 报告（机器可读）
├── junit-report.xml            # JUnit 格式（CI 集成）
└── test-results/               # 证据目录
    ├── login-正常登录-chromium/
    │   ├── video.webm          # 录屏
    │   └── trace.zip           # trace（最强调试工具）
    └── login-错误密码-failed-1/
        ├── test-failed-1.png   # 失败截图
        ├── video.webm
        └── trace.zip
```

---

## 测试用例示例

### 基础登录测试

```typescript
// tests/login.spec.ts
import { test, expect } from '@playwright/test';

test('正常登录应该跳转到首页', async ({ page }) => {
  // 访问登录页
  await page.goto('/login');

  // 输入用户名和密码
  await page.getByTestId('input-username').fill('test_user');
  await page.getByTestId('input-password').fill('Test@1234');

  // 点击登录
  await page.getByTestId('btn-login').click();

  // 断言：应该跳转到首页
  await expect(page).toHaveURL('/home');
  await expect(page.getByTestId('user-display-name')).toHaveText('test_user');
});
```

### 空数据测试（Mock API）

```typescript
test('空数据应该显示空状态', async ({ page }) => {
  // Mock API 返回空数据
  await page.route('/api/trainings', route => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ data: [] }),
    });
  });

  await page.goto('/home');

  // 断言：应该显示空状态
  await expect(page.getByTestId('empty-state')).toBeVisible();
  await expect(page.getByTestId('empty-state')).toContainText('暂无训练计划');
});
```

### 可访问性测试

```typescript
import AxeBuilder from '@axe-core/playwright';

test('首页应该通过 WCAG 2.1 AA 检查', async ({ page }) => {
  await page.goto('/home');

  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
    .analyze();

  expect(results.violations).toEqual([]);
});
```

---

## 稳定性最佳实践

### ✅ DO: 使用 data-testid

```typescript
// 强烈推荐：稳定、语义化
await page.getByTestId('btn-login').click();
```

### ❌ DON'T: 使用脆弱的选择器

```typescript
// 不推荐：易被 UI 微调打破
await page.click('.MuiButton-root.css-xyz');
await page.locator('div > div > button:nth-child(3)').click();
```

### ✅ DO: 显式等待

```typescript
// 等待元素可见
await expect(page.getByTestId('loading-spinner')).toBeVisible();
await expect(page.getByTestId('loading-spinner')).toBeHidden();
```

### ❌ DON'T: 固定延迟

```typescript
// 不推荐：不稳定且慢
await page.waitForTimeout(3000);
```

---

## 调试技巧

### 1. 查看失败截图

失败截图会自动保存在 `output/test-results/`，文件名包含测试标题。

### 2. 查看录屏

```bash
# 直接打开 .webm 文件
open output/test-results/login-错误密码-failed-1/video.webm
```

### 3. 查看 Trace（最强）

```bash
# 交互式回放每一步操作
npx playwright show-trace output/test-results/login-错误密码-failed-1/trace.zip
```

**Trace 能看到**:
- 每一步点击/输入/等待
- 每次网络请求（包括 payload）
- 控制台日志
- DOM 快照
- 时间线（哪一步慢了）

### 4. 本地调试模式

```bash
# 有头模式 + 慢速执行
docker run --rm \
  -e BASE_URL="https://test.example.com" \
  -e HEADED=true \
  -v "$PWD:/work" -w /work \
  e2e-runner:latest \
  npx playwright test --headed --slow-mo=500
```

---

## 门禁标准

在 Testing Pipeline 中，E2E 测试有严格门禁：

| 优先级 | 通过率要求 | 失败处理 |
|--------|-----------|---------|
| **P0** | 100% | 立即 FAIL，阻止发布 |
| **P1** | ≥ 90% | CONDITIONAL_PASS，需人工审批 |
| **P2** | ≥ 80% | PASS，记录风险 |

---

## CI 集成

### GitHub Actions 示例

```yaml
name: E2E Tests
on: [push, pull_request]

jobs:
  e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Build E2E Runner
        run: docker build -t e2e-runner:latest ai-spec/specs/common/skills/e2e-runner/v1/docker

      - name: Run E2E Tests
        run: |
          docker run --rm \
            -e BASE_URL="${{ secrets.TEST_URL }}" \
            -v "$PWD:/work" -w /work \
            e2e-runner:latest \
            npx playwright test

      - name: Upload Report
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: playwright-report
          path: output/playwright-report

      - name: Upload Evidence
        if: failure()
        uses: actions/upload-artifact@v3
        with:
          name: test-evidence
          path: output/test-results
```

---

## 微信小程序测试（可选）

微信小程序的 UI 自动化不走纯容器，需要：

1. 固定 runner 机器（Windows/Mac）
2. 安装微信开发者工具
3. 使用微信自动化 SDK（miniprogram-automator）

但"脚本驱动 UI → 输出报告/截图"的模式是一样的。

---

## 相关资源

- Skill 规范: `ai-spec/specs/common/skills/e2e-runner/v1/skill.yaml`
- Agent 规范: `ai-spec/specs/common/agents/e2e-test-executor/v1/agent.yaml`
- Docker 镜像: `ai-spec/specs/common/skills/e2e-runner/v1/docker/`
- 示例测试: `ai-spec/specs/common/skills/e2e-runner/v1/examples/`
- Playwright 文档: https://playwright.dev

---

## 核心提醒

1. **选择器稳定性第一** - 必须使用 data-testid
2. **失败证据完整** - 截图、视频、trace 三件套
3. **显式等待优于延迟** - 用 waitForSelector 不用 sleep
4. **P0 零容忍** - P0 失败 = 阻止发布
5. **Trace 是调试神器** - 失败时第一时间看 trace
