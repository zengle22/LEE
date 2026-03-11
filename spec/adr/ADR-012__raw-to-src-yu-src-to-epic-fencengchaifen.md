---
id: ADR-012
ssot_type: adr
title: raw-to-src 与 src-to-epic 分层拆分
status: draft
version: v1
parent_id: null
derived_from_ids:
  - id: ADR-001
    version: v1
  - id: ADR-003
    version: v1
  - id: ADR-011
    version: v1
source_refs: []
owner: governance
tags:
  - governance
  - product
  - workflow
  - ssot
  - src
  - epic
properties:
  adr_kind: workflow_design
  decision_scope: product_requirement_chain_layer_split
---

# raw-to-src 与 src-to-epic 分层拆分

## 1. Decision

LEE 采纳将当前产品主链中的 `raw -> SRC -> EPIC` 拆分为两个独立 L3 workflow 的方向。

本 ADR 冻结以下决定：

- 新增独立 L3：`workflow.product.task.raw_to_src`
- 收窄现有 L3：`workflow.product.task.src_to_epic` 只接受冻结后的 `SRC`
- 产品 L2 主编排改为：`raw_to_src -> src_to_epic -> epic_to_feat -> feat_to_delivery_prep`
- `SRC` 被确认为正式独立冻结关口和复用入口，不再只是 `src_to_epic` 内部中间态

命名上，本 ADR 采用 `raw_to_src` 作为 canonical workflow id。

- `input_to_src` 可以作为讨论期别名
- 正式 registry、workflow 引用、文档示例统一使用 `raw_to_src`

## 2. Context

当前产品链已经在 `ADR-003` 中冻结为：

`raw input -> SRC -> EPIC -> FEAT -> UI / TECH / TASK`

但仓库中的现役 L3 模板 `spec-global/departments/product/workflows/templates/src-to-epic/v1/workflow.yaml` 仍同时承担两类职责：

- 任意输入 `-> SRC`
- `SRC -> EPIC`

这使得 `src_to_epic` 实际上既负责源归一化与冻结，也负责需求建模与主题抽象。

与此同时，L2 主编排 `spec-global/departments/product/workflows/templates/product-main-pipeline/v1/workflow.yaml` 仍按三段组织：

- `src_to_epic`
- `epic_to_feat`
- `feat_to_delivery_prep`

这与当前主链中 `SRC` 作为正式对象的语义地位并不完全对齐。

## 3. Problem

将 `raw -> SRC` 与 `SRC -> EPIC` 合并在同一个 L3 中，短期上减少了模板数量，但长期会带来三类问题。

### 3.1 Name / Responsibility Drift

workflow 名称与真实职责不一致。

调用方看到 `src_to_epic`，无法直接判断：

- 它是否能接原始输入
- 它是否也负责产出正式 `SRC`
- 当目标只是获得规范化 `SRC` 时是否应该调用它

### 3.2 Missing Independent Entry For SRC

`SRC` 作为正式 SSOT 对象缺少独立 workflow 入口，不利于：

- 复用
- 单独重跑
- 分层单测
- 治理审查
- registry 和调用文档的稳定表达

### 3.3 Semantic Leakage

任何只想完成 `raw -> SRC` 的场景，都会被迫顺带耦合 `EPIC` 语义。

这会让以下场景变得笨重：

- 只做来源归一化与冻结
- 上游部门先产出 `SRC`，下游稍后再做 `EPIC`
- 针对 `SRC` 层单独做 replay stability 与一致性测试

## 4. Layering Principle

本 ADR 采用以下分层原则：

> 源归一化与冻结，不应与需求建模和主题抽象处于同一 workflow 责任层。

其中：

- `raw -> SRC` 解决的是“源归一化和冻结”问题
- `SRC -> EPIC` 解决的是“需求建模和主题抽象”问题

两者虽然在主链上前后相接，但不是同一语义层级的问题，因此不应继续塞在同一个 L3 中。

## 5. Target Structure

### 5.1 Canonical Chain

该 ADR 不改变 `ADR-003` 已冻结的对象链，只改变 workflow 分层表达。

正式主链仍为：

`raw input -> SRC -> EPIC -> FEAT -> UI / TECH / TASK`

### 5.2 Canonical Workflow Mapping

产品部门的分层映射应调整为：

- `workflow.product.task.raw_to_src`
- `workflow.product.task.src_to_epic`
- `workflow.product.task.epic_to_feat`
- `workflow.product.task.feat_to_delivery_prep`

其中 L2 主编排的 phase 顺序应同步调整为：

- `raw_to_src`
- `src_to_epic`
- `epic_to_feat`
- `feat_to_delivery_prep`

## 6. Boundary Definition

### 6.1 raw_to_src

`raw_to_src` 的职责仅包括：

- 接收任意原始输入
- 保存来源与引用关系
- 归一化为 `SRC candidate`
- 评审并冻结正式 `SRC`

`raw_to_src` 不负责：

- 生成 `EPIC`
- 引入 `EPIC` 级问题空间抽象
- 在同一模板中继续推进下游主题设计

### 6.2 src_to_epic

`src_to_epic` 的职责仅包括：

- 读取冻结后的 `SRC`
- 将 `SRC` 翻译为问题空间
- 生成、评审并冻结 `EPIC`

`src_to_epic` 必须遵守以下约束：

- 输入应为冻结 `SRC` 或其正式引用视图
- 不得再以原始输入作为直接 truth source
- 不得在本 workflow 内重新定义或重写 `SRC`

### 6.3 Freeze Rule

`SRC` 是进入 `EPIC` 设计前的正式冻结边界。

这意味着：

- `EPIC` 只能引用已冻结的 `SRC` 版本
- 如果原始输入变动，需要先重开 `raw_to_src`
- `src_to_epic` 的重跑稳定性应建立在相同 `SRC` 输入上，而不是相同 raw input 上

## 7. Governance Impact

该拆分不是简单“在现有 L3 中新增一个 stage 名称”，而是 workflow 入口和对象边界的正式重构。

因此后续派生变更至少应覆盖：

- workflow registry
- L2 / L3 workflow template 引用关系
- run spec 或 CLI 入口文档
- 调用示例与迁移说明
- `raw->src` 与 `src->epic` 的分层测试与 replay stability 基线

若存在兼容期：

- 旧的“向 `src_to_epic` 直接喂 raw input”只能作为显式兼容适配
- 该兼容路径必须标记为过渡态，而不能继续作为 canonical 入口

## 8. Why This Split Is Worth It

采纳该 ADR 后，将获得以下直接收益：

- `SRC` 成为真正独立的冻结关口
- “先把任意源转成规范 `SRC`”拥有单独明确入口
- 一致性测试可以按 `raw->src` 与 `src->epic` 分层设计
- replay stability 可以将“源归一化波动”和“主题抽象波动”分开观察
- workflow 名称、输入输出和真实职责重新对齐

代价同样需要被正视：

- 多一个 handoff
- 多一个 freeze 边界
- 模板引用、运行文档和测试资产需要同步迁移

本 ADR 的判断是：上述代价值得付出，因为对象边界和治理可观测性会清楚很多。

## 9. Relationship To ADR-011

`ADR-011` 已将需求链视为正式被测对象，并要求建立：

- 结构一致性测试
- 语义映射一致性测试
- replay stability 测试
- 下游可用性测试

本 ADR 进一步提供测试分层前提：

- `raw_to_src` 负责源归一化稳定性
- `src_to_epic` 负责主题抽象稳定性

因此，`ADR-011` 的一致性测试在产品链上不应只保留整链测试，也应允许：

- `raw -> SRC` 单独测试
- `SRC -> EPIC` 单独测试
- `raw -> SRC -> EPIC` 端到端联测

## 10. Out Of Scope

本 ADR 不直接冻结以下内容：

- `SRC` 或 `EPIC` schema 字段细节是否改动
- `epic_to_feat` 与 `feat_to_delivery_prep` 的对象语义调整
- 运行时实例数据结构的具体字段命名
- 兼容期持续多久的实施细节

这些内容需要由后续 workflow / contract / runtime 变更单独承接。

## 11. Follow-Up

本 ADR 之后建议派生以下正式工作：

1. 新增 `raw-to-src` L3 workflow template
2. 将现有 `src-to-epic` 缩减为只处理冻结 `SRC -> EPIC`
3. 更新 `product-main-pipeline` 为四段主链
4. 更新 workflow registry、运行文档和调用示例
5. 为 `raw->src`、`src->epic`、端到端链路补齐一致性测试与 replay stability 基线

在这些下游变更落地前，本 ADR 作为治理方向与对象边界约束，不直接替代实现 spec。
