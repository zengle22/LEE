---
id: FEAT-SRC-DRAFT-REV-001-04
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
  contract_key: feat_004
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

## AC-04-01

- Scenario: 缺失字段识别
- Given: 存在历史数据且部分元数据缺失
- When: 运行扫描脚本
- Then: 输出缺失字段清单
- Trace Hints: TASK, TESTSET, TECH

## AC-04-02

- Scenario: 数据补全执行
- Given: 缺失字段清单已生成
- When: 执行补全任务
- Then: 缺失字段被填充且符合 schema
- Trace Hints: TASK, TESTSET, TECH

## AC-04-03

- Scenario: 补全后验证
- Given: 数据补全完成
- When: 调用完整性校验接口
- Then: 验证通过且无阻塞
- Trace Hints: TASK, TESTSET, TECH

## AC-04-04

- Scenario: 日志与回滚
- Given: 补全任务执行完毕
- When: 查询操作日志
- Then: 日志完整且包含回滚方案
- Trace Hints: TASK, TESTSET, TECH
# Dependencies

- FEAT-SRC-DRAFT-REV-001-03
# Non Goals

- 不引入新的治理层级或平行目录
- 不把 ADR 当成 SRC / EPIC / FEAT 的业务源对象
