---
id: EPIC-113
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
frozen_at: '2026-03-13T13:50:20.661943'
---

# reverse-epic-feat-l3 对齐现行 SSOT 链逆向升级

## 目标

构建逆向工作流能力，使其能够完整承接并生成符合现行 SSOT 规范的文档链，确保 SRC/EPIC/FEAT 对象物化路径与 canonical 目录一致。

## 范围

- 逆向工作流引擎对现行 SSOT 链的兼容性改造
- SRC/EPIC/FEAT formal object 的直接物化逻辑实现
- UI/TECH/TASK 等辅助对象的 seed/view/handoff/index 产物标准化
- 输出路径与 canonical SSOT 目录的对齐验证

## 非目标

- 新增平行 workflow key
- 物化 SRC / EPIC / FEAT 之外的 formal object
- 为 UI / TECH / TASK / TESTSET / TC / REPORT / BUG / EVI 生产除 seed、view、handoff/index 之外的产物
- 偏离当前 canonical SSOT 目录结构的存储方案

## 成功标准

- 逆向工作流生成的 SSOT 文档链审计通过率 100%
- SRC/EPIC/FEAT 对象物化路径与规范一致性 100%
- 非标准产物生成次数降为 0
