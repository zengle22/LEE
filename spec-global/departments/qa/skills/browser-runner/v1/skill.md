# Browser Runner Skill v1.0
# Chrome 浏览器自动化技能

## 概述

Browser Runner 技能负责驱动 Chrome/Chromium 浏览器执行 E2E 测试。
基于 Playwright，提供页面导航、交互、等待、断言和证据采集能力。

## 技能标识

- **ID**: skill.test.browser_runner
- **名称**: Browser Runner (Chrome)
- **版本**: 1.0
- **所有者**: test-governance
- **实现框架**: Playwright

## 适用 Agent

- agent.test.e2e_test_executor

---

## 1. 核心能力

### 1.1 浏览器启动配置

```yaml
browser_config:
  browser: chromium  # chromium | firefox | webkit
  headless: true     # CI 环境用 true，调试用 false

  viewport:
    width: 1280
    height: 720

  # 慢动作模式 (调试用)
  slow_mo: 0  # ms

  # 录制配置
  record:
    video:
      enabled: true
      dir: "evidence/videos/"
      size: { width: 1280, height: 720 }
    trace:
      enabled: true
      dir: "evidence/traces/"
      screenshots: true
      snapshots: true

  # 超时配置
  timeouts:
    navigation: 30000
    action: 10000
    assertion: 5000

  # 网络配置
  network:
    offline: false
    throttle: null  # "slow-3g" | "fast-3g" | null
```

### 1.2 页面导航

```yaml
navigation:
  actions:
    - navigate:
        url: "https://example.com/login"
        wait_until: "networkidle"  # load | domcontentloaded | networkidle

    - go_back:
        wait_until: "load"

    - go_forward:
        wait_until: "load"

    - reload:
        wait_until: "networkidle"

  url_assertion:
    - assert_url:
        pattern: "*/dashboard*"
        message: "应跳转到仪表盘页面"
```

### 1.3 元素交互

```yaml
interactions:
  # 点击
  click:
    selector: "[data-testid='login-button']"
    options:
      force: false
      click_count: 1
      delay: 0

  # 填写输入框
  fill:
    selector: "[data-testid='email-input']"
    value: "test@example.com"
    options:
      clear_before: true

  # 下拉选择
  select:
    selector: "[data-testid='country-select']"
    value: "CN"  # 或 label: "中国"

  # 复选框
  check:
    selector: "[data-testid='agree-checkbox']"

  uncheck:
    selector: "[data-testid='newsletter-checkbox']"

  # 悬停
  hover:
    selector: "[data-testid='menu-item']"

  # 滚动
  scroll:
    selector: "[data-testid='long-list']"
    direction: "down"
    distance: 500

  # 文件上传
  upload:
    selector: "[data-testid='file-input']"
    files: ["test-data/avatar.png"]

  # 拖拽
  drag_and_drop:
    source: "[data-testid='drag-item']"
    target: "[data-testid='drop-zone']"
```

### 1.4 等待策略

```yaml
wait_strategies:
  # 等待元素出现
  wait_for_selector:
    selector: "[data-testid='loading-complete']"
    state: "visible"  # attached | detached | visible | hidden
    timeout: 10000

  # 等待网络空闲
  wait_for_network_idle:
    timeout: 5000

  # 等待特定请求完成
  wait_for_request:
    url_pattern: "**/api/users"
    method: "POST"
    timeout: 10000

  # 等待响应
  wait_for_response:
    url_pattern: "**/api/login"
    status: 200
    timeout: 10000

  # 固定等待 (尽量避免)
  wait_for_timeout:
    ms: 1000
    reason: "等待动画完成"
```

---

## 2. 证据采集

### 2.1 截图

```yaml
screenshot:
  # 全页截图
  full_page:
    path: "evidence/screenshots/{case_id}-{step}-fullpage.png"
    full_page: true

  # 元素截图
  element:
    selector: "[data-testid='error-message']"
    path: "evidence/screenshots/{case_id}-error.png"

  # 关键点自动截图
  auto_capture:
    on_failure: true
    on_assertion: true
    on_step_complete: false
```

### 2.2 视频录制

```yaml
video:
  enabled: true
  dir: "evidence/videos/"
  size: { width: 1280, height: 720 }

  # 视频保留策略
  retention:
    on_pass: false      # 通过的用例不保留视频
    on_failure: true    # 失败的用例保留视频
    on_flaky: true      # 不稳定的用例保留视频
```

### 2.3 Trace 采集

```yaml
trace:
  enabled: true
  dir: "evidence/traces/"

  captures:
    screenshots: true
    snapshots: true
    sources: true

  # Trace 可用 Playwright Trace Viewer 打开
  # npx playwright show-trace trace.zip
```

### 2.4 日志采集

```yaml
logs:
  console:
    enabled: true
    path: "evidence/logs/{case_id}-console.json"
    levels: ["error", "warning", "log"]

  network:
    enabled: true
    path: "evidence/logs/{case_id}-network.json"
    capture:
      requests: true
      responses: true
      failed_requests: true
```

---

## 3. 网络拦截

### 3.1 请求拦截

```yaml
network_intercept:
  # Mock API 响应
  mock_response:
    url_pattern: "**/api/feature-flags"
    response:
      status: 200
      body: { "new_feature": true }

  # 阻止请求
  block_request:
    url_patterns:
      - "**/analytics/**"
      - "**/ads/**"

  # 延迟响应 (测试 loading 状态)
  delay_response:
    url_pattern: "**/api/slow-endpoint"
    delay_ms: 3000

  # 模拟错误
  simulate_error:
    url_pattern: "**/api/unstable"
    error_rate: 0.5
    error_status: 500
```

---

## 4. 多标签页/多窗口

```yaml
multi_context:
  # 新标签页
  new_tab:
    trigger: "[data-testid='open-in-new-tab']"
    wait_for_load: true

  # 弹出窗口
  popup:
    trigger: "[data-testid='oauth-login']"
    handle:
      fill: "[name='username']"
      value: "test@example.com"
      click: "[type='submit']"

  # iframe
  iframe:
    selector: "iframe[name='payment-frame']"
    actions:
      - fill:
          selector: "[name='card-number']"
          value: "4242424242424242"
```

---

## 5. 移动设备模拟

```yaml
mobile_emulation:
  devices:
    - name: "iPhone 12"
      viewport: { width: 390, height: 844 }
      user_agent: "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0...)"
      has_touch: true
      is_mobile: true

    - name: "Pixel 5"
      viewport: { width: 393, height: 851 }
      has_touch: true
      is_mobile: true

  touch_actions:
    - tap:
        selector: "[data-testid='menu-button']"
    - swipe:
        start: { x: 300, y: 500 }
        end: { x: 50, y: 500 }
```

---

## 6. 错误处理

```yaml
error_handling:
  element_not_found:
    retry: 3
    retry_interval_ms: 1000
    on_exhaust: capture_and_fail

  timeout:
    capture_screenshot: true
    capture_dom: true
    fail_with_details: true

  network_error:
    retry: 2
    report_as: "environment_error"
```

---

## 7. 最佳实践

### 7.1 选择器策略 (关键!)

```yaml
selector_priority:
  # 推荐 (从高到低)
  1_data_testid: "[data-testid='login-button']"
  2_data_e2e: "[data-e2e='submit-form']"
  3_unique_id: "#unique-element-id"
  4_aria_label: "[aria-label='Close dialog']"
  5_role: "button[name='Submit']"

  # 避免使用
  bad_dynamic_class: ".ant-btn-primary"  # 会变
  bad_nth_child: "div:nth-child(3)"      # 脆弱
  bad_text: "text='Submit'"               # 国际化会变
```

### 7.2 等待策略

- **优先使用**: wait_for_selector, wait_for_response
- **尽量避免**: wait_for_timeout (固定等待)
- **网络相关**: wait_for_network_idle

### 7.3 可靠性

- 每个关键操作后验证状态
- 使用软断言收集更多失败信息
- 失败时完整采集证据

---

## 版本历史

| 版本 | 日期 | 变更说明 |
|------|------|----------|
| 1.0 | 2026-01-13 | 初始版本 |
