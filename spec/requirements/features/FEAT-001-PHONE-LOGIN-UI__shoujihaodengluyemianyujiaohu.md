---
id: FEAT-001-PHONE-LOGIN-UI
ssot_type: feat
title: 手机号登录页面与交互
status: active
version: v1
parent_id: EPIC-001-PHONE-LOGIN
derived_from_ids: []
source_refs:
- EPIC-001-PHONE-LOGIN#scope
- EPIC-001-PHONE-LOGIN#user_journey
owner: null
tags: []
properties:
  contract_key: feat_001
  identity_kind: ssot
---

# Goal

构建手机号一键登录的页面交互层，提供简洁直观的登录入口和手机号输入体验
# User Value

移动端用户可通过简洁直观的界面快速输入手机号并发起一键登录，减少登录步骤认知负担
# Inputs

- 用户手机号输入
- 国家/地区区号选择
- 一键登录按钮触发事件
# Processing

- 渲染手机号登录入口，与现有登录方式并行展示
- 手机号输入框实时格式校验与格式化显示
- 一键登录按钮状态管理（输入合法手机号后启用）
- 国家区号选择器交互（支持+86/+852/+853）
- 页面加载性能优化（首屏≤1.5s）
# Outputs

- 手机号登录页面渲染
- 格式化后的手机号数据
- 登录请求触发事件
- 错误提示信息
# Acceptance

- 登录页面新增"手机号一键登录"入口，与现有用户名/密码登录方式并行展示
- 手机号输入框支持国内手机号格式自动识别与格式化显示（如 138****1234）
- 一键登录按钮状态管理：输入合法手机号后启用，点击后进入验证码等待状态
- 支持国际手机号格式切换（区号选择器 + 手机号输入），第一阶段支持中国大陆(+86)、中国香港(+852)、中国澳门(+853)
- 页面加载性能：首屏渲染时间 ≤ 1.5 秒，交互响应延迟 ≤ 100ms
# Acceptance Checks

## AC-001-UI-001

- Scenario: 手机号登录入口展示
- Given: 用户进入登录页面
- When: 页面加载完成
- Then: 页面显示"手机号一键登录"入口，与用户名/密码登录并行展示
- Trace Hints: UI, TASK, TESTSET

## AC-001-UI-002

- Scenario: 手机号输入格式化
- Given: 用户在手机号输入框输入13800138000
- When: 输入过程中
- Then: 输入框实时格式化为138****3800显示
- Trace Hints: UI, TECH, TESTSET

## AC-001-UI-003

- Scenario: 一键登录按钮状态管理
- Given: 用户输入合法手机号
- When: 手机号校验通过
- Then: 一键登录按钮变为可用状态，点击后进入验证码等待状态
- Trace Hints: UI, TECH, TASK, TESTSET

## AC-001-UI-004

- Scenario: 国际手机号支持
- Given: 用户需要切换国家区号
- When: 点击区号选择器
- Then: 显示可选区号列表（+86/+852/+853），选择后更新区号
- Trace Hints: UI, TECH, TESTSET

## AC-001-UI-005

- Scenario: 页面加载性能
- Given: 用户访问登录页面
- When: 网络条件正常
- Then: 首屏渲染时间 ≤ 1.5秒，交互响应延迟 ≤ 100ms
- Trace Hints: UI, TECH, TESTSET
# Dependencies

- EPIC-001-PHONE-LOGIN
# Non Goals

- 不实现具体的验证码发送逻辑（由验证码服务层 FEAT 负责）
- 不实现身份验证和登录态管理（由账户绑定层 FEAT 负责）
- 不修改现有用户名/密码登录页面逻辑
- 不实现第三方社交登录入口
