---
id: TASK-FEAT-101-001
ssot_type: task
title: src-to-epic workflow 重构与边界净化实现
status: frozen
version: v1
parent_id: FEAT-101
derived_from_ids: []
source_refs:
- FEAT-101#delivery
owner: null
tags: []
properties:
  contract_key: task_feat_101_001
  identity_kind: ssot
frozen_at: '2026-03-12T14:01:00.121542'
---

# Objective

重构 src-to-epic workflow，移除 raw input 适配逻辑，仅接受 SRC 格式输入

# Description

清理 src-to-epic 中的 raw-to-src 转换代码，实现 SRC 格式验证入口，确保拒绝 raw 格式并返回明确错误，代码行数减少 >= 20%

## Acceptance Mapping
- FEAT-101 / AC-008-002-01: SRC 格式输入验证：接受 SRC 并正常处理
- FEAT-101 / AC-008-002-02: Raw 格式输入拒绝：返回明确错误
- FEAT-101 / AC-008-002-03: 代码精简：相关代码行数减少 >= 20%

## Dependencies
- TASK-FEAT-100-001

## Definition Of Done
- raw-to-src 转换代码已移除
- SRC 格式验证入口实现
- 错误分类机制实现
- 代码审查完成
