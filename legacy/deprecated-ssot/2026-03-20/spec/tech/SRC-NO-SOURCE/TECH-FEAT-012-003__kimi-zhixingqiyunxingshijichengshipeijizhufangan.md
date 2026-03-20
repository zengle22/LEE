---
id: TECH-FEAT-012-003
ssot_type: tech
title: Kimi 执行器运行时集成适配技术方案
status: active
version: v1
parent_id: FEAT-012-003
derived_from_ids: []
source_refs:
- FEAT-012-003
owner: architecture-team
tags:
- executor
- kimi
- runtime
- integration
properties:
  contract_key: tech_spec
  identity_kind: ssot
workflow_instance_id: wf-tech-feat-012-003__kimi-zhixingqiyunxingshijichengshipeijizhufangan-20260316
---

# Overview

本技术方案为 `FEAT-012-003` 提供运行时接入基线，目标是把 Kimi 作为与 `claude_code` 同类的通用 coding executor 接入 LEE。Kimi 的执行方式不是接入 Moonshot/OpenAI 兼容 API，也不是走 `llm/qwen` profile 路由，而是通过本地 `kimi-cli --print` 子进程调用进入现有 code step 执行链。

# Architecture Decisions

## Execution Model

- Technology: 本地 CLI 子进程调用
- Reasoning: Kimi 的目标形态是替换 `claude_code` 的使用场景，因此运行时语义必须与 `ClaudeCodeExecutor` 同类，确保 workspace 边界、命令治理、超时与证据输出策略可以复用

## Runner Strategy

- Technology: code runner 轨道复用，参考 `ClaudeCodeRunner`
- Reasoning: Kimi 需要接入 coding step 的受控执行链路，而不是接入 `LangGraph Runner` 的 LLM profile 路径；是否抽象出共享基类可以后续决定，但当前必须保持在 code runner 轨道

## Invocation Contract

- Technology: `kimi-cli --print`
- Reasoning: 使用稳定的命令行入口可以避免把 Kimi 错建模成远端 API provider，同时保持与本地开发者使用习惯一致

## Workflow Compatibility

- Technology: 现有 workflow wiring 复用
- Reasoning: 业务 workflow 模板不应感知底层执行器差异，只通过 `executor_type` 路由到对应 code executor

# Core Components

## KimiCodeExecutor

- Responsibilities: 封装 `kimi-cli --print` 的子进程调用，处理输入验证、prompt 注入、超时、重试、日志落盘、结构化结果解析
- Dependencies: `subprocess`, `asyncio`, evidence bundle 写入能力

## KimiCodeRunner Integration

- Responsibilities: 将 `executor_type="kimi"` 的 coding step 路由到 code runner 轨道，注入与 `claude_code` 同类的治理参数，并把执行结果交回现有 step/gate 处理链
- Dependencies: `llm_runner.py` 中的 `ClaudeCodeRunner` 接线、step config、executor factory

## ExecutorFactory Registration

- Responsibilities: 注册 `kimi` 到通用执行器工厂，使 CLI 参数与配置解析后的 `executor_type="kimi"` 可以实例化 Kimi 执行器
- Dependencies: `src/lee/orchestrator/execution/executors.py`

## Kimi CLI Environment Adapter

- Responsibilities: 统一读取 `KIMI_CLI_BINARY`、认证相关环境变量、模型选择参数和额外命令行 flags，并为缺失依赖提供明确错误提示
- Dependencies: 本地运行环境、环境变量管理

# Integration Points

- `src/lee/cli/commands/run.py`
  作用：把 `--executor kimi` 和默认配置结果透传到 workflow 实例

- `src/lee/orchestrator/execution/executors.py`
  作用：把 `kimi` 注册为 code executor，而不是 `LLMExecutor` profile 别名

- `src/lee/orchestrator/execution/claude_code_executor.py`
  作用：作为 Kimi CLI executor 的参考实现，复用其输入治理、超时控制、evidence bundle 与结果解析模式

- `src/lee/orchestrator/execution/runners/llm_runner.py`
  作用：在 `ClaudeCodeRunner` 所在轨道中为 `executor_type="kimi"` 提供与 code step 相匹配的 runner 接线

- coding workflow 模板
  作用：继续只声明 code step，不感知 Kimi/Claude/Codex 的底层差异

# Data Flow

1. 用户通过 `lee run ... --executor kimi` 或默认配置选择 `kimi`
2. workflow 实例把 `executor_override` 或默认 executor 传入 step 执行上下文
3. code step 进入 `ClaudeCodeRunner` 同类执行链路
4. runner 通过 `ExecutorFactory` 创建 Kimi code executor
5. executor 在 workspace 内调用本地 `kimi-cli --print`
6. stdout/stderr、结构化结果和 evidence bundle 被收集并返回 orchestrator
7. 现有 gate、freeze、审计链路继续消费统一结果格式

# Configuration Contract

- `KIMI_CLI_BINARY`
  说明：Kimi CLI 可执行文件路径，默认可回落到 `kimi-cli`

- `KIMI_MODEL`
  说明：可选模型参数，由 executor 翻译为 CLI flags；不是 LLM profile 配置

- `KIMI_API_KEY` 或 Kimi CLI 约定的认证环境变量
  说明：由本地 CLI 消费，不在 LEE 内直接发起 HTTP API 调用

- `executor: kimi`
  说明：作为 workflow/step 侧唯一需要暴露的选择信号

# Non-Goals

- 不把 Kimi 接入 `config/llm_config.yaml` 作为 OpenAI 兼容 profile
- 不复用 `LangGraph Runner` 作为 Kimi 的 coding 执行路径
- 不修改业务 workflow 模板
- 不在本阶段优化 Kimi CLI 的性能或提示词质量

# Risks

- 本地环境未安装 `kimi-cli` 或 PATH 不正确，会导致执行器启动失败
- Kimi CLI 的输出格式如果不稳定，可能影响结构化结果抽取，需要比照 `ClaudeCodeExecutor` 补充健壮解析
- 若 Kimi CLI 与 Claude Code 在权限、工作目录或交互模式上存在差异，runner 注入参数需要做适配，不能直接假设完全兼容

# Verification Plan

- 单元测试：验证 `kimi-cli --print` 命令拼装、环境变量传递、错误处理、缺失二进制提示
- 集成测试：验证 `executor_type="kimi"` 的 code step 进入 code runner 轨道，而不是 `llm/qwen` profile 轨道
- 回归测试：验证现有 `claude_code`、`codex` 和 `qwen` 路由不被 Kimi 接入破坏
