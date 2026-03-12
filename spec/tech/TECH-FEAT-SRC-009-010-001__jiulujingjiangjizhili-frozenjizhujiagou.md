---
id: TECH-FEAT-SRC-009-010-001
ssot_type: tech
title: 旧路径降级治理 - Frozen技术架构
status: active
version: v1
parent_id: FEAT-SRC-009-010
derived_from_ids:
- FEAT-SRC-009-010
- ADR-008
source_refs:
- FEAT-SRC-009-010
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

旧路径降级治理技术架构

## Goal Alignment

- 上游 FEAT：`FEAT-SRC-009-010`
- 目标：明确旧路径的 deprecated 状态，引导团队使用新的 L2 主入口，确保治理体系平稳过渡
- 用户价值：明确旧路径（如 phase-openspec-flow）的 deprecated 状态，引导团队使用新的 L2 主入口，确保治理体系平稳过渡
- 决策基线：`ADR-008`

## Tech Stack

| Layer | Technology | Reasoning |
| --- | --- | --- |
| `classification` | Path Classification Model | 把现有资产标成 current / compat / deprecated / broken。 |
| `guardrails` | Lint / CI / Scan Guardrails | 阻止旧入口继续被新增依赖。 |
| `compat_shell` | Compatibility Shell | 为必要旧入口提供只读兼容壳，不再承载新逻辑。 |
| `retirement` | Retirement Workflow | 定义统计、迁移、删除条件。 |

## Core Components

### PathClassifier
- 职责：维护路径状态与文档标签。
- 依赖：WorkflowGovernanceDoc

### LegacyUsageScanner
- 职责：扫描 import、workflow 引用和命令注册回流。
- 依赖：CI

### RetirementTracker
- 职责：跟踪删除条件和清理窗口。
- 依赖：Registry, GateLogs

## Input To Delivery Mapping

### FEAT Processing Projection
- 整理需标记 deprecated 的路径清单
- 定义标记规范（README、代码注释、workflow 文件头部标记）
- 编写迁移指南（从旧路径到新 L2 入口的映射）
- 定义旧路径活跃度监控机制
- 更新新入口 README/WORKFLOWS

### Expected Deliverables
- 旧路径降级治理文档
- Deprecated 路径清单
- 标记规范文档
- 迁移指南
- 活跃度监控机制定义
- 更新的 README/WORKFLOWS

### Acceptance Alignment
- 旧路径治理文档已冻结
- Deprecated 路径清单完整
- 标记规范覆盖 README、代码注释、workflow 文件头部
- 迁移指南包含从旧路径到新 L2 入口的映射
- 活跃度监控机制定义完整
- 新入口 README/WORKFLOWS 已更新
- 不强制迁移历史任务

## Implementation Constraints

- 所有实现必须以 `FEAT-SRC-009-010` 为上游事实源。
- 新增逻辑不得回流到 deprecated 或 broken 路径。
- 输出必须可被下游 TASK、Integration 或 Evidence Pack 审计。
- TECH 只定义技术结构、依赖、风险和交付边界，不替代实现代码。

## Risks And Fallback

- `R-001` 旧路径继续被 AI 复制扩散
  处理：把 deprecated/broken 明确写进文档和 CI。
- `R-002` 兼容壳变成常驻主路径
  处理：每条 compat 壳必须带退出条件。

## Review Checklist

- 技术选型是否支撑 FEAT 目标而非引入新的平级入口。
- 输入契约和输出边界是否可被下游 workflow 直接消费。
- 风险、fallback 和删除条件是否清晰且可执行。
- 是否保留对 `FEAT-SRC-009-010` 和 `ADR-008` 的可追溯引用。

## Out Of Scope

- 重写历史 workflow 文件
- 强制迁移历史任务
- 删除旧路径文件

## Metadata

- TECH ID：`TECH-FEAT-SRC-009-010-001`
- Parent FEAT：`FEAT-SRC-009-010`
- Source Refs：`FEAT-SRC-009-010`, `EPIC-SRC-009#scope`, `ADR-008`
- Materialized By：`batch-tech-src-009-20260312`
