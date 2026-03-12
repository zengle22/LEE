---
id: SRC-018
ssot_type: src
title: SRC
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
frozen_at: '2026-03-12T20:53:25.662168'
---

product_goal_analysis:
  core_objective:
    statement: 为 LEE 项目需求链建立自动化一致性测试体系
    scope: SRC→EPIC→FEAT→TASK 四层需求链
    test_layers:
    - 结构
    - 语义
    - 稳定性
    - 可用性
    replacement: 自动化测试替代人工目检
  business_drivers:
    pain_point: 主观人工评审缺乏客观标准
    transformation: 建立可量化治理标准
    key_metrics:
    - Trace Completeness
    - Semantic Alignment
    - Replay Stability
    - Overlap Rate
    - Executability
  target_users:
  - role: 需求治理人员
    need: 客观质量评估报告
  - role: 研发流程管理员
    need: 持续监控与回归验证
  - role: 技术负责人
    need: 量化评分决策依据
  key_constraints:
    technical: 6 个测试器落地 (Schema/Trace/Semantic/Overlap/Replay/Executable)
    deliverable: 统一报告格式 (report.json / scorecard.md)
    cost: 三层成本控制策略
    maintenance: 黄金样本集维护
  success_criteria:
  - 6 个测试器全部落地
  - 统一报告格式标准化
  - 黄金样本集维护与自动回归
  - 三层成本控制策略执行
