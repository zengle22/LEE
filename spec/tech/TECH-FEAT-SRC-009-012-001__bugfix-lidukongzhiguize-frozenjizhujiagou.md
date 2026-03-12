---
id: TECH-FEAT-SRC-009-012-001
ssot_type: tech
title: Bugfix 粒度控制规则 - Frozen技术架构
status: active
version: v1
parent_id: FEAT-SRC-009-012
derived_from_ids:
- FEAT-SRC-009-012
- ADR-008
source_refs:
- FEAT-SRC-009-012
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

Bugfix 粒度控制技术架构

## Goal Alignment

- 上游 FEAT：`FEAT-SRC-009-012`
- 目标：定义 Bugfix 的粒度控制标准，确保默认单 bug 单 workflow instance，同时为合理的 batch 场景提供审批机制
- 用户价值：明确 Bugfix 的粒度控制标准，确保默认单 bug 单 workflow instance，同时为合理的 batch 场景提供审批机制
- 决策基线：`ADR-008`

## Tech Stack

| Layer | Technology | Reasoning |
| --- | --- | --- |
| `policy` | Granularity Policy Schema | 定义单 bug 默认、batch 例外的规则模型。 |
| `evaluation` | Batch Eligibility Evaluation | 基于模块、根因、验证面、发布窗口判断能否 batch。 |
| `approval` | Exception Approval Gate | 对例外 batch 场景增加审批。 |
| `traceability` | Bug-to-Workflow Trace | 记录每个 BUG 与 workflow instance 的映射。 |

## Core Components

### GranularityPolicyEvaluator
- 职责：执行默认单 bug 与 batch 例外判断。
- 依赖：BugRefs, RootCauseRefs

### BatchApprovalGate
- 职责：对 batch_mode 请求进行人工/规则审批。
- 依赖：Severity, ReleaseWindow

### BugTraceBinder
- 职责：绑定 bug_refs、verification 和 evidence。
- 依赖：ArtifactRegistry

## Input To Delivery Mapping

### FEAT Processing Projection
- 定义默认规则（1 bug → 1 bugfix workflow instance）
- 定义五同原则（同模块、同根因、同修复方案、同测试范围、同风险等级）
- 设计 batch 例外审批流程
- 创建粒度合规检查 checklist
- 定义合规率统计方法

### Expected Deliverables
- Bugfix 粒度控制规则文档
- 默认规则定义
- 五同原则定义
- Batch 例外审批流程
- 粒度合规检查 checklist
- 合规率统计方法

### Acceptance Alignment
- Bugfix 粒度控制规则文档已冻结
- 默认规则明确为 1 bug → 1 bugfix workflow instance
- 五同原则完整定义（同模块、同根因、同修复方案、同测试范围、同风险等级）
- Batch 例外审批流程清晰可执行
- 粒度合规检查 checklist 可用
- 合规率统计方法定义
- 不实现自动化检查工具

## Implementation Constraints

- 所有实现必须以 `FEAT-SRC-009-012` 为上游事实源。
- 新增逻辑不得回流到 deprecated 或 broken 路径。
- 输出必须可被下游 TASK、Integration 或 Evidence Pack 审计。
- TECH 只定义技术结构、依赖、风险和交付边界，不替代实现代码。

## Risks And Fallback

- `R-001` 不同根因 BUG 被错误批处理
  处理：把五同原则前置为 batch 入口硬约束。
- `R-002` 粒度控制只停留在文档层
  处理：把 batch eligibility 评估做成显式输入和 gate。

## Review Checklist

- 技术选型是否支撑 FEAT 目标而非引入新的平级入口。
- 输入契约和输出边界是否可被下游 workflow 直接消费。
- 风险、fallback 和删除条件是否清晰且可执行。
- 是否保留对 `FEAT-SRC-009-012` 和 `ADR-008` 的可追溯引用。

## Out Of Scope

- 实现自动化粒度检查
- 修改 BUG 报告机制
- 强制拆分历史 batch

## Metadata

- TECH ID：`TECH-FEAT-SRC-009-012-001`
- Parent FEAT：`FEAT-SRC-009-012`
- Source Refs：`FEAT-SRC-009-012`, `EPIC-SRC-009#scope`, `ADR-008`
- Materialized By：`batch-tech-src-009-20260312`
