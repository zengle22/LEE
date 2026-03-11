---
id: FEAT-072
ssot_type: feat
title: 短信验证码发送服务
status: active
version: v1
parent_id: EPIC-003
derived_from_ids: []
source_refs:
- EPIC-003#scope
owner: null
tags: []
properties:
  contract_key: feat_001
  identity_kind: ssot
---

# Goal

实现短信验证码发送功能，用户输入手机号后可立即收到6位数字验证码短信
# User Value

用户输入手机号后可立即收到6位数字验证码短信
# Inputs

- 手机号（国内11位或国际E.164格式）
- 验证码类型（登录/绑定/解绑等）
# Processing

- 校验手机号格式合法性
- 检查发送频率限制（每手机号每60秒1次）
- 生成6位随机数字验证码
- 调用短信网关发送验证码
- 记录验证码发送日志
# Outputs

- 验证码发送结果（成功/失败/频率限制）
- 发送时间戳
# Acceptance

- 验证码发送成功率≥99%
- 验证码有效期为5分钟
- 单个手机号每60秒只能请求1次验证码
- 支持国内手机号（11位以1开头）和国际手机号（E.164格式，以+国家代码开头）
# Acceptance Checks

## AC-001-1

- Scenario: 国内手机号验证码发送成功
- Given: 用户输入有效的国内手机号（11位以1开头）
- When: 点击发送验证码按钮
- Then: 系统发送验证码并返回成功响应
- Trace Hints: UI, TECH, TESTSET

## AC-001-2

- Scenario: 国际手机号验证码发送成功
- Given: 用户输入有效的国际手机号（E.164格式，如+1-xxx-xxx-xxxx）
- When: 点击发送验证码按钮
- Then: 系统发送验证码并返回成功响应
- Trace Hints: UI, TECH, TESTSET

## AC-001-3

- Scenario: 频率限制阻止频繁请求
- Given: 同一手机号在60秒内已发送过验证码
- When: 再次点击发送验证码按钮
- Then: 系统返回频率限制提示
- Trace Hints: UI, TECH, TESTSET

## AC-001-4

- Scenario: 无效手机号格式被拒绝
- Given: 用户输入无效的手机号格式
- When: 点击发送验证码按钮
- Then: 系统返回格式错误提示
- Trace Hints: UI, TECH, TESTSET
# Dependencies

- None
# Non Goals

- 不实现语音验证码发送（FEAT-007负责）
- 不实现本机号码免密登录
