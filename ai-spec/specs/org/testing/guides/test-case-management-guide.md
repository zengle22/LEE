# Test Case Management Guide
# 测试用例管理完整指南

> **版本:** v1.0
> **创建日期:** 2026-01-15
> **适用范围:** 所有使用Testing Workflow v2.0的项目

---

## 📋 目录

1. [概述](#概述)
2. [从需求到用例的全流程](#从需求到用例的全流程)
3. [用例编写规范](#用例编写规范)
4. [测试套件组织](#测试套件组织)
5. [测试计划管理](#测试计划管理)
6. [需求追溯矩阵](#需求追溯矩阵)
7. [用例执行与维护](#用例执行与维护)
8. [最佳实践](#最佳实践)

---

## 概述

### 测试用例管理体系

```
需求文档 (PRD/User Story)
    ↓
测试计划 (Test Plan)
    ↓
测试套件 (Test Suite)
    ↓
测试用例 (Test Case)
    ↓
自动化脚本 (Automation Script)
    ↓
执行结果 (Test Report)
    ↓
Bug契约 (Bug Contract)
```

### 核心契约文件

| 契约类型 | Schema路径 | 用途 |
|---------|-----------|------|
| Test Case | `contracts/test-case/v1/schema.yaml` | 单个测试用例定义 |
| Test Suite | `contracts/test-suite/v1/schema.yaml` | 测试套件组织 |
| Test Plan | `contracts/test-plan/v1/schema.yaml` | 整体测试计划 |

---

## 从需求到用例的全流程

### Step 1: 需求分析

**输入:** PRD文档或User Story

**活动:**
1. 识别功能点
2. 提取验收标准
3. 识别风险区域

**输出:** 需求清单 + 验收标准

```yaml
# 示例：需求分析输出
requirement:
  id: REQ-2026-005
  title: "跑者画像 - 年龄输入"
  user_story: "作为用户，我想输入我的年龄，以便系统生成适合我的训练计划"

  acceptance_criteria:
    - "用户可以输入年龄"
    - "年龄必须在15-80之间"
    - "无效年龄显示错误提示"
    - "有效年龄可以继续下一步"

  risk_areas:
    - "边界值验证"
    - "输入格式验证"
```

---

### Step 2: 测试计划编写

**负责人:** QA Lead

**活动:**
1. 确定测试目标和范围
2. 制定测试策略（多轮、回归策略）
3. 选择测试套件
4. 分配资源和时间表

**输出:** Test Plan Contract

```bash
# 创建测试计划
project/
└── testing/
    └── test-plans/
        └── PLAN-2026-001.yaml  # 按test-plan schema填写
```

**模板使用:**

```yaml
plan_id: "PLAN-2026-001"
version: "v1.1.0"
target_release:
  release_version: "v1.1.0"
  release_date: "2026-01-20"

objectives:
  - "验证v1.1新功能正常工作"
  - "达到出测标准"

test_suites:
  - suite_id: "SUITE-SMOKE-001"
    execution_rounds: every
    priority: must
```

---

### Step 3: 测试用例设计

**负责人:** QA Engineer

**活动:**
1. 根据需求设计用例
2. 覆盖正向、负向、边界值场景
3. 关联需求ID（追溯）
4. 定义优先级

**输出:** Test Case Contract

#### 3.1 用例设计方法

**等价类划分:**
```
年龄输入：
- 有效等价类：15-80
- 无效等价类1：< 15
- 无效等价类2：> 80
- 无效等价类3：非数字
```

**边界值分析:**
```
边界值：14, 15, 16, 79, 80, 81
```

**场景组合:**
```
正向：输入28 → 接受 → 继续
负向：输入10 → 拒绝 → 错误提示
边界：输入15 → 接受（下限）
边界：输入80 → 接受（上限）
```

#### 3.2 用例编写

```yaml
# tests/cases/F-P1-002.yaml
case_id: "F-P1-002"
title: "年龄输入 - 边界值验证"
suite: e2e_chrome
priority: P1
type: boundary

traceability:
  requirement_id: "REQ-2026-005"
  feature_id: "runner-profile"
  acceptance_criteria: "年龄必须在15-80之间"

steps:
  - step_num: 1
    action: "输入年龄 10（低于下限）"
    expected: "显示错误提示：年龄需在15-80之间"

  - step_num: 2
    action: "输入年龄 85（高于上限）"
    expected: "显示错误提示：年龄需在15-80之间"

  - step_num: 3
    action: "输入年龄 15（下限边界）"
    expected: "接受输入，无错误提示"

  - step_num: 4
    action: "输入年龄 80（上限边界）"
    expected: "接受输入，无错误提示"

expected_result: "边界值验证正确，拒绝超出范围的输入"

automation:
  automated: true
  script_path: "tests/e2e/e2e-suite.spec.ts"
  framework: playwright

tags:
  - "validation"
  - "boundary"
  - "runner-profile"

status: approved
```

---

### Step 4: 测试套件组织

**负责人:** QA Lead + QA Engineer

**活动:**
1. 将用例按套件分类
2. 定义执行策略（顺序/并行）
3. 设置环境要求

**输出:** Test Suite Contract

#### 4.1 套件分类原则

**冒烟测试 (Smoke):**
- 只包含P0/P1核心流程用例
- 每轮必跑
- 顺序执行，fail_fast=true

**E2E测试:**
- 覆盖完整用户路径
- 每轮必跑
- 可并行执行

**回归测试 (Regression):**
- Bug修复相关用例
- 风险回归（不是每轮全量）
- 智能并行执行

**全量回归 (Full Regression):**
- 所有P0/P1/P2用例
- 仅最后一轮执行
- 并行执行

#### 4.2 套件创建

```yaml
# tests/suites/SUITE-SMOKE-001.yaml
suite_id: "SUITE-SMOKE-001"
name: "冒烟测试套件"
type: smoke

test_cases:
  - case_id: "F-BASE-002"
    enabled: true
    order: 1

  - case_id: "F-P1-004"
    enabled: true
    order: 2

execution_strategy:
  mode: sequential
  retry_on_failure: false
  fail_fast: true
  timeout_seconds: 600

environment:
  required_services:
    - "frontend"
    - "backend"
  browser: chromium

status: active
```

---

### Step 5: 自动化实现

**负责人:** Automation Engineer

**活动:**
1. 根据Test Case编写自动化脚本
2. 使用统一的框架（Playwright/Jest/Pytest）
3. 维护脚本与用例的双向关联

**输出:** 自动化脚本 + 更新Test Case的automation字段

#### 5.1 自动化脚本编写

```typescript
// tests/e2e/runner-profile.spec.ts

import { test, expect } from '@playwright/test'
import { uniButton } from '../helpers/selectors'

test.describe('F-P1-002: 年龄输入 - 边界值验证', () => {
  test.beforeEach(async ({ page }) => {
    // 登录并进入跑者画像页面
    await loginAndNavigateToProfile(page)
  })

  test('步骤1: 输入年龄10（低于下限）', async ({ page }) => {
    const ageInput = page.locator('input[placeholder*="年龄"]')
    await ageInput.fill('10')

    const nextButton = page.locator(uniButton('下一步'))
    await nextButton.click()

    await page.waitForTimeout(500)
    const errorMessage = page.locator('text=年龄需在 15-80 之间')
    await expect(errorMessage).toBeVisible()
  })

  test('步骤2: 输入年龄85（高于上限）', async ({ page }) => {
    // ...
  })

  test('步骤3: 输入年龄15（下限边界）', async ({ page }) => {
    // ...
  })

  test('步骤4: 输入年龄80（上限边界）', async ({ page }) => {
    // ...
  })
})
```

#### 5.2 更新Test Case

```yaml
# 更新 tests/cases/F-P1-002.yaml
automation:
  automated: true
  script_path: "tests/e2e/runner-profile.spec.ts"
  framework: playwright
```

---

### Step 6: 执行与报告

**负责人:** Test Executor (Agent或人工)

**活动:**
1. 按测试计划执行套件
2. 记录执行结果
3. 失败时创建Bug契约
4. 更新用例执行历史

**输出:** Test Report + Bug Contracts

#### 6.1 执行流程

```bash
# Round 1执行
python -m orchestrator start . s3_smoke

# 执行冒烟测试
npx playwright test tests/smoke/

# 如果失败 → 自动创建Bug契约
# bugs/BUG-2026-XXXX.contract.yaml
```

#### 6.2 更新用例执行历史

```yaml
# 自动追加到 tests/cases/F-P1-002.yaml
execution_history:
  - round_id: "TSTR-0001"
    executed_at: "2026-01-15T10:30:00Z"
    result: passed
    executor: "playwright-agent"
    duration_seconds: 15.2
    evidence:
      screenshot: "evidence/F-P1-002-passed.png"
```

---

## 用例编写规范

### 命名规范

**用例ID格式:**
```
{类型}-{模块}-{序号}

类型：
- F: 功能测试 (Functional)
- NF: 非功能测试 (Non-Functional)
- P: 性能测试 (Performance)
- S: 安全测试 (Security)

示例：
- F-BASE-002      # 功能-基础-002
- F-P1-001        # 功能-跑者画像Phase1-001
- NF-PERF-001     # 非功能-性能-001
```

**用例标题:**
```
{功能点} - {测试重点}

示例：
✅ "年龄输入 - 边界值验证"
✅ "开发测试登录 - 快速登录流程"
❌ "测试年龄"  (太简略)
❌ "验证用户在跑者画像页面输入年龄时系统对边界值的处理是否正确"  (太冗长)
```

### 步骤编写原则

**SMART原则:**
- **Specific** - 具体明确
- **Measurable** - 可度量
- **Actionable** - 可操作
- **Relevant** - 相关
- **Testable** - 可测试

**示例对比:**

❌ **不好的步骤:**
```yaml
- action: "测试登录"
  expected: "能登录"
```

✅ **好的步骤:**
```yaml
- action: "点击'开发测试登录'按钮"
  expected: "页面跳转到 /pages/runner-profile/index，token已存储"
```

### 优先级判定

| 优先级 | 定义 | 示例 |
|-------|------|------|
| P0 | 核心流程，阻塞上线 | 登录、支付、数据持久化 |
| P1 | 主要功能，影响大 | 表单验证、AI评估 |
| P2 | 次要功能，有规避 | 提示文案、边缘交互 |
| P3 | 体验优化，影响小 | UI细节、性能优化 |

### 测试数据管理

**数据驱动测试:**

```yaml
test_data:
  data_set: "age_boundary_values"
  inputs:
    valid_ages: [15, 20, 30, 50, 80]
    invalid_low: [0, 10, 14]
    invalid_high: [81, 100, 150]

  preconditions:
    user_state: "logged_in"
    profile_state: "empty"
```

---

## 测试套件组织

### 套件设计原则

**1. 单一职责**
- 每个套件聚焦一个测试目标
- 冒烟只测核心流程
- 回归只测Bug相关

**2. 合理粒度**
- 冒烟：5-15个用例
- E2E：10-30个用例
- 回归：动态（基于Bug数量）

**3. 独立性**
- 套件间可并行执行
- 用例间依赖最小化

### 套件类型与策略

| 套件类型 | 执行轮次 | 执行模式 | Fail Fast | 用例数量 |
|---------|---------|---------|-----------|---------|
| Smoke | 每轮必跑 | Sequential | Yes | 5-15 |
| E2E | 每轮必跑 | Parallel | No | 10-30 |
| Regression | 风险回归 | Smart Parallel | No | 动态 |
| Full Regression | 仅最后一轮 | Parallel | No | 全部P0/P1/P2 |
| Performance | 首轮+末轮 | Sequential | No | 5-10 |

---

## 测试计划管理

### 计划编写时机

**项目启动阶段:**
- PRD评审后
- 需求分析完成
- 架构设计确定

**输出:**
- 测试计划v1.0
- 风险清单
- 资源和时间表

### 计划审批流程

```
QA Lead编写 → Tech Lead审核 → PM审批 → 开始执行
```

### 计划跟踪

**进度跟踪:**
```yaml
execution_status:
  status: in_progress
  current_round: 2
  completion_percentage: 65

  actual_bugs_found:
    p0: 1
    p1: 0
    p2: 0

  vs_targets:
    p0: "1 vs 0 (超标)"
    pass_rate: "100% vs 95% (达标)"
```

**每轮更新:**
- 更新current_round
- 更新completion_percentage
- 更新actual_bugs_found
- 评估是否需要调整策略

---

## 需求追溯矩阵

### 什么是需求追溯

**双向追溯:**
```
需求 → 测试用例 (正向追溯)
测试用例 → 需求 (反向追溯)
```

### 追溯矩阵示例

| 需求ID | 需求标题 | 相关用例 | 覆盖率 | 状态 |
|-------|---------|---------|--------|------|
| REQ-2026-001 | 开发测试登录 | F-BASE-002 | 100% | ✅ |
| REQ-2026-005 | 年龄输入 | F-P1-002 | 100% | ✅ |
| REQ-2026-010 | AI评估 | F-P2-002 | 80% | ⚠️ |

### 生成追溯矩阵

**方法1: 从Test Case提取**

```bash
# 扫描所有用例文件
find tests/cases -name "*.yaml" | while read file; do
  req_id=$(yq '.traceability.requirement_id' $file)
  case_id=$(yq '.case_id' $file)
  echo "$req_id,$case_id"
done
```

**方法2: 使用Agent生成**

```python
# agent: requirement_tracer
def generate_traceability_matrix():
    matrix = {}

    for case_file in glob("tests/cases/*.yaml"):
        case = yaml.load(case_file)
        req_id = case['traceability']['requirement_id']

        if req_id not in matrix:
            matrix[req_id] = []

        matrix[req_id].append(case['case_id'])

    return matrix
```

### 追溯检查

**强制规则:**
- P0/P1用例必须有requirement_id
- 每个需求至少有1个用例覆盖

**检查命令:**

```bash
# 检查用例是否关联需求
python -m test_manager validate-traceability tests/cases/
```

---

## 用例执行与维护

### 执行流程

**自动化执行:**
```bash
# 执行单个套件
npx playwright test tests/suites/smoke/

# 执行所有E2E测试
npx playwright test tests/e2e/

# 执行指定用例
npx playwright test tests/e2e/runner-profile.spec.ts
```

**记录执行结果:**
- 自动更新execution_history
- 失败时创建Bug契约
- 生成测试报告

### 用例维护

**何时更新用例:**
1. 需求变更
2. Bug修复导致行为改变
3. 自动化脚本变更

**版本控制:**
```bash
# 用例文件Git管理
git add tests/cases/F-P1-002.yaml
git commit -m "feat(test): update F-P1-002 for new age validation rule"
```

**废弃用例:**
```yaml
status: deprecated
deprecation_reason: "功能已移除"
deprecated_at: "2026-01-20"
```

---

## 最佳实践

### ✅ DO - 应该做

**1. 需求驱动**
- 所有用例关联需求ID
- 验收标准即测试用例

**2. 优先级明确**
- P0/P1必须自动化
- 冒烟测试只包含P0/P1

**3. 可维护性**
- 用例描述清晰
- 步骤可复现
- 测试数据独立

**4. 追溯完整**
- 需求→用例双向追溯
- Bug→用例关联

**5. 持续更新**
- 需求变更及时同步
- 用例废弃及时标记

### ❌ DON'T - 不应该做

**1. 避免重复**
- 不同套件不重复相同用例
- 用例间避免重复步骤

**2. 避免依赖**
- 用例间避免强依赖
- 测试数据独立准备

**3. 避免模糊**
- 步骤不清晰
- 预期结果不明确

**4. 避免遗漏**
- P0用例无需求追溯
- 边界值未覆盖

---

## 工具推荐

### 用例管理工具

**当前方案: YAML文件 + Git**
- 优点：版本控制、可审查、契约化
- 缺点：需要手工维护

**可选工具:**
- TestRail (商业)
- Xray (Jira插件)
- qTest (商业)

### 自动化框架

| 测试类型 | 推荐框架 |
|---------|---------|
| E2E Web | Playwright |
| API | Postman / Rest-Assured |
| Unit | Jest / Pytest |
| Performance | JMeter / K6 |

---

## 示例项目结构

```
project/
├── requirements/
│   └── REQ-2026-005.md
│
├── testing/
│   ├── test-plans/
│   │   └── PLAN-2026-001.yaml
│   │
│   ├── test-suites/
│   │   ├── SUITE-SMOKE-001.yaml
│   │   ├── SUITE-E2E-001.yaml
│   │   └── SUITE-REGRESSION-001.yaml
│   │
│   ├── test-cases/
│   │   ├── F-BASE-002.yaml
│   │   ├── F-P1-001.yaml
│   │   ├── F-P1-002.yaml
│   │   └── ...
│   │
│   ├── traceability-matrix.csv
│   │
│   └── test-rounds/
│       ├── round-001/
│       └── round-002/
│
└── tests/
    ├── e2e/
    │   ├── login.spec.ts
    │   ├── runner-profile.spec.ts
    │   └── ...
    │
    ├── api/
    │   └── auth.spec.ts
    │
    └── helpers/
        └── selectors.ts
```

---

## 快速检查清单

### 用例编写完成清单

- [ ] case_id符合命名规范
- [ ] title简洁明确
- [ ] priority正确判定
- [ ] traceability.requirement_id已填写
- [ ] steps详细可操作
- [ ] expected_result明确
- [ ] automation.automated已标记
- [ ] tags合理分类
- [ ] status已设为approved

### 套件创建完成清单

- [ ] suite_id符合命名规范
- [ ] test_cases至少包含1个用例
- [ ] execution_strategy已定义
- [ ] environment要求已明确
- [ ] owner已指定
- [ ] status已设为active

### 测试计划完成清单

- [ ] objectives明确
- [ ] scope清晰（in_scope + out_of_scope）
- [ ] test_suites已选择
- [ ] schedule已制定
- [ ] quality_targets已设定
- [ ] risks已识别
- [ ] approved_by已签字

---

## 附录

### 相关文档

- [Test Case Contract Schema](../../contracts/test-case/v1/schema.yaml)
- [Test Suite Contract Schema](../../contracts/test-suite/v1/schema.yaml)
- [Test Plan Contract Schema](../../contracts/test-plan/v1/schema.yaml)
- [Testing Workflow v2.0 USAGE-GUIDE](../../workflows/test-main-pipeline/v2/USAGE-GUIDE.md)

### 模板文件

- Test Case Template: `templates/test-case-template.yaml`
- Test Suite Template: `templates/test-suite-template.yaml`
- Test Plan Template: `templates/test-plan-template.yaml`

---

**文档维护者:** test-governance
**最后更新:** 2026-01-15
**版本:** v1.0
**反馈渠道:** 提交Issue到项目仓库
