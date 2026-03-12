# Claude Code `stream-json` 演进方向备案

## 背景

当前 LEE 中的 `claude_code` 执行链仍采用 Claude CLI 的单次执行模式：

- 命令形态：`claude --print --output-format json`
- 执行模型：单次启动进程、等待完成、读取最终结果
- 实时可见性：通过 `conversation.live.log` 旁路输出实现

这条链已经能够满足当前阶段需求：

- `lee run` / `lee watch` 可看到 Claude Code 的实时输出
- 可观察执行状态是否处于 `starting / streaming / quiet / stalled`
- 可通过 evidence 目录审计 prompt、debug log、conversation log
- 可通过 `lee resume` 恢复被暂停或阻塞的 workflow

因此，短期内不计划把执行器直接升级到 `stream-json`。

## 当前架构结论

当前模式的本质是 `one-shot executor`：

1. Runner 为 step 构造输入
2. Executor 启动 Claude CLI 子进程
3. 子进程在单次 prompt 下完成任务
4. Executor 输出最终 `status / generated_text / evidence`
5. CLI 通过读取 live log 获取过程可见性

这意味着：

- 工作流层仍把 Claude step 视为单次执行单元
- 审计可以依赖 evidence bundle，而不必依赖长生命周期会话
- 当前实现改动集中在 CLI 展示层，不破坏 runner / gate / workflow 语义

## 为什么暂不升级

从 `--print` 升级到 `stream-json`，不是简单替换参数，而是执行器模型变化：

- `--print` 是单次结果模式
- `stream-json` 是会话流模式

一旦升级，Executor 内部会从：

- `request -> process -> final result`

变成：

- `start process -> init session -> stream events -> send control messages -> finalize session`

这会牵动以下层：

- `ClaudeCodeExecutor`
- `ClaudeCodeRunner`
- CLI 监控与状态展示
- 人工 gate / 审批交互
- 会话恢复与重试策略
- evidence 与事件存储模型

## 未来目标模型

若后续进入 `stream-json` 演进，建议目标架构如下：

### 1. 外部接口保持不变

对 workflow / runner 暴露的顶层接口尽量仍是：

- `execute(input) -> output`

也就是说，workflow step 不需要改成“长会话对象”。

### 2. Executor 内部升级为 session-based

`ClaudeCodeExecutor` 内部改为：

1. 启动 Claude CLI
2. 发送初始化消息
3. 发送用户请求
4. 持续消费 stdout 事件流
5. 必要时向 stdin 回写控制消息
6. 聚合最终结果对象
7. 输出统一 evidence 和 structured events

### 3. 引入协议层

建议增加独立协议层，而不是把逻辑全部堆进 executor：

- `ProtocolPeer` 或同类对象
- 负责 stdin/stdout 双向协议
- 负责事件解析、心跳、异常中断、resume token

### 4. 展示层切到结构化事件

当前 CLI 读取的是 `conversation.live.log` 文本流。

未来可以升级为：

- 文本流仍保留，作为兼容审计输出
- 新增结构化事件流，供 `run/watch/status` 直接消费

建议事件类型至少包括：

- `session_started`
- `assistant_partial`
- `assistant_completed`
- `tool_called`
- `tool_result`
- `session_quiet`
- `session_stalled`
- `session_failed`
- `session_finished`

### 5. 审批与 gate 以协议事件为边界

当 Claude 会话中出现需要人工决策的动作时：

- executor 不直接失败
- runner 将其转成统一的 gate / human decision 事件
- 决策后通过协议继续会话，而不是重新跑整步

## 对现有组件的影响评估

### 可保持不变的

- workflow template 的大部分 step 建模
- `run_until_blocked` 主循环
- SSOT / TASK / TECH 主链
- evidence bundle 的目录理念

### 必须变化的

- `ClaudeCodeExecutor` 的调用方式
- `conversation.live.log` 的生成策略
- 状态检测来源，从“文本 heartbeat”转向“协议事件 + heartbeat”
- timeout / retry / resume 的语义

### 建议新增的

- 协议适配层
- 结构化事件存储
- 会话恢复元数据
- 针对 protocol event 的测试夹具

## 推荐演进顺序

若未来启动该升级，建议按以下顺序推进：

1. 保留现有 `--print` 路径不动
2. 在 executor 内部增加可切换的实验性 `stream-json` 分支
3. 先只做“读事件，不做人机交互”
4. 再做“中途审批 / control message”
5. 最后将默认执行路径切换到 `stream-json`

不建议一步切换全量默认路径。

## 当前决策

当前阶段的正式决策是：

- 继续使用 `claude --print --output-format json`
- 保留基于 `conversation.live.log` 的实时反馈与审计能力
- 暂不引入 `stream-json` 会话协议
- 本文仅作为未来演进备案，不代表当前实施项

## 触发升级的条件

只有当以下需求明确出现时，再考虑启动该演进：

- 需要真正的中途人机交互，而不是旁路日志
- 需要工具调用级别的精细可视化
- 需要单 step 内的会话恢复，而不是整步重试
- 需要把 Claude 的工具审批接入统一 gate 模型
