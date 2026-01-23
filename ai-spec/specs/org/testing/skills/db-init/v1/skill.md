# Database Init Skill v1.0
# 数据库初始化技能 - 测试数据库初始化与管理

## 概述

Database Init 技能负责测试环境数据库的初始化、迁移和数据填充。
支持 PostgreSQL、MySQL、SQLite 等主流数据库。

## 技能标识

- **ID**: skill.test.db_init
- **名称**: Database Init
- **版本**: 1.0
- **所有者**: test-governance

## 适用 Agent

- agent.test.test_env_admin

---

## 1. 支持的数据库

### 1.1 PostgreSQL

```yaml
postgres:
  connection:
    host: "{db_host}"
    port: 5432
    database: "{db_name}"
    user: "{db_user}"
    password_ref: "vault:postgres_password"
    ssl_mode: "prefer"

  commands:
    # 检查连接
    ping: "pg_isready -h {host} -p {port} -U {user}"

    # 创建数据库
    create_db: "createdb -h {host} -U {user} {database}"

    # 删除数据库
    drop_db: "dropdb -h {host} -U {user} {database}"

    # 执行 SQL 文件
    exec_sql: "psql -h {host} -U {user} -d {database} -f {sql_file}"

    # 备份
    backup: "pg_dump -h {host} -U {user} {database} > {backup_file}"

    # 恢复
    restore: "psql -h {host} -U {user} {database} < {backup_file}"
```

### 1.2 MySQL

```yaml
mysql:
  connection:
    host: "{db_host}"
    port: 3306
    database: "{db_name}"
    user: "{db_user}"
    password_ref: "vault:mysql_password"

  commands:
    ping: "mysqladmin ping -h {host} -u {user} -p{password}"
    create_db: "mysql -h {host} -u {user} -p{password} -e 'CREATE DATABASE {database}'"
    drop_db: "mysql -h {host} -u {user} -p{password} -e 'DROP DATABASE {database}'"
    exec_sql: "mysql -h {host} -u {user} -p{password} {database} < {sql_file}"
    backup: "mysqldump -h {host} -u {user} -p{password} {database} > {backup_file}"
    restore: "mysql -h {host} -u {user} -p{password} {database} < {backup_file}"
```

### 1.3 SQLite

```yaml
sqlite:
  connection:
    file: "{db_path}"

  commands:
    create_db: "touch {file}"
    exec_sql: "sqlite3 {file} < {sql_file}"
    backup: "cp {file} {backup_file}"
    restore: "cp {backup_file} {file}"
```

---

## 2. 初始化流程

### 2.1 完整初始化

```yaml
init_flow:
  phases:
    - id: pre_check
      name: "前置检查"
      steps:
        - "验证数据库连接"
        - "检查数据库是否存在"
        - "检查迁移文件完整性"

    - id: backup
      name: "备份阶段"
      condition: "database_exists"
      steps:
        - "创建当前状态备份"
        - "记录备份位置"

    - id: reset
      name: "重置阶段"
      condition: "full_reset_requested"
      steps:
        - "删除现有数据库"
        - "创建新数据库"

    - id: migrate
      name: "迁移阶段"
      steps:
        - "执行数据库迁移"
        - "验证迁移成功"

    - id: seed
      name: "数据填充阶段"
      condition: "seed_requested"
      steps:
        - "执行种子数据脚本"
        - "验证数据完整性"

    - id: verify
      name: "验证阶段"
      steps:
        - "检查表结构"
        - "验证约束存在"
        - "确认索引创建"
```

### 2.2 快速重置

```yaml
quick_reset:
  description: "保留结构，只清空数据"
  steps:
    - step: "禁用外键检查"
      postgres: "SET session_replication_role = replica;"
      mysql: "SET FOREIGN_KEY_CHECKS = 0;"

    - step: "清空所有表"
      command: "TRUNCATE {table_name} CASCADE;"
      for_each: "tables"

    - step: "启用外键检查"
      postgres: "SET session_replication_role = DEFAULT;"
      mysql: "SET FOREIGN_KEY_CHECKS = 1;"

    - step: "重置序列"
      postgres: "ALTER SEQUENCE {sequence_name} RESTART WITH 1;"

    - step: "填充种子数据"
      condition: "seed_requested"
```

---

## 3. 迁移管理

### 3.1 迁移工具集成

```yaml
migration_tools:
  # Go - golang-migrate
  golang_migrate:
    command: "migrate -path {migrations_path} -database '{db_url}' up"
    status: "migrate -path {migrations_path} -database '{db_url}' version"
    rollback: "migrate -path {migrations_path} -database '{db_url}' down 1"

  # Node.js - Knex
  knex:
    command: "npx knex migrate:latest --env test"
    status: "npx knex migrate:status --env test"
    rollback: "npx knex migrate:rollback --env test"

  # Python - Alembic
  alembic:
    command: "alembic upgrade head"
    status: "alembic current"
    rollback: "alembic downgrade -1"

  # Ruby - Rails
  rails:
    command: "RAILS_ENV=test rails db:migrate"
    status: "RAILS_ENV=test rails db:migrate:status"
    rollback: "RAILS_ENV=test rails db:rollback"

  # SQL 文件
  raw_sql:
    command: "{db_client} < {sql_file}"
    files_pattern: "migrations/*.sql"
    order: "numeric"  # 按文件名数字排序
```

### 3.2 迁移验证

```yaml
migration_verification:
  checks:
    - name: "表存在检查"
      query: |
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = '{table}'
      expected: "{table}"

    - name: "列存在检查"
      query: |
        SELECT column_name FROM information_schema.columns
        WHERE table_name = '{table}' AND column_name = '{column}'
      expected: "{column}"

    - name: "索引存在检查"
      query: |
        SELECT indexname FROM pg_indexes WHERE indexname = '{index}'
      expected: "{index}"
```

---

## 4. 种子数据

### 4.1 种子数据配置

```yaml
seed_data:
  # 种子文件路径
  files:
    - path: "seeds/01_users.sql"
      description: "基础用户数据"
      required: true

    - path: "seeds/02_products.sql"
      description: "产品数据"
      required: true

    - path: "seeds/03_test_data.sql"
      description: "测试专用数据"
      required: false

  # 种子数据格式
  formats:
    - sql
    - json
    - csv

  # JSON 种子示例
  json_seed:
    file: "seeds/users.json"
    table: "users"
    mapping:
      id: "id"
      name: "name"
      email: "email"
```

### 4.2 动态种子数据

```yaml
dynamic_seed:
  # 生成测试用户
  test_users:
    count: 10
    template:
      name: "Test User {i}"
      email: "testuser{i}@example.com"
      password: "{hashed_password}"
      created_at: "{now}"

  # 生成测试数据
  test_orders:
    count: 100
    template:
      user_id: "{random_user_id}"
      product_id: "{random_product_id}"
      amount: "{random_int:1:10}"
      status: "{random_choice:pending,completed,cancelled}"
```

---

## 5. 备份与恢复

### 5.1 备份策略

```yaml
backup:
  # 部署前备份
  pre_deploy:
    enabled: true
    path: "backups/pre_deploy_{timestamp}.sql"
    retention: 5  # 保留最近 5 个

  # 定时备份
  scheduled:
    enabled: false
    cron: "0 2 * * *"  # 每天凌晨 2 点
    path: "backups/daily_{date}.sql"
    retention_days: 7

  # 备份命令
  command:
    postgres: "pg_dump -Fc {database} > {path}"
    mysql: "mysqldump --single-transaction {database} > {path}"
```

### 5.2 恢复流程

```yaml
restore:
  steps:
    - step: "停止应用服务"
      command: "systemctl stop app"

    - step: "删除现有数据库"
      command: "dropdb {database}"

    - step: "创建空数据库"
      command: "createdb {database}"

    - step: "恢复数据"
      command: "pg_restore -d {database} {backup_file}"

    - step: "启动应用服务"
      command: "systemctl start app"

    - step: "验证恢复"
      action: "health_check"
```

---

## 6. 安全规则

### 6.1 凭证管理

```yaml
security:
  credentials:
    # 禁止明文密码
    forbidden:
      - "在命令行参数中传递密码"
      - "在日志中记录密码"
      - "在代码中硬编码密码"

    # 推荐方式
    recommended:
      - "使用环境变量: PGPASSWORD"
      - "使用 .pgpass 文件"
      - "使用密钥管理服务"
```

### 6.2 数据脱敏

```yaml
data_masking:
  # 生产数据脱敏规则
  rules:
    - column: "email"
      method: "hash"
      pattern: "{hash}@example.com"

    - column: "phone"
      method: "mask"
      pattern: "***-****-{last4}"

    - column: "password"
      method: "replace"
      value: "{test_password_hash}"

    - column: "credit_card"
      method: "remove"
```

---

## 7. 错误处理

```yaml
error_handling:
  connection_failed:
    message: "数据库连接失败"
    action: "检查网络和凭证"
    retry: 3

  migration_failed:
    message: "迁移执行失败"
    action: "回滚到上一个版本"
    rollback: true

  seed_failed:
    message: "种子数据加载失败"
    action: "检查数据完整性约束"
    continue: false

  backup_failed:
    message: "备份失败"
    action: "检查磁盘空间和权限"
    block_deploy: true
```

---

## 8. 输出

### 8.1 初始化报告

```yaml
init_report:
  status: "success | failed"
  database: "{database}"
  started_at: "2026-01-14T10:00:00Z"
  completed_at: "2026-01-14T10:01:30Z"

  migrations:
    applied: 15
    pending: 0
    failed: 0

  seed_data:
    tables_seeded: 5
    rows_inserted: 1000

  backup:
    created: true
    path: "backups/pre_deploy_20260114.sql"
```

---

## 版本历史

| 版本 | 日期 | 变更说明 |
|------|------|----------|
| 1.0 | 2026-01-14 | 初始版本 |
