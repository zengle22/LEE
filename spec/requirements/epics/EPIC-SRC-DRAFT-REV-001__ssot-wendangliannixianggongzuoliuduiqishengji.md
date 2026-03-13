---
id: EPIC-SRC-DRAFT-REV-001
ssot_type: epic
title: SSOT 文档链逆向工作流对齐升级
status: frozen
version: v1
parent_id: null
derived_from_ids: []
source_refs: []
owner: null
tags: []
properties:
  contract_key: epic
  identity_kind: ssot
frozen_at: '2026-03-13T20:55:42.403995'
---

epic_id: EPIC-SRC-DRAFT-REV-001
title: SSOT 文档链逆向工作流对齐升级
goal: 解决 reverse workflow 无法完整承接现行 SSOT 文档链的问题，实现正式对象物化与输出路径的规范对齐。
scope:
- 实现 SRC/EPIC/FEAT 正式对象的直接物化逻辑
- 约束 UI/TECH/TASK 等辅助对象仅产出 seed/view/handoff/index
- 强制输出路径对齐当前 canonical SSOT 目录结构
- 确保不新增平行 workflow key 以保持链路单一性
non_goals:
- 修改现行 SSOT 目录结构规范
- 变更 upstream SRC 定义标准
- 引入与文档链对齐无关的业务功能逻辑
success_metrics:
- 逆向工作流产出物 100% 符合 canonical SSOT 目录路径
- 正式对象物化覆盖率达成 100%
- 平行 workflow key 新增数为 0
priority: P1
feat_split_principles:
- 按对象正式性分级：正式对象（SRC/EPIC/FEAT）与辅助对象（UI/TECH 等）拆分
- 按产出物类型拆分：seed、view、handoff/index 独立实现
- 按工作流阶段拆分：逆向解析与正向物化逻辑解耦
ssot:
  identity_kind: ssot
  ssot_type: EPIC
