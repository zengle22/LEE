---
id: TECH-FEAT-SRC-009-002-001
ssot_type: tech
title: Bugfix Delivery L2 工作流定义 - Frozen技术架构
status: active
version: v1
parent_id: FEAT-SRC-009-002
derived_from_ids:
- FEAT-SRC-009-002
- ADR-008
source_refs:
- FEAT-SRC-009-002
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
---

# Summary

Bugfix Delivery L2 主链技术架构

## Goal Alignment

- 上游 FEAT：`FEAT-SRC-009-002`
- 目标：定义 Dev 部门从 BUG 到 Evidence Pack 的完整 Bugfix 交付主链，建立 Bug 修复的标准化流程
- 用户价值：Dev 部门获得从 BUG 到 Evidence Pack 的完整 Bugfix 交付主链，实现 Bug 修复流程的标准化和可追溯，团队可通过统一的 L2 入口执行 Bug 修复任务
- 决策基线：`ADR-008`

## Tech Stack

| Layer | Technology | Reasoning |
| --- | --- | --- |
| `bug_intake` | BUG SSOT Intake | 以 bug_ssot_id、severity、reproduction_evidence 作为唯一事实输入。 |
| `workflow_definition` | Checked-in YAML Workflow Template | 定义 triage -> root_cause -> fix_design -> fix_implementation -> verification -> evidence_pack 主链。 |
| `policy_control` | Granularity Policy Engine | 默认单 bug，满足同根因/同模块/同发布窗口时才允许 batch。 |
| `evidence_trace` | Evidence Pack Traceability | 把修复、验证、回归证据收口到 bugfix evidence。 |

## Core Components

### BugfixDeliveryTemplate
- 职责：编排标准 bugfix 流程并挂接 batch_mode 判断。
- 依赖：GranularityPolicyEvaluator

### BugEvidenceResolver
- 职责：解析复现证据并映射验证范围。
- 依赖：BugRegistry

### VerificationRouter
- 职责：把修复结果送入验证和回归检查。
- 依赖：TestCaseRefs, EvidencePackAggregator

## Input To Delivery Mapping

### FEAT Processing Projection
- 校验输入完整性（bug_ssot_id, severity, reproduction_evidence）
- 定义 L3 阶段编排顺序（Triage → Fix → Verification → Evidence Pack）
- 定义 Bugfix 状态机
- 集成 Bugfix 粒度控制规则
- 设计与上游 BUG 源的契约接口
- 设计与下游 Evidence Pack 的契约接口

### Expected Deliverables
- Bugfix Delivery L2 工作流定义文档（冻结状态）
- Bugfix 输入规范文档
- Bugfix L3 阶段编排顺序定义
- Bugfix 状态机定义
- 粒度控制规则集成规范
- 契约接口定义文档

### Acceptance Alignment
- Bugfix Delivery L2 工作流定义文档已冻结并通过评审
- 输入规范包含 bug_ssot_id, severity, reproduction_evidence 字段定义
- L3 阶段编排顺序明确定义为 Triage → Fix → Verification → Evidence Pack
- 状态机定义完整
- Bugfix 粒度控制规则已集成
- 与上游 BUG 源的契约接口文档化
- 与下游 Evidence Pack 的契约接口文档化
- 不包含 L3 阶段具体实现逻辑

## Implementation Constraints

- 所有实现必须以 `FEAT-SRC-009-002` 为上游事实源。
- 新增逻辑不得回流到 deprecated 或 broken 路径。
- 输出必须可被下游 TASK、Integration 或 Evidence Pack 审计。
- TECH 只定义技术结构、依赖、风险和交付边界，不替代实现代码。

## Risks And Fallback

- `R-001` 多 bug 混装导致根因和证据失真
  处理：默认单 bug；batch 只在规则满足时开放。
- `R-002` BUG 复现证据质量不足
  处理：把 reproduction_evidence 作为硬输入契约字段，不满足时直接拒绝进入 L2。

## Review Checklist

- 技术选型是否支撑 FEAT 目标而非引入新的平级入口。
- 输入契约和输出边界是否可被下游 workflow 直接消费。
- 风险、fallback 和删除条件是否清晰且可执行。
- 是否保留对 `FEAT-SRC-009-002` 和 `ADR-008` 的可追溯引用。

## Out Of Scope

- 实现 L3 阶段的具体逻辑
- 修改 BUG 产生机制
- 实现具体修复代码

## Metadata

- TECH ID：`TECH-FEAT-SRC-009-002-001`
- Parent FEAT：`FEAT-SRC-009-002`
- Source Refs：`FEAT-SRC-009-002`, `EPIC-SRC-009#scope`, `ADR-008`
- Materialized By：`batch-tech-src-009-20260312`
