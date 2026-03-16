---
id: EPIC-SRC-041-016
ssot_type: epic
title: ADR-017 Gate 治理语义归一化与人工审批上下文统一治理
status: frozen
version: v1
workflow_instance_id: ADR-017
parent_id: SRC-041
derived_from_ids:
- id: SRC-041
  version: v1
  required: true
source_refs:
- SRC-041
- ADR-017
owner: null
tags: []
properties:
  src_root_id: SRC-041
frozen_at: '2026-03-15T04:31:05.460597'
---

# ADR-017 Gate 治理语义归一化与人工审批上下文统一治理

## 目标

在 LEE 治理语义冻结前建立统一、可审计、可度量的 gate 目标模型，将 gate 职责边界归一化为 purpose、参与方式归一化为 decision_mode，并把 human_gate_context 固定为所有人工决策场景的强制前置物，使治理负责人、workflow 设计者、runtime/CLI 维护者与人类审批者能够在同一治理语言下判断 why blocked、决策对象、证据、风险与后续动作。

## 范围

- 统一 gate 的职责语义与决策模式，收敛 Auto Gate/Review Gate/Approval Gate、auto_check/human_review/human_approval、human_gate 三套混合分类到 purpose 与 decision_mode 双轴模型。
- 将 human_gate_context 设为所有 decision_mode=human_required 或由自动检查升级到人工决策场景的强制前置物，确保审批前存在可消费的决策上下文。
- 稳定约束 freeze、release、merge、risk acceptance 等正式边界动作只能表达为 approval + human_required，阻断 review 对正式放行语义的污染。
- 统一待审批 gate 在 CLI list/show/decide 阶段的最小可判断信息与人工 gate 决策结果输出，确保审批者可直接看到 purpose、decision_mode、subject、why_now、evidence 和 next_action。
- 为后续 raw input intake、SRC normalization、spec、workflow 模板、runtime、CLI、trace 与审计收敛提供稳定的治理前置边界与统一 gate_result 目标模型。

## 非目标

- 技术架构设计与具体实现方案定版。
- 数据库最终列名、存储结构或一次性历史数据迁移方案。
- 前端 UI 样式、交互视觉设计或终端展现美化。
- 研发排期、资源拆分或跨团队执行计划。
- 脱离 gate 治理边界的通用业务功能扩展。

## 成功标准

- 100% 新增或收敛后的 gate 定义显式声明 purpose 与 decision_mode。
- 100% decision_mode=human_required 或升级到人工决策的 gate 在可审批前生成 human_gate_context。
- 100% 待审批 gate 在 list 阶段可见 purpose、decision_mode、subject 与 why_now 摘要。
- 100% 人工 gate 决策结果输出统一 gate_result，并包含 subject_refs、evidence_refs 与 next_action。
- 100% freeze、release、merge、risk acceptance 等正式边界动作稳定映射为 approval + human_required，不再借由 review 表达。
