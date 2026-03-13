---
id: FEAT-SRC-DRAFT-REV-001-01
ssot_type: feat
title: Reverse Pack 主链升级与 formal object 边界固化
status: active
version: v1
parent_id: EPIC-078
derived_from_ids: []
source_refs:
- EPIC-078#scope
owner: null
tags: []
properties:
  contract_key: feat_001
  identity_kind: ssot
---

# Goal

升级 core.reverse-epic-feat，使其从 repo evidence 逆向产出 SRC/EPIC/FEAT，并明确 formal object 只直物化这三类对象。
# User Value

产品和治理侧可以得到与现行 SSOT 主链一致的 reverse pack，而不是停留在 EPIC/FEAT-only 输出。
# Inputs

- EPIC-078#scope
- ADR-016 decision constraints
- repo evidence manifest
# Processing

- 解析 reverse workflow 的 repo evidence 与 ADR 约束
- 生成并串联 SRC reverse pack、EPIC、FEAT 三类 formal object
- 校验 formal object 物化边界仅覆盖 SRC / EPIC / FEAT
# Outputs

- SRC reverse pack
- EPIC formal object
- FEAT formal object bundle
- formal object boundary report
# Acceptance

- reverse workflow 能完整产出 SRC / EPIC / FEAT 三段 formal object
- 不直接 freeze UI / TECH / TASK / TESTSET / TC / REPORT / BUG / EVI
- 所有 formal object 都保留对上游 evidence 与 ADR 约束的追溯
# Acceptance Checks

## AC-01-01

- Scenario: 配置合法映射关系
- Given: 用户拥有配置权限且节点与类型存在
- When: 提交映射配置请求
- Then: 系统保存配置并返回成功状态
- Trace Hints: TASK, TESTSET, TECH

## AC-01-02

- Scenario: 配置非法映射关系
- Given: 用户提交不存在的节点 ID
- When: 提交映射配置请求
- Then: 系统拒绝请求并返回特定错误码
- Trace Hints: TASK, TESTSET, TECH

## AC-01-03

- Scenario: 工作流实例读取配置
- Given: 映射配置已保存
- When: 创建工作流实例
- Then: 实例正确加载节点与文档类型映射
- Trace Hints: TASK, TESTSET, TECH
# Dependencies

- None
# Non Goals

- 不替代现有正向 product / qa 正式治理流程
- 不新增平行 workflow key
