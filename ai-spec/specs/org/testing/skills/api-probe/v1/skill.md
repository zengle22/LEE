# API Probe Skill v1.0
# API 探测技能

## 概述

直接重放接口请求（与 UI 解耦），自动做参数边界/缺参/异常路径试探。
帮助区分"前端渲染问题 vs 后端数据问题"。

## 技能标识

- **ID**: skill.test.api_probe
- **名称**: API Probe
- **版本**: 1.0
- **所有者**: test-governance

## 适用 Agent

- agent.test.debug_agent

---

## 1. 请求重放

### 1.1 从 Network 日志重放

```yaml
replay_from_network:
  input:
    network_log:
      url: "https://api.example.com/orders"
      method: "POST"
      headers:
        Authorization: "Bearer token123"
        Content-Type: "application/json"
      body:
        sku: "SKU-001"
        quantity: 1

  replay_options:
    preserve_headers: true
    preserve_body: true
    new_trace_id: true  # 生成新的 trace_id 便于追踪

  output:
    original_response:
      status: 500
      body: { "error": "INVENTORY_CHECK_FAILED" }

    replay_response:
      status: 500  # 可复现
      body: { "error": "INVENTORY_CHECK_FAILED" }
      trace_id: "new-trace-456"

    conclusion: "问题可通过 API 复现，非前端特定问题"
```

### 1.2 构造请求

```yaml
construct_request:
  from_api_spec:
    openapi_path: "api-specs/order-service.yaml"
    endpoint: "/orders"
    method: "POST"

  generate:
    valid_request:
      body:
        sku: "SKU-001"
        quantity: 1
      expected: 200

    edge_cases:
      - name: "quantity = 0"
        body: { sku: "SKU-001", quantity: 0 }
        expected: 400

      - name: "quantity = -1"
        body: { sku: "SKU-001", quantity: -1 }
        expected: 400

      - name: "missing sku"
        body: { quantity: 1 }
        expected: 400

      - name: "invalid sku"
        body: { sku: "INVALID", quantity: 1 }
        expected: 404
```

---

## 2. 参数探测

### 2.1 边界值探测

```yaml
boundary_probing:
  strategies:
    numeric:
      - value: 0
        description: "零值"
      - value: -1
        description: "负数"
      - value: 1
        description: "最小正数"
      - value: 2147483647
        description: "INT_MAX"
      - value: 9999999999
        description: "超大数"

    string:
      - value: ""
        description: "空字符串"
      - value: " "
        description: "空格"
      - value: "a" * 10000
        description: "超长字符串"
      - value: "<script>alert(1)</script>"
        description: "XSS 探测"
      - value: "'; DROP TABLE users; --"
        description: "SQL 注入探测"

    array:
      - value: []
        description: "空数组"
      - value: ["a"] * 1000
        description: "超大数组"

    object:
      - value: null
        description: "null 值"
      - value: {}
        description: "空对象"

  output:
    probe_results:
      - param: "quantity"
        value: 0
        response_status: 400
        response_body: { "error": "INVALID_QUANTITY" }
        conclusion: "正确处理零值"

      - param: "quantity"
        value: -1
        response_status: 200  # 问题！
        response_body: { "order_id": "ORD-123" }
        conclusion: "❌ 未校验负数，可能是 Bug"
```

### 2.2 缺参探测

```yaml
missing_param_probing:
  strategy: "逐个移除必填参数"

  example:
    original:
      sku: "SKU-001"
      quantity: 1
      address_id: "ADDR-001"

    probes:
      - removed: "sku"
        request: { quantity: 1, address_id: "ADDR-001" }
        expected: 400
        actual: 400
        conclusion: "正确校验 sku 必填"

      - removed: "quantity"
        request: { sku: "SKU-001", address_id: "ADDR-001" }
        expected: 400
        actual: 200  # 问题！
        conclusion: "❌ quantity 未校验必填"

      - removed: "address_id"
        request: { sku: "SKU-001", quantity: 1 }
        expected: 400
        actual: 400
        conclusion: "正确校验 address_id 必填"
```

### 2.3 类型探测

```yaml
type_probing:
  strategy: "用错误类型的值测试"

  example:
    param: "quantity"
    expected_type: "integer"

    probes:
      - value: "abc"
        type: "string"
        expected: 400
        actual: 400
        conclusion: "正确拒绝字符串"

      - value: 1.5
        type: "float"
        expected: 400
        actual: 200  # 可能问题
        conclusion: "⚠️ 接受浮点数，可能导致精度问题"

      - value: true
        type: "boolean"
        expected: 400
        actual: 400
        conclusion: "正确拒绝布尔值"
```

---

## 3. 前后端区分

```yaml
frontend_vs_backend:
  diagnosis_flow:
    step_1:
      action: "直接调用 API（绕过 UI）"
      if_success: "问题在前端"
      if_failure: "问题在后端或 API"

    step_2:
      action: "用相同参数从 UI 触发"
      compare: "请求参数是否一致"
      if_different: "前端参数构造问题"
      if_same: "问题在后端"

    step_3:
      action: "检查响应处理"
      check: "前端是否正确解析响应"

  output:
    conclusion_types:
      - "FRONTEND_RENDER": "前端渲染问题"
      - "FRONTEND_PARAM": "前端参数构造问题"
      - "FRONTEND_PARSE": "前端响应解析问题"
      - "BACKEND_LOGIC": "后端业务逻辑问题"
      - "BACKEND_DATA": "后端数据问题"
      - "BACKEND_INFRA": "后端基础设施问题"

  example:
    api_direct:
      status: 200
      body: { "order_id": "ORD-123", "status": "created" }

    ui_triggered:
      status: 200
      body: { "order_id": "ORD-123", "status": "created" }

    ui_display: "页面显示错误"

    conclusion: "FRONTEND_RENDER - API 返回正确，前端渲染有问题"
```

---

## 4. 并发探测

```yaml
concurrency_probing:
  scenarios:
    race_condition:
      description: "并发请求同一资源"
      requests:
        - { method: "POST", path: "/orders", body: { sku: "SKU-001" } }
        - { method: "POST", path: "/orders", body: { sku: "SKU-001" } }
      timing: "simultaneous"
      check: "是否超卖"

    sequence_violation:
      description: "乱序请求"
      requests:
        - { method: "POST", path: "/orders/{id}/pay" }  # 先支付
        - { method: "POST", path: "/orders" }           # 后创建
      check: "是否正确拒绝"

  output:
    race_condition_result:
      requests_sent: 2
      success_count: 2  # 问题！应该只有 1 个成功
      conclusion: "❌ 存在并发超卖问题"
```

---

## 5. 幂等性探测

```yaml
idempotency_probing:
  strategy: "重复发送相同请求"

  test:
    request:
      method: "POST"
      path: "/orders"
      body: { sku: "SKU-001", quantity: 1 }
      idempotency_key: "key-123"

    repeat_count: 3

    expected:
      first_request: 201
      subsequent_requests: 200 or 409
      side_effect: "只创建一个订单"

    actual:
      first_request: 201
      subsequent_requests: 201  # 问题！
      side_effect: "创建了 3 个订单"

    conclusion: "❌ 未实现幂等性"
```

---

## 6. 响应分析

```yaml
response_analysis:
  checks:
    status_code:
      expected_ranges:
        success: [200, 201, 204]
        client_error: [400, 401, 403, 404, 422]
        server_error: [500, 502, 503]

    response_time:
      thresholds:
        fast: "< 200ms"
        normal: "200ms - 1s"
        slow: "1s - 3s"
        timeout: "> 3s"

    response_body:
      validate_schema: true
      check_error_format: true
      check_sensitive_data: true

  output:
    summary:
      status: 500
      time: "3500ms"
      body_valid: false
      issues:
        - "响应时间超过阈值"
        - "错误响应格式不规范"
```

---

## 7. 证据输出

```yaml
evidence_output:
  path: "evidence/api/{case_id}/"

  files:
    requests_log: "requests.json"
    responses_log: "responses.json"
    probe_results: "probe-results.json"
    summary: "api-probe-summary.md"

  summary_template: |
    ## API 探测报告

    ### 探测概览
    - 总请求数: {total_requests}
    - 成功: {success_count}
    - 失败: {failure_count}
    - 异常: {anomaly_count}

    ### 关键发现
    {#each findings}
    - [{severity}] {description}
    {/each}

    ### 前后端定位
    问题位置: {location}
    原因: {reason}

    ### 建议修复
    {#each suggestions}
    - {suggestion}
    {/each}
```

---

## 版本历史

| 版本 | 日期 | 变更说明 |
|------|------|----------|
| 1.0 | 2026-01-13 | 初始版本 |
