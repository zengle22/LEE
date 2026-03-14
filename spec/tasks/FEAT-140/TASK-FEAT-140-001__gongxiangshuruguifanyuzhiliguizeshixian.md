---
id: TASK-FEAT-140-001
ssot_type: task
title: 共享输入规范与治理规则实现
status: active
version: v1
parent_id: FEAT-140
derived_from_ids: []
source_refs:
- FEAT-140#delivery
owner: null
tags: []
properties:
  contract_key: task_epic_src_009_004
  identity_kind: ssot
---

# Objective

实现共享输入规范定义和治理规则文档

# Description

实现 Dev workflow 共享的输入规范定义和治理规则：
1. 共享输入规范: 基础字段 formal_ssot_id, source_refs, governing_adrs, repo_context；并明确 Feature Delivery L2 扩展字段 repo_frontend, repo_backend
2. 旧路径降级治理: deprecated 路径清单、标记规范、迁移指南
3. Bugfix 粒度控制规则: 默认规则、五同原则、batch 审批流程

## Acceptance Mapping
- FEAT-SRC-009-010 / AC-010-001: 旧路径治理文档冻结
- FEAT-SRC-009-010 / AC-010-002: Deprecated 路径清单完整性
- FEAT-SRC-009-010 / AC-010-004: 迁移指南完整性
- FEAT-140 / AC-011-001: 共享输入规范文档冻结
- FEAT-140 / AC-011-002: formal_ssot_id 规范完整性
- FEAT-SRC-009-012 / AC-012-001: Bugfix 粒度控制规则文档冻结
- FEAT-SRC-009-012 / AC-012-002: 默认规则明确性

## Dependencies
- TASK-EPIC-SRC-009-001

## Definition Of Done
- 共享输入规范 Schema 已创建并冻结
- 共享输入规范已文档化基础字段与 Feature Delivery L2 扩展字段
- Deprecated 路径清单 YAML 已创建
- 标记规范文档已创建
- 迁移指南文档已创建
- Bugfix 粒度控制规则文档已创建
- 输入验证 checklist 已创建
- 所有文档通过评审
