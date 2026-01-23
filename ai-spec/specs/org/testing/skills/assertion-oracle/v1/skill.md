# Assertion & Oracle Skill v1.0
# 断言与验证技能

## 概述

定义 E2E 测试的断言策略，包括 UI 断言、行为断言、网络断言。
支持软断言以收集更多失败信息。

## 技能标识

- **ID**: skill.test.assertion_oracle
- **名称**: Assertion & Oracle
- **版本**: 1.0
- **所有者**: test-governance

## 适用 Agent

- agent.test.e2e_test_executor
- agent.test.smoke_test_executor
- agent.test.system_test_executor

---

## 1. 断言类型

### 1.1 UI 断言

```yaml
ui_assertions:
  # 可见性断言
  visibility:
    - assert_visible:
        selector: "[data-testid='welcome-message']"
        message: "欢迎消息应该可见"

    - assert_hidden:
        selector: "[data-testid='loading-spinner']"
        message: "加载指示器应该消失"

    - assert_attached:
        selector: "[data-testid='modal']"
        message: "模态框应该在 DOM 中"

    - assert_detached:
        selector: "[data-testid='old-component']"
        message: "旧组件应该被移除"

  # 文本断言
  text:
    - assert_text:
        selector: "[data-testid='user-name']"
        text: "张三"
        match: "exact"  # exact | contains | regex

    - assert_text_contains:
        selector: "[data-testid='message']"
        text: "操作成功"

    - assert_text_regex:
        selector: "[data-testid='order-id']"
        pattern: "^ORD-[0-9]{8}$"

  # 属性断言
  attribute:
    - assert_attribute:
        selector: "[data-testid='submit-btn']"
        attribute: "disabled"
        value: null  # 属性不存在

    - assert_class:
        selector: "[data-testid='status']"
        class: "active"
        has: true

    - assert_value:
        selector: "[data-testid='email-input']"
        value: "test@example.com"

  # 状态断言
  state:
    - assert_enabled:
        selector: "[data-testid='submit-btn']"

    - assert_disabled:
        selector: "[data-testid='submit-btn']"

    - assert_checked:
        selector: "[data-testid='agree-checkbox']"

    - assert_focused:
        selector: "[data-testid='search-input']"

  # 数量断言
  count:
    - assert_count:
        selector: "[data-testid='list-item']"
        count: 10

    - assert_count_gte:
        selector: "[data-testid='search-result']"
        min: 1
        message: "应至少有1条搜索结果"
```

### 1.2 行为断言

```yaml
behavior_assertions:
  # URL 断言
  url:
    - assert_url:
        url: "/dashboard"
        match: "path"

    - assert_url_contains:
        contains: "success=true"

    - assert_url_regex:
        pattern: "/order/[0-9]+/detail"

  # 页面标题断言
  title:
    - assert_title:
        title: "Dashboard - MyApp"

    - assert_title_contains:
        contains: "Dashboard"

  # Cookie 断言
  cookie:
    - assert_cookie_exists:
        name: "session_token"

    - assert_cookie_value:
        name: "user_role"
        value: "admin"

  # LocalStorage 断言
  storage:
    - assert_local_storage:
        key: "auth_token"
        exists: true

    - assert_local_storage_value:
        key: "user_preference"
        value: { "theme": "dark" }

  # 下载断言
  download:
    - assert_download:
        trigger: "[data-testid='export-btn']"
        filename_pattern: "report_*.xlsx"
        timeout: 10000
```

### 1.3 网络断言

```yaml
network_assertions:
  # 请求断言
  request:
    - assert_request_made:
        url_pattern: "**/api/users"
        method: "POST"
        timeout: 5000

    - assert_request_body:
        url_pattern: "**/api/login"
        body:
          email: "test@example.com"

    - assert_request_headers:
        url_pattern: "**/api/**"
        headers:
          Authorization: "Bearer *"

  # 响应断言
  response:
    - assert_response_status:
        url_pattern: "**/api/users"
        status: 200

    - assert_response_body:
        url_pattern: "**/api/user/profile"
        body:
          id: "*"  # 任意值
          name: "张三"

    - assert_response_json_schema:
        url_pattern: "**/api/orders"
        schema: "schemas/orders-response.json"

  # 错误断言
  error:
    - assert_no_console_errors:
        ignore_patterns:
          - "favicon.ico"
          - "analytics"

    - assert_no_network_errors:
        ignore_patterns:
          - "**/analytics/**"
```

---

## 2. 软断言 (Soft Assertions)

### 2.1 概念

```yaml
soft_assertions:
  description: |
    软断言在失败时不会立即停止测试，而是记录失败并继续执行。
    这样可以在一次运行中收集多个失败点，提高调试效率。

  when_to_use:
    - "需要验证多个独立条件"
    - "想收集尽可能多的失败信息"
    - "非关键路径的验证"

  when_not_to_use:
    - "后续步骤依赖当前断言结果"
    - "关键前置条件验证"
    - "登录等阻塞性操作"
```

### 2.2 使用方式

```yaml
soft_assertion_usage:
  example: |
    // Playwright 软断言
    const errors = [];

    try {
      await expect(page.locator('[data-testid="title"]'))
        .toHaveText('Welcome');
    } catch (e) {
      errors.push(e);
    }

    try {
      await expect(page.locator('[data-testid="subtitle"]'))
        .toBeVisible();
    } catch (e) {
      errors.push(e);
    }

    try {
      await expect(page.locator('[data-testid="count"]'))
        .toHaveText('10');
    } catch (e) {
      errors.push(e);
    }

    // 最后统一抛出
    if (errors.length > 0) {
      throw new AggregateError(errors, `${errors.length} assertions failed`);
    }

  yaml_config:
    soft_assert:
      - selector: "[data-testid='title']"
        assertion: has_text
        value: "Welcome"
        soft: true

      - selector: "[data-testid='subtitle']"
        assertion: visible
        soft: true

      - selector: "[data-testid='count']"
        assertion: has_text
        value: "10"
        soft: true

    on_complete:
      aggregate_failures: true
      continue_on_failure: true
```

---

## 3. 断言超时

```yaml
timeouts:
  default:
    visibility: 5000
    text: 5000
    navigation: 30000
    network: 10000

  override_per_assertion:
    - assert_visible:
        selector: "[data-testid='slow-loading']"
        timeout: 15000

  retry:
    enabled: true
    interval: 100  # ms
    auto_wait: true
```

---

## 4. 失败处理

### 4.1 失败分类

```yaml
failure_categories:
  assertion_failed:
    description: "预期与实际不符"
    severity: "varies"
    evidence:
      - screenshot
      - expected_vs_actual

  element_not_found:
    description: "找不到目标元素"
    severity: "high"
    evidence:
      - screenshot
      - dom_snapshot

  timeout:
    description: "等待超时"
    severity: "medium"
    evidence:
      - screenshot
      - network_log

  network_error:
    description: "网络请求失败"
    severity: "high"
    evidence:
      - network_log
      - console_log

  script_error:
    description: "页面 JS 错误"
    severity: "high"
    evidence:
      - console_log
      - stack_trace
```

### 4.2 失败报告

```yaml
failure_report:
  template: |
    ## 断言失败

    **用例**: {case_id} - {case_name}
    **步骤**: {step_number}
    **断言**: {assertion_type}

    ### 期望 vs 实际
    - 期望: {expected}
    - 实际: {actual}

    ### 选择器
    ```
    {selector}
    ```

    ### 截图
    ![失败截图](evidence/{case_id}-failure.png)

    ### DOM 片段
    ```html
    {dom_snippet}
    ```

    ### 建议
    {suggestion}
```

---

## 5. 数据驱动断言

```yaml
data_driven:
  # 从数据文件读取预期值
  external_data:
    source: "test-data/expected-values.yaml"
    usage: |
      const expected = loadTestData('login-success');
      await expect(page.locator('[data-testid="message"]'))
        .toHaveText(expected.welcomeMessage);

  # 动态生成预期值
  dynamic_expected:
    example: |
      const orderId = generateOrderId();
      await expect(page.locator('[data-testid="order-id"]'))
        .toHaveText(orderId);

  # 基于环境的预期值
  environment_based:
    example: |
      const expectedUrl = process.env.BASE_URL + '/dashboard';
      await expect(page).toHaveURL(expectedUrl);
```

---

## 6. 复杂断言模式

### 6.1 等待并断言

```yaml
wait_and_assert:
  # 等待条件满足后断言
  pattern: |
    await page.waitForSelector('[data-testid="loaded"]');
    await expect(page.locator('[data-testid="data-count"]'))
      .toHaveText('10');

  # 轮询断言 (最终一致性)
  polling: |
    await expect(async () => {
      const count = await page.textContent('[data-testid="count"]');
      expect(parseInt(count)).toBeGreaterThan(0);
    }).toPass({ timeout: 10000 });
```

### 6.2 多元素断言

```yaml
multi_element:
  # 所有元素满足条件
  all: |
    const items = page.locator('[data-testid="item"]');
    await expect(items).toHaveCount(5);
    for (let i = 0; i < 5; i++) {
      await expect(items.nth(i)).toBeVisible();
    }

  # 至少一个元素满足
  any: |
    const items = page.locator('[data-testid="item"]');
    const count = await items.count();
    let found = false;
    for (let i = 0; i < count; i++) {
      const text = await items.nth(i).textContent();
      if (text.includes('特价')) {
        found = true;
        break;
      }
    }
    expect(found).toBe(true);
```

---

## 7. 最佳实践

```yaml
best_practices:
  clarity:
    - "每个断言都要有清晰的错误消息"
    - "断言应该描述'预期什么'而非'如何验证'"

  stability:
    - "使用合理的超时时间"
    - "对于异步内容使用等待"
    - "避免过于精确的断言 (如精确时间戳)"

  coverage:
    - "验证正向和负向场景"
    - "验证边界条件"
    - "不只验证 Happy Path"

  maintenance:
    - "将断言逻辑封装在 Page Object 中"
    - "使用数据驱动避免硬编码"
    - "定期清理不再需要的断言"
```

---

## 版本历史

| 版本 | 日期 | 变更说明 |
|------|------|----------|
| 1.0 | 2026-01-13 | 初始版本 |
