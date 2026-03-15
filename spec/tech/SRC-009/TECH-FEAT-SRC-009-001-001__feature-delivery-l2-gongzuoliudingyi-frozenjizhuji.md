---
id: TECH-FEAT-SRC-009-001-001
ssot_type: tech
title: Feature Delivery L2 工作流定义 - Frozen技术架构
status: active
version: v1
parent_id: FEAT-SRC-009-001
derived_from_ids:
- FEAT-SRC-009-001
- ADR-008
source_refs:
- FEAT-SRC-009-001
- EPIC-SRC-009#scope
- ADR-008
owner: dev-architecture-owner
tags:
- tech
- ssot
- dev
- adr-008
properties:
  contract_key: tech_spec
  identity_kind: ssot
  materialized_from: batch-tech-src-009-20260312
workflow_instance_id: wf-tech-feat-src-009-001-001__feature-delivery-l2-gongzuoliudingyi-frozenjizhuji-20260316
---

# Summary

Feature Delivery L2 主链技术架构

## Goal Alignment

- 上游 FEAT：`FEAT-SRC-009-001`
- 目标：定义 Dev 部门从 FEAT 到 Evidence Pack 的完整 Feature 交付主链，建立统一的 L2 编排层入口
- 用户价值：Dev 部门获得从 FEAT 到 Evidence Pack 的完整 Feature 交付主链，实现需求轴到交付轴的正式收口，团队可通过统一的 L2 入口执行特性开发任务
- 决策基线：`ADR-008`

## Tech Stack

| Layer | Technology | Reasoning |
| --- | --- | --- |
| `workflow_definition` | Checked-in YAML Workflow Template | 用 checked-in 模板定义 L2 主链，确保阶段顺序、输入输出和 gate 约束可审计。 |
| `orchestration_runtime` | Declarative Orchestrator Runtime | 复用现有 workflow runtime 执行阶段编排、状态推进和 symbol 解析。 |
| `state_model` | Finite State Machine | 以 Ready / In Progress / Evidence Pack Produced / Closed 管理生命周期。 |
| `contract_binding` | SSOT + Contract Schema | formal_ssot_id/source_refs/governing_adrs/repo_context/repo_frontend/repo_backend 进入统一契约校验链。 |

## Core Components

### FeatureDeliveryTemplate
- 职责：定义 tech_design -> contract_design -> backend_dev / frontend_dev 并行 -> integration -> evidence_pack -> smoke_gate 主链。
- 依赖：WorkflowRuntime, ContractSchemaValidator

### DeliveryStateMachine
- 职责：管理 L2 状态流转与异常回滚边界。
- 依赖：RunStateStore

### EvidenceBoundaryBinder
- 职责：把主链输出统一交给 Evidence Pack。
- 依赖：ArtifactRegistry, EvidencePackContract

## Input To Delivery Mapping

### FEAT Processing Projection
- 校验输入完整性（formal_ssot_id, source_refs, governing_adrs, repo_context, repo_frontend, repo_backend）
- 定义 L3 阶段编排顺序（Contract → Backend / Frontend 并行 → Integration → Evidence Pack）
- 定义状态机（Ready → In Progress → Evidence Pack Produced → Closed）
- 设计与上游 FEAT 的契约接口
- 设计与下游 Evidence Pack 的契约接口
- 定义输出物列表规范

### Expected Deliverables
- L2 工作流定义文档（冻结状态）
- 输入规范文档
- L3 阶段编排顺序定义
- 状态机定义文档
- 契约接口定义
- TECH 设计文档模板引用

### Acceptance Alignment
- L2 工作流定义文档已冻结并通过评审
- 输入规范包含 formal_ssot_id, source_refs, governing_adrs, repo_context, repo_frontend, repo_backend 六个字段定义
- L3 阶段编排顺序明确定义为 Contract → Backend / Frontend 并行 → Integration → Evidence Pack
- 状态机包含 Ready → In Progress → Evidence Pack Produced → Closed 四个状态
- 与上游 FEAT 的契约接口文档化
- 与下游 Evidence Pack 的契约接口文档化
- 不包含 L3 阶段具体实现逻辑

## Implementation Constraints

- 所有实现必须以 `FEAT-SRC-009-001` 为上游事实源。
- 新增逻辑不得回流到 deprecated 或 broken 路径。
- 输出必须可被下游 TASK、Integration 或 Evidence Pack 审计。
- TECH 只定义技术结构、依赖、风险和交付边界，不替代实现代码。

## Risks And Fallback

- `R-001` L2 与既有旧入口并存，造成 AI 回流
  处理：在模板层显式声明 canonical 入口，并用 lint/CI 阻断旧路径继续增长。
- `R-002` 状态机定义与真实实现脱节
  处理：把状态转换条件写入模板和 gate 校验，而不是只停留在 ADR。

## Review Checklist

- 技术选型是否支撑 FEAT 目标而非引入新的平级入口。
- 输入契约和输出边界是否可被下游 workflow 直接消费。
- 风险、fallback 和删除条件是否清晰且可执行。
- 是否保留对 `FEAT-SRC-009-001` 和 `ADR-008` 的可追溯引用。

## Out Of Scope

- 实现 L3 阶段的具体逻辑
- 修改 FEAT 产生机制
- 实现具体技术代码生成

## Metadata

- TECH ID：`TECH-FEAT-SRC-009-001-001`
- Parent FEAT：`FEAT-SRC-009-001`
- Source Refs：`FEAT-SRC-009-001`, `EPIC-SRC-009#scope`, `ADR-008`
- Materialized By：`batch-tech-src-009-20260312`
