# Selector & Page Model Skill v1.0
# 选择器策略与页面对象模型技能

## 概述

定义稳定的选择器策略和 Page Object 模型，减少 E2E 测试的脆弱性。
这是 E2E 测试稳定性的关键，必须强制前端添加 `data-testid`。

## 技能标识

- **ID**: skill.test.selector_page_model
- **名称**: Selector & Page Model
- **版本**: 1.0
- **所有者**: test-governance

## 适用 Agent

- agent.test.e2e_test_executor

---

## 1. 选择器策略 (关键!)

### 1.1 选择器优先级

```yaml
selector_priority:
  # 第一优先: 测试专用属性 (最稳定)
  tier_1_best:
    - pattern: "[data-testid='{name}']"
      example: "[data-testid='login-button']"
      stability: "★★★★★"
      reason: "专为测试设计，不受样式/结构影响"

    - pattern: "[data-e2e='{name}']"
      example: "[data-e2e='submit-form']"
      stability: "★★★★★"
      reason: "同上"

  # 第二优先: 语义化属性
  tier_2_good:
    - pattern: "#{id}"
      example: "#unique-user-id"
      stability: "★★★★☆"
      reason: "唯一 ID，但可能动态生成"

    - pattern: "[aria-label='{label}']"
      example: "[aria-label='关闭对话框']"
      stability: "★★★★☆"
      reason: "无障碍属性，相对稳定"

    - pattern: "role[name='{name}']"
      example: "button[name='提交']"
      stability: "★★★☆☆"
      reason: "语义化，但受国际化影响"

  # 第三优先: 谨慎使用
  tier_3_caution:
    - pattern: ".{class}"
      example: ".submit-button"
      stability: "★★☆☆☆"
      reason: "样式类可能变化"
      when_to_use: "仅当无其他选择且类名稳定"

    - pattern: "text='{text}'"
      example: "text='登录'"
      stability: "★★☆☆☆"
      reason: "国际化会变"
      when_to_use: "静态文本且无其他选择"

  # 禁止使用
  tier_4_forbidden:
    - pattern: ".ant-btn-primary"
      reason: "UI 框架的动态类名"
      alternative: "添加 data-testid"

    - pattern: "div:nth-child(3) > span"
      reason: "结构极不稳定"
      alternative: "添加 data-testid"

    - pattern: ".css-1a2b3c"
      reason: "CSS-in-JS 生成的哈希类名"
      alternative: "添加 data-testid"

    - pattern: "xpath=//div[3]/button[2]"
      reason: "结构脆弱，难以维护"
      alternative: "添加 data-testid"
```

### 1.2 强制规范 (给前端团队)

```yaml
frontend_requirements:
  mandatory:
    - rule: "所有可交互元素必须有 data-testid"
      elements:
        - button
        - input
        - select
        - link (导航)
        - 列表项 (可点击的)
        - 模态框
        - 表单

    - rule: "data-testid 命名规范"
      format: "{module}-{component}-{action}"
      examples:
        - "auth-login-submit"
        - "order-list-item"
        - "payment-method-select"

    - rule: "列表项加 data-index"
      example: |
        <div data-testid="order-item" data-index="{{index}}">

  enforcement:
    - "代码审查必检"
    - "CI 检查 (eslint-plugin-testing-library)"
    - "新组件必须包含"

  eslint_config: |
    // .eslintrc.js
    module.exports = {
      plugins: ['testing-library'],
      rules: {
        'testing-library/prefer-screen-queries': 'warn',
        // 自定义规则: 交互元素必须有 data-testid
      }
    }
```

---

## 2. Page Object 模型

### 2.1 Page Object 结构

```yaml
page_object_structure:
  # 每个页面一个 Page Object
  directory: "e2e/pages/"

  template:
    file: "{PageName}Page.ts"
    structure:
      - selectors: "元素选择器集合"
      - actions: "页面操作方法"
      - assertions: "页面断言方法"
      - getters: "获取页面数据"

  example: |
    // e2e/pages/LoginPage.ts
    export class LoginPage {
      // Selectors (集中管理)
      readonly selectors = {
        emailInput: '[data-testid="auth-email-input"]',
        passwordInput: '[data-testid="auth-password-input"]',
        submitButton: '[data-testid="auth-login-submit"]',
        errorMessage: '[data-testid="auth-error-message"]',
        forgotPassword: '[data-testid="auth-forgot-password"]',
      };

      constructor(private page: Page) {}

      // Actions
      async navigate() {
        await this.page.goto('/login');
      }

      async login(email: string, password: string) {
        await this.page.fill(this.selectors.emailInput, email);
        await this.page.fill(this.selectors.passwordInput, password);
        await this.page.click(this.selectors.submitButton);
      }

      // Assertions
      async expectErrorMessage(message: string) {
        await expect(
          this.page.locator(this.selectors.errorMessage)
        ).toContainText(message);
      }

      async expectLoginSuccess() {
        await expect(this.page).toHaveURL(/.*dashboard.*/);
      }

      // Getters
      async getErrorText() {
        return this.page.textContent(this.selectors.errorMessage);
      }
    }
```

### 2.2 Page Object 组织

```yaml
page_object_organization:
  structure: |
    e2e/
    ├── pages/
    │   ├── auth/
    │   │   ├── LoginPage.ts
    │   │   ├── RegisterPage.ts
    │   │   └── ForgotPasswordPage.ts
    │   ├── dashboard/
    │   │   ├── DashboardPage.ts
    │   │   └── SettingsPage.ts
    │   ├── order/
    │   │   ├── OrderListPage.ts
    │   │   ├── OrderDetailPage.ts
    │   │   └── CheckoutPage.ts
    │   └── index.ts  # 导出所有 Page Objects
    │
    ├── components/
    │   ├── NavBar.ts
    │   ├── Modal.ts
    │   ├── Toast.ts
    │   └── DataTable.ts
    │
    ├── fixtures/
    │   ├── test-data.ts
    │   └── accounts.ts
    │
    └── tests/
        ├── auth.spec.ts
        └── order.spec.ts

  component_vs_page:
    component:
      - "可复用的 UI 组件"
      - "如: NavBar, Modal, Toast"
      - "在多个页面中使用"

    page:
      - "完整的页面"
      - "包含该页面特有的选择器和操作"
      - "可能组合多个 Component"
```

---

## 3. 选择器生成

### 3.1 自动生成工具

```yaml
selector_generator:
  # 从页面 DOM 自动提取 data-testid
  command: "npm run e2e:generate-selectors"

  output:
    file: "e2e/generated/selectors.ts"
    format: |
      export const selectors = {
        login: {
          emailInput: '[data-testid="auth-email-input"]',
          passwordInput: '[data-testid="auth-password-input"]',
          // ...
        },
        dashboard: {
          // ...
        }
      };

  missing_report:
    file: "e2e/generated/missing-testids.md"
    content: |
      ## 缺失 data-testid 的元素

      ### Login Page
      - button.submit (建议: data-testid="auth-login-submit")
      - input[type="email"] (建议: data-testid="auth-email-input")
```

### 3.2 选择器验证

```yaml
selector_validation:
  # CI 中运行
  command: "npm run e2e:validate-selectors"

  checks:
    - "所有选择器能找到元素"
    - "无重复的 data-testid"
    - "命名符合规范"

  on_failure:
    - "生成报告"
    - "标记为警告 (不阻塞)"
    - "通知前端修复"
```

---

## 4. 最佳实践

### 4.1 选择器维护

```yaml
maintenance:
  # 集中管理
  - "选择器只在 Page Object 中定义"
  - "测试用例通过 Page Object 调用"
  - "修改选择器只需改一处"

  # 版本控制
  - "选择器变更需要代码审查"
  - "重大变更需要通知测试团队"

  # 文档
  - "维护选择器-功能映射表"
  - "记录不稳定的选择器"
```

### 4.2 处理动态内容

```yaml
dynamic_content:
  # 列表项
  list_items:
    strategy: "data-testid + data-index"
    example: |
      // 点击第3个订单
      await page.click('[data-testid="order-item"][data-index="2"]');

      // 或使用 nth
      await page.click('[data-testid="order-item"] >> nth=2');

  # 动态 ID
  dynamic_id:
    strategy: "使用属性选择器前缀"
    example: |
      // ID 是 user-123 这样的动态值
      await page.click('[id^="user-"]');  // 以 user- 开头

  # 条件渲染
  conditional:
    strategy: "等待元素出现"
    example: |
      await page.waitForSelector('[data-testid="loading"]', { state: 'hidden' });
      await page.click('[data-testid="content"]');
```

---

## 5. 缺失 data-testid 的处理

```yaml
missing_testid_handling:
  # 短期: 使用替代方案
  short_term:
    - "使用 aria-label"
    - "使用唯一 ID"
    - "使用稳定的类名 (非框架生成)"
    - "在报告中标记"

  # 长期: 推动前端添加
  long_term:
    - "创建 Ticket 跟踪"
    - "在 Sprint 中安排"
    - "添加后更新 Page Object"

  # 报告模板
  report: |
    ## 选择器稳定性报告

    ### 需要添加 data-testid 的元素

    | 页面 | 元素 | 当前选择器 | 建议 data-testid |
    |------|------|-----------|-----------------|
    | Login | 提交按钮 | .ant-btn-primary | auth-login-submit |
    | Dashboard | 用户头像 | .avatar-img | dashboard-user-avatar |
```

---

## 版本历史

| 版本 | 日期 | 变更说明 |
|------|------|----------|
| 1.0 | 2026-01-13 | 初始版本 |
