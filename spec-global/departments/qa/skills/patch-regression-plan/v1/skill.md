# Patch & Regression Plan Skill v1.0
# 修复与回归计划技能

## 概述

生成修复建议（伪代码/patch），自动要求/生成回归用例（单测、接口测或 E2E 之一）。
更新 bug.contract：fix plan + regression required。

## 技能标识

- **ID**: skill.test.patch_regression_plan
- **名称**: Patch & Regression Plan
- **版本**: 1.0
- **所有者**: test-governance

## 适用 Agent

- agent.test.debug_agent

---

## 1. 修复建议生成

### 1.1 Patch 草稿

```yaml
patch_draft:
  description: "生成修复补丁草稿（不提交，仅供参考）"

  output_formats:
    pseudo_code:
      description: "伪代码描述"
      example: |
        ## 修复方案

        ### 问题
        inventory 表缺少 sku 字段索引，导致查询超时

        ### 修复步骤
        1. 在 inventory 表添加 sku 索引
        2. 验证查询性能
        3. 更新 schema 文件

        ### 伪代码
        ```sql
        -- Add index to inventory table
        CREATE INDEX idx_inventory_sku ON inventory(sku);
        ```

    diff_patch:
      description: "diff 格式补丁"
      example: |
        --- a/src/main/resources/db/migration/V20260113__add_inventory_index.sql
        +++ b/src/main/resources/db/migration/V20260113__add_inventory_index.sql
        @@ -0,0 +1,3 @@
        +-- Add index for sku lookup performance
        +CREATE INDEX IF NOT EXISTS idx_inventory_sku ON inventory(sku);
        +

    code_snippet:
      description: "代码片段"
      example: |
        // File: InventoryRepository.java
        // Before:
        @Query("SELECT * FROM inventory WHERE sku = :sku")
        Stock findBySku(String sku);

        // After (with index hint for safety):
        @Query(value = "SELECT * FROM inventory USE INDEX (idx_inventory_sku) WHERE sku = :sku",
               nativeQuery = true)
        Stock findBySku(String sku);

  constraints:
    - "补丁仅供参考，不直接提交"
    - "开发团队需审查后决定采用"
    - "可能需要根据实际情况调整"
```

### 1.2 修复方案对比

```yaml
fix_comparison:
  description: "提供多个修复方案对比"

  template:
    options:
      - option: "A"
        name: "添加数据库索引"
        description: "在 inventory.sku 字段添加 B-tree 索引"
        pros:
          - "根本解决问题"
          - "一次性修复"
          - "改动最小"
        cons:
          - "需要 DBA 审批"
          - "大表可能需要在线 DDL"
        effort: "low"
        risk: "low"
        recommendation: "推荐"

      - option: "B"
        name: "增加查询超时时间"
        description: "将 InventoryService 超时从 3s 改为 10s"
        pros:
          - "改动简单"
          - "立即生效"
        cons:
          - "治标不治本"
          - "可能导致请求堆积"
          - "用户体验差"
        effort: "low"
        risk: "medium"
        recommendation: "不推荐（临时缓解可用）"

      - option: "C"
        name: "添加 Redis 缓存"
        description: "库存查询结果缓存 5 分钟"
        pros:
          - "大幅提升性能"
          - "减少 DB 压力"
        cons:
          - "增加复杂度"
          - "可能有一致性问题"
          - "需要额外基础设施"
        effort: "high"
        risk: "medium"
        recommendation: "可作为后续优化"

  output:
    recommended_option: "A"
    reason: "根本解决问题，改动最小，风险最低"
```

---

## 2. 回归用例生成

### 2.1 回归范围分析

```yaml
regression_scope:
  analysis:
    affected_code:
      - "InventoryService.checkStock()"
      - "OrderService.createOrder()"
      - "ProductController.getProduct()"

    affected_features:
      - "订单创建"
      - "库存查询"
      - "商品详情"

    call_graph:
      upstream:
        - "OrderController"
        - "CartService"
      downstream:
        - "InventoryRepository"
        - "Database"

  scope_determination:
    rules:
      - if: "修改影响多个模块"
        then: "需要 E2E 回归"

      - if: "修改仅影响单个服务内部"
        then: "接口测试 + 单元测试"

      - if: "修改是配置/SQL"
        then: "至少需要接口测试"

    output:
      scope: "moderate"
      required_tests:
        - type: "unit"
          coverage: ["InventoryRepository.findBySku()"]
        - type: "integration"
          coverage: ["OrderService.createOrder()"]
        - type: "e2e"
          coverage: ["订单创建流程"]
```

### 2.2 回归用例模板

```yaml
regression_cases:
  unit_test:
    template: |
      @Test
      void testFindBySku_Performance() {
        // Given
        String sku = "SKU-001";

        // When
        long startTime = System.currentTimeMillis();
        Stock stock = inventoryRepository.findBySku(sku);
        long duration = System.currentTimeMillis() - startTime;

        // Then
        assertNotNull(stock);
        assertTrue(duration < 100, "Query should complete within 100ms");
      }

      @Test
      void testFindBySku_NotFound() {
        // Given
        String nonExistentSku = "SKU-NONEXISTENT";

        // When
        Stock stock = inventoryRepository.findBySku(nonExistentSku);

        // Then
        assertNull(stock);
      }

  integration_test:
    template: |
      @Test
      void testCreateOrder_Success() {
        // Given
        OrderRequest request = new OrderRequest("SKU-001", 1);

        // When
        OrderResponse response = orderService.createOrder(request);

        // Then
        assertNotNull(response.getOrderId());
        assertEquals("CREATED", response.getStatus());
      }

      @Test
      void testCreateOrder_InsufficientStock() {
        // Given
        OrderRequest request = new OrderRequest("SKU-EMPTY", 100);

        // When/Then
        assertThrows(InsufficientStockException.class,
          () -> orderService.createOrder(request));
      }

  e2e_test:
    template: |
      test('Create order successfully', async ({ page }) => {
        // Login
        await loginAsUser(page, 'test_user');

        // Add to cart
        await page.goto('/products/SKU-001');
        await page.click('[data-testid="add-to-cart"]');

        // Checkout
        await page.click('[data-testid="checkout-btn"]');
        await page.click('[data-testid="confirm-order"]');

        // Verify
        await expect(page.locator('[data-testid="order-success"]'))
          .toBeVisible();
        await expect(page.locator('[data-testid="order-id"]'))
          .toContainText(/ORD-/);
      });

      test('Order creation completes within 3 seconds', async ({ page }) => {
        const startTime = Date.now();

        // ... order creation steps ...

        const duration = Date.now() - startTime;
        expect(duration).toBeLessThan(3000);
      });
```

### 2.3 回归检查清单

```yaml
regression_checklist:
  template: |
    ## 回归测试检查清单

    ### Bug 信息
    - Bug ID: {bug_id}
    - 修复内容: {fix_summary}

    ### 必须验证
    - [ ] 原问题已修复（按复现步骤验证）
    - [ ] 相关单元测试通过
    - [ ] 相关接口测试通过
    - [ ] 影响的功能正常

    ### 回归用例
    #### 单元测试
    - [ ] `InventoryRepositoryTest.testFindBySku_Performance`
    - [ ] `InventoryRepositoryTest.testFindBySku_NotFound`

    #### 接口测试
    - [ ] `OrderServiceTest.testCreateOrder_Success`
    - [ ] `OrderServiceTest.testCreateOrder_InsufficientStock`

    #### E2E 测试
    - [ ] 订单创建成功流程
    - [ ] 订单创建性能 < 3s

    ### 风险检查
    - [ ] 其他库存相关查询正常
    - [ ] 商品详情页加载正常
    - [ ] 购物车功能正常

    ### 验收标准
    - [ ] 所有回归用例通过
    - [ ] 无新增问题
    - [ ] 性能指标达标
```

---

## 3. Bug Contract 更新

### 3.1 更新字段

```yaml
bug_contract_update:
  add_fields:
    root_cause:
      type: object
      description: "根因分析结果"
      fields:
        summary: "inventory.sku 缺少索引导致查询超时"
        category: "database.index_missing"
        confidence: 0.92
        evidence_refs: ["evidence/db/...", "evidence/backend/..."]

    fix_plan:
      type: object
      description: "修复计划"
      fields:
        recommended:
          option: "A"
          description: "添加 inventory.sku 索引"
          patch_ref: "patches/BUG-2026-0001.patch"
        alternatives:
          - option: "B"
            description: "增加超时时间"
        assigned_to: null  # 待分配
        estimated_effort: "low"

    regression_required:
      type: object
      description: "回归测试要求"
      fields:
        unit_tests:
          - "InventoryRepositoryTest.testFindBySku_*"
        integration_tests:
          - "OrderServiceTest.testCreateOrder_*"
        e2e_tests:
          - "订单创建流程"
        checklist_ref: "checklists/BUG-2026-0001-regression.md"

    risk_assessment:
      type: object
      description: "风险评估"
      fields:
        fix_risk: "low"
        regression_risk: "medium"
        affected_areas:
          - "库存查询"
          - "订单创建"
          - "商品详情"
```

### 3.2 更新后的 Bug Contract 示例

```yaml
bug_contract_example:
  # 原有字段
  bug_id: "BUG-2026-0001"
  title: "创建订单时页面报错 500"
  severity: "P0"
  status: "diagnosed"  # 更新状态

  detected_in:
    version: "2.3.1"
    environment: "test"
    test_case_id: "TC-ORDER-001"

  repro:
    preconditions:
      - "用户已登录"
      - "购物车有商品"
    steps:
      - "点击结算按钮"
      - "选择支付方式"
      - "点击确认支付"
    expected: "跳转到支付页面"
    actual: "页面报错 500"

  # Debug Agent 新增字段
  root_cause:
    summary: "inventory.sku 缺少索引导致查询超时 (3.5s)"
    category: "database.index_missing"
    confidence: 0.92
    causal_chain:
      - "用户点击确认 → API 调用 → OrderService → InventoryService → DB 查询超时"
    code_locations:
      - file: "InventoryRepository.java"
        line: 23
        issue: "查询无索引"
    evidence_bundle: "evidence/debug/BUG-2026-0001/"

  fix_plan:
    recommended:
      option: "A"
      description: "添加 inventory.sku 索引"
      steps:
        - "创建 migration: V20260113__add_inventory_index.sql"
        - "添加索引: CREATE INDEX idx_inventory_sku ON inventory(sku)"
        - "验证查询性能"
      patch_ref: "patches/BUG-2026-0001.sql"
    assigned_to: null
    estimated_effort: "2h"

  regression_required:
    scope: "moderate"
    tests:
      unit:
        - name: "InventoryRepositoryTest.testFindBySku_Performance"
          status: "pending"
      integration:
        - name: "OrderServiceTest.testCreateOrder_Success"
          status: "pending"
      e2e:
        - name: "订单创建流程"
          status: "pending"
    checklist: "checklists/BUG-2026-0001-regression.md"

  risk_assessment:
    fix_risk: "low"
    fix_risk_detail: "在线 DDL，低峰期执行"
    regression_risk: "medium"
    affected_areas:
      - "库存查询"
      - "订单创建"
      - "商品详情"

  # 状态更新
  debug_completed_at: "2026-01-13T11:00:00Z"
  debug_agent: "agent.test.debug_agent"
  handoff_to: "development"
```

---

## 4. 输出产物

```yaml
outputs:
  patch_file:
    path: "patches/{bug_id}.patch"
    format: "diff"
    description: "修复补丁草稿"

  regression_checklist:
    path: "checklists/{bug_id}-regression.md"
    format: "markdown"
    description: "回归测试检查清单"

  test_templates:
    path: "test-templates/{bug_id}/"
    contents:
      - "unit-test-template.java"
      - "integration-test-template.java"
      - "e2e-test-template.ts"

  updated_bug_contract:
    path: "bugs/{bug_id}.yaml"
    description: "更新后的 Bug 契约"
```

---

## 5. 与开发交接

```yaml
handoff:
  notification:
    to: ["dev-lead", "assigned-developer"]
    channel: ["console", "slack"]
    message: |
      🔍 Bug {bug_id} 根因分析完成

      **根因**: {root_cause_summary}
      **推荐修复**: {fix_recommendation}
      **预估工作量**: {effort}

      📋 详情:
      - Bug 契约: bugs/{bug_id}.yaml
      - 补丁草稿: patches/{bug_id}.patch
      - 回归清单: checklists/{bug_id}-regression.md

      请审阅后分配开发资源。

  acceptance_criteria:
    for_developer:
      - "阅读根因分析"
      - "审阅修复建议"
      - "确认回归范围"
      - "开始编码修复"

    for_qa:
      - "准备回归测试"
      - "等待修复完成"
      - "执行回归验证"
```

---

## 版本历史

| 版本 | 日期 | 变更说明 |
|------|------|----------|
| 1.0 | 2026-01-13 | 初始版本 |
