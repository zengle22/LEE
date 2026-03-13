---
id: FEAT-004-LOGIN-SECURITY
ssot_type: feat
title: 登录安全风控
status: active
version: v1
parent_id: EPIC-001-PHONE-LOGIN
derived_from_ids: []
source_refs:
- EPIC-001-PHONE-LOGIN#scope
owner: null
tags: []
properties:
  contract_key: feat_004
  identity_kind: ssot
---

# Goal

构建登录安全风控体系，防止恶意攻击、验证码滥用和账户盗用
# User Value

保障用户账户安全，防止恶意攻击和验证码滥用
# Inputs

- 登录请求上下文（IP、设备信息、时间戳）
- 验证码使用记录
- 账户登录历史
- 异常行为检测信号
# Processing

- 验证码安全策略（6位随机、5分钟有效、单次使用）
- 频率限制执行（60秒限发、连续错误5次锁定30分钟）
- 设备指纹采集与异常设备检测
- 暴力破解行为识别（高频尝试、IP聚集）
- 风控拦截与二次验证触发
# Outputs

- 风控决策结果（放行/拦截/二次验证）
- 安全事件通知
- 风控触发日志
- 异常设备告警
- 人工申诉工单
# Acceptance

- 验证码安全：6 位随机数字，有效期 5 分钟，单次使用有效，使用后立即失效
- 频率限制：同一手机号 60 秒内限发 1 次，连续错误 5 次后锁定 30 分钟
- 设备指纹：记录登录设备信息，异常设备登录时增加二次验证或安全提醒
- 异常检测：识别暴力破解行为（如高频尝试、IP 聚集），触发风控拦截
- 安全通知：新设备登录、密码修改、手机号绑定变更时发送安全提醒通知
# Acceptance Checks

## AC-004-SEC-001

- Scenario: 验证码安全策略
- Given: 系统生成验证码
- When: 用户使用验证码
- Then: 验证码为6位随机数字，5分钟有效，使用一次后立即失效
- Trace Hints: TECH, TASK, TESTSET

## AC-004-SEC-002

- Scenario: 发送频率限制
- Given: 风控系统运行
- When: 监测发送请求
- Then: 同一手机号60秒内限发1次，连续错误5次后锁定30分钟
- Trace Hints: TECH, TESTSET

## AC-004-SEC-003

- Scenario: 设备指纹记录
- Given: 用户发起登录
- When: 记录设备信息
- Then: 采集设备指纹，标记异常设备
- Trace Hints: TECH, TASK, TESTSET

## AC-004-SEC-004

- Scenario: 异常设备二次验证
- Given: 异常设备尝试登录
- When: 风控检测触发
- Then: 要求二次验证或发送安全提醒
- Trace Hints: UI, TECH, TESTSET

## AC-004-SEC-005

- Scenario: 暴力破解检测
- Given: 监测登录请求
- When: 检测到高频尝试或IP聚集
- Then: 触发风控拦截
- Trace Hints: TECH, TASK, TESTSET
# Dependencies

- EPIC-001-PHONE-LOGIN
- FEAT-002-SMS-CODE-SERVICE
- FEAT-003-PHONE-ACCOUNT-BINDING
# Non Goals

- 不实现双因素认证（2FA）
- 不实现生物识别登录（指纹/人脸）
- 不实现实时风控决策引擎（仅基础规则）
- 不修改账户密码策略
