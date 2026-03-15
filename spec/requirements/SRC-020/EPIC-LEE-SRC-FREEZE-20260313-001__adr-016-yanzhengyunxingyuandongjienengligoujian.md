---
id: EPIC-LEE-SRC-FREEZE-20260313-001
ssot_type: epic
title: ADR-016 验证运行源冻结能力构建
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
frozen_at: '2026-03-13T01:50:03.707106'
---

epic_id: EPIC-LEE-SRC-FREEZE-20260313-001
title: ADR-016 验证运行源冻结能力构建
goal: 在 ADR-016 验证运行中建立源标准化与冻结能力，确保执行器配置边界内的工件完整性与路径一致性，支撑自动化架构审查。
scope:
- 实现 source_freeze 执行步骤逻辑
- 验证 frozen_inputs 元数据合规性
- 强制 workspace_artifacts 路径一致性 (E:\ai\LEE\output\design-frozen)
- 集成 qwen3.5-plus 模型进行标准化处理
- 基于冻结状态实现验证运行自动批准
non_goals:
- 定义业务功能需求
- 修改底层业务逻辑
- 实现用户界面功能
- 更改冻结元数据结构
success_metrics:
- 工件路径一致性验证通过率 100%
- 冻结状态标记准确率 100%
- 验证运行自动批准成功率 >= 95%
- 无业务逻辑漂移事件发生
priority: P1
feat_split_principles:
- 执行逻辑与验证逻辑分离
- 模型标准化配置与路径 enforcement 分离
- 元数据验证与审批工作流解耦
- 运行时状态管理与配置定义分离
ssot:
  identity_kind: ssot
  ssot_type: EPIC
  id: EPIC-LEE-SRC-FREEZE-20260313-001
  version: 1.0.0
