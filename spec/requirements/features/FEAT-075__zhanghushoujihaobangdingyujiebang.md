---
id: FEAT-075
ssot_type: feat
title: 账户手机号绑定与解绑
status: active
version: v1
parent_id: EPIC-003
derived_from_ids: []
source_refs:
- EPIC-003#scope
owner: null
tags: []
properties:
  contract_key: feat_004
  identity_kind: ssot
---

# Goal

实现已有账户的手机号绑定与解绑功能，用户可以绑定手机号后使用手机号登录
# User Value

已有用户名密码账户的用户可以绑定手机号，后续使用手机号登录
# Inputs

- 用户账户信息
- 待绑定/解绑的手机号
- 验证码
# Processing

- 验证用户身份
- 校验手机号是否已被绑定
- 发送绑定验证码
- 验证绑定验证码
- 创建绑定关系
- 验证解绑验证码
- 解除绑定关系
# Outputs

- 绑定结果（成功/失败）
- 当前绑定手机号列表
# Acceptance

- 一个手机号只能绑定一个账户
- 一个账户最多绑定3个手机号
- 绑定需验证短信验证码
- 支持解绑手机号（需二次验证，即需要验证码）
- 解绑后该手机号可重新绑定其他账户
# Acceptance Checks

## AC-004-1

- Scenario: 成功绑定手机号
- Given: 用户通过身份验证并输入待绑定手机号
- When: 完成绑定验证码验证
- Then: 手机号成功绑定到账户
- Trace Hints: UI, TECH, TESTSET

## AC-004-2

- Scenario: 手机号已被其他账户绑定
- Given: 待绑定手机号已绑定到其他账户
- When: 尝试绑定该手机号
- Then: 系统返回绑定失败提示
- Trace Hints: UI, TECH, TESTSET

## AC-004-3

- Scenario: 账户已达绑定上限
- Given: 账户已绑定3个手机号
- When: 尝试绑定第4个手机号
- Then: 系统返回绑定数量已达上限提示
- Trace Hints: UI, TECH, TESTSET

## AC-004-4

- Scenario: 成功解绑手机号
- Given: 用户选择解绑手机号并通过验证码验证
- When: 完成解绑验证码验证
- Then: 手机号成功解绑
- Trace Hints: UI, TECH, TESTSET

## AC-004-5

- Scenario: 解绑后手机号可重新绑定
- Given: 手机号已从原账户解绑
- When: 将该手机号绑定到新账户
- Then: 绑定成功
- Trace Hints: UI, TECH, TESTSET
# Dependencies

- FEAT-001
- FEAT-002
# Non Goals

- 不处理账户合并（超出当前范围）
