---
id: SRC-057
ssot_type: src
title: SSOT 需求轴验收治理体系
status: draft
version: v1
workflow_instance_id: wf_task_f309b4cb
parent_id: null
derived_from_ids: []
source_refs:
  - ADR-025
owner: null
tags:
  - governance
  - quality-assurance
  - ssot
  - gate
properties:
  contract_key: src
  identity_kind: ssot
frozen_at: null
---

contract_type: product-goal-contract
contract_version: 1.0.0
contract_info:
  contract_id: PGC-ADR-025-20260317
  title: SSOT 需求轴验收治理体系
  version: v1
  created_at: '2026-03-17T13:15:00Z'
  updated_at: '2026-03-17T13:15:00Z'
  status: DRAFT
requirement_overview:
  description: 建立 SSOT 需求轴质量验收治理体系，在每个 SSOT 文件 (SRC/EPIC/FEAT/UI/TECH/TASK) 生成前强制执行系统性测试和验收流程，确保功能逻辑闭环、用户体验达标、功能完整性、无逻辑漏洞、行业差距可见、改进方向明确，通过三阶段 Gate(Auto/Review/Approval) 卡点控制，实现质量验证闭环和问题修复跟踪。
  target_users: 产品部门 (PO/TechLead/DesignLead/QALead)、SSOT 作者、Gate 审批人、治理委员会
  context: 当前 SSOT 生成流程存在质量验证缺失、用户体验风险、行业差距不可见、问题修复无闭环、审批依据不足等 5 大核心问题，需要在冻结流程前引入强制性验收机制。
  expected_timeline: Phase 1-5 分阶段实施，预计 3-6 个月完成全量工具链建设和 L3 流程集成
key_designs:
  core_goal:
    primary_goal:
      description: 需求轴每个 SSOT 文件生成前，都必须经过测试和验收流程，通过 6 维度验收 (功能逻辑闭环、用户故事体验、功能完整性、逻辑漏洞扫描、行业实践差异、改进空间识别) 和 4 级缺陷分类 (P0/P1/P2/P3) 确保 SSOT 质量，验收报告作为 Gate 审批必要依据。
      rationale: 解决 SSOT 生成后直接进入冻结流程缺乏系统性质量验证的问题，降低用户体验风险，使行业差距可见，建立问题修复闭环机制，为 Gate 审批提供结构化依据。
      metrics: P0 缺陷密度=0、P1 缺陷密度<0.1、一次通过率>60%、平均修复轮次<2、验收覆盖率 100%、行业差距记录率 100%
      success_criteria:
        - 所有 SRC/EPIC/FEAT/UI/TECH/TASK 均通过完整验收流程后方可冻结
        - P0/P1 问题修复率 100%
        - 验收报告完整引用到 Gate 记录
        - 质量指标纳入团队考核
    secondary_goals:
      - description: 建立 Auto Gate 自动化检查能力，减少人工检查成本
        priority: 1
      - description: 建立行业对标库，支持最佳实践差距分析
        priority: 2
      - description: 建立质量度量体系，支持持续改进决策
        priority: 3
    confirmation:
      status: pending
      questions:
        - question: 是否确认 6 维度验收框架覆盖所有必要的质量检查项？
          answered: false
        - question: 是否确认 P0/P1/P2/P3 缺陷分级标准适用于所有 SSOT 类型？
          answered: false
      feedback: 需要治理 owner 对验收框架和缺陷分级标准进行确认。
  value_chain:
    user_need:
      description: SSOT 作者需要明确的质量标准和验收指引，评审人需要结构化的验收报告和缺陷跟踪工具，审批人需要可信的决策依据。
      validation: ADR-025 定义了完整的验收框架、6 维度检查项、4 级缺陷分类、三阶段流程、角色职责矩阵、冲突解决机制。
    product_feature:
      description: Auto Gate(自动检查)、Review Gate(人工评审)、Approval Gate(审批决策) 三阶段卡点；6 维度验收框架；P0/P1/P2/P3 缺陷分级；Fix Loop 修复循环；行业差距分析框架；验收报告合约；L3 流程集成。
      validation: 流程覆盖 SRC/EPIC/FEAT/UI/TECH/TASK 全部 SSOT 类型，含同步/异步评审机制、紧急发布快速通道、自动化程度分级 (L1-L4)。
    direct_value:
      description: 系统性识别和修复 SSOT 质量问题，降低下游交付风险；显式验收用户体验标准，减少体验断裂；量化行业差距，明确改进方向；结构化缺陷跟踪，确保 P0/P1 闭环；为 Gate 审批提供决策依据。
      validation: 验收报告合约定义完整 YAML schema，含 auto_check、manual_review、defect_list、industry_gap_analysis、improvement_backlog 等核心字段。
    business_impact:
      description: 提升 SSOT 质量降低返工成本，减少因需求问题导致的开发返工；提升产品交付质量，增强用户满意度；建立质量度量体系，支持持续改进；降低决策风险，提升审批效率。
      validation: 定义 Quality Metrics(P0 密度、P1 密度、一次通过率、修复轮次、覆盖率) 和 Process Metrics(Auto Gate 通过率、Review 周期、修复时间、审批通过率)。
    strategic_significance:
      description: 构建 SSOT 需求轴质量治理基础设施，实现质量左移；建立行业对标能力，持续缩小与最佳实践差距；形成质量数据资产，支持度量驱动改进；与 ADR-001/003/005 形成完整治理体系。
      validation: 继承 ADR-001(SSOT Delivery Chain Hard Governance)、ADR-003(Product Department SSOT Design)、ADR-005(Gate 三分类治理模型) 的治理原则并落地实施。
    explanation: 价值链从 SSOT 作者/评审人/审批人的核心需求出发，通过三阶段 Gate 和 6 维度验收框架提供系统化解决方案，最终实现质量左移和度量驱动改进。
  priority:
    scores:
      user_value:
        score: 90
        rationale: 直接提升 SSOT 作者、评审人、审批人的工作质量和效率，减少质量争议。
      industry:
        score: 80
        rationale: 建立系统性质量验证和行业对标机制，达到行业领先水平。
      efficiency:
        score: 90
        rationale: 通过自动化 Auto Gate 和结构化流程，减少人工检查成本，提升评审效率。
      cost:
        score: 80
        rationale: 质量左移降低下游返工成本，工具链开发投入可控 (分 5 阶段实施)。
      overall: 85
    recommendation:
      priority_level: P0
      suggested_timeline: 立即启动 Phase 1(基础定义)，3 个月内完成 Phase 1-3 核心能力建设，6 个月内完成全量实施
      resource_estimate: 需要 Workflow Owner 1 人、工具开发 2-3 人、PO/Tech Lead 参与评审流程设计，预计总投入 300-500 人天
      rationale: SSOT 质量是下游交付质量的基础，质量验证缺失是当前最大风险点；分阶段实施可快速见效并控制风险；紧急发布流程支持特殊情况。
    confirmation:
      status: pending
      questions:
        - question: 是否确认该事项为 P0 优先级治理基础设施？
          answered: false
      feedback: 优先级判断依赖对 SSOT 质量基础作用的共识。
  risks_and_boundaries:
    risks:
      - type: implementation_complexity
        description: 工具链开发复杂度超预期，影响实施进度
        impact: high
        mitigation: 分 5 阶段实施，优先建设核心能力，快速迭代验证。
      - type: team_adaptation
        description: 团队适应新流程需要时间，初期可能降低效率
        impact: medium
        mitigation: 提供培训和文档支持，设置适应期，收集反馈持续优化。
      - type: benchmark_maintenance
        description: 对标对象库建立需要持续投入和行业研究
        impact: medium
        mitigation: 建立对标库维护机制，鼓励团队贡献，定期更新。
      - type: emergency_abuse
        description: 紧急发布流程可能被滥用，需要严格管控
        impact: high
        mitigation: 设置严格的紧急发布审批条件，记录并审计所有紧急发布案例。
      - type: review_conflict
        description: 异步评审可能出现意见冲突，需要有效协调机制
        impact: medium
        mitigation: 建立冲突解决机制，明确最终决策责任人。
    in_scope:
      - SRC/EPIC/FEAT/UI/TECH/TASK 六类 SSOT 的验收流程
      - Auto/Review/Approval 三阶段 Gate 卡点
      - 6 维度验收框架和 4 级缺陷分类
      - 验收报告生成和存储
      - L3 流程集成 (raw-to-src/src-to-epic/epic-to-feat/feat-to-delivery-prep)
      - 质量度量指标采集和展示
    out_of_scope:
      - ADR 本身 (有独立评审流程)
      - TESTSET(由 QA 部门负责)
      - Dev 部门和 QA 部门的内部流程
      - 非 SSOT 需求轴的治理流程
    dependencies:
      - ADR-001: SSOT Delivery Chain Hard Governance (治理基础)
      - ADR-003: Product Department SSOT Design (SSOT 设计规范)
      - ADR-005: Gate 三分类治理模型 (Gate 机制)
      - L3 工作流系统 (流程集成)
      - Schema Validator / Contract Validator 工具链
    confirmation:
      status: pending
      questions:
        - question: 是否确认本阶段只做目标与价值归一化，不进入 EPIC、架构或排期分解？
          answered: false
        - question: 是否确认验收报告合约 schema 满足所有 SSOT 类型的验收需求？
          answered: false
      feedback: 边界一旦确认，后续 SRC normalization 才能稳定向下游传递。
detailed_analysis:
  user_value_analysis: SSOT 作者、评审人、审批人在当前流程中面临质量验证缺失、评审依据不足、决策风险高等问题。通过三阶段 Gate 和 6 维度验收框架，用户可以获得明确的质量标准、结构化的验收报告和可信的决策依据。
  industry_analysis: 系统性质量验证和行业对标机制是行业领先实践的核心特征。通过建立 Auto Gate 自动化检查和行业对标库，可以实现质量左移和持续改进。
  efficiency_analysis: 自动化 Auto Gate 可以大幅减少人工检查成本，结构化流程可以提升评审效率。分阶段实施可以控制风险并快速见效。
  cost_analysis: 工具链开发需要 300-500 人天投入，但质量左移可以显著降低下游返工成本，长期收益明显。
change_log:
  - version: v1
    date: '2026-03-17'
    changes: 基于 ADR-025 原始输入完成产品目标、价值链、优先级与边界归一化。
    author: Codex
