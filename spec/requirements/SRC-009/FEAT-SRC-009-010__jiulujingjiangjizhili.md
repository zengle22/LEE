---
id: FEAT-SRC-009-010
ssot_type: feat
title: 旧路径降级治理
status: frozen
version: v1
parent_id: EPIC-SRC-009
derived_from_ids:
- id: EPIC-SRC-009
  version: v1
source_refs:
- EPIC-SRC-009#scope
owner: null
tags: []
properties:
  contract_key: FEAT-SRC-009-010
  identity_kind: ssot
  materialized_from_workflow: wf_task_de4f2645
  priority: P1
  delivery_slice: governance
  lifecycle_status: draft
  derived_object_expectations:
    qa_seed_required: true
    testset_required: true
    task_required: true
  input_contract:
    required_artifacts:
    - Feature Delivery L2 定义文档
    - Bugfix Delivery L2 定义文档
    - 历史 workflow 路径清单
    required_fields:
    - formal_ssot_id
    - source_refs
    - governing_adrs
    - deprecated_paths
    consumption_rules:
    - 旧路径降级必须在 L2 定义冻结后进行
    - deprecated_paths 清单必须完整
    - 迁移指南必须清晰可执行
---

# Goal

明确旧路径的 deprecated 状态，引导团队使用新的 L2 主入口，确保治理体系平稳过渡
# User Value

明确旧路径（如 phase-openspec-flow）的 deprecated 状态，引导团队使用新的 L2 主入口，确保治理体系平稳过渡
# Inputs

- {'formal_ssot_id': 'L2 工作流定义文档 ID'}
- {'source_refs': '历史路径引用'}
- {'governing_adrs': '迁移决策 ADR'}
- {'deprecated_paths': '需标记 deprecated 的路径清单'}
# Input Contract

required_artifacts:
- Feature Delivery L2 定义文档
- Bugfix Delivery L2 定义文档
- 历史 workflow 路径清单
required_fields:
- formal_ssot_id
- source_refs
- governing_adrs
- deprecated_paths
consumption_rules:
- 旧路径降级必须在 L2 定义冻结后进行
- deprecated_paths 清单必须完整
- 迁移指南必须清晰可执行
# Processing

- 整理需标记 deprecated 的路径清单
- 定义标记规范（README、代码注释、workflow 文件头部标记）
- 编写迁移指南（从旧路径到新 L2 入口的映射）
- 定义旧路径活跃度监控机制
- 更新新入口 README/WORKFLOWS
# Outputs

- 旧路径降级治理文档
- Deprecated 路径清单
- 标记规范文档
- 迁移指南
- 活跃度监控机制定义
- 更新的 README/WORKFLOWS
# Acceptance

- 旧路径治理文档已冻结
- Deprecated 路径清单完整
- 标记规范覆盖 README、代码注释、workflow 文件头部
- 迁移指南包含从旧路径到新 L2 入口的映射
- 活跃度监控机制定义完整
- 新入口 README/WORKFLOWS 已更新
- 不强制迁移历史任务
# Acceptance Checks

- id: AC-010-001
  scenario: 旧路径治理文档冻结
  given: 旧路径降级治理设计完成
  when: 提交评审并通过
  then: 文档标记为 frozen 状态
  trace_hints:
  - TASK
  - TECH
- id: AC-010-002
  scenario: Deprecated 路径清单完整性
  given: 旧路径治理文档已冻结
  when: 检查路径清单
  then: 包含所有需标记 deprecated 的路径（如 phase-openspec-flow）
  trace_hints:
  - TECH
  - TESTSET
- id: AC-010-003
  scenario: 标记规范可执行性
  given: 旧路径治理设计完成
  when: 检查标记规范
  then: 覆盖 README、代码注释、workflow 文件头部三类标记位置
  trace_hints:
  - TECH
- id: AC-010-004
  scenario: 迁移指南完整性
  given: 旧路径治理设计完成
  when: 检查迁移指南
  then: 提供从旧路径到新 L2 入口的清晰映射关系
  trace_hints:
  - TECH
  - TESTSET
# Dependencies

- EPIC-SRC-009
- FEAT-SRC-009-001
- FEAT-SRC-009-002
# Non Goals

- 重写历史 workflow 文件
- 强制迁移历史任务
- 删除旧路径文件
