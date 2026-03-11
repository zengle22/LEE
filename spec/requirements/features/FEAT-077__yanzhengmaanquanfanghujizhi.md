---
id: FEAT-077
ssot_type: feat
title: 验证码安全防护机制
status: active
version: v1
parent_id: EPIC-003
derived_from_ids: []
source_refs:
- EPIC-003#scope
owner: null
tags: []
properties:
  contract_key: feat_006
  identity_kind: ssot
---

# Goal

实现验证码安全防护，防止暴力破解保护用户账户安全
# User Value

用户的登录安全得到保障，不会因验证码被暴力破解而导致账户被盗
# Inputs

- 请求来源IP
- 手机号
- 验证码输入
# Processing

- 记录IP请求频率
- 记录手机号请求频率
- 记录验证码错误次数
- 触发限制时拒绝请求
- 记录安全事件日志
# Outputs

- 请求结果（允许/拒绝）
- 限制原因
# Acceptance

- 同一IP每分钟最多请求5次验证码
- 同一手机号每分钟最多请求1次验证码
- 验证码错误3次后锁定手机号15分钟
- 同一IP连续10次验证码错误封禁1小时
- 安全事件日志完整记录可追溯
# Acceptance Checks

## AC-006-1

- Scenario: IP频率限制生效
- Given: 同一IP每分钟请求超过5次
- When: 第6次请求验证码
- Then: 系统拒绝请求并返回IP限制提示
- Trace Hints: TECH, TESTSET

## AC-006-2

- Scenario: 手机号频率限制生效
- Given: 同一手机号每分钟请求超过1次
- When: 第2次请求验证码
- Then: 系统拒绝请求并返回频率限制提示
- Trace Hints: UI, TECH, TESTSET

## AC-006-3

- Scenario: 手机号错误锁定生效
- Given: 同一手机号连续错误3次
- When: 第4次提交错误验证码
- Then: 系统锁定该手机号15分钟
- Trace Hints: TECH, TESTSET

## AC-006-4

- Scenario: IP封禁生效
- Given: 同一IP连续10次验证码错误
- When: 第11次错误
- Then: 系统封禁该IP 1小时
- Trace Hints: TECH, TESTSET

## AC-006-5

- Scenario: 安全事件日志完整记录
- Given: 发生安全事件
- When: 系统记录日志
- Then: 日志包含时间、IP、手机号、事件类型等完整信息
- Trace Hints: TECH, TESTSET
# Dependencies

- None
# Non Goals

- 不实现复杂的人机验证（CAPTCHA），但可集成图形验证码作为可选增强
