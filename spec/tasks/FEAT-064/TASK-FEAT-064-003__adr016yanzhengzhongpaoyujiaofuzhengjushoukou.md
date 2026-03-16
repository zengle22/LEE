---
id: TASK-FEAT-064-003
ssot_type: task
title: ADR-016 验证重跑与交付证据收口
status: frozen
version: v1
parent_id: FEAT-064
derived_from_ids: []
source_refs:
- FEAT-064#delivery
owner: null
tags: []
properties:
  contract_key: task_feat_064_003
  identity_kind: ssot
workflow_instance_id: wf_task_adr016_cleanup
frozen_at: '2026-03-14T13:37:00'
---

# Objective

完成 ADR-016 验证运行的重跑检查、结果归档与交付证据收口

# Description

对 ADR-016 尾部交付进行验证闭环：
- 检查 reverse SSOT chain 的 completion 与 review 报告
- 记录 `SRC / EPIC / FEAT / seed-view` 输出规模及阻塞情况
- 标记仍处于 `running` 的历史验证运行，避免误判为已闭环
- 为后续 FEAT 冻结与人工关单提供证据摘要

## Acceptance Mapping
- EPIC-064 / Scope-005: 基于冻结状态实现验证运行自动批准
- EPIC-064 / Success-003: 验证运行自动批准成功率 >= 95%

## Prerequisites
- TASK-FEAT-064-001
- TASK-FEAT-064-002

## Dependencies
- docs/reports/reverse-ssot-chain-completion.md
- docs/reports/reverse-epic-feat-review.json
- .artifacts/active/reverse-ssot-chain-manifest.json
- .artifacts/active/RUN-20260313234307-8cf0/manifest.yaml

## Observability
```yaml
execution_unit: task
log_scope: task-validation
audit_fields:
- task_id
- run_refs
- blocker_count
- major_count
- completion_status
```

## Evidence Requirements
```yaml
required_refs:
- docs/reports/reverse-ssot-chain-completion.md
- docs/reports/reverse-epic-feat-review.json
- .artifacts/active/reverse-ssot-chain-manifest.json
- .artifacts/active/RUN-20260313234307-8cf0/manifest.yaml
review_required: true
```

## Rollback Strategy
```yaml
mode: revert
restore_targets:
- spec/tasks/FEAT-LEE-SRC-FREEZE-20260313-001/
- docs/reports/reverse-ssot-chain-completion.md
- docs/reports/reverse-epic-feat-review.json
```

## Definition Of Done
- TASK 文件已冻结并写入 spec/tasks/FEAT-064/
- reverse SSOT chain 输出规模和 review 结果有明确证据引用
- 历史 `running` 运行被显式标记为未收口，不再混同为完成态
- ADR-016 尾部交付缺口被收敛为可跟踪的验证项
