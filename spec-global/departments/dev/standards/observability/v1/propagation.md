# Header Propagation Rules v1.0
# HTTP Header 透传规则

## 概述

本文档定义前端/网关/服务之间的 HTTP Header 透传契约，确保分布式追踪 ID 能够贯穿整个调用链。

---

## 1. 核心 Header 定义

### 1.1 追踪相关 Header

| Header | 格式 | 说明 | 来源 |
|--------|------|------|------|
| `traceparent` | W3C Trace Context | 分布式追踪上下文 | 网关生成 |
| `tracestate` | W3C Trace Context | 追踪状态扩展 | 可选 |
| `x-trace-id` | 32位十六进制 | 追踪 ID（简化版） | 网关生成 |
| `x-span-id` | 16位十六进制 | 当前 Span ID | 各服务生成 |
| `x-request-id` | `req_xxx` | 请求 ID | 网关生成 |
| `x-client-request-id` | `cr_xxx` | 客户端请求 ID | 前端生成 |

### 1.2 W3C Trace Context 格式

```
traceparent: {version}-{trace_id}-{parent_id}-{flags}
```

示例：
```
traceparent: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01
              │   │                                │               │
              │   │                                │               └─ flags (01=sampled)
              │   │                                └─ parent_id (16 hex)
              │   └─ trace_id (32 hex)
              └─ version (00)
```

---

## 2. 分层透传规则

### 2.1 前端 (Client)

```yaml
frontend:
  generate:
    x-client-request-id:
      format: "cr_{ulid}"
      timing: "每次用户触发的动作生成一次"
      example: "cr_01HXYZ789ABCDEF"

  send_headers:
    - x-client-request-id
    - traceparent  # 如果已有（来自上一次请求响应）

  capture_from_response:
    - x-trace-id
    - x-request-id
    - traceparent

  storage:
    session_context:
      trace_id: "缓存当前会话的 trace_id"
      request_id: "缓存当前请求的 request_id"
```

#### 前端代码示例

```typescript
// 生成 client_request_id
function generateClientRequestId(): string {
  return `cr_${ulid()}`;
}

// 请求拦截器
axios.interceptors.request.use((config) => {
  config.headers['x-client-request-id'] = generateClientRequestId();

  // 透传已有的 traceparent
  const traceparent = sessionStorage.getItem('traceparent');
  if (traceparent) {
    config.headers['traceparent'] = traceparent;
  }

  return config;
});

// 响应拦截器 - 捕获追踪头
axios.interceptors.response.use((response) => {
  const traceId = response.headers['x-trace-id'];
  const requestId = response.headers['x-request-id'];
  const traceparent = response.headers['traceparent'];

  if (traceId) sessionStorage.setItem('trace_id', traceId);
  if (requestId) sessionStorage.setItem('request_id', requestId);
  if (traceparent) sessionStorage.setItem('traceparent', traceparent);

  return response;
});
```

---

### 2.2 网关 (API Gateway)

网关是 **ID 体系的守门人**，负责：
1. 生成缺失的追踪 ID
2. 统一透传格式
3. 写入响应头供前端捕获

```yaml
gateway:
  on_request:
    # 1. 检查并生成 trace_id
    trace_id:
      if_header_missing: "traceparent"
      then: "生成新的 trace_id"
      format: "32位随机十六进制"

    # 2. 检查并生成 request_id
    request_id:
      if_header_missing: "x-request-id"
      then: "生成新的 request_id"
      format: "req_{ulid}"

    # 3. 保留 client_request_id
    client_request_id:
      action: "原样透传"

  propagate_to_upstream:
    headers:
      - traceparent  # W3C 标准
      - tracestate   # W3C 扩展
      - x-request-id
      - x-client-request-id
      - x-span-id    # 网关生成的 span

  on_response:
    add_headers:
      - name: x-trace-id
        value: "{trace_id}"
      - name: x-request-id
        value: "{request_id}"
      - name: traceparent
        value: "{generated_traceparent}"

  logging:
    required_fields:
      - trace_id
      - request_id
      - client_request_id
      - route
      - method
      - status_code
      - latency_ms
```

#### 网关代码示例 (Go/Gin)

```go
func TraceMiddleware() gin.HandlerFunc {
    return func(c *gin.Context) {
        // 1. 解析或生成 trace_id
        traceId := extractTraceId(c.GetHeader("traceparent"))
        if traceId == "" {
            traceId = generateTraceId()
        }

        // 2. 解析或生成 request_id
        requestId := c.GetHeader("x-request-id")
        if requestId == "" {
            requestId = fmt.Sprintf("req_%s", ulid.Make())
        }

        // 3. 保留 client_request_id
        clientRequestId := c.GetHeader("x-client-request-id")

        // 4. 生成新的 span_id
        spanId := generateSpanId()

        // 5. 构造 traceparent
        traceparent := fmt.Sprintf("00-%s-%s-01", traceId, spanId)

        // 6. 设置到 context
        ctx := context.WithValue(c.Request.Context(), "trace_id", traceId)
        ctx = context.WithValue(ctx, "request_id", requestId)
        ctx = context.WithValue(ctx, "client_request_id", clientRequestId)
        c.Request = c.Request.WithContext(ctx)

        // 7. 透传到上游
        c.Request.Header.Set("traceparent", traceparent)
        c.Request.Header.Set("x-request-id", requestId)

        // 8. 处理请求
        c.Next()

        // 9. 写入响应头
        c.Header("x-trace-id", traceId)
        c.Header("x-request-id", requestId)
        c.Header("traceparent", traceparent)
    }
}
```

---

### 2.3 后端服务 (Backend Service)

```yaml
backend_service:
  on_request:
    extract_headers:
      - traceparent  # 必须提取
      - x-request-id  # 必须提取
      - x-client-request-id  # 可选

    inject_to_context:
      - trace_id  # 从 traceparent 解析
      - span_id   # 从 traceparent 解析
      - request_id
      - client_request_id

  create_child_span:
    parent_span_id: "从 traceparent 获取"
    new_span_id: "生成新的 16位十六进制"
    new_traceparent: "00-{trace_id}-{new_span_id}-01"

  propagate_to_downstream:
    headers:
      - traceparent  # 更新后的 traceparent
      - x-request-id  # 原样透传
      - x-client-request-id  # 原样透传

  logging:
    mandatory_fields:
      - trace_id
      - span_id
      - request_id
    optional_fields:
      - client_request_id
      - parent_span_id
```

#### 后端代码示例 (Go)

```go
// 从 context 获取追踪信息
func GetTraceContext(ctx context.Context) TraceContext {
    return TraceContext{
        TraceID:         ctx.Value("trace_id").(string),
        SpanID:          ctx.Value("span_id").(string),
        RequestID:       ctx.Value("request_id").(string),
        ClientRequestID: ctx.Value("client_request_id").(string),
    }
}

// HTTP 客户端透传
func PropagateHeaders(ctx context.Context, req *http.Request) {
    tc := GetTraceContext(ctx)

    // 创建子 span
    newSpanId := generateSpanId()
    traceparent := fmt.Sprintf("00-%s-%s-01", tc.TraceID, newSpanId)

    req.Header.Set("traceparent", traceparent)
    req.Header.Set("x-request-id", tc.RequestID)
    if tc.ClientRequestID != "" {
        req.Header.Set("x-client-request-id", tc.ClientRequestID)
    }
}

// 结构化日志
func LogWithTrace(ctx context.Context, event string, fields map[string]any) {
    tc := GetTraceContext(ctx)

    log.Info().
        Str("trace_id", tc.TraceID).
        Str("span_id", tc.SpanID).
        Str("request_id", tc.RequestID).
        Str("event", event).
        Fields(fields).
        Msg("")
}
```

---

### 2.4 服务间调用 (RPC/gRPC)

```yaml
rpc_propagation:
  grpc:
    metadata_keys:
      - "x-trace-id"
      - "x-span-id"
      - "x-request-id"
      - "traceparent"

    interceptor:
      client: "自动注入追踪 metadata"
      server: "自动提取追踪 metadata"

  http_client:
    auto_inject:
      - traceparent
      - x-request-id
      - x-client-request-id

  message_queue:
    message_attributes:
      - trace_id
      - request_id
    comment: "通过消息属性传递追踪信息"
```

---

### 2.5 数据库查询

```yaml
database:
  sql_comment_injection:
    enabled: true
    format: "/* trace_id={trace_id}, request_id={request_id} */"
    example: |
      /* trace_id=4bf92f3577b34da6a3ce929d0e0e4736, request_id=req_01HXYZ */
      SELECT * FROM users WHERE id = $1

  benefits:
    - "DBA 可在慢查询日志中追溯请求来源"
    - "Debug Agent 可关联 DB 操作与请求"
```

---

## 3. 完整调用链示例

```
用户点击"提交订单"按钮
│
├─ 前端生成: x-client-request-id = cr_01HXYZ789
│
▼ [HTTP Request]
├─ Headers:
│   x-client-request-id: cr_01HXYZ789
│
▼ API Gateway
├─ 生成: trace_id = 4bf92f3577b34da6a3ce929d0e0e4736
├─ 生成: request_id = req_01HXYZABC
├─ 生成: span_id = 00f067aa0ba902b7
├─ 构造: traceparent = 00-4bf92f...-00f067...-01
│
├─ 日志: { trace_id, request_id, event: "http.request" }
│
▼ [透传到 Order Service]
├─ Headers:
│   traceparent: 00-4bf92f...-00f067...-01
│   x-request-id: req_01HXYZABC
│   x-client-request-id: cr_01HXYZ789
│
▼ Order Service
├─ 解析 traceparent
├─ 生成新 span_id = 1234567890abcdef
├─ 构造新 traceparent
│
├─ 日志: { trace_id, span_id, request_id, event: "svc.call" }
│
▼ [透传到 Inventory Service]
├─ Headers:
│   traceparent: 00-4bf92f...-1234567890abcdef-01
│   x-request-id: req_01HXYZABC
│
▼ Inventory Service
├─ 解析 traceparent
├─ 生成新 span_id
│
├─ 日志: { trace_id, span_id, event: "db.query" }
│
▼ [SQL with Comment]
│  /* trace_id=4bf92f..., request_id=req_01HXYZABC */
│  SELECT stock FROM inventory WHERE sku = 'SKU-001'
│
▼ [响应链路]
│
▼ API Gateway
├─ Response Headers:
│   x-trace-id: 4bf92f3577b34da6a3ce929d0e0e4736
│   x-request-id: req_01HXYZABC
│   traceparent: 00-4bf92f...-00f067...-01
│
▼ 前端
├─ 捕获响应头
├─ 存储到 sessionStorage
├─ 日志: { trace_id, client_request_id, event: "net.response" }
```

---

## 4. 日志查询示例

### 按 trace_id 查询完整调用链

```bash
# Elasticsearch
GET /logs/_search
{
  "query": {
    "term": { "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736" }
  },
  "sort": [{ "ts": "asc" }]
}

# Loki
{job="api"} | json | trace_id="4bf92f3577b34da6a3ce929d0e0e4736"
```

### 按 request_id 查询单次请求

```bash
# Grep
grep "req_01HXYZABC" /var/log/app/*.log
```

### 按 client_request_id 追踪用户操作

```bash
# 找到用户某次操作的所有请求
{job=~"frontend|api"} | json | client_request_id="cr_01HXYZ789"
```

---

## 5. OpenTelemetry 集成

如果使用 OpenTelemetry，推荐配置：

```yaml
opentelemetry:
  propagators:
    - tracecontext  # W3C Trace Context
    - baggage       # W3C Baggage

  auto_instrumentation:
    http:
      client: true
      server: true
    grpc:
      client: true
      server: true
    database:
      sql_commenter: true

  exporters:
    otlp:
      endpoint: "otel-collector:4317"
    jaeger:
      endpoint: "jaeger:14268"
```

---

## 6. 合规检查清单

```yaml
compliance_checklist:
  frontend:
    - "[ ] 每次用户动作生成 x-client-request-id"
    - "[ ] 请求携带已有 traceparent"
    - "[ ] 从响应头捕获 trace_id/request_id"
    - "[ ] 日志包含 client_request_id"

  gateway:
    - "[ ] 缺失 traceparent 时生成"
    - "[ ] 缺失 x-request-id 时生成"
    - "[ ] 透传所有追踪 header"
    - "[ ] 响应头包含 x-trace-id, x-request-id"
    - "[ ] 日志包含完整追踪字段"

  backend:
    - "[ ] 从请求头提取 traceparent"
    - "[ ] 创建子 span 并透传"
    - "[ ] HTTP 客户端自动透传 header"
    - "[ ] 日志必须包含 trace_id, request_id"

  database:
    - "[ ] SQL 注释包含 trace_id"
    - "[ ] 慢查询可追溯到请求"
```

---

## 版本历史

| 版本 | 日期 | 变更说明 |
|------|------|----------|
| 1.0 | 2026-01-13 | 初始版本 |
