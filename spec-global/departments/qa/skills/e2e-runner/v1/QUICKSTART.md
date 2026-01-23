# E2E Runner - 快速开始指南

> 5 分钟上手 E2E UI 自动化测试

---

## 第一步：构建 Docker 镜像

### Windows 用户

```cmd
cd ai-spec\specs\common\skills\e2e-runner\v1\docker
build.bat
```

### Linux/Mac 用户

```bash
cd ai-spec/specs/common/skills/e2e-runner/v1/docker
chmod +x build.sh
./build.sh
```

**预期输出**:
```
✅ 镜像构建成功: e2e-runner:latest
✅ Node.js: v18.x.x
✅ Playwright: v1.41.0
```

---

## 第二步：复制示例测试

```bash
# 复制示例到你的项目
cp -r ai-spec/specs/common/skills/e2e-runner/v1/examples/smoke-test \
     ./your-project/test-cases/e2e/
```

示例测试包含：
- `login.spec.ts` - 登录流程测试
- `home.spec.ts` - 首页功能测试
- `accessibility.spec.ts` - 可访问性测试

---

## 第三步：运行测试

### 基础运行

```bash
docker run --rm \
  -e BASE_URL="https://test.example.com" \
  -v "$PWD:/work" -w /work \
  e2e-runner:latest \
  npx playwright test
```

### 只运行 P0 用例

```bash
docker run --rm \
  -e BASE_URL="https://test.example.com" \
  -v "$PWD:/work" -w /work \
  e2e-runner:latest \
  npx playwright test --grep "P0"
```

### 有头模式（调试用）

```bash
docker run --rm \
  -e BASE_URL="http://localhost:3000" \
  -e HEADED=true \
  -v "$PWD:/work" -w /work \
  e2e-runner:latest \
  npx playwright test --headed
```

---

## 第四步：查看报告

### HTML 报告（人类可读）

```bash
npx playwright show-report output/playwright-report
```

浏览器会打开交互式报告，包含：
- ✅ 每个用例的执行状态
- 📸 失败截图
- 🎥 失败录屏
- 🔍 trace 查看器

### JSON 报告（机器可读）

```bash
cat output/e2e-report.json | jq '.'
```

---

## 第五步：调试失败用例

### 查看 Trace（最强工具）

```bash
# 找到失败的 trace 文件
npx playwright show-trace output/test-results/{test-name}-failed-1/trace.zip
```

**Trace 能看到**:
- 每一步点击/输入/导航
- 每次网络请求（包括 payload）
- 控制台日志
- DOM 快照
- 时间线

### 查看截图

```bash
# 失败截图在 test-results 目录
open output/test-results/{test-name}-failed-1/test-failed-1.png
```

### 查看录屏

```bash
# 录屏文件（webm 格式）
open output/test-results/{test-name}-failed-1/video.webm
```

---

## 编写测试用例

### 最小示例

```typescript
// tests/example.spec.ts
import { test, expect } from '@playwright/test';

test('示例测试', async ({ page }) => {
  // 1. 访问页面
  await page.goto('/');

  // 2. 操作元素（使用 data-testid）
  await page.getByTestId('btn-login').click();

  // 3. 断言结果
  await expect(page).toHaveURL('/home');
  await expect(page.getByTestId('welcome-message')).toBeVisible();
});
```

### 核心规则

1. **使用 data-testid**（不要用 CSS 选择器）
   ```typescript
   ✅ await page.getByTestId('btn-login').click();
   ❌ await page.click('.MuiButton-root');
   ```

2. **显式等待**（不要用固定延迟）
   ```typescript
   ✅ await expect(page.getByTestId('loading')).toBeHidden();
   ❌ await page.waitForTimeout(3000);
   ```

3. **Mock API**（不要依赖真实后端）
   ```typescript
   await page.route('/api/**', route => {
     route.fulfill({ status: 200, body: JSON.stringify({ data: [] }) });
   });
   ```

---

## 在 CI 中运行

### GitHub Actions

```yaml
name: E2E Tests
on: [push, pull_request]

jobs:
  e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Build E2E Runner
        run: |
          cd ai-spec/specs/common/skills/e2e-runner/v1/docker
          docker build -t e2e-runner:latest .

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

## 常见问题

### Q: 测试随机失败怎么办？

**A**: 检查以下问题：
1. 是否使用了 `data-testid`（不要用脆弱的 CSS 选择器）
2. 是否使用了显式等待（不要用 `waitForTimeout`）
3. 是否 Mock 了 API（不要依赖真实后端）
4. 查看 `knowledge/pitfalls.md` 了解常见坑点

### Q: 如何提高测试速度？

**A**: 几个技巧：
1. 增加并行数：`workers: 8`
2. 只运行 P0 用例：`--grep "P0"`
3. 使用 Fixture 复用登录状态
4. Mock API 而非真实请求

### Q: 如何调试失败的测试？

**A**: 三步走：
1. 查看 **trace.zip**（最强工具）
2. 查看失败截图
3. 查看录屏

### Q: 微信小程序怎么测？

**A**: 微信小程序不走纯容器，需要：
1. 固定 runner 机器（Windows/Mac）
2. 安装微信开发者工具
3. 使用 miniprogram-automator SDK

但"脚本驱动 UI → 输出报告/截图"的模式是一样的。

---

## 下一步

- 📖 阅读完整文档：`README.md`
- 🔍 了解常见坑点：`knowledge/pitfalls.md`
- 🎨 学习复用模式：`knowledge/patterns.md`
- 📝 查看测试契约：`../../contracts/e2e-test-input/v1/input.schema.json`
- 🤖 使用 Agent：`../../agents/e2e-test-executor/v1/agent.yaml`

---

## 获得帮助

- Playwright 官方文档: https://playwright.dev
- 示例测试: `examples/smoke-test/`
- 技术支持: testing-team@your-company.com
