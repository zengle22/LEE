---
id: SRC-040
ssot_type: src
title: ADR 原始输入归一化与合同复用前置目标分析
status: frozen
version: v1
workflow_instance_id: wf_task_26c2857e
parent_id: null
derived_from_ids: []
source_refs: []
owner: null
tags: []
properties:
  contract_key: src
  identity_kind: ssot
frozen_at: '2026-03-15T01:57:38.848168'
---

contract_type: product-goal-contract
contract_version: 1.0.0
contract_info:
  contract_id: PGC-SRC-NORMALIZATION-ADR-017-001
  title: ADR 原始输入归一化与合同复用前置目标分析
  version: v1
  created_at: '2026-03-14T17:12:49Z'
  status: DRAFT
requirement_overview:
  description: 将给定 ADR 原始输入归一化为 product-goal-contract 结构，先依据正式 schema 与 agent 规格确认字段和语义边界，再判断仓库内是否已有等价且合规的现有产物，若已存在则复用并完成结构校验，避免重复生成偏离合同的新文件。
  target_users: 负责 raw input intake 与 SRC normalization 的产品分析代理、合同产物维护者、需要复核合同合规性的治理维护者
  context: 输入内容显示当前工作并非设计新目标，而是把已有 ADR 相关原始输入稳定映射到正式合同；过程中已定位 schema、agent 规格和现有 ADR-017
    产物，并以程序化校验确认可作为交付基线。
  expected_timeline: 作为前置分析应在 intake 阶段即时完成，并在进入下游归一化或落盘前完成一次结构校验。
key_designs:
  core_goal:
    primary_goal:
      description: 建立一条可复用、可验证、避免重复落盘的原始输入归一化路径，使 ADR 类输入在进入 SRC normalization 前就能被稳定映射到正式的
        product-goal-contract。
      rationale: 先按正式 schema 归一化，再基于仓库现有产物判断是否需要新生成文件，可以降低模板猜字段、重复产物和格式漂移的风险。
      metrics:
      - 合同字段映射基于正式 schema 的覆盖率达到 100%
      - 生成前对同类现有产物的复用检查执行率达到 100%
      - 最终交付对象通过一次程序化 schema 校验
      - 重复生成与格式偏离导致的新增文件数量保持为 0
      success_criteria:
      - 分析者只读取与字段、语义和产物边界直接相关的规范内容，不依赖猜测补字段
      - 当仓库内已有高度匹配且合规的合同产物时，能够明确复用而非重复改写
      - 校验步骤可以证明交付对象符合正式 contract 版本
      - 输出可直接作为 raw input intake 与 SRC normalization 的前置输入
    confirmation:
      status: pending
      questions:
      - question: 是否确认在已有等价且通过校验的合同产物存在时，以复用为默认策略而不是重复生成？
        answered: false
      - question: 是否确认字段解释以正式 schema 和 agent 规格为唯一优先依据？
        answered: false
      feedback: 核心目标已清晰，但仍需 owner 确认复用优先级与例外条件。
  value_chain:
    user_need:
      description: 归一化执行者需要快速把原始 ADR 输入转成正式合同，同时避免因为字段猜测、旧模板或重复输出而降低结果可信度。
      validation: 输入文本明确强调先定位正式 schema、只读直接相关部分，并在发现现有 ADR-017 产物后优先核对其是否满足当前合同版本。
    product_feature:
      description: 提供一套以 schema 对齐、现有产物检索、合规复用和轻量程序化校验为核心的 intake 分析方法。
      validation: 输入已展示完整动作链：定位 schema 与 agent 规格、检查同类产物、比对 ADR-017、使用 Python 进行 schema
        校验。
    direct_value:
      description: 减少错误补字段、重复落盘和合同格式偏离，提升单次 intake 的正确率与可追溯性。
      validation: 输入中的关键判断就是“如果已有文件正确存在，就避免重复生成另一份偏离格式的文件”。
    business_impact:
      description: 让 SRC normalization 前置环节形成统一、可审计的产出基线，降低后续治理对象因输入不一致而返工的成本。
      validation: 通过正式 schema 校验与基线复用，后续环节可直接接收已验证的标准对象，而不是处理多份语义相近但格式漂移的文件。
    strategic_significance:
      description: 把 intake 从一次性文本整理提升为合同驱动的标准化入口，为后续规范收敛和自动化处理建立稳定前提。
      validation: 输入文本把该任务定位为 raw input intake 与 SRC normalization 的前置分析，说明其价值在于为后续流程提供统一入口。
    explanation: 价值链先归一化信息来源，再约束字段解释，随后通过现有产物复用与校验降低重复劳动，最终提升整个规范处理链路的一致性。
    confirmation:
      status: pending
      questions:
      - question: 是否接受通过正式 schema 校验且无需重复生成新文件作为第一优先的价值验证点？
        answered: false
      feedback: 价值链闭环完整，但复用策略的例外场景还需在下游治理中进一步约束。
  priority:
    scores:
      user_value:
        score: 88
        rationale: 直接降低执行者在 intake 阶段的判断成本与误填风险，使用对象明确。
      industry:
        score: 76
        rationale: 合同驱动归一化和 schema 校验是通用治理手段，但此处主要服务于仓库内流程而非外部市场能力。
      efficiency:
        score: 91
        rationale: 复用已有正确产物并避免重复生成，能立即减少返工、审阅和维护成本。
      cost:
        score: 82
        rationale: 主要依赖已有 schema、现有产物和轻量校验，分析成本较低，实施复杂度受控。
      overall: 84
    recommendation:
      priority_level: P1
      suggested_timeline: 应在每次 intake 开始时立即执行，并在进入 SRC normalization 前完成校验闭环。
      resource_estimate: 低到中，主要需要规范读取、产物核对和一次本地校验，不涉及技术架构或研发排期设计。
      rationale: 该能力不直接产出新业务功能，但它决定后续合同类对象是否可信，因此应作为高优先级前置控制点。
    confirmation:
      status: pending
      questions:
      - question: 是否确认 intake 阶段必须先做现有合同复用检查，再决定是否生成新对象？
        answered: false
      feedback: 优先级判断偏高，原因是它直接影响后续所有规范对象的输入质量。
  risks_and_boundaries:
    risks:
    - type: schema_misread
      description: 如果只按模板或历史印象补字段，而未以正式 schema 为准，容易产生类型错误或遗漏必填项。
      impact: high
      mitigation: 限定读取范围为正式 schema 与直接相关 agent 规格，并在交付前执行程序化校验。
    - type: duplicate_output
      description: 在已有等价合规产物存在时再次生成新文件，会造成版本分叉和基线混乱。
      impact: high
      mitigation: 将现有产物检索和版本符合性核对设为生成前置步骤。
    - type: boundary_drift
      description: 分析过程如果延伸到 EPIC、技术架构或研发排期，会稀释前置目标分析的职责边界。
      impact: medium
      mitigation: 只输出目标、价值、目标用户和关键约束，不进入实现设计与排期判断。
    - type: false_reuse
      description: 若现有文件与当前输入只是在主题上相似但不满足当前合同版本，盲目复用会引入隐性偏差。
      impact: medium
      mitigation: 复用前同时核对内容匹配度与当前 schema 合规性。
    in_scope:
    - 提炼原始输入中的核心目标、业务动因、目标用户和关键约束
    - 基于正式 schema 确认合同字段与语义边界
    - 检查仓库内是否已有可复用的同类合同产物
    - 对候选结果执行一次结构化 schema 校验
    - 形成可供 SRC normalization 使用的前置业务对象
    out_of_scope:
    - EPIC 设计
    - 技术架构
    - 研发排期
    - 实现层代码改造
    - 新增自动化框架选型
    dependencies:
    - 正式 product-goal-contract schema 可读取且为当前版本依据
    - 相关 agent 规格提供字段语义与产物边界参考
    - 仓库内已有同类产物可供比对复用
    - 本地可用轻量校验能力以验证输出结构
    confirmation:
      status: pending
      questions:
      - question: 是否确认本次前置分析的交付边界止于标准对象归一化与校验，不向下游设计延伸？
        answered: false
      feedback: 边界已按任务要求收敛，但仍需确认复用策略在特殊场景下的人工判定规则。
detailed_analysis:
  user_value_analysis: 该输入的核心用户是执行 intake 与规范归一化的内部角色，而不是终端市场用户。对他们最有价值的不是更多模板，而是稳定的字段依据、复用判断和可验证的交付基线。
  industry_analysis: 在规范治理场景中，先以正式 contract 为锚点，再做现有资产复用与结构校验，是降低文档漂移和重复劳动的成熟做法。
  efficiency_analysis: 该方法把生成新对象变成条件动作，而不是默认动作，从而把更多时间投入到核对和校验，而非重复制造近似文件。
  cost_analysis: 分析本身成本较低，主要由规范读取、已有文件核对和一次本地校验构成；高成本项如系统改造和排期并不在本任务范围内。
confirmation_summary:
  core_goal_status: pending
  value_chain_status: pending
  priority_status: pending
  risks_status: pending
  all_confirmed: false
approval:
  status: pending
  decision: awaiting_intake_confirmation
  comments: 当前对象可作为 raw input intake 与 SRC normalization 的前置分析基线，待确认复用策略与边界约束后进入下游使用。
  next_stage: src_normalization
  owner: product-goal-analyzer
change_log:
- version: v1
  date: '2026-03-14'
  changes: 基于原始执行日志生成首版产品目标与价值分析对象，明确复用优先、schema 对齐与结构校验边界。
  author: Codex
