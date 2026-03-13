---
id: TASK-FEAT-143-003
ssot_type: task
title: ChainValidator 与链路完整性校验实现
status: draft
version: v1
parent_id: FEAT-143
derived_from_ids: []
source_refs:
- FEAT-143#delivery
owner: null
tags: []
properties:
  contract_key: task_chain_validator_impl
  identity_kind: ssot
---

# ChainValidator 与链路完整性校验实现

# Objective

实现 RELEASE→PLAN→TASK 链路完整性校验器

# Description

实现 ChainValidator 组件，按渐进式顺序 (task→plan→release) 逐级校验执行路径完整性。包含 LRU 缓存策略 (60s TTL)、错误定位提示、Registry 不一致时降级策略。

## Acceptance Mapping
- FEAT-143 / AC-003-002: ChainValidator 验证 release_ref→testplan_ref→task_ref 链路完整且有效

## Dependencies
- {"task_id": "TASK-FEAT-143-001", "relation": "requires_specification"}
- {"task_id": "TASK-FEAT-143-002", "relation": "parallel_implementation"}

## Definition Of Done
- src/lee/qa/chain_validator.py 实现完成
- 渐进式校验 (task→plan→release) 已实现
- LRU 缓存策略已配置 (60s TTL)
- Registry 降级策略已实现
- 错误码 ERR-CHAIN-001~004 已注册
- TASK 文件已冻结

# Inputs

- TASK-FEAT-143-001 输出的执行入口规范
- Frozen Technical Architecture（FTA-FEAT-143-001）组件定义
- ArtifactManager 和 SSOTService 现有接口

# Processing

- 实现 ChainValidator.validate() 异步方法，接收 task_ref 返回 ChainValidationResult
- 实现 _validate_task() TASK 存在性和状态校验
- 实现 _validate_testplan() TESTPLAN 归属校验
- 实现 _validate_release() RELEASE 链路校验
- 实现 LRU 缓存层（60s TTL，max_size=1000）
- 实现 Registry 不一致检测（is_fresh() 检查）
- 实现降级策略（Registry 不可用时降级到直接读取 front matter）
- 实现渐进式错误提示（按 task→plan→release 顺序提示首个失败点）

# Outputs

- src/lee/qa/chain_validator.py ChainValidator 核心组件
- src/lee/qa/cache.py LRU 缓存工具类
- tests/qa/test_chain_validator.py 单元测试
- tests/qa/test_chain_validator_integration.py 集成测试

# Dependencies

- TASK-FEAT-143-001（规范定义）
- TASK-FEAT-143-002（并行实现 TASK）

# Non Goals

- 不涉及 EntryRouter 入口路由逻辑
- 不涉及实际测试执行
- 不涉及审计日志写入
