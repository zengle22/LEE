---
id: EPIC-SRC-009
ssot_type: epic
title: Dev Department SSOT Alignment - Delivery Governance Foundation
status: frozen
version: v1
parent_id: null
derived_from_ids:
- id: SRC-009
  version: v1
source_refs:
- SRC-009
owner: null
tags: []
properties:
  manual_materialization: true
  materialized_from_workflow: wf_task_24fc5dec
---

# Dev Department SSOT Alignment - Delivery Governance Foundation

epic_id: EPIC-SRC-009
title: Dev Department SSOT Alignment - Delivery Governance Foundation
goal: 建立 Dev 部门在三轴 SSOT 体系下的正式定位，实现双主入口工作流收口（Feature Delivery L2 + Bugfix Delivery L2），补齐完整交付主链，将 Dev 部门从'实现能力'升级为'交付治理能力'。
scope:
- Feature Delivery L2 工作流定义：建立从 FEAT 到 Evidence Pack 的完整 Feature 交付主链
- Bugfix Delivery L2 工作流定义：建立从 BUG 到 Evidence Pack 的完整 Bugfix 交付主链
- TECH 桥接对象设计：作为需求轴收敛成交付轴的正式桥接层，建立 FEAT→TECH→Implementation 的稳定翻译路径
- Evidence Pack 收口机制：作为证据轴正式收口对象，确保所有交付可审计、可追踪
- L3 阶段家族补齐：Contract Design、Backend Development、Frontend Development、Integration、Evidence Pack 等阶段定义
- 旧路径降级治理：phase-openspec-flow 等旧路径标记为 deprecated，README/WORKFLOWS 更新指向新主入口
- 共享输入规范落地：所有 Dev workflow 统一遵守共享输入规范，并在 Feature Delivery L2 中显式声明 formal_ssot_id、source_refs、governing_adrs、repo_context、repo_frontend、repo_backend
- Bugfix 粒度控制规则：默认 1 bug → 1 bugfix workflow instance，五同原则 batch 例外机制
non_goals:
- 修改需求轴上游（FEAT 定义方式）——仅消费 FEAT，不改变其产生机制
- 修改证据轴下游（Evidence Pack 审计规则）——仅生产 Evidence Pack，不干预其审计逻辑
- 重写所有历史 workflow 文件——仅标记旧路径为 deprecated，不强制迁移历史任务
- 实现具体的技术代码生成——聚焦于工作流治理框架，不介入具体实现技术
- 建立跨部门的新协作协议——仅明确 Dev 部门内部治理规则，不扩展跨部门协议边界
- 提供通用的 workflow 模板市场——仅针对 Dev 部门特定场景，不做通用化抽象
success_metrics:
- 入口收敛度 = 2（仅保留 Feature Delivery L2 和 Bugfix Delivery L2 两个 Dev 主入口）
- 三轴对齐完整度 = 100%（需求轴→交付轴→证据轴全链路映射，无断点）
- TECH 设计覆盖率 = 100%（所有 FEAT 必须经过 TECH 才能进入大规模实现阶段）
- 证据收口完整度 = 100%（所有交付必须有 Evidence Pack，无缺位交付）
- 旧路径活跃度 = 0（phase-openspec-flow 等旧路径不再接收新任务）
- Bugfix 粒度合规率 ≥ 95%（单 bug 单 workflow instance，batch 需满足五同原则并审批）
priority: P0
feat_split_principles:
- 按工作流层级拆分：L2 编排层与 L3 执行层独立成 FEAT，允许并行开发
- 按交付类型拆分：Feature Delivery 与 Bugfix Delivery 形成独立 FEAT 族系，避免类型混淆
- 按阶段边界拆分：Contract Design、Backend、Frontend、Integration、Evidence Pack 各阶段可独立成 FEAT，保持阶段内聚
- 按治理对象拆分：旧路径降级、入口收敛、共享规范落地作为独立治理 FEAT，与业务 FEAT 并行
- 按依赖顺序拆分：先冻结 L2 定义，再补齐 L3 阶段；先标记旧路径 deprecated，再迁移文档入口
- 保持 FEAT 可验收性：每个 FEAT 必须对应可审计的 Evidence Pack 产出物
source_refs:
- SRC-009
ssot:
  identity_kind: ssot
  ssot_type: EPIC
  parent: None
  derived_from: SRC-009
