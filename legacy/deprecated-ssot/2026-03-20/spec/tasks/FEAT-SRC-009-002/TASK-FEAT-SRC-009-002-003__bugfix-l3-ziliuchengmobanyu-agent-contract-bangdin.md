---
id: TASK-FEAT-SRC-009-002-003
ssot_type: task
title: Bugfix L3 子流程模板与 Agent/Contract 绑定
status: frozen
version: v1
parent_id: FEAT-SRC-009-002
derived_from_ids: []
source_refs:
- FEAT-SRC-009-002#delivery
owner: null
tags: []
properties:
  contract_key: task_feat_src_009_002_003
  identity_kind: ssot
frozen_at: '2026-03-13T00:38:12.864658'
---

# Objective

实现 Bugfix L2 引用的 L3 子流程模板族，并完成与 Agent 和 Gate 的绑定

# Description

基于 ADR-008 定义的 Bugfix L3 家族，实现以下 L3 模板并完成与现有 Agent/Gate 的绑定：(1) template.dev.bugfix_triage_l3；(2) template.dev.bugfix_root_cause_l3；(3) template.dev.bugfix_fix_design_l3；(4) template.dev.bugfix_fix_impl_l3；(5) template.dev.bugfix_verification_l3；(6) template.dev.bugfix_evidence_pack_l3。集成现有 Agent (bug-triage, bug-root-cause-analyst, bug-fix-planner, bug-fix-implementer, bug-fix-verifier, bug-evidence-pack) 和 Gate (bugfix-plan-gate, contract-freeze-gate, smoke-gate)。

## Acceptance Mapping
- FEAT-SRC-009-002 / AC-002-001: Bugfix L3 子流程模板族已创建并绑定到 L2
- FEAT-SRC-009-002 / AC-002-003: L3 阶段编排通过 Agent/Contract 绑定可执行

## Prerequisites
- TASK-FEAT-SRC-009-002-002 完成

## Dependencies
- TASK-FEAT-SRC-009-002-002

## Observability
```yaml
execution_unit: task
log_scope: task-execution
audit_fields:
- run_id
- changed_files
- agent_bindings
- gate_bindings
- l3_template_ids
```

## Evidence Requirements
```yaml
required_refs:
- spec-global/departments/dev/workflows/templates/bugfix-triage-l3-template.yaml
- spec-global/departments/dev/workflows/templates/bugfix-root-cause-l3-template.yaml
- spec-global/departments/dev/workflows/templates/bugfix-fix-design-l3-template.yaml
- spec-global/departments/dev/workflows/templates/bugfix-fix-impl-l3-template.yaml
- spec-global/departments/dev/workflows/templates/bugfix-verification-l3-template.yaml
- spec-global/departments/dev/workflows/templates/bugfix-evidence-pack-l3-template.yaml
review_required: true
```

## Rollback Strategy
```yaml
mode: revert
restore_targets:
- spec-global/departments/dev/workflows/templates/bugfix-*l3-template.yaml
preconditions:
- L3 模板未正式引用前可回滚
```

## Definition Of Done
- 6 个 Bugfix L3 模板文件已创建 (triage, root_cause, fix_design, fix_impl, verification, evidence_pack)
- 每个 L3 模板正确引用对应的 Agent (bug-triage, bug-root-cause-analyst, bug-fix-planner, bug-fix-implementer, bug-fix-verifier)
- Gate 绑定完整 (bugfix-plan-gate 用于 triage, contract-freeze-gate 用于 fix_design, smoke-gate 用于 merge_decision)
- L2 到 L3 的数据传递契约已定义
- L3 到 L2 的输出返回契约已定义
- 所有模板通过语法和结构验证
