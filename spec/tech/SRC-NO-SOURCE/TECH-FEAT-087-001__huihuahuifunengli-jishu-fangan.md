---
id: TECH-FEAT-087-001
ssot_type: tech
title: 会话恢复能力技术方案
status: frozen
version: v1
parent_id: FEAT-087
derived_from_ids: []
source_refs:
- FEAT-087
- EPIC-004
- ADR-004
owner: tech
tags:
- claude-code
- session
- resume
- tech
properties: {}
frozen_at: '2026-03-12T00:20:48.0005842+08:00'
workflow_instance_id: wf-tech-feat-087-001__huihuahuifunengli-jishu-fangan-20260316
---

# Overview

本技术方案为 `FEAT-087` 提供 Claude Code 会话的持久化与恢复机制，使用户在中断执行后可以回到可恢复上下文，而不是每次都从零开始。

# Architecture Decisions

## Session Persistence

- Technology: JSON state snapshot + SQLite event store
- Reasoning: JSON 用于可读快照，SQLite 用于结构化事件与恢复索引，避免额外外部依赖

## Resume Entry

- Technology: CLI resume command + checkpoint discovery
- Reasoning: 提供明确恢复入口，而不是让用户手工拼接执行上下文

## Checkpoint Strategy

- Technology: explicit checkpoint creation on critical execution boundaries
- Reasoning: 提高恢复成功率，并减少重复执行已完成步骤

# Core Components

## SessionManager

- Responsibilities: 维护会话快照、检查点和恢复索引
- Dependencies: JSON store, SQLite, StreamExecutor

## ResumeCoordinator

- Responsibilities: 接收恢复请求，选择检查点并协调恢复后的继续执行
- Dependencies: SessionManager, CLI command surface

# Integration Points

- 执行中断事件捕获
- CLI `resume` 入口
- 状态检测和事件日志

# Related Tasks

- [TASK-FEAT-087-001__huihuachijiuhuacunchucengshixian.md](/E:/ai/LEE/spec/tasks/FEAT-087/TASK-FEAT-087-001__huihuachijiuhuacunchucengshixian.md)
- [TASK-FEAT-087-002__huihuahuifu-cli-jicheng.md](/E:/ai/LEE/spec/tasks/FEAT-087/TASK-FEAT-087-002__huihuahuifu-cli-jicheng.md)

# Risks

- 并非所有执行现场都能 100% 恢复，需要显式定义不可恢复场景和回退策略
- 若恢复点创建过密，会引入额外 IO 负担；过稀又会降低恢复价值

