---
id: SRC-019
ssot_type: src
title: SRC
status: active
version: v1
parent_id: null
derived_from_ids: []
source_refs: []
owner: null
tags: []
properties:
  contract_key: src
  identity_kind: ssot
---

metadata:
  source_type: ADR
  source_id: ADR-015
  source_title: AI 交付护栏与候选结果包闭环治理
  version: '1.0'
  normalized_at: '2026-03-13T00:04:11+08:00'
  upstream_workspace: wf_task_9f012c61
core_objectives:
  mission_statement: '将 LEE 从「已有 AI 参与的工程系统」演进为「默认以 AI 高吞吐为前提设计的交付系统」，

    建立系统化的 AI 交付治理框架。

    '
  objectives:
  - id: OBJ-001
    title: 建立候选结果包标准
    description: 所有 AI 产出均以结构化 candidate package 形式呈现
    measurable: true
    metric: candidate package 形成率 = 100%
  - id: OBJ-002
    title: 分离生成与完成语义
    description: 生成者不自证完成，由独立 gate 闭环确认
    measurable: true
    metric: 生成者自认证率 = 0%
  - id: OBJ-003
    title: 系统化交付护栏
    description: 关键约束从「提示词化」升级为「系统化」
    measurable: true
    metric: 约束系统化率 = 100%
  - id: OBJ-004
    title: 证据默认产出
    description: evidence 成为交付的默认组成部分，而非事后补记
    measurable: true
    metric: 证据完整率 = 100%
  - id: OBJ-005
    title: 回退能力同等重要
    description: 任何交付必须具备明确的回滚路径和冻结机制
    measurable: true
    metric: 失败时可回退率 ↑
business_drivers:
  problem_driven:
  - id: P1
    title: 完成语义模糊
    problem: 代码写完、文档生成、测试通过被误当成「任务完成」
    pain_point: 未考虑 canonical path、真实系统边界、spec/tests/evidence 更新、gate 通过
    consequence: 伪完成导致技术债务和治理缺口
  - id: P2
    title: 上下文漂移
    problem: 长链路、多文件、多阶段任务中关键约束容易漂移
    pain_point: 非目标被误做、禁止路径被误碰、局部通过误解为全链闭环
    consequence: 上游 acceptance criteria 在下游被稀释
  - id: P3
    title: 证据碎片化
    problem: run 产物多但缺乏统一 candidate package
    pain_point: 审阅者需自行拼接：改了什么、没改什么、跑了哪些验证、哪些风险未覆盖
    consequence: review 成本上升，gate 质量下降
  - id: P4
    title: 静默治理绕过
    problem: canonical path、required validations、forbidden paths 不是系统硬约束
    pain_point: 执行 agent 可能在高速产出下绕过治理边界
    consequence: 治理形同虚设
  opportunity_driven:
  - id: O1
    title: 治理基础已具备
    description: 已有 `.workflow` 运行时、`spec/` 链路、`tests/`、`evidence/`
    value: 可在现有基础上升级而非从零建设
  - id: O2
    title: 决策边界已收敛
    description: ADR 与 gate 设计已逐步收敛 review/approval/freeze 职责
    value: 可直接接入新治理层
  - id: O3
    title: 高吞吐前提设计
    description: AI 生成速度已超过人工审阅速度，倒逼治理升级
    value: 先发建立 AI 时代交付标准
target_users:
  primary_roles:
  - role_id: USER-001
    name: AI 执行器
    alias: Generator Agent
    type: 生成者
    core_need: 清晰的约束边界、明确的完成标准、可预期的审查流程
  - role_id: USER-002
    name: 审查者
    alias: Reviewer
    type: 审阅者
    core_need: 统一的审查对象、完整的证据包、显式的风险暴露
  - role_id: USER-003
    name: 审批者
    alias: Approver
    type: 决策者
    core_need: 可追溯的证据链、系统影响面分析、回退方案
  - role_id: USER-004
    name: 治理管理员
    alias: Governance Admin
    type: 约束维护者
    core_need: 硬约束的可配置性、违规自动检测、升级路径定义
  user_journey: "[AI 执行器] 生成 candidate package \n  → [Auto Gate] 自动检查 \n  → [Review\
    \ Gate] 影响面审阅 \n  → [Approval Gate] 正式放行 \n  → [系统] 冻结状态 + 证据链存档\n"
key_constraints:
  governance_principles:
  - principle: 生成与完成必须分离
    description: 禁止生成者自证完成
  - principle: 速度提升不能换取治理降级
    description: 高吞吐 ≠ 低质量
  - principle: 交付护栏必须系统化
    description: 约束进系统，不进提示词
  - principle: 证据必须是默认产物
    description: 非事后补记
  - principle: 回退能力必须与放行能力同等重要
    description: 可进可退
  guardrail_layers:
  - layer: 候选结果包层
    requirements:
    - 原始任务目标
    - completion criteria
    - changed files
    - integration points
    - impact scan
    - validations run
    - tests changed
    - unverified items
    - risks and assumptions
    - criterion-by-criterion evidence playback
  - layer: 验证层
    requirements:
    - 验证必须前置为完成判定的一部分
    - '支持类型: unit / integration / workflow / e2e'
    - 未运行验证项必须显式列出
  - layer: 约束层
    requirements:
    - canonical path allowlist
    - forbidden path denylist
    - legacy/evidence snapshot 保护
    - 高风险动作人审升级条件必须明确
  - layer: 一致性层
    requirements:
    - spec ↔ implementation 对齐
    - evidence 回指 subject
    - completion criteria 证据支撑
    - touched/untouched 区域显式说明
  - layer: 回滚与放行层
    requirements:
    - 产物是否进入可放行边界
    - 失败时回退状态
    - freeze/approval 后证据链
    - 变更可逆性评估
  gate_constraints:
  - gate: Auto Gate
    responsibility: required validations、路径约束、基础一致性、证据完整性
    constraint: 自动化检查，不通过则阻断
  - gate: Review Gate
    responsibility: 系统影响面、未验证项、风险、边界正确性
    constraint: 基于 candidate package 审阅
  - gate: Approval Gate
    responsibility: 正式放行、freeze、风险接受、阶段完成
    constraint: 必须引用 candidate package 和 evidence
  path_constraints:
  - 优先 canonical path
  - 禁止平行实现
  - 禁止误改 legacy/snapshots
  - 风险路径变更在 Auto Gate 或 Review Gate 阻断或升级
  - 禁止通过临时副本、平行目录、copy-path 规避真实集成
  rejected_options:
  - option: 仅提示词治理
    reason: 长链路约束易漂移、规则无法复用、无法审计
  - option: 测试通过即完成
    reason: 不等于改在正确边界、不等于 spec/evidence 闭环、不等于风险接受
  - option: 生成者自认证
    reason: 削弱 gate 意义、review 退化为装饰、无法承接高吞吐
value_metrics:
  process_metrics:
  - metric: candidate package 形成率
    target: 100%
  - metric: 验证前置率
    target: 100%
  - metric: 约束系统化率
    target: 100%
  - metric: 证据完整率
    target: 100%
  outcome_metrics:
  - metric: review 效率
    direction: 提升
    indicator: 审阅时间 ↓ (统一 package 降低拼接成本)
  - metric: gate 质量
    direction: 提升
    indicator: 假通过率 ↓ (系统化检查减少绕过)
  - metric: 回退能力
    direction: 提升
    indicator: 失败时可回退率 ↑ (明确回滚路径)
  - metric: 合规性
    direction: 提升
    indicator: canonical path 遵守率 ↑ (系统硬约束)
normalization_summary:
  what: 建立 AI 交付护栏系统，统一 candidate result package 标准
  why: 治理 AI 高吞吐交付的完成语义模糊、上下文漂移、证据碎片化、治理绕过风险
  who: AI 执行器(生成者)、审查者(审阅者)、审批者(决策者)、治理管理员(约束维护者)
  how: 五层护栏(candidate package → validation → constraint → consistency → rollback)
    + 三层 Gate
  boundary: 冻结治理方向和必备能力面，不冻结具体 CLI 命令、数据库 schema、UI 交互细节
  success_criteria: AI 产出默认视为候选物、完成由独立 gate 确认、证据默认产出、约束系统化
downstream_outputs:
  for_src_normalization:
  - 核心目标定义
  - 业务动因梳理
  - 目标用户画像
  - 关键约束清单
  - 价值衡量指标
  for_epic_design:
  - 治理边界定义
  - AI delivery workflow 设计约束
  - review/approval gate 设计约束
  - evidence pack 设计约束
  - candidate package contract 定义约束
