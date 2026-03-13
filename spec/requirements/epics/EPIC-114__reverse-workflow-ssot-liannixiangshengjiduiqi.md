---
id: EPIC-114
ssot_type: epic
title: Reverse Workflow SSOT 链逆向升级对齐
status: frozen
version: v1
parent_id: null
derived_from_ids: []
source_refs: []
owner: null
tags: []
properties: {}
frozen_at: '2026-03-13T14:07:35.645768'
---

# Reverse Workflow SSOT 链逆向升级对齐

## 目标

升级 reverse workflow 使其能够完整承接并逆向对齐现行 SSOT 文档链，确保从 FEAT 到 EPIC 到 SRC 的逆向追溯能力与现行 SSOT 目录结构完全一致。

## 范围

- 扩展 reverse workflow 以支持现行 SSOT 链中所有 formal object (SRC/EPIC/FEAT) 的逆向物化
- 实现 reverse workflow 输出路径与当前 canonical SSOT 目录结构的严格对齐
- 为 UI/TECH/TASK/TESTSET/TC/REPORT/BUG/EVI 等非 formal object 提供 seed、view、handoff/index 级别的逆向物化支持
- 确保 reverse workflow 不引入新的平行 workflow key
- 建立 reverse workflow 与现行 SSOT 链的完整双向映射关系

## 非目标

- 新增平行 workflow key 或改变现有 workflow 架构
- 直接物化 SRC/EPIC/FEAT 之外的 formal object
- 完整物化 UI/TECH/TASK/TESTSET/TC/REPORT/BUG/EVI 等非 formal object 的完整内容
- 改变现行 SSOT 目录结构或 canonical 路径规则
- 扩展 reverse workflow 到业务功能领域（如用户认证、支付等）

## 成功标准

- reverse workflow 能够 100% 覆盖现行 SSOT 链中所有 SRC/EPIC/FEAT 的逆向物化
- reverse workflow 输出路径与 canonical SSOT 目录的一致性达到 100%
- 非 formal object 的逆向物化（seed/view/handoff/index）覆盖率达到 95% 以上
- reverse workflow 执行时间在现有基础上增加不超过 20%
- 治理审查员能够通过 reverse workflow 完整追溯任一 FEAT 到其源头 SRC
