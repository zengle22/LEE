---
id: SRC-003
ssot_type: src
title: LEE 主动智能体演进方向预留需求
status: draft
version: v1
parent_id: null
derived_from_ids: []
source_refs: []
owner: architecture
tags:
- agent
- autonomy
- skill
- roadmap
properties: {}
---

# Background

LEE 当前已经具备工作流编排、状态管理、人工门禁、Agent/Skill 概念和 SSOT 治理链，但整体运行模式仍以“用户显式触发 -> workflow 执行”为主。

在分析《构建会思考的测试Agent：从自动化到自主智能的演进》后，可以确认一个值得长期预留的方向：

- 将 LEE 从“被动工作流编排框架”扩展为“受治理约束的主动智能体操作底座”
- 在不破坏现有 workflow-first、gate-first、SSOT-first 边界的前提下，引入轻量自主感知与能力装配机制

# Problem Statement

当前 LEE 的核心能力强在“规划后执行”，弱在“持续感知后决定是否需要执行”。

这会带来几个长期缺口：

- 缺少统一的轻量触发/巡检层，很多事情只能靠人或外部脚本发起
- Skill 已被提出为核心能力，但还缺少声明式注册、过滤、装配的统一模型
- PM Agent / workflow 负责解释任务，但没有明确的“目标驱动”预留语义
- 执行前解释、预演、计划透明化能力还没有被定义为正式演进目标

这些缺口短期不阻塞 LEE 作为编排框架使用，但会限制其向更高层 Agent Runtime 演进。

# Target User

- LEE 框架维护者
- 未来负责 Agent Runtime、workflow 入口和治理能力的架构设计者
- 需要在项目中基于 LEE 承载主动巡检、目标驱动执行能力的产品团队

# Trigger Context

本需求来自对企业测试数字人体系的外部案例分析。该案例验证了以下方向具备工程价值：

- 轻量感知/决策层与重量执行编排层分离
- 能力以 Skill 形式声明式装配，而不是全部堆入单一 Agent
- 规则触发与目标驱动共存
- 执行前提供预测试/预演，增强可解释性和安全性

LEE 当前无需立即实现这些能力，但应先把它们冻结为正式演进源对象，避免后续讨论再次漂移成零散灵感。

# Business Motivation

为该方向补一份薄 SRC 的目的不是立刻做“大而全数字人平台”，而是：

- 为后续 `EPIC / FEAT / ADR / TECH` 提供可追溯的正式源输入
- 把“主动智能体演进”限定为受治理约束的框架扩展，而不是旁路现有 orchestrator 的新系统
- 为后续是否建设 trigger engine、skill registry、goal planner、preflight 能力提供统一问题定义

# Constraints

- 本轮只做未来方向预留，不承诺立即实现
- 不新建并行 orchestrator、并行 runtime 或独立 agent 平台
- 不削弱现有 workflow-first、gate-first、SSOT-first 治理边界
- ADR 负责约束架构边界，不能替代该 SRC 作为业务主链源对象
- 后续若进入实施，必须优先复用现有 `lee cli`、orchestrator、artifacts、verifier 入口

# Non-Goals

- 本轮不实现 trigger engine、skill engine、goal planner
- 本轮不改动现有 CLI 命令面或 workflow 模板
- 本轮不引入新数据库、新服务进程或新部署拓扑
- 本轮不把外部文章里的数字人模型原样搬入 LEE

# Success Criteria

- 形成一份可被冻结、可被 `EPIC / FEAT` 追溯的正式 `SRC`
- 明确“主动智能体演进”是 LEE 的未来方向之一，而非当前版本承诺
- 为后续 ADR 提供合法的主链来源，避免直接用 ADR 替代 SRC
- 后续讨论该方向时，可统一引用此 SRC，而不是重复从外部文章重新起题
