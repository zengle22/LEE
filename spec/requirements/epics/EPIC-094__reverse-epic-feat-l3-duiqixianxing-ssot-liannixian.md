---
id: EPIC-094
ssot_type: epic
title: reverse-epic-feat-l3 对齐现行 SSOT 链逆向升级
status: frozen
version: v1
parent_id: null
derived_from_ids: []
source_refs: []
owner: null
tags: []
properties: {}
frozen_at: '2026-03-13T13:15:03.366395'
---

# reverse-epic-feat-l3 对齐现行 SSOT 链逆向升级

## 目标

构建能够完整承接现行 SSOT 文档链的逆向工作流，确保 SRC/EPIC/FEAT 正式对象物化与 canonical 目录严格对齐，消除文档链断裂风险。

## 范围

- 实现 SRC/EPIC/FEAT 正式对象的直接物化逻辑
- 建立 UI/TECH/TASK 等辅助对象的 seed/view/handoff 生成机制
- 重构输出路径以对齐当前 canonical SSOT 目录结构
- 集成逆向升级流程至现有 workflow 引擎

## 非目标

- 新增平行 workflow key
- 物化 SRC/EPIC/FEAT 之外的 formal object
- 完整物化 UI/TECH/TASK/TESTSET/TC/REPORT/BUG/EVI 对象
- 变更现有 SSOT 身份认证或用户管理体系

## 成功标准

- 逆向工作流对现行 SSOT 文档链覆盖率达成 100%
- 生成产物路径与 canonical SSOT 目录合规率 100%
- 文档链维护人工映射成本降低 80%
