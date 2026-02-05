# Test Case Design Pipeline - Usage Guide
# 测试用例设计工作流使用指南

> **版本**: v1.0
> **创建日期**: 2026-02-04
> **适用范围**: 从需求文档到 E2E 测试脚本的完整测试用例设计流程
> **关键特性**: 需求对齐、分支覆盖、专项测试、人类评审、Playwright 自动生成

---

## 目录

1. [工作流概述](#工作流概述)
2. [前置条件](#前置条件)
3. [输入输出](#输入输出)
4. [工作流步骤](#工作流步骤)
5. [使用示例](#使用示例)
6. [故障排查](#故障排查)
7. [最佳实践](#最佳实践)
8. [常见问题](#常见问题)

---

## 工作流概述

### 什么是测试用例设计工作流？

**测试用例设计工作流（Test Case Design Pipeline）**是一个从需求到测试的自动化设计流程，完整覆盖：

- 需求对齐（PRD、架构、UI 三方一致性验证）
- 功能点校准（建立需求到实现的映射）
- 分支覆盖用例设计（基于决策点的完整覆盖）
- 专项测试用例设计（性能、安全、可访问性）
- 人类评审（质量把关和风险控制）
- Playwright E2E 脚本生成（自动化测试代码）

### 核心价值

| 特性 | 传统测试设计 | 本工作流 |
|------|------------|---------|
| 需求追溯 | 手工维护，易遗漏 | 自动生成，100%可追溯 |
| 分支覆盖 | 经验驱动，易漏测 | 决策点分析，完整覆盖 |
| 专项测试 | 临时补充，系统性差 | 结构化设计，全面覆盖 |
| 自动化脚本 | 手工编写，耗时费力 | 自动生成，即用即跑 |
| 质量保证 | 依赖个人能力 | 门禁机制 + 人类评审 |

### 适用场景

**新功能测试设计**
- PRD 已冻结，技术架构已确定
- UI 原型已完成，需要设计完整测试方案
- 需要生成可执行的 E2E 自动化脚本

**回归测试用例补充**
- 发现测试覆盖缺口
- 需要补充分支测试用例
- 需要补充专项测试（性能、安全等）

**质量基线建立**
- 新项目启动，建立完整测试体系
- 遗留项目，重构测试用例库
- 合规要求，建立可追溯的质量体系

---

## 前置条件

### 必需的契约文件

#### 1. PRD 契约（冻结版）

```yaml
# 文件路径示例
prd/contracts/frozen-detailed-prd-contract/v1/prd-ai-marathon-coach-v1.0.yaml

# 必需字段
product_id: "AI-MARATHON-COACH"
version: "1.0.0"
status: "frozen"  # 必须是 frozen
requirements:
  - requirement_id: "REQ-2026-001"
    feature_id: "goal-management"
    title: "跑步目标管理"
    acceptance_criteria:
      - "用户可以创建、编辑、删除跑步目标"
      - "目标数据持久化存储"
    priority: "P0"
```

#### 2. 技术架构契约（冻结版）

```yaml
# 文件路径示例
dev/contracts/frozen-technical-architecture-contract/v1/arch-ai-marathon-coach-v1.0.yaml

# 必需字段
architecture_id: "ARCH-2026-001"
version: "1.0.0"
status: "frozen"  # 必须是 frozen
components:
  - component_id: "frontend-web"
    type: "web-app"
    tech_stack: ["React", "TypeScript"]
  - component_id: "backend-api"
    type: "rest-api"
    tech_stack: ["Go", "Gin"]
  - component_id: "database"
    type: "postgresql"
```

#### 3. UI 原型契约（冻结版）

```yaml
# 文件路径示例
ui/contracts/frozen-ui-prototype-contract/v1/prototype-ai-marathon-coach-v1.0.yaml

# 必需字段
prototype_id: "UI-PROTO-2026-001"
version: "1.0.0"
status: "frozen"  # 必须是 frozen
pages:
  - page_id: "goal-list-page"
    wireframe_url: "/designs/goal-list.png"
    interactions:
      - "点击目标卡片进入详情页"
      - "滑动刷新目标列表"
```

#### 4. UI 页面契约

```yaml
# 文件路径示例
ui/contracts/ui-page-contract/v1/pages-ai-marathon-coach.yaml

# 必需字段
pages:
  - page_id: "goal-list-page"
    route: "/goals"
    components:
      - component_id: "goal-card"
        selectors:
          web: ".goal-card"
          wechat: ".goal-card"
        test_ids:
          - "goal-card-{goalId}"
    data_binding:
      - field: "goal.title"
        selector: "[data-testid='goal-title']"
```

### 环境要求

```bash
# 1. Python 环境
python >= 3.9

# 2. 依赖包
pip install orchestrator-cli  # LEE 框架 CLI 工具

# 3. 工作流文件
# 确保工作流定义文件可用
ls ai-spec/specs/org/qa/workflows/test-case-design-pipeline/v1/workflow.yaml
```

---

## 输入输出

### 输入文件

| 文件类型 | 契约定义 | 状态要求 | 用途 |
|---------|---------|---------|------|
| PRD 契约 | `frozen-detailed-prd-contract` | **frozen** | 需求来源 |
| 架构契约 | `frozen-technical-architecture-contract` | **frozen** | 技术实现 |
| UI 原型契约 | `frozen-ui-prototype-contract` | **frozen** | UI 交互 |
| UI 页面契约 | `ui-page-contract` | 可用 | 测试自动化 |

### 输出产物

```
test-case-design-package/
├── test-case-design/              # 测试用例设计文档
│   ├── requirement-alignment.yaml      # 需求对齐报告
│   ├── feature-calibration.yaml        # 功能点校准报告
│   ├── branch-coverage.yaml            # 分支覆盖分析
│   └── specialized-tests.yaml          # 专项测试设计
│
├── test-cases/                    # 测试用例集合
│   ├── functional/
│   │   ├── smoke/                      # 冒烟测试用例
│   │   ├── core-flow/                  # 核心流程用例
│   │   └── branch-coverage/            # 分支覆盖用例
│   ├── performance/                    # 性能测试用例
│   ├── security/                       # 安全测试用例
│   └── accessibility/                  # 可访问性测试用例
│
├── e2e-scripts/                    # Playwright E2E 脚本
│   ├── playwright/
│   │   ├── specs/                     # 测试规范文件
│   │   ├── helpers/                   # 辅助函数
│   │   └── config/                    # 配置文件
│   └── test-data/                     # 测试数据
│
├── review/                         # 评审产物
│   ├── test-case-review-package.yaml  # 评审包
│   ├── test-case-review-approval.yaml  # 审批记录
│   └── test-case-review-feedback.yaml  # 反馈记录
│
└── delivery/                       # 交付物
    ├── test-case-design-package/    # 完整交付包
    ├── metrics.yaml                 # 质量指标
    └── delivery-manifest.yaml       # 交付清单
```

### 关键输出示例

#### 需求对齐报告

```yaml
# test-case-design/requirement-alignment.yaml
alignment_id: "ALIGN-2026-001"
prd_version: "1.0.0"
architecture_version: "1.0.0"
ui_prototype_version: "1.0.0"

consistency_matrix:
  prd_to_architecture:
    total_requirements: 25
    mapped_requirements: 25
    coverage_rate: 100%
    gaps: []

  prd_to_ui:
    total_requirements: 25
    mapped_requirements: 24
    coverage_rate: 96%
    gaps:
      - requirement_id: "REQ-2026-025"
        issue: "UI 缺少错误提示设计"

  architecture_to_ui:
    total_components: 12
    mapped_components: 12
    coverage_rate: 100%

recommendations:
  - "补充 REQ-2026-025 的错误提示 UI 设计"
  - "所有映射关系已验证，可进入下一阶段"
```

#### 功能点校准报告

```yaml
# test-case-design/feature-calibration.yaml
calibration_id: "CALIB-2026-001"
total_features: 15
mapped_features: 15

feature_to_component_mapping:
  - feature_id: "goal-management"
    requirement_id: "REQ-2026-001"
    components:
      - "frontend-web:goal-list-page"
      - "frontend-web:goal-detail-page"
      - "backend-api:goal-handler"
      - "database:goals-table"
    ui_pages:
      - "goal-list-page"
      - "goal-detail-page"
    test_coverage:
      smoke_cases: 3
      functional_cases: 12
      branch_cases: 8

coverage_matrix:
  total_requirements: 25
  covered_requirements: 25
  coverage_rate: 100%

uncovered_features: []
orphan_components: []
orphan_pages: []
```

#### 分支覆盖分析

```yaml
# test-case-design/branch-coverage.yaml
coverage_id: "BRANCH-2026-001"
total_user_flows: 8
total_decision_points: 24
total_branch_cases: 67

user_flows:
  - flow_id: "create-goal-flow"
    flow_name: "创建目标流程"
    decision_points:
      - point_id: "goal-type-selection"
        location: "goal-create-page"
        condition: "用户选择目标类型"
        branches:
          - branch_id: "time-based-goal"
            cases: 3
          - branch_id: "distance-based-goal"
            cases: 3
          - branch_id: "frequency-based-goal"
            cases: 3
      - point_id: "goal-validation"
        condition: "目标数据验证"
        branches:
          - branch_id: "valid-goal"
            cases: 2
          - branch_id: "invalid-goal-name"
            cases: 2
          - branch_id: "invalid-target-value"
            cases: 2

branch_cases:
  - case_id: "F-BRANCH-001"
    flow_id: "create-goal-flow"
    branch_id: "time-based-goal"
    title: "创建时间目标 - 正常流程"
    priority: "P0"
    automated: true
```

#### Playwright 测试脚本

```typescript
// e2e-scripts/playwright/specs/functional/goal-management.spec.ts
import { test, expect } from '@playwright/test';
import { GoalPage } from '../helpers/page-objects';

test.describe('Goal Management', () => {
  let goalPage: GoalPage;

  test.beforeEach(async ({ page }) => {
    goalPage = new GoalPage(page);
    await goalPage.goto();
  });

  test('F-SMOKE-001: Create time-based goal successfully', async () => {
    // 冒烟测试：创建时间目标
    await goalPage.clickCreateButton();
    await goalPage.selectGoalType('time-based');
    await goalPage.enterGoalName('Morning Run');
    await goalPage.enterTarget('30', 'minutes');
    await goalPage.submit();

    await expect(goalPage.successMessage).toBeVisible();
    await expect(goalPage.goalCard).toContainText('Morning Run');
  });

  test('F-BRANCH-001: Validate goal name - empty name', async () => {
    // 分支测试：目标名称为空
    await goalPage.clickCreateButton();
    await goalPage.enterGoalName('');
    await goalPage.submit();

    await expect(goalPage.errorMessage).toContainText('目标名称不能为空');
  });
});
```

---

## 工作流步骤

### Stage 1: 输入验证（INPUT_VALIDATION）

**目的**: 确保所有输入契约完整且一致

**步骤**:
```bash
# 启动工作流
cd project/<项目名>/test-design
python -m orchestrator init . \
  --workflow ai-spec/specs/org/qa/workflows/test-case-design-pipeline/v1/workflow.yaml \
  --inputs \
    prd=../../prd/contracts/frozen-detailed-prd-contract/v1/prd.yaml \
    technical_architecture=../../dev/contracts/frozen-technical-architecture-contract/v1/arch.yaml \
    ui_prototype=../../ui/contracts/frozen-ui-prototype-contract/v1/prototype.yaml \
    ui_page=../../ui/contracts/ui-page-contract/v1/pages.yaml

# 开始输入验证
python -m orchestrator start . s1_1_validate_inputs
```

**验证项**:
- 所有契约文件存在且可读
- 契约版本号一致
- PRD、架构、UI 状态均为 `frozen`
- 契约 schema 验证通过

**输出**:
```yaml
# validation/input-validation-report.yaml
validation_status: "PASSED"
validated_at: "2026-02-04T10:00:00Z"
contracts_validated:
  - prd: "VALID"
  - technical_architecture: "VALID"
  - ui_prototype: "VALID"
  - ui_page: "VALID"
```

**失败处理**:
- 状态自动切换到 `BLOCKED`
- 通知 qa_lead 和 pm
- 需要修复输入契约后重新开始

---

### Stage 2: 需求对齐（REQUIREMENT_ALIGNMENT）

**目的**: 验证 PRD、架构文档、UI 契约之间的一致性

**步骤**:
```bash
# Stage 2.1: 验证三方一致性
python -m orchestrator start . s2_1_validate_consistency

# 如果有冲突（自动检测到），Stage 2.2 会执行
python -m orchestrator start . s2_2_resolve_conflicts
```

**处理内容**:

1. **PRD 到架构映射**
   - 每个需求是否都有对应的组件实现
   - 组件是否覆盖所有功能点
   - 技术选型是否满足需求

2. **PRD 到 UI 映射**
   - 每个需求是否都有对应的 UI 页面
   - UI 交互是否完整描述用户流程
   - 是否有缺失的 UI 元素

3. **架构到 UI 映射**
   - 每个组件是否都有对应的 UI 实现
   - API 契约是否与 UI 数据绑定匹配

**输出**:
```yaml
# test-case-design/requirement-alignment.yaml
consistency_matrix:
  prd_to_architecture:
    total_requirements: 25
    mapped_requirements: 25
    coverage_rate: 100%
    conflicts: []

  prd_to_ui:
    total_requirements: 25
    mapped_requirements: 24
    coverage_rate: 96%
    conflicts:
      - requirement_id: "REQ-2026-025"
        conflict_type: "missing_ui"
        description: "缺少错误提示 UI 设计"
        severity: "MEDIUM"

gaps_identified:
  - gap_id: "GAP-001"
    requirement_id: "REQ-2026-025"
    missing_artifact: "ui_error_prompt_design"
    impact: "错误提示测试用例无法设计"

recommendations:
  - priority: "HIGH"
    action: "补充错误提示 UI 设计"
    assignee: "ui-designer"
    deadline: "2026-02-06"
```

**冲突解决**:
- 自动尝试解决简单冲突（如命名不一致）
- 复杂冲突升级到人类介入
- 生成冲突报告和修复建议

---

### Stage 3: 功能点校准（FEATURE_CALIBRATION）

**目的**: 建立 PRD 功能点与架构组件、UI 页面的映射关系

**步骤**:
```bash
# Step 3.1: 提取功能点
python -m orchestrator start . s3_1_extract_features

# Step 3.2: 映射到架构组件
python -m orchestrator start . s3_2_map_to_components

# Step 3.3: 映射到 UI 页面
python -m orchestrator start . s3_3_map_to_pages

# Step 3.4: 生成校准报告
python -m orchestrator start . s3_4_generate_calibration_report
```

**处理内容**:

1. **提取功能点**
   ```yaml
   # test-case-design/feature-list.yaml
   features:
     - feature_id: "goal-management"
       requirement_id: "REQ-2026-001"
       sub_features:
         - "create-goal"
         - "edit-goal"
         - "delete-goal"
         - "list-goals"
   ```

2. **映射到架构组件**
   ```yaml
   # test-case-design/feature-to-component-mapping.yaml
   mappings:
     - feature_id: "create-goal"
       components:
         - component_id: "goal-create-page"
           component_type: "frontend"
           files:
             - "src/pages/goal/create.tsx"
         - component_id: "goal-api"
           component_type: "backend"
           files:
             - "internal/handler/goal_handler.go"
   ```

3. **映射到 UI 页面**
   ```yaml
   # test-case-design/feature-to-page-mapping.yaml
   mappings:
     - feature_id: "create-goal"
       ui_pages:
         - page_id: "goal-create-page"
           route: "/goals/create"
           test_ids:
             - "goal-create-form"
             - "goal-type-selector"
   ```

4. **生成校准报告**
   - 覆盖矩阵：需求 → 组件 → 页面
   - 未覆盖功能点：需要补充测试
   - 孤立组件/页面：无需求对应，需要清理

**输出**:
```yaml
# test-case-design/feature-calibration.yaml
coverage_summary:
  total_requirements: 25
  total_features: 15
  total_components: 12
  total_ui_pages: 10

coverage_matrix:
  requirement_to_feature: 100%
  feature_to_component: 100%
  feature_to_ui_page: 100%

uncovered_features: []
orphan_components: []
orphan_pages: []

test_coverage_plan:
  total_estimated_cases: 120
  breakdown:
    smoke: 15
    functional: 65
    branch: 40
```

---

### Stage 4: 分支覆盖用例设计（BRANCH_COVERAGE_DESIGN）

**目的**: 基于用户流程和决策点设计分支测试用例

**步骤**:
```bash
# Step 4.1: 识别用户流程
python -m orchestrator start . s4_1_identify_user_flows

# Step 4.2: 识别决策点
python -m orchestrator start . s4_2_identify_decision_points

# Step 4.3: 设计分支用例
python -m orchestrator start . s4_3_design_branch_cases
```

**处理内容**:

1. **识别用户流程**
   ```yaml
   # test-case-design/user-flows.yaml
   user_flows:
     - flow_id: "create-goal-flow"
       flow_name: "创建目标流程"
       entry_point: "goal-list-page"
       exit_point: "goal-detail-page"
       steps:
         - step: 1
           action: "点击创建按钮"
           page: "goal-list-page"
         - step: 2
           action: "选择目标类型"
           page: "goal-create-page"
         - step: 3
           action: "输入目标信息"
           page: "goal-create-page"
         - step: 4
           action: "提交创建"
           page: "goal-create-page"
   ```

2. **识别决策点**
   ```yaml
   # test-case-design/decision-points.yaml
   decision_points:
     - point_id: "goal-type-selection"
       flow_id: "create-goal-flow"
       location: "goal-create-page"
       condition: "用户选择目标类型"
       branches:
         - branch_id: "time-based"
           condition: "目标类型 = 时间目标"
           probability: "high"
         - branch_id: "distance-based"
           condition: "目标类型 = 距离目标"
           probability: "high"
         - branch_id: "frequency-based"
           condition: "目标类型 = 频率目标"
           probability: "medium"

   edge_cases:
     - case_id: "edge-001"
       scenario: "未选择目标类型直接提交"
       expected_behavior: "显示错误提示"
   ```

3. **设计分支用例**
   ```yaml
   # test-cases/functional/branch-coverage/flow-create-goal/branch-time-based.yaml
   case_id: "F-BRANCH-001"
   flow_id: "create-goal-flow"
   branch_id: "time-based-goal"
   title: "创建时间目标 - 正常流程"
   priority: "P0"
   automated: true

   preconditions:
     - user_logged_in: true
     - goal_list_page_loaded: true

   test_steps:
     - step: 1
       action: "点击创建按钮"
       expected: "跳转到目标创建页"
     - step: 2
       action: "选择'时间目标'类型"
       expected: "显示时间目标输入框"
     - step: 3
       action: "输入目标名称：晨跑"
       expected: "目标名称输入成功"
     - step: 4
       action: "输入目标时长：30分钟"
       expected: "时长输入成功"
     - step: 5
       action: "点击提交"
       expected: "创建成功，跳转到目标详情页"

   expected_result:
     - "目标创建成功"
     - "目标详情页显示正确信息"
     - "目标列表页包含新目标"

   traceability:
     requirement_id: "REQ-2026-001"
     feature_id: "goal-management"
     decision_point_id: "goal-type-selection"
   ```

**输出**:
```
test-cases/functional/branch-coverage/
├── flow-create-goal/
│   ├── main-path.yaml          # 主流程用例
│   ├── branch-time-based.yaml  # 时间目标分支
│   ├── branch-distance-based.yaml  # 距离目标分支
│   ├── branch-frequency-based.yaml  # 频率目标分支
│   └── edge-cases.yaml         # 边界情况用例
└── flow-edit-goal/
    └── ...
```

---

### Stage 5: 专项测试用例设计（SPECIALIZED_TEST_DESIGN）

**目的**: 设计性能、安全、可访问性测试用例

**步骤**:
```bash
# Step 5.1: 性能测试用例
python -m orchestrator start . s5_1_performance_tests

# Step 5.2: 安全测试用例
python -m orchestrator start . s5_2_security_tests

# Step 5.3: 可访问性测试用例
python -m orchestrator start . s5_3_accessibility_tests

# Step 5.4: 汇总专项测试报告
python -m orchestrator start . s5_4_assemble_specialized_report
```

**处理内容**:

1. **性能测试用例**
   ```yaml
   # test-cases/performance/load-tests.yaml
   performance_tests:
     - test_id: "PERF-001"
       title: "目标列表加载性能"
       type: "load_test"
       target: "goal-list-page"
       metrics:
         - metric: "page_load_time"
           threshold: "<= 2s"
           percentile: "p95"
         - metric: "time_to_interactive"
           threshold: "<= 3s"
           percentile: "p95"
       load_profile:
         virtual_users: 100
         ramp_up_duration: "60s"
         test_duration: "300s"

   stress_tests:
     - test_id: "PERF-002"
       title: "并发创建目标压力测试"
       type: "stress_test"
       metrics:
         - metric: "success_rate"
           threshold: ">= 99%"
         - metric: "response_time"
           threshold: "<= 1s"
           percentile: "p99"
       load_profile:
         virtual_users: 500
         ramp_up_duration: "30s"
         test_duration: "600s"
   ```

2. **安全测试用例**
   ```yaml
   # test-cases/security/auth-tests.yaml
   security_tests:
     - test_id: "SEC-001"
       title: "用户认证测试"
       category: "authentication"
       threats:
         - "SQL 注入"
         - "XSS 攻击"
         - "CSRF 攻击"
       test_cases:
         - case_id: "SEC-001-01"
           title: "登录 SQL 注入防护"
           attack_vector: "username=' OR '1'='1"
           expected_result: "登录失败，显示通用错误"
         - case_id: "SEC-001-02"
           title: "Session 劫持防护"
           test_scenario: "检查 session token 安全性"
           expected_result: "token 加密存储，httpOnly"

     - test_id: "SEC-002"
       title: "API 安全测试"
       category: "api_security"
       threats:
         - "未授权访问"
         - "数据泄露"
       test_cases:
         - case_id: "SEC-002-01"
           title: "未登录访问目标 API"
           request: "GET /api/goals"
           headers:
             Authorization: ""
           expected_result: "401 Unauthorized"
   ```

3. **可访问性测试用例**
   ```yaml
   # test-cases/accessibility/wcag-tests.yaml
   accessibility_tests:
     - test_id: "A11Y-001"
       title: "WCAG 2.1 AA 合规性测试"
       standard: "WCAG 2.1 AA"
       test_criteria:
         - criterion: "1.1.1 Non-text Content"
           test_cases:
             - "所有图片都有 alt 属性"
             - "图标有 aria-label"
         - criterion: "2.1.1 Keyboard"
           test_cases:
             - "所有功能可通过键盘访问"
             - "Tab 键导航顺序合理"
         - criterion: "1.4.3 Contrast (Minimum)"
           test_cases:
             - "文本与背景对比度 >= 4.5:1"
             - "大文本对比度 >= 3:1"

       test_results:
         automated_checks:
           tool: "axe-playwright"
           passed: 45
           failed: 2
           warnings: 3

         manual_checks:
           - "键盘导航测试"
           - "屏幕阅读器测试"
   ```

**输出**:
```yaml
# test-case-design/specialized-tests.yaml
specialized_test_summary:
  performance_tests:
    total: 15
    automated: 12
    manual: 3

  security_tests:
    total: 20
    categories:
      - authentication: 5
      - authorization: 4
      - injection_attacks: 6
      - data_protection: 5

  accessibility_tests:
    total: 25
    wcag_level: "AA"
    automated_coverage: "80%"
```

---

### Stage 6: 用例评审（TEST_CASE_REVIEW）

**目的**: 人类介入评审测试用例，确保质量和覆盖度

**步骤**:
```bash
# Step 6.1: 准备评审包
python -m orchestrator start . s6_1_prepare_review_package

# Step 6.2: 人类评审（需要人类审批）
python -m orchestrator review . s6_2_human_review

# 如果评审被拒绝，执行 Step 6.3
python -m orchestrator start . s6_3_incorporate_feedback
```

**评审包内容**:
```yaml
# review/test-case-review-package.yaml
review_package_id: "REVIEW-2026-001"
prepared_at: "2026-02-04T15:00:00Z"
prepared_by: "agent.qa.feature_calibration_agent"

summary:
  total_test_cases: 120
  breakdown:
    smoke: 15
    functional: 65
    branch: 40
  automated_cases: 85
  automation_rate: 70.8%

test_case_inventory:
  - category: "smoke"
    cases: 15
    coverage: "100%"
  - category: "functional"
    cases: 65
    coverage: "100%"
  - category: "branch"
    cases: 40
    coverage: "95%"
  - category: "performance"
    cases: 15
    coverage: "100%"
  - category: "security"
    cases: 20
    coverage: "100%"
  - category: "accessibility"
    cases: 25
    coverage: "80%"

coverage_metrics:
  requirement_coverage: 100%
  feature_coverage: 100%
  ui_page_coverage: 100%
  decision_point_coverage: 95%

quality_metrics:
  case_quality_score: 8.5
  traceability: 100%
  clarity: 92%

risk_assessment:
  high_risk_areas: []
  medium_risk_areas:
    - area: "可访问性测试"
      reason: "自动化覆盖不足 80%，需要补充手工测试"
      mitigation: "增加手工测试用例"

  recommendations:
    - "补充可访问性手工测试用例"
    - "所有用例质量良好，建议批准"
```

**评审标准**:
- 覆盖度完整性 >= 90%
- 用例质量评分 >= 8/10
- 需求可追溯性 = 100%
- 高风险点覆盖 = 100%

**评审流程**:

1. **评审者收到通知**
   ```bash
   # 评审者查看评审包
   cat review/test-case-review-package.yaml

   # 查看详细用例
   ls test-cases/
   ```

2. **评审者审批或拒绝**
   ```bash
   # 批准
   python -m orchestrator approve . s6_2_human_review \
     --approver "qa-lead" \
     --decision "approve" \
     --comments "质量良好，批准进入下一阶段"

   # 拒绝
   python -m orchestrator approve . s6_2_human_review \
     --approver "qa-lead" \
     --decision "reject" \
     --comments "需要补充可访问性测试用例"
   ```

3. **如果被拒绝，融入反馈**
   ```yaml
   # review/test-case-review-feedback.yaml
   review_id: "REVIEW-2026-001"
   decision: "rejected"
   reviewed_by: "qa-lead"
   reviewed_at: "2026-02-04T16:00:00Z"

  feedback_items:
    - category: "coverage"
      severity: "major"
      description: "可访问性测试覆盖不足"
      affected_cases: []
      suggested_fix: "补充 5 个可访问性手工测试用例"

  required_changes:
    - case_id: "NEW-A11Y-001"
      change_type: "add"
      description: "添加键盘导航测试用例"
    - case_id: "NEW-A11Y-002"
      change_type: "add"
      description: "添加屏幕阅读器测试用例"

  revision_deadline: "2026-02-05T18:00:00Z"
   ```

**超时处理**:
- 24 小时未评审：通知 qa_lead
- 48 小时未评审：通知 qa_lead, tech_lead, pm
- 72 小时未评审：升级到治理层

---

### Stage 7: Playwright 脚本生成（PLAYWRIGHT_GENERATION）

**目的**: 基于评审通过的测试用例生成 Playwright E2E 脚本

**步骤**:
```bash
# Step 7.1: 生成 Playwright 测试规范
python -m orchestrator start . s7_1_generate_playwright_specs

# Step 7.2: 生成辅助函数
python -m orchestrator start . s7_2_generate_helpers

# Step 7.3: 生成配置文件
python -m orchestrator start . s7_3_generate_config

# Step 7.4: 生成测试数据
python -m orchestrator start . s7_4_generate_test_data

# Step 7.5: 验证脚本质量
python -m orchestrator start . s7_5_validate_scripts

# Step 7.6: 生成文档
python -m orchestrator start . s7_6_generate_documentation
```

**处理内容**:

1. **生成测试规范文件**
   ```typescript
   // e2e-scripts/playwright/specs/smoke/core-flow.spec.ts
   import { test, expect } from '@playwright/test';
   import { GoalPage } from '../../helpers/page-objects';

   test.describe('Smoke Tests: Core Flow', () => {
     let goalPage: GoalPage;

     test.beforeEach(async ({ page }) => {
       goalPage = new GoalPage(page);
       await goalPage.login();
     });

     test('F-SMOKE-001: Create goal successfully', async ({ page }) => {
       // 用例 ID: F-SMOKE-001
       // 需求 ID: REQ-2026-001
       // 功能点: goal-management

       await goalPage.goto();
       await goalPage.clickCreateButton();
       await goalPage.selectGoalType('time-based');
       await goalPage.enterGoalName('Morning Run');
       await goalPage.enterTarget('30', 'minutes');
       await goalPage.submit();

       await expect(page.locator('[data-testid="goal-card"]')).toContainText('Morning Run');
     });

     test.afterEach(async ({ page }) => {
       await goalPage.cleanup();
     });
   });
   ```

2. **生成辅助函数**
   ```typescript
   // e2e-scripts/playwright/helpers/page-objects.ts
   export class GoalPage {
     readonly page: Page;
     readonly createButton: Locator;
     readonly goalTypeSelector: Locator;
     readonly goalNameInput: Locator;
     readonly targetValueInput: Locator;
     readonly submitButton: Locator;
     readonly successMessage: Locator;

     constructor(page: Page) {
       this.page = page;
       this.createButton = page.locator('[data-testid="create-goal-button"]');
       this.goalTypeSelector = page.locator('[data-testid="goal-type-selector"]');
       this.goalNameInput = page.locator('[data-testid="goal-name-input"]');
       this.targetValueInput = page.locator('[data-testid="target-value-input"]');
       this.submitButton = page.locator('[data-testid="submit-button"]');
       this.successMessage = page.locator('[data-testid="success-message"]');
     }

     async goto() {
       await this.page.goto('/goals');
     }

     async clickCreateButton() {
       await this.createButton.click();
     }

     async selectGoalType(type: string) {
       await this.goalTypeSelector.selectOption(type);
     }

     async enterGoalName(name: string) {
       await this.goalNameInput.fill(name);
     }

     async enterTarget(value: string, unit: string) {
       await this.targetValueInput.fill(value);
       // ... 选择单位
     }

     async submit() {
       await this.submitButton.click();
     }

     async cleanup() {
       // 清理测试数据
     }
   }
   ```

3. **生成配置文件**
   ```typescript
   // e2e-scripts/playwright/config/playwright.config.ts
   import { defineConfig, devices } from '@playwright/test';

   export default defineConfig({
     testDir: './specs',
     fullyParallel: true,
     forbidOnly: !!process.env.CI,
     retries: process.env.CI ? 2 : 0,
     workers: process.env.CI ? 1 : undefined,
     reporter: 'html',

     use: {
       baseURL: process.env.BASE_URL || 'http://localhost:3000',
       trace: 'on-first-retry',
       screenshot: 'only-on-failure',
     },

     projects: [
       {
         name: 'chromium',
         use: { ...devices['Desktop Chrome'] },
       },
       {
         name: 'firefox',
         use: { ...devices['Desktop Firefox'] },
       },
       {
         name: 'webkit',
         use: { ...devices['Desktop Safari'] },
       },
       {
         name: 'Mobile Chrome',
         use: { ...devices['Pixel 5'] },
       },
     ],
   });
   ```

4. **生成测试数据**
   ```json
   // e2e-scripts/test-data/users.json
   {
     "test_users": [
       {
         "user_id": "test-user-001",
         "username": "testuser1",
         "email": "testuser1@example.com",
         "role": "user"
       },
       {
         "user_id": "test-admin-001",
         "username": "testadmin",
         "email": "testadmin@example.com",
         "role": "admin"
       }
     ]
   }

   // e2e-scripts/test-data/scenarios.json
   {
     "goal_scenarios": [
       {
         "scenario_id": "scenario-001",
         "goal_type": "time-based",
         "goal_name": "Morning Run",
         "target_value": 30,
         "target_unit": "minutes",
         "expected_success": true
       },
       {
         "scenario_id": "scenario-002",
         "goal_type": "distance-based",
         "goal_name": "Marathon Training",
         "target_value": 42,
         "target_unit": "km",
         "expected_success": true
      }
     ]
   }
   ```

5. **验证脚本质量**
   ```yaml
   # e2e-scripts/validation-report.yaml
   validation_id: "VALIDATE-2026-001"
   validated_at: "2026-02-04T17:00:00Z"

   syntax_check:
     status: "PASSED"
     files_checked: 45
     errors: 0
     warnings: 3

   best_practices:
     status: "PASSED"
     score: 9.2
     checks:
       - check: "page_objects_used"
         status: "PASS"
         coverage: "100%"
       - check: "test_data_separation"
         status: "PASS"
         coverage: "100%"
       - check: "proper_waits"
         status: "PASS"
         coverage: "100%"

   maintainability_index:
     overall_score: 8.5
     code_duplication: "5%"
     average_complexity: "low"
     test_organization: "excellent"

   coverage_estimation:
     test_case_coverage: "100%"
     automated_cases: 85
     manual_cases: 35
     automation_rate: "70.8%"
   ```

6. **生成文档**
   ```markdown
   <!-- e2e-scripts/README.md -->
   # E2E Playwright 测试脚本

   ## 设置说明

   \`\`\`bash
   # 安装依赖
   npm install

   # 安装 Playwright 浏览器
   npx playwright install
   \`\`\`

   ## 执行指南

   \`\`\`bash
   # 运行所有测试
   npx playwright test

   # 运行冒烟测试
   npx playwright test --grep @smoke

   # 运行特定测试文件
   npx playwright test specs/smoke/core-flow.spec.ts

   # 调试模式
   npx playwright test --debug
   \`\`\`

   ## 测试覆盖

   - 冒烟测试: 15 个用例
   - 功能测试: 65 个用例
   - 分支测试: 40 个用例

   ## 故障排除

   ### 常见问题

   **Q: 测试超时怎么办？**
   A: 增加 `testTimeout` 配置或检查网络环境

   **Q: 如何调试失败的测试？**
   A: 使用 `--debug` 模式或查看 trace 文件
   ```

---

### Stage 8: 产物归档（ARTIFACT_FREEZE）

**目的**: 冻结所有产物，准备交付

**步骤**:
```bash
# Step 8.1: 创建交付包
python -m orchestrator start . s8_1_create_delivery_package

# Step 8.2: 生成指标报告
python -m orchestrator start . s8_2_generate_metrics
```

**交付包结构**:
```
delivery/test-case-design-package/
├── README.md                            # 交付说明
├── test-case-design/                    # 设计文档
├── test-cases/                          # 测试用例
├── e2e-scripts/                         # E2E 脚本
├── review/                              # 评审记录
└── delivery-manifest.yaml               # 交付清单
```

**交付清单**:
```yaml
# delivery/delivery-manifest.yaml
delivery_id: "DELIVERY-2026-001"
delivered_at: "2026-02-04T18:00:00Z"
delivered_by: "workflow.test_case_design_pipeline"

package_contents:
  test_case_design:
    files: 4
    artifacts:
      - "requirement-alignment.yaml"
      - "feature-calibration.yaml"
      - "branch-coverage.yaml"
      - "specialized-tests.yaml"

  test_cases:
    total: 120
    breakdown:
      smoke: 15
      functional: 65
      branch: 40
      performance: 15
      security: 20
      accessibility: 25

  e2e_scripts:
    total_files: 45
    test_specs: 35
    helpers: 5
    config_files: 3
    test_data_files: 2

  review_artifacts:
    files: 3
    approval_status: "approved"

quality_metrics:
  coverage:
    requirement_coverage: 100%
    feature_coverage: 100%
    ui_page_coverage: 100%
  quality:
    case_quality_score: 8.5
    traceability: 100%
  automation:
    automation_rate: 70.8%
    playwright_coverage: 70.8%

signatures:
  qa_design: "agent.qa.feature_calibration_agent"
  qa_review: "qa-lead"
```

---

## 使用示例

### 完整命令行示例

#### 示例 1: 新功能测试设计

```bash
# 1. 创建工作目录
cd project/ai-marathon-coach
mkdir -p test-design

# 2. 初始化工作流
cd test-design
python -m orchestrator init . \
  --workflow ai-spec/specs/org/qa/workflows/test-case-design-pipeline/v1/workflow.yaml \
  --inputs \
    prd=../prd/contracts/frozen-detailed-prd-contract/v1/prd-ai-marathon-coach-v1.0.yaml \
    technical_architecture=../dev/contracts/frozen-technical-architecture-contract/v1/arch-ai-marathon-coach-v1.0.yaml \
    ui_prototype=../ui/contracts/frozen-ui-prototype-contract/v1/prototype-ai-marathon-coach-v1.0.yaml \
    ui_page=../ui/contracts/ui-page-contract/v1/pages-ai-marathon-coach.yaml

# 3. 检查状态
python -m orchestrator status .

# 4. 执行工作流（自动推进到人类介入点）
python -m orchestrator start . --auto

# 5. 等待人类评审
# 评审者查看评审包
cat review/test-case-review-package.yaml

# 6. 人类审批
python -m orchestrator approve . s6_2_human_review \
  --approver "zhang-san" \
  --decision "approve" \
  --comments "质量良好，批准"

# 7. 继续执行剩余步骤
python -m orchestrator start . --auto

# 8. 查看最终产物
ls delivery/test-case-design-package/
```

#### 示例 2: 回归测试用例补充

```bash
# 1. 仅执行分支覆盖用例设计
python -m orchestrator start . s4_branch_coverage \
  --skip-stages "s5_specialized_tests"

# 2. 查看生成的分支用例
cat test-cases/functional/branch-coverage/flow-create-goal/branch-time-based.yaml

# 3. 生成对应的 Playwright 脚本
python -m orchestrator start . s7_playwright_generation \
  --input-cases "test-cases/functional/branch-coverage/"
```

#### 示例 3: 专项测试补充

```bash
# 1. 仅执行专项测试设计
python -m orchestrator start . s5_specialized_tests

# 2. 查看性能测试用例
cat test-cases/performance/load-tests.yaml

# 3. 查看安全测试用例
cat test-cases/security/auth-tests.yaml
```

### 使用 Orchestrator 批处理

```bash
# 批量处理多个项目
for project in project-1 project-2 project-3; do
  cd $project/test-design
  python -m orchestrator start . --auto
  cd ../..
done
```

---

## 故障排查

### 常见问题和解决方案

#### 问题 1: 输入契约验证失败

**错误信息**:
```
Error: Input validation failed - PRD status is not frozen
```

**原因**:
- PRD 契约状态不是 `frozen`

**解决方案**:
```bash
# 检查 PRD 状态
cat ../prd/contracts/frozen-detailed-prd-contract/v1/prd.yaml | grep status

# 如果状态不是 frozen，需要先冻结 PRD
# 联系产品经理完成 PRD 冻结流程
```

#### 问题 2: 需求对齐失败

**错误信息**:
```
Error: Requirement alignment failed - 3 requirements not mapped to UI
```

**原因**:
- PRD 中的需求在 UI 原型中没有对应设计

**解决方案**:
```yaml
# 查看对齐报告
cat test-case-design/requirement-alignment.yaml

# 报告会列出所有未映射的需求
gaps_identified:
  - requirement_id: "REQ-2026-025"
    missing_artifact: "ui_design"
    impact: "无法设计对应测试用例"

# 解决方案：
# 1. 联系 UI 设计师补充缺失的设计
# 2. 或者从 PRD 中移除该需求
# 3. 重新运行工作流
```

#### 问题 3: 评审被拒绝

**错误信息**:
```
Review rejected - Need to add 5 accessibility test cases
```

**原因**:
- 评审者认为测试覆盖不足

**解决方案**:
```bash
# 1. 查看评审反馈
cat review/test-case-review-feedback.yaml

# 2. 融入反馈，修订用例
python -m orchestrator start . s6_3_incorporate_feedback

# 3. 重新提交评审
python -m orchestrator review . s6_2_human_review
```

#### 问题 4: Playwright 脚本生成失败

**错误信息**:
```
Error: Cannot find page object for 'goal-list-page'
```

**原因**:
- UI 页面契约中缺少选择器定义

**解决方案**:
```bash
# 1. 检查 UI 页面契约
cat ../ui/contracts/ui-page-contract/v1/pages.yaml | grep -A 10 "goal-list-page"

# 2. 确保包含选择器和 test_ids
pages:
  - page_id: "goal-list-page"
    selectors:
      web: ".goal-list"
      wechat: ".goal-list"
    test_ids:
      - "goal-create-button"
      - "goal-card"

# 3. 重新生成脚本
python -m orchestrator start . s7_1_generate_playwright_specs
```

#### 问题 5: 人类评审超时

**错误信息**:
```
Warning: Review timeout - 72 hours exceeded
```

**原因**:
- 评审者在 72 小时内没有审批

**解决方案**:
```bash
# 1. 查看评审状态
python -m orchestrator status .

# 2. 升级到管理层
# 系统会自动通知 qa_lead、tech_lead、pm

# 3. 管理层可以：
#    - 延长评审期限
#    - 指定新的评审者
#    - 强制批准（需签字）
```

### 调试技巧

#### 启用详细日志

```bash
# 设置环境变量
export ORCHESTRATOR_LOG_LEVEL=debug

# 重新运行工作流
python -m orchestrator start . --auto
```

#### 检查工作流状态

```bash
# 查看当前状态
python -m orchestrator status .

# 查看详细状态
python -m orchestrator status . --verbose

# 查看某个步骤的输出
cat .workflow/stages/s2_requirement_alignment/outputs/requirement-alignment.yaml
```

#### 重试失败的步骤

```bash
# 重试特定步骤
python -m orchestrator start . s3_feature_calibration --retry

# 跳过某些步骤
python -m orchestrator start . s4_branch_coverage \
  --skip-stages "s1_input_validation,s2_requirement_alignment"
```

---

## 最佳实践

### 1. 需求冻结是前提

**为什么重要**:
- 需求变更会导致测试用例失效
- 重复设计浪费时间和资源

**最佳实践**:
```bash
# 确保所有契约状态为 frozen
for contract in prd arch ui; do
  cat ../$contract/contracts/*/v1/*.yaml | grep status
done

# 输出应该都是：
# status: frozen
```

### 2. 分阶段设计

**推荐顺序**:
1. 先设计冒烟测试用例（核心功能）
2. 再设计功能测试用例（完整覆盖）
3. 然后设计分支测试用例（边界情况）
4. 最后设计专项测试用例（性能、安全）

**为什么重要**:
- 渐进式设计，容易验证
- 早期发现问题，早期修复
- 避免后期大规模返工

### 3. 充分利用自动化

**自动化的优势**:
- 70%+ 的用例可以自动化
- 减少重复劳动
- 提高测试效率

**最佳实践**:
```typescript
// 使用 Page Object 模式
export class GoalPage {
  // 封装页面元素和操作
  async createGoal(goal: GoalData) {
    await this.goto();
    await this.clickCreateButton();
    await this.fillGoalForm(goal);
    await this.submit();
    return this;
  }
}

// 测试用例变得简洁
test('create goal', async ({ page }) => {
  const goalPage = new GoalPage(page);
  await goalPage.createGoal({
    type: 'time-based',
    name: 'Morning Run',
    target: 30
  });
  await expect(goalPage.successMessage).toBeVisible();
});
```

### 4. 严格评审机制

**评审要点**:
- 覆盖度是否完整？
- 用例质量是否达标？
- 需求追溯是否清晰？

**最佳实践**:
```yaml
# 评审前自检
python -m orchestrator validate . s6_test_case_review \
  --criteria coverage_completeness \
  --threshold 90

# 如果不满足，自动补充用例
python -m orchestrator start . s5_specialized_tests \
  --target-coverage 95
```

### 5. 持续改进

**收集指标**:
- 测试用例总数
- 自动化率
- 执行时间
- 缺陷发现率

**最佳实践**:
```yaml
# 每个迭代后分析指标
cat delivery/metrics.yaml

# 对比历史数据
# 找出改进空间
# 优化工作流配置
```

---

## 常见问题

### Q1: 工作流执行需要多长时间？

**A**: 取决于项目规模

| 项目规模 | 用例数 | 执行时间 |
|---------|-------|---------|
| 小型 | 50-100 | 2-4 小时 |
| 中型 | 100-200 | 4-8 小时 |
| 大型 | 200+ | 8-16 小时 |

**注意**: 不包括人类评审时间（通常 24-72 小时）

### Q2: 可以只执行部分阶段吗？

**A**: 可以

```bash
# 只执行分支覆盖设计
python -m orchestrator start . s4_branch_coverage

# 只执行专项测试设计
python -m orchestrator start . s5_specialized_tests

# 只生成 Playwright 脚本
python -m orchestrator start . s7_playwright_generation
```

### Q3: 如何处理需求变更？

**A**:

1. **小变更**: 增量更新测试用例
   ```bash
   # 只更新变更的部分
   python -m orchestrator start . s3_feature_calibration \
     --update-only "goal-management"
   ```

2. **大变更**: 重新运行完整工作流
   ```bash
   # 重新设计所有测试用例
   python -m orchestrator start . --auto
   ```

3. **重大变更**: 先冻结新的 PRD，再运行工作流

### Q4: 生成的 Playwright 脚本可以直接运行吗？

**A**: 大部分可以，但可能需要调整

**自动运行**:
- 70-80% 的脚本可以直接运行
- 冒烟测试通常可以直接运行

**需要调整**:
- 复杂的业务逻辑
- 需要特殊测试数据的场景
- 依赖第三方服务的场景

**最佳实践**:
```bash
# 先在本地运行冒烟测试
npx playwright test specs/smoke/

# 修复失败用例
# 逐步扩展到完整测试套件
```

### Q5: 如何保证测试用例的质量？

**A**: 三重保障

1. **自动化检查**
   - Schema 验证
   - 语法检查
   - 最佳实践检查

2. **人类评审**
   - 覆盖度检查
   - 质量评分
   - 风险评估

3. **实际执行**
   - 先运行冒烟测试
   - 逐步扩展
   - 发现问题及时修复

### Q6: 可以自定义工作流吗？

**A**: 可以

**修改工作流配置**:
```yaml
# workflow.yaml
stages:
  - id: s5_specialized_tests
    # 可以添加新的测试类型
    steps:
      - id: s5_4_custom_tests
        name: "自定义测试用例"
        run: agent.qa.custom_test_agent
```

**添加自定义 Agent**:
```yaml
# agents/custom-test-agent/v1/agent.yaml
id: agent.qa.custom_test_agent
name: Custom Test Agent
# ...
```

### Q7: 工作流失败后如何恢复？

**A**:

```bash
# 1. 查看失败原因
python -m orchestrator status . --verbose

# 2. 修复问题

# 3. 从失败点继续
python -m orchestrator start . --resume

# 或者重新运行特定阶段
python -m orchestrator start . s3_feature_calibration --retry
```

---

## 附录

### 相关文档

- [工作流定义](./workflow.yaml)
- [测试用例设计契约](../../contracts/test-case-design-contract/v1/schema.yaml)
- [测试用例契约](../../contracts/test-case/v1/schema.yaml)
- [E2E 脚本契约](../../contracts/e2e-script-contract/v1/schema.yaml)
- [Lee 框架文档](https://lee-framework.dev/docs)

### 版本历史

- v1.0 (2026-02-04) - 初始版本
  - 支持需求对齐、功能校准、分支覆盖、专项测试
  - 支持人类评审机制
  - 支持 Playwright 脚本自动生成

### 联系方式

- **维护者**: qa-design-team
- **最后更新**: 2026-02-04
- **反馈渠道**: [提交 Issue](https://github.com/org/qa-specs/issues)

---

**本文档遵循 LEE 框架文档规范，使用契约化管理和自动化流程。**
