---
id: TECH-FEAT-SRC-012
ssot_type: tech
title: tech_design
status: frozen
version: v1
parent_id: FEAT-SRC-009-007
derived_from_ids: []
source_refs: []
owner: null
tags: []
properties:
  contract_key: tech_spec
  identity_kind: ssot
frozen_at: '2026-03-13T00:58:15.753220'
---

rollback_paths:
  contract_violation:
    trigger: Self-Check 检测到响应结构与 Contract 不匹配
    action: 回滚至 Contract Design 阶段，重新冻结 API Contract
    blocking: true
  type_mismatch:
    trigger: 运行时类型错误 (TypeScript 编译通过但运行时报错)
    action: 回退至 Type Generation 阶段，修正类型生成器
    blocking: true
  coverage_threshold_not_met:
    trigger: 测试覆盖率 < 80%
    action: 回退至 UT 编写阶段，补充测试用例
    blocking: true
  integration_failure:
    trigger: 前后端集成测试失败
    action: '- 如为契约结构问题 → 回滚至 Contract Design

      - 如为实现问题 → 回滚至 Backend/Frontend Dev

      '
    blocking: false
  smoke_gate_failure:
    trigger: Smoke Gate 测试失败
    action: 最高优先级回滚，禁止绕过，需人类 Gate 审批
    blocking: true
    requires_human_approval: true
