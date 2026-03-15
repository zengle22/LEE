---
id: TECH-FEAT-SRC-009-011-001
ssot_type: tech
title: 共享输入规范落地 - Frozen技术架构
status: active
version: v1
parent_id: FEAT-SRC-009-011
derived_from_ids:
- FEAT-SRC-009-011
- ADR-008
source_refs:
- FEAT-SRC-009-011
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
workflow_instance_id: wf-tech-feat-src-009-011-001__gongxiangshuruguifanluodi-frozenjizhujiagou-20260316
---

# Summary

共享输入规范技术架构

## Goal Alignment

- 上游 FEAT：`FEAT-SRC-009-011`
- 目标：统一所有 Dev workflow 的输入规范，确保跨工作流的一致性和可集成性
- 用户价值：所有 Dev workflow 统一遵守输入规范，确保跨工作流的一致性和可集成性，降低上下文切换成本
- 决策基线：`ADR-008`

## Tech Stack

| Layer | Technology | Reasoning |
| --- | --- | --- |
| `schema` | Shared Input Contract Schema | 统一 formal_ssot_id/source_refs/governing_adrs/repo_context 等共享字段。 |
| `resolution` | Input Resolution Layer | 统一 workflow 输入解析与 hydration 规则。 |
| `validation` | Contract Validation Chain | 在运行前校验必填字段、引用类型和状态。 |
| `reuse` | Cross-workflow Reuse Policy | 供 feature / bugfix / l3 阶段统一复用。 |

## Core Components

### SharedInputSchema
- 职责：定义共享输入字段和类型。
- 依赖：SchemaRegistry

### ContextResolver
- 职责：把 FEAT/BUG/ADR/repo_context 解析到运行时。
- 依赖：AgentContextBuilder

### InputValidator
- 职责：在 step 启动前阻断缺失或错误输入。
- 依赖：RuntimeChecks

## Input To Delivery Mapping

### FEAT Processing Projection
- 定义 formal_ssot_id 规范（格式、校验规则）
- 定义 source_refs 规范（引用格式、必填性）
- 定义 governing_adrs 规范（ADR 引用格式、影响范围声明）
- 定义 repo_context 规范（代码库路径、分支规则）
- 创建输入验证 checklist

### Expected Deliverables
- 共享输入规范文档
- formal_ssot_id 规范定义
- source_refs 规范定义
- governing_adrs 规范定义
- repo_context 规范定义
- 输入验证 checklist

### Acceptance Alignment
- 共享输入规范文档已冻结
- formal_ssot_id 规范包含格式和校验规则
- source_refs 规范包含引用格式和必填性
- governing_adrs 规范包含 ADR 引用格式和影响范围声明
- repo_context 规范包含代码库路径和分支规则
- 输入验证 checklist 可用
- 不实现验证工具

## Implementation Constraints

- 所有实现必须以 `FEAT-SRC-009-011` 为上游事实源。
- 新增逻辑不得回流到 deprecated 或 broken 路径。
- 输出必须可被下游 TASK、Integration 或 Evidence Pack 审计。
- TECH 只定义技术结构、依赖、风险和交付边界，不替代实现代码。

## Risks And Fallback

- `R-001` 不同 workflow 字段同名异义
  处理：共享 schema 做唯一权威定义。
- `R-002` 输入 hydration 漏字段导致漂移
  处理：把 required_fields 和 resolution trace 写入 runtime。

## Review Checklist

- 技术选型是否支撑 FEAT 目标而非引入新的平级入口。
- 输入契约和输出边界是否可被下游 workflow 直接消费。
- 风险、fallback 和删除条件是否清晰且可执行。
- 是否保留对 `FEAT-SRC-009-011` 和 `ADR-008` 的可追溯引用。

## Out Of Scope

- 实现输入验证工具
- 修改 workflow 引擎
- 强制历史任务合规

## Metadata

- TECH ID：`TECH-FEAT-SRC-009-011-001`
- Parent FEAT：`FEAT-SRC-009-011`
- Source Refs：`FEAT-SRC-009-011`, `EPIC-SRC-009#scope`, `ADR-008`
- Materialized By：`batch-tech-src-009-20260312`
