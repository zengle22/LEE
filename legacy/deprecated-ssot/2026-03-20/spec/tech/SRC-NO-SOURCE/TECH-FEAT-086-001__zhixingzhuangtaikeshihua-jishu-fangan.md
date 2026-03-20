---
id: TECH-FEAT-086-001
ssot_type: tech
title: 执行状态可视化技术方案
status: frozen
version: v1
parent_id: FEAT-086
derived_from_ids: []
source_refs:
- FEAT-086
- EPIC-004
- ADR-004
owner: tech
tags:
- claude-code
- state-machine
- cli
- tech
properties: {}
frozen_at: '2026-03-12T00:20:48.0005842+08:00'
workflow_instance_id: wf-tech-feat-086-001__zhixingzhuangtaikeshihua-jishu-fangan-20260316
---

# Overview

本技术方案为 `FEAT-086` 提供状态检测和状态展示基础，使 Claude Code 执行过程不再只有“开始/结束”两个离散结果，而是具备运行中、卡死、完成、失败四类可程序化判断状态。

# Architecture Decisions

## State Management

- Technology: enum-based state machine
- Reasoning: 以显式状态枚举和状态转换规则保证判定逻辑稳定、可测试、可审计

## Activity Detection

- Technology: heartbeat + silence timeout
- Reasoning: 结合输出活动和进程状态判断“运行中”与“卡死”之间的边界

## Event Logging

- Technology: state transition event stream
- Reasoning: 让状态变化不只是 UI 瞬时展示，还能进入后续审计和恢复链路

# Core Components

## StateDetector

- Responsibilities: 维护状态枚举、心跳时钟和超时阈值，产生状态变更事件
- Dependencies: StreamExecutor, timer, state machine

## StatusPresenter

- Responsibilities: 将当前状态和关键依据暴露给 CLI 展示层
- Dependencies: state transition events, CLI formatter

# Integration Points

- Claude Code 输出活动检测
- CLI 状态提示展示
- 会话恢复前的状态快照

# Related Tasks

- [TASK-FEAT-086-001__zhixingzhuangtaimeijuyuzhuangtaijishixian.md](/E:/ai/LEE/spec/tasks/FEAT-086/TASK-FEAT-086-001__zhixingzhuangtaimeijuyuzhuangtaijishixian.md)

# Risks

- 卡死阈值的默认值需要结合真实执行数据迭代校准
- 状态判定若过度依赖单一信号，容易把“无输出但仍在运行”的情况误判为卡死

