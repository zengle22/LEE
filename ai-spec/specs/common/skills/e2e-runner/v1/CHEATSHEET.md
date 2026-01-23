# E2E Runner - 快速参考卡

> 一页纸速查指南

---

## 🚀 快速开始（3 步）

```bash
# 1️⃣ 构建镜像
cd ai-spec/specs/common/skills/e2e-runner/v1/docker
./build.sh  # Windows: build.bat

# 2️⃣ 运行测试
docker run --rm \
  -e BASE_URL="https://your-app.com" \
  -v "$PWD:/work" -w /work \
  e2e-runner:latest \
  npx playwright test

# 3️⃣ 查看报告
npx playwright show-report output/playwright-report
```

---

## 📝 编写测试（模板）

```typescript
import { test, expect } from '@playwright/test';

test('测试名称', async ({ page }) => {
  // 1. 访问页面
  await page.goto('/path');

  // 2. 操作元素（✅ 使用 data-testid）
  await page.getByTestId('btn-id').click();
  await page.getByTestId('input-id').fill('text');

  // 3. 断言结果
  await expect(page).toHaveURL('/expected');
  await expect(page.getByTestId('element-id')).toBeVisible();
});
```

---

## 🎯 核心规则（必须遵守）

| 规则 | ✅ 正确 | ❌ 错误 |
|------|---------|---------|
| **选择器** | `getByTestId('btn-login')` | `.MuiButton-root` |
| **等待** | `expect(...).toBeVisible()` | `waitForTimeout(3000)` |
| **API** | `page.route('/api/**', ...)` | 依赖真实后端 |

---

## 🔍 调试失败（3 步）

```bash
# 1️⃣ 查看 Trace（最强）
npx playwright show-trace output/test-results/{test-name}/trace.zip

# 2️⃣ 查看截图
open output/test-results/{test-name}/test-failed-1.png

# 3️⃣ 查看录屏
open output/test-results/{test-name}/video.webm
```

---

## 📊 输出文件

```
output/
├── playwright-report/          # HTML 报告（人类）
├── e2e-report.json             # JSON 报告（机器）
└── test-results/               # 证据（截图/视频/trace）
    └── {test-name}-failed-1/
        ├── test-failed-1.png   # 截图
        ├── video.webm          # 录屏
        └── trace.zip           # Trace（调试神器）
```

---

## 🔧 常用命令

```bash
# 只运行 P0 测试
npx playwright test --grep "P0"

# 有头模式（调试）
docker run -e HEADED=true ... npx playwright test --headed

# 只运行失败的测试
npx playwright test --last-failed

# 查看 Trace
npx playwright show-trace path/to/trace.zip

# 查看报告
npx playwright show-report output/playwright-report
```

---

## 🚦 门禁标准

| 优先级 | 要求 | 失败处理 |
|--------|------|----------|
| **P0** | 100% | 立即 FAIL |
| **P1** | ≥ 90% | CONDITIONAL_PASS |
| **P2** | ≥ 80% | PASS（记录） |

---

## 📚 文档链接

| 文档 | 用途 |
|------|------|
| `README.md` | 完整使用指南 |
| `QUICKSTART.md` | 5 分钟快速开始 |
| `EXAMPLES.md` | 40+ 测试示例 |
| `pitfalls.md` | 7 个常见坑点 |
| `patterns.md` | 8 个复用模式 |
| `DEMO.md` | 7 个真实场景 |

---

## 💡 核心提醒

1. **选择器**: 必须用 `data-testid`
2. **等待**: 显式等待，不要 sleep
3. **Mock**: API 必须 Mock
4. **证据**: 失败必有 trace
5. **Trace**: 调试第一工具

---

## 🆘 遇到问题？

| 问题 | 解决方案 |
|------|----------|
| 测试随机失败 | 检查选择器、等待、Mock |
| 镜像构建失败 | 检查网络、Docker 版本 |
| 测试超时 | 增加 timeout 配置 |
| 找不到元素 | 查看 Trace，确认元素存在 |

---

## 📞 获取帮助

- Playwright 文档: https://playwright.dev
- 项目文档: `README.md`
- 示例代码: `examples/`

---

**快速参考卡 v1.0** | 2026-01-16
