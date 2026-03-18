---
id: FEAT-SRC-058-003
ssot_type: feat
title: Smoke 执行性能优化
status: frozen
version: v2
workflow_instance_id: wf_task_fdb19191-refreeze
parent_id: EPIC-SRC-058-001
derived_from_ids:
- id: EPIC-SRC-058-001
  version: v3
  required: true
source_refs:
- EPIC-SRC-058-001#scope
owner: null
tags: []
properties:
  contract_key: feat_003
  identity_kind: ssot
frozen_at: '2026-03-17T12:00:00.000000'
---

# Goal

确保本地 Smoke 执行时间≤30 分钟，在合理反馈时间内完成完整测试覆盖

# User Value

确保本地 Smoke 执行时间≤30 分钟，在合理反馈时间内完成完整测试覆盖，不阻塞开发流程

# Inputs

- test_execution_metrics
- performance_threshold
- timeout_config

# Processing

- 实现本地 Smoke 执行时间测量
- 配置≤30 分钟性能约束
- 实现超时告警机制
- 支持多浏览器实例并行执行 (Playwright)
- 支持跨模块并行 (pytest-xdist)
- 并行数配置：默认 4，最大 8
- 实现动态超时策略：基础 15 分钟 + 按用例数增加

# Outputs

- execution_time_metrics
- performance_report
- timeout_alerts

# Acceptance

- 本地 Smoke 执行时间≤30 分钟
- 性能约束配置生效
- 超时告警机制正常
- 并行执行功能正常，支持默认 4 路并行
- 动态超时策略生效

# Acceptance Checks

## AC-001
Smoke 执行时间自动测量并记录

## AC-002
执行时间超过 30 分钟时触发告警

## AC-003
性能报告生成并可视化

## AC-004
并行执行功能正常，支持默认 4 路并行，执行时间减少 60% 以上

## AC-005
动态超时策略生效，根据用例数量自动调整超时阈值

# Non Goals

- CI 环境性能优化
- 完整回归测试性能约束

# Dependencies

- FEAT-SRC-058-002
