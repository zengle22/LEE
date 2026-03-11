---
id: FEAT-078
ssot_type: feat
title: 短信发送容错与备选方案
status: active
version: v1
parent_id: EPIC-003
derived_from_ids: []
source_refs:
- EPIC-003#scope
owner: null
tags: []
properties:
  contract_key: feat_007
  identity_kind: ssot
---

# Goal

实现短信发送容错机制，短信服务故障时提供语音验证码作为备选方案
# User Value

即使短信服务暂时不可用，也能通过备用方式完成登录
# Inputs

- 手机号
- 验证码类型
# Processing

- 调用短信网关发送验证码
- 发送失败时执行重试逻辑
- 重试全部失败后触发语音验证码
- 记录故障日志
- 故障恢复后通知用户
# Outputs

- 发送结果（短信成功/重试中/语音验证码）
# Acceptance

- 短信发送失败后自动重试3次
- 重试间隔为30秒、60秒、120秒（指数退避）
- 重试全部失败后自动提供语音验证码选项
- 故障期间日志完整记录，故障恢复后自动通知用户
- 整体登录成功率≥99.5%（含备用方案）
# Acceptance Checks

## AC-007-1

- Scenario: 短信发送失败后自动重试
- Given: 短信网关返回发送失败
- When: 系统检测到失败
- Then: 系统自动重试，共3次
- Trace Hints: TECH, TESTSET

## AC-007-2

- Scenario: 重试使用指数退避策略
- Given: 需要重试发送
- When: 第1/2/3次重试
- Then: 间隔分别为30秒、60秒、120秒
- Trace Hints: TECH, TESTSET

## AC-007-3

- Scenario: 重试全部失败后提供语音验证码
- Given: 短信重试3次全部失败
- When: 系统判断需要备选方案
- Then: 自动触发语音验证码流程
- Trace Hints: UI, TECH, TESTSET

## AC-007-4

- Scenario: 故障日志完整记录
- Given: 发送故障发生
- When: 系统记录日志
- Then: 日志包含完整的故障信息
- Trace Hints: TECH, TESTSET

## AC-007-5

- Scenario: 整体登录成功率达标
- Given: 包含短信和备用方案
- When: 统计登录成功率
- Then: 成功率≥99.5%
- Trace Hints: TESTSET
# Dependencies

- FEAT-001
# Non Goals

- 不实现人工客服通道（作为兜底方案但不纳入本次FEAT）
