---
id: TASK-FEAT-134-001
ssot_type: task
title: L3 阶段模板定义实现
status: active
version: v1
parent_id: FEAT-134
derived_from_ids: []
source_refs:
- FEAT-134#delivery
owner: null
tags: []
properties:
  contract_key: task_epic_src_009_003
  identity_kind: ssot
---

# Objective

实现五个 L3 阶段的标准化模板定义

# Description

实现 L2 工作流引用的五个 L3 阶段模板：
1. Contract Design L3: API/数据/事件契约设计阶段
2. Backend Development L3: TDD 后端开发阶段
3. Frontend Development L3: TDD 前端开发阶段
4. Integration L3: 集成验证阶段
5. Evidence Pack L3: 证据打包阶段
每个模板包含输入规范、任务清单、输出规范、完成标准、交接规则。

## Acceptance Mapping
- FEAT-134 / AC-005-001: Contract Design 阶段文档冻结
- FEAT-134 / AC-005-002: 阶段任务清单覆盖三类设计任务
- FEAT-SRC-009-006 / AC-006-001: Backend Development 阶段文档冻结
- FEAT-SRC-009-006 / AC-006-002: UTDD 循环定义完整性
- FEAT-SRC-009-007 / AC-007-001: Frontend Development 阶段文档冻结
- FEAT-SRC-009-008 / AC-008-001: Integration 阶段文档冻结
- FEAT-SRC-009-009 / AC-009-001: Evidence Pack 阶段文档冻结

## Dependencies
- TASK-EPIC-SRC-009-001

## Definition Of Done
- 5 个 L3 阶段模板 YAML 已创建并冻结
- 每个模板包含输入规范、任务清单、输出规范
- 每个模板定义完成标准和交接规则
- 所有模板通过 JSON Schema 验证
- L3 模板 README 使用文档已提供
