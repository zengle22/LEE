---
id: FEAT-073
ssot_type: feat
title: 短信验证码验证服务
status: active
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
---

# Goal

实现验证码验证逻辑，系统确认验证码有效性后允许用户继续登录流程
# User Value

系统确认验证码有效性后允许用户继续登录流程
# Inputs

- 手机号
- 用户输入的6位验证码
# Processing

- 查询对应手机号的验证码记录
- 校验验证码是否过期
- 比对用户输入与存储的验证码
- 记录验证错误次数
- 超过错误次数后锁定手机号
- 验证成功后清除验证码记录
# Outputs

- 验证结果（成功/失败/锁定/过期）
- 剩余错误次数
# Acceptance

- 验证码验证准确率100%
- 验证码错误3次后锁定该手机号15分钟
- 验证成功后清除验证码记录（防止复用）
- 验证响应时间<500ms
# Acceptance Checks

## AC-002-1

- Scenario: 正确验证码验证成功
- Given: 用户输入正确的6位验证码
- When: 提交验证码
- Then: 系统返回验证成功
- Trace Hints: UI, TECH, TESTSET

## AC-002-2

- Scenario: 错误验证码验证失败
- Given: 用户输入错误的验证码
- When: 提交验证码
- Then: 系统返回验证失败并提示剩余次数
- Trace Hints: UI, TECH, TESTSET

## AC-002-3

- Scenario: 错误3次后手机号被锁定
- Given: 同一手机号连续错误3次
- When: 第4次提交验证码
- Then: 系统返回锁定提示，15分钟内禁止验证
- Trace Hints: UI, TECH, TESTSET

## AC-002-4

- Scenario: 过期验证码被拒绝
- Given: 验证码已超过5分钟有效期
- When: 提交验证码
- Then: 系统返回验证码已过期提示
- Trace Hints: UI, TECH, TESTSET
# Dependencies

- FEAT-001
# Non Goals

- 不处理登录会话创建（FEAT-003负责）
