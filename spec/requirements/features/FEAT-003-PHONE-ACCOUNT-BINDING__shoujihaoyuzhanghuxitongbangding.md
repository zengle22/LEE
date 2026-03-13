---
id: FEAT-003-PHONE-ACCOUNT-BINDING
ssot_type: feat
title: 手机号与账户系统绑定
status: active
version: v1
parent_id: EPIC-001-PHONE-LOGIN
derived_from_ids: []
source_refs:
- EPIC-001-PHONE-LOGIN#scope
owner: null
tags: []
properties:
  contract_key: feat_003
  identity_kind: ssot
---

# Goal

实现手机号与用户账户的绑定机制，支持首次登录自动开户和已有账户关联
# User Value

用户可使用手机号快速关联已有账户或创建新账户，实现无缝登录体验
# Inputs

- 已验证的手机号
- 验证码校验成功凭证
- 用户设备信息
- 可选：已有账户登录态（用于绑定场景）
# Processing

- 查询手机号-账户映射关系
- 首次登录：手机号未绑定账户时创建新账户并绑定
- 已有账户绑定：验证身份后建立映射关系
- 账户冲突检测与处理（合并/切换选项）
- 生成标准登录态（JWT/Session）
# Outputs

- 登录态凭证（JWT/Session）
- 用户账户信息
- 绑定成功确认
- 账户冲突提示（如适用）
- 审计日志记录
# Acceptance

- 手机号-账户映射：建立手机号与用户账户的一对一/多对多映射关系，支持数据库存储
- 首次登录流程：手机号未绑定账户时，自动创建新账户并绑定手机号，或引导绑定已有账户
- 已有账户绑定：已登录用户可在账户设置中绑定/解绑手机号，需验证身份
- 登录态生成：验证成功后生成标准登录态（JWT/Session），与现有登录方式返回格式一致
- 账户冲突处理：手机号已绑定其他账户时，提供合并账户或切换账户选项
# Acceptance Checks

## AC-003-BIND-001

- Scenario: 手机号-账户映射建立
- Given: 用户手机号验证成功
- When: 系统处理登录请求
- Then: 建立手机号与账户的映射关系并持久化存储
- Trace Hints: TECH, TASK, TESTSET

## AC-003-BIND-002

- Scenario: 首次登录自动开户
- Given: 手机号未绑定任何账户
- When: 用户完成验证
- Then: 自动创建新账户并绑定手机号，返回登录态
- Trace Hints: TECH, TASK, TESTSET

## AC-003-BIND-003

- Scenario: 已有账户绑定手机号
- Given: 用户已登录现有账户
- When: 在账户设置中绑定手机号并完成验证
- Then: 建立手机号与现有账户的映射关系
- Trace Hints: UI, TECH, TASK, TESTSET

## AC-003-BIND-004

- Scenario: 登录态生成
- Given: 验证成功
- When: 系统生成登录凭证
- Then: 返回标准格式JWT/Session，与现有登录方式一致
- Trace Hints: TECH, TASK, TESTSET

## AC-003-BIND-005

- Scenario: 账户冲突处理
- Given: 手机号已绑定其他账户
- When: 用户尝试登录或绑定
- Then: 提供合并账户或切换账户选项
- Trace Hints: UI, TECH, TESTSET
# Dependencies

- EPIC-001-PHONE-LOGIN
- FEAT-002-SMS-CODE-SERVICE
# Non Goals

- 不修改现有用户名/密码登录的认证逻辑
- 不实现账户密码找回流程的重构
- 不实现强制绑定手机号的策略
- 不实现账户注销功能
