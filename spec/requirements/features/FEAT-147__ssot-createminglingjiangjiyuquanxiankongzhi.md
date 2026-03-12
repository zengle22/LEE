---
id: FEAT-147
ssot_type: feat
title: ssot create命令降级与权限控制
status: frozen
version: v1
parent_id: EPIC-017
derived_from_ids: []
source_refs:
- EPIC-017#scope
owner: null
tags: []
properties:
  contract_key: feat_003
  identity_kind: ssot
frozen_at: '2026-03-12T20:17:54.593232'
---

# Goal

将ssot create命令从推荐主入口降级为internal/admin/maintenance命令，防止普通用户绕过治理链直接创建formal object
# User Value

防止普通用户绕过治理链直接创建formal object，仅允许admin/maintenance场景下使用底层物化原语
# Inputs

- 现有ssot create命令实现
- 权限模型定义(admin/user/maintenance角色)
- CLI参数解析框架
- 审计日志规范
# Processing

- 分析现有ssot create命令的使用场景和调用点
- 设计权限检查机制，识别admin/maintenance角色
- 实现--admin和--maintenance命令行标志解析
- 修改ssot create默认行为，无标志时显示引导信息并退出
- 实现admin标志调用时的审计日志记录
# Outputs

- 降级后的ssot create命令实现
- 权限检查模块
- 审计日志记录功能
- 用户引导信息模板
- 命令降级迁移指南
# Acceptance

- ssot create命令默认禁用或提示使用高层入口
- 添加--admin或--maintenance标志方可执行
- 不带标志执行时给出明确引导信息
- 验收时验证普通用户无法无意调用成功
- admin标志调用时记录审计日志
# Acceptance Checks

## AC-017-003-01

- Scenario: 默认行为降级
- Given: 普通用户执行ssot create命令
- When: 不带--admin或--maintenance标志
- Then: 命令拒绝执行并显示指向高层入口的引导信息
- Trace Hints: UI, TECH, TASK, TESTSET

## AC-017-003-02

- Scenario: admin权限执行
- Given: admin用户执行ssot create命令
- When: 带有--admin标志
- Then: 命令执行成功并记录审计日志
- Trace Hints: TECH, TESTSET

## AC-017-003-03

- Scenario: 审计日志完整性
- Given: 通过--admin标志执行的ssot create操作
- When: 查询审计日志
- Then: 日志包含用户身份、时间戳、操作类型、对象ID
- Trace Hints: TECH, TESTSET
# Dependencies

- FEAT-017-001
# Non Goals

- 不直接删除旧demo或历史命令
