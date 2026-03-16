---
id: EPIC-189
ssot_type: epic
title: 验证 raw_to_src 到 src_to_epic 数据传递修复
status: frozen
version: v1
workflow_instance_id: PGC-BUG-20260316-001
parent_id: null
derived_from_ids: []
source_refs: []
owner: null
tags: []
properties: {}
frozen_at: '2026-03-16T00:42:33.310855'
---

# 验证 raw_to_src 到 src_to_epic 数据传递修复

## 目标

验证 product.main 工作流中 raw_to_src 到 src_to_epic 的数据传递修复，确保新生成的 SRC 能够正确传递给 src_to_epic 阶段，且 EPIC 的 source_refs 和 ssot.parent 正确指向该 SRC，保障后续交付质量。

## 范围

- 运行 product.main 工作流执行验证，确保 raw_to_src 生成的新 SRC 能被 src_to_epic 正确消费
- 检查生成的 SRC 和 EPIC 文件字段一致性，验证 source_freeze_ref 与 source_id 匹配
- 验证 EPIC.source_refs 包含正确的 SRC ID 且 ssot.parent 指向正确 SRC
- 确认三个验收标准全部通过：数据一致、工作流可完整跑通、无数据不一致问题

## 非目标

- EPIC 设计
- 技术架构修改
- 研发排期
- intake/workflow/schema 处理过程改写为正式业务目标

## 成功标准

- product.main 工作流可完整跑通 raw_to_src 到 src_to_epic 的数据传递
- 生成的 SRC 和 EPIC 文件字段一致性验证通过（source_freeze_ref 与 source_id 匹配）
- EPIC.source_refs 包含正确的 SRC ID 且 ssot.parent 指向正确 SRC
- 三个验收标准全部通过且无数据不一致问题
- 验证成本控制在 1-2 人时内完成
