---
id: TASK-FEAT-170-001
ssot_type: task
<<<<<<< HEAD
title: Qwen 执行器工厂注册与实例化
=======
title: Qwen Chat 工厂注册与实例化
>>>>>>> codex/src011-qwen-implementation
status: active
version: v1
parent_id: FEAT-170
derived_from_ids: []
source_refs:
- FEAT-170#delivery
owner: null
tags: []
properties:
  contract_key: task_feat_170_001
  identity_kind: ssot
---

# Objective

<<<<<<< HEAD
在现有 ExecutorFactory 中注册并实例化 qwen 通用执行器

# Description

基于 TECH-FEAT-170-001，在现有 `ExecutorFactory` 中新增 `qwen` 注册与构造路径，确保其默认绑定 `qwen profile`，并与既有 `llm`、`claude_code`、`codex`、`kimi` 执行器并存。

## Acceptance Mapping
- FEAT-170 / AC-001: 工厂创建 qwen 实例
=======
在现有 ExecutorFactory 中注册并实例化 qwen_chat 对话执行实例

# Description

基于 TECH-FEAT-170-001，在现有 `ExecutorFactory` 中新增 `qwen_chat` 注册与构造路径，并兼容历史别名 `qwen`，确保其默认绑定 `qwen` 对话 profile，并与既有 `llm`、`claude_code`、`codex`、`kimi` 执行器并存。

## Acceptance Mapping
- FEAT-170 / AC-001: 工厂创建 qwen_chat 实例
>>>>>>> codex/src011-qwen-implementation
- FEAT-170 / AC-002: 实例接口合规

## Prerequisites
- TECH-FEAT-170-001 技术方案已冻结

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
- TECH-FEAT-170-001
review_required: true
```

## Rollback Strategy
```yaml
mode: revert
restore_targets:
- src/lee/orchestrator/execution/executors.py
- src/lee/orchestrator/execution/llm_executor.py
```

## Definition Of Done
<<<<<<< HEAD
- `ExecutorFactory.create(\"qwen\")` 可返回可执行实例
- `QwenExecutor` 默认绑定 `qwen` profile
- 不影响现有执行器的实例化逻辑
- TASK 文件已冻结

=======
- `ExecutorFactory.create(\"qwen_chat\")` 可返回可执行实例
- `QwenExecutor` 默认绑定 `qwen` profile
- 不影响现有执行器的实例化逻辑
- TASK 文件已冻结
>>>>>>> codex/src011-qwen-implementation
