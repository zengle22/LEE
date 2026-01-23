# Frontend Observability Skill v1.0
# 前端可观测性技能

## 概述

启动 Chrome/小程序沙箱，采集前端运行时信息：console、network、performance、页面快照、关键 DOM 状态。
支持"对比前后版本差异"，帮助定位前端相关问题。

## 技能标识

- **ID**: skill.test.frontend_observability
- **名称**: Frontend Observability
- **版本**: 1.0
- **所有者**: test-governance

## 适用 Agent

- agent.test.debug_agent
- agent.test.e2e_test_executor

---

## 1. Console 日志采集

```yaml
console_capture:
  levels:
    - error    # 必采
    - warning  # 必采
    - log      # 可选
    - info     # 可选
    - debug    # 调试时采

  format:
    - timestamp: "2026-01-13T10:30:45.123Z"
      level: "error"
      message: "Uncaught TypeError: Cannot read property 'id' of undefined"
      source: "app.js:1234"
      stack_trace: |
        at OrderService.getOrderId (app.js:1234)
        at handleClick (checkout.js:56)

  filtering:
    ignore_patterns:
      - "favicon.ico"
      - "analytics"
      - "hotjar"
    highlight_patterns:
      - "Error"
      - "Exception"
      - "Failed"
      - "undefined"
      - "null"

  output:
    path: "evidence/console/{case_id}.json"
```

---

## 2. Network 请求采集

```yaml
network_capture:
  capture_all: true

  request_details:
    - url
    - method
    - headers
    - body (if POST/PUT)
    - timestamp

  response_details:
    - status
    - headers
    - body (truncate if > 10KB)
    - timing
    - size

  error_detection:
    - status >= 400
    - status == 0 (网络错误)
    - timing.total > 5000 (慢请求)
    - body contains "error"

  format:
    - request_id: "req-001"
      url: "https://api.example.com/orders"
      method: "POST"
      request:
        headers:
          Authorization: "Bearer ***MASKED***"
          Content-Type: "application/json"
        body: { "sku": "SKU-001", "quantity": 1 }
      response:
        status: 500
        headers: { ... }
        body: { "error": "INVENTORY_CHECK_FAILED", "message": "库存检查超时" }
      timing:
        dns: 5
        connect: 10
        ssl: 15
        wait: 3500  # 问题！
        receive: 20
        total: 3550

  output:
    path: "evidence/network/{case_id}.json"
    summary_path: "evidence/network/{case_id}-summary.md"
```

---

## 3. Performance 采集

```yaml
performance_capture:
  metrics:
    navigation_timing:
      - domContentLoaded
      - load
      - firstPaint
      - firstContentfulPaint
      - largestContentfulPaint

    resource_timing:
      - "slow resources (> 1s)"
      - "failed resources"
      - "large resources (> 1MB)"

    long_tasks:
      - "tasks > 50ms"
      - "blocking time"

  memory:
    - heap_used
    - heap_total
    - memory_leaks (对比前后)

  format:
    navigation:
      domContentLoaded: 1200
      load: 2500
      firstPaint: 800
      firstContentfulPaint: 1000
      largestContentfulPaint: 1800
    slow_resources:
      - url: "https://cdn.example.com/large-image.png"
        duration: 3200
        size: 2500000
    long_tasks:
      - start: 1500
        duration: 150
        source: "app.bundle.js"

  output:
    path: "evidence/performance/{case_id}.json"
```

---

## 4. DOM 快照

```yaml
dom_snapshot:
  capture_points:
    - "页面加载完成"
    - "错误发生时"
    - "关键操作前后"

  capture_content:
    full_html:
      path: "evidence/dom/{case_id}-{step}.html"

    key_elements:
      selectors:
        - "[data-testid='error-message']"
        - "[data-testid='order-form']"
        - ".modal"
        - ".toast"
      capture:
        - outerHTML
        - computedStyle
        - boundingRect
        - visibility

    diff_mode:
      before: "evidence/dom/{case_id}-before.html"
      after: "evidence/dom/{case_id}-after.html"
      diff: "evidence/dom/{case_id}-diff.html"
```

---

## 5. 截图采集

```yaml
screenshot_capture:
  types:
    full_page:
      description: "整页截图"
      path: "evidence/screenshots/{case_id}-{step}-full.png"

    viewport:
      description: "可视区域截图"
      path: "evidence/screenshots/{case_id}-{step}-viewport.png"

    element:
      description: "指定元素截图"
      selector: "[data-testid='error-message']"
      path: "evidence/screenshots/{case_id}-error-element.png"

  auto_capture_on:
    - "page_load"
    - "error_occurred"
    - "assertion_failed"
    - "before_click"
    - "after_click"

  annotation:
    enabled: true
    highlight_errors: true
    add_timestamp: true
```

---

## 6. 版本对比

```yaml
version_comparison:
  description: "对比 Bug 版本和当前版本的前端行为差异"

  compare_dimensions:
    network:
      - "请求数量变化"
      - "响应时间变化"
      - "错误率变化"

    console:
      - "新增错误"
      - "消失的错误"
      - "日志级别变化"

    dom:
      - "元素存在性"
      - "元素内容"
      - "样式变化"

    performance:
      - "加载时间变化"
      - "资源大小变化"

  output:
    diff_report:
      path: "evidence/comparison/{case_id}-diff.md"
      template: |
        ## 版本对比报告

        ### 版本信息
        - 基线版本: {baseline_version}
        - 当前版本: {current_version}

        ### Network 变化
        | 维度 | 基线 | 当前 | 变化 |
        |------|------|------|------|
        | 请求数 | {baseline_requests} | {current_requests} | {diff_requests} |
        | 平均耗时 | {baseline_avg_time} | {current_avg_time} | {diff_avg_time} |
        | 错误率 | {baseline_error_rate} | {current_error_rate} | {diff_error_rate} |

        ### Console 变化
        #### 新增错误
        {new_errors}

        #### 消失的错误
        {removed_errors}

        ### DOM 变化
        {dom_changes}
```

---

## 7. 微信小程序适配

```yaml
wechat_adaptation:
  console:
    capture_via: "开发者工具 console API"
    levels: ["error", "warn", "log"]

  network:
    capture_via: "wx.request 拦截"
    include_wx_apis: true

  page_snapshot:
    capture_via: "WXML 结构导出"
    format: "xml"

  limitations:
    - "视频录制依赖开发者工具"
    - "Performance API 支持有限"
    - "部分原生组件无法截图"
```

---

## 8. 证据聚合

```yaml
evidence_bundle:
  output:
    path: "evidence/frontend/{case_id}/"
    structure: |
      {case_id}/
      ├── console.json
      ├── network.json
      ├── network-summary.md
      ├── performance.json
      ├── dom/
      │   ├── step-1.html
      │   ├── step-2.html
      │   └── error.html
      ├── screenshots/
      │   ├── step-1-full.png
      │   ├── step-2-full.png
      │   └── error-element.png
      └── summary.md

  summary_template: |
    ## 前端证据摘要

    ### 关键发现
    - Console 错误数: {error_count}
    - Network 失败请求: {failed_requests}
    - 慢请求 (>3s): {slow_requests}

    ### 主要错误
    {#each top_errors}
    - [{level}] {message} @ {source}
    {/each}

    ### 失败请求
    {#each failed_network}
    - {method} {url} → {status}
    {/each}
```

---

## 版本历史

| 版本 | 日期 | 变更说明 |
|------|------|----------|
| 1.0 | 2026-01-13 | 初始版本 |
