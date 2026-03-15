---
id: SRC-016
ssot_type: src
title: 需求链一致性测试体系建设
status: frozen
version: v1
parent_id: null
derived_from_ids: []
source_refs: []
owner: null
tags: []
properties:
  contract_key: src
  identity_kind: ssot
frozen_at: '2026-03-12T21:06:30.650000'
---

metadata:
  src_id: SRC-ADR-011-001
  title: 需求链一致性测试体系建设
  version: v1
  contract_ref: PGC-ADR-011-001
  normalization_date: '2026-03-12'
core_goal:
  primary_statement: '建立四层一致性测试体系，将需求链从"文档审阅对象"转变为

    "可自动验证、可回归测试的软件系统"

    '
  goal_dimensions:
  - dimension: 结构一致性
    description: Schema validator 覆盖必填字段、类型、引用合法性
    validator: SchemaValidator
  - dimension: 语义映射一致性
    description: src->epic->feat->task 三段语义对齐检测
    validator: SemanticAlignmentJudge
  - dimension: 追溯完整性
    description: Traceability checker 识别 orphan、broken link
    validator: TraceabilityChecker
  - dimension: 重跑稳定性
    description: Replay stability suite 检测节点波动和颗粒度变化
    validator: ReplayStabilitySuite
  measurable_outcomes:
  - metric: Trace Completeness
    target: '>= 95%'
    measurement: 可完整追溯的task数/task总数
  - metric: Semantic Alignment Score
    target: '>= 80分'
    measurement: src->epic->feat->task 三段平均分
  - metric: Replay Stability Score
    target: '>= 90%'
    measurement: 多次运行核心结构一致性程度
  - metric: Overlap Rate
    target: < 15%
    measurement: FEAT高重叠率和TASK重复率
  - metric: Executability Rate
    target: '>= 85%'
    measurement: 可直接进入下游准备的task比例
business_drivers:
  pain_points:
  - issue: 人工目检成本高
    evidence: 当前 review 面向单阶段对象，需大量人工检查链路一致性
    impact: 高
  - issue: 难以规模化
    evidence: 缺少自动化测试流水线，无法应对需求链增长
    impact: 高
  - issue: 无法持续监控趋势
    evidence: 缺少统一 scorecard 和质量指标趋势跟踪
    impact: 中
  - issue: 语义漂移无检测
    evidence: 上下游需求转换过程中语义偏离无法自动发现
    impact: 中
  value_proposition:
    immediate_benefits:
    - benefit: 自动化硬检查替代人工
      value: 减少 60-70% 人工检查工作量
    - benefit: 提前发现结构错误
      value: 在交付前识别 schema violation 和 broken link
    - benefit: 检测语义漂移
      value: 自动发现上下游语义覆盖缺失和新增假设
    strategic_benefits:
    - benefit: 治理范式转变
      value: 从"文档写得好不好"转为"是否通过测试"
    - benefit: 可回归验证
      value: workflow/agent/contract 变更可量化评估影响
    - benefit: 规模化能力
      value: 支持 CI 集成和持续治理
  roi_indicators:
    cost_reduction: Phase 1 减少人工检查工作量 60-70%
    quality_improvement: 结构错误发现率提升至 100%（自动化规则覆盖）
    cycle_time: 单阶段一致性验证时间从小时级降至分钟级
target_users:
  primary_users:
  - role: 产品治理团队 (Governance)
    responsibilities:
    - 需求链质量标准制定
    - 一致性测试结果审核
    - 趋势分析和治理决策
    pain_points:
    - 人工检查效率低
    - 缺乏量化质量指标
    success_criteria:
    - 能通过 scorecard 快速判断链路健康度
    - 能追踪质量指标趋势变化
  - role: Review Agent 开发者
    responsibilities:
    - 开发六类测试器
    - 维护验证规则
    - 优化判断准确率
    pain_points:
    - 缺少统一的测试框架
    - 验证逻辑分散在各阶段
    success_criteria:
    - 能独立开发和部署新的 validator
    - 能通过 golden set 回归测试
  - role: Workflow 维护者
    responsibilities:
    - 维护 src->epic->feat->task 主链
    - 集成一致性测试节点
    - 监控 CI/CD 集成
    pain_points:
    - workflow 变更影响难评估
    - 缺少自动化回归测试
    success_criteria:
    - 能在 CI 中接入一致性测试
    - 能观察 consistency score 变化
  secondary_users:
  - role: CI/CD 集成团队
    usage_pattern: 将一致性测试集成到部署流水线
  - role: EPIC/FEAT/TASK 阶段评审者
    usage_pattern: 使用一致性测试结果辅助评审决策
constraints:
  scope_constraints:
    in_scope:
    - item: src -> epic -> feat -> task 当前主链的一致性测试
      rationale: 现役链路，直接产生价值
    - item: 结构合法性、引用合法性、trace 完整性验证
      rationale: Phase 1 核心硬检查能力
    - item: 上下游语义覆盖、漂移、遗漏、新增假设检测
      rationale: Phase 2 核心软判断能力
    - item: Task 可执行性检测
      rationale: 下游可用性关键指标
    - item: Replay stability 测试
      rationale: 确保测试结果可复现
    - item: Scorecard 指标与回归比较
      rationale: 支持趋势分析和变更评估
    - item: Golden set 样本集维护
      rationale: 回归测试基础
    out_of_scope:
    - item: 直接改写业务需求内容
      reason: 治理工具不替代业务判断
    - item: 替代产品 owner 的业务价值判断
      reason: 一致性测试不判断价值合理性
    - item: 替代 dev/qa 的实现与执行验证
      reason: 需求链测试 ≠ 代码测试
    - item: 把一致性测试等同于 release gate
      reason: 质量信号而非发布决定因素
    - item: 在本 ADR 中直接引入新的业务主链对象
      reason: 未来迁移路径已规划，当前按现役主链落地
  technical_constraints:
  - constraint: 三层成本控制策略
    description: L0规则全量/L1轻量筛查全量/L2 LLM judge抽样
    implication: 需设计分层触发机制
  - constraint: Hybrid Rules 设计
    description: 规则初筛 + LLM精判
    implication: Semantic Alignment 和 Executability Judge 需降低 LLM 依赖
  - constraint: Schema 校验基础设施
    description: 依赖现有 SSOT P0/P1 校验机制
    implication: 需兼容现有 schema 定义
  timeline_constraints:
    phase_1:
      duration: 2-3周
      deliverables:
      - Schema validator
      - Traceability checker
      - 基础报告输出
    phase_2:
      duration: 2-3周
      deliverables:
      - Semantic alignment judge
      - Overlap detector
    phase_3:
      duration: 2周
      deliverables:
      - Replay stability suite
      - Golden set regression
  risk_constraints:
  - risk: LLM 判断一致性波动
    mitigation: 抽样对比机制，持续优化 prompt
  - risk: 范围蔓延
    mitigation: 明确 Out of Scope 边界
  - risk: 未来主链迁移
    mitigation: 保持平移能力，按现役主链先落地
normalization_summary:
  core_goal_normalized: true
  value_chain_validated: true
  target_users_profiled: true
  constraints_identified: true
  readiness_for_epic:
    status: READY
    conditions:
    - 核心目标已提炼为 4 个可测维度
    - 业务动因已量化为 ROI 指标
    - 目标用户已明确为 3 类主要角色
    - 范围边界已清晰界定 In/Out of Scope
  recommended_next_steps:
  - step: 进入 EPIC 设计阶段
    priority: P1
    rationale: 需求已归一化，具备进入详细设计条件
  - step: 准备 Golden Set 样本
    priority: P1
    rationale: 回归测试需要基准样本
  - step: 细化 Schema Validator 规则
    priority: P1
    rationale: Phase 1 核心交付物
output_mapping:
  for_epic_design:
  - src_field: core_goal.goal_dimensions
    epic_usage: FEAT 边界划分的维度依据
  - src_field: core_goal.measurable_outcomes
    epic_usage: 验收标准 (Acceptance Criteria) 来源
  - src_field: target_users.primary_users
    epic_usage: 用户故事 (User Stories) 角色定义
  - src_field: constraints.scope_constraints.in_scope
    epic_usage: 范围声明 (Scope Statement)
  - src_field: constraints.scope_constraints.out_of_scope
    epic_usage: 排除项 (Exclusions)
  for_contract_design:
  - src_field: core_goal.measurable_outcomes
    contract_usage: 协议字段验证规则来源
  - src_field: constraints.technical_constraints
    contract_usage: 协议版本兼容性约束
  for_test_plan:
  - src_field: core_goal.measurable_outcomes
    test_usage: 测试通过标准
  - src_field: constraints.timeline_constraints
    test_usage: 测试阶段规划依据
