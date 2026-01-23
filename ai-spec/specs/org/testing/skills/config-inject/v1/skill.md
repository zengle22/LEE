# Config Inject Skill v1.0
# 配置注入技能 - 环境变量与配置文件管理

## 概述

Config Inject 技能负责为测试环境注入正确的配置。
支持环境变量、配置文件模板、密钥注入等多种方式。

## 技能标识

- **ID**: skill.test.config_inject
- **名称**: Config Inject
- **版本**: 1.0
- **所有者**: test-governance

## 适用 Agent

- agent.test.test_env_admin

---

## 1. 配置来源

### 1.1 支持的配置源

```yaml
config_sources:
  # 环境变量文件
  env_file:
    path: ".env.test"
    format: "dotenv"

  # YAML 配置
  yaml_file:
    path: "config/test.yaml"
    format: "yaml"

  # JSON 配置
  json_file:
    path: "config/test.json"
    format: "json"

  # 模板文件
  template:
    source: "config/app.yaml.template"
    target: "config/app.yaml"
    variables:
      from: ["env", "vault", "file"]

  # 密钥管理服务
  vault:
    provider: "hashicorp"  # hashicorp | aws-secrets | azure-keyvault
    path: "secret/test-env"
```

### 1.2 配置优先级

```yaml
priority:
  # 从低到高
  levels:
    - name: "defaults"
      source: "config/defaults.yaml"

    - name: "environment"
      source: "config/{ENV}.yaml"

    - name: "env_file"
      source: ".env.{ENV}"

    - name: "environment_variables"
      source: "process.env"

    - name: "secrets"
      source: "vault:secret/{ENV}"

  # 合并策略
  merge_strategy: "deep"  # deep | shallow | replace
```

---

## 2. 环境变量注入

### 2.1 .env 文件管理

```yaml
dotenv:
  # 生成 .env 文件
  generate:
    source: ".env.example"
    target: ".env.test"
    variables:
      # 静态值
      NODE_ENV: "test"
      LOG_LEVEL: "debug"

      # 从密钥管理获取
      DATABASE_URL: "vault:secret/test/database_url"
      API_KEY: "vault:secret/test/api_key"

      # 动态生成
      SESSION_SECRET: "generate:random:32"
      JWT_SECRET: "generate:random:64"

  # 验证必需变量
  required:
    - "DATABASE_URL"
    - "API_KEY"
    - "JWT_SECRET"

  # 可选变量
  optional:
    - "SENTRY_DSN"
    - "ANALYTICS_ID"
```

### 2.2 环境变量模板

```dotenv
# .env.example (模板)

# 应用配置
NODE_ENV=${ENV}
PORT=${PORT:-3000}
LOG_LEVEL=${LOG_LEVEL:-info}

# 数据库配置
DATABASE_URL=${DATABASE_URL}
DATABASE_POOL_SIZE=${DATABASE_POOL_SIZE:-10}

# Redis 配置
REDIS_URL=${REDIS_URL:-redis://localhost:6379}

# 认证配置
JWT_SECRET=${JWT_SECRET}
JWT_EXPIRES_IN=${JWT_EXPIRES_IN:-7d}

# 外部服务
API_KEY=${API_KEY}
WEBHOOK_URL=${WEBHOOK_URL}
```

---

## 3. 配置文件生成

### 3.1 模板渲染

```yaml
template_rendering:
  # 模板语法 (支持 Go template)
  syntax: "go-template"

  # 模板示例
  example:
    source: "config/app.yaml.tmpl"
    content: |
      server:
        host: "{{ .HOST | default \"0.0.0.0\" }}"
        port: {{ .PORT | default 8080 }}

      database:
        url: "{{ .DATABASE_URL }}"
        pool_size: {{ .DATABASE_POOL_SIZE | default 10 }}

      redis:
        url: "{{ .REDIS_URL }}"

      auth:
        jwt_secret: "{{ .JWT_SECRET }}"
        expires_in: "{{ .JWT_EXPIRES_IN | default \"7d\" }}"

      features:
        {{ range $key, $value := .FEATURES }}
        {{ $key }}: {{ $value }}
        {{ end }}

  # 变量来源
  variables:
    - source: "env"
      prefix: ""
    - source: "vault"
      path: "secret/test"
    - source: "file"
      path: "config/overrides.yaml"
```

### 3.2 多环境配置

```yaml
multi_env:
  # 环境定义
  environments:
    - name: "test"
      base: "config/base.yaml"
      overrides: "config/test.yaml"
      secrets: "vault:secret/test"

    - name: "staging"
      base: "config/base.yaml"
      overrides: "config/staging.yaml"
      secrets: "vault:secret/staging"

  # 生成命令
  generate:
    command: "envsubst < {source} > {target}"
    validate: true
```

---

## 4. 密钥管理

### 4.1 HashiCorp Vault

```yaml
vault:
  # 连接配置
  connection:
    address: "${VAULT_ADDR}"
    token_ref: "env:VAULT_TOKEN"
    namespace: "test"

  # 读取密钥
  read:
    path: "secret/data/test-env"
    keys:
      - "database_url"
      - "api_key"
      - "jwt_secret"

  # 注入方式
  inject:
    as_env: true  # 注入为环境变量
    as_file: false
    env_prefix: ""
```

### 4.2 AWS Secrets Manager

```yaml
aws_secrets:
  # 连接配置
  connection:
    region: "us-west-2"
    profile: "test-env"

  # 读取密钥
  secrets:
    - name: "test-env/database"
      keys:
        - "url"
        - "username"
        - "password"

    - name: "test-env/api-keys"
      keys:
        - "external_api_key"
```

### 4.3 本地密钥文件

```yaml
local_secrets:
  # 加密文件
  file:
    path: ".secrets.enc"
    encryption: "age"  # age | gpg | sops
    key_ref: "env:SECRETS_KEY"

  # 解密后的格式
  format: "yaml"

  # 使用方式
  inject:
    DATABASE_PASSWORD: "$.database.password"
    API_KEY: "$.api_keys.external"
```

---

## 5. 配置验证

### 5.1 验证规则

```yaml
validation:
  # 必需字段
  required:
    - name: "DATABASE_URL"
      pattern: "^postgres://.*$"
      message: "DATABASE_URL 必须是有效的 PostgreSQL 连接串"

    - name: "PORT"
      type: "integer"
      range: [1024, 65535]
      message: "PORT 必须是 1024-65535 之间的整数"

    - name: "LOG_LEVEL"
      enum: ["debug", "info", "warn", "error"]
      message: "LOG_LEVEL 必须是 debug/info/warn/error 之一"

  # 可选字段
  optional:
    - name: "SENTRY_DSN"
      pattern: "^https://.*@.*\\.ingest\\.sentry\\.io/.*$"
      default: null

  # 自定义验证
  custom:
    - name: "database_connection"
      command: "pg_isready -d ${DATABASE_URL}"
      message: "无法连接到数据库"
```

### 5.2 验证报告

```yaml
validation_report:
  status: "pass | fail"
  checked_at: "2026-01-14T10:00:00Z"

  results:
    - name: "DATABASE_URL"
      status: "pass"
      value: "postgres://****@localhost:5432/test"  # 脱敏

    - name: "PORT"
      status: "pass"
      value: "8080"

    - name: "API_KEY"
      status: "fail"
      error: "缺少必需的环境变量"

  summary:
    total: 10
    passed: 9
    failed: 1
```

---

## 6. 配置同步

### 6.1 同步到服务器

```yaml
sync:
  # 上传配置文件
  upload:
    files:
      - local: ".env.test"
        remote: "{work_dir}/.env"

      - local: "config/test.yaml"
        remote: "{work_dir}/config/config.yaml"

    # 设置权限
    permissions:
      ".env": "600"
      "config/*.yaml": "644"

  # 注入环境变量
  inject_env:
    method: "export"  # export | systemd | docker
    target: "/etc/profile.d/test-env.sh"
```

### 6.2 Docker 配置注入

```yaml
docker_inject:
  # 环境变量
  env_vars:
    from_file: ".env.test"
    additional:
      - "CONTAINER_ENV=true"

  # 配置文件挂载
  volumes:
    - source: "config/app.yaml"
      target: "/app/config/config.yaml"
      read_only: true

  # Docker Compose 配置
  compose_env_file:
    - ".env.test"
    - ".env.secrets"
```

---

## 7. 安全规则

### 7.1 敏感信息处理

```yaml
security:
  # 敏感字段识别
  sensitive_patterns:
    - "*password*"
    - "*secret*"
    - "*key*"
    - "*token*"
    - "*credential*"

  # 日志脱敏
  log_masking:
    enabled: true
    replacement: "***REDACTED***"

  # 文件权限
  file_permissions:
    ".env*": "600"
    "*.key": "600"
    "*.pem": "600"

  # 禁止行为
  forbidden:
    - "将密钥提交到版本控制"
    - "在日志中输出密钥值"
    - "通过命令行参数传递密钥"
```

### 7.2 密钥轮换

```yaml
key_rotation:
  # 检测过期密钥
  expiry_check:
    enabled: true
    warn_before_days: 30

  # 轮换流程
  rotation_steps:
    - "从密钥管理服务获取新密钥"
    - "更新配置文件"
    - "重启服务"
    - "验证服务正常"
    - "删除旧密钥"
```

---

## 8. 输出

### 8.1 配置注入报告

```yaml
inject_report:
  status: "success | failed"
  environment: "test"
  injected_at: "2026-01-14T10:00:00Z"

  files_generated:
    - path: ".env.test"
      variables: 15
      secrets: 3

    - path: "config/app.yaml"
      from_template: true

  validation:
    passed: true
    errors: []

  secrets_injected:
    - "database_url"
    - "api_key"
    - "jwt_secret"
```

---

## 版本历史

| 版本 | 日期 | 变更说明 |
|------|------|----------|
| 1.0 | 2026-01-14 | 初始版本 |
