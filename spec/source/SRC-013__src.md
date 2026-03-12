---
id: SRC-013
ssot_type: src
title: SRC
status: archived
version: v1
parent_id: null
derived_from_ids: []
source_refs: []
owner: null
tags: []
properties:
  contract_key: src
  identity_kind: ssot
  superseded_by: SRC-016
  superseded_reason: Replaced by the latest ADR-011 source draft retained for downstream cleanup.
frozen_at: '2026-03-12T19:41:54.888288'
---

src_metadata:
  version: '1.0'
  derived_from: ADR-011
  source_type: architecture_decision_record
  upstream_run: RUN-20260312193528-0a14-raw_input_intake
  normalized_at: '2026-03-12'
product_goal:
  identifier: PG-REQ-CHAIN-TEST-001
  title: 需求链一致性测试体系建设
  essence: 将需求链从'文档审阅对象'转化为'可测试系统'
  objectives:
    primary:
    - id: OBJ-1
      description: 将需求链 (src -> epic -> feat -> task) 从'文档审阅对象'转化为'可测试系统'
      priority: P0
      acceptance_criteria: 建立四层测试体系，输出结构化报告
    - id: OBJ-2
      description: 用自动化测试流水线替代人工目检，降低治理成本
      priority: P0
      acceptance_criteria: 6个核心测试器落地，L0规则校验全量覆盖
    - id: OBJ-3
      description: 建立需求链质量的可量化指标体系
      priority: P1
      acceptance_criteria: 5类核心指标可采集、可比较、可回归
    - id: OBJ-4
      description: 保障需求链的语义一致性，防止下游漂移
      priority: P1
      acceptance_criteria: 三段对齐评分 (src→epic→feat→task) 可计算
    - id: OBJ-5
      description: 建立回归测试能力，支持变更影响评估
      priority: P2
      acceptance_criteria: Golden Set + Replay Stability Suite 运行
  business_drivers:
    pain_points:
    - 审阅视角碎片化 — 当前 review 面向单阶段单对象，缺少整条链的统一校验视角
    - 语义漂移不可感知 — schema validator 只检查字段格式，不检查上下游语义漂移
    - 计划完整性≠可执行性 — delivery plan validation 只判断形态完整，不等于 task 真正可执行
    - 缺乏稳定性保障 — 无正式 replay stability 套件，无法判断同一输入重跑后的结构稳定性
    - 质量趋势不可见 — 无统一 scorecard，无法持续观察 trace completeness、alignment、executability 趋势
    value_proposition:
      efficiency:
        from: 人工目检，耗时高
        to: 规则优先自动校验
        value: 降低硬检查人力成本
      confidence:
        from: 经验判断，主观性强
        to: 结构化评分+指标趋势
        value: 可追溯、可比较的质量基线
      safety:
        from: 无回归能力
        to: Golden Set 自动重跑
        value: workflow/agent/contract 变更可评估影响
      usability:
        from: Task'看起来完整'
        to: Task 可执行性判断
        value: 减少下游开工准备时的口头解释成本
  target_users:
  - role: governance_owner
    scenario: 定义和维护一致性测试规则、审批测试体系变更
    needs: 规则可配置、指标可观测、变更可控
  - role: review_agent_pm
    scenario: 执行 src/epic/feat review，输出结构化结论
    needs: 减少人工硬检查工作量，聚焦语义判断
  - role: workflow_maintainer
    scenario: 变更 workflow/agent/contract 时评估影响
    needs: 有回归测试能力，不怕改坏现有链路
  - role: downstream_dev_qa
    scenario: 消费 TASK 进入实现阶段
    needs: 收到的 TASK 真正可执行，减少澄清成本
  - role: project_manager
    scenario: 跟踪需求链质量趋势
    needs: 有 scorecard 可看趋势，有数据可决策
  constraints:
    functional:
    - id: CONS-1
      rule: 不直接改写业务需求内容 — 测试体系只检测一致性，不自动修复
      source: ADR-011 Section 4.2
    - id: CONS-2
      rule: 不替代产品 owner 的业务价值判断 — 只判断'是否一致'，不判断'是否有价值'
      source: ADR-011 Section 4.2
    - id: CONS-3
      rule: 不替代 dev/qa 的实现与执行验证 — task executability 判断的是'是否可开工准备'，不是'实现是否正确'
      source: ADR-011 Section 4.2
    - id: CONS-4
      rule: 一致性测试 ≠ Release Gate — 不直接阻塞发布，提供质量信号供决策
      source: ADR-011 Section 4.2
    technical:
    - id: CONS-5
      rule: Programmatic Rules First — 必填字段、类型、ID唯一性、引用存在性优先用规则实现
      source: ADR-011 Section 7.1
    - id: CONS-6
      rule: Hybrid Rules Preferred — 成本高但判断价值大的项，采用'规则初筛 + LLM精判'
      source: ADR-011 Section 7.2
    - id: CONS-7
      rule: LLM Judge Reserved For Semantics — 范围清晰度、语义漂移、可执行性判断才可使用 LLM
      source: ADR-011 Section 7.3
    - id: CONS-8
      rule: 成本控制三层模型 — L0规则校验全量、L1轻量筛查全量、L2 LLM judge仅异常/抽样
      source: ADR-011 Section 10.2
    evolutionary:
    - id: CONS-9
      rule: 分阶段落地 — Phase1 结构校验+可执行性，Phase2 语义对齐，Phase3 回归测试
      source: ADR-011 Section 11
    - id: CONS-10
      rule: 当前主链兼容 — 先按 src->epic->feat->task 落地，待正式迁移到 RELEASE->DEVPLAN/TESTPLAN->TASK
        后平移
      source: ADR-011 Section 12
    - id: CONS-11
      rule: 不直接冻结 schema/CLI — 本 ADR 冻结方向和分层，下游再定义具体 contract
      source: ADR-011 Section 1, 14
  key_metrics:
  - name: Trace Completeness
    description: 需求链引用完整性
    phase: Phase1
  - name: Semantic Alignment
    description: 三段对齐评分
    phase: Phase2
  - name: Replay Stability
    description: 重跑稳定性
    phase: Phase3
  - name: Overlap Rate
    description: 需求重叠率
    phase: Phase2
  - name: Executability Rate
    description: Task可执行率
    phase: Phase1
normalization_summary:
  objectives_extracted: 5
  pain_points_identified: 5
  value_dimensions: 4
  user_roles: 5
  constraints_catalogued: 11
  metrics_defined: 5
  readiness_for_src:
    core_objectives: ✓ CLEAR - 5 objectives with P0/P1/P2 priorities
    business_drivers: ✓ CLEAR - Pain points + value proposition mapped
    target_users: ✓ CLEAR - 5 roles with scenarios and needs
    constraints: ✓ CLEAR - Functional/technical/evolutionary categorized
    acceptance_criteria: ✓ CLEAR - Per-objective anchors defined
