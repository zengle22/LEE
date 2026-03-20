---
id: TASK-FEAT-169-004
ssot_type: task
title: 配置文件加载器扩展与向后兼容
status: frozen
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
frozen_at: '2026-03-13T01:36:39.496826'
---

# Objective

扩展 config_loader 支持 executor 配置字段加载并保持向后兼容

# Description

修改 src/lee/orchestrator/config_loader.py 在 ExecutorConfig 数据类中添加 default_type 字段，实现配置文件 executor.default_type 字段的加载和验证，当配置文件不存在或 executor 字段缺失时优雅降级到默认执行器 claude_code，提供配置加载错误的清晰提示

## Acceptance Mapping
- FEAT-169 / AC-002: 配置文件设置 executor: qwen 时配置层正确识别
- FEAT-169 / AC-004: 配置错误时返回明确错误信息

## Prerequisites
- TASK-FEAT-169-001

## Dependencies
- TASK-FEAT-169-001

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
review_required: true
```

## Rollback Strategy
```yaml
mode: revert
restore_targets:
- src/lee/orchestrator/config_loader.py
```

## Definition Of Done
- ExecutorConfig 数据类包含 default_type 字段
- 配置文件加载器支持 executor.default_type 字段解析
- 配置缺失时默认返回 claude_code
- 配置文件格式错误时返回明确错误提示
- 向后兼容：无 executor 配置的旧项目正常工作
