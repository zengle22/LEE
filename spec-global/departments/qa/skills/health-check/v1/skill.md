# Health Check Skill v1.0
# 健康检查技能 - 服务可用性验证

## 概述

Health Check 技能负责验证测试环境中各服务的可用性和健康状态。
支持 HTTP、TCP、命令执行等多种检查方式。

## 技能标识

- **ID**: skill.test.health_check
- **名称**: Health Check
- **版本**: 1.0
- **所有者**: test-governance

## 适用 Agent

- agent.test.test_env_admin
- agent.test.e2e_test_executor
- agent.test.smoke_test_executor

---

## 1. 检查类型

### 1.1 HTTP 健康检查

```yaml
http_check:
  # 基础配置
  config:
    url: "http://{host}:{port}/health"
    method: "GET"
    headers:
      Authorization: "Bearer {token}"
      Content-Type: "application/json"

  # 预期结果
  expected:
    status_codes: [200, 204]
    body_contains: "ok"
    body_json:
      path: "$.status"
      value: "healthy"

  # 超时和重试
  timeout: 10
  retries: 3
  retry_interval: 5

  # 检查结果
  on_success:
    status: "healthy"
    message: "服务正常响应"

  on_failure:
    status: "unhealthy"
    message: "服务无响应或返回错误"
```

### 1.2 TCP 端口检查

```yaml
tcp_check:
  config:
    host: "{host}"
    port: "{port}"
    timeout: 5

  # 常见端口
  common_ports:
    http: 80
    https: 443
    postgres: 5432
    mysql: 3306
    redis: 6379
    mongodb: 27017
    elasticsearch: 9200

  # 检查命令
  commands:
    linux: "nc -zv {host} {port}"
    fallback: "timeout 5 bash -c 'echo > /dev/tcp/{host}/{port}'"
```

### 1.3 命令执行检查

```yaml
command_check:
  # 数据库连接检查
  postgres:
    command: "pg_isready -h {host} -p {port} -U {user}"
    expected_output: "accepting connections"
    expected_exit_code: 0

  mysql:
    command: "mysqladmin ping -h {host} -u {user} -p{password}"
    expected_output: "mysqld is alive"

  redis:
    command: "redis-cli -h {host} -p {port} ping"
    expected_output: "PONG"

  mongodb:
    command: "mongosh --host {host} --port {port} --eval 'db.runCommand({ping: 1})'"
    expected_output: "ok"

  # 自定义命令
  custom:
    command: "{health_command}"
    expected_exit_code: 0
    timeout: 30
```

### 1.4 Docker 容器健康检查

```yaml
docker_check:
  # 容器状态检查
  container_status:
    command: "docker inspect --format='{{.State.Status}}' {container_name}"
    expected: "running"

  # 容器健康状态 (需要 HEALTHCHECK 指令)
  container_health:
    command: "docker inspect --format='{{.State.Health.Status}}' {container_name}"
    expected: "healthy"

  # 容器日志检查
  log_check:
    command: "docker logs --tail 50 {container_name} 2>&1"
    not_contains:
      - "error"
      - "fatal"
      - "panic"
```

---

## 2. 服务检查配置

### 2.1 常见服务模板

```yaml
service_templates:
  # 后端 API 服务
  backend_api:
    type: "http"
    endpoints:
      - path: "/health"
        expected_status: 200
      - path: "/api/v1/status"
        expected_status: 200
    critical: true

  # 前端服务
  frontend:
    type: "http"
    endpoints:
      - path: "/"
        expected_status: 200
      - path: "/static/js/main.js"
        expected_status: 200
    critical: true

  # PostgreSQL 数据库
  postgres:
    type: "command"
    check: "pg_isready -h {host} -p 5432"
    critical: true

  # Redis 缓存
  redis:
    type: "command"
    check: "redis-cli -h {host} ping"
    critical: false

  # Nginx 反向代理
  nginx:
    type: "tcp"
    ports: [80, 443]
    critical: true
```

### 2.2 检查集合

```yaml
health_check_suite:
  name: "测试环境完整性检查"
  services:
    - name: "backend"
      type: "http"
      url: "http://localhost:8080/health"
      critical: true

    - name: "frontend"
      type: "http"
      url: "http://localhost:3000"
      critical: true

    - name: "database"
      type: "tcp"
      host: "localhost"
      port: 5432
      critical: true

    - name: "redis"
      type: "tcp"
      host: "localhost"
      port: 6379
      critical: false

  # 检查顺序 (依赖关系)
  order:
    - "database"   # 先检查数据库
    - "redis"      # 再检查缓存
    - "backend"    # 然后检查后端
    - "frontend"   # 最后检查前端
```

---

## 3. 执行流程

### 3.1 检查流程

```yaml
execution_flow:
  phases:
    - id: prepare
      name: "准备阶段"
      steps:
        - "加载服务配置"
        - "解析检查参数"
        - "验证网络连通性"

    - id: check
      name: "检查阶段"
      steps:
        - "按顺序执行服务检查"
        - "记录每个服务状态"
        - "失败服务触发重试"

    - id: report
      name: "报告阶段"
      steps:
        - "汇总检查结果"
        - "生成健康报告"
        - "触发告警 (如有失败)"
```

### 3.2 重试策略

```yaml
retry_strategy:
  # 默认重试配置
  default:
    max_retries: 3
    retry_interval: 5  # 秒
    backoff: "linear"  # linear | exponential

  # 指数退避
  exponential:
    initial_interval: 1
    multiplier: 2
    max_interval: 30

  # 重试条件
  retry_on:
    - "timeout"
    - "connection_refused"
    - "status_5xx"

  no_retry_on:
    - "status_4xx"
    - "invalid_response"
```

---

## 4. 输出报告

### 4.1 健康状态报告

```yaml
health_report:
  # 整体状态
  overall:
    status: "healthy | degraded | unhealthy"
    checked_at: "2026-01-14T10:00:00Z"
    duration_ms: 1500

  # 各服务状态
  services:
    - name: "backend"
      status: "healthy"
      response_time_ms: 45
      last_check: "2026-01-14T10:00:00Z"
      details:
        url: "http://localhost:8080/health"
        status_code: 200
        body: '{"status":"ok"}'

    - name: "database"
      status: "healthy"
      response_time_ms: 12
      last_check: "2026-01-14T10:00:00Z"
      details:
        connection: "established"
        version: "PostgreSQL 15.4"

    - name: "redis"
      status: "unhealthy"
      response_time_ms: null
      last_check: "2026-01-14T10:00:00Z"
      error: "Connection refused"
      retries: 3

  # 摘要
  summary:
    total: 4
    healthy: 3
    unhealthy: 1
    critical_failed: 0
```

### 4.2 状态定义

```yaml
status_definitions:
  healthy:
    description: "所有关键服务正常"
    criteria: "all critical services pass"
    action: "可以继续测试"

  degraded:
    description: "部分非关键服务异常"
    criteria: "some non-critical services fail"
    action: "警告，可以继续但功能受限"

  unhealthy:
    description: "关键服务异常"
    criteria: "any critical service fails"
    action: "阻塞，需要修复后继续"
```

---

## 5. 告警配置

### 5.1 告警规则

```yaml
alerts:
  rules:
    - name: "关键服务失败"
      condition: "critical_service_failed"
      severity: "critical"
      message: "关键服务 {service_name} 健康检查失败: {error}"

    - name: "服务响应慢"
      condition: "response_time > 5000ms"
      severity: "warning"
      message: "服务 {service_name} 响应时间过长: {response_time}ms"

    - name: "连续失败"
      condition: "consecutive_failures >= 3"
      severity: "critical"
      message: "服务 {service_name} 连续 {count} 次健康检查失败"
```

### 5.2 通知渠道

```yaml
notification:
  channels:
    - type: "log"
      level: "all"

    - type: "webhook"
      url: "{webhook_url}"
      events: ["critical", "recovery"]
      format: |
        {
          "service": "{service_name}",
          "status": "{status}",
          "message": "{message}",
          "timestamp": "{timestamp}"
        }
```

---

## 6. 持续监控

### 6.1 轮询配置

```yaml
continuous_monitoring:
  enabled: true
  interval: 30  # 秒
  services:
    - name: "backend"
      interval: 15  # 覆盖默认间隔
    - name: "database"
      interval: 60

  # 报告触发
  report_on:
    - "status_change"
    - "every_5_minutes"
```

### 6.2 指标采集

```yaml
metrics:
  # 响应时间
  response_time:
    type: "histogram"
    buckets: [10, 50, 100, 500, 1000, 5000]

  # 成功率
  success_rate:
    type: "gauge"
    window: "5m"

  # 检查次数
  check_count:
    type: "counter"
    labels: ["service", "status"]
```

---

## 7. 最佳实践

### 7.1 检查设计

- 健康端点应快速响应 (< 1s)
- 避免在健康检查中执行重操作
- 区分存活检查 (liveness) 和就绪检查 (readiness)
- 返回详细的健康信息便于诊断

### 7.2 超时配置

- HTTP 检查: 5-10 秒
- TCP 检查: 3-5 秒
- 数据库检查: 5-10 秒
- 总检查超时: 60 秒

### 7.3 失败处理

- 关键服务失败应立即告警
- 提供详细的错误信息
- 记录失败历史便于分析
- 支持手动重试

---

## 版本历史

| 版本 | 日期 | 变更说明 |
|------|------|----------|
| 1.0 | 2026-01-14 | 初始版本 |
