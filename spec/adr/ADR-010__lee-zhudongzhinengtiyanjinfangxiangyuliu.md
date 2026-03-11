---
id: ADR-010
ssot_type: adr
title: LEE 主动智能体演进方向预留
status: draft
version: v1
parent_id: null
derived_from_ids:
- id: ADR-001
  version: v1
- id: ADR-003
  version: v1
- id: ADR-006
  version: v1
source_refs:
- SRC-003
owner: architecture
tags:
- architecture
- agent
- autonomy
- roadmap
properties: {}
---

# LEE 主动智能体演进方向预留

## 1. Decision

LEE 采纳“主动智能体演进方向预留”决策，但当前仅冻结方向边界，不进入实现承诺。

该方向的核心决定如下：

- 保留“轻量感知/决策层 + 重量 workflow 执行层”的双层演进方向
- 保留“Skill 声明式注册、过滤、按需装配”的能力模型方向
- 保留“规则触发优先、目标驱动补充”的自主运行方向
- 保留“执行前预演 / dry-run / explain-plan”作为正式可解释性方向

同时明确，该方向必须建立在现有 LEE runtime 和治理体系之上，而不是旁路另起一套数字人平台。

## 2. Context

当前 LEE 已经具备：

- workflow 编排与状态机
- gate / approval 边界
- Agent / Skill / Executor 概念
- SSOT 物化与治理链
- CLI 作为统一入口

但这些能力主要面向“接到任务后执行”。对于“持续感知环境、判断是否应触发任务、决定调用何种能力、在执行前解释计划”这一层，现阶段仍缺少正式架构决策。

如果不先冻结方向边界，后续围绕 Agent、Skill、autonomy、planner 的设计容易出现以下漂移：

- 把自主触发做成旁路脚本
- 把 Skill 做成无治理的工具清单
- 把 PM Agent 继续膨胀成大一统决策者
- 为了主动能力再造一套并行 runtime

## 3. Governing Principles

### 3.1 Reuse Existing Runtime

未来任何主动智能体能力都必须优先复用现有：

- `lee cli`
- `src/lee/orchestrator/`
- artifacts / registry / evidence
- verifier / gate / workflow template

不允许先以“未来会合并”为理由创建并行 orchestrator 或独立 agent 平台。

### 3.2 Workflow Remains The Heavy Execution Path

复杂规划、状态流转、人工介入、产物落盘仍由现有 workflow/orchestrator 负责。

未来新增的主动能力层，不得取代 workflow 的重执行职责。

### 3.3 Autonomy Must Stay Governed

主动触发不等于绕过治理。

未来即使出现自主巡检、目标驱动规划，也必须继续接受：

- workflow 入口约束
- gate / review / approval
- artifact evidence
- SSOT source chain

### 3.4 ADR Does Not Equal Immediate Delivery Commitment

本 ADR 仅冻结演进边界与约束。

是否实施、何时实施、拆成哪些 EPIC/FEAT，必须以后续基于 SRC 的正式链路为准。

## 4. Reserved Architecture Direction

### 4.1 Dual-Layer Model

预留以下分层：

- 轻量层：负责感知、巡检、触发判断、计划解释
- 重量层：负责 workflow 编排、执行、状态管理、人工介入、产物治理

轻量层的职责是“是否要做、建议怎么做”。
重量层的职责是“真正执行并留下可治理证据”。

### 4.2 Skill Registry And Policy Filter

未来 Skill 不应只被视为某种 Executor 的别名，而应逐步收敛为：

- 声明式能力单元
- 可按角色/场景/模式过滤
- 可按需装配
- 可被 workflow / planner / agent 共享引用

但本 ADR 不要求现在就实现完整 Skill Engine。

### 4.3 Rules First, Goals Second

未来若引入自主模式，应优先支持规则触发：

- 定时巡检
- verifier 失败
- artifact 缺失
- spec / repo 状态变化

在规则触发可控后，再考虑目标驱动规划，避免直接把开放式目标规划作为第一落点。

### 4.4 Explain-Before-Execute

未来如提供主动执行或高层 Agent 入口，应优先支持预演能力：

- 本次会命中哪个 workflow
- 会装配哪些 skill / executor
- 预期输入、产物和 gate 是什么
- 为什么建议执行或不执行

这类能力优先级高于“更像人聊天”的交互包装。

## 5. Explicit Non-Decisions

本 ADR 当前不决定：

- 未来是否命名为“数字人”
- 是否引入 Web UI、IM 通知、多渠道委派
- 具体使用多少 Agent 角色
- Skill 元数据 schema 的最终结构
- 触发器、planner、memory 的具体持久化模型

这些都属于后续 EPIC/FEAT/TECH 的问题。

## 6. Existing Anchors

当前仓库中可作为未来演进锚点的现有基础包括：

- `README.md` 中的 orchestrator / verifier / workflow 定位
- `docs/architecture/ARCHITECTURE-MIGRATION-GUIDE.md` 中已提出的 PM Agent 与 Skill 方向
- `docs/architecture/LEE_Orchestrator_v3_Architecture.md` 中已固化的 runtime core 与外圈能力分层
- `spec/adr/ADR-001__ssot-delivery-chain-hard-governance.md` 的 SSOT 治理链约束
- `spec/adr/ADR-003__product-department-ssot-design.md` 与 `spec/adr/ADR-006__cli-minglingfencyussot-wuhuabianjie.md` 的 SRC/ADR 边界

未来设计必须先兼容这些锚点，再扩展主动能力。

## 7. Consequences

采纳本 ADR 后，后续相关讨论应遵循以下叙事：

- “主动智能体”是现有 LEE 的演进方向，不是替代物
- 任何提案都应先说明如何接入现有 workflow/orchestrator/gate/SSOT 边界
- 若要新增 Agent、Skill、Trigger、Planner，应先判断其是否只是现有能力的重命名
- 优先补齐架构说明、预演能力和治理接口，再考虑外部交互包装

## 8. Follow-Up

建议后续只在需要进入正式实施时，再继续派生：

- `EPIC`: 主动触发与计划解释能力
- `EPIC`: Skill 注册与过滤模型
- `FEAT`: workflow dry-run / explain-plan
- `FEAT`: verifier / artifact / repo 事件触发器

在此之前，本 ADR 只作为未来方向约束，不作为当前版本待交付事项。
