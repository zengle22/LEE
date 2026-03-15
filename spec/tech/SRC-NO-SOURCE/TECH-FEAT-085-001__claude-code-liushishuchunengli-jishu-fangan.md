---
id: TECH-FEAT-085-001
ssot_type: tech
title: Claude Code 流式输出能力技术方案
status: frozen
version: v1
parent_id: FEAT-085
derived_from_ids: []
source_refs:
- FEAT-085
- EPIC-004
- ADR-004
owner: tech
tags:
- claude-code
- streaming
- cli
- tech
properties: {}
frozen_at: '2026-03-12T00:20:48.0005842+08:00'
workflow_instance_id: wf-tech-feat-085-001__claude-code-liushishuchunengli-jishu-fangan-20260316
---

# Overview

本技术方案为 `FEAT-085` 提供最小可落地实现，目标是在不重写现有 Claude Code executor 生命周期的前提下，为 `lee cli` 建立实时输出能力，让 stdout、stderr 和进度信息能够在命令执行过程中被稳定暴露出来。

# Architecture Decisions

## Execution Runtime

- Technology: Python `asyncio` + `subprocess`
- Reasoning: 复用现有 Python 进程管理能力，便于与当前 executor 主链兼容接入

## Streaming Output

- Technology: `asyncio.StreamReader` + 队列缓冲
- Reasoning: 支撑 stdout/stderr 的逐段读取和终端即时刷新，控制首字节输出延迟

## CLI Presentation

- Technology: Rich + ANSI escape codes
- Reasoning: 为实时输出、进度提示和错误流提供更稳定的终端格式能力

# Core Components

## StreamExecutor

- Responsibilities: 管理 Claude Code 子进程的流式执行，读取 stdout/stderr，并把输出按统一节奏推送到 CLI
- Dependencies: `subprocess`, `asyncio`, queue buffer

## CLIFormatter

- Responsibilities: 将流式输出格式化为适合终端展示的结构，区分普通输出、错误输出和进度提示
- Dependencies: Rich, ANSI formatter

# Integration Points

- 当前 `claude code executor` 的进程拉起与 stdout/stderr 采集链路
- `lee cli` 的终端展示层
- 后续状态检测和会话恢复能力的事件输入

# Related Tasks

- [TASK-FEAT-085-001__liushishuchuyinqingshixian.md](/E:/ai/LEE/spec/tasks/FEAT-085/TASK-FEAT-085-001__liushishuchuyinqingshixian.md)
- [TASK-FEAT-085-002__liushishuchu-cli-geshihuazujian.md](/E:/ai/LEE/spec/tasks/FEAT-085/TASK-FEAT-085-002__liushishuchu-cli-geshihuazujian.md)

# Risks

- 流式输出延迟可能在高负载下不稳定，需要预留缓冲调节和降级策略
- 不同平台终端对实时刷新和 ANSI 输出的支持差异，可能影响展示一致性

