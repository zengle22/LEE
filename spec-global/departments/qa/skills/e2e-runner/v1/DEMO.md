# E2E Runner - 使用演示

> 真实场景的完整使用流程

---

## 场景 1: 在本地开发中使用

### 目标

在本地运行 E2E 测试，验证新开发的登录功能。

### 前置条件

- ✅ Docker 已安装
- ✅ e2e-runner 镜像已构建
- ✅ 本地应用运行在 `http://localhost:3000`

### 步骤

#### 1. 准备项目结构

```bash
my-app/
├── src/                    # 应用代码
├── test-cases/
│   └── e2e/
│       └── login/
│           └── login.spec.ts
├── package.json
└── playwright.config.ts
```

#### 2. 编写测试用例

```typescript
// test-cases/e2e/login/login.spec.ts
import { test, expect } from '@playwright/test';

test.describe('登录功能', () => {
  test('正常登录应该成功', async ({ page }) => {
    await page.goto('/login');

    await page.getByTestId('input-username').fill('testuser');
    await page.getByTestId('input-password').fill('password123');
    await page.getByTestId('btn-login').click();

    await expect(page).toHaveURL('/dashboard');
  });
});
```

#### 3. 运行测试

```bash
docker run --rm \
  -e BASE_URL="http://host.docker.internal:3000" \
  -v "$PWD:/work" -w /work \
  e2e-runner:latest \
  npx playwright test test-cases/e2e/login
```

#### 4. 查看结果

```bash
# HTML 报告
npx playwright show-report output/playwright-report

# 失败时查看 trace
npx playwright show-trace output/test-results/login-正常登录-failed-1/trace.zip
```

---

## 场景 2: 在 CI/CD 中使用

### 目标

在 GitHub Actions 中自动运行 E2E 测试。

### GitHub Actions 配置

```yaml
# .github/workflows/e2e-tests.yml
name: E2E Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  e2e:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Build e2e-runner image
        run: |
          cd ai-spec/specs/common/skills/e2e-runner/v1/docker
          docker build -t e2e-runner:latest .

      - name: Start application
        run: |
          docker-compose up -d app
          # 等待应用启动
          sleep 10

      - name: Run E2E tests
        run: |
          docker run --rm \
            --network host \
            -e BASE_URL="http://localhost:3000" \
            -v "$PWD:/work" -w /work \
            e2e-runner:latest \
            npx playwright test test-cases/e2e/

      - name: Upload test report
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: playwright-report
          path: output/playwright-report
          retention-days: 30

      - name: Upload test evidence
        if: failure()
        uses: actions/upload-artifact@v3
        with:
          name: test-evidence
          path: output/test-results
          retention-days: 7

      - name: Comment PR with results
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v6
        with:
          script: |
            const fs = require('fs');
            const report = JSON.parse(fs.readFileSync('output/e2e-report.json', 'utf8'));

            const comment = `
            ## 🧪 E2E Test Results

            - **Total**: ${report.summary.total}
            - **Passed**: ✅ ${report.summary.passed}
            - **Failed**: ❌ ${report.summary.failed}
            - **Pass Rate**: ${report.summary.pass_rate.toFixed(2)}%

            ${report.summary.failed > 0 ? '⚠️ Some tests failed. Check the artifacts for details.' : '✅ All tests passed!'}
            `;

            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: comment
            });
```

---

## 场景 3: 在 Orchestrator 中使用

### 目标

通过 e2e-test-executor Agent 执行测试，作为 Testing Pipeline 的一部分。

### 步骤

#### 1. 准备测试套件

```bash
project/AI跑步教练/testing/
├── test-cases/
│   └── e2e/
│       └── chrome/
│           ├── login.spec.ts
│           ├── home.spec.ts
│           └── training.spec.ts
└── release-manifest.yaml
```

#### 2. 执行测试步骤

```bash
# 使用 orchestrator 执行 E2E 测试
python -m orchestrator start \
  ./project/AI跑步教练/testing \
  t4_1_e2e_chrome_execution \
  --agent e2e_test_executor
```

#### 3. Agent 自动完成

Agent 会自动：
1. 读取测试套件路径和 BASE_URL
2. 构建/拉取 e2e-runner 镜像
3. 在 Docker 中运行 Playwright 测试
4. 收集 HTML 报告、JSON 报告、证据
5. 分析结果并判定状态（PASS/CONDITIONAL_PASS/FAIL）
6. 输出符合契约的 JSON 结果

#### 4. 查看输出

```bash
# 检查输出文件
cat project/AI跑步教练/testing/output/e2e/chrome-report.json

# 查看 HTML 报告
npx playwright show-report project/AI跑步教练/testing/output/e2e/evidence/chrome/

# 查看失败的 trace
npx playwright show-trace project/AI跑步教练/testing/output/e2e/evidence/chrome/traces/{test}.zip
```

---

## 场景 4: 调试失败的测试

### 目标

调试一个随机失败的测试用例。

### 症状

```
❌ 测试失败: 登录 - 点击登录按钮
错误: Timeout 30000ms exceeded waiting for selector [data-testid="dashboard"]
```

### 调试步骤

#### 1. 查看 Trace

```bash
npx playwright show-trace output/test-results/login-点击登录按钮-failed-1/trace.zip
```

在 Trace 中查看：
- ✅ 点击了登录按钮
- ✅ 发送了 POST /api/login 请求
- ❌ 但返回了 500 错误
- ❌ 页面没有跳转到 dashboard

**发现**: API 返回 500 错误

#### 2. 查看截图

```bash
open output/test-results/login-点击登录按钮-failed-1/test-failed-1.png
```

截图显示：页面显示了 "Server Error" 提示

#### 3. 查看录屏

```bash
open output/test-results/login-点击登录按钮-failed-1/video.webm
```

录屏确认：用户点击登录后，看到错误提示

#### 4. 根因分析

- 问题不在测试代码
- 问题在后端 API（500 错误）
- 需要修复后端，而非修改测试

#### 5. 修复验证

```bash
# 修复后端后，重新运行测试
docker run --rm \
  -e BASE_URL="http://localhost:3000" \
  -v "$PWD:/work" -w /work \
  e2e-runner:latest \
  npx playwright test --grep "登录 - 点击登录按钮"

# ✅ 测试通过
```

---

## 场景 5: 编写新测试（Page Object 模式）

### 目标

为新功能"训练计划"编写测试，使用 Page Object 模式。

### 步骤

#### 1. 创建 Page Object

```typescript
// test-cases/e2e/pages/TrainingPlanPage.ts
import { Page, expect } from '@playwright/test';

export class TrainingPlanPage {
  constructor(private page: Page) {}

  async goto() {
    await this.page.goto('/training-plan');
  }

  async createPlan(name: string, days: number) {
    await this.page.getByTestId('btn-create-plan').click();
    await this.page.getByTestId('input-plan-name').fill(name);
    await this.page.getByTestId('input-plan-days').fill(days.toString());
    await this.page.getByTestId('btn-save').click();
  }

  async expectPlanVisible(name: string) {
    const plan = this.page.getByTestId(`plan-card-${name}`);
    await expect(plan).toBeVisible();
    await expect(plan.getByTestId('plan-name')).toHaveText(name);
  }

  async deletePlan(name: string) {
    const plan = this.page.getByTestId(`plan-card-${name}`);
    await plan.getByTestId('btn-delete').click();
    await this.page.getByTestId('btn-confirm-delete').click();
  }

  async expectPlanNotVisible(name: string) {
    await expect(this.page.getByTestId(`plan-card-${name}`)).toBeHidden();
  }
}
```

#### 2. 编写测试

```typescript
// test-cases/e2e/training-plan.spec.ts
import { test } from '@playwright/test';
import { TrainingPlanPage } from './pages/TrainingPlanPage';

test.describe('训练计划管理', () => {
  let planPage: TrainingPlanPage;

  test.beforeEach(async ({ page }) => {
    planPage = new TrainingPlanPage(page);
    await planPage.goto();
  });

  test('创建新计划', async () => {
    await planPage.createPlan('5公里训练', 30);
    await planPage.expectPlanVisible('5公里训练');
  });

  test('删除计划', async () => {
    await planPage.createPlan('临时计划', 7);
    await planPage.deletePlan('临时计划');
    await planPage.expectPlanNotVisible('临时计划');
  });
});
```

#### 3. 运行测试

```bash
docker run --rm \
  -e BASE_URL="http://localhost:3000" \
  -v "$PWD:/work" -w /work \
  e2e-runner:latest \
  npx playwright test test-cases/e2e/training-plan.spec.ts
```

---

## 场景 6: API Mock 测试边界情况

### 目标

测试空数据、加载失败等边界情况。

### 测试代码

```typescript
// test-cases/e2e/edge-cases.spec.ts
import { test, expect } from '@playwright/test';

test.describe('边界情况', () => {
  test('API 返回空数据应该显示空状态', async ({ page }) => {
    // Mock API 返回空数组
    await page.route('/api/training-plans', route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ data: [] }),
      });
    });

    await page.goto('/training-plan');

    await expect(page.getByTestId('empty-state')).toBeVisible();
    await expect(page.getByTestId('empty-state')).toContainText('暂无训练计划');
  });

  test('API 返回 500 应该显示错误提示', async ({ page }) => {
    await page.route('/api/training-plans', route => {
      route.fulfill({
        status: 500,
        body: JSON.stringify({ error: 'Internal Server Error' }),
      });
    });

    await page.goto('/training-plan');

    await expect(page.getByTestId('error-state')).toBeVisible();
    await expect(page.getByTestId('btn-retry')).toBeVisible();
  });

  test('加载超时应该显示重试按钮', async ({ page }) => {
    await page.route('/api/training-plans', async route => {
      // 延迟 10 秒（超过默认超时）
      await new Promise(resolve => setTimeout(resolve, 10000));
      route.fulfill({ status: 200, body: '[]' });
    });

    await page.goto('/training-plan');

    await expect(page.getByTestId('timeout-error')).toBeVisible({ timeout: 15000 });
  });
});
```

---

## 场景 7: 可访问性测试

### 目标

确保应用符合 WCAG 2.1 AA 标准。

### 测试代码

```typescript
// test-cases/e2e/accessibility.spec.ts
import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test.describe('可访问性检查', () => {
  test('训练计划页应该通过 WCAG 2.1 AA', async ({ page }) => {
    await page.goto('/training-plan');

    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();

    expect(results.violations).toEqual([]);
  });

  test('键盘导航应该正常工作', async ({ page }) => {
    await page.goto('/training-plan');

    // Tab 到创建按钮
    await page.keyboard.press('Tab');
    await expect(page.getByTestId('btn-create-plan')).toBeFocused();

    // Enter 触发点击
    await page.keyboard.press('Enter');
    await expect(page.getByTestId('modal-create-plan')).toBeVisible();
  });

  test('所有图片应该有 alt 属性', async ({ page }) => {
    await page.goto('/training-plan');

    const images = await page.locator('img').all();
    for (const img of images) {
      const alt = await img.getAttribute('alt');
      expect(alt).not.toBeNull();
      expect(alt).not.toBe('');
    }
  });
});
```

---

## 📊 总结

| 场景 | 难度 | 用时 | 说明 |
|------|------|------|------|
| 本地开发 | ⭐ | 5分钟 | 最简单，适合日常开发 |
| CI/CD 集成 | ⭐⭐ | 30分钟 | 一次配置，长期受益 |
| Orchestrator | ⭐⭐⭐ | 10分钟 | 需要理解 Agent 工作流 |
| 调试失败 | ⭐⭐ | 15分钟 | 使用 Trace 快速定位 |
| Page Object | ⭐⭐⭐ | 1小时 | 提高测试可维护性 |
| API Mock | ⭐⭐ | 20分钟 | 测试边界情况 |
| 可访问性 | ⭐⭐ | 15分钟 | 确保无障碍访问 |

---

✅ 所有场景演示完成，开箱即用！
