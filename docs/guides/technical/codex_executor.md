# Codex Executor 使用文档

## 概述

Codex Executor 是 LEE 框架中基于 OpenAI Codex CLI 的代码生成执行器。它完全复用 Claude Code Executor 的架构设计，通过 `codex exec` 命令实现非交互式代码生成任务。

## 安装前提

### 1. 安装 Codex CLI

```bash
npm install -g @openai/codex
```

### 2. 配置认证

Codex CLI 支持两种认证方式：

#### 方式一：ChatGPT 账户（推荐用于包月用户）

```bash
codex login
# 按提示完成 ChatGPT 账户登录
```

#### 方式二：API Key

在 `~/.codex/config.toml` 中配置：

```toml
[model_providers.openai]
env_key = "OPENAI_API_KEY"
```

或设置环境变量：

```bash
export OPENAI_API_KEY="sk-..."
```

## 基本使用

### 通过 CLI 使用（推荐）

使用 `--executor` 参数指定使用 Codex Executor 执行工作流：

```bash
# 使用 Codex Executor 执行工作流
lee run my-workflow --executor codex

# 指定项目目录
lee run my-workflow --executor codex --project-dir /path/to/project

# 指定分支
lee run my-workflow --executor codex --branch feature/new-feature
```

**注意**：`--executor` 参数会覆盖 spec 文件中配置的 executor 类型，优先级最高。

### 通过 ExecutorFactory 创建

```python
from lee.orchestrator.execution.executors import ExecutorFactory

executor = ExecutorFactory.create("codex")
result = await executor.execute({
    "goal": "实现用户登录 API",
    "workspace": "/path/to/project",
})
```

### 直接实例化

```python
from lee.orchestrator.execution.codex_executor import CodexExecutor

executor = CodexExecutor()
result = await executor.execute({
    "goal": "实现用户登录 API",
    "workspace": "/path/to/project",
})
```

## 输入参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `goal` | str | ✅ | - | 任务描述 |
| `workspace` | str | ✅ | - | 工作目录路径 |
| `context_files` | list[str] | ❌ | [] | 上下文文件列表 |
| `allowed_commands` | list[str] | ❌ | ["cat", "ls", "find", "grep"] | 允许执行的命令 |
| `write_scope` | list[str] | ❌ | [] | 允许写入的路径 |
| `max_iterations` | int | ❌ | 5 | 最大迭代次数 |
| `max_bash_calls` | int | ❌ | 60 | Bash 调用上限 |
| `timeout_seconds` | int | ❌ | 3600 | 超时时间（秒） |
| `timeout_retries` | int | ❌ | 1 | 超时重试次数 |
| `sandbox_mode` | str | ❌ | "workspace-write" | 沙箱模式 |
| `model` | str | ❌ | "gpt-4o" | 使用的模型 |
| `evidence_base` | str | ❌ | ".workflow/codex" | 证据输出目录 |

## 沙箱模式

Codex CLI 支持三种沙箱模式：

| 模式 | 说明 |
|------|------|
| `read-only` | 只读模式，不允许写入文件 |
| `workspace-write` | 工作区可写（默认） |
| `danger-full-access` | 完全访问权限（危险） |

```python
result = await executor.execute({
    "goal": "只读取代码",
    "workspace": "/path/to/project",
    "sandbox_mode": "read-only",
})
```

## 支持的模型

| 模型 | 说明 |
|------|------|
| `gpt-4o` | 默认模型，性价比高 |
| `gpt-4-turbo` | GPT-4 Turbo |
| `o1-mini` | O1 Mini，推理能力强 |
| `o1-preview` | O1 Preview |
| `o3-mini` | O3 Mini |
| `gpt-5.3-codex` | GPT-5.3 Codex |

## 输出格式

```python
{
    "status": "success",  # success / fail / timeout / needs_human
    "iterations_used": 3,
    "changed_files": ["src/auth.go"],
    "commands_run": [{"cmd": "go test ./...", "exit_code": 0}],
    "test_results": {"passed": 5, "failed": 0},
    "diff_summary": {
        "files_changed": 1,
        "lines_added": 50,
        "lines_deleted": 10
    },
    "evidence_bundle_path": "/path/to/evidence/...",
    "conversation_log_path": "/path/to/conversation.log",
    "debug_log_path": "/path/to/debug.log",
    "generated_text": "完成！实现了...",
    "error": None,
    "cost_usd": 0.15,
    "tokens_used": 8500,
    "thread_id": "thread-uuid",
}
```

## 证据目录结构

```
.workflow/codex/20250226-183000/
├── conversation.log          # 原始 JSONL 输出
├── result.json             # 结构化执行结果
├── input_snapshot.json      # 输入参数快照
├── prompt.system.txt       # 系统提示词
├── prompt.user.txt         # 用户提示词
├── conversation.live.log   # 实时执行日志
└── codex-debug.log         # Codex CLI 调试日志
```

## 环境变量

| 变量 | 说明 |
|------|------|
| `CODEX_BINARY` | Codex CLI 可执行文件路径 |
| `CODEX_MODEL` | 默认模型 |
| `OPENAI_API_KEY` | OpenAI API Key |

## CLI 参数

### `--executor`

强制指定执行器类型，覆盖 spec 文件中的配置。

**语法**：
```bash
lee run <workflow_key> --executor <executor_type>
```

**支持的执行器类型**：
- `llm` - LLM Executor（默认）
- `shell` - Shell Executor
- `legacy_executor` - Legacy Executor Executor
- `claude_code` - Claude Code Executor
- `codex` - Codex Executor
- `langgraph` - LangGraph Executor

**优先级**：
```
CLI --executor 参数 > spec 文件配置 > 默认执行器
```

**示例**：
```bash
# 覆盖 spec 中的 claude_code 配置，改用 codex
lee run my-workflow --executor codex

# 覆盖 spec 中的 llm 配置，改用 claude_code
lee run my-workflow --executor claude_code
```

## 与 Claude Code Executor 对比

| 特性 | Claude Code Executor | Codex Executor |
|------|---------------------|----------------|
| CLI 命令 | `claude --print` | `codex exec` |
| 输出格式 | JSON | JSONL |
| 模型 | Claude Sonnet/Opus | GPT-4o/O1/O3 |
| 认证 | API Key / 账户 | ChatGPT 账户 / API Key |
| 计费方式 | API 按量 | 包月 / API 按量 |

## 高级用法

### 自定义 System Prompt

```python
result = await executor.execute({
    "goal": "实现用户登录 API",
    "workspace": "/path/to/project",
    "system_prompt_extra": "请使用 Python FastAPI 框架实现",
})
```

### 停止条件配置

```python
result = await executor.execute({
    "goal": "运行测试并修复失败",
    "workspace": "/path/to/project",
    "stop_conditions": {
        "on_test_fail": "stop_needs_human",
        "on_policy_violation": "fail",
    },
})
```

### 成本计算

Codex Executor 自动计算任务成本：

```python
pricing = {
    "gpt-4o": {"input": 0.005, "output": 0.015},   # per 1K tokens
    "o1-mini": {"input": 0.003, "output": 0.012},
    # ...
}
```

## 故障排除

### 问题：Codex CLI 未找到

```
Codex CLI binary not found: codex
```

**解决**：安装 Codex CLI 或设置 `CODEX_BINARY` 环境变量。

### 问题：认证失败

```
Codex CLI invocation failed: Authentication failed
```

**解决**：运行 `codex login` 重新认证，或设置 `OPENAI_API_KEY`。

### 问题：沙箱权限错误

```
Permission denied: operation not permitted in sandbox mode
```

**解决**：调整 `sandbox_mode` 或使用 `danger-full-access`（谨慎）。

## 注册执行器

```python
from lee.orchestrator.execution.codex_executor import register_codex_executor

register_codex_executor()
```

## 参考链接

- [Codex CLI 官方文档](https://developers.openai.com/codex)
- [Claude Code Executor 文档](./claude_code_executor.md)
- [LEE 执行器架构](../architecture.md)
