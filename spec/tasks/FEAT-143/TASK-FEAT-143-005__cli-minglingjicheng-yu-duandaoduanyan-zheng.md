---
id: TASK-FEAT-143-005
ssot_type: task
title: CLI 命令集成与端到端验证
status: draft
version: v1
parent_id: FEAT-143
derived_from_ids: []
source_refs:
- FEAT-143#delivery
owner: null
tags: []
properties:
  contract_key: task_cli_integration
  identity_kind: ssot
---

# CLI 命令集成与端到端验证

# Objective

实现 lee qa execute 命令并完成端到端集成验证

# Description

实现 lee qa execute CLI 命令，集成 EntryRouter/BypassBlocker/ChainValidator/AuditLogger 组件。实现 5 阶段反馈模型、状态图标系统、错误码显示。完成端到端测试验证所有 AC。

## Acceptance Mapping
- FEAT-143 / AC-003-001: lee qa execute 命令仅接受有效 task_ref 参数
- FEAT-143 / AC-003-003: 旁路执行请求被阻断并显示 ERR-BYPASS 错误码
- FEAT-143 / AC-003-004: lee qa audit log 命令可查询审计日志

## Dependencies
- {"task_id": "TASK-FEAT-143-001", "relation": "requires_specification"}
- {"task_id": "TASK-FEAT-143-002", "relation": "requires_entry_router"}
- {"task_id": "TASK-FEAT-143-003", "relation": "requires_chain_validator"}
- {"task_id": "TASK-FEAT-143-004", "relation": "requires_audit_logger"}

## Definition Of Done
- src/lee/cli/commands/qa_execute.py 实现完成
- 5 阶段反馈模型已实现
- 状态图标系统已配置
- 错误码显示已集成
- 端到端测试覆盖所有 AC 场景
- lee qa audit log 命令已实现
- TASK 文件已冻结

# Inputs

- TASK-FEAT-143-001 输出的错误码注册表
- TASK-FEAT-143-002 输出的 EntryRouter/BypassBlocker
- TASK-FEAT-143-003 输出的 ChainValidator
- TASK-FEAT-143-004 输出的 AuditLogger
- Frozen UI 原型（FUIP-20260313-004）交互规范
- Click CLI 框架现有基础设施

# Processing

- 实现 lee qa execute 命令（Click 命令定义）
- 实现 --task-ref 必需参数（Click option）
- 实现 --plan-ref/--release-ref 可选参数
- 实现 --validate-only 仅校验模式
- 实现 --json JSON 输出模式
- 实现 5 阶段反馈模型（[ENTRY]、[CHAIN]、[AUDIT]、[EXEC]）
- 实现状态图标系统（✓、✗、⚠、→、○、ℹ）
- 实现错误码显示（ERR-ENTRY-*、ERR-CHAIN-*、ERR-BYPASS-*）
- 实现 lee qa audit log 查询命令
- 实现端到端测试（覆盖 AC-003-001~004 所有场景）

# Outputs

- src/lee/cli/commands/qa_execute.py CLI 执行命令
- src/lee/cli/commands/qa_audit.py CLI 审计查询命令
- src/lee/cli/output_formatter.py CLI 输出格式化工具
- tests/e2e/test_qa_execute_e2e.py 端到端测试
- tests/e2e/test_qa_audit_e2e.py 审计查询端到端测试

# Dependencies

- TASK-FEAT-143-001（规范定义）
- TASK-FEAT-143-002（EntryRouter/BypassBlocker）
- TASK-FEAT-143-003（ChainValidator）
- TASK-FEAT-143-004（AuditLogger）

# Non Goals

- 不涉及测试用例内容设计
- 不涉及测试报告格式
- 不涉及图形化界面
