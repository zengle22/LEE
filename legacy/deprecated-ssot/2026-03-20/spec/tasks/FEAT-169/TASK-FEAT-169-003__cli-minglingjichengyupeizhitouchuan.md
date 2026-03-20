---
id: TASK-FEAT-169-003
ssot_type: task
title: CLI 命令集成与配置透传
status: frozen
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
frozen_at: '2026-03-13T01:36:39.475010'
---

# Objective

在 run 命令中集成执行器配置解析并在 workflow_data 中透传

# Description

修改 src/lee/cli/commands/run.py 集成 --executor CLI 参数解析，注入 ConfigResolver 进行配置解析和验证，验证失败时抛出 click.ClickException 阻止 workflow 启动，在 workflow_data 中设置 executor_override 和 executor_selection_source 字段透传到 Orchestrator 层

## Acceptance Mapping
- FEAT-169 / AC-001: CLI 指定 --executor=qwen 时配置层正确识别
- FEAT-169 / AC-003: 执行器来源优先级判定 CLI > 配置文件 > 默认设置

## Prerequisites
- TASK-FEAT-169-002

## Dependencies
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
- FTA-FEAT-169-20260313
- FEAT-169-UI
review_required: true
```

## Rollback Strategy
```yaml
mode: revert
restore_targets:
- src/lee/cli/commands/run.py
```

## Definition Of Done
- run.py 支持 --executor 参数
- ConfigResolver 正确集成到 run 命令
- 验证失败时抛出 ClickException 并显示错误信息
- workflow_data 包含 executor_override 字段
- workflow_data 包含 executor_selection_source 字段
- --verbose 模式输出配置追溯信息
