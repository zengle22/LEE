---
id: EPIC-001-PHONE-LOGIN
ssot_type: epic
title: 用户登录体验优化 - 手机号一键登录
status: frozen
version: v1
parent_id: null
derived_from_ids: []
source_refs: []
owner: null
tags: []
properties:
  contract_key: epic
  identity_kind: ssot
frozen_at: '2026-03-13T01:44:35.694689'
---

epic_id: EPIC-001-PHONE-LOGIN
title: 用户登录体验优化 - 手机号一键登录
goal: 简化用户登录流程，通过手机号一键登录替代繁琐的用户名密码两步操作，提升移动端用户体验和登录转化率
scope:
- 手机号一键登录功能的登录页面入口和交互设计
- 手机号格式校验（支持国际手机号格式）和验证码发送机制
- 短信验证码服务集成与可靠投递保障
- 手机号与现有账户系统的绑定和身份验证逻辑
- 与现有用户名/密码登录方式的并行共存机制
- 登录安全性保障（验证码有效期、重发限制、防暴力破解）
non_goals:
- 移除或修改现有的用户名/密码登录方式
- 引入第三方社交登录（微信/QQ/支付宝等）
- 重构密码找回流程
- 提升账户安全等级要求（如强制双因素认证）
- 实现免密登录或无感登录
- 修改用户注册流程
success_metrics:
- 一键登录功能上线后，移动端登录转化率提升 ≥ 20%
- 用户登录平均耗时从现有 45 秒降低至 ≤ 15 秒
- 短信验证码到达率 ≥ 99.5%，平均到达时间 ≤ 30 秒
- 用户登录失败率 ≤ 2%（排除用户主动放弃情况）
- 客服关于"登录困难"的工单数量下降 ≥ 30%
priority: P0
feat_split_principles:
- 按用户旅程拆分：登录入口/UI 层、验证码服务层、身份验证/账户绑定层
- 按技术域拆分：前端交互组件、短信网关服务、账户认证服务、安全风控模块
- 按依赖关系拆分：优先实现短信服务接入和账户绑定基础能力，再构建前端登录流程
- 按风险拆分：先实现国内手机号支持作为 MVP，国际手机号格式作为增强特性
- 保持现有登录方式不受影响，新旧登录方式可独立演进
source_refs:
- PD-src-20260310-001
ssot:
  identity_kind: ssot
  ssot_type: EPIC
  parent: SRC-001
  derived_from: PD-src-20260310-001
