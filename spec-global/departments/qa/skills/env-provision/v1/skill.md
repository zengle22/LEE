# Env Provision Skill v1.0
# 测试环境准备技能

## 概述

测试环境准备技能负责拉起测试环境、注入配置、准备测试账号和数据。
确保 E2E 测试执行前环境处于可测试状态。

## 技能标识

- **ID**: skill.test.env_provision
- **名称**: Env Provision
- **版本**: 1.0
- **所有者**: test-governance

## 适用 Agent

- agent.test.e2e_test_executor
- agent.test.smoke_test_executor
- agent.test.system_test_executor

---

## 1. 核心能力

### 1.1 环境健康检查

```yaml
health_check:
  endpoints:
    - path: "/health"
      expected_status: 200
      timeout_ms: 5000

    - path: "/api/status"
      expected_status: 200
      expected_body:
        status: "ok"

  dependencies:
    - name: database
      check: "SELECT 1"
      timeout_ms: 3000

    - name: redis
      check: "PING"
      timeout_ms: 1000

    - name: external_api
      check: "GET /health"
      timeout_ms: 5000
```

### 1.2 版本验证

```yaml
version_check:
  method: "GET /api/version"
  expected:
    version: "$EXPECTED_VERSION"
    commit: "$EXPECTED_COMMIT"

  on_mismatch:
    action: fail
    message: "部署版本与提测版本不匹配"
```

### 1.3 测试账号准备

```yaml
test_accounts:
  strategy: "create_or_reuse"

  accounts:
    - role: admin
      username: "test_admin@example.com"
      password: "${TEST_ADMIN_PASSWORD}"
      permissions: ["all"]

    - role: user
      username: "test_user@example.com"
      password: "${TEST_USER_PASSWORD}"
      permissions: ["read", "write"]

    - role: guest
      username: "test_guest@example.com"
      password: "${TEST_GUEST_PASSWORD}"
      permissions: ["read"]

  cleanup:
    after_suite: true
    preserve_on_failure: true
```

### 1.4 测试数据准备

```yaml
test_data:
  fixtures:
    - name: "基础商品数据"
      source: "fixtures/products.json"
      target: "database"
      cleanup: after_suite

    - name: "订单历史数据"
      source: "fixtures/orders.json"
      target: "database"
      cleanup: after_suite

  generators:
    - name: "随机用户"
      factory: "user_factory"
      count: 10

  isolation:
    enabled: true
    strategy: "prefix"  # 用前缀隔离测试数据
    prefix: "E2E_TEST_"
```

---

## 2. 环境类型支持

### 2.1 本地开发环境

```yaml
local:
  base_url: "http://localhost:3000"
  api_url: "http://localhost:8080"

  setup:
    - "docker-compose up -d"
    - "wait_for_healthy localhost:8080"

  teardown:
    - "docker-compose down"
```

### 2.2 测试环境

```yaml
test:
  base_url: "https://test.example.com"
  api_url: "https://api.test.example.com"

  credentials:
    source: "vault"
    path: "secret/test/credentials"

  deployment:
    method: "kubernetes"
    namespace: "test"
    version_check: true
```

### 2.3 预发布环境

```yaml
staging:
  base_url: "https://staging.example.com"
  api_url: "https://api.staging.example.com"

  credentials:
    source: "vault"
    path: "secret/staging/credentials"

  restrictions:
    - "不允许大批量数据操作"
    - "不允许删除生产同步数据"
```

---

## 3. 输出

### 3.1 环境状态

```yaml
env_status:
  ready: true
  base_url: "https://test.example.com"
  api_url: "https://api.test.example.com"
  version: "v1.0.0-rc2"
  commit: "abc123"

  health:
    api: healthy
    database: healthy
    cache: healthy

  accounts:
    - role: admin
      username: "test_admin@example.com"
      token: "${SESSION_TOKEN}"
    - role: user
      username: "test_user@example.com"
      token: "${SESSION_TOKEN}"

  data:
    products_loaded: 50
    orders_loaded: 100
    users_created: 10

  provisioned_at: "2026-01-13T10:00:00Z"
```

---

## 4. 错误处理

```yaml
error_handling:
  health_check_failed:
    retry: 3
    backoff_ms: 5000
    on_exhaust: fail_with_report

  version_mismatch:
    action: fail_immediately
    notify: [development, devops]

  data_preparation_failed:
    action: cleanup_and_fail
    preserve_logs: true

  timeout:
    total_timeout_ms: 300000  # 5 minutes
    on_timeout: fail_with_status
```

---

## 5. 最佳实践

### 5.1 环境隔离

- 使用前缀区分测试数据
- 每个测试套件使用独立的测试账号
- 测试后清理创建的数据

### 5.2 可靠性

- 健康检查要有重试机制
- 版本检查要严格
- 超时要合理设置

### 5.3 可观测性

- 记录环境准备的详细日志
- 输出可用的环境状态
- 失败时保留诊断信息

---

## 版本历史

| 版本 | 日期 | 变更说明 |
|------|------|----------|
| 1.0 | 2026-01-13 | 初始版本 |
