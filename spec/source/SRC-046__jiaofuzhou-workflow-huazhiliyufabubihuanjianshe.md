---
id: SRC-046
ssot_type: src
title: 交付轴 workflow 化治理与发布闭环建设
status: frozen
version: v1
workflow_instance_id: wf_task_772d5190
parent_id: null
derived_from_ids: []
source_refs:
- ADR-001
owner: null
tags: []
properties:
  contract_key: src
  identity_kind: ssot
frozen_at: '2026-03-15T16:15:53.304511'
---

# 交付轴 workflow 化治理与发布闭环建设

## 问题陈述

将当前“对象存在、命令存在、局部执行链存在”但尚未形成正式版本交付 workflow 的状态，收敛为一个稳定的源问题：建立以 RELEASE 为起点的正式交付主链和发布闭环，使版本交付、计划承接、任务执行、证据回流与发布关闭能够按统一治理路径运行，而不再依赖分散命令和兼容入口拼接完成。

## 目标用户

- LEE 内部负责版本发布治理、需求承接治理、研发执行治理、QA 交付治理与流程审计的产品/治理负责人

## 业务动因

当前交付轴缺少正式 workflow，导致版本交付仍依赖命令式创建、局部链路拼接和历史兼容入口，难以保证交付对象绑定一致性、scope 完整性、缺陷回流路径和发布关闭标准。先把交付轴主链 workflow 化，才能为后续 EPIC/FEAT 提供稳定来源，并收敛 QA 入口切换、bugfix 治理和兼容治理。

## 关键约束

- ADR-001 三轴治理方向与交付链硬治理约束
- 现有 RELEASE、DEVPLAN、TESTPLAN、TASK 对象基础
- 现有 release-cut、plan-derive、plan-check、release-check、release-close 等命令基础
- QA 已部分切换到 TASK -> TESTPLAN -> RELEASE 的现状，为入口治理收口提供迁移基础
- Python runtime 继续承担 workflow 执行编排责任

## Bridge Context

- governed_by_adrs: ADR-001
- change_scope: 将当前“对象存在、命令存在、局部执行链存在”但尚未形成正式版本交付 workflow 的状态，收敛为一个稳定的源问题：建立以 RELEASE 为起点的正式交付主链和发布闭环，使版本交付、计划承接、任务执行、证据回流与发布关闭能够按统一治理路径运行，而不再依赖分散命令和兼容入口拼接完成。
- expected_downstream_objects: EPIC, FEAT, RELEASE, TECH, TASK

## 验收与交付影响

- 交付轴形成一个正式 L1 release delivery DAG，并落地 release management、devplan management、testplan management 三条 L2 workflow
- 交付轴补齐 scope init、scope validate、scope freeze、recut audit、task pack、coverage check、commit gate、go/no-go、closeout 等核心 L3
- QA 与研发执行入口对正式交付主链的绑定关系明确，兼容入口仅保留受控过渡职责，不再与正式入口并行竞争
- bugfix 的证据归属与执行承诺位置被明确区分，bugfix 承诺必须重新进入交付轴治理闭环
- 本轮 raw_to_src 只形成一个聚焦的正式 SRC，后续可稳定拆解 release workflow、plan workflow、bugfix governance 与兼容治理收口

## 非目标

- EPIC 设计
- 技术架构
- 研发排期
- 将 intake、workflow、schema 处理过程改写为正式业务目标
- 重新发明 ADR-001 之外的三轴模型
