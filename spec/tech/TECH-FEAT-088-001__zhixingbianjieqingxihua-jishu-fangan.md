---
id: TECH-FEAT-088-001
ssot_type: tech
title: 执行边界清晰化技术方案
status: frozen
version: v1
parent_id: FEAT-088
derived_from_ids: []
source_refs:
- FEAT-088
- EPIC-004
- ADR-004
owner: tech
tags:
- claude-code
- boundary
- observability
- tech
properties: {}
frozen_at: '2026-03-12T00:20:48.0005842+08:00'
---

# Overview

本技术方案为 `FEAT-088` 提供日志、证据、事件、展示四类信息的边界定义，避免 Claude Code 执行链继续把所有输出混在一个黑盒日志通道里。

# Architecture Decisions

## Boundary Separation

- Technology: custom event emitter pattern
- Reasoning: 让状态变化、执行证据和 CLI 展示能够由不同消费者独立订阅和处理

## Storage Routing

- Technology: file-system backed categorized outputs
- Reasoning: 在现有 LEE 目录体系中按职责存储，不引入新的持久化系统

## Presentation Layer

- Technology: display-facing formatted output channel
- Reasoning: CLI 展示只消费展示层数据，不直接耦合技术日志和执行证据

# Core Components

## BoundarySeparator

- Responsibilities: 对四类信息进行分类、路由和标识
- Dependencies: event emitter, filesystem, formatter

## DisplayChannel

- Responsibilities: 将展示层输出与底层日志/证据隔离，并提供统一终端前缀规范
- Dependencies: BoundarySeparator, CLI formatter

# Integration Points

- 运行日志目录
- 执行证据目录
- 会话事件流
- CLI 实时展示通道

# Related Tasks

- [TASK-FEAT-088-001__sileixinxibianjiedingyiyucunchufenli.md](/E:/ai/LEE/spec/tasks/FEAT-088/TASK-FEAT-088-001__sileixinxibianjiedingyiyucunchufenli.md)
- [TASK-FEAT-088-002__bianjiekeshihua-ui-qianzhuishixian.md](/E:/ai/LEE/spec/tasks/FEAT-088/TASK-FEAT-088-002__bianjiekeshihua-ui-qianzhuishixian.md)

# Risks

- 部分输出同时具备“日志 + 证据”双重属性，需要定义优先级和多重标注规则
- 如果展示层直接复用底层日志内容，边界仍会再次耦合回去
