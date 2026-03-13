---
id: TASK-FEAT-143-005
ssot_type: task
title: CLI Executor (lee qa execute) 命令与 5 阶段反馈实现
status: active
version: v1
parent_id: FEAT-143
derived_from_ids: []
source_refs:
- FEAT-143#delivery
owner: null
tags: []
properties:
  contract_key: task_feat_143_005
  identity_kind: ssot
---

# Objective

实现 lee qa execute 命令，集成 EntryRouter/BypassBlocker/ChainValidator/AuditLogger，提供 5 阶段反馈模型

# Description

实现 lee qa execute 命令：集成 EntryRouter/BypassBlocker/ChainValidator/AuditLogger；实现 5 阶段反馈模型 ([1/5] 入口校验、[2/5] 旁路检测、[3/5] 链路校验、[4/5] 执行准备、[5/5] 执行启动)；实现 exit_codes (0:成功、1:入口校验失败、2:链路校验失败、3:旁路阻断、4:执行失败、5:内部错误)。

## Acceptance Mapping
- FEAT-143 / AC-003-001: lee qa execute 命令仅接受有效的 task_ref 且 task 归属 testplan 的执行请求
- FEAT-143 / AC-003-002: lee qa execute 命令在执行前进行路径完整性校验并反馈 [3/5] 链路校验进度
- FEAT-143 / AC-003-003: lee qa execute 命令拒绝绕过 TESTPLAN/TASK 的直接执行请求并返回入口规范错误
- FEAT-143 / AC-003-004: lee qa execute 命令记录所有执行请求的审计日志

## Prerequisites
- TASK-FEAT-143-001
- TASK-FEAT-143-002
- TASK-FEAT-143-003
- TASK-FEAT-143-004

## Dependencies
- Click
- EntryRouter
- BypassBlocker
- ChainValidator
- AuditLogger

## Observability
```yaml
execution_unit: task
log_scope: task-cli-integration
audit_fields:
- run_id
- task_id
- changed_files
- test_results
- cli_command_refs
```

## Evidence Requirements
```yaml
required_refs:
- TECH-FEAT-143-009
- TASK-FEAT-143-001
- TASK-FEAT-143-002
- TASK-FEAT-143-003
- TASK-FEAT-143-004
review_required: true
```

## Rollback Strategy
```yaml
mode: revert
restore_targets:
- src/lee/cli/commands/qa_execute.py
preconditions:
- 保留实现前的代码版本
- 确保原有 CLI 命令可用
```

## Definition Of Done
- TASK 文件已冻结
- lee qa execute 命令实现完成并通过集成测试
- 5 阶段反馈模型完整实现
- exit_codes 全部覆盖
- 命令选项 --task-ref/--plan-ref/--release-ref/--validate-only/--json/--verbose 全部可用
