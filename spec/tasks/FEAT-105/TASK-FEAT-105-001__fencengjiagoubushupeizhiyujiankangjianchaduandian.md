---
id: TASK-FEAT-105-001
ssot_type: task
title: 分层架构部署配置与健康检查端点
status: frozen
version: v1
parent_id: FEAT-105
derived_from_ids: []
source_refs:
- FEAT-105#delivery
owner: null
tags: []
properties:
  contract_key: task_feat_105_001
  identity_kind: ssot
frozen_at: '2026-03-12T14:01:00.156573'
---

# Objective

提供 raw-to-src 和 src-to-epic 的独立运行配置，实现层特定的 readiness 健康检查

# Description

创建 raw-to-src 和 src-to-epic 的独立运行配置，使用 CLI / script 形式的 readiness probe 代替 HTTP `/health` 服务接口，编写运行配置文档，验证故障隔离能力

## Acceptance Mapping
- FEAT-105 / AC-008-006-01: Raw-to-src 独立运行：workflow 可独立运行
- FEAT-105 / AC-008-006-02: Src-to-epic 独立运行：不依赖 raw-to-src 运行时
- FEAT-105 / AC-008-006-03: 健康检查探针：返回层特定健康状态
- FEAT-105 / AC-008-006-04: 运行配置文档：包含独立运行、联合运行、回滚流程
- FEAT-105 / AC-008-006-05: 故障隔离验证：raw-to-src 故障不影响 src-to-epic

## Dependencies
- TASK-FEAT-100-001
- TASK-FEAT-101-001

## Definition Of Done
- raw-to-src 运行配置完成
- src-to-epic 运行配置完成
- readiness probe 实现
- 运行配置文档已发布
- 故障隔离验证通过
