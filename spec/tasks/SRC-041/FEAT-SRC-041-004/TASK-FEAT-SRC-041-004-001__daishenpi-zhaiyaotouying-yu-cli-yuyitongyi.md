---
id: TASK-FEAT-SRC-041-004-001
ssot_type: task
title: 待审批摘要投影视图与 CLI 语义统一
status: draft
version: v1
workflow_instance_id: adr-017-gate-governance-impl
parent_id: FEAT-SRC-041-004
derived_from_ids:
- id: FEAT-SRC-041-004
  version: v1
  required: true
source_refs:
- FEAT-SRC-041-004#delivery
- TECH-FEAT-SRC-041-001
- ADR-017#Gate Flow And Workflow State Machine
owner: null
tags:
- cli
- gate
- projection
properties:
  contract_key: task_feat_src_041_004_001_cli_projection
  identity_kind: ssot
---

# Objective

统一待审批 gate 的最小可判断摘要模型，并让 `list`、`show`、`decide` 三条 CLI 链路复用同一字段命名、来源与含义。

# Description

围绕 FEAT-SRC-041-016-004，把 `purpose`、`decision_mode`、`subject`、`why_now` 与必要 `repo_context` 收敛为单一 `pending_gate_summary` 读模型，明确摘要字段如何从 `human_gate_context` 与 gate 语义回填，并阻断 CLI 侧再造第二套治理术语。

## Acceptance Mapping

- FEAT-SRC-041-004 / AC-FEAT-SRC-041-004-01: 待审批 gate 在 `list` 阶段即可稳定展示 `purpose`、`decision_mode`、`subject`、`why_now` 摘要。
- FEAT-SRC-041-004 / AC-FEAT-SRC-041-004-02: `show` 与 `decide` 延续同一字段命名与语义，不再出现平行命名体系。

## Prerequisites

- FEAT-SRC-041-001 已冻结
- FEAT-SRC-041-002 已冻结
- FEAT-SRC-041-004 已冻结

## Dependencies

- TASK-FEAT-SRC-041-001-001
- TASK-FEAT-SRC-041-002-001

## Inputs

- 双轴语义与 `human_gate_context` 前置对象
- TECH-FEAT-SRC-041-016 中 `pending_gate_summary`、CLI 投影视图与 repo_context 边界
- 现有 CLI `list`、`show`、`decide` 链路的待审批展示需求

## Outputs

- `pending_gate_summary` 统一字段模型
- `list/show/decide` 共用的字段来源与渲染边界
- `repo_context` 来源、最小内容与缺失处理规则

## Definition Of Done

- `pending_gate_summary` 已冻结为 CLI 唯一最小可判断摘要模型
- `list` 在不跳转详情的前提下提供四个最小判断字段
- `show` 与 `decide` 复用同名同义字段，不再引入平行术语或二次映射
- `repo_context` 的来源、必要性与最小边界已明确，避免未定义依赖进入摘要链路
- 当 `human_gate_context` 无法回填摘要字段时，gate 不进入可审批列表

## Observability

```yaml
execution_unit: task
log_scope: gate-cli-projection-task
audit_fields:
- run_id
- task_id
- gate_id
- projection_version
- purpose
- decision_mode
- subject
- why_now
- repo_context_ref
- evidence_refs
```

## Evidence Requirements

```yaml
required_refs:
- FEAT-SRC-041-004
- TECH-FEAT-SRC-041-016
- ADR-017
review_required: true
```

## Rollback Strategy

```yaml
mode: revert
restore_targets:
- spec/requirements/SRC-041/FEAT-SRC-041-004__daishenpi-gate-dezuixiaokepanduanzhaiyaotongyi.md
- spec/tech/TECH-FEAT-SRC-041-016__adr-017-gate-shuangzhou-yurenjueshenpi-frozen-jishujiagou.md
- src/lee/cli/commands/gates_cmd.py
- src/lee/orchestrator/execution/gate_projection.py
preconditions:
- 记录当前 list/show/decide 字段差异与命名冲突样本
```
