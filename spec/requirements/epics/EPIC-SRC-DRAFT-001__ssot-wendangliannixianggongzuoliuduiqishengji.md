---
id: EPIC-SRC-DRAFT-001
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
frozen_at: '2026-03-13T21:07:25.973205'
---

epic_id: EPIC-SRC-DRAFT-001
title: SSOT 文档链逆向工作流对齐升级
goal: 重构 reverse workflow 以完整承接现行 SSOT 文档链治理要求，确保 formal object 物化合规且输出路径对齐 canonical
  目录
scope:
- 实现 SRC 到 EPIC 再到 FEAT 的逆向映射逻辑
- 强制执行 formal object 仅物化 SRC/EPIC/FEAT 的规则
- 确保输出路径对齐 canonical SSOT 目录结构
- 为 UI/TECH 等非 formal object 仅生成 seed/view/handoff/index 产物
non_goals:
- 新增平行 workflow key
- 直接物化除 SRC/EPIC/FEAT 外的 formal object
- 为 UI/TECH/TASK 等生成除 seed/view/handoff/index 外的完整产物
- 修改与文档链治理无关的业务功能逻辑
success_metrics:
- 逆向工作流输出路径 100% 对齐 canonical SSOT 目录
- formal object 物化违规次数为零
- 治理审查员验证通过率 100%
priority: P0
feat_split_principles:
- 按物化对象类型拆分 (SRC/EPIC/FEAT)
- 按校验阶段拆分 (结构/内容/路径)
- 按集成节点拆分 (输入解析/输出生成)
ssot:
  identity_kind: ssot
  ssot_type: EPIC
