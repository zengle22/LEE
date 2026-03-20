---
id: TASK-FEAT-012-003-001
ssot_type: task
title: Kimi 执行器接口实现与工厂注册
status: frozen
version: v1
parent_id: FEAT-012-003
derived_from_ids: []
source_refs:
- FEAT-012-003#delivery
owner: null
tags: []
properties:
  contract_key: task_feat_012_003_001
  identity_kind: ssot
frozen_at: '2026-03-12T22:50:57.184192'
---

# Objective

实现 Kimi CLI 执行器、CLI 调用封装，并在 executor 工厂中完成注册

# Description

基于 canonical executor 架构实现 Kimi CLI 执行器类，参考 `ClaudeCodeExecutor` 的子进程调用方式封装本地 `kimi-cli --print` 执行，并在 executor 工厂中注册以支持别名 "kimi" 解析，确保 Kimi 进入与 `claude_code` 同类的 code executor 路由，而不是 `llm/qwen` profile 路由

## Acceptance Mapping
- FEAT-012-003 / AC-012-003-01: Kimi CLI 执行器具备 `kimi-cli --print` 调用能力并符合 code executor 契约
- FEAT-012-003 / AC-012-003-02: Kimi 执行器通过工厂可被正确实例化，支持别名 "kimi" 解析

## Prerequisites
- FEAT-012-001
- FEAT-012-002

## Observability
```yaml
execution_unit: task
log_scope: task-execution
audit_fields:
- run_id
- changed_files
- test_results
- evidence_refs
```

## Evidence Requirements
```yaml
required_refs:
- FEAT-012-003
- TECH-FEAT-012-003
review_required: true
```

## Rollback Strategy
```yaml
mode: revert
restore_targets:
- src/lee/orchestrator/execution/kimi_code_executor.py
- src/lee/orchestrator/execution/executors.py
```

## Definition Of Done
- Kimi CLI executor 封装 `kimi-cli --print` 调用
- ExecutorFactory 注册 Kimi 执行器并支持 "kimi" 别名
- 单元测试通过，验证 CLI 调用参数与错误处理
- 工厂注册测试通过，验证别名解析正确
- TASK 文件已冻结
