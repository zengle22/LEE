---
id: FEAT-074
ssot_type: feat
title: 手机号登录会话管理
status: active
version: v1
parent_id: EPIC-003
derived_from_ids: []
source_refs:
- EPIC-003#scope
owner: null
tags: []
properties:
  contract_key: feat_003
  identity_kind: ssot
---

# Goal

实现手机号登录后的会话管理，用户完成验证码验证后自动登录进入系统
# User Value

用户完成验证码验证后自动登录进入系统
# Inputs

- 验证通过的手机号
- 用户基本信息
# Processing

- 查询或创建用户账户
- 生成会话Token
- 创建会话记录
- 设置Token有效期（7天）
- 返回用户ID和基本信息
# Outputs

- 会话Token
- 用户ID
- 用户基本信息
# Acceptance

- 会话Token有效期为7天
- 登录成功后返回用户ID和基本信息
- 同一设备多端登录可共存（最多5个设备）
- 会话创建时间<1秒
# Acceptance Checks

## AC-003-1

- Scenario: 验证码验证成功后创建会话
- Given: 用户通过验证码验证
- When: 系统完成验证
- Then: 系统创建会话并返回Token
- Trace Hints: UI, TECH, TESTSET

## AC-003-2

- Scenario: 会话Token有效期为7天
- Given: 用户登录成功获取Token
- When: 使用Token访问系统
- Then: Token在7天内持续有效
- Trace Hints: TECH, TESTSET

## AC-003-3

- Scenario: 多端登录可共存
- Given: 用户已在5个设备登录
- When: 第6个设备登录
- Then: 系统允许登录并可继续使用
- Trace Hints: TECH, TESTSET

## AC-003-4

- Scenario: 会话创建响应时间满足要求
- Given: 验证码验证通过
- When: 创建会话
- Then: 会话创建时间<1秒
- Trace Hints: TECH, TESTSET
# Dependencies

- FEAT-002
# Non Goals

- 不处理会话续期/刷新（由现有会话机制处理）
