---
id: ADR-015
ssot_type: adr
title: AI 交付护栏与候选结果包闭环治理
status: draft
version: v1
parent_id: null
derived_from_ids:
  - id: ADR-001
    version: v1
  - id: ADR-005
    version: v1
  - id: ADR-011
    version: v1
  - id: ADR-013
    version: v1
source_refs: []
owner: governance
tags:
  - governance
  - ai-delivery
  - gates
  - evidence
  - workflow
  - review
properties:
  adr_kind: governance_design
  decision_scope: ai_delivery_guardrails_and_candidate_package
---

# AI 交付护栏与候选结果包闭环治理

## 1. Decision

LEE 采纳“AI 交付护栏”作为后续演进方向，用统一的候选结果包、门禁闭环和证据约束，治理 AI 参与下的高吞吐交付。

本 ADR 冻结以下治理方向：

- AI 生成的实现、文档、配置或计划，默认只视为 `candidate result package`，不直接等价于完成态
- 任务完成语义必须由独立 gate 闭环确认，而不是由生成者自证
- 交付审查对象必须从“单个 diff”升级为“系统影响面 + 证据 + 风险 + 可回退性”
- canonical path、验证要求、证据要求、禁止路径和升级路径必须进入系统约束，而不是停留在聊天提示
- 后续 feature / bugfix / spec 交付链路都应逐步接入统一的 AI 交付护栏

本 ADR 当前冻结的是治理边界和必备能力面，不在本文件中直接冻结最终 CLI 命令名、数据库 schema 或 UI 交互细节。

## 2. Context

LEE 当前已经具备较强的流程治理基础：

- 存在 `.workflow` 运行时目录、locks、traces、approvals、workspace 等执行治理面
- 存在 `spec/source -> requirements -> tech -> tasks -> testing -> ui` 的 formal design 链路
- 存在 `tests/` 下的 unit、integration、orchestrator、qa 等验证资产
- 存在 `evidence/` 下的大量 run 级产物，可沉淀 `manifest`、review status、findings 和阶段输出
- 已通过 ADR 与 gate 设计逐步收敛 review / approval / freeze 的职责边界

但随着 AI 生成能力上升，当前链路仍存在新的结构性压力：

- 生成速度快于人工审阅速度，容易把 review 压成表面确认
- 有测试和 evidence，并不等于每次交付都形成统一、可审计、可比较的候选结果包
- canonical path、derived artifact、legacy path、历史 phase 副本之间的边界，对执行 agent 仍可能不够硬
- spec、implementation、evidence 之间虽然都存在，但一致性校验还没有统一提升为默认 completion 前门禁
- 很多关键约束仍可能散落在 prompt、对话和人工记忆中，长链路执行时容易漂移

因此，当前系统更接近“已经有 AI 参与的工程系统”，但还未完全成为“默认以 AI 高吞吐为前提设计的交付系统”。

## 3. Governing Principle

本 ADR 统一采用以下原则：

> AI 产出是候选交付物，不是完成事实；完成事实必须由验证、证据和独立决策边界共同确认。

该原则进一步展开为：

- 生成与完成必须分离
- 速度提升不能换取治理降级
- 交付护栏必须系统化，而不是提示词化
- 证据必须是默认产物，而不是事后补记
- 回退能力必须与放行能力同等重要

## 4. Problem

如果继续沿用“AI 先生成，人类凭经验看一下是否差不多”的弱治理方式，LEE 会面临以下风险。

### 4.1 Completion Ambiguity

生成者容易把：

- 代码已写完
- 文档已生成
- 某组测试通过

误当成“任务已完成”。

但在 LEE 中，真正的完成还取决于：

- 是否改在 canonical path
- 是否触达真实系统边界
- 是否更新了应更新的 spec / tests / evidence
- 是否通过了对应 gate

### 4.2 Context Drift

长链路、多文件、多阶段任务中，关键约束容易在执行过程中漂移，例如：

- 非目标被误做成目标
- 禁止编辑路径被误碰
- 局部通过被误解为全链闭环
- 上游 acceptance criteria 在下游被稀释

### 4.3 Evidence Fragmentation

即使 run 产物很多，如果缺少统一 candidate package，审阅者仍需要自己拼接：

- 改了什么
- 没改什么
- 跑了哪些验证
- 哪些风险未覆盖
- 是否真的满足完成标准

这会让 review 成本持续上升，并降低 gate 质量。

### 4.4 Silent Governance Bypass

如果 canonical path、required validations、forbidden paths、consistency checks 不是系统硬约束，执行 agent 可能在高速产出下绕过原本应存在的治理边界。

## 5. In Scope

本 ADR 约束以下未来演进方向：

- feature / bugfix / spec 交付中的 candidate result package 标准
- completion 前的 validation、review、approval 和 evidence 闭环
- canonical path 与 forbidden path 的执行约束
- spec / implementation / evidence 一致性校验
- AI 参与任务中的上下文约束注入、风险显式化和未验证项暴露
- 与回滚、freeze、审计、责任归属相关的交付语义

## 6. Out Of Scope

本 ADR 当前不直接规定：

- 某个具体执行器的 prompt 文本
- 某个单独 workflow 模板的完整 YAML 改法
- 所有历史 evidence run 的一次性迁移策略
- 某个数据库表的最终字段定义
- 前端展示界面的最终布局

这些内容应在后续 `EPIC / FEAT / TECH / TASK` 中分步落地。

## 7. Mandatory Guardrail Layers

LEE 后续 AI 交付治理至少必须补齐五层护栏。

### 7.1 Candidate Package Layer

每次 AI 主导的交付，在宣称可审查前都必须形成结构化候选结果包。

最小内容至少包括：

- 原始任务目标
- completion criteria
- changed files
- integration points
- impact scan
- validations run
- tests changed
- unverified items
- risks and assumptions
- criterion-by-criterion evidence playback

其目的不是增加文书工作，而是把“分散在脑中和对话里的完成判断”收敛为可审查对象。

### 7.2 Validation Layer

验证必须前置为完成判定的一部分，而不是实现结束后的附带动作。

后续系统至少应支持：

- unit / integration / workflow / e2e 等验证类型的声明与执行
- required validations by task type
- 未运行验证项的显式暴露
- 验证结果进入 candidate package 和 gate 输入

### 7.3 Constraint Layer

关键约束必须写进系统：

- canonical path allowlist
- forbidden path denylist
- legacy / evidence snapshot / historical phase path 保护
- 高风险动作的人审升级条件
- 不同任务类型的最小权限与最小写入面

### 7.4 Consistency Layer

后续交付必须逐步引入统一的一致性门禁，至少覆盖：

- spec 与 implementation 是否仍然对齐
- evidence 是否能回指本次 subject
- completion criteria 是否有实际证据支撑
- touched / untouched but related 区域是否被显式说明

### 7.5 Rollback And Release Layer

AI 交付护栏不只约束“如何生成”，也必须约束“如何撤退”。

系统后续至少应能表达：

- 当前产物是否已进入可放行边界
- 失败时回退到哪个正式状态
- freeze / approval 后可回溯的证据链
- 哪些变更是可逆的，哪些需要额外保护

## 8. Candidate Result Package Decision

LEE 统一将 `candidate result package` 视为 AI 交付链中的正式中间对象。

其语义如下：

- 它不是最终 truth object
- 它是 review gate 和 approval gate 的直接输入对象
- 它必须能承载“完成主张”和“未完成风险”同时存在
- 它必须允许 `REJECT`、`REVISE` 或 `ESCALATE`，而不是只服务于通过

因此，后续任何试图只输出 summary prose、原始 diff 或零散测试结果就直接进入 completion 判定的设计，都不再视为充分方案。

## 9. Gate Alignment Decision

AI 交付护栏必须与现有 gate 语义对齐，不得自行发明旁路。

后续推荐边界如下：

1. `Auto Gate`
   - 检查 required validations、路径约束、基础一致性、证据完整性
2. `Review Gate`
   - 基于 candidate package 审阅系统影响面、未验证项、风险和边界正确性
3. `Approval Gate`
   - 对正式放行、freeze、风险接受和阶段完成承担责任

同时明确：

- 生成 agent 不能直接输出完成态
- review 通过不自动等于正式完成
- approval 必须引用 candidate package 和 evidence，而不是脱离证据单独发生

## 10. Canonical Path Decision

LEE 后续必须把“优先 canonical path、禁止平行实现、禁止误改 legacy / snapshots”从软约定升级为硬治理。

最低要求包括：

- 系统能识别当前任务的 canonical editing surface
- 系统能识别 forbidden paths 和 deprecated paths
- 若变更落在风险路径，应在 Auto Gate 或 Review Gate 明确阻断或升级
- 不允许通过新增临时副本、平行目录或 copy-path 的方式规避真实集成

## 11. Rejected Option

### 11.1 Keep Prompt-Only Governance

不采纳“继续主要靠 prompt、人工记忆和口头提醒来约束 AI 交付”。

原因是：

- 长链路执行中约束容易漂移
- 规则无法稳定复用
- 无法形成统一审计证据

### 11.2 Treat Passing Tests As Completion

也不采纳“只要测试通过，就可视为任务完成”。

原因是：

- 测试通过不等于改在正确系统边界
- 测试通过不等于 spec / evidence 已闭环
- 测试通过不等于风险已被显式接受

### 11.3 Let Generator Self-Certify

不采纳“由生成 agent 自己声明 ready / done 即可进入完成态”。

原因是：

- 这会削弱独立 gate 的存在意义
- 会让 review 退化为装饰性步骤
- 无法稳定承接未来更高吞吐的 AI 交付量

## 12. Implementation Direction

本 ADR 之后，建议按以下方向拆解后续功能：

- 定义 `candidate result package` 的正式 contract / schema
- 在 workflow runtime 中增加 required validations 与 evidence completeness 检查
- 增加 canonical path / forbidden path 检测与升级逻辑
- 增加 `spec -> implementation -> evidence` consistency gate
- 为不同任务类型定义最小交付护栏 profile
- 让 review / approval CLI 或 UI 默认消费 candidate package，而不是消费自由文本总结
- 增加 rollback / fallback / freeze 对应的交付状态与证据引用设计

这些功能面应由后续 `EPIC / FEAT / TECH / TASK / TESTSET` 分层冻结，不在本 ADR 中直接细化到实现参数。

## 13. Consequences

采纳该 ADR 后：

- LEE 对 AI 交付的治理重心会从“生成质量”转向“交付闭环质量”
- 候选结果包会成为 review 与 gate 的核心输入对象
- evidence 将从附属材料进一步升级为默认交付组成部分
- workflow、gate、review、tests、spec 的职责边界会更清晰
- 后续任何新增 AI 交付能力，如果削弱独立 review、evidence 或 approval 语义，都应被视为违反本 ADR

## 14. Downstream Constraints

本 ADR 将作为后续以下对象的硬约束：

- AI 相关 delivery workflow
- review / approval gate 设计
- evidence pack 设计
- candidate package contract
- consistency testing and reporting
- canonical path enforcement

但本 ADR 不是业务需求源对象，不替代 `SRC / EPIC / FEAT`。

它的作用是：

- 约束未来交付系统如何接纳 AI 产出
- 约束完成语义如何被证明
- 约束治理边界如何不被高速生成绕开
