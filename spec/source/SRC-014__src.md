---
id: SRC-014
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
frozen_at: '2026-03-12T20:13:34.283798'
---

input_id: ADR-011
input_type: ADR
input_title: 需求链一致性测试体系建设
input_status: draft
input_version: v1
input_owner: governance
input_tags:
- governance
- ssot
- testing
- requirements
- workflow
goal_primary:
  statement: 将需求链人工目检转化为自动化测试流水线
  description: '替代现有人工评审 `src -> epic -> feat -> task` 链路的大量人工目检工作，

    建立系统化的自动化测试体系，实现需求链质量的持续验证。

    '
  measurable_outcomes:
  - 6个核心测试器可用：Schema Validator, Traceability Checker, Semantic Alignment Judge, Overlap
    Detector, Replay Stability Suite, Executability Judge
  - 5类指标可输出：Trace Completeness, Semantic Alignment Score, Replay Stability Score,
    Overlap Rate, Executability Rate
  - 统一报告格式落地：report.json / scorecard.md
goal_secondary:
- id: G2
  statement: 将需求链本身视为正式被测对象
  description: 而非仅将单个文档作为审阅对象，建立全链路统一校验视角
- id: G3
  statement: 量化指标驱动治理
  description: 通过统一输出实现需求链质量的可测量、可比较、可回归
drivers:
- id: D1
  category: 结构性缺口
  current_pain: Review 面向单阶段、单对象；Schema Validator 只检查字段格式；无 Replay Stability 套件；无统一
    Scorecard
  desired_state: 全链路统一校验视角；校验上下游语义漂移；持续观察 trace/alignment/executability 趋势
- id: D2
  category: 治理范式升级
  description: 从"文档评审模式"转向"系统测试模式"，将需求链视为可测试的软件系统
- id: D3
  category: 效率与成本优化
  benefits:
  - 减少人工硬检查耗时
  - 结构化自动发现"结构正确但语义错"的问题
  - 建立回归测试能力，防止 consistency score 退化
users:
- role: Governance Team
  needs: 治理合规性验证
  scenario: 审计需求链完整性、追溯性
- role: Product Owner
  needs: 需求传递质量
  scenario: 确认 src 意图被正确传递到 epic/feat/task
- role: Workflow/Agent Developer
  needs: 回归测试验证
  scenario: workflow/agent/contract/validator 变更后的质量验证
- role: Review Agent
  needs: 结构化输出规范
  scenario: 输出可比较的结构化结果替代 prose review
- role: CI/CD Pipeline
  needs: 自动化质量门禁
  scenario: 接入需求链回归测试，阻断质量退化
scope_constraints:
  in_scope:
  - src -> epic -> feat -> task 当前主链的一致性测试
  - 结构合法性、引用合法性、trace 完整性
  - 上下游语义覆盖、漂移、遗漏、新增假设检测
  - Task 可执行性检测
  - Replay stability 测试
  - Scorecard 指标与回归比较
  out_of_scope:
  - 直接改写业务需求内容
  - 替代产品 owner 的业务价值判断
  - 替代 dev/qa 的实现与执行验证
  - 把一致性测试等同于 release gate
  - 直接引入新的业务主链对象
implementation_constraints:
- type: 规则优先
  detail: 必填字段、类型合法性、ID 唯一性、引用存在性 → 优先程序规则
- type: 混合策略
  detail: 成本高但价值大的项 → 规则初筛 + LLM 精判
- type: LLM 保留
  detail: 语义漂移、可执行性、重叠检测 → LLM Judge 主判
testing_layer_control:
- level: L0
  type: 规则校验
  coverage: 全量
- level: L1
  type: 相似度/轻量筛查
  coverage: 全量
- level: L2
  type: LLM Judge
  coverage: 异常项、关键样本、抽样项
phased_delivery:
- phase: Phase 1
  focus: Schema Validator + Traceability Checker + Scorecard + Task Executability
  goal: 替代最耗时的人工硬检查
- phase: Phase 2
  focus: Semantic Alignment Judge + Overlap Detector
  goal: 发现"结构正确但语义错"
- phase: Phase 3
  focus: Replay Stability Suite + Golden Set Regression + 趋势比较
  goal: 真正的回归测试能力
output_constraints:
- 必须输出结构化报告 (report.json / scorecard.md)
- 不能只输出自然语言结论
- 必须包含：每层 pass/fail、发现列表、指标摘要、样本对比、基线变化趋势
value_summary: 'Before: "这份文档写得好不好" (主观、离散、不可回归)

  After:  "这条需求链是否通过结构、语义、稳定性、可用性测试" (客观、量化、可自动化回归)

  '
core_values:
- 自动化 → 降低人工评审成本
- 结构化 → 输出可比较、可回归的指标
- 全覆盖 → 从单点 review 到全链路 consistency testing
- 可预防 → 通过回归测试防止质量退化
core_intent: '建立需求链一致性测试体系，将人工目检转化为自动化测试流水线，

  实现需求链质量的可测量、可比较、可回归。

  '
success_criteria:
- 6个核心测试器可用：Schema Validator, Traceability Checker, Semantic Alignment Judge, Overlap
  Detector, Replay Stability Suite, Executability Judge
- 5类指标可输出：Trace Completeness, Semantic Alignment Score, Replay Stability Score, Overlap
  Rate, Executability Rate
- 统一报告格式落地：report.json / scorecard.md
- Golden Set 回归测试体系建立
key_constraints:
- 不直接改写业务需求，只做一致性检测
- 不替代业务价值判断，只验证传递保真度
- 分三阶段落地，Phase 1 聚焦结构校验和可执行性
- L2 LLM Judge 仅用于异常项和抽样，控制成本
