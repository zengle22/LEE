---
title: Spec-Global Workflows Catalog
author: LEE Team
date: 2026-01-29
version: 1.0
last_updated: 2026-02-19
---

# Spec-Global Workflows Catalog

> **LEE Orchestrator v3.1 - 全流程清单**
>
> 文档版本: 1.1
> 创建日期: 2026-01-28
> 更新日期: 2026-01-28
> 状态: ✅ 已完成

---

## 📋 目录

- [一、概览](#一概览)
- [二、L1 工作流（项目级）](#二l1-工作流项目级)
- [三、L2 工作流（部门级）](#三l2-工作流部门级)
- [四、L3 工作流（任务级）](#四l3-工作流任务级)
- [五、跨工作流关系图](#五跨工作流关系图)
- [六、统计摘要](#六统计摘要)

---

## 一、概览

### 1.1 层级定义

| 层级 | level 值 | 物理目录 | 职责 | 数量 |
|------|----------|----------|------|------|
| **L1** | `project` | `cross/workflows/project/` | 跨部门编排，串联多个 L2 | 2 |
| **L2** | `department` | `departments/{dept}/workflows/` | 部门专业流程，输出标准化产物 | 6 |
| **L3** | `task` | `cross/workflows/task/` 或 `departments/{dept}/workflows/子目录/` | 最小执行单元，可被 L2 spawn | 5 |

### 1.2 部门映射

| 部门 | 代码 | L2 工作流 | L3 工作流 |
|------|------|-----------|-----------|
| 产品部 | `prd` | 2 | - |
| 开发部 | `dev` | 1 | 2 |
| 测试部 | `qa` | 1 | 2 |
| 设计部 | `ui` | 1 | - |
| 策略部 | `stg` | 1 | - |
| 办公室 | `office` | - | - |

### 1.3 工作流命名规范

```
workflow.{scope}.{name}

scope 规则：
- L1: cross
- L2: {department} (prd/dev/qa/ui/stg)
- L3 跨部门: cross.task.*
- L3 部门内: {department}.task.*
```

---

## 二、L1 工作流（项目级）

### 2.1 产品 MVP 工作流 ⭐

**ID**: `workflow.cross.product_mvp`
**路径**: `cross/workflows/project/product-mvp/v1/workflow.yaml`
**Level**: `project` (L1)
**Owner**: 跨部门（`departments/office`）

#### 功能描述

这是 LEE 系统的核心 L1 工作流，负责串行编排各部门 L2 流程，完成产品 MVP 的完整开发。

**核心设计思想**：
- **L1 不做具体工作，只负责编排**
- **每个 L2 输出"冻结包"作为下一个 L2 的输入**
- **冻结包是部门间交接的唯一合法形式**
- **上游 L2 未完成，下游 L2 不得启动**

**流程概览**：

```
Step 1: STG → 产出"商业机会冻结包"
   ↓
Step 2: PRD → 接收"商业机会冻结包"，产出"研发冻结包"
   ↓
Step 3: UI → 接收"商业机会冻结包"，产出"原型冻结包"
   ↓
Step 4: Dev → 接收"研发冻结包"+"原型冻结包"，产出"提测冻结包"
   ↓
Step 5: QA → 接收"提测冻结包"，产出"可交付版本"
   ↓
Step 6: Release → 最终发布批准（Human Gate）
```

#### 6 个步骤详解

**Step 1: STG - 商业机会发现（L2）**

- **L2 工作流**: `workflow.stg.opportunity_discovery`
- **输入**: 无（L1 起点）
- **输出**: `business_opportunity_freeze.yaml`（商业机会冻结包）
- **职责**:
  - 定义我们要做什么生意？（一句话机会定义）
  - 目标用户是谁？
  - 为什么是现在？（Why Now）
  - 风险是什么？（Reasons NOT to Do）
- **Human Gate**: `stg_lead` + `product_lead` 双重审批

**Step 2: PRD - 产品需求冻结（L2）**

- **L2 工作流**: `workflow.prd.product_to_dev_pipeline`
- **输入**: `business_opportunity_freeze.yaml`
- **输出**: `dev_freeze_package.yaml`（研发冻结包）
- **职责**:
  - 将商业机会转化为产品需求
  - 定义验收标准
  - 编写技术规格
- **Human Gate**: `prd_lead` + `dev_lead` 双重审批

**Step 3: UI - 原型设计冻结（L2）**

- **L2 工作流**: `workflow.ui.design_pipeline`
- **输入**: `business_opportunity_freeze.yaml`
- **输出**: `prototype_freeze_package.yaml`（原型冻结包）
- **职责**:
  - 基于商业机会设计用户界面
  - 定义交互流程
  - 设计视觉规范
- **Human Gate**: `ui_lead` + `product_lead` 双重审批

**Step 4: Dev - 研发实现（L2）**

- **L2 工作流**: `workflow.dev.development_pipeline`
- **输入**:
  - `dev_freeze_package.yaml`（研发冻结包）
  - `prototype_freeze_package.yaml`（原型冻结包）
- **输出**: `test_submission_freeze_package.yaml`（提测冻结包）
- **职责**:
  - 解冻研发规格，理解需求
  - 参考 UI 原型进行开发
  - 执行 OpenSpec 13 步流程
  - 完成代码、测试、评审
- **Human Gate**: `dev_lead` + `qa_lead` 双重审批

**Step 5: QA - 测试交付（L2）**

- **L2 工作流**: `workflow.qa.testing_pipeline`
- **输入**: `test_submission_freeze_package.yaml`
- **输出**: `deliverable_release.yaml`（可交付版本）
- **职责**:
  - 多轮测试（最多 3 轮）
  - Bug 生命周期管理
  - 质量门控
- **Human Gate**: `qa_lead` + `product_lead` 双重审批

**Step 6: Release - 发布批准（L1 Human Gate）**

- **输入**:
  - 所有上游冻结包
  - `deliverable_release.yaml`
- **输出**: `product_mvp_release.yaml`（产品 MVP 发布包）
- **审批角色**: `product_owner` + `tech_lead`
- **通过条件**:
  - 商业价值实现
  - 质量达标（测试通过率 ≥ 95%，无 P0/P1 Bug）
  - 完整性（所有功能、设计、测试文档齐全）
  - 可维护性（代码质量、文档质量达标）

#### 冻结包清单

| 冻结包 | 产出者 | 消费者 | 必需字段 |
|--------|--------|--------|----------|
| `business_opportunity_freeze.yaml` | STG | PRD, UI | one_liner, target_user, why_now, differentiation, reasons_not_to_do, validation_path |
| `dev_freeze_package.yaml` | PRD | Dev | requirements, acceptance_criteria, technical_specs, api_contracts, data_models |
| `prototype_freeze_package.yaml` | UI | Dev | design_system, page_flows, component_specs, interaction_patterns, visual_specs |
| `test_submission_freeze_package.yaml` | Dev | QA | source_code, test_report, deployment_guide, known_issues, release_notes |
| `deliverable_release.yaml` | QA | Release | release_version, test_summary, bug_report, quality_metrics, deployment_artifacts |
| `product_mvp_release.yaml` | L1 | Production | 所有上游产物 + 最终发布批准 |

#### 质量门控

| 门控 | 检查项 | 标准 |
|------|--------|------|
| **STG 冻结包完整性** | 必需字段、审批 | one_liner, target_user, why_now 等齐全；stg_lead + product_lead 审批 |
| **PRD 冻结包完整性** | 必需字段、审批 | requirements, acceptance_criteria 等齐全；prd_lead + dev_lead 审批 |
| **UI 冻结包完整性** | 必需字段、审批 | design_system, page_flows 等齐全；ui_lead + product_lead 审批 |
| **Dev 提测包完整性** | 必需字段、测试覆盖、审批 | source_code, test_report 等齐全；测试覆盖率 ≥ 80%；dev_lead + qa_lead 审批 |
| **QA 交付包完整性** | 必需字段、Bug 检查、审批 | release_version, test_summary 等齐全；无 P0/P1 Bug；qa_lead + product_lead 审批 |

#### 执行配置

```yaml
execution_mode: serial  # 串行执行，确保上游完成下游才能启动
timeout:
  stg_opportunity_discovery: 1209600    # 14 days
  prd_requirement_freeze: 604800        # 7 days
  ui_prototype_freeze: 604800           # 7 days
  dev_implementation: 1209600           # 14 days
  qa_testing_delivery: 604800           # 7 days
  release_approval: 86400               # 1 day
```

#### 依赖关系图

```
STG (商业机会冻结)
  ↓
  ├──→ PRD (研发冻结)
  │      ↓
  │   ┌───┴────────────┐
  │   Dev (研发实现)   │
  │   ↓                │
  │ QA (测试交付)      │
  │   ↓                │
  └────────────────────┤
                      ↓
                 Release (发布批准)
```

---

### 2.2 产品决策流水线（旧版）

**ID**: `workflow.cross.product_pipeline`
**路径**: `cross/workflows/product-pipeline/v1/workflow.yaml`
**Level**: `project` (L1)
**Owner**: 跨部门（可选：`departments/office`）

> **注意**: 这是旧版的产品决策流水线，包含 4 个阶段的详细决策流程。目前主要使用 **2.1 产品 MVP 工作流** 作为 L1 主流程。

---

## 三、L2 工作流（部门级）

### 3.1 PRD 部门 - 产品流水线

**ID**: `workflow.prd.product_pipeline`
**路径**: `departments/prd/workflows/product-pipeline/v1/workflow.yaml`
**Level**: `department` (L2)
**Owner**: `prd`

#### 功能描述

PRD 部门的核心产品流程，负责从需求到 PRD 文档的完整产出。

**阶段结构**：
- 需求采集
- 需求分析
- PRD 编写
- 内部评审

#### 输出产物

- `requirements.yaml` - 需求清单
- `prd_document.yaml` - PRD 文档（冻结）

---

### 3.2 PRD 部门 - 产品交付流水线 ⭐

**ID**: `workflow.prd.product_to_dev_pipeline`
**路径**: `departments/prd/workflows/product-to-dev-pipeline/v1/workflow.yaml`
**Level**: `department` (L2)
**Owner**: `prd`

#### 功能描述

这是连接 PRD 部门和 Dev 部门的关键 L2 流程。

**核心价值**：
- 将产品需求转化为"研发冻结包"
- 提供标准化的研发输入
- 为下游 Dev 部门提供清晰的验收标准

**阶段结构**：
1. **需求解冻** - 解析上游产物
2. **规格编写** - 编写技术规格
3. **评审确认** - 内部评审
4. **冻结打包** - 生成研发冻结包

#### 输出产物

| 产物 | 说明 | 下游 |
|------|------|------|
| `dev_freeze_package.yaml` | 研发冻结包 | L2 Dev 部门流水线 |

#### 冻结包内容

```yaml
dev_freeze_package:
  requirements:           # 需求（来自 PRD）
    - id: "REQ-001"
      title: "用户登录功能"
      acceptance_criteria: [...]

  specifications:         # 技术规格（PRD 编写）
    - id: "SPEC-001"
      api_spec: "..."
      data_model: "..."

  constraints:            # 约束条件
    performance:
      - "登录响应 < 500ms"
    security:
      - "密码加密存储"

  handoff:               # 交接信息
    from_department: "prd"
    to_department: "dev"
    freeze_version: "v1.0"
    freeze_time: "2026-01-28T10:00:00Z"
```

#### 与 L1 的关系

```
L1 Product Pipeline (Stage 4: delivery_planning)
        ↓
    输出：交付计划 + 研发冻结包（草稿）
        ↓
┌─────────────────────────────────────────┐
│  L2: PRD Product-to-Dev Pipeline        │
│  ┌────────────┐  ┌────────────┐        │
│  │规格编写    │→ │冻结打包    │        │
│  └────────────┘  └────────────┘        │
└─────────────────────────────────────────┘
        ↓
    输出：研发冻结包（正式）
        ↓
L2 Dev Development Pipeline (Stage: s3_0)
        ↓
    输入：解冻研发冻结包
```

---

### 3.3 Dev 部门 - 开发流水线

**ID**: `workflow.dev.development_pipeline`
**路径**: `departments/dev/workflows/development-pipeline/v1/workflow.yaml`
**Level**: `department` (L2)
**Owner**: `dev`

#### 功能描述

Dev 部门的核心研发流程，负责从研发冻结包到可交付版本的完整闭环。

**阶段结构**（7 个 Stage）：

```
s3_0: 研发准备
├── 接收研发冻结包
├── 解冻规格
└── 【Human Gate】规格确认

s3_1: 技术设计
├── 架构设计
├── 接口定义
└── 【Human Gate】设计评审

s3_2: OpenSpec 阶段
└── spawn L3: workflow.dev.phase_openspec_flow

s3_3: 开发实现
├── 代码编写
├── 单元测试
└── 【Human Gate】代码评审

s3_4: 集成测试
└── spawn L3: workflow.qa.testing_pipeline

s3_5: 部署准备
├── 部署脚本
├── 配置管理
└── 【Human Gate】部署评审

s3_6: 发布交付
├── 灰度发布
├── 监控验证
└── 【Human Gate】发布确认
```

#### Human Gate 规则

| Gate | 审批角色 | 通过条件 |
|------|----------|----------|
| 规格确认 | `tech_lead`, `product_lead` | 规格完整、无歧义 |
| 设计评审 | `architect`, `tech_lead` | 架构合理、可扩展 |
| 代码评审 | `tech_lead`, `peer_dev` | 代码质量、测试覆盖 |
| 部署评审 | `devops_lead`, `tech_lead` | 部署方案安全 |
| 发布确认 | `product_lead`, `tech_lead` | 验收通过 |

#### 输出产物

| 产物 | 说明 |
|------|------|
| `tech_design.yaml` | 技术设计文档 |
| `openspec_result.yaml` | OpenSpec 阶段结果 |
| `test_report.yaml` | 测试报告 |
| `release_manifest.yaml` | 发布清单 |
| `release_notes.md` | 发布说明 |

---

### 3.4 QA 部门 - 测试主流水线 v2

**ID**: `workflow.qa.testing_pipeline`
**路径**: `departments/qa/workflows/test-main-pipeline/v2/workflow.yaml`
**Level**: `department` (L2)
**Owner**: `qa`

#### 功能描述

QA 部门的多轮测试流水线，负责完整的测试生命周期管理。

**核心特性**：
- 支持多轮测试（最多 3 轮）
- 每轮测试包含：冒烟测试 → 回归测试 → Bug 验证
- 自动 spawn Bug 子工作流
- 风险驱动的回归测试策略

#### 状态机（10+ 个状态）

```
┌─────────────────────────────────────────────────────────────┐
│                     测试主流程状态机                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────┐    ┌────────┐    ┌──────────┐    ┌─────────┐   │
│  │ READY │ → │ SMOKE  │ → │ REGRESSION │ → │ VERIFICATION │ │
│  └──────┘    └────────┘    └──────────┘    └─────────┘   │
│      ↓            ↓              ↓              ↓          │
│  ┌────────┐  ┌────────┐    ┌──────────┐    ┌─────────┐   │
│  │BLOCKED │  │GATE_WAIT│   │ BUG_OPENED │   │COMPLETE │   │
│  └────────┘  └────────┘    └──────────┘    └─────────┘   │
│                                          ↑                  │
│                                    spawn bug_sub           │
└─────────────────────────────────────────────────────────────┘
```

**状态定义**：

| 状态 | 说明 | 下一状态 |
|------|------|----------|
| `READY` | 准备就绪，等待测试开始 | `SMOKE_TEST` |
| `SMOKE_TEST` | 冒烟测试中 | `SMOKE_PASS` → `REGRESSION_TEST` |
| `SMOKE_FAIL` | 冒烟失败 | `GATE_REJECTED` |
| `REGRESSION_TEST` | 回归测试中 | `REGRESSION_PASS` → `VERIFICATION` |
| `BUG_OPENED` | 发现 Bug，spawn 子工作流 | `BLOCKED` |
| `BLOCKED` | 被 Bug 阻塞，等待修复 | `READY` (修复后) |
| `VERIFICATION` | Bug 验证中 | `VERIFIED` → `COMPLETE` |
| `GATE_WAIT` | 等待人工 Gate | `GATE_APPROVED` → `COMPLETE` |
| `COMPLETE` | 测试完成 | 终态 |

#### 测试轮次控制

```yaml
round_control:
  max_rounds: 3

  round_1:
    - smoke_test
    - full_regression
    - bug_verification

  round_2:
    - regression_on_fixed_bugs
    - smoke_test
    - bug_verification

  round_3:
    - smoke_test
    - critical_path_regression
    - final_verification

  on_max_rounds_reached:
    action: "escalate_to_human"
    notify: [qa_lead, tech_lead, product_manager]
```

#### 风险驱动的回归策略

```yaml
regression_strategy:
  risk_based:
    high_risk:
      - "全量回归测试"
      - "边界值测试"
      - "性能测试"

    medium_risk:
      - "核心功能回归"
      - "关联功能测试"

    low_risk:
      - "冒烟测试"
      - "修复点验证"
```

#### 输出产物

| 产物 | 说明 |
|------|------|
| `test_report.yaml` | 测试报告（每轮） |
| `bugs/*.contract.yaml` | Bug 契约文件列表 |
| `rejection_notice.yaml` | 拒绝通知（如打回） |
| `final_test_summary.yaml` | 最终测试总结 |

#### Bug 子工作流集成

当测试失败时：

```yaml
on_test_failure:
  - spawn: workflow.qa.bug_sub
    with:
      bug_id: "BUG-{timestamp}"
      evidence:
        test_failure_event: "$EVENT"
        round_id: "$CURRENT_ROUND"
        version: "$VERSION"
```

---

### 3.5 UI 部门 - UI 设计流水线

**ID**: `workflow.ui.design_pipeline`
**路径**: `departments/ui/workflows/ui-design-pipeline/v1/workflow.yaml`
**Level**: `department` (L2)
**Owner**: `ui`

#### 功能描述

UI 部门的设计流程，负责从设计需求到设计交付的完整闭环。

**三个质量门控**：

```
┌─────────────────────────────────────────────────────────────┐
│                  UI 设计流水线                               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  设计需求 → UI 设计 → 【UI Gate】 → 开发对接 → 【Dev Gate】 │
│                                      ↓                      │
│                              交付准备 → 【Release Gate】     │
└─────────────────────────────────────────────────────────────┘
```

**Gate 规则**：

| Gate | 审批角色 | 通过条件 |
|------|----------|----------|
| UI Gate | `design_lead`, `product_lead` | 设计符合需求、可用性良好 |
| Dev Gate | `tech_lead`, `designer` | 设计可实现、资源评估合理 |
| Release Gate | `product_lead`, `design_lead` | 设计完整、可交付 |

#### Contract 驱动设计

```yaml
contracts:
  pages:
    - id: "PAGE-001"
      file: "contracts/pages/login/v1/design.yaml"
      required: true

  components:
    - id: "COMP-001"
      file: "contracts/components/button/v1/design.yaml"

  tokens:
    - id: "TOKEN-001"
      file: "contracts/tokens/colors/v1/tokens.yaml"

  a11y:
    - id: "A11Y-001"
      file: "contracts/a11y/wcag-compliance/v1/checklist.yaml"
```

---

### 3.6 STG 部门 - 商业机会发现流水线

**ID**: `workflow.stg.opportunity_discovery`
**路径**: `departments/stg/workflows/opportunity_discovery/v1/workflow.yaml`
**Level**: `department` (L2)
**Owner**: `stg`
**版本**: v1.1

#### 功能描述

策略部门的核心流程，负责从市场信号到商业机会冻结的完整发现过程。

**核心思想**：
- "可冻结、可复盘"的商业机会发现流水线
- 分析必须在 freeze 层收敛
- 机会构建后必须经过 human gate 冻结
- 输出"商业机会冻结包"作为下游 L2 流程的输入

**6 层流程结构**：

```
┌─────────────────────────────────────────────────────────────┐
│              商业机会发现流水线（7 步）                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  【事实采集层】                                             │
│  Step 1: search_signals - 搜索采集                          │
│           ↓                                                │
│  【分析层】                                                 │
│  Step 2: analyze_user_signals - 用户信号分析                │
│  Step 3: analyze_industry_structure - 行业结构分析          │
│  Step 4: analyze_supply_competition - 供给竞争分析          │
│           ↓                                                │
│  【冻结层】⭐ 关键                                           │
│  Step 5: freeze_market_signals - 市场信号冻结（Human Gate） │
│           ↓                                                │
│  【机会构建层】                                             │
│  Step 6: build_business_opportunity - 商业机会构建          │
│           ↓                                                │
│  【冻结层】⭐ 最终冻结                                       │
│  Step 7: freeze_business_opportunity - 商业机会冻结（Gate） │
└─────────────────────────────────────────────────────────────┘
```

#### Human Gate 1（市场信号冻结层）

**这是系统稳定性的根！**

```yaml
gate_rules:
  reviewers:
    - role: stg_lead
      description: "策略部门负责人"

  approval_criteria:
    - label: "分析一致性"
      criteria: "三个分析层输出无明显矛盾"
      required: true

    - label: "置信度达标"
      criteria: "综合置信度 ≥ 50"
      required: true

    - label: "可验证性"
      criteria: "核心假设可以通过后续验证"
      required: true

  rejection_criteria:
    - "分析层输出存在重大矛盾"
    - "置信度过低（<30）"
    - "假设过于宽泛，无法验证"
```

#### Human Gate 2（商业机会冻结层）⭐ 新增

**这是商业机会的最终冻结点！**

```yaml
gate_rules:
  reviewers:
    - role: stg_lead
      description: "策略部门负责人"
    - role: product_lead
      description: "产品部门负责人（共同审核）"

  approval_criteria:
    - label: "机会价值"
      criteria: "一句话机会定义清晰、目标用户明确"
      required: true

    - label: "时机合适"
      criteria: "Why Now 理由充分、市场时机成熟"
      required: true

    - label: "风险识别"
      criteria: "Reasons NOT to Do 至少 3 条、风险可接受"
      required: true

    - label: "可验证性"
      criteria: "验证路径清晰、假设可测试"
      required: true

  rejection_criteria:
    - "机会定义模糊、目标用户不明确"
    - "时机不成熟、缺乏 Why Now 理由"
    - "风险未充分识别、 Reasons NOT to Do 不够诚实"
    - "验证路径不清晰、假设不可测试"
```

#### 输出产物清单

| 产物 | 说明 | 层级 |
|------|------|------|
| `signals.yaml` | 搜索信号数据 | 事实采集 |
| `hypothesis.yaml` | 用户假设分析 | 分析 |
| `structure.yaml` | 行业结构分析 | 分析 |
| `gap.yaml` | 供给空缺分析 | 分析 |
| `freeze.yaml` (市场信号) | 市场信号冻结 | ⭐ 冻结层 1 |
| `opportunity.yaml` | 商业机会假设 | 机会构建 |
| `freeze.yaml` (商业机会) | **商业机会冻结包** | ⭐⭐ 冻结层 2（最终输出） |

#### 核心约束

**分析层约束**（Step 2-4）：
- 只基于关键词+常识+公开资料
- 禁止发明用户故事
- 必须标注推断置信度

**机会构建约束**（Step 6）：
- 只能引用 freeze 内容
- 必须包含风险（Reasons NOT to Do）
- 不设计具体功能

**冻结原则**（Step 7）：
- 机会假设完整且可验证
- 风险已充分识别
- Reasons NOT to Do 已诚实列出
- 可以作为下游 L2 流程的可靠输入

#### 版本更新

**v1.1** (2026-01-28):
- 删除 Step 7: product_handoff（产品部门交付）
- 新增 Step 7: freeze_business_opportunity（商业机会冻结 Human Gate）
- 输出改为"商业机会冻结包"，作为下游 L2 流程输入
- 增加 product_lead 作为联合审核角色

---

## 四、L3 工作流（任务级）

### 4.1 Dev 阶段 - OpenSpec Flow

**ID**: `workflow.dev.phase_openspec_flow`
**路径**: `departments/dev/workflows/phase-openspec-flow/v1/workflow.yaml`
**Level**: `task` (L3)
**Owner**: `dev`

#### 功能描述

Dev 部门的核心任务流程，定义了开发阶段的 13 个强制步骤。

**版本**: 1.7（强化执行机制、补救循环）

**核心原则**：
- 13 步全部强制执行
- 每步都有明确的输出契约
- 支持失败补救循环
- 禁止跳步或并行

#### 13 个强制步骤

```
┌─────────────────────────────────────────────────────────────┐
│                  OpenSpec Flow (13 Steps)                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  p1: requirement_calibration     - 需求校准                  │
│  p2: test_contract_drafting      - 测试契约编写              │
│  p3: design_review               - 设计评审                  │
│  p4: implementation_plan         - 实现计划                  │
│  p5: implementation_execution    - 代码实现                  │
│  p6: unit_test_composition       - 单元测试编写              │
│  p7: local_unit_test_passing     - 本地单元测试通过          │
│  p8: code_review                 - 代码评审                  │
│  p9: retrospective               - 回顾总结                  │
│  p10: knowledge_merge_to_base    - 知识合并到主干            │
│  p11: final_integration_test     - 最终集成测试              │
│  p12: handoff_to_next_phase      - 交接下一阶段              │
│  p13: archive_and_cleanup        - 归档清理                  │
└─────────────────────────────────────────────────────────────┘
```

#### 步骤详解

| 步骤 | 名称 | 输出 | 验证标准 |
|------|------|------|----------|
| p1 | 需求校准 | `calibrated_requirements.yaml` | 需求无歧义、验收标准清晰 |
| p2 | 测试契约编写 | `test_contract.yaml` | 测试用例完整、覆盖充分 |
| p3 | 设计评审 | `design_review_report.yaml` | 设计通过评审 |
| p4 | 实现计划 | `implementation_plan.yaml` | 任务分解合理 |
| p5 | 代码实现 | `source_code/` | 代码编写完成 |
| p6 | 单元测试编写 | `unit_tests/` | 测试覆盖核心逻辑 |
| p7 | 本地单元测试通过 | `test_result.yaml` | 100% 通过 |
| p8 | 代码评审 | `code_review_report.yaml` | 评审通过 |
| p9 | 回顾总结 | `retrospective.md` | 总结记录完整 |
| p10 | 知识合并 | `merge_commit.yaml` | 合并到主干 |
| p11 | 最终集成测试 | `integration_test_result.yaml` | 集成测试通过 |
| p12 | 交接下一阶段 | `handoff.yaml` | 交接文档完整 |
| p13 | 归档清理 | `archive.tar.gz` | 归档完成 |

#### 执行机制

```yaml
enforcement:
  strict_ordering: true      # 严格顺序执行
  skip_protection: true      # 禁止跳步
  parallel_protection: true  # 禁止并行

remediation_loops:
  p1_p2:
    - if: "requirement_ambiguous"
      then: "restart_p1"
      max_retries: 3

  p7:
    - if: "unit_test_failed"
      then: "fix_and_retry_p7"
      max_retries: 5

  p8:
    - if: "code_review_rejected"
      then: "fix_and_restart_p8"
      max_retries: 3
```

#### 输出产物

```yaml
outputs:
  required:
    - calibrated_requirements.yaml
    - test_contract.yaml
    - design_review_report.yaml
    - implementation_plan.yaml
    - source_code/
    - unit_tests/
    - test_result.yaml
    - code_review_report.yaml
    - retrospective.md
    - merge_commit.yaml
    - integration_test_result.yaml
    - handoff.yaml
    - archive.tar.gz
```

---

### 4.2 Dev 任务 - 开发返修流程

**ID**: `workflow.dev.retest`
**路径**: `departments/dev/workflows/dev-retest/v1/workflow.yaml`
**Level**: `task` (L3)
**Owner**: `dev`

#### 功能描述

专门处理测试打回后的 Bug 修复和再提测。

**核心原则**：
- 在需求冻结前提下修复已知问题
- 禁止引入新需求或非相关改动
- 快速迭代，严格门禁
- 连续失败后强制升级人类介入

**5 个阶段**：

```
┌─────────────────────────────────────────────────────────────┐
│                  开发返修流程（5 阶段）                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  r1: preparation      - 返修准备                             │
│      ├─ r1_1: 接收拒绝通知                                  │
│      └─ r1_2: 影响范围分析                                  │
│                                                             │
│  r2: fix_planning     - 修复计划                             │
│      ├─ r2_1: Bug 分诊                                       │
│      └─ r2_2: 修复计划审核（Gate）                          │
│                                                             │
│  r3: fix_execution    - 修复执行                             │
│      ├─ r3_1: 代码修复                                       │
│      └─ r3_2: 补充回归测试                                  │
│                                                             │
│  r4: selfcheck        - 开发自检（关键门禁）                  │
│      ├─ r4_1: 单元测试（Gate: 100%通过）                    │
│      ├─ r4_2: 本地冒烟测试（Gate）                          │
│      └─ r4_3: 自检总结                                      │
│                                                             │
│  r5: resubmit         - 再次提测                             │
│      ├─ r5_1: 生成返修提测包                                │
│      ├─ r5_2: 再提测门禁（Gate）                            │
│      └─ r5_3: 交接测试团队                                  │
└─────────────────────────────────────────────────────────────┘
```

#### 入口门禁（强约束）

```yaml
entry_gate:
  required_inputs:
    - test-rejection-notice.yaml
    - bugs/*.contract.yaml
    - test-report.yaml

  validation_rules:
    - rule: "bugs_count > 0"
      message: "必须有明确的 Bug 需要修复"

    - rule: "rejection_reason != 'requirement_change'"
      message: "如果是需求变更，应该走完整研发流程"

    - rule: "retest_round_count < 3"
      message: "连续返修超过3次，必须升级人类介入"
      on_fail:
        action: escalate_to_human
        notify: [tech-lead, product-manager]
```

#### 防滥用规则

```yaml
constraints:
  forbidden_actions:
    - action: "add_new_requirement"
      description: "禁止引入新需求"
      penalty: "workflow_abort"

    - action: "modify_frozen_spec"
      description: "禁止修改已冻结的规格"
      penalty: "workflow_abort"

    - action: "change_acceptance_criteria"
      description: "禁止修改验收标准"
      penalty: "workflow_abort"

    - action: "unrelated_refactor"
      description: "禁止非必要的重构"
      penalty: "human_review_required"

  allowed_scope:
    - "修复 bug.contract 中列出的问题"
    - "补充回归测试用例"
    - "必要的配置调整（需声明）"
    - "相关单元测试"
```

#### 循环控制（防失控）

```yaml
loop_control:
  max_iterations: 3

  on_iteration_fail:
    - if: "iteration == 1"
      then:
        action: "continue"
        message: "第1次返修失败，允许再次尝试"

    - if: "iteration == 2"
      then:
        action: "continue_with_warning"
        message: "第2次返修失败，建议人工介入"
        notify: [tech-lead]

    - if: "iteration >= 3"
      then:
        action: "escalate_and_pause"
        message: "连续3次返修失败，强制升级人类介入"
        notify: [tech-lead, product-manager, qa-lead]
        require_human_approval: true
```

#### 输出产物

| 产物 | 说明 | 必需 |
|------|------|------|
| `dev-fix-plan.yaml` | 修复计划 | ✅ |
| `dev-selfcheck.yaml` | 自检报告 | ✅ |
| `retest-release-manifest.yaml` | 返修提测包 | ✅ |
| `fix-commits.yaml` | 修复提交记录 | ✅ |
| `impact-analysis.yaml` | 影响范围分析 | 可选 |
| `tests/regression/*.test.*` | 新增回归测试 | 可选 |

---

### 4.3 QA 任务 - Bug 子工作流

**ID**: `workflow.qa.bug_sub`
**路径**: `departments/qa/workflows/bug-sub-workflow/v1/workflow.yaml`
**Level**: `task` (L3)
**Owner**: `bug-governance`

#### 功能描述

单 Bug 的完整生命周期管理，支持跨团队协同流转。

**核心特性**：
- 独立状态机，不可跳跃状态
- 跨研发/产品/测试/平台团队流转
- 人类介入的特殊分支（安全/财务/需求争议）
- 严格的角色权限边界（防止自证闭环）
- 并行推进，事件通知主流程

#### 状态机（10+ 个状态）

```
┌─────────────────────────────────────────────────────────────┐
│                    Bug 状态机                                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  【主路径】                                                 │
│  NEW → TRIAGED → ROUTED → DEBUGGED → FIXING → FIXED        │
│    → VERIFYING → VERIFIED → CLOSED                          │
│                                                             │
│  【阻塞分支】                                               │
│  TRIAGED → BLOCKED_PM       - 需产品澄清                    │
│  TRIAGED → BLOCKED_HUMAN    - 需人类决策（安全/财务/法律）   │
│  TRIAGED → BLOCKED_ENV      - 环境/不稳定问题               │
│  VERIFYING → BLOCKED_DEPENDENCY - 依赖其他 Bug              │
└─────────────────────────────────────────────────────────────┘
```

**状态定义**：

| 状态 | 说明 | 触发条件 |
|------|------|----------|
| `NEW` | 新建 | 测试失败时自动创建 |
| `TRIAGED` | 已分流 | 补充复现步骤、定级、分配 owner |
| `ROUTED` | 已分配 | 分配给具体团队/Agent |
| `DEBUGGED` | 已诊断 | P0/P1 完成 Debug 分析 |
| `FIXING` | 修复中 | 开发开始修复 |
| `FIXED` | 已修复 | 代码已提交 |
| `VERIFYING` | 验证中 | QA 开始验证 |
| `VERIFIED` | 已验证 | 验证通过 |
| `CLOSED` | 已关闭 | Bug 关闭 |
| `BLOCKED_PM` | 阻塞-需产品澄清 | 需求争议/歧义 |
| `BLOCKED_HUMAN` | 阻塞-需人类介入 | 安全/财务/法律/重大变更 |
| `BLOCKED_ENV` | 阻塞-环境/不稳定 | 环境/不稳定问题 |
| `BLOCKED_DEPENDENCY` | 阻塞-依赖其他 Bug | 依赖其他 Bug |

#### 角色权限边界（硬规则）

```yaml
role_permissions:
  qa_agent:
    can_write:
      - status: [NEW, TRIAGED, VERIFYING, VERIFIED, CLOSED]
      - evidence.*
      - reproduction_steps
      - verification.*
    cannot_write:
      - fix.*
      - analysis.root_cause
      - decision.pm_resolution

  dev_agent:
    can_write:
      - status: [FIXING, FIXED]
      - fix.*
      - analysis.root_cause (补充)
    cannot_write:
      - verification.*
      - decision.*
      - status: [VERIFIED, CLOSED]

  pm_agent:
    can_write:
      - status: [BLOCKED_PM -> ROUTED, BLOCKED_PM -> CLOSED]
      - decision.pm_resolution
    cannot_write:
      - fix.*
      - verification.*
```

**防自证闭环**：
```yaml
validation:
  - rule: "verification.verified_by != routing.owner_agent"
    error: "不允许自证闭环"
```

#### 人类介入判定规则（自动触发）

```yaml
human_intervention_rules:
  auto_trigger_human_gate:
    - condition: "category == security"
      reason: "安全相关 Bug 必须人类审批"

    - condition: "category == data_loss OR category == payment"
      reason: "数据不可逆风险或财务相关"

    - condition: "analysis.risk_area CONTAINS 'irreversible'"
      reason: "不可回滚的变更"

    - condition: "decision.scope_change == major"
      reason: "修复等同改需求，影响验收口径"

    - condition: "severity == P0 AND detected_in == production"
      reason: "线上 P0 事故需要人类确认回滚/止血策略"

  human_gate_sla:
    timeout: 4h
    escalation: [qa_lead, tech_lead, product_owner]
```

#### 阶段结构

```
Stage 1: creation
└─ create_bug_contract

Stage 2: triage
├─ enrich_evidence
├─ classify_and_route
└─ route_decision

Stage 3: debug_analysis (可选，P0/P1 自动触发)
└─ trigger_debug_agent

Stage 4: fix
└─ developer_fix

Stage 5: verification
└─ verify_fix

Stage 6: closure
└─ close_bug
```

#### 事件通知（给主流程）

```yaml
events:
  emit:
    - bug_created:
        when: "status == NEW"
        notify: test_main_workflow

    - bug_triaged:
        when: "status == TRIAGED"
        notify: test_main_workflow

    - bug_blocked_critical:
        when: "status IN [BLOCKED_HUMAN, BLOCKED_PM] AND severity == P0"
        notify: test_main_workflow

    - bug_fixed:
        when: "status == FIXED"
        notify: test_main_workflow

    - bug_verified:
        when: "status == VERIFIED"
        notify: test_main_workflow

    - bug_closed:
        when: "status == CLOSED"
        notify: test_main_workflow
```

#### SLA 与超时处理

| 阶段 | 超时时间 | 升级对象 |
|------|----------|----------|
| triage | 2h | qa_lead |
| debug_p0 | 4h | tech_lead |
| fix_p0 | 24h | tech_lead, pm |
| fix_p1 | 48h | tech_lead |
| human_decision | 4h | qa_lead, tech_lead, product_owner |
| verification | 12h | qa_lead |

---

### 4.4 QA 任务 - 测试流水线 v1

**ID**: `workflow.qa.testing_pipeline`
**路径**: `departments/qa/workflows/testing-pipeline/v1/workflow.yaml`
**Level**: `task` (L3)
**Owner**: `qa`

#### 功能描述

QA 部门的基础测试流程（v1 版本），已被 v2 版本替代，但保留作为参考。

---

### 4.5 QA 任务 - 冒烟测试

**ID**: `workflow.qa.smoke_test`
**路径**: `departments/qa/workflows/smoke-test/v1/workflow.yaml`
**Level**: `task` (L3)
**Owner**: `qa`

#### 功能描述

快速冒烟测试流程，用于验证核心功能可用性。

---

## 五、跨工作流关系图

### 5.1 L1 产品 MVP 工作流（完整流程）⭐

```
┌─────────────────────────────────────────────────────────────────┐
│                  L1: Product MVP Workflow                       │
│                  产品 MVP 工作流 - 跨部门主流程                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Step 1: STG → 商业机会冻结                                      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  L2: workflow.stg.opportunity_discovery                │   │
│  │  输出: business_opportunity_freeze.yaml                 │   │
│  └─────────────────────────────────────────────────────────┘   │
│                         ↓                                       │
│  ┌────────────────┴────────────────┐                          │
│  ↓                                 ↓                          │
│  Step 2: PRD                       Step 3: UI                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  L2: workflow.prd.product_to_dev_pipeline              │   │
│  │  输入: business_opportunity_freeze.yaml                 │   │
│  │  输出: dev_freeze_package.yaml                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  L2: workflow.ui.design_pipeline                        │   │
│  │  输入: business_opportunity_freeze.yaml                 │   │
│  │  输出: prototype_freeze_package.yaml                    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                         ↓                                       │
│  ┌────────────────┴────────────────┐                          │
│  ↓                                 ↓                          │
│  Step 4: Dev (接收 2 个冻结包)                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  L2: workflow.dev.development_pipeline                  │   │
│  │  输入: dev_freeze_package.yaml                          │   │
│  │       prototype_freeze_package.yaml                     │   │
│  │  输出: test_submission_freeze_package.yaml             │   │
│  └─────────────────────────────────────────────────────────┘   │
│                         ↓                                       │
│  Step 5: QA                                                     │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  L2: workflow.qa.testing_pipeline                       │   │
│  │  输入: test_submission_freeze_package.yaml             │   │
│  │  输出: deliverable_release.yaml                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                         ↓                                       │
│  Step 6: Release (Human Gate)                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  L1: release_approval                                  │   │
│  │  输入: deliverable_release.yaml + 所有上游冻结包        │   │
│  │  输出: product_mvp_release.yaml                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 冻结包流转图

```
┌─────────────────────────────────────────────────────────────────┐
│                       冻结包流转链                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  STG (L2)                                                      │
│    ↓ business_opportunity_freeze.yaml                          │
│    ├─→ PRD (L2) ──→ dev_freeze_package.yaml ─┐                │
│    │                                            │                │
│    └─→ UI (L2) ───→ prototype_freeze_package.yaml│                │
│                                                 │                │
│                                                 ↓                │
│  Dev (L2) ←─────────────────────────────────────┘                │
│    ↓ test_submission_freeze_package.yaml                         │
│    ↓                                                              │
│  QA (L2)                                                       │
│    ↓ deliverable_release.yaml                                   │
│    ↓                                                              │
│  Release (L1 Gate)                                              │
│    ↓ product_mvp_release.yaml                                   │
│    ↓                                                              │
│  Production                                                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 5.3 Bug 修复流程

```
┌─────────────────────────────────────────────────────────────┐
│  L2: QA Testing Pipeline v2                                │
│  ... 测试失败 ...                                           │
│      ↓                                                      │
│  spawn Bug Sub-workflow                                     │
└─────────────────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────────────────┐
│  L3: Bug Sub-workflow                                      │
│  ... Bug 修复完成 ...                                       │
│      ↓                                                      │
│  验证失败                                                  │
└─────────────────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────────────────┐
│  L3: Dev Retest Workflow (开发返修流程)                     │
│  ... 修复并再次提测 ...                                      │
│      ↓                                                      │
│  触发新一轮测试                                             │
└─────────────────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────────────────┐
│  L2: QA Testing Pipeline v2 (Round 2)                       │
└─────────────────────────────────────────────────────────────┘
```

### 5.3 OpenSpec 流程

```
┌─────────────────────────────────────────────────────────────┐
│  L2: Dev Development Pipeline                              │
│  Stage s3_2: OpenSpec 阶段                                  │
│      ↓                                                      │
│  spawn L3: workflow.dev.phase_openspec_flow                 │
└─────────────────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────────────────┐
│  L3: OpenSpec Flow (13 步强制流程)                         │
│  p1: 需求校准                                               │
│  p2: 测试契约编写                                          │
│  p3: 设计评审                                              │
│  p4: 实现计划                                              │
│  p5: 代码实现                                              │
│  p6: 单元测试编写                                          │
│  p7: 本地单元测试通过（Gate: 100%）                         │
│  p8: 代码评审（Gate）                                       │
│  p9: 回顾总结                                              │
│  p10: 知识合并到主干                                       │
│  p11: 最终集成测试                                         │
│  p12: 交接下一阶段                                         │
│  p13: 归档清理                                             │
│      ↓                                                      │
│  完成，返回 L2                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 六、统计摘要

### 6.1 按层级统计

| 层级 | 数量 | 工作流 ID |
|------|------|-----------|
| **L1** | 2 | `workflow.cross.product_mvp` ⭐, `workflow.cross.product_pipeline` |
| **L2** | 6 | `workflow.prd.*`, `workflow.dev.*`, `workflow.qa.*`, `workflow.ui.*`, `workflow.stg.*` |
| **L3** | 5 | `workflow.dev.*`, `workflow.qa.*` |
| **总计** | **13** | |

### 6.2 按部门统计

| 部门 | L2 | L3 | 总计 |
|------|----|----|----|
| **PRD（产品）** | 2 | 0 | 2 |
| **Dev（开发）** | 1 | 2 | 3 |
| **QA（测试）** | 1 | 2 | 3 |
| **UI（设计）** | 1 | 0 | 1 |
| **STG（策略）** | 1 | 0 | 1 |
| **Cross（跨部门）** | 0 | 0 | 2 (L1) |
| **总计** | **6** | **4** | **13** |

### 6.3 关键指标

| 指标 | 数值 | 说明 |
|------|------|------|
| **总工作流数** | 13 | L1 + L2 + L3 |
| **Human Gate 总数** | 25+ | 分布在各个关键节点（含 L1 MVP 的 6 个 Gate） |
| **状态机数量** | 2 | Bug 子工作流、测试主流程 |
| **平均阶段数** | 4-7 | L2/L3 工作流 |
| **最多步骤数** | 13 | OpenSpec Flow |
| **最大迭代次数** | 3 | 测试主流程、开发返修 |
| **跨部门依赖** | 5 | L1 MVP 编联 5 个 L2 |
| **冻结包类型** | 6 | 商业机会、研发、原型、提测、可交付、MVP 发布 |

### 6.4 产物清单

**L1 MVP 冻结包**（按流转顺序）：

| 冻结包 | 产出者 | 消费者 | 价值 |
|--------|--------|--------|------|
| `business_opportunity_freeze.yaml` | L2 STG | PRD, UI | 定义商业机会 |
| `dev_freeze_package.yaml` | L2 PRD | Dev | 研发输入 |
| `prototype_freeze_package.yaml` | L2 UI | Dev | 设计输入 |
| `test_submission_freeze_package.yaml` | L2 Dev | QA | 提测包 |
| `deliverable_release.yaml` | L2 QA | Release | 可交付版本 |
| `product_mvp_release.yaml` | L1 Gate | Production | MVP 发布包 |

**其他核心产物**：

| 产物 | 来源 | 价值 |
|------|------|------|
| `bugs/*.contract.yaml` | L3 Bug Sub | 问题追溯 |
| `design_contract.yaml` | L2 UI | 设计规范 |

---

## 附录

### A. 工作流命名规范

```
workflow.{scope}.{name}

scope 规则：
- L1: cross
- L2: {department} (prd/dev/qa/ui/stg)
- L3 跨部门: cross.task.*
- L3 部门内: {department}.task.*

name 规则：
- 使用小写字母和下划线
- 描述性名称，避免缩写
- 示例：product_pipeline, testing_pipeline, phase_openspec_flow
```

### B. 版本号规范

```
{major}.{minor}

major: 重大架构变更
minor: 功能迭代或 bug 修复

示例：
- v1.0: 初始版本
- v1.7: 功能增强（OpenSpec Flow）
- v2.0: 架构重构（Testing Pipeline）
```

### C. 文档版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| 1.1 | 2026-01-28 | 新增 L1 产品 MVP 工作流；更新 STG 流程（v1.1）；总工作流数更新为 13 个 |
| 1.0 | 2026-01-28 | 初始版本，完整梳理 12 个工作流 |

---

**文档维护**: LEE Team
**最后更新**: 2026-01-28
**状态**: ✅ 已完成 (v1.1)
