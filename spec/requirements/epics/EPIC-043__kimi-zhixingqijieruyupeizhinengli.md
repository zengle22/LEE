---
id: EPIC-043
ssot_type: epic
title: Kimi 执行器接入与配置能力
status: frozen
version: v1
parent_id: null
derived_from_ids: []
source_refs: []
owner: null
tags: []
properties: {}
frozen_at: '2026-03-12T21:24:01.597168'
---

# Kimi 执行器接入与配置能力

## 目标

在 LEE 工作流执行框架内，建立 Kimi 执行器的标准接入与配置能力，使其成为可显式选择、可配置为默认、可追溯、可复用的执行能力选项，支撑中文场景下的需求分析与代码执行任务，同时严格遵循现有架构复用原则。

## 范围

- CLI 支持 `--executor kimi` 命令入口，实现执行器显式选择能力
- 配置系统支持切换默认 coding executor 的能力
- Kimi 执行器与现有 canonical executor 架构的集成适配
- 复用现有 Runner 与 workflow wiring，确保执行链路一致性
- 兼容现有 `qwen` 等执行器别名模式
- 执行器配置的标准化入口与运行约束定义

## 非目标

- 不创建平行 workflow 或平行执行链
- 不新建业务 workflow 模板
- 不替换 Claude Code / Codex 存量实现
- 不包含生产发布、灰度或运维策略设计
- 不在本阶段完成 src_to_epic、epic_to_feat、feat_to_delivery_prep 等下游流程
- 不重构其他执行器的历史实现

## 成功标准

- CLI 支持 `--executor kimi` 命令且正确路由到 Kimi 执行器
- 配置支持切换默认 coding executor 且修改后自动生效
- 现有 coding 步骤模板无需修改即可使用 Kimi 执行器
- 执行器输出格式兼容现有 executor 接口规范
- 无新增平行链路，路由逻辑与现有执行器一致
