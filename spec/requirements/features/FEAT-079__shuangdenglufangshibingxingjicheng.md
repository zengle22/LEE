---
id: FEAT-079
ssot_type: feat
title: 双登录方式并行集成
status: active
version: v1
parent_id: EPIC-003
derived_from_ids: []
source_refs:
- EPIC-003#scope
owner: null
tags: []
properties:
  contract_key: feat_008
  identity_kind: ssot
---

# Goal

实现双登录方式并行，用户可以选择使用原有的用户名密码或新的手机号方式登录
# User Value

用户可以选择使用原有的用户名密码或新的手机号方式登录
# Inputs

- 用户名密码
- 或手机号验证码
# Processing

- 加载登录页面
- 展示双登录方式入口
- 处理用户名密码登录请求
- 处理手机号验证码登录请求
- 返回统一的会话Token
# Outputs

- 登录结果
- 会话Token
# Acceptance

- 登录页面同时展示两种登录方式入口
- 两种方式登录后的会话权限一致
- 不影响现有用户名密码登录的性能和可用性
- 双登录方式可独立运行，互不影响
# Acceptance Checks

## AC-008-1

- Scenario: 登录页面展示双入口
- Given: 用户访问登录页面
- When: 页面加载
- Then: 同时展示用户名密码和手机号验证码登录入口
- Trace Hints: UI, TESTSET

## AC-008-2

- Scenario: 用户名密码登录正常
- Given: 用户输入正确的用户名密码
- When: 点击登录
- Then: 登录成功并返回Token
- Trace Hints: UI, TECH, TESTSET

## AC-008-3

- Scenario: 手机号登录正常
- Given: 用户通过手机号验证码登录
- When: 完成验证码验证
- Then: 登录成功并返回Token
- Trace Hints: UI, TECH, TESTSET

## AC-008-4

- Scenario: 双登录方式权限一致
- Given: 两种方式分别登录
- When: 对比会话权限
- Then: 两种方式获得的权限完全一致
- Trace Hints: TECH, TESTSET

## AC-008-5

- Scenario: 双登录方式独立运行
- Given: 手机号登录服务异常
- When: 使用用户名密码登录
- Then: 不影响，用户名密码登录正常
- Trace Hints: TECH, TESTSET
# Dependencies

- FEAT-003
# Non Goals

- 不实现登录方式切换动画效果（UI优化不属于本次范围）
