# Root Cause Synthesis Skill v1.0
# 根因归因引擎技能

## 概述

将 UI 现象 + API 请求 + 后端日志 + DB 结果串成一条因果链。
输出：根因假设、验证步骤、修复策略、潜在回归风险点。

## 技能标识

- **ID**: skill.test.root_cause_synthesis
- **名称**: Root Cause Synthesis
- **版本**: 1.0
- **所有者**: test-governance

## 适用 Agent

- agent.test.debug_agent

---

## 1. 证据关联

### 1.1 时序对齐

```yaml
timeline_alignment:
  description: "将所有证据按时间戳对齐，构建事件序列"

  sources:
    - frontend_console
    - frontend_network
    - backend_logs
    - db_operations

  alignment:
    normalize_timezone: true
    tolerance_ms: 100  # 时间对齐容差

  output:
    timeline:
      - timestamp: "2026-01-13T10:30:45.100Z"
        source: "frontend"
        event: "User clicks checkout button"

      - timestamp: "2026-01-13T10:30:45.150Z"
        source: "network"
        event: "POST /api/orders sent"

      - timestamp: "2026-01-13T10:30:45.200Z"
        source: "backend"
        event: "OrderService.createOrder() started"

      - timestamp: "2026-01-13T10:30:45.210Z"
        source: "backend"
        event: "Calling InventoryService.checkStock()"

      - timestamp: "2026-01-13T10:30:48.710Z"
        source: "backend"
        event: "TimeoutException at InventoryService"

      - timestamp: "2026-01-13T10:30:48.720Z"
        source: "network"
        event: "Response 500 received"

      - timestamp: "2026-01-13T10:30:48.730Z"
        source: "frontend"
        event: "Error displayed: 订单创建失败"
```

### 1.2 因果链构建

```yaml
causal_chain:
  description: "从证据中识别因果关系"

  pattern_matching:
    cause_effect_patterns:
      - cause: "TimeoutException"
        effect: "500 Internal Error"

      - cause: "NullPointerException"
        effect: "400/500 Error"

      - cause: "Database deadlock"
        effect: "Request timeout"

      - cause: "Cache miss + slow DB"
        effect: "High latency"

  chain_building:
    algorithm: "backward_chaining"
    steps:
      - "从最终失败点开始"
      - "向前追溯每个异常的触发原因"
      - "直到找到根本原因"

  output:
    causal_chain:
      - level: 1
        event: "用户看到错误：订单创建失败"
        caused_by: "API 返回 500"

      - level: 2
        event: "API 返回 500"
        caused_by: "OrderService 抛出 InventoryCheckFailed"

      - level: 3
        event: "OrderService 抛出 InventoryCheckFailed"
        caused_by: "InventoryService 调用超时"

      - level: 4
        event: "InventoryService 调用超时"
        caused_by: "数据库查询慢 (3.5s)"
        root_cause: true  # 根因标记

      - level: 5
        event: "数据库查询慢"
        caused_by: "缺少 sku 字段索引"
        root_root_cause: true  # 根根因
```

---

## 2. 根因假设生成

### 2.1 假设排名

```yaml
hypothesis_ranking:
  criteria:
    - name: "证据覆盖度"
      weight: 0.4
      description: "假设能解释多少证据"

    - name: "时序一致性"
      weight: 0.3
      description: "假设与事件时序是否一致"

    - name: "历史相似性"
      weight: 0.2
      description: "是否与历史 Bug 相似"

    - name: "代码变更相关性"
      weight: 0.1
      description: "最近是否有相关代码变更"

  output:
    hypotheses:
      - rank: 1
        hypothesis: "inventory 表缺少 sku 索引导致查询超时"
        confidence: 0.92
        evidence_coverage: 100%
        timeline_consistency: true
        supporting_evidence:
          - "DB 查询日志显示 3.5s"
          - "EXPLAIN 显示全表扫描"
          - "inventory 表有 100万 条记录"
        contradicting_evidence: []

      - rank: 2
        hypothesis: "InventoryService 服务资源不足"
        confidence: 0.65
        evidence_coverage: 70%
        supporting_evidence:
          - "服务响应慢"
        contradicting_evidence:
          - "其他接口响应正常"
          - "CPU/内存监控正常"
```

### 2.2 验证步骤

```yaml
verification_steps:
  description: "为每个假设生成验证步骤"

  for_hypothesis_1:
    hypothesis: "inventory 表缺少 sku 索引"
    steps:
      - step: 1
        action: "检查 inventory 表索引"
        command: "SHOW INDEX FROM inventory"
        expected: "sku 字段没有索引"

      - step: 2
        action: "执行 EXPLAIN 分析"
        command: "EXPLAIN SELECT * FROM inventory WHERE sku = 'SKU-001'"
        expected: "type = ALL (全表扫描)"

      - step: 3
        action: "添加索引后测试"
        command: "CREATE INDEX idx_sku ON inventory(sku)"
        expected: "查询时间 < 100ms"
```

---

## 3. 分类与定位

### 3.1 问题分类

```yaml
problem_classification:
  categories:
    frontend:
      - "RENDER_ERROR": "渲染错误"
      - "STATE_ERROR": "状态管理错误"
      - "PARAM_ERROR": "参数构造错误"
      - "PARSE_ERROR": "响应解析错误"

    backend:
      - "LOGIC_ERROR": "业务逻辑错误"
      - "DATA_ERROR": "数据处理错误"
      - "INTEGRATION_ERROR": "集成调用错误"
      - "RESOURCE_ERROR": "资源不足"

    database:
      - "QUERY_SLOW": "查询性能问题"
      - "INDEX_MISSING": "索引缺失"
      - "DEADLOCK": "死锁"
      - "CONSTRAINT_VIOLATION": "约束违反"

    infrastructure:
      - "NETWORK_ERROR": "网络问题"
      - "TIMEOUT": "超时"
      - "MEMORY_LEAK": "内存泄漏"
      - "CONNECTION_POOL": "连接池问题"

  output:
    classification:
      category: "database"
      subcategory: "INDEX_MISSING"
      confidence: 0.92
```

### 3.2 代码定位

```yaml
code_localization:
  description: "定位到具体的代码位置"

  sources:
    - "异常堆栈"
    - "调用链"
    - "最近代码变更"

  output:
    locations:
      - file: "InventoryService.java"
        line: 156
        method: "checkStock"
        type: "exception_origin"
        snippet: |
          public Stock checkStock(String sku) {
            return inventoryRepository.findBySku(sku);  // 这里慢
          }

      - file: "InventoryRepository.java"
        line: 23
        method: "findBySku"
        type: "slow_query"
        snippet: |
          @Query("SELECT * FROM inventory WHERE sku = :sku")
          Stock findBySku(String sku);  // 缺少索引

      - file: "schema.sql"
        line: 45
        type: "missing_index"
        snippet: |
          CREATE TABLE inventory (
            id BIGINT PRIMARY KEY,
            sku VARCHAR(50),  -- 需要添加索引
            stock INT
          );
```

---

## 4. 修复策略

```yaml
fix_strategy:
  description: "生成修复策略"

  output:
    strategy:
      immediate_fix:
        description: "立即修复方案"
        actions:
          - "为 inventory.sku 添加索引"
          - "command: CREATE INDEX idx_sku ON inventory(sku)"

      alternative_fixes:
        - description: "增加查询超时时间"
          pros: "快速缓解"
          cons: "治标不治本"
          recommendation: "不推荐"

        - description: "添加缓存"
          pros: "减少 DB 压力"
          cons: "增加复杂度，可能有一致性问题"
          recommendation: "可作为后续优化"

      long_term_fix:
        description: "长期解决方案"
        actions:
          - "添加索引监控告警"
          - "定期审计慢查询"
          - "制定索引规范"
```

---

## 5. 风险评估

```yaml
risk_assessment:
  impact_analysis:
    affected_features:
      - "订单创建"
      - "库存查询"
      - "商品详情页"

    affected_users:
      scope: "all"
      estimate: "100%"

    severity: "P0"

  fix_risk:
    risks:
      - risk: "添加索引可能锁表"
        mitigation: "在低峰期执行，使用 ONLINE DDL"
        probability: "medium"

      - risk: "索引可能影响写入性能"
        mitigation: "监控写入延迟"
        probability: "low"

  regression_risk:
    areas:
      - "库存相关的所有查询"
      - "订单创建流程"
      - "商品详情页加载"
```

---

## 6. 输出格式

### 6.1 根因报告

```yaml
root_cause_report:
  template: |
    ## 根因分析报告

    ### Bug 信息
    - Bug ID: {bug_id}
    - 标题: {title}
    - 严重程度: {severity}

    ### 根因结论
    **{root_cause_summary}**

    置信度: {confidence}%

    ### 因果链
    ```mermaid
    flowchart TD
      A[用户看到错误] --> B[API 返回 500]
      B --> C[OrderService 异常]
      C --> D[InventoryService 超时]
      D --> E[DB 查询慢 3.5s]
      E --> F[缺少 sku 索引]
      style F fill:#f66,stroke:#333
    ```

    ### 证据支持
    {#each evidence}
    - [{type}] {description}
      ```
      {content}
      ```
    {/each}

    ### 代码定位
    | 文件 | 行号 | 方法 | 问题 |
    |------|------|------|------|
    {#each locations}
    | {file} | {line} | {method} | {issue} |
    {/each}

    ### 修复建议
    **立即修复**:
    {immediate_fix}

    **长期优化**:
    {long_term_fix}

    ### 回归风险
    {#each regression_areas}
    - {area}
    {/each}

    ### 验证步骤
    {#each verification_steps}
    {step}. {action}
    {/each}
```

---

## 7. 与其他 Skills 协作

```yaml
skill_integration:
  inputs_from:
    - skill: "repro_scenario"
      data: "复现结果"

    - skill: "frontend_observability"
      data: "前端证据 (console/network/DOM)"

    - skill: "backend_trace"
      data: "后端日志与调用链"

    - skill: "api_probe"
      data: "API 探测结果"

    - skill: "db_inspection"
      data: "数据库检查结果"

  outputs_to:
    - skill: "patch_regression_plan"
      data: "根因结论 + 代码定位 + 修复策略"
```

---

## 版本历史

| 版本 | 日期 | 变更说明 |
|------|------|----------|
| 1.0 | 2026-01-13 | 初始版本 |
