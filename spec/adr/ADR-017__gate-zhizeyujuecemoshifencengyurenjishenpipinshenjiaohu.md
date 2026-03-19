---
id: ADR-017
ssot_type: adr
title: Gate 职责与决策模式分层及人机审批交互收敛
status: frozen
version: v1
workflow_instance_id: gate-governance-design-20260315
parent_id: null
derived_from_ids:
- id: ADR-005
  version: v1
- id: ADR-006
  version: v1
- id: ADR-015
  version: v1
source_refs: []
owner: governance
tags:
- gate
- review
- approval
- cli
- workflow
- human-in-the-loop
properties:
  adr_kind: governance_design
  decision_scope: gate_purpose_mode_and_human_gate_cli
frozen_at: '2026-03-17T17:17:55.525189'
---

# Gate 职责与决策模式分层及人机审批交互收敛

## 1. Decision

LEE 不再把 gate 的分类建立在单一 `gate_type` 轴上，而采用二维模型：

- `purpose`
  - `review`
  - `approval`
- `decision_mode`
  - `auto`
  - `conditional_human`
  - `human_required`

本 ADR 冻结以下规则：

- Gate 的职责语义由 `purpose` 表达，而不是由“是否需要人类”直接表达。
- Gate 的执行与参与方式由 `decision_mode` 表达，而不是把 `review`、`approval`、`human gate` 混为同一层概念。
- `review` 与 `approval` 的边界必须严格分离：
  - `review` 负责质量、风险、证据、边界正确性判断
  - `approval` 负责正式责任确认、freeze、release、风险接受和边界放行
- `approval` 在默认治理模型下只允许 `human_required`，不允许 `auto approval` 成为正式主路径。
- 所有进入人工决策的 gate，都必须先产出可审阅的 `human_gate_context`，CLI 审批必须消费该上下文，而不能只显示一个裸 `gate_id`。

若与 `ADR-005` 的单轴三分类表述冲突，以本 ADR 为准；`ADR-005` 中关于 freeze 必属正式放行边界、review 不等于 freeze 的约束继续有效。

## 2. Context

当前仓库里同时存在三套彼此未完全对齐的 gate 心智：

- 治理 ADR 层把 gate 表达为 `Auto Gate / Review Gate / Approval Gate`
- workflow 模板层大量使用 `auto_check / human_review / human_approval`
- runtime/CLI 层又将大部分人工 gate 折叠成 `human_gate`

这导致两个直接问题。

### 2.1 Review 与 Approval 边界仍然模糊

当前语义里，`human_review` 与 `human_approval` 虽然名字不同，但：

- 常共用同一套 pending gate 记录和 CLI 决策入口
- 共用相似的 approve/reject/revise/flag 操作模型
- 在运行时未形成独立的职责边界

结果是：

- “审阅通过”容易被误解为“正式放行”
- freeze 前的质量判断与 freeze 时的责任承担容易混在一起
- 人类审批记录无法稳定表达“这是 review 决定还是 approval 决定”

### 2.2 Human Gate 当前几乎不可审批

当前 CLI 的主要问题不是“没有 approve 命令”，而是“没有可审批的上下文”。

典型症状包括：

- gate 卡住时只知道有一个 pending gate，却不知道为何触发
- 不知道当前 gate 审的对象是 step、artifact、phase 还是 freeze
- 不知道需要去哪里看 evidence、review report、diff、candidate package
- `lee gates list` 只能看到少量 DB 字段，无法支持真正的责任判断
- `lee gates approve/reject/revise` 交互前没有结构化 review capsule，审批者只能凭猜测做决定

这使得当前 human gate 更像“流程阻塞器”，而不是“可执行的治理边界”。

## 3. Problem

如果继续沿用单轴 gate 分类，并保持当前 CLI 只暴露裸 gate 记录，LEE 会持续出现以下问题。

### 3.1 职责和参与方式混杂

`review` / `approval` 是职责差异，`auto` / `conditional_human` / `human_required` 是决策参与方式差异。

把这两类概念挤在一个 `gate_type` 字段中，会导致：

- 类型数量持续膨胀
- 同一种职责在不同参与方式下难以统一治理
- runtime、CLI、trace、DB 都需要不断引入临时兼容语义

### 3.2 Human Gate 无法形成稳定审计闭环

如果审批时没有统一上下文对象：

- 决策原因无法审计
- evidence 引用无法稳定回放
- 人类只是在“点击继续”，而不是在“审阅并承担责任”
- gate 记录无法成为 downstream workflow、审计和 trace 的稳定输入

### 3.3 Freeze 与 Review 仍会互相污染

freeze 是正式放行，而不是单纯的审阅结果。

如果不单独固定 `approval` 职责：

- review approve 容易越权等价为 freeze
- auto gate 失败升级后，可能绕过 review 直接进入“形式上的通过”
- Product/QA/Dev 的关键边界无法稳定形成“先 review，再 approval”的闭环

## 4. Decision Model

### 4.1 Purpose

每个 gate 必须先声明 `purpose`。

允许值固定为：

- `review`
- `approval`

#### `review`

`review` 回答的问题是：

- 当前产物是否满足质量与边界要求
- 当前证据是否足以支持继续推进
- 当前风险是否需要修订、拒绝、标记或升级

`review` 不承担正式 freeze / release / 风险接受责任。

#### `approval`

`approval` 回答的问题是：

- 谁对继续推进承担正式责任
- 当前对象是否允许冻结、发布、合并、阶段完成或风险接受

`approval` 必须与责任人、证据引用和 subject 绑定。

### 4.2 Decision Mode

每个 gate 必须再声明 `decision_mode`。

允许值固定为：

- `auto`
- `conditional_human`
- `human_required`

#### `auto`

由 agent / machine 直接给出决策。

适用于：

- 规则检查
- 阈值检查
- 契约完整性检查
- 证据完整性与路径约束检查

#### `conditional_human`

由 agent 先做初判，再根据规则决定是否升级给人类。

适用于：

- 初步风险评估
- findings 聚类后判断是否需要人工介入
- candidate package 质量初筛

`conditional_human` 的核心不是“人可选”，而是“必须先给出升级理由和机器初判”。

#### `human_required`

必须由人类做正式决策。

适用于：

- 审阅结论必须由人类确认的 review 边界
- freeze / release / merge / risk acceptance 等正式 approval 边界

### 4.3 Allowed Combinations

最小可用组合固定如下：

- `review + auto`
- `review + conditional_human`
- `review + human_required`
- `approval + human_required`

默认不允许：

- `approval + auto`
- `approval + conditional_human`

若未来确需引入机器辅助 approval，只能作为带明确人类 signoff 的受限扩展，不得成为默认主路径。

## 5. Decision Semantics

### 5.1 Decisions By Purpose

`review` 允许：

- `approve`
- `revise`
- `reject`
- `flag`

`approval` 允许：

- `approve`
- `reject`

### 5.2 Semantics Constraint

必须遵守以下语义约束：

- `review approve` 仅表示审阅通过，不自动等价于 freeze、release 或正式放行
- `approval approve` 才表示责任确认与边界放行
- `approval reject` 必须明确回退、终止或派生动作
- `conditional_human` 若升级给人类，必须带上 agent 初判、升级原因和相关 evidence refs

## 6. Unified Gate Result

所有 gate 必须输出统一的 `gate_result`。

最小字段如下：

- `gate_id`
- `purpose`
- `decision_mode`
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

- `subject_refs` 用于标识当前 gate 实际作用对象，例如 step、artifact、phase、release bundle
- `rule_results` 记录 machine checks、thresholds、findings 摘要和 escalation reason
- `evidence_refs` 引用 candidate package、review report、diff、test results、freeze source 等
- `next_action` 表达继续、回退、重试、升级、spawn 新 workflow 等动作

freeze / release 类 `approval` gate 除 `gate_result` 外，还必须输出正式引用对象，例如：

- `source_freeze_ref`
- `epic_freeze_ref`
- `feat_freeze_ref`
- `delivery_prep_freeze_ref`
- `merge_decision_ref`
- `release_decision_ref`

## 7. Human Gate Context Contract

凡是 `decision_mode=human_required` 或 `conditional_human` 升级给人的 gate，都必须生成 `human_gate_context`。

它是人类审批的最小上下文对象，不得省略。

### 7.1 Minimum Fields

`human_gate_context` 至少应包含：

- `gate_id`
- `purpose`
- `decision_mode`
- `workflow_id`
- `current_step`
- `blocked_reason`
- `subject_refs`
- `summary`
- `why_now`
- `decision_question`
- `recommended_actions`
- `approval_criteria`
- `review_checklist`
- `evidence_refs`
- `artifact_refs`
- `candidate_package_ref`
- `structured_feedback`
- `upstream_outputs`
- `related_but_untouched`
- `risk_summary`
- `fallback_actions`

### 7.2 Human Readability Rule

`human_gate_context` 必须同时满足：

- 可机器消费
- 可 CLI 直接渲染
- 审批者在不翻源码的情况下，能先理解“为什么卡住”和“审什么”

不允许再出现只有 `gate_id + status + reviewers` 的裸 gate 审批体验。

## 8. Human Gate CLI Decision

### 8.1 CLI Goal

Human gate CLI 的目标不是“提供 approve/reject 按钮”，而是：

- 让审批者快速理解 gate 的职责、对象、证据和影响面
- 让审批者知道当前应该看什么，而不是自己在仓库中盲搜
- 让审批决定直接绑定证据、评论、结构化反馈和后续动作

### 8.2 Required Commands

最小 CLI 入口建议固定为：

- `lee gates list`
- `lee gates show <workflow_id> <gate_id>`
- `lee gates decide <workflow_id> <gate_id>`
- `lee gates approve <workflow_id> <gate_id>`
- `lee gates revise <workflow_id> <gate_id>`
- `lee gates reject <workflow_id> <gate_id>`
- `lee gates flag <workflow_id> <gate_id>`

其中：

- `list` 只负责发现 gate
- `show` 负责上下文展示
- `decide` 负责交互式决策
- 其他命令负责脚本化和显式决策

### 8.3 Required `list` Output

`lee gates list` 至少应显示：

- `gate_id`
- `purpose`
- `decision_mode`
- `workflow_id`
- `step_id`
- `subject`
- `status`
- `created_at`
- `why_now` 摘要

审批者看到 list 时，必须能立刻知道：

- 这是 review 还是 approval
- 是必须人审还是条件升级
- 审的是什么对象

### 8.4 Required `show` Output

`lee gates show` 必须渲染 `human_gate_context`，至少分成以下区块：

1. `What Is This`
- gate 类型
- 当前职责
- 当前问题

2. `Why Blocked`
- 触发原因
- 上游 machine result
- 是否由 `conditional_human` 升级而来

3. `What You Are Deciding`
- 当前决策问题
- 允许的 decision 集
- 该 decision 的后果

4. `Evidence`
- candidate package
- review report
- test / diff / artifact / freeze source refs
- 关键文件路径或产物路径

5. `Checklist`
- approval criteria
- review checklist
- 未验证项
- 风险摘要

6. `Next Actions`
- approve 后会发生什么
- revise/reject/flag 后会发生什么
- 推荐命令

### 8.5 Required `decide` Interaction

`lee gates decide` 必须是上下文驱动的交互，而不是裸确认框。

最小流程：

1. 先展示 `human_gate_context` 摘要
2. 要求审批者选择决策
3. 根据决策类型要求补充必要字段
4. 再次展示“决策后果摘要”
5. 最后确认并提交

决策时的最小输入要求：

- `approve`
  - 必填：`decision comment`
- `revise`
  - 必填：`reason`
  - 必填：`target_step` 或默认回退目标
  - 可选：`structured_feedback`
- `reject`
  - 必填：`reason`
  - 必填：`next_action`
- `flag`
  - 必填：`issues`
  - 必填：是否继续 workflow

### 8.6 Required Linkability

CLI 中出现的 evidence refs、artifact refs、candidate package refs，必须能直接：

- 打印为路径
- 被后续子命令消费
- 支持跳转到对应对象或文件

人类审批不应再依赖“自己猜这个 gate 可能和哪个文件有关”。

## 9. Workflow Rules

### 9.1 Review Before Approval

当某一边界同时存在质量审阅与正式放行要求时，必须拆成两个 gate：

1. 前置 `review`
2. 后置 `approval`

不得再用一个 `human_approval` 同时承担：

- finding 审阅
- 风险判断
- freeze 放行

### 9.2 Conditional Human Upgrade Rule

`review + conditional_human` 的升级必须满足：

- 机器先给出初判
- 初判必须附带升级理由
- 升级后必须生成 `human_gate_context`

不允许只因为“系统不知道怎么办”就直接抛给人，且不给上下文。

### 9.3 Freeze Rule

freeze 始终属于：

- `purpose=approval`
- `decision_mode=human_required`

其最小输入至少包括：

- 上游 review 结论
- 当前 freeze subject
- candidate package 或 freeze package
- evidence refs
- 下游将消费的正式 `*_freeze_ref`

## 10. Gate Flow And Workflow State Machine

### 10.1 Scope

本节定义两个相互协同但不得混淆的状态机：

- `gate_instance.status`
- `workflow.status`

`gate_instance.status` 负责表达当前 gate 决策生命周期。

`workflow.status` 负责表达整个 workflow 是否继续推进、暂停等待、失败终止或被派生替代。

### 10.2 Workflow Status Baseline

第一阶段沿用现有 workflow 状态集合：

- `pending`
- `running`
- `paused`
- `completed`
- `failed`
- `superseded`

并冻结以下约束：

- gate 被创建并等待人工决策时，workflow 必须进入 `paused`
- gate 决策后若 workflow 继续推进，必须先回到 `running`
- workflow 不得从 `paused` 直接跳到 `completed`
- `failed` 与 `superseded` 是终止性状态，不得继续 enqueue 原 workflow 的后续步骤

### 10.3 Gate Status Baseline

第一阶段沿用现有 gate 状态集合：

- `pending`
- `approved`
- `rejected`
- `revised`
- `flagged`
- `invalidated`

最小生命周期约束如下：

- gate 创建后初始状态固定为 `pending`
- `pending` 只能流转到终局决策态之一：`approved / rejected / revised / flagged`
- `invalidated` 不是人工主动决策，而是上游 rewind / retry / spawn 后对旧 gate 的作废标记
- 处于 `approved / rejected / revised / flagged / invalidated` 的 gate 不得再次被决策

### 10.4 Gate Creation Rule

当任一 gate 实例被创建时，必须同步满足以下条件：

1. 记录 `gate_result` 初始骨架，至少包含 `gate_id / purpose / decision_mode / subject_refs / evidence_refs`
2. 若 `decision_mode=human_required`，或 `conditional_human` 已判断为升级给人，则生成 `human_gate_context`
3. workflow 从 `running` 切换到 `paused`
4. `current_step` 保持在 gate 所属 step，不得偷偷推进到下游 step

换言之，人工 gate 的本质是“在当前 step 上暂停等待决策”，而不是“跳过 step，另开一条人工旁路”。

### 10.5 Decision To Transition Matrix

#### `review + approve`

- gate: `pending -> approved`
- workflow: `paused -> running`
- step effect: 完成当前 gate step
- next action: `continue`
- side effect: 不触发 freeze，不生成正式 release/merge 决议

#### `approval + approve`

- gate: `pending -> approved`
- workflow: `paused -> running`
- step effect: 完成当前 gate step
- next action: `continue`
- side effect: 执行 freeze / publish / merge / release decision materialization
- completion rule: 若该 gate step 已是最后阻塞边界，则在恢复 `running` 后按正常完成检测进入 `completed`

#### `review + revise`

- gate: `pending -> revised`
- workflow: `paused -> running`
- step effect: 不视为当前产物通过，而是执行 `rewind_to(..., mode=retry)`
- next action: `retry`
- side effect: 自目标步骤起的下游执行记录、旧 gate 决策、相关临时产物都应被作废

#### `review + reject`

`review reject` 不等于一个固定动作，必须显式绑定 `next_action`。

允许的最小动作：

- `rollback`
- `spawn`
- `terminate`

对应规则：

- `rollback`
  - gate: `pending -> rejected`
  - workflow: `paused -> running`
  - step effect: 执行 `rewind_to(..., mode=rollback)`
- `spawn`
  - gate: `pending -> rejected`
  - workflow: 原 workflow `paused -> superseded`
  - side effect: 创建新 workflow 继承必要上下文，原 workflow 不再继续
- `terminate`
  - gate: `pending -> rejected`
  - workflow: `paused -> failed`
  - side effect: 终止当前 workflow，保留拒绝原因与 evidence

#### `approval + reject`

`approval reject` 同样必须显式绑定 `next_action`，但默认治理更严格。

允许的最小动作：

- `rollback`
- `spawn`
- `terminate`

附加约束：

- freeze / release / merge 类 `approval reject` 默认不允许“静默继续”
- 若选择 `rollback`，必须明确回退边界，不能只写“退回上一步”
- 若选择 `terminate`，必须记录责任说明、拒绝原因和关键 evidence refs

#### `review + flag`

`flag` 只属于 `review`，用于“发现问题但不立即作废当前推进结论”的场景。

允许两种后果：

- `continue_with_risk`
  - gate: `pending -> flagged`
  - workflow: `paused -> running`
  - step effect: 完成当前 gate step
- `hold`
  - gate: `pending -> flagged`
  - workflow: 保持 `paused`
  - step effect: gate 保持为已标记但待进一步处理

`flag` 不得用于 `approval`，避免把正式放行责任偷换成“先标记再说”。

### 10.6 `next_action` Enum

为保证 CLI、DB、trace 和 runtime 一致，`gate_result.next_action` 第一阶段固定为：

- `continue`
- `retry`
- `rollback`
- `spawn`
- `terminate`
- `continue_with_risk`
- `hold`
- `escalate`

约束如下：

- `approve` 只能搭配 `continue`
- `revise` 只能搭配 `retry`
- `reject` 只能搭配 `rollback / spawn / terminate`
- `flag` 只能搭配 `continue_with_risk / hold`
- `escalate` 只用于机器初判阶段，不是人工最终决策结果

### 10.7 Rewind And Invalidation Rule

当 gate 触发 `retry` 或 `rollback` 时，系统必须执行统一的 rewind 原语，而不是局部手工改状态。

rewind 后至少要保证：

- 目标步骤之后的 `TaskExecution` 记录被标记为 `invalidated` 或被等价作废
- 目标步骤之后产生的 gate 记录被标记为 `invalidated`
- 旧 `human_gate_context` 不得继续用于新一轮审批
- 下游 `step_outputs`、临时 candidate package、旧 review capsule 必须按治理规则清理或重建

### 10.8 Spawn Rule

当 gate 拒绝后选择 `spawn`：

- 原 workflow 进入 `superseded`
- 新 workflow 必须显式记录 `parent_workflow_id` 或等价的派生关系
- 新 workflow 必须带上触发 gate、拒绝原因、必要输入上下文
- 原 workflow 的 pending gate 全部视为不可再决策对象

`spawn` 适用于“不是简单回退修一下，而是要开一条新的治理路径”的场景，例如：

- 方案被否决，需要新方案重走主链
- 当前工作流上下文已不适合作为修订基础
- 需要把责任边界切换到新的 package / candidate / phase

### 10.9 Workflow Completion Rule

gate 决策本身不直接宣告 workflow 完成，除非它只是恢复正常执行后，由现有完成检测判定 workflow 已无后续可执行步骤。

因此必须遵守：

- gate `approve` 后，先恢复到 `running`
- gate step 被正常完成
- 然后由统一 completion check 决定是否进入 `completed`

这样可以避免形成“审批命令直接把 paused workflow 硬改成 completed”的旁路。

### 10.10 CLI State Preview Rule

`lee gates decide` 在最终确认前，必须预览本次决策会造成的状态变化。

最小预览内容包括：

- `gate status: pending -> ...`
- `workflow status: paused -> ...`
- `step effect`
- `next_action`
- `affected steps`
- `will invalidate`
- `will freeze/publish`
- `will spawn new workflow`

示例：

- `approve(review)`: `pending -> approved`, `paused -> running`, `complete current gate step`, `no freeze`
- `revise`: `pending -> revised`, `paused -> running`, `rewind to step <x>`, `invalidate downstream executions`
- `reject(spawn)`: `pending -> rejected`, `paused -> superseded`, `create new workflow`

若 CLI 无法计算这些后果摘要，则不应允许直接提交决策。

### 10.11 State Transition Guardrails

以下行为在治理上明确禁止：

- 用 `review approve` 直接代替 `approval approve`
- gate `reject` 后 workflow 仍保持 `running`
- gate `flag` 在 `approval` 中被用作“变相通过”
- gate 被 rewind 作废后仍允许继续 approve/reject
- 没有 `target_step` 却执行 `retry / rollback`
- 没有 `next_action` 却提交 `reject`

## 11. Compatibility Mapping

为兼容当前仓库语义，第一阶段允许以下映射：

- `auto_check`
  - -> `purpose=review`
  - -> `decision_mode=auto`
- `human_review`
  - -> `purpose=review`
  - -> `decision_mode=human_required`
- `human_approval`
  - -> `purpose=approval`
  - -> `decision_mode=human_required`

若现有 runtime 中存在“auto fail 后 fallback 到 human_review”的模式，则应解释为：

- 原 auto gate：`review + auto`
- 升级后人工 gate：`review + conditional_human` 的人工分支

而不是“从 auto gate 变成另一个无类型 human gate”。

## 12. Implementation Direction

本 ADR 之后，后续实现建议按以下顺序推进：

1. 先统一 spec 和 workflow 模板中的 `purpose / decision_mode`
2. 再升级 runtime 分发逻辑，不再把非 auto gate 全折叠为 `human_gate`
3. 补 `gate_result` 与 `human_gate_context` contract
4. 升级 DB / trace / CLI 字段，使其能稳定表达 `purpose / decision_mode / subject / evidence`
5. 补人类审批 CLI 的上下文渲染和交互式决策体验

第一阶段可以保留旧字段，但必须显式做兼容映射，不允许再继续扩散新旧混合语义。

## 13. Non-Goals

本 ADR 当前不直接规定：

- 最终前端 UI 样式
- 数据库最终列名
- 所有历史 gate 记录的完整迁移方案
- 每个部门模板的一次性全集改造顺序

这些应由后续 `EPIC / FEAT / TASK / TESTSET` 承接。

## 14. Final Rule

关于 LEE 的 gate，今后固定三条规则：

- `review` 与 `approval` 是职责边界，不能再与“是否需要人类”混写在同一分类轴上。
- `auto / conditional_human / human_required` 是决策模式边界，不能再偷换成职责类型。
- 凡是进入 human gate 的审批，都必须先有可消费的 `human_gate_context`；没有上下文的 gate，不视为可审批 gate。
