---
id: TECH-FEAT-SRC-009-008-001
ssot_type: tech
title: L3 Integration 阶段定义 - Frozen技术架构
status: active
version: v1
parent_id: FEAT-SRC-009-008
derived_from_ids:
- FEAT-SRC-009-008
- ADR-008
source_refs:
- FEAT-SRC-009-008
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

L3 Integration 阶段技术架构

## Goal Alignment

- 上游 FEAT：`FEAT-SRC-009-008`
- 目标：定义 Integration 阶段的标准化流程，确保前后端、内外部依赖正确集成
- 用户价值：Dev 团队获得标准化的集成验证阶段指导，确保前后端、内外部依赖正确集成，产出集成测试证据
- 决策基线：`ADR-008`

## Tech Stack

| Layer | Technology | Reasoning |
| --- | --- | --- |
| `integration_plan` | Integration Plan Definition | 显式定义联调对象、环境、账号和数据要求。 |
| `verification` | Contract + Environment Verification | 无环境时做 contract/mock 校验，有环境时做真实联调。 |
| `rollback` | Structural Rollback Routing | 识别结构问题应回滚到 TECH/CONTRACT 还是实现层。 |
| `reporting` | Integration Report Publication | 输出 integration report 供后续 Evidence Pack 消费。 |

## Core Components

### IntegrationPlanner
- 职责：定义联调矩阵和执行路径。
- 依赖：ContractFreezeRef, ArtifactRefs

### IntegrationVerifier
- 职责：执行接口和环境级联调验证。
- 依赖：EnvRef, TestAccountRef

### StructuralIssueRouter
- 职责：识别结构性问题并给出回滚边界。
- 依赖：TechSpecRef, ContractFreezeRef

## Input To Delivery Mapping

### FEAT Processing Projection
- 定义阶段输入规范（Backend/Frontend 阶段输出）
- 定义阶段内任务清单（环境准备、集成测试执行、问题修复）
- 定义输出物规范（集成测试报告、问题修复记录）
- 定义完成标准（集成测试通过率阈值）
- 定义与 Evidence Pack 阶段的交接规则

### Expected Deliverables
- L3 Integration 阶段定义文档
- 输入规范文档
- 阶段任务清单
- 输出物规范
- 完成标准定义（含通过率阈值）
- 阶段交接规则文档

### Acceptance Alignment
- L3 Integration 阶段文档已冻结
- 输入规范明确定义 Backend/Frontend 阶段输出为输入
- 阶段任务清单覆盖环境准备、集成测试执行、问题修复
- 输出物规范定义集成测试报告和问题修复记录格式
- 完成标准包含集成测试通过率阈值
- 与 Evidence Pack 阶段的交接规则文档化
- 不包含具体集成测试框架

## Implementation Constraints

- 所有实现必须以 `FEAT-SRC-009-008` 为上游事实源。
- 新增逻辑不得回流到 deprecated 或 broken 路径。
- 输出必须可被下游 TASK、Integration 或 Evidence Pack 审计。
- TECH 只定义技术结构、依赖、风险和交付边界，不替代实现代码。

## Risks And Fallback

- `R-001` 把结构问题误判为实现问题
  处理：在 report 中区分 structural_issue 和 impl_issue。
- `R-002` 环境依赖不明确导致联调失真
  处理：把 env/base_url/test_account/seed_data 定义为显式输入。

## Review Checklist

- 技术选型是否支撑 FEAT 目标而非引入新的平级入口。
- 输入契约和输出边界是否可被下游 workflow 直接消费。
- 风险、fallback 和删除条件是否清晰且可执行。
- 是否保留对 `FEAT-SRC-009-008` 和 `ADR-008` 的可追溯引用。

## Out Of Scope

- 实现集成测试框架
- 定义具体测试工具
- 实现自动化部署

## Metadata

- TECH ID：`TECH-FEAT-SRC-009-008-001`
- Parent FEAT：`FEAT-SRC-009-008`
- Source Refs：`FEAT-SRC-009-008`, `EPIC-SRC-009#scope`, `ADR-008`
- Materialized By：`batch-tech-src-009-20260312`
