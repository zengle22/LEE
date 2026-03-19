# LEE 执行器总览

## 背景

LEE 当前支持 5 类执行器：

- `claude_code`
- `kimi`
- `codex`
- `qwen_chat`
- `llm`

它们都可以承担规划、评审、SSOT 文本生成、结构化 JSON/YAML 生成、文档改写，以及在不同程度上承担代码落地工作。

因此，更合理的划分方式不是“代码型 / 文本型”，而是：

- 成本模型：套餐型 CLI 执行器 vs 按量型 API 执行器
- 接入方式：本地 CLI runtime vs 远程 API runtime
- 治理能力：强治理工作区执行器 vs 轻治理生成执行器

当前最重要的工程结论是：

> 默认优先使用套餐型 CLI 执行器，尽量减少按量 API 调用。

## 一级划分：成本模型

### 套餐型 CLI 执行器

- `claude_code`
- `kimi`
- `codex`
- `qwen_chat`

特点：

- 主要使用 coding plan / 包月套餐
- 边际成本低
- 适合高频使用
- 适合长上下文、多轮执行、大任务
- 既可以做规划评审，也可以做文档生成和部分工程落地

工程建议：

- 将这类执行器作为默认执行层
- 优先承接规划、评审、SSOT、文档、代码修改等绝大多数任务

### 按量型 API 执行器

- `llm`

特点：

- 通过 API 按 token 计费
- 标准化程度高
- provider 切换灵活
- 更适合作为补充能力或兜底后端

工程建议：

- 不应作为默认高频执行后端
- 在 CLI 执行器不适合、不可用、或需要特定 provider 能力时再使用

## 二级划分：接入方式

### CLI Agent Executors

- `claude_code`
- `kimi`
- `codex`
- `qwen_chat`

共同点：

- 通过本地 CLI 子进程执行
- 依赖宿主机安装对应 CLI
- 适合承接长任务、多轮任务
- 更接近“本地 agent runtime”

### API LLM Executor

- `llm`

共同点：

- 通过 HTTP API 调用模型服务
- 依赖 `config/llm_config.yaml` 与环境变量
- 更接近“标准远程推理后端”

## 三级划分：治理能力

### 强治理工作区执行器

- `claude_code`
- `kimi`
- `codex`

共同特点：

- 有明确 `workspace`
- 能绑定 `context_files`
- 能控制 `allowed_commands`
- 能约束 `write_scope`
- 能生成 evidence bundle
- 能收集 diff summary
- 能处理超时、静默超时、重试、执行日志

适用场景：

- 需要文件落盘
- 需要命令执行
- 需要审计链和证据链
- 需要受控改动工作区

### 轻治理生成执行器

- `qwen_chat`
- `llm`

共同特点：

- 更偏向生成内容本身
- 更适合结构化分析、文本生成、规划评审
- 默认工程审计能力弱于强治理执行器

说明：

- “轻治理”不代表能力弱，也不代表不能做规划、评审、SSOT 生成
- 它只表示默认工程控制壳更轻

## 五类执行器说明

### `claude_code`

实现文件：
[claude_code_executor.py](/E:/ai/LEE/src/lee/orchestrator/execution/claude_code_executor.py)

定位：

- 基于 Claude Code CLI 的强治理通用 Agent 执行器

核心机制：

- 校验 `goal` 与 `workspace`
- 注入治理型 system prompt
- 约束 workspace、命令、写入范围、最大迭代次数
- 落盘 prompt、debug log、live log、conversation log
- 解析执行输出
- 收集 `git diff --stat`
- 写入 evidence bundle

适合：

- 代码实现
- 规划
- 评审
- SSOT 文本生成
- 文档修改
- 需要工作区审计和证据链的任务

### `kimi`

实现文件：
[kimi_code_executor.py](/E:/ai/LEE/src/lee/orchestrator/execution/kimi_code_executor.py)

定位：

- 基于 Kimi CLI 的强治理通用 Agent 执行器

核心机制：

- 复用 `claude_code` 的治理逻辑、超时控制、evidence 模型、结果解析
- 主要替换底层命令调用为 `kimi-cli`

适合：

- 作为 `claude_code` 的平替或降级后端
- 规划、评审、SSOT 生成
- 代码和文档类任务

### `codex`

实现文件：
[codex_executor.py](/E:/ai/LEE/src/lee/orchestrator/execution/codex_executor.py)

定位：

- 基于 Codex CLI 的强治理通用 Agent 执行器

核心机制：

- 调用 `codex exec --json`
- 解析 JSONL 事件流
- 提取 `thread_id`、`tokens_used`、`cost_usd`
- 支持 `sandbox_mode`
- 提供和 `claude_code` 相似的工作区治理能力

适合：

- 规划、评审、SSOT 生成
- 代码修改和命令执行
- 需要 sandbox 控制的任务

### `qwen_chat`

实现文件：
[qwen_executor.py](/E:/ai/LEE/src/lee/orchestrator/execution/qwen_executor.py)

定位：

- 基于 Qwen CLI 的轻治理通用生成执行器

核心机制：

- 调用 `qwen --output-format json` 或 `stream-json`
- 解析结构化输出
- 对低质量回复进行重试
- 提取 `structured_payload`

适合：

- 中文规划分析
- 评审
- SSOT 文本与结构化输出
- JSON/YAML 生成

说明：

- 当前实现中，`qwen_chat` 不属于 coding executor 链
- 这代表默认调度定位，不代表能力边界

### `llm`

实现文件：
[llm_executor.py](/E:/ai/LEE/src/lee/orchestrator/execution/llm_executor.py)

配置文件：
[llm_config.yaml](/E:/ai/LEE/config/llm_config.yaml)

定位：

- 基于标准 API 的通用 LLM 执行器

核心机制：

- 读取 profile 配置
- 支持环境变量覆盖
- 发起 chat/completions 请求
- 支持 fallback providers
- 支持超时与重试

适合：

- provider 标准化接入
- 特定 API 模型能力调用
- CLI 不可用时兜底
- 补充式文本生成任务

限制：

- 按量计费
- 不适合成为默认高频执行层

## 共性

所有执行器都通过统一工厂创建：

- [executors.py](/E:/ai/LEE/src/lee/orchestrator/execution/executors.py)

统一接口：

```python
await executor.execute(input_data)
```

统一调度入口：

- CLI 入口：[run.py](/E:/ai/LEE/src/lee/cli/commands/run.py)
- 执行器解析：[resolver.py](/E:/ai/LEE/src/lee/orchestrator/config/resolver.py)
- 配置定义：[config_loader.py](/E:/ai/LEE/src/lee/orchestrator/config_loader.py)

统一选择优先级：

1. CLI `--executor`
2. 环境变量 `LEE_EXECUTOR` / `LEE_EXECUTOR_TYPE`
3. `.lee/config.yaml`
4. 默认值

## 关键差异

### 成本差异

- 套餐型：`claude_code`、`kimi`、`codex`、`qwen_chat`
- 按量型：`llm`

### 接入差异

- CLI：`claude_code`、`kimi`、`codex`、`qwen_chat`
- API：`llm`

### 治理差异

- 强治理：`claude_code`、`kimi`、`codex`
- 轻治理：`qwen_chat`、`llm`

### 默认调度角色差异

当前仓库中，coding executor 类型定义见：

- [types.py](/E:/ai/LEE/src/lee/orchestrator/config/types.py)

当前 coding executor 集合为：

- `claude_code`
- `kimi`
- `codex`

说明：

- 这是默认调度角色
- 不是能力范围定义

## 推荐策略

### 核心原则

- 套餐优先
- API 保底

### 推荐执行顺序

强治理任务推荐：

1. `claude_code`
2. `kimi`
3. `codex`
4. `llm`

轻量生成任务推荐：

1. `qwen_chat`
2. `claude_code`
3. `kimi`
4. `codex`
5. `llm`

默认策略建议：

- 能用套餐 CLI 做的，优先不用 API
- API 只在必要时使用

## 推荐配置

项目级配置建议放在 `.lee/config.yaml`。

推荐默认配置：

```yaml
executor:
  default_type: claude_code
  coding_executor: claude_code
  coding_fallbacks:
    - kimi
    - codex
  timeout_seconds: 600
```

含义：

- 普通步骤默认优先使用套餐型 CLI 执行器
- 代码类步骤首选 `claude_code`
- 失败后降级到 `kimi`、`codex`
- `llm` 不作为默认高频后端

## 常用环境变量

### `claude_code`

- `CLAUDE_CODE_BINARY`
- `CLAUDE_CODE_MODEL`

### `kimi`

- `KIMI_CLI_BINARY`
- `KIMI_MODEL`
- `KIMI_API_KEY`
- `MOONSHOT_API_KEY`

### `codex`

- `CODEX_BINARY`
- `CODEX_MODEL`
- `OPENAI_API_KEY`

### `qwen_chat`

- `QWEN_CLI_BINARY`
- `QWEN_MODEL`
- `QWEN_OUTPUT_FORMAT`
- `QWEN_APPROVAL_MODE`

### `llm`

- `LLM_PROFILE`
- `LLM_API_KEY`
- `LLM_BASE_URL`
- `LLM_MODEL`
- `LLM_TEMPERATURE`
- `LLM_MAX_TOKENS`

## 使用示例

CLI：

```bash
lee run dev.bugfix-delivery --spec bug.yaml --executor claude_code
lee run dev.bugfix-delivery --spec bug.yaml --executor kimi
lee run dev.bugfix-delivery --spec bug.yaml --executor codex
lee run product.src-to-epic --spec src.yaml --executor qwen_chat
lee run product.src-to-epic --spec src.yaml --executor llm
```

Python：

```python
from lee.orchestrator.execution.executors import ExecutorFactory

executor = ExecutorFactory.create("codex")
result = await executor.execute({
    "goal": "整理当前 FEAT 的技术设计与评审结论",
    "workspace": "E:/ai/LEE",
    "context_files": ["README.md"],
})
```

## 结论

执行器体系不应再按“代码任务 / 文本任务”做硬划分。更符合实际的说法是：

- `claude_code`、`kimi`、`codex`、`qwen_chat` 是套餐型 CLI 执行器，是默认主执行层
- `llm` 是按量型 API 执行器，是补充层和兜底层

对于大多数任务，推荐优先使用套餐型执行器，以控制长期成本并保持高频可用性。
