---
id: TASK-FEAT-169-001
ssot_type: task
title: 执行器类型枚举与数据模型定义
status: frozen
version: v1
parent_id: FEAT-169
derived_from_ids: []
source_refs:
- FEAT-169#delivery
owner: null
tags: []
properties:
  contract_key: task_feat_169_001
  identity_kind: ssot
frozen_at: '2026-03-13T01:36:39.436516'
---

# Objective

定义 ExecutorType 枚举、ResolvedExecutorConfig 数据类和 ConfigSource 枚举

# Description

在 src/lee/orchestrator/config/types.py 创建执行器类型核心数据模型：ExecutorType 枚举定义允许的执行器类型 (claude_code, qwen, kimi, codex, langgraph, shell, llm)，ConfigSource 枚举定义配置来源 (cli_override, file_config, default)，ResolvedExecutorConfig 数据类承载解析结果包含 executor_type、source、raw_cli、raw_file、is_valid、error_message 字段

## Acceptance Mapping
- FEAT-169 / AC-001: CLI 指定 --executor=qwen 时配置层正确识别 - 由 ExecutorType 枚举支持 qwen 值
- FEAT-169 / AC-002: 配置文件设置 executor: qwen 时配置层正确识别 - 由 ResolvedExecutorConfig 承载配置值

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
- FEAT-169
review_required: true
```

## Rollback Strategy
```yaml
mode: revert
restore_targets:
- src/lee/orchestrator/config/types.py
```

## Definition Of Done
- ExecutorType 枚举定义完成，包含所有允许的执行器类型
- ConfigSource 枚举定义完成，包含三种配置来源
- ResolvedExecutorConfig 数据类包含所有必需字段
- 提供 from_string 静态方法支持大小写不敏感解析
- 提供 allowed_values 类方法返回允许值列表
