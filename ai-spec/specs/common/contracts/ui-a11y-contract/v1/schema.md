# UI A11y Rules Contract v1.0

可访问性规则契约 - 定义 UI 可访问性门禁标准。

## 核心理念

**可访问性是质量门禁的重要组成部分**：
- 基于 WCAG 2.1 标准
- 自动化测试 + 人工审核
- 门禁化强制执行

## WCAG 四大原则

| 原则 | 英文 | 说明 |
|------|------|------|
| 可感知 | Perceivable | 信息必须能被用户感知 |
| 可操作 | Operable | UI 组件必须可操作 |
| 可理解 | Understandable | 信息和操作必须可理解 |
| 健壮性 | Robust | 内容必须能被各种用户代理解析 |

## 完整示例

```yaml
# spec/ui/a11y/a11y.rules.yaml
$schema: ui-a11y-contract/v1
version: "1.0.0"
level: AA  # WCAG 合规级别

rules:
  # ========== 可感知 ==========
  - id: image-alt
    name: 图片替代文本
    wcag: "1.1.1"
    category: perceivable
    severity: critical
    description: 所有非装饰性图片必须有 alt 属性
    check: image-alt  # axe-core 规则 ID
    scope: [page, component]

  - id: color-contrast
    name: 颜色对比度
    wcag: "1.4.3"
    category: perceivable
    severity: serious
    description: 文本与背景的对比度至少 4.5:1
    check: color-contrast
    scope: [page, component]

  - id: color-contrast-large
    name: 大文本对比度
    wcag: "1.4.3"
    category: perceivable
    severity: serious
    description: 大文本（18pt+）对比度至少 3:1
    check: color-contrast-enhanced
    scope: [page, component]

  # ========== 可操作 ==========
  - id: keyboard-access
    name: 键盘可访问
    wcag: "2.1.1"
    category: operable
    severity: critical
    description: 所有功能必须可通过键盘操作
    check: keyboard
    scope: [page, component]

  - id: focus-visible
    name: 焦点可见
    wcag: "2.4.7"
    category: operable
    severity: serious
    description: 键盘焦点必须可见
    check: focus-visible
    scope: [page, component]

  - id: focus-order
    name: 焦点顺序
    wcag: "2.4.3"
    category: operable
    severity: serious
    description: 焦点顺序必须有逻辑
    check: focus-order-semantics
    scope: [page]

  - id: skip-link
    name: 跳过链接
    wcag: "2.4.1"
    category: operable
    severity: moderate
    description: 提供跳过重复内容的机制
    check: skip-link
    scope: [page]

  # ========== 可理解 ==========
  - id: label-content
    name: 表单标签
    wcag: "3.3.2"
    category: understandable
    severity: critical
    description: 表单控件必须有关联标签
    check: label
    scope: [component]

  - id: error-identification
    name: 错误识别
    wcag: "3.3.1"
    category: understandable
    severity: serious
    description: 错误必须被识别并文本描述
    check: aria-input-field-name
    scope: [page, component]

  - id: language
    name: 页面语言
    wcag: "3.1.1"
    category: understandable
    severity: moderate
    description: 页面必须指定语言
    check: html-has-lang
    scope: [page]

  # ========== 健壮性 ==========
  - id: valid-aria
    name: 有效的 ARIA
    wcag: "4.1.2"
    category: robust
    severity: critical
    description: ARIA 属性必须有效
    check: aria-valid-attr
    scope: [page, component]

  - id: unique-id
    name: 唯一 ID
    wcag: "4.1.1"
    category: robust
    severity: serious
    description: ID 必须唯一
    check: duplicate-id
    scope: [page]

  - id: button-name
    name: 按钮名称
    wcag: "4.1.2"
    category: robust
    severity: critical
    description: 按钮必须有可访问名称
    check: button-name
    scope: [component]

exceptions:
  - ruleId: skip-link
    target: page.login
    reason: 单页登录无需跳过链接
    approvedBy: a11y-team
    expiry: "2026-06-30"

  - ruleId: color-contrast
    target: component.decorative_badge
    reason: 装饰性元素，非关键信息
    approvedBy: a11y-team

testing:
  engine: axe-core
  runOn: [build, pr]
  threshold:
    critical: 0      # 不允许 critical 级别问题
    serious: 3       # 允许最多 3 个 serious
    moderate: 10     # 允许最多 10 个 moderate
```

## 规则严重程度

| 级别 | 英文 | 说明 | 门禁策略 |
|------|------|------|----------|
| 致命 | critical | 导致用户完全无法使用 | 阻断构建 |
| 严重 | serious | 严重影响用户体验 | 警告，限制数量 |
| 中等 | moderate | 可能造成困扰 | 警告 |
| 轻微 | minor | 最佳实践建议 | 仅提示 |

## 与测试集成

### 自动化测试配置

```javascript
// playwright.config.js
import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test('home page a11y', async ({ page }) => {
  await page.goto('/');

  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa'])
    .analyze();

  expect(results.violations).toEqual([]);
});
```

### CI 配置

```yaml
# .github/workflows/a11y.yml
- name: A11y Audit
  run: |
    npx axe-core --tags wcag2aa --exit

- name: Check A11y Threshold
  run: |
    npx a11y-gate-check \
      --rules=spec/ui/a11y/a11y.rules.yaml \
      --results=a11y-results.json
```

## 门禁规则

### UI Gate
- [ ] `testing.threshold.critical = 0`（不允许致命问题）

### Dev Gate
- [ ] 所有组件通过 a11y 单测
- [ ] `testing.threshold.serious` 内的问题

### Release Gate
- [ ] 所有页面通过 a11y 端到端测试
- [ ] 无未处理的 critical/serious 问题
- [ ] exceptions 中的豁免未过期
