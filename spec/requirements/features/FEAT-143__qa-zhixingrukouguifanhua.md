---
id: FEAT-143
ssot_type: feat
title: QA 执行入口规范化
status: frozen
version: v1
parent_id: EPIC-QA-SSOT-UPGRADE
derived_from_ids: []
source_refs:
- EPIC-QA-SSOT-UPGRADE#scope
owner: null
tags: []
properties:
  contract_key: feat_002
  identity_kind: ssot
frozen_at: '2026-03-12T20:16:11.841230'
---

# Goal

收敛 QA 测试执行入口到 TESTPLAN 下的 TASK，确保正式交付只能通过 RELEASE -> PLAN -> TASK 路径进入执行
# User Value

消除分散执行入口导致的追溯断裂风险，确保所有测试执行行为可被 SSOT 主链完整追踪和审计
# Inputs

- FEAT-QA-SSOT-001 输出的改造后 TESTPLAN/TASK 对象
- EPIC-QA-SSOT-UPGRADE 定义的入口约束（CR-003, CR-007）
- 现有 QA 执行入口清单
- SSOT 执行路径规范
# Processing

- 识别并登记现有所有 QA 执行入口
- 定义标准执行入口：TESTPLAN 下的 TASK
- 实现执行入口路由规则：仅接受 TASK 触发的执行请求
- 实现执行路径校验：RELEASE -> PLAN -> TASK
- 建立执行入口与 SSOT 三轴模型的绑定关系审计
# Outputs

- 仅允许通过 TESTPLAN 下的 TASK 触发执行
- 校验 RELEASE -> PLAN -> TASK 链路的完整性
- 记录所有执行请求的入口来源和路径信息
- 拒绝绕过 TESTPLAN/TASK 的直接执行请求
# Acceptance

- QA 执行入口唯一性验证：所有测试执行必须通过 TESTPLAN 下的 TASK 触发
- RELEASE -> PLAN -> TASK 执行路径完整性校验通过
- 禁止绕过 TESTPLAN/TASK 的直接执行入口，旁路请求被拒绝
- 执行入口与 SSOT 三轴模型的绑定关系可审计
# Acceptance Checks

## AC-003-001

- Scenario: 执行入口唯一性验证
- Given: 系统已部署执行入口路由规则
- When: 提交测试执行请求
- Then: 仅当请求包含有效的 task_ref 且 task 归属 testplan 时才被接受
- Trace Hints: TECH, TASK, UI

## AC-003-002

- Scenario: 执行路径完整性校验
- Given: 存在有效的 TASK 执行请求
- When: 执行前路径校验
- Then: 系统验证 release_ref -> testplan_ref -> task_ref 链路完整且有效
- Trace Hints: TECH, TASK

## AC-003-003

- Scenario: 旁路执行入口阻断验证
- Given: 尝试绕过 TESTPLAN/TASK 直接触发测试执行
- When: 执行旁路请求
- Then: 系统拒绝请求并返回入口规范错误，记录审计日志
- Trace Hints: TECH, TASK, UI

## AC-003-004

- Scenario: 执行入口审计验证
- Given: 系统已完成多次测试执行
- When: 查询执行入口审计日志
- Then: 日志中包含每次执行的入口来源、路径链、时间戳、操作用户
- Trace Hints: TECH, TASK
# Dependencies

- EPIC-QA-SSOT-UPGRADE
- FEAT-QA-SSOT-001
# Non Goals

- 不修改测试执行引擎内部逻辑
- 不替换现有 runner 实现
- 不修改具体测试用例的内容
- 不影响测试结果的判定逻辑
