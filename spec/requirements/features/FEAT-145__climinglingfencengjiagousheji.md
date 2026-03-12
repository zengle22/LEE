---
id: FEAT-145
ssot_type: feat
title: CLI命令分层架构设计
status: frozen
version: v1
parent_id: EPIC-017
derived_from_ids: []
source_refs:
- EPIC-017#scope
owner: null
tags: []
properties:
  contract_key: feat_001
  identity_kind: ssot
frozen_at: '2026-03-12T20:17:54.574222'
---

# Goal

建立CLI命令分层机制，定义高层治理入口与底层物化原语的职责边界，确保面向用户的治理入口与面向系统的物化原语职责清晰分离
# User Value

普通用户通过高层治理入口(lee epic/lee feat/lee adr)操作，避免直接操作底层物化原语，降低误操作风险，确保治理链完整性
# Inputs

- 高层命令命名规范草案
- 现有CLI架构文档
- SSOT模块接口定义
- workflow模块接口定义
# Processing

- 分析现有CLI命令结构，识别治理入口与物化原语
- 设计高层命令(lee epic/lee feat/lee adr)的接口契约
- 定义高层命令与底层ssot create的职责边界
- 设计命令路由机制，确保用户请求正确分发
- 实现高层命令框架，支持治理链绑定扩展点
# Outputs

- CLI分层架构设计文档
- 高层命令接口规范
- 分层边界定义说明
- 命令实现框架代码
- 职责边界验证用例
# Acceptance

- 高层命令(lee epic/lee feat/lee adr)完成设计与实现
- 能够与底层ssot create明确区分职责边界
- 用户通过高层命令创建的formal object自动绑定review/gate/freeze治理链
- 验收时可演示从高层命令到治理链执行的完整流程
- 验证无绕过治理链的快捷路径
# Acceptance Checks

## AC-017-001-01

- Scenario: 高层命令框架实现
- Given: CLI分层架构设计完成
- When: 执行lee epic init或lee feat init命令
- Then: 系统调用workflow治理链而非直接调用ssot create
- Trace Hints: TECH, TASK, TESTSET

## AC-017-001-02

- Scenario: 职责边界验证
- Given: 用户通过高层命令创建EPIC
- When: 命令执行完成
- Then: 生成的对象包含完整的治理链引用，且无直接storage操作记录
- Trace Hints: TECH, TESTSET

## AC-017-001-03

- Scenario: 无绕过路径验证
- Given: 系统部署完成
- When: 安全审计扫描CLI入口点
- Then: 除显式admin路径外，所有formal object创建入口均经过治理链
- Trace Hints: TECH, TESTSET
# Dependencies

- None
# Non Goals

- 不规定高层命令最终命名(adr/epic/feat可后续迭代)
- 不直接设计runtime内部持久化细节
