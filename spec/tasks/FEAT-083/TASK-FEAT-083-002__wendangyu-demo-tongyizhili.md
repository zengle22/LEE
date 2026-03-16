---
id: TASK-FEAT-083-002
ssot_type: task
title: 文档与 Demo 统一治理
status: frozen
version: v1
parent_id: FEAT-083
derived_from_ids: []
source_refs:
- FEAT-083#delivery
owner: null
tags: []
properties:
  contract_key: task_feat_083_002
  identity_kind: ssot
frozen_at: '2026-03-12T19:26:45.197825'
---

# Objective

更新文档站点和 Demo 示例，确保与 CLI Help 分组一致，统一传递 workflow-first 治理理念

# Description

重构 README.md Getting Started 章节，更新 docs/guides/user/ 用户指南，修改 demo.py 使用 lee adr new / lee epic new / lee feat new 等 workflow-first 命令，更新测试文件命名和描述

## Acceptance Mapping
- FEAT-083 / AC-004-002: 文档站点 Getting Started 章节优先展示 workflow-first 入口
- FEAT-083 / AC-004-003: Demo 示例使用 lee adr new / lee epic new / lee feat new 命令
- FEAT-083 / AC-004-001: 测试用例命名和描述统一使用 workflow-first 术语

## Dependencies
- TASK-FEAT-083-001

## Definition Of Done
- README.md Getting Started 章节重构完成
- Demo 示例使用 workflow-first 命令
- 测试文件命名符合规范
- 文档与 CLI help 输出保持一致
- 文档审查通过
- TASK 文件已冻结
