---
id: TASK-FEAT-169-004
ssot_type: task
title: 端到端集成测试与验证
status: active
version: v1
parent_id: FEAT-169
derived_from_ids: []
source_refs:
- FEAT-169#delivery
owner: null
tags: []
properties:
  contract_key: task_feat_169_004
  identity_kind: ssot
---

# Objective

覆盖所有 AC 场景的端到端测试

# Description

执行端到端集成测试，覆盖 AC-001(CLI 指定)、AC-002(配置文件)、AC-003(优先级覆盖)、AC-004(非法配置错误)所有场景，验证 --verbose 模式配置追溯功能

## Acceptance Mapping
- FEAT-169 / AC-001: CLI 指定 --executor=qwen 时配置层正确识别
- FEAT-169 / AC-002: 配置文件设置 executor: qwen 时配置层正确识别
- FEAT-169 / AC-003: 执行器来源优先级判定 CLI > 配置文件 > 默认设置
- FEAT-169 / AC-004: 配置错误时返回明确错误信息

## Prerequisites
- 执行器配置优先级与验证规则规范
- TASK-FEAT-169-001
- TASK-FEAT-169-002
- TASK-FEAT-169-003

## Dependencies
- TASK-FEAT-169-000
- TASK-FEAT-169-001
- TASK-FEAT-169-002
- TASK-FEAT-169-003

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
- FTA-FEAT-169-20260312
- FEAT-169-UI
review_required: true
```

## Rollback Strategy
```yaml
mode: revert
restore_targets:
- src/lee/orchestrator/config/
- src/lee/cli/commands/run.py
```

## Definition Of Done
- AC-001 测试通过：--executor=qwen 正确识别
- AC-002 测试通过：配置文件 executor: qwen 正确识别
- AC-003 测试通过：CLI 覆盖配置文件优先级正确
- AC-004 测试通过：无效执行器类型返回明确错误信息
- --verbose 模式配置追溯输出正确
- 向后兼容性验证通过(无 executor 配置时默认 claude_code)
