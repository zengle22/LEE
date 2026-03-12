---
id: EPIC-023
ssot_type: epic
title: 需求链自动化一致性测试体系
status: frozen
version: v1
parent_id: null
derived_from_ids: []
source_refs: []
owner: null
tags: []
properties:
  contract_key: epic
  identity_kind: ssot
frozen_at: '2026-03-12T20:59:04.837496'
---

epic_id: EPIC-018
title: 需求链自动化一致性测试体系
goal: 为LEE项目建立覆盖SRC→EPIC→FEAT→TASK四层需求链的自动化一致性测试体系，通过结构、语义、稳定性、可用性四维测试替代人工目检，建立可量化的需求治理标准，为需求治理人员、研发流程管理员和技术负责人提供客观的质量评估与决策依据。
scope:
- Schema测试器：验证四层需求链各节点（SRC/EPIC/FEAT/TASK）的结构合规性，确保字段完整性与类型正确
- Trace测试器：验证需求链的纵向追溯完整性，确保SRC→EPIC→FEAT→TASK的链接无断裂
- Semantic测试器：验证相邻层间的语义一致性，确保需求意图在传递过程中不发生偏差
- Overlap测试器：检测FEAT层与TASK层的功能重叠与边界冲突，确保拆分合理性
- Replay测试器：验证需求链的稳定性与可重现性，确保相同输入产生一致输出
- Executable测试器：验证TASK层任务的可执行性，确保任务描述可被研发人员直接理解并实施
- 统一报告格式：实现report.json结构化报告与scorecard.md评分卡标准化输出
- 黄金样本集：建立并维护覆盖典型场景的标准化测试样本
- 三层成本控制策略：采样控制、缓存机制、增量测试，确保测试体系可持续运行
- CI/CD集成：将测试体系集成至持续集成流程，实现需求变更的自动回归验证
non_goals:
- 不替代需求本身的创作与定义工作，测试体系仅负责验证而非生成需求
- 不涉及具体业务功能的实现与验证，聚焦需求链结构治理而非业务逻辑
- 不替代人工对业务逻辑合理性的主观判断，仅提供结构性和语义性检测
- 不直接修改或修复被检测出的不一致问题，仅输出检测报告供人工决策
- 不覆盖需求链之外的研发流程环节（如代码实现、测试执行、部署发布等）
- 不提供实时告警通知功能，仅生成周期性或触发式的质量报告
success_metrics:
- Trace Completeness ≥ 95%：需求链纵向追溯完整性达到95%以上
- Semantic Alignment ≥ 90%：相邻层间语义一致性评分达到90%以上
- Replay Stability ≥ 98%：相同输入下重复执行结果一致性达到98%以上
- Overlap Rate ≤ 10%：FEAT层功能重叠率控制在10%以内
- Executability ≥ 85%：TASK层任务可执行性评分达到85%以上
- 测试执行时间 ≤ 5分钟：单条需求链的完整测试执行时间控制在5分钟以内
- 报告生成延迟 ≤ 30秒：检测报告从执行完成到报告可用的延迟控制在30秒以内
- 假阳性率 ≤ 5%：测试器误报率控制在5%以内
priority: P0
feat_split_principles:
- 按测试器维度拆分：每个测试器（Schema/Trace/Semantic/Overlap/Replay/Executable）作为独立FEAT，便于并行开发与独立迭代
- 按需求链层级拆分：支持按SRC→EPIC、EPIC→FEAT、FEAT→TASK分层验证，允许按需启用特定层级的测试
- 按治理场景拆分：区分需求变更回归验证、持续监控、治理决策三类场景，提供场景化的测试配置
- 核心与扩展分离：核心测试引擎（采样/缓存/增量控制）作为基础FEAT，各测试器作为扩展FEAT挂载
- 报告与执行分离：测试执行引擎与报告生成分离，支持多种输出格式扩展
- 样本与引擎分离：黄金样本集维护独立于测试引擎，支持样本版本化管理与动态加载
ssot:
  identity_kind: ssot
  ssot_type: EPIC
  ssot_version: '1.0'
  source_problem_id: SRC-018
  author: product-strategist
  created_at: '2026-03-12'
  status: active
