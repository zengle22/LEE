# Flowcore / LEE 执行架构设计（v1.0）

## 1. 设计目标

本架构的目标：

1. **将「流程控制」与「具体执行」彻底解耦**。
2. **保证 AI 无法绕过流程直接产生"有效副作用"**。
3. **支持多种执行形态**：LLM / MetaGPT / Skill / MCP / Shell。
4. **允许顶层 AI（PM agent）参与决策，但不拥有执行权**。
5. **在无 Claude Code / 无人值守的情况下，Orchestrator + Executors 仍可独立运行**。

---

## 2. 核心原则

### P1. Orchestrator 只负责编排，不执行具体工作

Orchestrator 不负责任何业务逻辑，只负责：

- 解析 `workflow.yaml`
- 维护 workflow state（ready / running / completed / blocked）
- 决定「下一步该跑哪个 step」
- 将 step 转交给对应的 Executor
- 记录 step 执行结果与 artifacts

Orchestrator **不直接**：

- 调用 LLM / MetaGPT API
- 跑测试 / 构建 / 部署
- 调用 Figma / CI / K8s 等外部系统

这些由 Executor + Skill/MCP 层完成。

---

### P2. 所有"有效副作用"只能通过 Orchestrator 发生

系统只承认以下行为是"真实发生过的"：

- Orchestrator 将某个 step 标记为 `completed` / `failed`。
- Orchestrator 在 state 中记录该 step 的 `outputs` / `artifacts`。
- Orchestrator 写入的 execution log / 状态文件。

任何**未经过 Orchestrator 的行为**（包括 AI 在对话中"声称已经做完某事"）：

> **一律视为无效，不进入系统状态。**

---

### P3. 顶层 AI = 决策者，不是执行者

- 顶层 AI（PM Agent）只负责"看状态 + 做决策"。
- 顶层 AI 只能通过工具调用 Orchestrator：
  - 例如：`orchestrator_run_step(project_dir, step_id)`
  - 例如：`orchestrator_next(project_dir)`
- 顶层 AI **不直接**：
  - 写项目文件
  - 调 shell / CI / K8s
  - 调 LLM / MetaGPT 生成最终产物
- 顶层 AI 不能自行判定 step 完成情况，完成与否以 Orchestrator 的 state 为准。

---

## 3. 分层架构总览

```
┌────────────────────────────────┐
│           PM Agent             │
│ (Claude Code / LLM Supervisor) │
│  - 思考 / 决策                  │
│  - 调 orchestrator_* 工具       │
└──────────────┬─────────────────┘
               │ action / command
               ▼
┌────────────────────────────────┐
│           Orchestrator         │
│  - Workflow State Machine      │
│  - Step 调度                   │
│  - Artifact / Log 记账          │
└──────────────┬─────────────────┘
               │ StepExecutionRequest
               ▼
┌────────────────────────────────┐
│        Engine / Executors      │
│  - LLMExecutor                 │
│  - MetaGPTExecutor             │
│  - ShellSkillExecutor          │
│  - MCPSkillExecutor            │
└──────────────┬─────────────────┘
               │
               ▼
┌────────────────────────────────┐
│    外部系统 / 工具 / MCP       │
│  - OpenAI / Claude API         │
│  - CI / pytest                 │
│  - Figma / HTTP API / K8s      │
└────────────────────────────────┘
```

---

## 4. 关键组件职责

### 4.1 PM Agent（顶层大模型）

**定位**：唯一的大脑（项目 PM / Supervisor）。

**职责**：

* 读取项目状态摘要：
  * 当前 workflow 步骤列表与状态
  * 已完成步骤的主要产物摘要
* 规划或选择下一步动作：
  * 跑哪个 step
  * 等待人类决策 / 进入 human gate
  * 结束当前 phase
* 通过 tools 调用 Orchestrator：
  * `orchestrator_get_state`
  * `orchestrator_run_step`
  * `orchestrator_next`

**约束**：

* 不直接写项目目录中的文件。
* 不直接执行 shell / CI / K8s / MCP。
* 不自行判定某个 step 已完成。

**输出协议**：详见 `PM_AGENT_PROTOCOL.md`。

---

### 4.2 Orchestrator（flowcore.orchestrator）

**定位**：流程控制系统（公司制度 / 审批流）。

**主要职责**：

1. **加载项目 state**
   * 从 `project_dir` 读取 workflow 配置和执行状态。
2. **解析 workflow.yaml**
   * 构建内部 state machine。
3. **确定 ready steps**
   * 基于依赖关系和 gate 规则。
4. **构造 StepExecutionRequest**
   * 包含 `project_dir`, `step_id`, `agent_or_skill_spec`, `context`。
5. **调用 EngineFactory 创建 Executor 并执行**
   * `executor = EngineFactory.create_executor(spec, project_dir)`
   * `result = await executor.execute(request)`
6. **更新 state 与产物记录**
   * 标记 step 状态（`completed/failed`）。
   * 记录 `outputs`（文件路径 / artifact id）。
   * 写执行日志。

**Orchestrator 不关心**：

* LLM provider / 模型种类。
* Skill 如何连接外部系统。
* MCP server 实现细节。

---

### 4.3 Engine / Executor 层

**定位**：面向 Orchestrator 的执行适配层。

**统一接口**：

```python
@dataclass
class StepExecutionRequest:
    project_dir: str
    step_id: str
    spec: dict      # agent 或 skill spec
    context: dict   # workflow 上下文（输入产物、contracts 等）

@dataclass
class StepExecutionResult:
    status: Literal["completed", "failed", "skipped"]
    outputs: list[str]        # 产物路径 / artifact ids
    messages: list[dict]      # 过程日志（可选）
    raw: Any                  # 引擎原始响应（可选）
```

```python
class BaseExecutor(Protocol):
    async def execute(self, req: StepExecutionRequest) -> StepExecutionResult:
        ...
```

**常见 Executor 类型**：

| Executor           | 用途                      |
| ------------------ | ----------------------- |
| LLMExecutor        | 文本 / 代码 / 分析类工作         |
| MetaGPTExecutor    | 多角色、重型开发任务              |
| ShellSkillExecutor | pytest / build / script |
| MCPSkillExecutor   | CI / Figma / K8s 等      |

Executor **只能被 Orchestrator 调用**。

---

### 4.4 Skill / MCP

**定位**：与真实世界交互的"确定性动作单元"。

Skill 可以是：

* 本地脚本（shell / python）
* 远端 HTTP 调用
* MCP server 的某个 tool

**特点**：

* 有明确的输入 / 输出。
* 行为可预期、可重复。
* 不直接由 PM agent 调用，只能被 Executor 调用。

---

## 5. Spec 建模规范

### 5.1 Workflow Spec（示例）

```yaml
# ai-spec/workflows/demo/workflow.yaml
kind: workflow
id: demo_flow
name: Demo Flow

steps:
  - id: generate_code
    kind: agent
    agent: developer
    description: 生成一个简单的 Python 函数，并保存到 src/demo.py
    inputs: []
    outputs:
      - path: src/demo.py

  - id: run_unit_tests
    kind: skill
    skill: ci.run_tests
    depends_on:
      - generate_code
    description: 运行 pytest，生成测试报告
    outputs:
      - path: reports/unit_test_report.xml
```

### 5.2 Agent Spec（示例）

```yaml
# ai-spec/agents/developer/agent.yaml
kind: agent
id: developer
name: 开发者

engine:
  type: llm
  provider: openai
  model: gpt-4.1-mini

system_prompt: |
  你是一个严谨的后端开发工程师。
  - 根据步骤描述与输入产物生成代码。
  - 严格遵守输出路径约定，不要随意创建额外文件。
  - 代码需可通过基础单元测试。
```

### 5.3 Skill Spec（示例）

```yaml
# ai-spec/skills/ci.run_tests.yaml
kind: skill
id: ci.run_tests
name: 运行单元测试

engine:
  type: shell
  command: |
    cd {{ project_dir }} && pytest --maxfail=1 --disable-warnings -q \
      --junitxml=reports/unit_test_report.xml
```

---

## 6. Claude Code 的定位与边界

Claude Code 在本架构中的角色：

* 顶层 PM Agent 的运行环境（IDE + 对话）。
* 提供工具给 PM Agent，例如：
  * `orchestrator_get_state`
  * `orchestrator_run_step`
  * （只读）查看项目文件。
* 提供人类协作入口（human gate 决策、查看日志等）。

Claude Code **不是**：

* Orchestrator 的一部分。
* Executor 的一部分。
* 系统运行的必需组件。

**未来可以将 PM Agent 从 Claude Code 迁出，改为后端服务调用 LLM API，但 Orchestrator + Executor 的架构不变。**

---

## 7. AI 需要理解什么？

* AI 不需要理解整个架构细节。
* AI 只需要通过 system prompt 理解：

  1. 自己是 PM / Supervisor 角色；
  2. 自己只能输出 action / 调用 orchestrator 工具；
  3. 自己不能直接执行步骤或修改项目文件。

所有这些在 `PM_AGENT_PROTOCOL.md` 中以"使用说明 + 约束"的形式呈现即可。

---

**文档版本**: v1.0
**最后更新**: 2025-01-22
**维护者**: LEE 框架团队
