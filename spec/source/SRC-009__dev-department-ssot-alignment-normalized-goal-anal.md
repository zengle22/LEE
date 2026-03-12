---
id: SRC-009
ssot_type: src
title: Dev Department SSOT Alignment - Normalized Goal Analysis
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
frozen_at: '2026-03-12T16:44:14.947994'
---

normalization_id: NGA-LEE-DEV-008-001
src_id: SRC-LEE-DEV-008-001
title: Dev Department SSOT Alignment - Normalized Goal Analysis
version: v1.0.0
created_at: '2026-03-12'
status: normalized
core_goal:
  statement: '建立 Dev 部门在三轴 SSOT 体系下的正式定位：

    能把需求轴稳定翻译成交付轴，并把实现结果稳定收口到证据轴。

    '
  primary_objective: '实现双主入口工作流收口（Feature Delivery L2 + Bugfix Delivery L2），

    补齐完整交付主链，将 Dev 部门从"实现能力"升级为"交付治理能力"。

    '
  success_indicators:
  - metric: 入口收敛度
    target: 仅保留 2 个 Dev 主入口
    current: 多路径并存
  - metric: 三轴对齐完整度
    target: 需求轴→交付轴→证据轴 100% 映射
    current: 缺桥状态
  - metric: TECH 设计覆盖率
    target: 所有 FEAT 必须经过 TECH
    current: 部分 FEAT 跳过 TECH
  - metric: 证据收口完整度
    target: 所有交付有 Evidence Pack
    current: 证据分散
business_drivers:
- id: BD-001
  name: 主路径混乱
  problem: 'AI 与人类都无法稳定判断哪条才是当前主路径。

    Contract-First L2/L3 模板已形成，但 phase-openspec-flow 试图表达另一套流程，

    README/WORKFLOWS 传播旧入口。

    '
  impact: '新 workflow 继续沿旧上下文生长，无法收敛；

    Dev 工程师每次任务都需要重新判断"应该走哪条路"。

    '
  urgency: high
- id: BD-002
  name: 三轴缺桥
  problem: '需求轴、交付轴、证据轴之间仍然缺桥。

    Dev 部门对外只能表达"会写代码"，不能表达"如何从 FEAT 收敛到可审计交付"。

    '
  impact: '跨部门协作缺乏明确对象边界和握手点；

    无法实现从需求到证据的稳定翻译与收口。

    '
  urgency: high
- id: BD-003
  name: Bugfix 漂移
  problem: 'bugfix 模板与真实 agent/gate 目录命名已经发生漂移；

    batch bugfix 缺乏治理规则，导致多根因混装、验证结果失真、回滚边界模糊。

    '
  impact: '缺陷修复流程缺乏统一入口和治理；

    修复质量难以保证，回滚风险高。

    '
  urgency: medium
- id: BD-004
  name: 交付可预测性不足
  problem: '缺乏 TECH 桥接导致需求理解偏差；

    Evidence Pack 缺位导致无法审计交付完成度。

    '
  impact: '隐性成本高（决策成本、验证成本、偏差成本）；

    难以规模化 AI 辅助开发。

    '
  urgency: medium
target_users:
  primary:
  - persona: Dev 部门工程师
    needs:
    - 清晰的工作流主路径判断
    - 明确的阶段输入/输出定义
    - 可复用的模板和工具
    pain_points:
    - 每次任务都要判断"走哪条路"
    - 新旧模板混淆
  - persona: Dev 部门架构师
    needs:
    - 统一的技术设计锚点（TECH）
    - 跨模块依赖追踪能力
    - 治理规则的可执行性
    pain_points:
    - 技术设计分散在多个文档
    - 无法从 FEAT 追踪到实现
  - persona: 技术负责人
    needs:
    - 交付可预测性度量
    - 治理规则的可审计性
    - 部门效能的量化评估
    pain_points:
    - 无法回答"我们完成了多少"
    - 证据分散难以汇总
  secondary:
  - persona: AI Agent 工作流编排系统
    needs:
    - 明确的入口和阶段定义
    - 结构化的输入/输出契约
    role: 作为工作流的执行者和编排者
  - persona: 跨部门协作者（PM/QA/UI）
    needs:
    - 清晰的对象边界和握手点
    - 可追踪的交付状态
    role: 作为需求输入方或验收方
key_constraints:
  governance_rules:
  - id: KC-001
    name: 双入口限制
    rule: Dev 部门只保留两个主入口：Feature Delivery L2 和 Bugfix Delivery L2
    violation: 不允许再引入第三个 Dev 主入口
    rationale: 确保主路径唯一性，消除选择困惑
  - id: KC-002
    name: TECH 前置
    rule: TECH 是 Dev 将需求轴收敛成交付轴的正式桥接对象
    violation: 不允许从 FEAT 直接跳过 TECH 进入大规模实现
    rationale: 建立需求到实现的稳定翻译层，减少理解偏差
  - id: KC-003
    name: 证据收口
    rule: Evidence Pack 是证据轴正式收口对象，不只是文件打包动作
    violation: 不允许让 Evidence Pack 缺位后直接宣称"已完成交付"
    rationale: 确保所有交付可审计、可追踪
  - id: KC-004
    name: Bugfix 粒度控制
    rule: 默认 1 bug -> 1 bugfix workflow instance
    exception: 只有满足五同原则时才允许 batch（同模块、同根因、同策略、同验证面、同窗口）
    rationale: 避免多根因混装、验证结果失真、回滚边界模糊
  - id: KC-005
    name: 旧路径降级
    rule: phase-openspec-flow 等旧路径降级为 draft/deprecated
    violation: 不允许继续把旧路径当作当前现役主链扩展
    rationale: 强制收敛到新主路径，避免新旧并存
  shared_input_rule:
    description: 所有 Dev workflow 必须遵守的输入规范
    required_fields:
    - formal_ssot_id: 上游最小独立验收需求对象（FEAT/TASK）的正式 ID
    - source_refs: 指向需求/架构/决策的引用集合
    - governing_adrs: 对当前交付有约束力的已冻结 ADR 列表
    - repo_context: 仓库路径、module、环境、账号、种子数据等
value_proposition:
  for_users:
  - 清晰的双入口选择：Feature 或 Bugfix，首次判断即可确定工作流
  - 完整的主链指引：从输入到输出的每个阶段都有明确定义
  - 降低决策成本：消除新旧路径混淆带来的隐性成本
  for_business:
  - 交付可预测性提升：从"实现能力"升级为"交付治理能力"
  - 审计能力建立：所有交付可通过 Evidence Pack 追溯
  - AI 辅助开发基础：为规模化自动化建立治理框架
  for_organization:
  - 工程效能参考范式：SSOT 三轴体系成为组织级最佳实践
  - 跨部门协作规范：明确的对象边界和握手点
priority:
  level: P0
  rationale: '这是 Dev 部门治理基础能力建设，阻塞后续规模化交付和 AI 辅助开发。

    不解决此问题，所有新 workflow 将继续沿旧上下文生长，无法收敛。

    '
  timeline: 4-6 周分阶段实施
  phases:
  - phase: 1
    duration: 1-2周
    focus: 冻结 Dev workflow canonical family
    deliverable: Feature/Bugfix L2 定义 + L3 家族清单
  - phase: 2
    duration: 1周
    focus: 更新文档，封旧入口
    deliverable: README/WORKFLOWS 更新 + 旧路径标记
  - phase: 3
    duration: 1-2周
    focus: 补齐 L3 阶段
    deliverable: tech_design_l3 + evidence_pack_l3
  - phase: 4
    duration: 1-2周
    focus: 重写 bugfix 家族
    deliverable: bugfix_delivery_l2 + L3 家族
risk_summary:
  high:
  - item: Evidence Pack 集成复杂度
    mitigation: 将 evidence_pack_l3 作为独立阶段投入设计
  medium:
  - item: 新旧 workflow 并行混淆
    mitigation: 按 Migration Order 逐步替换，先冻结再封入口
  - item: TECH 强制前置的采用阻力
    mitigation: 明确 FEAT 1->1 TECH 默认关系，简化创建流程
upstream_refs:
  raw_input_intake:
  - product-goal-analysis.json
  - src-dev-ssot-alignment.yaml
  governing_adrs:
  - ADR-008 (primary)
  - ADR-001, ADR-003, ADR-005, ADR-006, ADR-007
normalization_check:
  core_goal_extracted: true
  business_drivers_identified: true
  target_users_profiled: true
  key_constraints_documented: true
  value_proposition_defined: true
  priority_assessed: true
  risks_summarized: true
  ready_for_src_convergence: true
