---
id: TASK-FEAT-145-001
ssot_type: task
title: CLI高层命令框架与核心命令实现
status: frozen
version: v1
parent_id: FEAT-145
derived_from_ids: []
source_refs:
- FEAT-145#delivery
owner: null
tags: []
properties:
  contract_key: task_feat_145_001
  identity_kind: ssot
frozen_at: '2026-03-12T20:29:19.665106'
---

# Objective

实现CLI三层架构中的用户层和治理层入口，包括高层命令注册、路由、workflow绑定及epic/feat/adr核心命令实现

# Description

基于Frozen Technical Architecture设计，实现：1) HighLevelCommandRegistry命令注册中心；2) CommandRouter命令路由与分发；3) GovernanceEntryFacade治理入口封装；4) lee epic init/create、lee feat init/create、lee adr propose高层命令；5) WorkflowTemplateExtensions工作流模板扩展。完成用户层到治理层的完整通路。

## Acceptance Mapping
- FEAT-145 / AC-017-001-01: 高层命令框架实现：支持lee epic/feat/adr命令注册与路由
- FEAT-145 / AC-017-001-02: 职责边界验证：用户层命令正确绑定治理链，通过GovernanceEntryFacade调用workflow

## Definition Of Done
- HighLevelCommandRegistry接口定义完成并通过评审
- CommandRouter实现命令解析与路由逻辑
- GovernanceEntryFacade封装workflow调用
- lee epic init/create命令实现并通过测试
- lee feat init/create命令实现并通过测试
- lee adr propose命令实现并通过测试
- WorkflowTemplateExtensions模板扩展机制实现
- CLI命令帮助文档更新
