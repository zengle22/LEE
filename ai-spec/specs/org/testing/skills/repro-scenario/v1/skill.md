# Repro & Scenario Skill v1.0
# 复现与场景构建技能

## 概述

负责从 bug.contract 复现步骤自动构建"复现脚本"，支持最小化复现（减少变量）。
当复现失败时，分析差异条件并增强复现信息。

## 技能标识

- **ID**: skill.test.repro_scenario
- **名称**: Repro & Scenario
- **版本**: 1.0
- **所有者**: test-governance

## 适用 Agent

- agent.test.debug_agent

---

## 1. 核心能力

### 1.1 复现脚本生成

```yaml
repro_script_generation:
  input:
    bug_contract:
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

  output:
    repro_script:
      type: "playwright"  # 或 api_script
      content: |
        // Auto-generated repro script
        test('BUG-2026-0001 reproduction', async ({ page }) => {
          // Preconditions
          await loginAsUser(page, 'test_user');
          await addToCart(page, 'SKU-001');

          // Steps
          await page.click('[data-testid="checkout-btn"]');
          await page.click('[data-testid="payment-alipay"]');
          await page.click('[data-testid="confirm-pay"]');

          // Assertion (expect failure for bug repro)
          await expect(page).toHaveURL(/payment/);
        });
```

### 1.2 最小化复现

```yaml
minimize_repro:
  strategy:
    binary_search:
      description: "通过二分法减少步骤，找到最小复现路径"
      process:
        - "移除一半步骤，检查是否仍能复现"
        - "如能复现，继续减少"
        - "如不能复现，恢复并尝试另一半"
        - "直到找到最小步骤集"

    variable_isolation:
      description: "隔离变量，确定关键触发条件"
      variables:
        - "用户类型 (新用户/老用户)"
        - "数据状态 (空/有数据)"
        - "时间条件 (首次/重复)"
        - "并发条件 (单用户/多用户)"

  output:
    minimal_steps:
      - step: "直接访问 /checkout 页面"
      - step: "点击确认支付"
    key_conditions:
      - "购物车必须有库存不足商品"
      - "用户必须是首次支付"
```

### 1.3 复现失败处理

```yaml
repro_failure_handling:
  when_cannot_reproduce:
    actions:
      - "对比环境差异"
      - "检查数据状态差异"
      - "检查时序条件"
      - "检查并发条件"

    environment_diff:
      check_items:
        - "浏览器版本"
        - "操作系统"
        - "网络条件"
        - "后端版本"
        - "数据库状态"

    data_diff:
      check_items:
        - "用户数据"
        - "订单状态"
        - "库存数量"
        - "配置开关"

    output:
      enhanced_repro:
        missing_conditions:
          - "需要特定用户 ID: 12345"
          - "需要库存 = 0 的商品"
        environment_requirements:
          - "Chrome 120+"
          - "backend version >= 2.3.0"
        data_setup:
          - script: "setup_test_data.sql"
            description: "创建库存为 0 的商品"
```

---

## 2. 复现策略

### 2.1 UI 复现

```yaml
ui_repro:
  framework: playwright
  config:
    headless: false  # 调试时显示浏览器
    slow_mo: 500     # 放慢执行便于观察
    video: true      # 录制视频
    trace: true      # 记录 trace

  steps:
    - "启动浏览器"
    - "执行前置条件"
    - "按步骤操作"
    - "在关键点截图"
    - "记录 console/network"
    - "捕获错误信息"
```

### 2.2 API 复现

```yaml
api_repro:
  description: "绕过 UI 直接复现 API 问题"
  use_when:
    - "问题明确在后端"
    - "UI 复现成本高"
    - "需要快速验证"

  steps:
    - "构造请求参数"
    - "发送 API 请求"
    - "记录响应"
    - "对比预期"

  example: |
    # API 复现脚本
    curl -X POST https://test.example.com/api/orders \
      -H "Authorization: Bearer ${TOKEN}" \
      -H "Content-Type: application/json" \
      -d '{"sku": "SKU-001", "quantity": 1}' \
      -v
```

### 2.3 数据驱动复现

```yaml
data_driven_repro:
  description: "使用多组数据尝试复现，找出触发条件"

  test_data_matrix:
    - scenario: "正常用户正常商品"
      user_type: "normal"
      sku_stock: 100
      expected_repro: false

    - scenario: "正常用户库存不足"
      user_type: "normal"
      sku_stock: 0
      expected_repro: true  # 可能触发

    - scenario: "VIP用户库存不足"
      user_type: "vip"
      sku_stock: 0
      expected_repro: false  # VIP 有特殊处理

  output:
    trigger_condition: "user_type == 'normal' && sku_stock == 0"
```

---

## 3. 复现报告

```yaml
repro_report:
  template: |
    ## 复现报告

    ### Bug 信息
    - Bug ID: {bug_id}
    - 标题: {title}
    - 报告人: {reporter}

    ### 复现结果
    - 状态: {repro_status}  # SUCCESS | FAILED | PARTIAL
    - 复现率: {repro_rate}  # 5/5 = 100%
    - 最小步骤数: {min_steps}

    ### 复现条件
    {#each conditions}
    - {condition}
    {/each}

    ### 复现脚本
    ```
    {repro_script}
    ```

    ### 复现证据
    - 视频: {video_path}
    - 截图: {screenshot_path}
    - 日志: {log_path}

    ### 差异分析 (如复现失败)
    {#if repro_failed}
    | 维度 | 报告环境 | 当前环境 |
    |------|----------|----------|
    {#each diffs}
    | {dimension} | {reported} | {current} |
    {/each}
    {/if}
```

---

## 4. 最佳实践

```yaml
best_practices:
  before_repro:
    - "确认环境版本与 Bug 报告一致"
    - "准备必要的测试数据"
    - "清理可能影响结果的缓存"

  during_repro:
    - "严格按步骤执行，不跳步"
    - "记录每一步的系统响应"
    - "多次执行确认复现率"

  after_repro:
    - "保存所有证据"
    - "尝试最小化复现"
    - "记录触发条件"

  when_cannot_reproduce:
    - "不要立即关闭 Bug"
    - "请求更多环境/数据信息"
    - "尝试不同的数据组合"
    - "考虑时序/并发因素"
```

---

## 版本历史

| 版本 | 日期 | 变更说明 |
|------|------|----------|
| 1.0 | 2026-01-13 | 初始版本 |
