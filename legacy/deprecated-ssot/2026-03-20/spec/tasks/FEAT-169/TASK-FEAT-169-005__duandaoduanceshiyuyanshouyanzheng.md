---
id: TASK-FEAT-169-005
ssot_type: task
title: 端到端测试与验收验证
status: frozen
version: v1
parent_id: FEAT-169
derived_from_ids: []
source_refs:
- FEAT-169#delivery
owner: null
tags: []
properties:
  contract_key: task_feat_169_005
  identity_kind: ssot
frozen_at: '2026-03-13T01:36:39.518143'
---

# Objective

执行覆盖所有 AC 场景的端到端集成测试

# Description

执行端到端集成测试覆盖四个 AC 场景：AC-001 验证 CLI 指定 --executor=qwen 正确识别，AC-002 验证配置文件 executor: qwen 正确识别，AC-003 验证 CLI 覆盖配置文件的优先级逻辑，AC-004 验证非法执行器类型返回明确错误并阻止 workflow 执行，验证 --verbose 模式配置追溯输出，验证向后兼容性

## Acceptance Mapping
- FEAT-169 / AC-001: CLI 指定 --executor=qwen 时配置层正确识别
- FEAT-169 / AC-002: 配置文件设置 executor: qwen 时配置层正确识别
- FEAT-169 / AC-003: 执行器来源优先级判定 CLI > 配置文件 > 默认设置
- FEAT-169 / AC-004: 配置错误时返回明确错误信息

## Prerequisites
- TASK-FEAT-169-002
- TASK-FEAT-169-003
- TASK-FEAT-169-004

## Dependencies
- TASK-FEAT-169-002
- TASK-FEAT-169-003
- TASK-FEAT-169-004

## Observability
```yaml
execution_unit: task
log_scope: task-execution
audit_fields:
- run_id
- changed_files
- evidence_refs
```

## Evidence Requirements
```yaml
required_refs:
- FTA-FEAT-169-20260313
- FEAT-169-UI
review_required: true
```

## Rollback Strategy
```yaml
mode: revert
restore_targets:
- src/lee/orchestrator/config/
- src/lee/cli/commands/
```

## Definition Of Done
- AC-001 测试通过：--executor=qwen 被正确识别并透传
- AC-002 测试通过：配置文件 executor: qwen 被正确识别
- AC-003 测试通过：CLI 优先级高于配置文件
- AC-004 测试通过：无效执行器返回明确错误并阻止执行
- --verbose 模式输出配置来源追溯信息
- 向后兼容性验证：无配置时使用默认执行器
