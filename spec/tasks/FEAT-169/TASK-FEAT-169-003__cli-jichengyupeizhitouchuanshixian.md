---
id: TASK-FEAT-169-003
ssot_type: task
title: CLI 集成与配置透传实现
status: active
version: v1
parent_id: FEAT-169
derived_from_ids: []
source_refs:
- FEAT-169#delivery
owner: null
tags: []
properties:
  contract_key: task_feat_169_003
  identity_kind: ssot
---

# Objective

在 CLI run 命令中集成执行器配置并在 workflow_data 中透传

# Description

修改 src/lee/cli/commands/run.py 实现 --executor 参数解析和 ExecutorTypeResolver 集成，扩展 config_loader.py 实现配置文件 executor 字段验证，在 workflow_data 中透传 executor_config

## Acceptance Mapping
- FEAT-169 / AC-001: CLI 指定 --executor=qwen 时配置层正确识别
- FEAT-169 / AC-002: 配置文件设置 executor: qwen 时配置层正确识别
- FEAT-169 / AC-003: 执行器来源优先级判定 CLI > 配置文件 > 默认设置

## Prerequisites
- 执行器配置优先级与验证规则规范
- TASK-FEAT-169-002

## Dependencies
- TASK-FEAT-169-000
- TASK-FEAT-169-002

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
- src/lee/cli/commands/run.py
- src/lee/orchestrator/config_loader.py
```

## Definition Of Done
- run.py 支持 --executor 参数
- run.py 集成 ExecutorTypeResolver
- config_loader.py 支持 executor 字段验证
- workflow_data 包含 executor_config 透传结构
- CLI 输出符合交互原则(优先级透明、错误即时反馈)
