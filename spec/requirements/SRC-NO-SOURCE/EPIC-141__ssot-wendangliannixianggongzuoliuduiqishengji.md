---
id: EPIC-141
ssot_type: epic
title: SSOT 文档链逆向工作流对齐升级
status: frozen
version: v1
parent_id: null
derived_from_ids: []
source_refs: []
owner: null
tags: []
properties: {}
frozen_at: '2026-03-13T21:07:26.198275'
---

# SSOT 文档链逆向工作流对齐升级

## 目标

重构 reverse workflow 以完整承接现行 SSOT 文档链治理要求，确保 formal object 物化合规且输出路径对齐 canonical 目录

## 范围

- 实现 SRC 到 EPIC 再到 FEAT 的逆向映射逻辑
- 强制执行 formal object 仅物化 SRC/EPIC/FEAT 的规则
- 确保输出路径对齐 canonical SSOT 目录结构
- 为 UI/TECH 等非 formal object 仅生成 seed/view/handoff/index 产物

## 非目标

- 新增平行 workflow key
- 直接物化除 SRC/EPIC/FEAT 外的 formal object
- 为 UI/TECH/TASK 等生成除 seed/view/handoff/index 外的完整产物
- 修改与文档链治理无关的业务功能逻辑

## 成功标准

- 逆向工作流输出路径 100% 对齐 canonical SSOT 目录
- formal object 物化违规次数为零
- 治理审查员验证通过率 100%
