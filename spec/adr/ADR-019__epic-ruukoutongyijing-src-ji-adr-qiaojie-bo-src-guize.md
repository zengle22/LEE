---
id: ADR-019
ssot_type: adr
title: EPIC 入口统一经 SRC 及 ADR 桥接薄 SRC 规则
status: draft
version: v1
workflow_instance_id: epic-entry-governance-20260315
parent_id: null
derived_from_ids:
  - id: ADR-001
    version: v1
  - id: ADR-003
    version: v1
  - id: ADR-012
    version: v1
source_refs: []
owner: governance
tags:
  - governance
  - product
  - src
  - epic
  - adr
  - traceability
properties:
  adr_kind: governance_design
  decision_scope: epic_entry_via_src_and_adr_bridge_rule
---

# EPIC 入口统一经 SRC 及 ADR 桥接薄 SRC 规则

## 1. Decision

LEE 对 `EPIC` 的入口边界补充冻结以下规则：

- 所有正式 `EPIC` 都必须经由至少一个冻结后的 `SRC` 进入主链。
- `ADR` 仍是决策型 SSOT，不直接充当 `EPIC` 的业务 source object。
- 当某个 `ADR` 需要推动下游进入 `EPIC -> FEAT -> UI / TECH / TASK` 主链时，必须先桥接生成一份薄 `SRC`，再由该 `SRC` 进入 `src_to_epic`。
- 不是每个 `ADR` 都必须生成 `SRC`；只有会形成业务/交付对象链变更的 `ADR` 才需要桥接 `SRC`。
- 该桥接 `SRC` 的正式定位是“主链入口对象”，不是“用 `SRC` 替代 `ADR`”。

本 ADR 采纳以下 canonical 关系：

`ADR governs -> bridge SRC enters -> EPIC derives`

不采纳以下表达：

- `ADR directly derives EPIC`
- `ADR replaces SRC`
- `every ADR must generate EPIC`
- `every ADR must generate SRC`

## 2. Context

`ADR-003` 已冻结产品主链：

`raw input -> SRC -> EPIC -> FEAT -> UI / TECH / TASK`

同时，`ADR-003` 也已明确：

- `ADR` 是决策与治理对象链
- `ADR` 不进入业务主链
- `ADR` 不应充当业务 source object

`ADR-012` 进一步将产品前半链分为：

- `raw_to_src`
- `src_to_epic`

并将 `SRC` 冻结为 `EPIC` 之前的正式关口。

但在实际治理讨论中，会反复出现以下场景：

- 某个 `ADR` 决定了新的 workflow / contract / bridge 方向
- 该决定会真实触发后续 `EPIC/FEAT` 设计和实施
- 团队又坚持所有 `EPIC` 必须统一从 `SRC` 进入

如果没有补充规则，团队容易在两种错误做法之间摇摆：

- 要么让 `ADR` 直接充当 `EPIC` 的 source object
- 要么要求所有 `ADR` 无差别地产生业务链对象

这两种做法都不理想。

## 3. Problem

### 3.1 Direct ADR -> EPIC Conflicts With Existing SSOT Design

如果允许 `ADR` 直接成为 `EPIC` 的上游 source：

- 会与 `ADR-003` 中“`ADR` 不进入业务主链”的冻结结论冲突
- 会让 `EPIC` 的业务来源与治理来源混在一起
- 会弱化 `SRC` 作为正式主链入口的地位

### 3.2 Every ADR -> SRC Causes Governance Pollution

如果反过来规定“每个 `ADR` 都必须产生 `SRC`”：

- 纯治理、纯说明、纯约束型 `ADR` 会平白污染业务链
- `SRC` 会混入大量并不需要下游业务拆解的对象
- `EPIC`、`FEAT` 注册表会被非必要对象稀释

### 3.3 Missing Bridge Pattern

当前更缺的不是“让 `ADR` 成为业务真源”，而是缺一条正式桥接规则：

- 哪些 `ADR` 需要桥接 `SRC`
- 桥接 `SRC` 的语义边界是什么
- `EPIC` 应如何同时保留 `SRC` 溯源和 `ADR` 治理引用

## 4. Boundary Rule

### 4.1 Source Rule

`EPIC` 的正式入口必须是冻结后的 `SRC`。

最小语义要求：

- `EPIC` 必须能追溯到至少一个冻结 `SRC`
- 若没有 `SRC`，则不得把该对象视为正式 `EPIC`
- `src_to_epic` 不得以裸 `ADR` 直接作为 truth source

### 4.2 ADR Rule

`ADR` 的正式职责仍然是：

- `governs`
- `constrains`
- `explains`

`ADR` 可以约束：

- workflow
- contract
- agent
- skill
- TECH
- TASK
- TESTSET
- 某个由其触发的 `EPIC/FEAT`

但 `ADR` 不直接取代 `SRC` 的职责。

### 4.3 Bridge Rule

当某个 `ADR` 满足以下条件之一时，应先桥接生成一份薄 `SRC`：

- 将触发新的 `EPIC/FEAT` 范围设计
- 将触发新的下游实施计划或交付对象
- 将形成需要业务验收、实施验收或回归验证的新增对象链

当 `ADR` 仅用于以下场景时，不要求生成 `SRC`：

- 纯治理说明
- 纯 review / approval / gate 策略调整
- 不形成新 `EPIC/FEAT` 的局部约束修订
- 仅作为现有对象的 governing ADR，被动提供约束

## 5. Bridge SRC Definition

### 5.1 Position

桥接 `SRC` 是从治理决策进入业务主链时的正式入口对象。

它的作用是：

- 把“决策已成立”翻译成“主链需要处理的需求/范围入口”
- 保留 `ADR -> SRC -> EPIC` 的稳定追溯关系
- 保证 `EPIC` 仍然只从 `SRC` 进入，而不是从 `ADR` 直接跳入

### 5.2 Naming

本 ADR 暂采用语义名称：

- `bridge SRC`
- `thin SRC`
- `ADR-derived SRC`

其中 canonical 含义是同一件事：由 `ADR` 触发、但作为主链入口存在的轻量 `SRC`。

具体 schema 字段名是否采用：

- `source_kind: governance_bridge_src`
- `source_kind: adr_derived_src`

留待后续 contract 变更冻结。

### 5.3 Minimum Semantic Content

桥接 `SRC` 至少应表达以下语义：

- 它所桥接的上游 `ADR` 是谁
- 该 `ADR` 触发的主链变化范围是什么
- 哪些下游对象预计会被创建或调整
- 哪些验收或交付边界将受到影响
- 哪些内容明确不在本次桥接范围内

桥接 `SRC` 不要求重复书写完整 `ADR` 正文，也不应伪装成普通用户原始需求。

## 6. EPIC Derivation Rule

从本 ADR 起，推荐以下 `EPIC` 关系语义：

- `derived_from_ids` 至少包含一个 `SRC`
- `source_refs` 指向对应 `SRC` 或其片段
- 若存在上游治理决策，则以 `governing_adrs`、`decision_refs` 或等价关系保留 `ADR`

不推荐：

- `EPIC` 只引用 `ADR`，不引用 `SRC`
- `EPIC.parent = ADR`
- 用自由文本在 `EPIC` 正文里口头说明“其实它来自某个 ADR”，但 machine-readable 关系缺失

## 7. Examples

### 7.1 Should Create Bridge SRC

`ADR` 冻结“统一建立 raw_to_src 独立 workflow 入口，并调整产品主编排相位顺序”。

若该决定要进一步进入：

- 新增产品 workflow `EPIC`
- 新增 contract / runtime / migration `FEAT`

则应先生成一份桥接 `SRC`，再由该 `SRC` 进入 `EPIC` 设计。

### 7.2 Should Not Create Bridge SRC

`ADR` 仅补充：

- gate 的 `decision_mode`
- 审批 CLI 展示上下文要求
- 某类 review finding 的治理分级

若不形成新的业务/交付对象链，仅作为治理约束存在，则不必生成 `SRC`。

## 8. Governance Impact

本 ADR 冻结的是对象边界和派生规则，不直接冻结字段名与脚本实现。

后续派生工作至少可能包括：

- 在 `SRC` contract 中增加 source kind 或等价分类语义
- 在 `EPIC` contract / validator 中增加“必须引用 `SRC`”校验
- 在 workflow 中增加 `ADR -> bridge SRC` 的显式入口或适配逻辑
- 为 bridge SRC 补充示例、review checklist 和 replay 基线

在这些 follow-up 落地前，本 ADR 先作为治理边界约束生效。

## 9. Compatibility

若仓库内存在历史 `EPIC`：

- 只记录 `ADR`
- 未显式记录 `SRC`

则应视为历史兼容态，而不是推荐继续沿用的 canonical 模式。

新产生的正式 `EPIC` 不应再复制该模式。

## 10. Out Of Scope

本 ADR 不直接冻结：

- bridge SRC 的最终 schema 字段名
- 是否需要单独 `raw_to_src` 子模式来处理 `ADR` 输入
- 历史 `EPIC` 的一次性回补迁移策略
- `FEAT`、`TECH`、`TASK` 的具体字段补充

这些内容应由后续 contract / workflow / validator 变更承接。

## 11. Follow-Up

建议后续派生以下工作：

1. 新增 SRC 分类语义及示例
2. 为 `EPIC` 增加“至少有一个 `SRC` 上游”的硬校验
3. 设计 `ADR -> bridge SRC` 的 workflow 或适配入口
4. 为 bridge SRC 补充 review checklist
5. 盘点现有只挂 `ADR` 的历史 `EPIC`，决定是否迁移
