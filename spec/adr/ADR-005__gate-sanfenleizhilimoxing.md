---
id: ADR-005
ssot_type: adr
title: Gate 三分类治理模型
status: frozen
version: v1
parent_id: null
derived_from_ids: []
source_refs: []
owner: codex
tags: []
properties: {}
frozen_at: '2026-03-11T14:48:58.883070'
---

# Problem

LEE 当前的 gate 语义混杂了自动规则检查、人工审阅、正式放行三种职责。

现状问题包括：

- `auto_check` 与 `human_approval` 只区分“是否需要人”，没有区分治理职责。
- freeze gate 同时承担审批、阶段冻结、文件快照输出，责任边界不清晰。
- `Review Gate` 和 `Approval Gate` 混用，导致“审阅意见”和“正式放行”无法分层。
- 自动规则判定与人工责任确认没有统一建模，难以扩展到多 reviewer、override、risk acceptance、freeze ref 等能力。

如果不先统一 gate 的治理模型，后续 runtime、CLI、DB、workflow 模板重构会继续沿用混合语义，造成实现复杂化和行为不一致。

# Decision

LEE 统一将 gate 定义为工作流中的正式决策边界组件，并分为三类：

1. `Auto Gate`
   - 由机器自动判定是否满足继续执行条件。
   - 适用于 schema、contract、完整性、阈值、规则性合规检查。
   - 输出 machine verdict，可为 `pass`、`fail`、`escalate`。

2. `Review Gate`
   - 由机器提供 review package，人类基于 evidence、findings、diff、风险信息做审阅决策。
   - 适用于设计评审、质量评审、风险判断、异常升级。
   - 输出 review decision，可为 `approve`、`revise`、`reject`、`flag`。

3. `Approval Gate`
   - 由责任人对阶段放行承担正式责任。
   - 适用于 freeze、release、风险接受、正式签字放行。
   - 输出 approval record，可为 `approve`、`reject`。

同时明确以下约束：

- Gate 不等于人工审批节点，Human Gate 只是 Gate 的一种参与方式，不是 Gate 的定义本体。
- freeze 属于 `Approval Gate`，不是 `Review Gate`。
- `Review Gate` 不直接等价于 freeze，也不承担正式放行责任。
- `Auto Gate` 失败时只能直接失败，或升级到 `Review Gate`，不能直接冒充 `Approval Gate`。
- gate 的核心输出应是统一的决策结果与引用对象，例如 `gate_result`、`*_freeze_ref`，而不是把 freeze 文件视为主对象。

# Decision Object

Gate 的决策对象不是单一按钮动作，而是某个工作流边界上的正式继续执行判断。

每个 gate 至少应绑定以下决策对象之一：

- 当前步骤产出物是否满足进入下一边界的条件
- 当前阶段是否允许正式结束并进入下游阶段
- 当前 SSOT 对象或对象集合是否允许进入冻结或放行状态
- 当前风险集合是否被接受、退回修订或需要升级处理

因此，gate 的决策对象可以落在 step、artifact、stage 上，但其语义必须统一表达为：

- 是否允许继续执行
- 若不允许，应该如何回退、修订、升级或终止

# Gate Result Contract

所有 gate 都应输出统一的 `gate_result` 对象，作为 runtime、CLI、审计和下游 workflow 的标准输入。

`gate_result` 至少应包含：

- `gate_id`
- `gate_type`
- `decision`
- `decision_by`
- `decision_at`
- `subject_refs`
- `rule_results`
- `evidence_refs`
- `comments`
- `structured_feedback`
- `next_action`

其中：

- `gate_type` 取值为 `auto`、`review`、`approval`
- `decision` 取值受 gate 类型约束
- `subject_refs` 用于标识当前 gate 实际作用的 step / artifact / stage
- `rule_results` 用于记录机器规则判定结果
- `evidence_refs` 用于记录审阅和审批所依据的正式证据
- `next_action` 用于表达继续、回退、重试、升级、派生新工作流等动作

freeze 类 gate 除 `gate_result` 外，还应输出正式的 `*_freeze_ref`，用于表达冻结后的 SSOT 引用，而非依赖 freeze 文件实体。

# Allowed Decisions By Gate Type

不同类型 gate 只允许使用与其职责一致的决策集合。

`Auto Gate` 允许：

- `pass`
- `fail`
- `escalate`

`Review Gate` 允许：

- `approve`
- `revise`
- `reject`
- `flag`

`Approval Gate` 允许：

- `approve`
- `reject`

同时约束如下：

- `Auto Gate` 不承担正式责任放行，因此不能直接输出 `approve` 语义替代 `Approval Gate`
- `Review Gate` 可以输出 `approve`，但该 `approve` 仅表示“审阅通过”，不自动等价于正式冻结或放行
- `Approval Gate` 的 `approve` 才表示正式责任确认与边界放行

# Freeze Semantics

freeze 是 SSOT 对象的正式状态变化，而不是一个额外文件类型。

因此：

- freeze 必须归类为 `Approval Gate`
- freeze 的主结果是 SSOT 状态转为 `frozen`
- freeze 的标准输出是 `*_freeze_ref`
- freeze 文件若存在，只能视为兼容快照、导出物或调试产物，不应再作为主真理载体

下游 workflow 应长期以冻结后的 SSOT 引用为主输入，而不是以 freeze 文件路径为主输入。

# Escalation Rules

Gate 之间允许按职责逐级升级，但不允许职责逆转。

允许的升级路径：

- `Auto Gate -> Review Gate`
- `Review Gate -> Approval Gate`

不允许的路径：

- `Auto Gate -> Approval Gate` 直接跳过审阅判断
- `Review Gate` 直接冒充 freeze 完成正式放行

推荐模式如下：

1. `Auto Gate` 先完成规则检查
2. 若规则失败但仍需人工判断，则升级为 `Review Gate`
3. 若边界需要责任确认或冻结放行，则进入 `Approval Gate`

当某一边界同时存在审阅与放行要求时，应拆成前置 `Review Gate` 和后置 `Approval Gate`，而不是将两类职责混入同一个 gate。

# Scope

本 ADR 约束以下范围：

- orchestrator runtime 中 gate 的类型语义与状态流转
- workflow 模板中的 gate 分类与命名
- CLI/API 中 gate 的展示、审批、修订、拒绝和升级动作
- freeze 语义与 gate 的关系
- 后续 gate 数据模型、存储模型、审批记录模型的重构方向

# Non-Goals

本 ADR 当前不直接规定：

- 具体数据库表结构如何迁移
- 具体 CLI 交互界面如何设计
- 旧 gate 文件快照能力是否立即删除
- cross/stg/ui 等全部历史 freeze 体系的同步迁移方案

这些内容应在后续 EPIC/FEAT 中分别落地。

# Consequences

采纳该 ADR 后：

- LEE 中所有 gate 都必须首先明确自己属于 `Auto Gate`、`Review Gate`、`Approval Gate` 之一。
- product 主链中的 `source_freeze`、`epic_freeze`、`feat_freeze`、`delivery_prep_freeze` 应归类为 `Approval Gate`。
- 现有 `auto_check` 语义应收敛为 `Auto Gate`。
- 现有 `human_review` / `human_decision` / 类似人审流程应收敛为 `Review Gate`。
- freeze 文件应逐步从“主交接物”降级为兼容产物，长期方向是保留 freeze 状态与 freeze ref，而不是依赖 freeze 文件实体。
