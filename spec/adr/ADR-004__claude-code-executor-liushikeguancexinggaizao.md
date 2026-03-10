---
id: ADR-004
ssot_type: adr
title: Claude Code Executor 流式可观测性改造
status: draft
version: v1
parent_id: null
derived_from_ids: []
source_refs: []
owner: codex
tags: []
properties: {}
---

# Claude Code Executor 流式可观测性改造

## 状态

提议

## 背景

当前 LEE 的 `ClaudeCodeExecutor` 已经通过子进程实时读取 `stdout/stderr`，并把过程写入 `conversation.live.log`，但上层 `llm_runner` 与 `lee run` 仍把执行视为一次性黑盒调用：

- 执行器默认使用 `claude --print --output-format json`
- Runner 等待 `executor.execute()` 整体返回后再更新结果
- `lee run` / `lee watch` 只显示工作流状态，不显示 Claude 过程输出

这导致两个直接问题：

1. CLI 使用者无法在执行过程中观察 Claude Code 当前在做什么
2. 后续若要支持中断、审批、follow-up、resume，现有一次性结果模式扩展成本高

## 决策

本次改造采用“两阶段收敛”，并以 LEE 现有执行器路径为唯一 canonical implementation：

### 阶段 1：先暴露现有实时日志，不重写协议

- 保留 Python `ClaudeCodeExecutor`
- 继续使用当前 evidence/live log 机制
- 在 `lee run` / `lee watch` 中增加对当前运行步骤 live log 的跟随输出
- 目标是立刻消除“黑盒执行”问题

### 阶段 2：再从结果模式升级到流式协议模式

- 将 Claude CLI 调用从 `--print --output-format json` 迁移为 `stream-json` 输入输出
- 在 Python 内实现轻量协议桥接层
- 支持会话 ID、增量消息、取消、中断，以及未来的工具审批

## 明确约束

1. 不引入平行执行器实现，不创建 `claude_code_executor_v2`
2. 不直接迁移 Rust 模块作为运行时依赖
3. 允许借鉴 `vibe-kanban` 的协议设计、日志规范化思路和会话恢复策略
4. 第一阶段必须优先落地于现有 `src/lee/orchestrator/execution/claude_code_executor.py` 与 `lee cli`，而不是新建服务栈

## 影响

正向影响：

- CLI 可见 Claude Code 实时输出
- 调试成本下降
- 后续审批/交互能力具备清晰演进路径

代价与风险：

- CLI 输出噪音可能增加，需要做前缀或过滤
- live log 跟随需要处理并发打印与终端退出清理
- 阶段 2 协议升级会影响解析逻辑与错误处理

## 实施边界

本 ADR 仅约束 Claude Code 执行器与 CLI 可观测性演进路径，不改变：

- 工作流编排职责边界
- SQLite 作为状态权威的原则
- 现有 Codex executor 的独立实现边界

## 后续动作

1. 先给 `lee run` 增加 Claude/Codex live log 跟随能力
2. 将 live log 路径提升为 runner/CLI 可直接消费的结构化字段
3. 评估将 Claude CLI 切换到 `stream-json` 协议的兼容性与测试覆盖面
