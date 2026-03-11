---
id: FEAT-069
ssot_type: feat
title: Gate 三类治理模型定义
status: frozen
version: v1
parent_id: EPIC-003
derived_from_ids: []
source_refs:
- EPIC-003#scope
owner: null
tags: []
properties:
  contract_key: feat_002
  identity_kind: ssot
frozen_at: '2026-03-11T14:48:58.774907'
---

# Goal

明确定义 Gate 与普通人工审批节点的区分标准，建立完整的三类治理模型
# User Value

确保治理流程的标准化和可度量性，用户清晰理解三类 Gate 的语义和触发条件
# Inputs

- SSOT 物化请求
- 当前 Gate 状态
- 用户角色信息
- Gate 类型配置
# Processing

- 解析 Gate 类型配置，识别 Auto/Review/Approval 三类
- 根据 Gate 类型执行对应的决策规则
- 生成 Gate 决策结果和状态输出
- 记录 Gate 审批日志
# Outputs

- Gate 决策结果 (approve/reject/pending)
- Gate 状态变更记录
- 权限模型输出
- 三类 Gate 的语义定义文档
# Acceptance

- Gate 与普通人工审批节点有明确的区分标准
- 三类 Gate (Auto/Review/Approval) 有完整的语义定义
- 三类 Gate 有明确的触发条件和决策规则
- Gate 决策有明确的权限模型和状态输出
# Acceptance Checks

## AC-GATE-001

- Scenario: Gate 与人工审批节点区分标准
- Given: 系统存在审批节点配置
- When: 配置审批节点时
- Then: 用户可选择 Gate 类型或普通人工审批，并明确两者的区分
- Trace Hints: TASK, UI

## AC-GATE-002

- Scenario: 三类 Gate 语义定义
- Given: 系统配置界面
- When: 查看 Gate 类型选项
- Then: 显示 Auto/Review/Approval 三类的完整语义说明
- Trace Hints: UI, TASK

## AC-GATE-003

- Scenario: Gate 触发条件判断
- Given: SSOT 物化请求
- When: 请求进入 Gate 审查阶段
- Then: 系统根据配置判断触发哪种 Gate 类型
- Trace Hints: TECH, TESTSET

## AC-GATE-004

- Scenario: Gate 决策权限模型
- Given: Gate 决策操作
- When: 决策者执行 approve/reject 操作
- Then: 系统验证决策者权限，记录决策结果并更新状态
- Trace Hints: TECH, TASK
# Dependencies

- FEAT-CLI-REFACTOR
# Non Goals

- 不处理 CLI 命令分层的实现细节
- 不定义 Freeze 状态的具体语义
- 不涉及升级路径的自动化实现
