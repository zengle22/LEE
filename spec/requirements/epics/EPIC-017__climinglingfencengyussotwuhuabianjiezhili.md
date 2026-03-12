---
id: EPIC-017
ssot_type: epic
title: CLI命令分层与SSOT物化边界治理
status: frozen
version: v1
parent_id: null
derived_from_ids: []
source_refs: []
owner: null
tags: []
properties: {}
frozen_at: '2026-03-12T19:38:58.443780'
---

# CLI命令分层与SSOT物化边界治理

## 目标

将formal object的生成条件收回到workflow/gate体系中，建立CLI命令分层机制，使registry与spec/中的对象更可信、更可追溯，确保面向用户的治理入口与面向系统的物化原语职责清晰分离

## 范围

- CLI命令分层设计：定义高层治理入口（lee epic/lee feat/lee adr）与底层物化原语（ssot create）的职责边界
- SSOT对象生成入口的治理链绑定：确保所有formal object生成必须经过review/gate/freeze完整治理链
- ssot create命令的降级与权限界定：将其从推荐主入口降级为internal/admin/maintenance命令
- workflow与SSOT物化的职责边界：明确workflow负责治理链执行，SSOT原语负责最终物化
- formal object的source_refs、父子关系自动继承机制：实现从SRC到EPIC/FEAT/ADR的自动引用链
- CLI帮助文档与demo的统一叙事：将用户引导至规范的workflow-first入口

## 非目标

- 不直接删除旧demo、旧帮助文案或所有历史命令
- 不规定高层命令最终是否命名为adr/epic/feat（命名方案可后续迭代）
- 不直接设计runtime内部全部持久化细节
- 不替换ADR与SRC的关系（治理型需求仍需先补薄SRC）
- 不实现跨runtime的分布式SSOT同步

## 成功标准

- 普通用户100%默认从workflow-first入口创建EPIC/FEAT/ADR
- ssot create命令明确降级，其使用需显式--admin或--maintenance标志
- formal object的source_refs、父子关系和治理链引用由workflow自动继承，人工维护错误率降至0
- CLI、文档和测试叙事统一为'高层入口负责治理，SSOT原语负责物化'
- registry中对象治理状态一致性达到100%，无绕过治理链的formal object
