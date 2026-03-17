---
id: EPIC-057
ssot_type: epic
title: SSOT 需求轴验收治理体系
status: frozen
version: v1
workflow_instance_id: wf_task_4ac7ef06
parent_id: SRC-057
derived_from_ids:
- id: SRC-057
  version: v1
  required: true
source_refs:
- SRC-057#scope
owner: null
tags: []
properties:
  src_root_id: SRC-057
frozen_at: '2026-03-17T20:22:33.518161'
---

# SSOT 需求轴验收治理体系

## 目标

建立系统性的 SSOT 验收治理体系，确保 SRC/EPIC/FEAT/UI/TECH/TASK 六类 SSOT 文件在生成前都经过严格的测试和验收流程，以识别和修复 SSOT 质量问题，降低下游交付风险

## 范围

- 为 SRC/EPIC/FEAT/UI/TECH/TASK 六类 SSOT 文件建立强制性的测试和验收流程
- 实施 Auto Gate（自动化校验）、Review Gate（人工审查）、Approval Gate（审批冻结）三阶段质量把控机制
- 基于 6 维度验收框架对 SSOT 进行质量评估
- 使用 P0/P1/P2/P3 缺陷分级机制识别和修复 SSOT 质量问题
- 建立质量指标体系并监控：P0 缺陷密度=0、P1 缺陷密度<0.1、一次通过率>60%、验收覆盖率 100%
- 集成 L3 工作流系统、Schema Validator、Contract Validator 工具链
- 分阶段实施（Phase 1-5），预计 3-6 个月完成全量落地

## 非目标

- ADR 本身的验收流程
- TESTSET 的验收流程
- Dev 和 QA 部门内部流程

## 成功标准

- SSOT 一次通过率 > 60%
- P0 缺陷密度 = 0
- P1 缺陷密度 < 0.1
- SSOT 验收覆盖率 100%
- SSOT 质量问题导致的下游返工率显著降低
