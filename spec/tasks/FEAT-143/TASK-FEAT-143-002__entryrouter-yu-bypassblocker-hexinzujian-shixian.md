---
id: TASK-FEAT-143-002
ssot_type: task
title: EntryRouter 与 BypassBlocker 核心组件实现
status: draft
version: v1
parent_id: FEAT-143
derived_from_ids: []
source_refs:
- FEAT-143#delivery
owner: null
tags: []
properties:
  contract_key: task_entry_router_impl
  identity_kind: ssot
---

# EntryRouter 与 BypassBlocker 核心组件实现

# Objective

实现执行入口路由器和旁路阻断器核心组件

# Description

实现 EntryRouter 作为执行入口的核心接口，集成 BypassBlocker 检测并阻断旁路执行请求。包含 BYPASS-001~004 场景识别、ERR-BYPASS-*错误码返回、异步审计记录。

## Acceptance Mapping
- FEAT-143 / AC-003-001: EntryRouter 仅接受包含有效 task_ref 的执行请求
- FEAT-143 / AC-003-003: BypassBlocker 检测并阻断旁路执行尝试，返回规范错误码

## Dependencies
- {"task_id": "TASK-FEAT-143-001", "relation": "requires_specification"}

## Definition Of Done
- src/lee/qa/entry_router.py 实现完成
- src/lee/qa/bypass_blocker.py 实现完成
- 旁路检测规则 BYPASS-001~004 已实现
- 单元测试覆盖所有旁路场景
- TASK 文件已冻结

# Inputs

- TASK-FEAT-143-001 输出的执行入口规范
- Frozen Technical Architecture（FTA-FEAT-143-001）组件定义
- ArtifactManager 和 SSOTService 现有接口

# Processing

- 实现 EntryRouter.route() 异步方法，接收 ExecutionRequest 返回 ExecutionResult
- 实现 EntryRouter.validate_entry() 入口校验方法
- 实现 BypassBlocker.check() 旁路检测方法
- 实现 BypassBlocker.block() 阻断方法
- 实现 BYPASS-001（无 task_ref 直接调用）检测规则
- 实现 BYPASS-002（task 不归属 TESTPLAN）检测规则
- 实现 BYPASS-003（TESTPLAN 不归属 RELEASE）检测规则
- 实现 BYPASS-004（参数注入攻击）检测规则
- 集成 AuditLogger 记录阻断审计日志

# Outputs

- src/lee/qa/entry_router.py EntryRouter 核心组件
- src/lee/qa/bypass_blocker.py BypassBlocker 核心组件
- tests/qa/test_entry_router.py 单元测试
- tests/qa/test_bypass_blocker.py 单元测试

# Dependencies

- TASK-FEAT-143-001（规范定义）

# Non Goals

- 不涉及 ChainValidator 链路校验逻辑
- 不涉及实际测试执行引擎
- 不涉及 CLI 命令层
