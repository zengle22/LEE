---
id: FEAT-SRC-DRAFT-REV-001-03
ssot_type: feat
title: Review Contract、Manifest 与 Trace 治理对齐
status: active
version: v1
parent_id: EPIC-078
derived_from_ids: []
source_refs:
- EPIC-078#scope
owner: null
tags: []
properties:
  contract_key: feat_003
  identity_kind: ssot
---

# Goal

补齐 reverse workflow 的 review contract、manifest 和 traceability 约束，使整条 SSOT 链可审查、可追溯、可验证。
# User Value

治理审查员可以按完整 SSOT 链检查 reverse 结果，避免只审 EPIC/FEAT 导致链路失真。
# Inputs

- EPIC-078#scope
- reverse pack outputs
- review and manifest contracts
# Processing

- 扩展 review contract 到 SRC / EPIC / FEAT / seeds / views / handoff
- 生成覆盖 reverse scope 的 manifest 与 trace index
- 校验 formal / seed / view 边界与 evidence 追踪闭环
# Outputs

- full-chain review contract
- reverse scope manifest
- trace index / evidence map
- governance validation summary
# Acceptance

- review contract 能覆盖整条 reverse SSOT 链
- manifest 清晰声明 formal / seed / view / handoff 边界
- trace index 能把 repo evidence、SRC、EPIC、FEAT 与下游 seeds/views 关联起来
# Acceptance Checks

## AC-03-01

- Scenario: 完整文档链校验
- Given: 文档链所有节点存在
- When: 调用校验接口
- Then: 返回完整性状态为通过
- Trace Hints: TASK, TESTSET, TECH

## AC-03-02

- Scenario: 缺失节点标识
- Given: 文档链存在缺失节点
- When: 调用校验接口
- Then: 返回缺失节点列表及位置
- Trace Hints: TASK, TESTSET, TECH

## AC-03-03

- Scenario: 性能指标验证
- Given: 大规模文档链数据
- When: 执行校验请求
- Then: 响应时间小于 500ms
- Trace Hints: TESTSET, TECH
# Dependencies

- FEAT-SRC-DRAFT-REV-001-02
# Non Goals

- 不引入新的治理层级或平行目录
- 不把 ADR 当成 SRC / EPIC / FEAT 的业务源对象
