# Backend Log & Trace Skill v1.0
# 后端日志与链路追踪技能

## 概述

按 request_id/trace_id 拉取全链路日志，聚合错误栈、异常码、关键上下文参数。
产出"可能根因 Top N + 证据链"。

## 技能标识

- **ID**: skill.test.backend_trace
- **名称**: Backend Log & Trace
- **版本**: 1.0
- **所有者**: test-governance

## 适用 Agent

- agent.test.debug_agent

---

## 1. Trace ID 关联

```yaml
trace_correlation:
  id_types:
    - trace_id: "分布式链路 ID"
    - request_id: "请求 ID"
    - span_id: "调用段 ID"
    - user_id: "用户 ID (辅助)"
    - order_id: "业务 ID (辅助)"

  extraction_sources:
    - "HTTP Header: X-Trace-Id"
    - "HTTP Header: X-Request-Id"
    - "前端 Network 日志"
    - "Bug 契约中的 trace_id 字段"

  correlation_flow: |
    1. 从前端 network 日志获取 request header 中的 trace_id
    2. 使用 trace_id 查询后端日志系统
    3. 获取完整调用链
    4. 聚合所有相关日志

  example:
    input:
      trace_id: "abc123def456"
    query: |
      SELECT * FROM logs
      WHERE trace_id = 'abc123def456'
      ORDER BY timestamp ASC
```

---

## 2. 日志采集

### 2.1 日志查询

```yaml
log_query:
  systems:
    elasticsearch:
      query: |
        GET /logs-*/_search
        {
          "query": {
            "bool": {
              "must": [
                { "term": { "trace_id": "{trace_id}" } }
              ]
            }
          },
          "sort": [{ "@timestamp": "asc" }]
        }

    loki:
      query: |
        {app="myapp"} |= "{trace_id}"

    cloudwatch:
      query: |
        fields @timestamp, @message
        | filter trace_id = "{trace_id}"
        | sort @timestamp asc

  time_window:
    default: "1h"
    max: "24h"
    around_incident: true  # 以故障时间为中心
```

### 2.2 日志解析

```yaml
log_parsing:
  formats:
    json:
      fields:
        - timestamp
        - level
        - message
        - trace_id
        - span_id
        - service
        - method
        - duration
        - error
        - stack_trace

    text:
      pattern: "{timestamp} [{level}] [{trace_id}] {service} - {message}"

  extraction:
    error_patterns:
      - "Exception"
      - "Error"
      - "FATAL"
      - "failed"
      - "timeout"

    context_patterns:
      - "user_id=\\d+"
      - "order_id=\\w+"
      - "sku=\\w+"

    timing_patterns:
      - "duration=(\\d+)ms"
      - "elapsed=(\\d+)"
```

---

## 3. 调用链可视化

```yaml
call_chain:
  visualization:
    format: "mermaid"
    template: |
      sequenceDiagram
        participant Client
        participant Gateway
        participant OrderService
        participant InventoryService
        participant DB

        Client->>Gateway: POST /orders
        Gateway->>OrderService: createOrder()
        OrderService->>InventoryService: checkStock()
        Note over InventoryService: ❌ TimeoutException
        InventoryService-->>OrderService: timeout (3500ms)
        OrderService-->>Gateway: 500 Internal Error
        Gateway-->>Client: 500

  timeline:
    format: "table"
    columns:
      - timestamp
      - service
      - method
      - duration
      - status
      - message

  example: |
    | 时间戳 | 服务 | 方法 | 耗时 | 状态 | 消息 |
    |--------|------|------|------|------|------|
    | 10:30:45.100 | Gateway | handleRequest | - | START | POST /orders |
    | 10:30:45.110 | OrderService | createOrder | - | START | |
    | 10:30:45.115 | OrderService | validateUser | 5ms | OK | |
    | 10:30:45.120 | InventoryService | checkStock | - | START | |
    | 10:30:48.620 | InventoryService | checkStock | 3500ms | TIMEOUT | ❌ |
    | 10:30:48.630 | OrderService | createOrder | 3520ms | ERROR | InventoryCheckFailed |
    | 10:30:48.640 | Gateway | handleRequest | 3540ms | 500 | Internal Error |
```

---

## 4. 异常分析

```yaml
exception_analysis:
  stack_trace_parsing:
    extract:
      - exception_type
      - message
      - stack_frames
      - caused_by

    format:
      exception_type: "TimeoutException"
      message: "Inventory check timed out after 3000ms"
      stack_frames:
        - class: "com.example.InventoryService"
          method: "checkStock"
          file: "InventoryService.java"
          line: 156
        - class: "com.example.OrderService"
          method: "createOrder"
          file: "OrderService.java"
          line: 89
      caused_by: null

  root_exception:
    description: "找到最底层的异常（caused by 链的末端）"
    importance: "通常是真正的根因"

  common_patterns:
    timeout:
      keywords: ["timeout", "timed out", "deadline exceeded"]
      likely_cause: "下游服务响应慢或网络问题"

    null_pointer:
      keywords: ["NullPointerException", "null", "undefined"]
      likely_cause: "数据缺失或未初始化"

    connection:
      keywords: ["ConnectionException", "refused", "reset"]
      likely_cause: "服务不可用或网络问题"

    database:
      keywords: ["SQLException", "deadlock", "constraint"]
      likely_cause: "数据库问题"
```

---

## 5. 上下文聚合

```yaml
context_aggregation:
  from_logs:
    user_context:
      - user_id
      - user_type
      - permissions

    request_context:
      - request_id
      - trace_id
      - client_ip
      - user_agent

    business_context:
      - order_id
      - sku
      - quantity
      - payment_method

    system_context:
      - service_version
      - instance_id
      - region
      - pod_name

  output:
    context_summary:
      user:
        user_id: "12345"
        user_type: "normal"
      request:
        trace_id: "abc123"
        path: "/api/orders"
        method: "POST"
      business:
        order_id: "pending"
        sku: "SKU-001"
        quantity: 1
      system:
        service: "order-service"
        version: "2.3.1"
        instance: "order-service-pod-abc"
```

---

## 6. 根因候选输出

```yaml
root_cause_candidates:
  format:
    - rank: 1
      hypothesis: "InventoryService.checkStock 超时导致订单创建失败"
      confidence: 0.9
      evidence:
        - type: "exception"
          content: "TimeoutException at InventoryService.checkStock"
          timestamp: "10:30:48.620"
        - type: "timing"
          content: "checkStock 耗时 3500ms，超过 3000ms 阈值"
        - type: "log"
          content: "WARN: Inventory service response slow"
      suggested_fix:
        - "增加 Inventory 服务超时时间"
        - "优化 Inventory 服务性能"
        - "添加熔断降级"
      affected_code:
        - file: "InventoryService.java"
          line: 156
          method: "checkStock"

    - rank: 2
      hypothesis: "数据库连接池耗尽导致 Inventory 查询慢"
      confidence: 0.6
      evidence:
        - type: "log"
          content: "WARN: Connection pool exhausted, waiting..."
      suggested_fix:
        - "增加连接池大小"
        - "优化慢查询"
```

---

## 7. 敏感信息处理

```yaml
sensitive_data:
  auto_mask:
    fields:
      - password
      - token
      - secret
      - credit_card
      - phone
      - email
      - id_card

    patterns:
      - "Bearer [A-Za-z0-9\\-_]+"
      - "\\d{11}"  # 手机号
      - "\\d{16,19}"  # 银行卡

  mask_action: "replace with ***MASKED***"

  audit_log:
    enabled: true
    log_access: true
    retention: "90d"
```

---

## 8. 日志源配置

```yaml
log_sources:
  # 配置多个日志源
  elasticsearch:
    enabled: true
    url: "${ES_URL}"
    index_pattern: "logs-*"
    auth: "${ES_AUTH}"

  loki:
    enabled: false
    url: "${LOKI_URL}"

  cloudwatch:
    enabled: false
    region: "${AWS_REGION}"
    log_group: "${LOG_GROUP}"

  file:
    enabled: true
    paths:
      - "/var/log/app/*.log"
    format: "json"
```

---

## 版本历史

| 版本 | 日期 | 变更说明 |
|------|------|----------|
| 1.0 | 2026-01-13 | 初始版本 |
