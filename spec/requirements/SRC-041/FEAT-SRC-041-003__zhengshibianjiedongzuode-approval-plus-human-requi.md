---
id: FEAT-SRC-041-003
ssot_type: feat
title: 正式边界动作的 approval plus human_required 约束
status: frozen
version: v1
workflow_instance_id: feat-specs-epic-src-041-016-v1
parent_id: EPIC-SRC-041-016
derived_from_ids:
- id: EPIC-SRC-041-016
  version: v1
  required: true
source_refs:
- EPIC-SRC-041-016#scope
owner: null
tags: []
properties:
  contract_key: feat_003
  identity_kind: ssot
  src_root_id: SRC-041
frozen_at: '2026-03-15T05:28:24.292508'
---

# Goal

冻结 freeze、release、merge、risk acceptance 等正式边界动作只能表达为 purpose=approval 且 decision_mode=human_required 的治理规则，阻断 review 语义侵入正式放行场景。
# User Value

治理负责人能够稳定区分正式放行与普通评审，避免 freeze、release、merge、risk acceptance 等高风险动作继续借 review 语义绕过审批边界。
# Inputs

- 已冻结的 gate 双轴语义定义
- 正式边界动作清单：freeze、release、merge、risk acceptance
- 人工决策前置上下文强制化规则
- 现行 review 语义在正式放行场景的误用样本
# Processing

- 识别正式边界动作集合，并将其全部绑定到 purpose=approval。
- 将正式边界动作的 decision_mode 固定为 human_required，阻断自动或 review 语义替代。
- 定义 review 与 approval 的边界，明确 review 不构成正式放行。
- 输出可被 workflow、runtime 与审计共同消费的正式动作分类约束。
# Outputs

- 正式 FEAT 规格：正式边界动作的 approval / human_required 约束
- review 与 approval 的边界判定规则
- 正式动作违规分类的阻断条件
# Acceptance

- freeze、release、merge、risk acceptance 必须稳定映射为 purpose=approval 且 decision_mode=human_required。
- review 语义不得再表达正式放行动作。
- 任何正式边界动作若缺少 human_gate_context 或未落在 approval / human_required 组合内，均不能被视为合规定义。
# Acceptance Checks

## AC-FEAT-SRC-041-016-003-01

- Scenario: 正式边界动作被约束到审批语义
- Given: 存在一个 freeze、release、merge 或 risk acceptance 类 gate
- When: 规格系统校验该 gate 的分类
- Then: 校验结果要求 purpose=approval 且 decision_mode=human_required，否则判定为不合规
- Trace Hints: TASK, TESTSET, TECH

## AC-FEAT-SRC-041-016-003-02

- Scenario: review 无法表达正式放行
- Given: 有人尝试用 review 语义定义正式边界动作
- When: 该定义进入规格审核或运行时消费链路
- Then: 系统或审核规则明确拒绝该表达，并要求改为 approval + human_required
- Trace Hints: TASK, TESTSET, TECH
# Dependencies

- FEAT-SRC-041-016-001
- FEAT-SRC-041-016-002
# Non Goals

- 审批界面设计
- 跨团队排期
- 通用业务审批扩展
