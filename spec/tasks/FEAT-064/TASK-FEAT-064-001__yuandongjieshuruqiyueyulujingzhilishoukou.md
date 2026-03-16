---
id: TASK-FEAT-064-001
ssot_type: task
title: 源冻结输入契约与路径治理收口
status: frozen
version: v1
parent_id: FEAT-064
derived_from_ids: []
source_refs:
- FEAT-064#delivery
owner: null
tags: []
properties:
  contract_key: task_feat_064_001
  identity_kind: ssot
workflow_instance_id: wf_task_adr016_cleanup
frozen_at: '2026-03-14T13:35:00'
---

# Objective

固化 ADR-016 验证运行所需的 source_freeze 输入契约、路径边界和自动批准前提

# Description

围绕 ADR-016 的验证运行范围，补齐源冻结阶段的规范收口：
- 明确 `source_freeze`、`frozen_inputs`、`workspace_artifacts` 的契约边界
- 固定冻结输出路径为 `output/design-frozen/` 及其下游传递方式
- 约束自动批准仅建立在冻结态与输入元数据完整的前提上
- 为后续实现与验证任务提供稳定的评审基线

## Acceptance Mapping
- FEAT-064 / AC-001: 执行器调用 source_freeze 步骤后生成包含工件列表的执行报告
- EPIC-064 / Scope-002: 验证 frozen_inputs 元数据合规性
- EPIC-064 / Scope-003: 强制 workspace_artifacts 路径一致性
- EPIC-064 / Scope-005: 基于冻结状态实现验证运行自动批准

## Dependencies
- ADR-016
- EPIC-064

## Observability
```yaml
execution_unit: task
log_scope: task-governance
audit_fields:
- task_id
- changed_files
- evidence_refs
- review_report_refs
```

## Evidence Requirements
```yaml
required_refs:
- ADR-016
- EPIC-064
- spec-global/departments/product/workflows/templates/raw-to-src/v1/workflow.yaml
- tests/test_run_spec_governance.py
review_required: true
```

## Rollback Strategy
```yaml
mode: revert
restore_targets:
- spec/requirements/features/FEAT-LEE-SRC-FREEZE-20260313-001__yuandongjiezhixingbuzouluojishixian.md
- spec/tasks/FEAT-LEE-SRC-FREEZE-20260313-001/
```

## Definition Of Done
- TASK 文件已冻结并写入 spec/tasks/FEAT-064/
- FEAT 交付段明确列出 ADR-016 尾部任务
- `source_freeze`、`frozen_inputs`、`workspace_artifacts` 的契约边界有明确落盘说明
- 自动批准仅在冻结态和输入元数据齐备时触发的边界被写明
