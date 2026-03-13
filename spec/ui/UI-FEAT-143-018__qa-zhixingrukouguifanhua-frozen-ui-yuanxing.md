---
id: UI-FEAT-143-018
ssot_type: ui
title: QA 执行入口规范化 - Frozen UI 原型
status: active
version: v1
parent_id: FEAT-143
derived_from_ids: []
source_refs: []
owner: null
tags: []
properties:
  contract_key: ui
  identity_kind: ssot
---

design_specs:
  core_paths:
  - 标准执行入口路径：RELEASE → PLAN → TASK → EXECUTION（含 6 个校验节点）
  - 旁路阻断路径：旁路检测 → 阻断确认 → 审计记录 → 返回错误（4 类旁路场景）
  - 审计查询路径：查询入口 → 过滤条件 → 数据检索 → 结果展示（6 个查询维度）
  interaction_principles:
  - 'UIP-001: 单一入口原则 - 所有测试执行必须通过 TESTPLAN.TASK.execute() 触发'
  - 'UIP-002: 链路完整原则 - 必须验证 RELEASE→PLAN→TASK 三级引用链路'
  - 'UIP-003: 显式拒绝原则 - 旁路请求必须明确拒绝并返回规范错误码'
  - 'UIP-004: 审计透明原则 - 每次执行的入口来源、路径链、时间戳、用户必须可追溯'
  - 'UIP-005: 渐进校验原则 - 校验失败时按 task→plan→release 顺序逐级提示'
  - 'UIP-006: 静默失败原则 - 阻断旁路时返回友好错误，不暴露内部实现细节'
  key_states:
  - 'STATE-001: 执行请求入口解析 - 解析 CLI 命令参数，提取 task_ref'
  - 'STATE-002: TASK 有效性校验 - 验证 TASK 存在性、状态、归属'
  - 'STATE-003: PLAN 归属校验 - 验证 TASK 归属的 TESTPLAN'
  - 'STATE-004: RELEASE 链路校验 - 验证 PLAN 归属的 RELEASE'
  - 'STATE-005: 旁路执行阻断 - 检测并阻断非规范入口'
  - 'STATE-006: 审计记录 - 写入审计日志，生成 execution_id 和 audit_ref'
  - 'STATE-007: 执行引擎分发 - 路由到 ExecutionEngine，跟踪执行进度'
  edge_cases:
  - 'EDGE-001: 自动补全场景 - 用户仅提供 task_ref 时自动推导完整链路'
  - 'EDGE-002: 参数冲突场景 - 用户指定参数与自动推导结果冲突时的处理'
  - 'EDGE-003: 并发执行场景 - 同一 TASK 并发执行时分配独立 execution_id'
  - 'EDGE-004: 网络异常场景 - 执行中断时保存进度支持恢复'
  - 'EDGE-005: 权限不足场景 - 用户无执行权限时返回授权提示'
  - 'EDGE-006: Registry 同步延迟场景 - 检测到 Registry 过期时自动刷新'
metadata:
  is_frozen: true
  contract_id: FUIP-20260313-005
  frozen_at: '2026-03-13'
  feat_ref: FEAT-143
  review_status: approved
  reviewer: Human Reviewer
  reviewed_at: '2026-03-13T12:00:00+08:00'
