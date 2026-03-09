---
id: ADR-003
ssot_type: adr
title: Product Department SSOT Design
status: draft
version: v1
parent_id:
derived_from_ids:
  - ADR-001
source_refs:
  []
owner: product
tags: [ssot, product, governance, workflow]
properties:
  adr_kind: department_design
  decision_scope: product_department_canonical_path
  replaces_path: spec-global/departments/prd
---

# Product Department SSOT Design

## 1. Decision

将产品部门从“围绕 PRD 文档组织”重构为“围绕 SSOT 主链组织”。

产品部门新的 canonical 主链为：

`raw input -> SRC -> EPIC -> FEAT -> UI / TECH / TASK`

该设计进入项目级 `spec/`，作为正式 SSOT 设计决策。

从现在开始：

- `spec/` 是本项目正式 SSOT 文档落点
- `spec-global/` 只保存框架规范与通用映射
- `spec-global/departments/prd/` 不再承载前向产品部门设计

## 2. Why

当前问题：

- 旧 `prd` 目录围绕 `requirement/prd/dev-freeze` 建模
- 旧流程前半段重复
- 新产品链路已经要求 `SRC -> EPIC -> FEAT`
- 项目级正式设计放在 `spec-global` 不符合当前仓库的 SSOT 落点规则

因此，产品部门的新设计必须：

- 回到项目级 `spec/`
- 以 SSOT 链而不是 PRD 文档为中心
- 统一所有来源输入的收敛方式

## 3. Canonical Chain

### 3.1 Main Chain

`raw input -> SRC -> EPIC -> FEAT -> UI / TECH / TASK`

### 3.2 Object Meaning

- `raw input`
  - 非 SSOT
  - 可以是一句话、文章、会议结论、客户反馈、老板想法
- `SRC`
  - 正式需求源对象
  - 是产品链路的真实起点
- `EPIC`
  - 覆盖多个可独立验收 `FEAT` 的产品主题
- `FEAT`
  - 最小可独立验收能力单元
- `UI`
  - FEAT 对应的界面与交互设计对象
- `TECH`
  - FEAT 对应的技术设计对象
  - `API` 属于 `TECH`
- `TASK`
  - FEAT 对应的执行任务对象
  - `frontend / backend / integration` 属于 `TASK` 视角
- `ADR`
  - 决策型 SSOT
  - 用于治理、约束和说明，不进入业务主链

### 3.3 ADR Position

`ADR` 不是产品业务链的起点，也不是默认从 `EPIC/FEAT` 派生出来的业务对象。

正式定位：

- `SRC / EPIC / FEAT / UI / TECH / TASK / TESTSET` 是业务与交付对象链
- `ADR` 是决策与治理对象链

因此：

- `ADR` 可以约束 `workflow / contract / agent / skill / TECH / TASK / TESTSET`
- `ADR` 可以被某次 `EPIC/FEAT` 分歧或架构讨论触发
- 但 `ADR` 不进入 `raw input -> SRC -> EPIC -> FEAT` 这条主链

推荐关系语义：

- `ADR governs`
- `ADR constrains`
- `ADR explains`

不推荐：

- `ADR derives FEAT`
- `ADR replaces SRC`
- `ADR acts as business source`

## 4. Mandatory SRC Rule

`EPIC` 之前必须先生成 `SRC`。

理由：

- 输入不一定来自战略部门
- 输入可能并不结构化
- 若没有 `SRC freeze`，`EPIC` 无法追溯来源
- 若直接从一句话跳到 `EPIC`，会破坏 SSOT 治理

正式规则：

- 任意原始输入必须先归一化为 `SRC candidate`
- 经 gate 后冻结为 `SRC`
- 只有冻结后的 `SRC` 才能进入 `EPIC` 设计

## 5. Product Department Scope

### In Scope

- 原始输入接入
- `SRC` 归一化与冻结
- `EPIC` 设计与冻结
- `FEAT` 拆解与冻结
- `UI / TECH / TASK` 准备
- 向 `dev / ui / qa` 输出可开工基线

### Out of Scope

- 代码实现
- 测试执行
- 发布部署
- 运行态故障处理

## 6. Workflow Architecture

产品部门采用：

- 1 条 L2 主编排
- 3 条 L3 子流程

补充边界：

- 仓库中的 workflow spec 是 template
- 运行时 workflow instance 由 Python runtime / orchestrator 动态生成
- 不得把 checked-in workflow spec 当成固定执行实例

### 6.1 L2

`workflow.product.product_main_pipeline`

职责：

- 作为唯一推荐入口
- 串联 L3
- 检查 freeze 前置条件
- 组装下游 handoff

### 6.2 L3: SRC to EPIC

`workflow.product.task.src_to_epic`

推荐步骤：

1. raw input intake
2. source normalization
3. source review
4. source freeze
5. problem alignment
6. epic design
7. epic review
8. epic freeze

### 6.3 L3: EPIC to FEAT

`workflow.product.task.epic_to_feat`

推荐步骤：

1. feat boundary design
2. feat spec generation
3. feat dependency mapping
4. feat review
5. feat freeze

### 6.4 L3: FEAT to Delivery Prep

`workflow.product.task.feat_to_delivery_prep`

推荐步骤：

1. UI design
2. TECH design
3. task planning
4. delivery plan validation
5. delivery prep freeze

该 L3 的输出不是“供参考的任务清单”，而是可执行的实施计划。

## 7. Delivery Prep Freeze Decision

### 7.1 Decision

`Delivery Prep Freeze` 的正式含义调整为：

- 冻结 `UI / TECH / TASK`
- 同时冻结一份可执行实施计划

该实施计划必须能够直接作为下游研发排期、任务分发和执行的基线。

### 7.2 Not Enough

以下内容单独存在时，不足以通过 `Delivery Prep Freeze`：

- 只有 UI 设计稿
- 只有技术方案
- 只有粗粒度任务列表
- 只有“前端/后端/接口要做”的口头分工

### 7.3 Required Output

`Delivery Prep Freeze` 必须至少产出：

- `UI` 冻结对象
- `TECH` 冻结对象
- `TASK` 计划对象
- `delivery prep review`
- 可执行实施计划摘要

## 8. Executable Implementation Plan

### 8.1 Goal

可执行实施计划要回答的不是“理论上怎么做”，而是：

- 谁做
- 做什么
- 先做什么后做什么
- 哪些能并行
- 哪些必须阻塞等待
- 什么时候达到哪个里程碑
- 如果延期，优先砍哪些

### 8.2 Minimum Structure

计划至少应包含：

- role assignment
- task list
- dependency graph
- critical path
- milestones
- entry conditions
- risks
- fallback / cut order

### 8.3 Role Assignment

至少要明确这些责任域：

- product owner
- design owner
- tech lead
- frontend owner
- backend owner
- integration owner
- qa owner

允许一个人兼任多个角色，但角色责任不能缺失。

### 8.4 Task Model

任务必须至少拆到这些可执行域：

- `frontend`
- `backend`
- `integration`
- `qa`（可选但推荐）

约束：

- `UI` 不是 task，它是 frontend task 的设计依赖
- `API` 不是独立平级 task 类型，它属于 `TECH`
- `frontend / backend / integration` 是任务执行域

### 8.5 Dependency Rules

默认依赖规则：

- `UI -> frontend task`
- `TECH(API included) -> frontend task`
- `TECH(API included) -> backend task`
- `frontend + backend -> integration task`
- `integration -> qa validation task`

允许补充更细的局部依赖，但不得破坏这条主依赖线。

### 8.6 Critical Path

计划必须明确：

- 哪条路径是关键路径
- 哪些任务可并行
- 哪些节点是阻塞节点
- 哪些节点延误会直接影响交付日期

### 8.7 Milestones

至少要有这些里程碑：

1. design ready
2. contract ready
3. frontend ready
4. backend ready
5. integration ready
6. qa ready

若项目较小，可以合并里程碑，但不能缺失交付节点定义。

### 8.8 Entry Conditions

计划必须定义开工前置条件，例如：

- `FEAT freeze` 已完成
- UI 设计达到可实现粒度
- API 合同达到可联调粒度
- 关键技术风险已识别
- 外部依赖已确认

### 8.9 Risk and Fallback

计划必须显式给出：

- 关键风险
- 不确定性最大的位置
- 延期时的砍减顺序
- 可先简化的部分

### 8.10 Example Shape

一个典型的实施计划应至少具备如下结构：

```yaml
delivery_plan:
  roles:
    product_owner: product
    design_owner: design
    tech_lead: backend_lead
    frontend_owner: fe_owner
    backend_owner: be_owner
    integration_owner: fullstack_owner
  tasks:
    - id: FEAT-023-FE-01
      lane: frontend
      depends_on: [UI-023, API-023]
    - id: FEAT-023-BE-01
      lane: backend
      depends_on: [TECH-023]
    - id: FEAT-023-INT-01
      lane: integration
      depends_on: [FEAT-023-FE-01, FEAT-023-BE-01]
  milestones:
    - id: M1
      name: contract-ready
    - id: M2
      name: integration-ready
  critical_path:
    - FEAT-023-BE-01
    - FEAT-023-INT-01
```

## 9. Gate Model

硬 gate 固定为：

1. `SRC freeze`
2. `EPIC freeze`
3. `FEAT freeze`
4. `Delivery Prep freeze`

约束：

- gate 前的对象可修订
- gate 后只能新版本 supersede，不得原地改旧冻结版本

### 9.1 Delivery Prep Freeze Approval Criteria

`Delivery Prep Freeze` 通过条件必须至少包括：

- `UI` 信息足以支持前端实施
- `TECH` 信息足以支持前后端实施
- `TASK` 已拆分到可执行粒度
- 有明确责任分工
- 有明确依赖图
- 有明确关键路径
- 有明确里程碑
- 有明确 entry conditions
- 有明确风险与 fallback 顺序

### 9.2 Delivery Prep Freeze Reviewers

建议审批角色：

- `product_owner`
- `tech_lead`
- `design_lead`

必要时可追加：

- `qa_lead`
- `engineering_manager`

## 10. Relationship Rules

必须遵守：

- `raw input` 不能直接生成 `EPIC freeze`
- `SRC` 可以派生多个 `EPIC`
- `EPIC` 必须聚合多个 `FEAT`
- `FEAT` 才能挂 `UI / TECH / TASK`
- `UI / TECH / TASK` 不能直接挂 `EPIC`
- `API` 属于 `TECH`
- `frontend / backend / integration` 属于 `TASK`
- `TESTSET` 由 `FEAT` 派生，不直接挂在 `EPIC`

禁止：

- 把一句话需求直接当 `EPIC`
- 把 `API` 与 `frontend/backend` 建成四平级主对象
- 用 `PRD 文档` 替代 `FEAT` 真源

## 11. FEAT Governance Rules

### 11.1 FEAT Position

`FEAT` 的正式定义固定为：

> `FEAT` 是最小可独立验收的业务能力单元。

它是产品链路中的业务中轴对象，下游默认从 `FEAT` 派生：

`FEAT -> UI / TECH / TASK / TESTSET`

### 11.2 P0 Mandatory Rules

所有 `FEAT` 必须满足以下强约束：

1. 必须是最小可独立验收能力
   - 必须存在明确 `Acceptance Criteria`
   - 若无法被测试验证，则不是合法 `FEAT`
2. 必须定义系统能力，而不是工程任务
   - 允许写“系统能够生成训练计划”
   - 不允许写“实现训练计划接口”
3. 必须给出清晰系统边界
   - 至少说明 `inputs / processing / outputs`
4. 必须包含 `Acceptance Criteria`
   - `AC` 是 `FEAT` 验收和测试生成的唯一强锚点
5. 一个 `FEAT` 只能承载一个核心能力
   - 若同时承载两个能力，必须拆分
6. 必须能够派生 `TASK`
   - 若不能拆出可执行任务，说明粒度不正确
7. 必须能够派生 `TESTSET`
   - 若无法形成测试集，说明验收边界不成立
8. 不允许依赖 `UI`
   - `UI` 是 `FEAT` 的派生对象，不是 `FEAT` 的前置定义
9. 必须来自 `EPIC` 或已冻结 `SRC`
   - 禁止无来源 `FEAT`
10. `FEAT ID` 必须稳定
   - 冻结后只允许新版本 supersede，不允许改写历史 ID

### 11.3 P1 Recommended Rules

以下为质量建议，不是硬阻塞：

1. 用户行为型 `FEAT` 可包含 `User Story`
   - `User Story` 是表达视角，不是治理主对象
2. 单个 `FEAT` 的 `User Story` 建议不超过 3 条
3. 单个 `FEAT` 的 `Acceptance Criteria` 建议控制在 3 到 5 条
4. `FEAT` 文档不应包含实现细节
   - 实现细节属于 `TECH` 或 `TASK`

### 11.4 User Story Decision

`User Story` 的治理定位固定为：

- 可选
- 仅适用于用户行为型 `FEAT`
- 用于补充用户视角和业务价值
- 不作为主链治理核心

正式治理核心仍然是：

- `FEAT`
- `Acceptance Criteria`
- `derived TASK`
- `derived TESTSET`

### 11.5 FEAT Size Signals

出现以下信号时，应优先拆分 `FEAT`：

- `User Story > 3`
- `Acceptance Criteria > 5`
- `TASK > 6`

### 11.6 FEAT Lifecycle

推荐生命周期：

`draft -> active -> frozen -> archived`

### 11.7 FEAT Granularity Rule

默认粒度标准：

> 一个 `FEAT` 应能在一个迭代内完成并验收。

通常对应：

- 1 到 2 周开发窗口

### 11.8 FEAT to TASK Derivation Rules

`TASK` 是 `FEAT` 的执行派生，不是独立需求源。

正式规则：

1. `TASK` 必须可追溯回单一 `FEAT`
2. `TASK` 默认从以下输入派生：
   - `FEAT`
   - `Acceptance Criteria`
   - `UI`（若涉及前端）
   - `TECH`（API included）
3. `TASK` 必须至少覆盖以下执行域之一：
   - `frontend`
   - `backend`
   - `integration`
   - `qa`（可选）
4. 每个 `TASK` 必须具备：
   - 稳定 `task_id`
   - `lane`
   - `owner_role`
   - `depends_on`
   - `acceptance_criteria_refs`
   - `definition_of_done`
5. `TASK` 不得反向定义 `FEAT`
   - 只能实现 `FEAT`
   - 不能替代 `FEAT`

推荐拆解模式：

- `frontend task` 实现界面和交互
- `backend task` 实现服务和数据能力
- `integration task` 完成联调与端到端拼接
- `qa task` 承担测试数据、验收支持或验证编排

### 11.9 FEAT to TESTSET Derivation Rules

`TESTSET` 是 `FEAT` 的测试派生对象，但其治理归属属于 `QA`，不属于 `product`。

正式规则：

1. 每个 `FEAT` 必须可被 `QA` 派生为 `TESTSET`
2. `TESTSET` 生成的最小输入为：
   - `FEAT`
   - `Acceptance Criteria`
   - `TECH`
   - 风险和依赖信息
3. `product` 不直接承载 `TESTSET` 生成职责
4. `product` 必须向 `QA` 提供稳定 seed，使 `QA` 能基于现有 `test-set` contract 生成正式 `TESTSET`
5. `TESTSET` 必须显式验证其父 `FEAT`

因此链路上的职责分工固定为：

- `product`: 生成 `FEAT` 与 `delivery prep`
- `qa`: 基于 `FEAT` 和 `delivery prep` 派生 `TESTSET`

### 11.10 Delivery Prep as TESTSET Seed

`Delivery Prep` 除了服务研发开工，还必须满足 `QA` 生成 `TESTSET` 的最小输入要求。

因此 `Delivery Prep` 应至少为每个 `FEAT` 提供：

- `feat_id`
- `acceptance_criteria`
- `task lanes`
- `tech dependencies`
- `risk notes`
- `entry conditions`
- `integration points`

若这些信息缺失，即使研发可勉强开工，也不视为完整的 `Delivery Prep Freeze`。

## 12. Contract and Output Strategy

### 12.1 Delivery Prep Output

`Delivery Prep Freeze` 推荐形成两类产物：

1. 正式对象
- `UI`
- `TECH`
- `TASK`

2. 冻结视图 / bundle
- `delivery_prep_freeze`
- `delivery_plan_review`

补充约束：

- `delivery_prep_bundle` 必须同时可作为 `QA` 生成 `TESTSET` 的 seed 输入
- 不允许在 `product` 目录下复制一份平行 `TESTSET` contract

### 12.2 Development Plan Binding

`TASK` 计划对象必须至少覆盖：

- 任务粒度
- 角色归属
- 依赖关系
- 排期概要
- 里程碑
- 关键路径

如现有 `development-plan-contract` 表达不足，后续应扩充而不是绕过。

## 13. Placement Decision

本设计文档的正式路径是：

- `spec/adr/ADR-003__product-department-ssot-design.md`

不是：

- `spec-global/departments/product/...`
- `spec-global/departments/prd/...`

原因：

- `spec/` 是项目级 SSOT 正文落点
- `spec-global/` 是框架规范与元数据层
- 本文档属于项目级正式设计决策

## 14. Migration Rule

迁移原则：

1. `departments/product/` 作为实现与 workflow 路径继续存在
2. 正式设计决策以本 ADR 为准
3. `departments/prd/` 仅保留兼容和历史参考
4. 后续新增 contract / workflow / gate 应按本 ADR 演进

## 15. ADR As Execution Context

### 15.1 Rule

ADR 的主要使用方式是“约束上下文输入”，不是“主链派生产物”。

下游对象和流程在需要遵守正式决策时，应显式注入：

- `governing_adrs`
- `decision_refs`
- `decision_constraints`
- `architecture_constraints`
- `process_constraints`

### 15.2 Where ADR Must Be Used

在这些面上，ADR 应作为执行上下文传入相关 agent 或 skill：

- `feat-to-delivery-prep`
- `dev.feature`
- `qa.test-set-production`
- spec maintainer agents
- skill maintainer / creator 流程

### 15.3 Expected Behavior

当 agent 或 skill 收到 `governing_adrs` 时，应：

- 将其视为硬约束
- 在生成 `TECH / TASK / TESTSET / workflow / contract / agent / skill` 时主动遵守
- 在必要时于输出中保留 trace 引用

推荐标准化约定：

- `governing_adrs`
  - 用于输入上下文，给出相关 ADR refs
- `decision_refs`
  - 用于输出 trace，记录本次实际采用了哪些 ADR
- `decision_constraints`
  - 用于简化 prompt/context，把 ADR 抽成必须执行的规则
- `architecture_constraints`
  - 用于声明对象归属、依赖边界、拆分规则
- `process_constraints`
  - 用于声明 freeze、review、evidence、handoff 规则

### 15.4 Typical Examples

- `TECH` 设计读取 ADR，确认 `API` 归 `TECH` 而不是独立主类型
- `TASK` 规划读取 ADR，确认 `UI -> frontend`、`TECH -> frontend/backend` 的主依赖
- `TESTSET` 生成读取 ADR，确认测试派生依赖的是 `FEAT` 和 `delivery prep seed`
- spec maintainer agent 读取 ADR，确认当前维护的是项目级决策还是框架级规则

### 15.5 Trace Rules

推荐 trace 落点：

- `TECH.properties.governing_adrs`
- `TASK.traceability.governing_adrs`
- `TASK.traceability.decision_refs`
- `TESTSET.traceability.governing_adrs`
- `TESTSET.traceability.decision_refs`
- `workflow instance context.decision_refs`

这些字段用于审计回答：

- 为什么采用当前对象拆分
- 当前依赖和 freeze 规则来自哪条正式决策
- 本次产物是否符合治理约束

## 16. Spec Governance Entry

产品部门的 spec 维护推荐统一通过以下 skill 进入治理流程：

- `C:\Users\shado\.codex\skills\lee-spec-governance\SKILL.md`

该 skill 的职责不是替代 spec maintainer agents，而是：

- 识别当前修改的是 workflow / agent / contract / gate / skill / review spec
- 将修改路由到正确的 core maintainer 边界
- 要求完成后执行 `spec-review`
- 防止直接手改 spec 导致治理边界失效

对应维护边界：

- workflow -> `spec-global/core/agents/workflow-spec-maintainer`
- agent -> `spec-global/core/agents/agent-spec-maintainer`
- contract -> `spec-global/core/agents/contracts-spec-maintainer`
- gate -> `spec-global/core/agents/gates-spec-maintainer`
- review -> `spec-global/core/agents/spec-review`

## 16. Follow-up

后续需要继续完成：

1. 将 `FEAT` 的 `TESTSET` 派生规则纳入正式 contract / validator
2. 扩充 `Delivery Prep Freeze` 对可执行实施计划的 schema 和 validator
3. 在运行时 validator 中增加产品链路约束
4. 清理剩余 `prd` 兼容路径并收紧 deprecated 约束
