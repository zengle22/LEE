---
id: FEAT-139
ssot_type: feat
title: 旧路径降级治理
status: frozen
version: v1
parent_id: EPIC-SRC-009
derived_from_ids: []
source_refs:
- EPIC-SRC-009#scope
owner: null
tags: []
properties:
  contract_key: feat_010
  identity_kind: ssot
frozen_at: '2026-03-12T19:47:01.869899'
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
# Acceptance

- 旧路径治理文档已冻结
- Deprecated 路径清单完整
- 标记规范覆盖 README、代码注释、workflow 文件头部
- 迁移指南包含从旧路径到新 L2 入口的映射
- 活跃度监控机制定义完整
# Acceptance Checks

## AC-010-001

- Scenario: 旧路径治理文档冻结
- Given: 旧路径降级治理设计完成
- When: 提交评审并通过
- Then: 文档标记为 frozen 状态
- Trace Hints: TASK, TECH

## AC-010-002

- Scenario: Deprecated 路径清单完整性
- Given: 旧路径治理文档已冻结
- When: 检查路径清单
- Then: 包含所有需标记 deprecated 的路径（如 phase-openspec-flow）
- Trace Hints: TECH, TESTSET

## AC-010-003

- Scenario: 标记规范可执行性
- Given: 旧路径治理设计完成
- When: 检查标记规范
- Then: 覆盖 README、代码注释、workflow 文件头部三类标记位置
- Trace Hints: TECH

## AC-010-004

- Scenario: 迁移指南完整性
- Given: 旧路径治理设计完成
- When: 检查迁移指南
- Then: 提供从旧路径到新 L2 入口的清晰映射关系
- Trace Hints: TECH, TESTSET
# Dependencies

- EPIC-SRC-009
- FEAT-SRC-009-001
- FEAT-SRC-009-002
# Non Goals

- 重写历史 workflow 文件
- 强制迁移历史任务
- 删除旧路径文件
