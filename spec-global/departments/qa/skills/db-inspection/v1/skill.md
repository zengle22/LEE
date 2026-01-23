# DB Inspection Skill v1.0
# 数据库检查技能

## 概述

按用户/订单/实体主键查询数据库（只读）。
校验约束：唯一性、外键、状态机字段、时间戳。
能做"前后快照 diff"（修复前/后、请求前/后）。

## 技能标识

- **ID**: skill.test.db_inspection
- **名称**: DB Inspection
- **版本**: 1.0
- **所有者**: test-governance

## 适用 Agent

- agent.test.debug_agent

## 安全约束

```yaml
security:
  access_mode: "READ ONLY"
  forbidden_operations:
    - INSERT
    - UPDATE
    - DELETE
    - DROP
    - ALTER
    - TRUNCATE

  connection:
    use_readonly_replica: true
    user: "readonly_debug"
    max_query_time: "30s"
    max_rows: 1000

  audit:
    log_all_queries: true
    log_path: "output/debug/audit/db-queries.log"
```

---

## 1. 实体查询

### 1.1 按主键查询

```yaml
entity_query:
  by_primary_key:
    examples:
      user:
        table: "users"
        key: "id"
        query: "SELECT * FROM users WHERE id = {user_id}"

      order:
        table: "orders"
        key: "order_id"
        query: "SELECT * FROM orders WHERE order_id = {order_id}"

      product:
        table: "products"
        key: "sku"
        query: "SELECT * FROM products WHERE sku = {sku}"

  by_business_key:
    examples:
      - table: "orders"
        keys: ["user_id", "created_at"]
        query: |
          SELECT * FROM orders
          WHERE user_id = {user_id}
          AND created_at > {start_time}
          ORDER BY created_at DESC
          LIMIT 10
```

### 1.2 关联查询

```yaml
related_query:
  description: "查询相关联的数据"

  example:
    order_with_details:
      main_query: |
        SELECT * FROM orders WHERE order_id = {order_id}

      related_queries:
        - name: "order_items"
          query: |
            SELECT * FROM order_items WHERE order_id = {order_id}

        - name: "payment"
          query: |
            SELECT * FROM payments WHERE order_id = {order_id}

        - name: "shipping"
          query: |
            SELECT * FROM shipping_records WHERE order_id = {order_id}

        - name: "user"
          query: |
            SELECT * FROM users WHERE id = {user_id}
```

---

## 2. 约束校验

### 2.1 唯一性检查

```yaml
uniqueness_check:
  description: "检查唯一约束是否被违反"

  checks:
    - table: "users"
      unique_fields: ["email", "phone"]
      query: |
        SELECT email, COUNT(*) as cnt
        FROM users
        GROUP BY email
        HAVING COUNT(*) > 1

    - table: "orders"
      unique_fields: ["idempotency_key"]
      query: |
        SELECT idempotency_key, COUNT(*) as cnt
        FROM orders
        WHERE idempotency_key IS NOT NULL
        GROUP BY idempotency_key
        HAVING COUNT(*) > 1

  output:
    violations:
      - table: "users"
        field: "email"
        duplicate_value: "test@example.com"
        count: 2
        conclusion: "❌ 存在重复 email"
```

### 2.2 外键检查

```yaml
foreign_key_check:
  description: "检查外键引用是否有效"

  checks:
    - table: "order_items"
      foreign_key: "order_id"
      references: "orders.order_id"
      query: |
        SELECT oi.*
        FROM order_items oi
        LEFT JOIN orders o ON oi.order_id = o.order_id
        WHERE o.order_id IS NULL

    - table: "orders"
      foreign_key: "user_id"
      references: "users.id"
      query: |
        SELECT o.*
        FROM orders o
        LEFT JOIN users u ON o.user_id = u.id
        WHERE u.id IS NULL

  output:
    orphan_records:
      - table: "order_items"
        orphan_count: 5
        sample_ids: ["OI-001", "OI-002"]
        conclusion: "❌ 存在孤儿记录"
```

### 2.3 状态机检查

```yaml
state_machine_check:
  description: "检查状态转换是否合法"

  order_states:
    valid_transitions:
      created: [pending_payment, cancelled]
      pending_payment: [paid, cancelled, payment_timeout]
      paid: [shipped, refund_requested]
      shipped: [delivered, returned]
      delivered: [completed, refund_requested]

  check:
    query: |
      SELECT
        o.order_id,
        o.status as current_status,
        ol.from_status,
        ol.to_status,
        ol.created_at
      FROM orders o
      JOIN order_status_log ol ON o.order_id = ol.order_id
      ORDER BY ol.created_at

  output:
    invalid_transitions:
      - order_id: "ORD-123"
        from: "created"
        to: "shipped"  # 跳过了 paid
        conclusion: "❌ 非法状态转换"
```

### 2.4 时间戳检查

```yaml
timestamp_check:
  description: "检查时间戳逻辑是否正确"

  checks:
    - name: "创建时间 <= 更新时间"
      query: |
        SELECT * FROM orders
        WHERE updated_at < created_at

    - name: "支付时间 > 创建时间"
      query: |
        SELECT * FROM orders
        WHERE paid_at IS NOT NULL
        AND paid_at < created_at

    - name: "发货时间 > 支付时间"
      query: |
        SELECT * FROM orders
        WHERE shipped_at IS NOT NULL
        AND shipped_at < paid_at

  output:
    violations:
      - check: "支付时间 > 创建时间"
        count: 3
        samples:
          - order_id: "ORD-123"
            created_at: "2026-01-13 10:00:00"
            paid_at: "2026-01-13 09:00:00"
        conclusion: "❌ 时间戳逻辑错误"
```

---

## 3. 数据快照与 Diff

### 3.1 快照采集

```yaml
snapshot:
  capture:
    tables:
      - name: "orders"
        filter: "order_id = {order_id}"
      - name: "order_items"
        filter: "order_id = {order_id}"
      - name: "inventory"
        filter: "sku IN ({skus})"

    timing:
      before_operation: "snapshot_before.json"
      after_operation: "snapshot_after.json"

  output:
    path: "evidence/db/snapshots/{case_id}/"
    format: "json"
```

### 3.2 Diff 对比

```yaml
snapshot_diff:
  compare:
    before: "snapshot_before.json"
    after: "snapshot_after.json"

  diff_types:
    added:
      description: "新增的记录"
    removed:
      description: "删除的记录"
    modified:
      description: "修改的字段"

  output:
    format: |
      ## 数据变更报告

      ### orders 表
      #### 修改的记录
      | order_id | 字段 | 修改前 | 修改后 |
      |----------|------|--------|--------|
      | ORD-123 | status | created | paid |
      | ORD-123 | paid_at | null | 2026-01-13 10:30:00 |

      ### inventory 表
      #### 修改的记录
      | sku | 字段 | 修改前 | 修改后 |
      |-----|------|--------|--------|
      | SKU-001 | stock | 100 | 99 |

  example:
    diff:
      orders:
        modified:
          - id: "ORD-123"
            changes:
              status: { before: "created", after: "paid" }
              paid_at: { before: null, after: "2026-01-13 10:30:00" }

      inventory:
        modified:
          - sku: "SKU-001"
            changes:
              stock: { before: 100, after: 99 }
```

---

## 4. 数据一致性检查

```yaml
consistency_checks:
  cross_table:
    - name: "订单金额一致性"
      description: "订单总金额 = 订单项金额之和"
      query: |
        SELECT
          o.order_id,
          o.total_amount as order_total,
          SUM(oi.price * oi.quantity) as items_total
        FROM orders o
        JOIN order_items oi ON o.order_id = oi.order_id
        GROUP BY o.order_id, o.total_amount
        HAVING o.total_amount != SUM(oi.price * oi.quantity)

    - name: "库存一致性"
      description: "库存 = 初始库存 - 已售"
      query: |
        SELECT
          p.sku,
          p.initial_stock,
          p.current_stock,
          COUNT(oi.id) as sold_count,
          p.initial_stock - COUNT(oi.id) as expected_stock
        FROM products p
        LEFT JOIN order_items oi ON p.sku = oi.sku
        LEFT JOIN orders o ON oi.order_id = o.order_id AND o.status = 'completed'
        GROUP BY p.sku, p.initial_stock, p.current_stock
        HAVING p.current_stock != p.initial_stock - COUNT(oi.id)

  output:
    inconsistencies:
      - check: "订单金额一致性"
        violations: 2
        samples:
          - order_id: "ORD-123"
            order_total: 100.00
            items_total: 99.00
            difference: 1.00
```

---

## 5. 敏感数据处理

```yaml
sensitive_data:
  mask_fields:
    - field: "password"
      action: "never_select"
    - field: "phone"
      action: "mask"
      pattern: "138****8888"
    - field: "email"
      action: "mask"
      pattern: "t***@example.com"
    - field: "id_card"
      action: "mask"
      pattern: "****"
    - field: "bank_account"
      action: "mask"
      pattern: "****"

  query_rewrite:
    original: "SELECT * FROM users WHERE id = 123"
    rewritten: |
      SELECT
        id,
        CONCAT(LEFT(phone, 3), '****', RIGHT(phone, 4)) as phone,
        CONCAT(LEFT(email, 1), '***', SUBSTRING(email, LOCATE('@', email))) as email,
        -- password excluded
        created_at
      FROM users WHERE id = 123
```

---

## 6. 输出格式

```yaml
output:
  path: "evidence/db/{case_id}/"

  files:
    query_log: "queries.log"
    snapshots: "snapshots/"
    diff_report: "diff-report.md"
    constraint_check: "constraint-check.json"
    summary: "db-inspection-summary.md"

  summary_template: |
    ## 数据库检查报告

    ### 检查概览
    - 查询数: {query_count}
    - 表数: {table_count}
    - 记录数: {record_count}

    ### 约束检查
    | 检查项 | 结果 | 违规数 |
    |--------|------|--------|
    | 唯一性 | {uniqueness_result} | {uniqueness_violations} |
    | 外键 | {fk_result} | {fk_violations} |
    | 状态机 | {state_result} | {state_violations} |
    | 时间戳 | {timestamp_result} | {timestamp_violations} |

    ### 数据变更 (Diff)
    {diff_summary}

    ### 发现的问题
    {#each issues}
    - [{severity}] {description}
    {/each}
```

---

## 版本历史

| 版本 | 日期 | 变更说明 |
|------|------|----------|
| 1.0 | 2026-01-13 | 初始版本 |
