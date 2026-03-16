---
id: SRC-041
ssot_type: src
title: ADR-017 Gate 治理目标与价值分析
status: frozen
version: v1
workflow_instance_id: wf_task_f9958f64
parent_id: null
derived_from_ids: []
source_refs: []
owner: null
tags: []
properties:
  contract_key: src
  identity_kind: ssot
frozen_at: '2026-03-15T04:05:17.953905'
---

contract_type: product-goal-contract
contract_version: 1.0.0
contract_info:
  contract_id: PGC-ADR-017-V1
  title: ADR-017 Gate 治理目标与价值分析
  version: v1
  created_at: '2026-03-14T19:52:52.1516764Z'
  updated_at: '2026-03-14T19:52:52.1516764Z'
  status: DRAFT
requirement_overview:
  description: 将 ADR-017 中关于 gate 职责语义、决策模式和人工审批上下文的原始治理要求，归一化为可执行的产品目标输入，解决当前 LEE
    在 gate 分类、审批边界和 CLI 审批上下文上的混乱问题，为后续 raw input intake 与 SRC normalization 提供稳定前置分析。
  target_users: 治理负责人、workflow 设计者、runtime/CLI 维护者、需要执行 review/approval 的人类审批者
  context: 当前仓库同时存在 Auto Gate/Review Gate/Approval Gate、auto_check/human_review/human_approval、human_gate
    三套未完全对齐的语义，导致 review 与 approval 边界模糊、人工 gate 缺少可审批上下文、freeze 与 review 污染。ADR-017
    的核心是先统一目标语义，再约束人机决策交互。
  expected_timeline: 作为治理语义冻结前置项，应在后续 spec、workflow 模板与 CLI 收敛前完成确认。
key_designs:
  core_goal:
    primary_goal:
      description: 建立一套可审计、可度量、可被人机共同消费的 gate 目标模型，将 gate 的职责边界归一化为 purpose，将参与方式归一化为
        decision_mode，并强制所有人工决策场景先生成 human_gate_context。
      rationale: 先归一化职责和模式，才能稳定判断一个 gate 审什么、谁负责、何时需要人、决策后会带来什么后果；否则 runtime、CLI、trace
        和治理审计都会持续扩散兼容语义，形成高成本和高误判。
      metrics:
      - 100% 新增或收敛后的 gate 定义显式声明 purpose 与 decision_mode
      - 100% decision_mode=human_required 或升级到人工的 gate 生成 human_gate_context
      - 100% 待审批 gate 在 list 阶段可见 purpose、decision_mode、subject 与 why_now 摘要
      - 100% human gate 决策结果输出统一 gate_result，并包含 subject_refs、evidence_refs 与 next_action
      success_criteria:
      - review 与 approval 在治理语义上不再共用同一分类轴
      - freeze、release、merge、risk acceptance 被稳定约束为 approval + human_required
      - 审批者在不翻源码的前提下可通过 CLI 理解 why blocked、what you are deciding、evidence 和 next actions
      - reject、revise、flag 的后果在 gate 与 workflow 状态机上可被一致预览和审计
    secondary_goals:
    - description: 降低历史 gate 语义向新模型迁移时的歧义和重复兼容成本
      priority: 2
    - description: 为 downstream workflow、trace、审计和 freeze 引用提供稳定输入
      priority: 3
    confirmation:
      status: pending
      questions:
      - question: 是否确认 approval 在默认治理模型下只允许 human_required，且不接受 auto approval 作为正式主路径？
        answered: false
      - question: 是否确认 human_gate_context 是所有人工 gate 的强制前置物，而不是 CLI 可选增强项？
        answered: false
      feedback: 需要治理 owner 对默认组合和人工审批下限达成明确确认。
  value_chain:
    user_need:
      description: 审批者和治理执行者需要在最短路径内判断当前 gate 的职责、对象、证据、风险和决策后果，避免将质量审阅误当作正式放行，也避免在缺乏上下文时盲目点击继续。
      validation: 原始输入明确指出当前 pending gate 只能看到少量 DB 字段，无法知道为何触发、审什么对象、证据在哪里、决策会造成什么影响。
    product_feature:
      description: 提供基于 purpose + decision_mode 的统一 gate 归类方式、统一 gate_result 输出，以及对人工决策强制产出的
        human_gate_context 与上下文驱动 CLI 决策入口。
      validation: ADR-017 已冻结最小字段、允许组合、决策语义、CLI 入口和状态预览规则，可直接作为产品能力抽象。
    direct_value:
      description: 减少审批误判、职责越权和人工 gate 卡死；让 review、approval、freeze、rewind、spawn 等关键动作具备一致语义和可审计记录。
      validation: 若 list/show/decide 输出包含职责、模式、subject、evidence、next_action，审批者可以完成责任判断，不再依赖猜测。
    business_impact:
      description: 提升 LEE 治理流程的可信度和审计闭环质量，降低因 gate 语义混乱导致的返工、错误放行和流程阻塞，从而提升 workflow
        运行稳定性与组织责任清晰度。
      validation: review 与 approval 分离后，freeze 等正式边界不再被审阅通过偷换；统一状态机可减少 runtime 和 CLI
        的兼容分叉。
    strategic_significance:
      description: 这是 LEE 人机协同治理的基础抽象层，决定后续 spec、workflow、runtime、CLI、trace、审计和 freeze
        引用能否使用同一套语言描述治理边界。
      validation: ADR-017 明确替代 ADR-005 的单轴分类冲突，并要求后续实现按统一语义逐步收敛，说明其属于基础治理能力而非局部功能优化。
    explanation: 价值链先从审批者的可判断性出发，再落到统一能力模型，最终服务于治理可信度、审计闭环和后续系统收敛。
  priority:
    scores:
      user_value:
        score: 90
        rationale: 直接解决当前人工 gate 不可审批、review/approval 混淆、freeze 污染等高频高痛问题。
      industry:
        score: 85
        rationale: 对任何需要 human-in-the-loop、审计追踪和责任边界的治理型工作流都具有通用价值。
      efficiency:
        score: 82
        rationale: 统一语义后可减少 runtime、CLI、trace、模板层的重复兼容与人工解释成本，但前期需要收敛现有混合语义。
      cost:
        score: 68
        rationale: 成本主要来自规范、模板、runtime 和 CLI 的多层同步，不涉及重做整体技术架构，但需要跨模块对齐。
      overall: 81
    recommendation:
      priority_level: P0
      suggested_timeline: 应作为治理收敛的前置优先项尽快确认，先完成目标与边界冻结，再进入后续规范和实现分解。
      resource_estimate: 需要 governance owner 主导，联合 workflow、runtime、CLI 代表完成一次统一确认与语义映射。
      rationale: 这是后续所有 gate 相关规范和实现的判定基线；若不先统一目标模型，后续任何实现都会继续放大历史歧义。
    confirmation:
      status: pending
      questions:
      - question: 是否接受将该事项定义为 P0 治理收敛项，而不是局部 CLI 优化项？
        answered: false
      feedback: 优先级判断依赖对其基础治理属性的共识。
  risks_and_boundaries:
    risks:
    - type: semantic_migration
      description: 历史 gate_type、workflow 模板和 runtime 语义映射不一致，可能在迁移阶段产生双重解释。
      impact: high
      mitigation: 先冻结 purpose/decision_mode 归一化规则，再对旧字段做显式兼容映射，禁止继续扩散混合语义。
    - type: context_quality
      description: 若 human_gate_context 只补字段不补信息质量，人工审批仍可能形式化存在、实质不可判断。
      impact: high
      mitigation: 将 why_now、decision_question、evidence_refs、risk_summary、next actions
        设为最低可用上下文，并要求 CLI 直接消费。
    - type: boundary_enforcement
      description: 如果 runtime 或流程设计没有严格执行 review before approval，review approve 仍可能被误用为正式放行。
      impact: high
      mitigation: 明确 freeze/release/merge 仅属于 approval + human_required，并在状态机与 CLI
        后果预览中强制体现。
    - type: execution_overhead
      description: 新增统一上下文和状态预览会增加前期建模与操作成本。
      impact: medium
      mitigation: 控制第一阶段为最小可用字段集，优先覆盖高风险人工 gate，再逐步扩展。
    in_scope:
    - 从 ADR-017 原始输入中提炼 gate 治理的核心目标、业务动因、目标用户和约束
    - 明确该事项对 raw input intake 与 SRC normalization 的前置价值
    - 定义可衡量的成功标准、优先级和关键边界
    - 归纳当前问题为职责混杂、审批上下文缺失、freeze 与 review 污染三类核心矛盾
    out_of_scope:
    - EPIC 设计
    - 技术架构设计
    - 研发排期
    - 数据库最终列名
    - 前端 UI 样式
    - 一次性历史数据迁移方案
    dependencies:
    - ADR-005、ADR-006、ADR-015 中仍然有效的上位治理约束
    - product-goal-contract v1 schema
    - governance owner 对 approval 默认必须 human_required 的确认
    - 现有 workflow 模板、runtime、CLI 与 trace 对 gate 语义的盘点和映射
    confirmation:
      status: pending
      questions:
      - question: 是否确认本阶段只做目标与价值归一化，不进入 EPIC、架构或排期分解？
        answered: false
      - question: 是否确认 freeze/release/merge 等正式边界全部纳入 approval，而不再借由 review 表达？
        answered: false
      feedback: 边界一旦确认，后续 SRC normalization 才能稳定向下游传递。
detailed_analysis:
  user_value_analysis: 当前人类审批者面对的是一个流程阻塞器，而不是一个可审批对象。将 gate 归一化为职责、模式和上下文三个层次后，用户价值体现在更低认知负担、更高责任清晰度和更稳定的决策依据。
  industry_analysis: 在治理型工作流中，review 和 approval 的混淆会直接损害审计闭环和责任归属。ADR-017 的价值不在单个命令，而在形成可复用的人机审批抽象。
  efficiency_analysis: 统一语义后，spec、workflow、runtime、CLI、trace 不再各自定义人审逻辑，能显著减少兼容分叉和人工解释；同时也为后续自动检查与条件升级提供清晰挂点。
  cost_analysis: 成本集中在跨层收敛和旧语义映射，不属于单点低成本修补，但相比长期维持多套心智模型，其投入具有明显治理回报。
change_log:
- version: v1
  date: '2026-03-14'
  changes: 基于 ADR-017 原始输入完成产品目标、价值链、优先级与边界归一化。
  author: Codex
