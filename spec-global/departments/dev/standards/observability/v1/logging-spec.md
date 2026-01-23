# Logging & Observability Specification v1.0
# 日志与可观测性规范

## 概述

本规范定义统一的日志体系标准，目标是：
- **让 Bug Fix Agent / E2E Agent / Orchestrator 能稳定串起"前端 → 网关 → 服务 → DB"**
- 让"可观测"成为硬约束，避免以后每次排障都靠猜（根源性预防）

## 规范标识

- **ID**: standard.dev.observability.logging
- **名称**: Logging & Observability Spec
- **版本**: 1.0
- **所有者**: dev-governance
- **适用范围**: 研发部所有 Agent

---

## 1. 统一目标与原则

### 1.1 目标

1. **一条用户操作能被完整追踪**：UI 事件 → API 请求 → 服务内部调用 → DB 读写
2. **任何报错都有"可复现证据链"**：request_id / trace_id / error_code / stack / 关键上下文
3. **机器可判定**：日志是结构化 JSON，不依赖人读自然语言
4. **最小侵入**：先打通主链路与关键字段，再逐步丰富

### 1.2 原则

| 原则 | 描述 |
|------|------|
| **结构化优先** | JSON 日志（强制） |
| **关联优先** | 先保证 id/上下文贯穿，再谈内容详尽 |
| **分层一致** | 前端/网关/服务/DB 的字段命名一致 |
| **安全默认** | 敏感字段禁止入日志（默认脱敏） |

---

## 2. ID 体系与贯穿规则（核心）

### 2.1 必须的 4 个 ID

| ID | 说明 | 生成位置 |
|----|------|----------|
| `trace_id` | 端到端调用链（推荐 W3C Trace Context） | 网关/SDK |
| `span_id` | 链路内的一个片段（用于分布式追踪） | 各服务 |
| `request_id` | 一次 HTTP 请求 | 网关生成或透传 |
| `session_id` / `user_id` | 用户维度关联 | 前端/认证服务 |

### 2.2 生成与透传规则

```yaml
propagation_rules:
  frontend:
    generate:
      - x-client-request-id  # 每次用户触发动作生成一次
    capture:
      - trace_id  # 从响应头获取并缓存
      - request_id

  gateway:
    generate:
      - trace_id  # 如不存在则生成
      - request_id  # 如不存在则生成
    propagate:
      - traceparent  # W3C Trace Context
      - x-request-id
      - x-client-request-id
    response_headers:
      - x-trace-id
      - x-request-id

  service:
    propagate:
      - traceparent
      - x-request-id
      - x-client-request-id
    mandatory_log_fields:
      - trace_id
      - request_id  # 至少其一不能丢

  database:
    comment_injection:
      - trace_id  # 注入 SQL 注释
      - request_id
```

### 2.3 Header 透传契约

参见 [propagation.md](./propagation.md)

---

## 3. 结构化日志字段契约

### 3.1 必填字段（所有层必须）

```json
{
  "ts": "2026-01-13T13:21:09.231Z",
  "level": "INFO",
  "service": "api-gateway",
  "env": "test",
  "version": "v0.8.3-rc2",
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
  "span_id": "00f067aa0ba902b7",
  "request_id": "req_01HXYZ...",
  "event": "http.request",
  "msg": "optional human summary"
}
```

### 3.2 推荐字段（用于排障/聚合/统计）

| 字段 | 类型 | 说明 |
|------|------|------|
| `route` | string | API 路由 |
| `method` | string | HTTP 方法 |
| `status_code` | integer | HTTP 状态码 |
| `latency_ms` | number | 延迟毫秒 |
| `client_platform` | string | web/weapp/ios/android |
| `client_version` | string | 客户端版本 |
| `user_id_hash` | string | 用户 ID 哈希（不要明文） |
| `session_id` | string | 会话 ID |
| `ip_hash` | string | IP 地址哈希 |
| `tags` | array | 快速过滤标签，如 `["core_flow","payment"]` |
| `sampled` | boolean | 是否采样 |

### 3.3 错误对象规范（强制统一）

```json
{
  "error": {
    "code": "AUTH_TOKEN_EXPIRED",
    "type": "BusinessError",
    "message": "token expired",
    "stack": "stack trace here (server only)",
    "cause": "optional root cause",
    "retryable": false
  }
}
```

**关键约束**：
- `error.code` **必须稳定、可枚举**（给 Gate/告警/回归聚类用）
- 参见 [error-codes.yaml](./error-codes.yaml)

### 3.4 JSON Schema

完整 Schema 参见 [log-schema.json](./log-schema.json)

---

## 4. 分层规范

### 4.1 前端（Web/小程序）日志规范

#### 4.1.1 必须记录的事件类型

| event | 说明 |
|-------|------|
| `ui.action` | 用户动作（点击/提交/导航） |
| `ui.state` | 关键 UI 状态变化（loading、empty、error-banner） |
| `net.request` | 网络请求发送 |
| `net.response` | 网络请求响应 |
| `ui.error` | 未捕获异常/资源加载失败/白屏 |

#### 4.1.2 前端日志必须带的字段

- `client_request_id`（前端生成）
- `trace_id`（从响应头拿到并缓存）
- `page` / `component`（定位 UI）
- `selector` / `data-testid`（E2E 可对齐）

#### 4.1.3 示例

```json
{
  "ts": "2026-01-13T10:30:45.100Z",
  "level": "INFO",
  "service": "frontend",
  "event": "ui.action",
  "client_request_id": "cr_01HXYZ...",
  "page": "dashboard",
  "action": "click",
  "target": "data-testid=btn-submit",
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
  "request_id": "req_01HXYZ..."
}
```

#### 4.1.4 前端错误捕获要求

- 全局异常捕获（JS error + promise rejection）
- 记录：`error.code`（如果能映射） + `stack`
- 上报到后端统一日志入口或 Sentry 类工具

---

### 4.2 网关（API Gateway / BFF）日志规范

#### 4.2.1 必须输出的日志类型

| event | 说明 |
|-------|------|
| `http.request` | 入站请求摘要 |
| `http.response` | 出站响应摘要 |
| `auth.decision` | 鉴权/限流/风控决策 |

#### 4.2.2 网关是 request_id 的守门人

```yaml
gateway_responsibilities:
  - 没有 x-request-id → 网关生成
  - 透传并写入响应头: x-request-id, traceparent
  - 记录完整的入站出站日志
```

---

### 4.3 后端服务日志规范

#### 4.3.1 事件命名规则

| event | 说明 |
|-------|------|
| `http.handler` | 入口 handler |
| `svc.call` | 服务内部关键函数 |
| `rpc.client` / `rpc.server` | 服务间调用 |
| `db.query` | DB 查询摘要 |
| `cache.get` / `cache.set` | 缓存操作摘要 |
| `domain.event` | 领域事件（如 `plan.created`, `run.logged`） |

#### 4.3.2 必须带的业务上下文字段

| 字段 | 说明 |
|------|------|
| `entity_type` | plan/run/user/session |
| `entity_id_hash` | 实体 ID 哈希 |
| `operation` | create/update/delete/read |
| `result` | success/fail |

---

### 4.4 数据库（DB）日志/审计规范

#### 4.4.1 应用侧 db.query 摘要（推荐）

```json
{
  "event": "db.query",
  "db.system": "postgres",
  "db.operation": "update",
  "db.table": "training_plan",
  "latency_ms": 18,
  "rows": 1,
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
  "request_id": "req_01HXYZ..."
}
```

#### 4.4.2 关键表业务审计日志（强烈推荐）

对核心状态机表（订单/计划/支付/权限）记录：
- 谁改的（user_id_hash / service）
- 从什么状态到什么状态
- 变更前后摘要（脱敏）

---

## 5. 日志级别、采样与成本控制

### 5.1 日志级别定义（统一口径）

| Level | 说明 | 采样 |
|-------|------|------|
| DEBUG | 开发调试，默认不进生产 | 仅 dev/test |
| INFO | 关键事件、生命周期节点 | 可采样 |
| WARN | 可恢复异常、降级、重试 | 全量 |
| ERROR | 业务失败/不可恢复错误 | 全量 |
| FATAL | 进程崩溃/不可用 | 全量 + 告警 |

### 5.2 采样策略建议

```yaml
sampling:
  ERROR: 100%  # 不采样
  WARN: 100%   # 不采样
  INFO:
    core_flow: 100%
    non_core: 10%
  DEBUG:
    dev: 100%
    test: 100%
    staging: 10%
    production: 0%
```

---

## 6. 脱敏与安全（必须遵守）

### 6.1 禁止写入日志的字段（黑名单）

```yaml
blacklist:
  - password
  - token
  - secret
  - cookie
  - private_key
  - id_card
  - bank_account
  - phone  # 明文
  - email  # 明文
  - address  # 精确地址
```

### 6.2 脱敏规则

| 字段类型 | 脱敏方式 | 示例 |
|----------|----------|------|
| phone | 中间4位掩码 | 138****8888 |
| email | 首尾保留 | t***@example.com |
| id_card | 全掩码 | **** |
| ip | 哈希 | sha256(ip) |
| user_id | 哈希 | sha256(user_id) |

### 6.3 两层保护

1. **日志 SDK 层面拦截/掩码**（最可靠）
2. **log sink 层面再做一次过滤**（兜底）

---

## 7. 与 Bug Contract / Debug Agent 对齐

### 7.1 Bug Contract 必填证据字段

Debug Agent 和 Bug Contract 需要从日志体系获取：

```yaml
required_evidence_fields:
  - trace_id
  - request_id
  - client_request_id
  - error.code
  - service
  - version
  - env
  - ts
```

### 7.2 对齐流程

```
Bug 发现 → 提取 trace_id → 日志服务查询 → 完整调用链 → 根因分析
```

---

## 8. Agent 遵守要求

### 8.1 必须遵守的 Agent 列表

| 类型 | Agent | 职责 |
|------|-------|------|
| **架构师** | backend-architect | 设计时考虑日志架构 |
| **架构师** | frontend-architect | 设计前端日志方案 |
| **架构师** | tech-lead | 审查日志规范遵守 |
| **开发者** | go-backend-engineer | 实现日志输出 |
| **开发者** | database-engineer | 实现 DB 审计日志 |
| **开发者** | uniapp-frontend-engineer | 实现前端日志 |
| **开发者** | ai-engineer | AI 服务日志 |
| **开发者** | devops-engineer | 日志基础设施 |
| **开发者** | implementation-executor | 遵守日志规范编码 |
| **审查者** | code-reviewer | 审查日志规范合规 |
| **审查者** | acceptance-reviewer | 验收日志完整性 |
| **审查者** | secops | 安全审计日志 |
| **审查者** | delivery-gate | 日志门禁检查 |

### 8.2 Agent 合规检查清单

```yaml
compliance_checklist:
  architects:
    - "[ ] 日志架构设计包含 ID 贯穿方案"
    - "[ ] 日志采集和存储方案明确"
    - "[ ] 安全脱敏策略已设计"

  developers:
    - "[ ] 代码使用结构化日志"
    - "[ ] 所有日志包含 trace_id/request_id"
    - "[ ] 错误使用统一 error.code"
    - "[ ] 敏感字段已脱敏"
    - "[ ] 关键操作有审计日志"

  reviewers:
    - "[ ] 审查代码日志规范合规"
    - "[ ] 验证 ID 贯穿完整"
    - "[ ] 检查敏感信息泄露"
    - "[ ] 确认错误码规范"
```

---

## 9. 最小落地清单

### 第 1 周（最小可用）

- [ ] 全链路透传：`trace_id` / `request_id`
- [ ] 所有后端日志结构化 JSON + 必填字段
- [ ] 网关输出请求/响应摘要
- [ ] 前端记录 `client_request_id` + 网络失败日志
- [ ] 统一 `error.code`（先从 20 个核心错误开始）

### 第 2~3 周（明显提效）

- [ ] 增加 `db.query` 摘要日志
- [ ] 引入基本 tracing（OpenTelemetry 推荐）
- [ ] Bug Contract 证据字段自动补齐

---

## 10. 相关文件

| 文件 | 说明 |
|------|------|
| [log-schema.json](./log-schema.json) | 日志 JSON Schema（CI 校验用） |
| [error-codes.yaml](./error-codes.yaml) | 错误码枚举 |
| [propagation.md](./propagation.md) | Header 透传规则 |

---

## 版本历史

| 版本 | 日期 | 变更说明 |
|------|------|----------|
| 1.0 | 2026-01-13 | 初始版本 |
