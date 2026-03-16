---
id: TECH-FEAT-SRC-009
ssot_type: tech
title: tech_design
status: frozen
version: v1
parent_id: FEAT-SRC-009-006
derived_from_ids: []
source_refs: []
owner: null
tags: []
properties:
  contract_key: tech_spec
  identity_kind: ssot
frozen_at: '2026-03-13T00:53:50.485041'
workflow_instance_id: wf-tech-feat-src-009__tech-design-20260316
---

contract_type: frozen-technical-architecture
contract_version: v1.0.0
metadata:
  contract_id: FTA-20260313-001
  status: FROZEN
  is_frozen: true
  derived_from_feat: FEAT-SRC-009-006
  governing_adrs:
  - ADR-008
  frozen_at: '2026-03-13T00:00:00+08:00'
  reviewer_approval_pending: true
architecture_decisions:
  tech_stack:
  - layer: Workflow Orchestration
    technology: LEE Workflow Engine (L2/L3 Template System)
    reasoning: 基于 ADR-008 的三轴 SSOT 模型，L2 作为编排入口，L3 作为具体执行阶段，确保需求轴到交付轴的稳定翻译
  - layer: API Contract Layer
    technology: YAML-based Contract Schema with JSON Schema Validation
    reasoning: 契约优先原则要求 API 契约作为结构真相源，JSON Schema 提供机器可验证性，YAML 提供人类可读性
  - layer: Backend Runtime
    technology: Go 1.21+ with Gin/Echo Framework
    reasoning: DEV 宪法规定 Go 后端工程师 Agent 存在，Go 提供强类型、高性能、并发安全的后端运行时
  - layer: Frontend Runtime
    technology: Vue 3 + UniApp + TypeScript
    reasoning: DEV 宪法规定 UniApp 前端工程师 Agent 存在，UniApp 支持多端部署，TypeScript 提供类型安全
  - layer: Testing Framework (Backend)
    technology: Go testing/stdlib + testify + gocov
    reasoning: TDD 模式要求，testify 提供断言和 mock 能力，gocov 提供覆盖率报告（阈值≥80%）
  - layer: Testing Framework (Frontend)
    technology: Vitest + Vue Test Utils
    reasoning: TDD 模式要求，Vitest 提供快速单元测试，Vue Test Utils 提供组件测试能力
  - layer: Code Quality
    technology: golint + go vet (Backend) / ESLint + Prettier (Frontend)
    reasoning: DEV 宪法第 14 条质量标准强制要求
  - layer: Evidence Pack
    technology: YAML-based Evidence Schema with Git Diff Integration
    reasoning: ADR-008 规定 Evidence Pack 是证据轴正式收口对象，需收敛 diff、test、review、gate 等证据
  - layer: Gate System
    technology: YAML-based Gate Definition with PASS/FAIL/BLOCKED Status
    reasoning: DEV 宪法第 17 条门禁机制要求 Contract Freeze Gate、Dev Gate、Smoke Gate 三层守门
  core_components:
  - name: TECH (Technical Bridge Object)
    responsibilities: 作为需求轴收敛成交付轴的正式桥接层，将 FEAT 翻译为技术实现规格，约束 API Contract 设计
    dependencies:
    - FEAT (frozen)
    - ADR-008
    - repo_context
  - name: API Contract (frozen-technical-architecture-contract)
    responsibilities: 定义技术架构的输出 Schema，包括技术选型、核心组件、风险管理三大模块
    dependencies:
    - TECH
    - JSON Schema Draft-07
  - name: L2 Feature Delivery Workflow
    responsibilities: 作为特性开发主入口，编排 Contract Design → Frontend/Backend Dev → Integration
      → Evidence Pack → Smoke Gate 全流程
    dependencies:
    - template.dev.feature_delivery_l2
    - L3 templates
  - name: L3 Backend Development Workflow
    responsibilities: 执行 UTDD 循环（UT → Impl → Refactor），产出代码、单元测试、覆盖率报告，遵循 TDD 模式
    dependencies:
    - template.dev.feature_be_l3
    - API Contract (frozen)
    - Go Backend Engineer Agent
  - name: L3 Frontend Development Workflow
    responsibilities: 执行 UTDD 循环，产出前端代码、组件测试、覆盖率报告，类型从 contract 生成
    dependencies:
    - template.dev.feature_fe_l3
    - API Contract (frozen)
    - UniApp Frontend Engineer Agent
  - name: L3 Integration Workflow
    responsibilities: 执行前后端集成测试，验证契约一致性，产出集成测试报告，通过率阈值 100% 关键路径
    dependencies:
    - template.dev.feature_integration_l3
    - Backend Outputs
    - Frontend Outputs
  - name: L3 Evidence Pack Workflow
    responsibilities: 收敛 diff、test、review、gate 等证据，映射回 FEAT/TECH/Contract/Acceptance，生成覆盖结论
    dependencies:
    - template.dev.evidence_pack_l3
    - DEV_EVIDENCE_PACK schema
  - name: Tech Architect Agent
    responsibilities: 基于冻结的模块级需求进行技术选型、架构设计、高风险点识别
    dependencies:
    - contracts/frozen-module-requirement-contract/v1/schema.json
    - contracts/frozen-technical-architecture-contract/v1/schema.json
  - name: Contract Freeze Gate
    responsibilities: 验证 API Contract 是否满足冻结条件，阻止未冻结契约进入实现阶段
    dependencies:
    - spec-global/departments/dev/gates/contract-freeze-gate/v1/gate.yaml
  - name: Smoke Gate
    responsibilities: 作为最终守门结论，失败时阻止合并，优先级最高
    dependencies:
    - spec-global/departments/dev/gates/smoke-gate/v1/gate.yaml
  system_architecture:
    description: 三轴 SSOT 架构：需求轴 → 交付轴 → 证据轴
    data_flow: FEAT → TECH → API Contract → FE/BE Implementation → Integration → Evidence
      Pack → Smoke Gate
    governance_flow: ADR → constrains all layers without replacing business source
risk_management:
  high_risk_points:
  - id: RISK-001
    description: TECH 对象缺位风险：从 FEAT 直接进入实现，导致需求到交付的翻译丢失，追溯链断裂
    mitigation_plan: 强制执行 TECH Rule：FEAT 1:1 TECH，在 L2 工作流中设置 Contract Freeze Gate，TECH
      未冻结则阻塞后续阶段
    degradation_strategy: 如发现 TECH 缺失，立即回滚至 Tech Design 阶段，生成 TECH 文档后方可继续
  - id: RISK-002
    description: 契约漂移风险：实现过程中私自修改已冻结的 API Contract，导致前后端接口不一致
    mitigation_plan: 实施契约绑定策略：代码自检查验响应结构与 Contract 完全匹配，发现偏差立即上报
    degradation_strategy: 触发结构性回滚至 Contract Design 阶段，禁止在实现层私自修复契约问题
  - id: RISK-003
    description: Evidence Pack 缺位风险：交付完成后无正式证据闭环，无法验证验收项覆盖
    mitigation_plan: L2 工作流强制包含 Evidence Pack 阶段，无 Evidence Pack 则交付状态不可标记为 completed
    degradation_strategy: 如 Evidence Pack 无法生成，回滚至 Integration 阶段重新验证产出
  - id: RISK-004
    description: TDD 模式失效风险：单元测试覆盖率未达阈值（≥80%）即进入下一阶段
    mitigation_plan: 在 L3 Backend/Frontend 工作流中集成覆盖率门禁，低于 80% 自动失败
    degradation_strategy: 回退至 UT 编写阶段，补充测试直到覆盖率达标
  - id: RISK-005
    description: 多根因混装风险：Bugfix 场景下多个无关 bug 混装修复，导致验证结果失真、回滚边界模糊
    mitigation_plan: 强制执行 ADR-008 Bugfix 粒度规则：1 bug → 1 bugfix workflow，仅当同一模块/根因/策略/验证面/窗口时才允许批量
    degradation_strategy: 发现混装立即拆分，每个 bug 单独进入修复流程
  - id: RISK-006
    description: 环境变量替代 SSOT 风险：使用 runtime config / env ref 替代正式 FEAT/TECH 输入
    mitigation_plan: L2/L3 工作流输入校验强制检查 formal_ssot_id / source_refs / governing_adrs
      存在，环境输入只能作为辅助上下文
    degradation_strategy: 如检测到环境变量替代业务主源，立即终止执行并报错
  - id: RISK-007
    description: 旧入口失效风险：phase-openspec-flow 等旧工作流仍被当作主入口使用，导致与新模板不兼容
    mitigation_plan: 执行 ADR-008 第 8 章资产分类：phase-openspec-flow 降级为 Draft，禁止作为新任务入口
    degradation_strategy: 更新 README/WORKFLOWS 文档封禁旧入口，CI 校验 workflow 引用来源
  - id: RISK-008
    description: Smoke Gate 失效风险：冒烟测试失败仍能合并，导致质量问题流入生产
    mitigation_plan: Smoke Gate 设置最高优先级，失败时强制 blocking，需人类 Gate 审批方可绕过
    degradation_strategy: 触发人类 Gate 审批流程，记录绕过原因和责任人
  uncertainty_points:
  - id: UNC-001
    description: TECH 自动生成可行性：当前 TECH 对象需人工设计，是否可由 AI 自动生成待验证
    backup_plan: 保持 Tech Architect Agent 人工 +AI 协同模式，AI 生成初稿，人类架构师评审后冻结
  - id: UNC-002
    description: 跨仓库集成边界：前后端可能分属不同仓库，Integration 阶段的仓库边界和权限未明确
    backup_plan: 假设单仓库模式优先落地，多仓库场景通过 repo_frontend/repo_backend 参数扩展支持
  - id: UNC-003
    description: Evidence Pack 存储格式：当前只定义 Schema，具体存储位置（Git LFS / artifact store）待定
    backup_plan: 优先使用 Git 仓库内路径存储，后期可迁移至外部 artifact store
  rollback_paths:
    contract_violation: 回滚至 Contract Design 阶段，重新冻结 API Contract
    tech_missing: 回滚至 Tech Design 阶段，生成 TECH 文档
    integration_failure: 如为契约结构问题 → 回滚至 Contract Design；如为实现问题 → 回滚至 Backend/Frontend
      Dev
    evidence_pack_incomplete: 回滚至 Integration 阶段，补充缺失证据
    smoke_gate_failure: 最高优先级回滚，禁止绕过，需人类 Gate 审批
human_approval:
  approval_required: true
  approval_status: PENDING
  approver_role: Dev Department Technical Architect
  approval_checklist:
  - 技术选型理由充分
  - 至少识别 2 个核心技术风险
  - 包含降级与应对策略
  - 回滚路径清晰可执行
  signature_field: 待人类评审签字后填写
  approval_date_field: 待人类评审签字后填写
