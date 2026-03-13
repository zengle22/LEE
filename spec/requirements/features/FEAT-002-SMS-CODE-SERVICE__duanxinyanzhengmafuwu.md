---
id: FEAT-002-SMS-CODE-SERVICE
ssot_type: feat
title: 短信验证码服务
status: active
version: v1
parent_id: EPIC-001-PHONE-LOGIN
derived_from_ids: []
source_refs:
- EPIC-001-PHONE-LOGIN#scope
owner: null
tags: []
properties:
  contract_key: feat_002
  identity_kind: ssot
---

# Goal

构建可靠的短信验证码发送与校验服务，支持手机号验证流程
# User Value

用户可及时、可靠地接收短信验证码，验证码校验准确无误
# Inputs

- 手机号（含国家区号）
- 验证码发送请求
- 验证码校验请求（用户提交的验证码）
# Processing

- 手机号格式校验（国内/国际 E.164 标准）
- 频率限制检查（60秒限发、24小时限10次）
- 防刷保护检查（IP限流、异常检测）
- 6位随机验证码生成
- 调用短信网关发送验证码
# Outputs

- 短信发送结果（成功/失败）
- 验证码校验结果（成功/失败/过期/超限）
- 剩余尝试次数
- 风控拦截提示
- 发送日志与告警
# Acceptance

- 手机号格式校验：严格验证国内手机号格式（1[3-9]xxxxxxxx），支持国际手机号格式验证（E.164 标准）
- 短信发送接口：调用短信网关服务发送 6 位数字验证码，发送成功率 ≥ 99.5%
- 验证码存储：服务端缓存验证码，有效期 5 分钟，支持 Redis/内存存储
- 验证码校验：用户提交验证码后服务端校验，正确返回校验成功，错误返回剩余尝试次数
- 重发限制：同一手机号 60 秒内禁止重复发送，24 小时内发送次数 ≤ 10 次
# Acceptance Checks

## AC-002-SMS-001

- Scenario: 手机号格式校验
- Given: 用户提交手机号
- When: 发送验证码请求
- Then: 系统校验手机号格式，国内格式（1[3-9]xxxxxxxx）或E.164标准
- Trace Hints: TECH, TASK, TESTSET

## AC-002-SMS-002

- Scenario: 短信发送成功率
- Given: 系统调用短信网关
- When: 正常网络条件
- Then: 发送成功率 ≥ 99.5%
- Trace Hints: TECH, TESTSET

## AC-002-SMS-003

- Scenario: 验证码存储与过期
- Given: 验证码发送成功
- When: 存储到缓存
- Then: 验证码有效期为5分钟，存储于Redis/内存
- Trace Hints: TECH, TASK, TESTSET

## AC-002-SMS-004

- Scenario: 验证码校验
- Given: 用户提交验证码
- When: 请求校验
- Then: 正确返回成功，错误返回剩余尝试次数
- Trace Hints: TECH, TASK, TESTSET

## AC-002-SMS-005

- Scenario: 60秒重发限制
- Given: 用户已发送验证码
- When: 60秒内再次请求发送
- Then: 拒绝请求并提示重发冷却时间
- Trace Hints: TECH, TESTSET
# Dependencies

- EPIC-001-PHONE-LOGIN
- FEAT-001-PHONE-LOGIN-UI
# Non Goals

- 不实现用户身份验证和账户绑定逻辑
- 不实现登录态管理和会话保持
- 不接入第三方短信服务商的详细配置（仅保留接口抽象）
- 不实现语音验证码作为备选
