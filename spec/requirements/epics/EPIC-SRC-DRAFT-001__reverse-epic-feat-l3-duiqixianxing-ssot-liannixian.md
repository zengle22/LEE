---
id: EPIC-SRC-DRAFT-001
ssot_type: epic
title: reverse-epic-feat-l3 对齐现行 SSOT 链逆向升级
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
frozen_at: '2026-03-13T10:25:14.416104'
---

epic_id: EPIC-SRC-DRAFT-001
title: reverse-epic-feat-l3 对齐现行 SSOT 链逆向升级
goal: 实现 reverse workflow 对现行 SSOT 文档链的完整承接与逆向升级，确保形式化对象治理边界清晰。
scope:
- reverse-epic-feat-l3 工作流与现行 SSOT 链标准对齐
- 形式化对象仅直接物化 SRC / EPIC / FEAT
- 输出路径对齐当前 canonical SSOT 目录
- 支持产品经理、研发工程师、QA 工程师、治理审查员使用
non_goals:
- 新增平行 workflow key
- 直接物化 SRC / EPIC / FEAT 之外的 formal object
- 为 UI / TECH / TASK / TESTSET / TC / REPORT / BUG / EVI 生成除 seed、view、handoff/index
  外的产出
success_metrics:
- reverse workflow 输出路径与 canonical SSOT 目录 100% 一致
- 无未经授权的形式化对象物化行为
- 治理审查员验证通过率 100%
priority: P1
feat_split_principles:
- 按形式化对象类型拆分 (SRC, EPIC, FEAT)
- 按产物生成阶段拆分 (seed, view, handoff/index)
- 按用户角色权限边界拆分
ssot:
  identity_kind: ssot
  ssot_type: EPIC
  id: EPIC-SRC-DRAFT-001
  version: 1.0.0
