---
id: EPIC-SRC-046-001
ssot_type: epic
title: 交付轴 workflow 化治理与发布闭环建设
status: frozen
version: v1
workflow_instance_id: SRC-046
parent_id: SRC-046
derived_from_ids:
- id: SRC-046
  version: v1
  required: true
source_refs:
- SRC-046#scope
owner: null
tags: []
properties:
  src_root_id: SRC-046
frozen_at: '2026-03-16T11:28:15.308344'
---

# 交付轴 workflow 化治理与发布闭环建设

## 目标

建立以 RELEASE 为起点的正式交付主链和发布闭环，使版本交付、计划承接、任务执行、证据回流与发布关闭能够按统一治理路径运行，消除对分散命令和兼容入口拼接的依赖

## 范围

- 建立 RELEASE 为起点的交付主链，确保交付对象绑定一致性和 scope 完整性
- 统一缺陷回流路径和发布关闭标准，形成可审计的治理闭环
- 明确 QA 与研发执行入口对正式交付主链的绑定关系，完成入口治理收口
- 区分 bugfix 的证据归属与执行承诺位置，将其重新纳入交付轴治理闭环
- 基于现有 RELEASE、DEVPLAN、TESTPLAN、TASK 对象基础进行 workflow 化治理
- 利用现有 release-cut、plan-derive、plan-check、release-check、release-close 等命令能力进行整合

## 非目标

- EPIC 设计本身不是目标，而是治理过程的产物
- 不涉及技术架构重构
- 不包含研发排期管理
- 不将 intake、workflow、schema 处理过程改写为正式业务目标
- 不重新发明 ADR-001 之外的三轴模型

## 成功标准

- 版本交付 workflow 覆盖率：100% 的正式发布版本通过交付主链完成交付
- 交付对象绑定一致性：交付链上各对象 (RELEASE/DEVPLAN/TESTPLAN/TASK) 的绑定关系可追溯、可验证
- 发布关闭标准统一：所有发布关闭操作遵循统一治理路径，无例外通道
- 缺陷回流路径清晰：100% 的 bugfix 可明确归属到对应交付版本并重新进入交付轴闭环
- QA 入口收口完成：QA 执行入口与正式交付主链建立明确绑定关系
