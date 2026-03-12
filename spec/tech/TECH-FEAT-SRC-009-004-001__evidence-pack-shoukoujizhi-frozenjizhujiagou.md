---
id: TECH-FEAT-SRC-009-004-001
ssot_type: tech
title: Evidence Pack 收口机制 - Frozen技术架构
status: active
version: v1
parent_id: FEAT-SRC-009-004
derived_from_ids:
- FEAT-SRC-009-004
- ADR-008
source_refs:
- FEAT-SRC-009-004
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

Evidence Pack 收口技术架构

## Goal Alignment

- 上游 FEAT：`FEAT-SRC-009-004`
- 目标：设计 Evidence Pack 作为证据轴正式收口对象，确保所有交付可审计、可追踪
- 用户价值：作为证据轴正式收口对象，确保所有交付可审计、可追踪，满足三轴 SSOT 体系的证据完整性要求
- 决策基线：`ADR-008`

## Tech Stack

| Layer | Technology | Reasoning |
| --- | --- | --- |
| `manifest` | Evidence Manifest | 用统一 manifest 描述证据包内容、来源和校验状态。 |
| `aggregation` | Artifact Aggregator | 聚合 code diff、review、test、gate、report 等证据。 |
| `traceability` | Acceptance Trace Matrix | 把证据映射回 FEAT/TECH/TASK/BUG。 |
| `audit` | Audit-ready Package Rendering | 输出可审计、可追踪的 evidence package。 |

## Core Components

### EvidencePackAggregator
- 职责：收集并去重各阶段证据引用。
- 依赖：ArtifactRegistry, TaskOutputs

### CoverageAuditor
- 职责：检查 acceptance 是否有足够证据覆盖。
- 依赖：TraceMatrix

### EvidencePublisher
- 职责：将 evidence pack 作为正式 SSOT/报告对象发布。
- 依赖：ReportRegistry

## Input To Delivery Mapping

### FEAT Processing Projection
- 设计 Evidence Pack Schema 定义
- 定义必需证据清单（代码、测试报告、评审记录、部署记录）
- 设计与 L2 工作流的集成接口
- 定义审计追溯规则
- 创建示例 Evidence Pack 模板

### Expected Deliverables
- Evidence Pack Schema 定义文档
- 必需证据清单文档
- L2 工作流集成接口规范
- 审计追溯规则文档
- 示例 Evidence Pack 模板

### Acceptance Alignment
- Evidence Pack Schema 文档已冻结
- Schema 包含完整的证据类型定义
- 必需证据清单覆盖代码、测试报告、评审记录、部署记录
- L2 工作流集成接口规范完整
- 审计追溯规则文档化
- 示例 Evidence Pack 模板提供
- 不干预 Evidence Pack 审计逻辑

## Implementation Constraints

- 所有实现必须以 `FEAT-SRC-009-004` 为上游事实源。
- 新增逻辑不得回流到 deprecated 或 broken 路径。
- 输出必须可被下游 TASK、Integration 或 Evidence Pack 审计。
- TECH 只定义技术结构、依赖、风险和交付边界，不替代实现代码。

## Risks And Fallback

- `R-001` 证据散落在各目录无法审计
  处理：统一由 Evidence Pack manifest 做收口和索引。
- `R-002` 只收集不校验，导致假闭环
  处理：引入 coverage auditor，输出缺口而不是只做打包。

## Review Checklist

- 技术选型是否支撑 FEAT 目标而非引入新的平级入口。
- 输入契约和输出边界是否可被下游 workflow 直接消费。
- 风险、fallback 和删除条件是否清晰且可执行。
- 是否保留对 `FEAT-SRC-009-004` 和 `ADR-008` 的可追溯引用。

## Out Of Scope

- 实现审计逻辑
- 修改 Evidence Pack 审计规则
- 实现证据收集自动化

## Metadata

- TECH ID：`TECH-FEAT-SRC-009-004-001`
- Parent FEAT：`FEAT-SRC-009-004`
- Source Refs：`FEAT-SRC-009-004`, `EPIC-SRC-009#scope`, `ADR-008`
- Materialized By：`batch-tech-src-009-20260312`
