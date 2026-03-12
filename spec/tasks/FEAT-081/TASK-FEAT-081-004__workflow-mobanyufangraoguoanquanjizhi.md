---
id: TASK-FEAT-081-004
ssot_type: task
title: Workflow 模板与防绕过安全机制
status: active
version: v1
parent_id: FEAT-081
derived_from_ids: []
source_refs:
- FEAT-081#delivery
owner: null
tags: []
properties:
  contract_key: task_feat_081_002
  identity_kind: ssot
---

# Objective

创建 ADR/EPIC/FEAT 三类 workflow 模板，实现 DirectCreationBlocker 防绕过机制

# Description

创建 governance.adr-create、product.epic-create、product.feat-create 三个 workflow 模板（L3 层）。实现 DirectCreationBlocker 安全模块，包含 front_matter workflow_instance_id 验证、Git pre-commit hook、CI pipeline 验证三层防护。集成 pm_workflow API 实现 workflow 启动逻辑。

## Acceptance Mapping
- FEAT-081 / AC-002-002: 命令启动治理流程 - adr_new() 调用 pm_workflow() 启动 workflow
- FEAT-081 / AC-002-004: workflow-only 创建路径生效 - 无 workflow_instance_id 的 SSOT 文件被阻止提交

## Dependencies
- TASK-FEAT-081-001

## Definition Of Done
- spec-global/core/workflows/templates/adr-create/v1/workflow.yaml 创建完成
- spec-global/departments/product/workflows/templates/epic-create/v1/workflow.yaml 创建完成
- spec-global/departments/product/workflows/templates/feat-create/v1/workflow.yaml 创建完成
- DirectCreationBlocker 模块实现 front_matter 验证逻辑
- Git pre-commit hook 脚本配置完成
- CI pipeline 验证步骤添加
- 集成测试验证 workflow 启动和防绕过机制
- TASK 文件已冻结
