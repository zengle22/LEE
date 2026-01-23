# Orchestrator 架构设计文档

> **⚠️ ARCHITECTURE UPDATE NOTICE**
>
> **This document describes the v1.6 architecture, which has been superseded by v2.0.**
>
> The new architecture introduces:
> - **PM Agent Layer**: Decision-making AI that only orchestrates, doesn't execute
> - **Unified Engine Interface**: Standardized executors for LLM/MetaGPT/Shell/MCP
> - **Orchestrator Evolution**: Now controls execution through EngineRegistry, not external AI tools
>
> **For the latest architecture, see**: [architecture.md](./architecture.md)
> **For migration guidance, see**: [ARCHITECTURE-MIGRATION-GUIDE.md](./ARCHITECTURE-MIGRATION-GUIDE.md)
>
> ---
>
> This document is preserved for historical reference and for projects still using the v1.6 architecture.
>
> **Version**: v1.6
> **Update Date**: 2025-01-22
> **Status**: **LEGACY** - Superseded by v2.0

---

## 目录

1. [概述](#1-概述)
2. [架构设计原则](#2-架构设计原则)
3. [系统架构](#3-系统架构)
4. [核心模块](#4-核心模块)
5. [数据流](#5-数据流)
6. [状态机设计](#6-状态机设计)
7. [门禁机制](#7-门禁机制)
8. [Token 管理](#8-token-管理)
9. [Agent 上下文系统](#9-agent-上下文系统)
10. [事件溯源](#10-事件溯源)
11. [追踪系统](#11-追踪系统)
12. [跨平台集成](#12-跨平台集成)
13. [扩展性设计](#13-扩展性设计)
14. [安全设计](#14-安全设计)
15. [性能考虑](#15-性能考虑)
16. [技术选型](#16-技术选型)

---

## 1. 概述

### 1.1 系统目标

Orchestrator 是一个**通用的 AI 工作流编排器**，核心目标是：

1. **强制执行规范**：让工作流规范从"建议"变成"协议"
2. **人类在环控制**：在关键决策点强制人工审批
3. **完整审计追踪**：记录所有操作，可追溯、可回放
4. **跨平台支持**：支持 Claude Code、Codex CLI、Gemini Code 等

### 1.2 核心问题

| 问题 | 解决方案 |
|------|----------|
| Agent 编排可能被跳过 | 状态机 + 依赖检查 + Step Token |
| 人类门禁可能被忽略 | Gate 产物化 + 下游强依赖 |
| 产物验证可能被遗漏 | Artifact Gate + 强制验证 |
| 执行日志可能不完整 | 自动事件记录 + Span 追踪 |

### 1.3 系统边界

**包含**：
- 工作流状态管理
- 步骤执行编排
- 门禁控制
- 产物验证
- 事件记录
- Agent 上下文注入

**不包含**：
- Agent 实现（由外部系统提供）
- 具体的验证器实现（可扩展）
- 存储系统（使用文件系统）

---

## 2. 架构设计原则

### 2.1 SOLID 原则

#### 单一职责原则 (SRP)

每个模块只负责一个功能领域：

- `StateMachine`: 状态管理
- `EventLog`: 事件记录
- `TokenManager`: Token 管理
- `AgentContextBuilder`: Agent 上下文构建

#### 开闭原则 (OCP)

通过接口和扩展点支持新功能：

```python
class InjectorRegistry:
    """注入器注册表 - 支持自定义注入器"""

    @staticmethod
    def register_injector(name: str, injector_class: type):
        """注册新的注入器"""
        _injectors[name] = injector_class
```

#### 里氏替换原则 (LSP)

所有注入器实现相同的接口：

```python
class ContextInjector(ABC):
    """上下文注入器接口"""

    @abstractmethod
    def inject(self, context: AgentContext, step_id: str) -> InjectionResult:
        """注入上下文"""
        pass
```

#### 接口隔离原则 (ISP)

最小化接口依赖：

```python
# TokenManager 只依赖必要的接口
class TokenManager:
    def validate_token(self, token_id: str, step_id: str) -> Tuple[bool, Optional[str]]:
        # 只需要 token_id 和 step_id
        pass
```

#### 依赖倒置原则 (DIP)

高层模块不依赖低层模块，都依赖抽象：

```python
# 高层模块 (StateMachine) 依赖抽象 (EventLog)
class StateMachine:
    def __init__(self, project_dir: str):
        self.event_log = EventLog(project_dir)  # 依赖抽象接口
```

### 2.2 其他原则

#### 关注点分离 (Separation of Concerns)

- **编排逻辑** 与 **业务逻辑** 分离
- **状态管理** 与 **持久化** 分离
- **验证规则** 与 **验证执行** 分离

#### 最小惊讶原则 (Principle of Least Surprise)

- 命令行参数一致
- 状态转换直观
- 错误信息清晰

#### 防御性编程 (Defensive Programming)

```python
def can_start_step(self, step_id: str) -> Tuple[bool, Optional[str]]:
    # 检查步骤是否存在
    if step_id not in state["steps"]:
        return False, f"Step not found: {step_id}"

    # 检查当前状态
    if step["state"] not in [StepState.PENDING.value, StepState.READY.value]:
        return False, f"Step {step_id} is not in pending/ready state"

    # 检查门禁
    for gate_id, gate in state.get("gates", {}).items():
        if gate["blocking"] and gate["status"] == "pending":
            return False, f"Blocked by pending gate: {gate_id}"

    return True, None
```

---

## 3. 系统架构

### 3.1 整体架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Orchestrator 系统架构                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                      CLI Layer                              │   │
│  │  (命令行接口 - cli.py)                                       │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                │                                    │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                   Core Services Layer                       │   │
│  ├─────────────────────────────────────────────────────────────┤   │
│  │                                                               │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │   │
│  │  │ State       │  │ Event       │  │ Agent                │  │   │
│  │  │ Machine     │  │ Log         │  │ Context Builder      │  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────────────┘  │   │
│  │                                                               │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │   │
│  │  │ Token       │  │ Workflow    │  │ Tracing              │  │   │
│  │  │ Manager     │  │ Parser      │  │ Integration          │  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                │                                    │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    Adapter Layer                            │   │
│  │  (跨平台适配 - agent_injector/)                              │   │
│  ├─────────────────────────────────────────────────────────────┤   │
│  │  Claude Code  │  Codex CLI  │  Gemini Code  │  Custom       │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                │                                    │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                   Storage Layer                             │   │
│  ├─────────────────────────────────────────────────────────────┤   │
│  │  State Files  │  Event Logs  │  Tokens  │  Artifacts        │   │
│  │  (YAML)       │  (JSONL)     │  (JSON)  │  (JSON)           │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 模块依赖图

```
┌──────────────┐
│     CLI      │
└──────┬───────┘
       │
       ├──► StateMachine
       │    │
       │    ├──► EventLog
       │    │
       │    ├──► TokenManager
       │    │
       │    └──► AgentContextBuilder
       │          │
       │          ├──► AgentResolver
       │          │
       │          ├──► AgentLoader
       │          │
       │          └──► InjectorRegistry
       │
       ├──► WorkflowParser
       │
       └──► TraceLog
```

---

## 4. 核心模块

### 4.1 StateMachine (状态机)

**职责**：
- 管理工作流运行状态
- 管理步骤执行状态
- 检查步骤依赖
- 触发和审批门禁
- 验证产物

**核心方法**：

```python
class StateMachine:
    def init(self, workflow: Dict, run_id: str = None) -> str:
        """初始化工作流运行"""

    def can_start_step(self, step_id: str) -> Tuple[bool, Optional[str]]:
        """检查是否可以开始步骤"""

    def start_step(self, step_id: str, agent_id: str, token: str) -> Tuple[bool, Optional[str]]:
        """开始执行步骤"""

    def complete_step(self, step_id: str, outputs: List[str]) -> Tuple[bool, Optional[str]]:
        """完成步骤"""

    def set_validation_result(self, step_id: str, passed: bool, details: Dict) -> Tuple[bool, Optional[str]]:
        """设置验证结果"""

    def trigger_gate(self, gate_id: str, step_id: str, gate_type: str, blocking: bool) -> str:
        """触发门禁"""

    def approve_gate(self, gate_id: str, approver: str, comment: str) -> Tuple[bool, str]:
        """审批门禁"""

    def verify_required_outputs(self, step_id: str, provided_outputs: List[str]) -> Dict:
        """验证必需输出"""
```

**状态转换图**：

```
                    ┌─────────┐
                    │ PENDING │
                    └────┬────┘
                         │ can_start
                    ┌────▼────┐
                    │  READY  │
                    └────┬────┘
                         │ start
                    ┌────▼──────┐
                    │IN_PROGRESS │
                    └─────┬──────┘
                          │ complete
                    ┌─────▼──────┐
                    │ VALIDATING │
                    └─────┬──────┘
                          │ validate
              ┌───────────┴───────────┐
              │                       │
         ┌────▼────┐            ┌────▼────┐
         │  GATE   │            │COMPLETED│
         │ PENDING │◄───────────┤         │
         └────┬────┘  approve   └─────────┘
              │
         ┌────▼────┐
         │ FAILED  │
         └─────────┘
```

### 4.2 EventLog (事件日志)

**职责**：
- 自动记录所有工作流事件
- 提供事件查询接口
- 生成统计报告
- 导出审计报告

**事件类型**：

```python
class EventType(Enum):
    # 运行级事件
    RUN_CREATED = "run_created"
    RUN_STARTED = "run_started"
    RUN_COMPLETED = "run_completed"
    RUN_FAILED = "run_failed"

    # 步骤级事件
    STEP_STARTED = "step_started"
    STEP_COMPLETED = "step_completed"
    STEP_FAILED = "step_failed"

    # 验证事件
    VALIDATION_PASSED = "validation_passed"
    VALIDATION_FAILED = "validation_failed"

    # 门禁事件
    GATE_TRIGGERED = "gate_triggered"
    GATE_APPROVED = "gate_approved"
    GATE_REJECTED = "gate_rejected"

    # 令牌事件
    TOKEN_ISSUED = "token_issued"
    TOKEN_VALIDATED = "token_validated"
```

**数据结构**：

```python
@dataclass
class Event:
    event_id: str
    event_type: EventType
    timestamp: str
    run_id: str
    step_id: Optional[str]
    agent_id: Optional[str]
    actor: Optional[str]  # human / agent / system
    data: Optional[Dict]
    error: Optional[str]
```

### 4.3 TokenManager (Token 管理器)

**职责**：
- 签发步骤令牌
- 验证令牌有效性
- 检查工具调用权限
- 管理令牌生命周期

**Token 结构**：

```python
@dataclass
class StepToken:
    token_id: str
    run_id: str
    step_id: str
    agent_id: str
    issued_at: str
    expires_at: str
    permissions: List[str]  # 允许的工具/操作
    signature: Optional[str]
    revoked: bool
```

**工具权限映射**：

```python
class ToolGuard:
    TOOL_PERMISSIONS = {
        "read": ["Read", "Glob", "Grep", "WebFetch"],
        "write": ["Write", "Edit", "NotebookEdit"],
        "execute": ["Bash", "Task"],
        "deploy": ["Bash:deploy", "Bash:kubectl"],
        "commit": ["Bash:git commit", "Bash:git push"],
    }
```

### 4.4 AgentContextBuilder (Agent 上下文构建器)

**职责**：
- 解析 Agent 规范
- 构建步骤执行上下文
- 整合工作流状态
- 注入上下文到 AI 工具

**上下文结构**：

```python
@dataclass
class AgentContext:
    # 步骤信息
    step_id: str
    step_name: str
    step_description: str
    step_inputs: List[str]
    step_outputs: List[str]

    # Agent 信息
    agent_id: str
    agent_name: str
    agent_system_prompt: str
    agent_instructions: List[str]
    agent_persona: Dict
    agent_forbidden_behaviors: List
    agent_quality_bar: List[str]

    # 契约
    input_contract: Optional[Dict]
    output_contract: Optional[Dict]

    # 工作流
    workflow_id: str
    workflow_name: str
    run_id: str
```

### 4.5 WorkflowParser (工作流解析器)

**职责**：
- 解析 workflow.yaml
- 提取步骤定义
- 解析依赖关系
- 提取门禁定义

**支持格式**：

```yaml
# 格式 1: 扁平格式
steps:
  - id: step1
    run: agent:worker
    depends_on: []
    outputs:
      - path: output/result.txt

# 格式 2: 嵌套格式
stages:
  - id: stage1
    steps:
      - id: step1
        run: agent:worker
```

### 4.6 TracingIntegration (追踪集成)

**职责**：
- 集成 Span 追踪
- 自动记录操作耗时
- 记录 Token 使用
- 记录错误信息

**Span 类型**：

```python
class SpanType(Enum):
    STEP = "step"
    VALIDATION = "validation"
    GATE = "gate"
    TOOL_CALL = "tool_call"
```

---

## 5. 数据流

### 5.1 步骤执行流程

```
┌─────────────────────────────────────────────────────────────────────┐
│                      步骤执行数据流                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. CLI: next ./project                                            │
│     └─► StateMachine.get_ready_steps()                             │
│         └─► 返回就绪步骤列表                                        │
│                                                                     │
│  2. StateMachine.start_step(step_id)                               │
│     ├─► TokenManager.issue_token()                                 │
│     │   └─► 生成 Token (TKN-XXX)                                   │
│     ├─► AgentContextBuilder.build_and_inject()                     │
│     │   └─► 注入上下文到 AI 工具                                    │
│     ├─► StateMachine._save_state()                                 │
│     └─► EventLog.log_step_started()                                │
│                                                                     │
│  3. Agent 执行 (外部 AI 工具)                                       │
│     ├─► 读取 Agent Context                                         │
│     ├─► 携带 Token 调用工具                                        │
│     └─► 生成输出文件                                               │
│                                                                     │
│  4. CLI: complete ./project step_id --outputs file1,file2          │
│     ├─► StateMachine.complete_step()                               │
│     │   ├─► 计算输出 hash                                          │
│     │   └─► 状态 → VALIDATING                                      │
│     └─► EventLog.log_step_completed()                              │
│                                                                     │
│  5. CLI: validate ./project step_id                                │
│     ├─► StateMachine.verify_required_outputs()                     │
│     │   ├─► 检查所有必需文件是否存在                                │
│     │   ├─► 生成 manifest                                          │
│     │   └─► 返回验证结果                                            │
│     ├─► StateMachine.set_validation_result()                       │
│     │   ├─► 如果有 gate → GATE_PENDING                              │
│     │   └─► 否则 → COMPLETED                                        │
│     └─► EventLog.log_validation_passed()                           │
│                                                                     │
│  6. (如果有 gate) CLI: approve ./project gate_id --approver name    │
│     ├─► StateMachine.approve_gate()                                │
│     │   ├─► 生成 approval artifact                                 │
│     │   └─► 步骤状态 → COMPLETED                                    │
│     └─► EventLog.log_gate_approved()                               │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 5.2 事件记录流程

```
┌─────────────────────────────────────────────────────────────────────┐
│                      事件记录流程                                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  每个操作 → EventLog.log(event_type, ...)                          │
│      ├─► 生成 event_id                                             │
│      ├─► 记录 timestamp                                            │
│      ├─► 记录 actor (human/agent/system)                           │
│      ├─► 记录 data/error                                           │
│      └─► 追加到 events.jsonl                                       │
│                                                                     │
│  查询 → EventLog.get_events(filters)                               │
│      ├─► 读取 events.jsonl                                         │
│      ├─► 应用过滤条件                                               │
│      └─► 返回事件列表                                               │
│                                                                     │
│  统计 → EventLog.get_statistics()                                  │
│      ├─► 扫描所有事件                                               │
│      ├─► 计算步骤耗时                                               │
│      ├─► 计算门禁等待时间                                           │
│      └─► 返回统计信息                                               │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 5.3 Agent 上下文注入流程

```
┌─────────────────────────────────────────────────────────────────────┐
│                  Agent 上下文注入流程                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. 解析 workflow.yaml                                             │
│     └─► WorkflowParser.parse()                                     │
│         ├─► 提取步骤定义                                            │
│         └─► 提取 Agent 引用                                         │
│                                                                     │
│  2. 加载 Agent Spec                                                 │
│     └─► AgentLoader.load(agent_ref)                                │
│         ├─► 查找 spec 文件                                          │
│         ├─► 解析 YAML/JSON                                          │
│         └─► 返回 AgentSpec 对象                                     │
│                                                                     │
│  3. 构建上下文                                                     │
│     └─► AgentContextBuilder.build()                                │
│         ├─► 整合 Agent 规范                                         │
│         ├─► 整合步骤信息                                            │
│         ├─► 整合工作流状态                                          │
│         └─► 返回 AgentContext 对象                                  │
│                                                                     │
│  4. 注入上下文                                                     │
│     └─► InjectorRegistry.inject(context, step_id)                 │
│         ├─► Claude Code: 写入 .workflow/current-context.yaml      │
│         ├─► Codex CLI: 设置环境变量                                 │
│         └─► 其他: 自定义注入方式                                    │
│                                                                     │
│  5. AI 工具读取上下文                                              │
│     └─► Agent 根据上下文执行任务                                    │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 6. 状态机设计

### 6.1 步骤状态机

**状态定义**：

```python
class StepState(Enum):
    PENDING = "pending"           # 等待执行
    BLOCKED = "blocked"           # 被依赖阻断
    READY = "ready"               # 可以执行
    IN_PROGRESS = "in_progress"   # 执行中
    VALIDATING = "validating"     # 验证中
    GATE_PENDING = "gate_pending" # 等待门禁
    COMPLETED = "completed"       # 已完成
    FAILED = "failed"             # 失败
    SKIPPED = "skipped"           # 跳过
```

**状态转换规则**：

| 当前状态 | 可转换到 | 触发条件 |
|---------|---------|---------|
| PENDING | READY | 所有依赖完成，无阻断门禁 |
| READY | IN_PROGRESS | 调用 start_step() |
| IN_PROGRESS | VALIDATING | 调用 complete_step() |
| VALIDATING | GATE_PENDING | 有门禁且验证通过 |
| VALIDATING | COMPLETED | 无门禁且验证通过 |
| VALIDATING | FAILED | 验证失败 |
| GATE_PENDING | COMPLETED | 门禁审批通过 |
| GATE_PENDING | FAILED | 门禁被拒绝 |
| FAILED | PENDING | 调用 reset_step() |

### 6.2 运行状态机

**状态定义**：

```python
class RunState(Enum):
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"         # 等待门禁
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"
```

**状态转换规则**：

| 当前状态 | 可转换到 | 触发条件 |
|---------|---------|---------|
| CREATED | RUNNING | 开始第一个步骤 |
| RUNNING | PAUSED | 有阻断门禁待审批 |
| PAUSED | RUNNING | 门禁审批通过 |
| RUNNING | COMPLETED | 所有步骤完成 |
| RUNNING | FAILED | 步骤失败且无法重试 |
| RUNNING | FAILED | 门禁被拒绝 |

### 6.3 状态持久化

**存储格式**：YAML

**文件位置**：`.workflow/state.yaml`

**保存时机**：
- 状态变更时立即保存
- 使用原子写操作（先写临时文件，再重命名）

**示例**：

```python
def _save_state(self):
    """保存状态"""
    self._state["updated_at"] = datetime.now().isoformat()

    # 原子写操作
    temp_path = self.state_path.with_suffix('.tmp')
    with open(temp_path, 'w', encoding='utf-8') as f:
        yaml.dump(self._state, f, allow_unicode=True)

    # 原子重命名
    temp_path.replace(self.state_path)
```

---

## 7. 门禁机制

### 7.1 门禁类型

#### Human Gate (人工门禁)

需要人工审批的门禁。

**触发时机**：步骤验证通过后

**阻断行为**：阻塞后续步骤执行

**审批产物**：生成 approval artifact

**示例**：

```yaml
steps:
  - id: deploy
    human_gate: deploy_approval
```

**审批流程**：

```
Step Complete → Validate → Has Gate? → YES → Trigger Gate
                                              ↓
                                         Block Execution
                                              ↓
                                         Human Approve
                                              ↓
                                    Generate Approval Artifact
                                              ↓
                                         Unblock Execution
```

#### Auto Gate (自动门禁)

基于条件自动通过的门禁（预留）。

**触发条件**：
- 所有必需输出存在
- 验证器全部通过
- 自定义条件表达式为真

**示例**：

```yaml
steps:
  - id: auto_check
    auto_gate:
      condition: "test_success_rate >= 0.95"
```

### 7.2 Gate 产物化

**目的**：将门禁审批变成可追溯的产物

**产物格式**：

```json
{
  "gate_id": "deploy_approval",
  "step_id": "deploy",
  "run_id": "RUN-20250122-153045",
  "approver": "张三",
  "approved_at": "2025-01-22T15:40:00",
  "comment": "测试通过，可以部署",
  "artifacts_hash": "abc123",
  "approval_id": "APPR-12345678",
  "signature": null
}
```

**产物作用**：
- 审计追踪
- 下游依赖检查
- 不可抵赖性

### 7.3 下游强依赖

**设计**：下游步骤必须检查上游的审批产物

**实现**：

```python
def has_valid_approval(self, step_id: str) -> Tuple[bool, Optional[str]]:
    """检查步骤是否有有效的审批"""
    for gate_id, gate in state.get("gates", {}).items():
        if gate["step_id"] == step_id:
            if gate["status"] == "approved":
                approval_path = self.project_dir / gate.get("approval_artifact", "")
                if approval_path.exists():
                    return True, gate["approval_artifact"]
                else:
                    return False, "Approval artifact not found"
            elif gate["status"] == "pending":
                return False, f"Gate {gate_id} is pending approval"
            else:
                return False, f"Gate {gate_id} was rejected"

    return True, None  # 没有门禁要求
```

---

## 8. Token 管理

### 8.1 Token 设计

**目的**：限制 Agent 只能执行授权的操作

**Token 结构**：

```python
@dataclass
class StepToken:
    token_id: str          # TKN-XXXXXXXX
    run_id: str            # 关联运行
    step_id: str           # 关联步骤
    agent_id: str          # 关联 Agent
    issued_at: str         # 签发时间
    expires_at: str        # 过期时间
    permissions: List[str] # 权限列表
    signature: str         # HMAC 签名
    revoked: bool          # 是否已撤销
```

### 8.2 签发流程

```python
def issue_token(self, run_id: str, step_id: str, agent_id: str) -> StepToken:
    # 1. 生成 Token ID
    token_id = f"TKN-{secrets.token_hex(8).upper()}"

    # 2. 设置过期时间（默认 4 小时）
    expires = datetime.now() + timedelta(hours=4)

    # 3. 创建 Token
    token = StepToken(
        token_id=token_id,
        run_id=run_id,
        step_id=step_id,
        agent_id=agent_id,
        issued_at=datetime.now().isoformat(),
        expires_at=expires.isoformat(),
        permissions=["read", "write", "execute"],
        signature=None
    )

    # 4. 签名
    token.signature = self._sign_token(token)

    # 5. 保存
    token_path = self.tokens_dir / f"{token.token_id}.json"
    with open(token_path, 'w') as f:
        json.dump(asdict(token), f)

    return token
```

### 8.3 验证流程

```python
def validate_token(self, token_id: str, step_id: str, required_permission: str) -> Tuple[bool, Optional[str]]:
    # 1. 加载 Token
    token = self.load_token(token_id)
    if not token:
        return False, "Token not found"

    # 2. 检查撤销
    if token.revoked:
        return False, "Token has been revoked"

    # 3. 验证签名
    if not self._verify_signature(token):
        return False, "Invalid token signature"

    # 4. 检查过期
    if datetime.now() > datetime.fromisoformat(token.expires_at):
        return False, "Token has expired"

    # 5. 检查步骤匹配
    if step_id and token.step_id != step_id:
        return False, f"Token is for step {token.step_id}, not {step_id}"

    # 6. 检查权限
    if required_permission and required_permission not in token.permissions:
        return False, f"Token does not have permission: {required_permission}"

    return True, None
```

### 8.4 工具调用守卫

**权限映射**：

```python
class ToolGuard:
    TOOL_PERMISSIONS = {
        "read": ["Read", "Glob", "Grep", "WebFetch"],
        "write": ["Write", "Edit", "NotebookEdit"],
        "execute": ["Bash", "Task"],
        "deploy": ["Bash:deploy", "Bash:kubectl"],
        "commit": ["Bash:git commit", "Bash:git push"],
    }
```

**检查流程**：

```python
def check_tool_access(self, token_id: str, tool_name: str, step_id: str) -> Tuple[bool, Optional[str]]:
    # 1. 确定需要的权限
    required_permission = self._get_permission_for_tool(tool_name)

    # 2. 验证 Token
    valid, reason = self.token_manager.validate_token(
        token_id,
        step_id=step_id,
        required_permission=required_permission
    )

    return valid, reason
```

### 8.5 Token 与上下文

**编码格式**：

```python
def encode_token_for_context(self, token: StepToken) -> str:
    """将 Token 编码为可注入 LLM 上下文的格式"""
    data = {
        "t": token.token_id,
        "s": token.step_id,
        "e": token.expires_at,
        "p": token.permissions
    }
    encoded = base64.b64encode(json.dumps(data).encode()).decode()
    return f"WORKFLOW_TOKEN:{encoded}"
```

**使用方式**：

```yaml
# Agent Context 中
step_token: "WORKFLOW_TOKEN:eyJ0IjoiVEstS..."
```

---

## 9. Agent 上下文系统

### 9.1 Agent 规范

**规范路径**：`ai-spec/agents/{agent_id}/agent.yaml`

**规范结构**：

```yaml
kind: agent
version: "1.0"
id: architect
name: 架构师
version: "1.0.0"

description: |
  负责系统架构设计的 Agent

persona:
  role: "系统架构师"
  expertise: ["系统设计", "技术选型", "性能优化"]
  tone: "专业、严谨"

instructions:
  - "优先考虑系统的可扩展性"
  - "关注性能和成本"
  - "提供多个技术方案供选择"

quality_bar:
  - "架构设计必须完整"
  - "必须考虑性能指标"
  - "必须提供技术选型理由"

forbidden_behaviors:
  - id: "skip_security"
    name: "跳过安全考虑"
    description: "不允许在设计时忽略安全性"

responsibility:
  input_schema:
    type: object
    properties:
      requirements:
        type: string
  output_schema:
    type: object
    properties:
      design:
        type: string
      tech_stack:
        type: array
```

### 9.2 上下文构建

**构建流程**：

```python
def build(self, step_id: str, step_data: Dict, workflow_data: Dict, state_data: Dict) -> AgentContext:
    # 1. 提取步骤信息
    step_name = step_data.get("name", step_id)
    step_inputs = self._extract_paths(step_data.get("inputs", []))
    step_outputs = self._extract_paths(step_data.get("outputs", []))

    # 2. 获取 Agent 引用
    agent_ref = step_data.get("run", "")

    # 3. 加载 Agent Spec
    agent_spec = self._load_agent_spec(agent_ref)

    # 4. 构建上下文
    context = AgentContext(
        step_id=step_id,
        step_name=step_name,
        agent_id=agent_spec.id,
        agent_system_prompt=agent_spec.get_system_prompt(),
        agent_instructions=agent_spec.get_instructions(),
        agent_persona=agent_spec.persona,
        agent_forbidden_behaviors=agent_spec.forbidden_behaviors,
        agent_quality_bar=agent_spec.get_quality_bar(),
        # ... 其他字段
    )

    return context
```

### 9.3 上下文注入

**注入器接口**：

```python
class ContextInjector(ABC):
    @abstractmethod
    def inject(self, context: AgentContext, step_id: str) -> InjectionResult:
        """注入上下文"""
        pass

    @abstractmethod
    def get_current_context(self) -> Optional[AgentContext]:
        """获取当前上下文"""
        pass

    @abstractmethod
    def clear_context(self) -> bool:
        """清除上下文"""
        pass
```

**Claude Code 注入器**：

```python
class ClaudeCodeInjector(ContextInjector):
    def inject(self, context: AgentContext, step_id: str) -> InjectionResult:
        # 1. 序列化上下文
        context_data = asdict(context)
        context_file = self.project_dir / ".workflow" / "current-context.yaml"

        # 2. 写入文件
        with open(context_file, 'w', encoding='utf-8') as f:
            yaml.dump(context_data, f, allow_unicode=True)

        return InjectionResult(
            success=True,
            injector_name="claude_code",
            context_location=str(context_file),
            message="Context injected successfully"
        )
```

**注入器注册**：

```python
class InjectorRegistry:
    _injectors = {
        "claude_code": ClaudeCodeInjector,
        "codex_cli": CodexCLIInjector,
        # 其他注入器...
    }

    @staticmethod
    def register_injector(name: str, injector_class: type):
        """注册自定义注入器"""
        _injectors[name] = injector_class

    @staticmethod
    def create_injector(project_dir: str, injector_name: str = None) -> Optional[ContextInjector]:
        """创建注入器实例"""
        if injector_name:
            injector_class = _injectors.get(injector_name)
        else:
            # 自动检测
            injector_class = _detect_injector(project_dir)

        if injector_class:
            return injector_class(project_dir)
        return None
```

---

## 10. 事件溯源

### 10.1 事件存储

**存储格式**：JSONL（每行一个 JSON 对象）

**文件位置**：`.workflow/events.jsonl`

**写入方式**：追加模式（append-only）

**示例**：

```json
{"event_id":"EVT-20250122153045001-0001","event_type":"run_created","timestamp":"2025-01-22T15:30:45","run_id":"RUN-20250122-153045","step_id":null,"agent_id":null,"actor":"system","data":{"workflow_id":"my-workflow"}}
{"event_id":"EVT-20250122153050002-0002","event_type":"step_started","timestamp":"2025-01-22T15:30:50","run_id":"RUN-20250122-153045","step_id":"step1","agent_id":"agent:worker","actor":"agent","data":{"token":"TKN-A1B2C3D4"}}
```

### 10.2 事件查询

**过滤接口**：

```python
def get_events(self,
               event_type: EventType = None,
               step_id: str = None,
               since: str = None,
               limit: int = None) -> List[Event]:
    """查询事件"""
    events = []
    with open(self.log_path, 'r') as f:
        for line in f:
            event = Event.from_dict(json.loads(line))

            # 应用过滤条件
            if event_type and event.event_type != event_type:
                continue
            if step_id and event.step_id != step_id:
                continue
            if since and event.timestamp < since:
                continue

            events.append(event)

            if limit and len(events) >= limit:
                break

    return events
```

### 10.3 统计分析

**统计接口**：

```python
def get_statistics(self) -> Dict:
    """获取统计信息"""
    events = self.get_events()

    stats = {
        "total_events": len(events),
        "event_counts": {},
        "step_durations": {},
        "gate_wait_times": {},
        "error_count": 0,
        "retry_count": 0
    }

    # 计算步骤耗时
    step_starts = {}
    for event in events:
        if event.event_type == EventType.STEP_STARTED:
            step_starts[event.step_id] = event.timestamp
        elif event.event_type == EventType.STEP_COMPLETED:
            start = datetime.fromisoformat(step_starts[event.step_id])
            end = datetime.fromisoformat(event.timestamp)
            duration = (end - start).total_seconds()
            stats["step_durations"][event.step_id] = duration

    return stats
```

---

## 11. 追踪系统

### 11.1 Span 追踪

**Span 结构**：

```python
@dataclass
class Span:
    span_id: str
    parent_span_id: Optional[str]
    name: str
    span_type: SpanType
    status: SpanStatus
    start_time: str
    end_time: Optional[str]
    duration_ms: Optional[int]
    attributes: Dict[str, Any]
    events: List[Dict]
    links: List[str]
```

**Span 类型**：

```python
class SpanType(Enum):
    STEP = "step"
    VALIDATION = "validation"
    GATE = "gate"
    TOOL_CALL = "tool_call"
```

**Span 状态**：

```python
class SpanStatus(Enum):
    SUCCESS = "success"
    FAILED = "failed"
    RUNNING = "running"
    TIMEOUT = "timeout"
```

### 11.2 TracedStateMachine

**集成方式**：装饰器模式

```python
class TracedStateMachine(StateMachine):
    """带追踪的状态机"""

    def __init__(self, project_dir: str):
        super().__init__(project_dir)
        self.trace_log = TraceLog(project_dir, self._state["run_id"])

    def start_step(self, step_id: str, agent_id: str, token: str) -> Tuple[bool, Optional[str]]:
        # 创建 Span
        span = self.trace_log.create_span(
            name=step_id,
            span_type=SpanType.STEP,
            attributes={
                "agent_id": agent_id,
                "token": token
            }
        )

        # 执行原方法
        success, reason = super().start_step(step_id, agent_id, token)

        # 关闭 Span
        if success:
            self.trace_log.finish_span(span.span_id, SpanStatus.SUCCESS)
        else:
            self.trace_log.finish_span(span.span_id, SpanStatus.FAILED, error=reason)

        return success, reason
```

### 11.3 追踪导出

**Markdown 格式**：

```python
def export_markdown_report(self, output_path: str = None) -> str:
    """导出 Markdown 格式的追踪报告"""
    spans = self.get_spans()

    lines = []
    lines.append("# Execution Trace Report\n")
    lines.append(f"Generated: {datetime.now().isoformat()}\n")

    for span in spans:
        lines.append(f"## {span.name}")
        lines.append(f"- Type: {span.span_type.value}")
        lines.append(f"- Status: {span.status.value}")
        lines.append(f"- Duration: {span.duration_ms}ms")

        if span.events:
            lines.append("\n### Events")
            for event in span.events:
                lines.append(f"- {event['timestamp']}: {event['name']}")

        lines.append("")

    report = "\n".join(lines)

    if output_path:
        with open(output_path, 'w') as f:
            f.write(report)

    return output_path
```

---

## 12. 跨平台集成

### 12.1 集成架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    跨平台集成架构                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐  │
│  │ Claude    │  │ Codex     │  │ Gemini    │  │ Custom    │  │
│  │ Code      │  │ CLI       │  │ Code      │  │ Agent     │  │
│  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  │
│        │              │              │              │          │
│        ▼              ▼              ▼              ▼          │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │                    Adapter Layer                         │  │
│  │  (inject_context, check_token, log_action)              │  │
│  └─────────────────────────────────────────────────────────┘  │
│                              │                                 │
│                              ▼                                 │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │                  Orchestrator Core                       │  │
│  │  StateMachine, EventLog, TokenManager                   │  │
│  └─────────────────────────────────────────────────────────┘  │
│                              │                                 │
│                              ▼                                 │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │                   File System                            │  │
│  │  .workflow/state.yaml, events.jsonl, tokens/            │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 12.2 Claude Code 集成

**配置文件**：`CLAUDE.md`

```markdown
## 工作流执行规则

执行任何开发任务前，必须：

1. 运行 `python -m flowcore.orchestrator status .` 检查当前状态
2. 如果有待审批门禁，等待人类审批
3. 获取当前步骤的 token: `python -m flowcore.orchestrator token . <step_id>`
4. 完成后运行验证: `python -m flowcore.orchestrator validate . <step_id>`

违反上述规则的操作将被拒绝。
```

**上下文注入**：`.workflow/current-context.yaml`

```yaml
step_id: "step1"
step_name: "生成报告"
agent_id: "architect"
agent_system_prompt: |
  你是一个系统架构师...
agent_instructions:
  - "优先考虑系统的可扩展性"
  - "关注性能和成本"
step_token: "WORKFLOW_TOKEN:eyJ0IjoiVEstS..."
```

### 12.3 Codex CLI 集成

**配置文件**：`codex-constitution.yaml`

```yaml
pre_execute_hook: "python -m flowcore.orchestrator check . --token $STEP_TOKEN"
post_execute_hook: "python -m flowcore.orchestrator complete . --step $STEP_ID"
```

### 12.4 自定义集成

**实现注入器**：

```python
class MyCustomInjector(ContextInjector):
    def inject(self, context: AgentContext, step_id: str) -> InjectionResult:
        # 自定义注入逻辑
        # 例如：写入数据库、发送 API 等
        pass

# 注册注入器
InjectorRegistry.register_injector("my_custom", MyCustomInjector)
```

---

## 13. 扩展性设计

### 13.1 自定义验证器

**接口**：

```python
class Validator(ABC):
    @abstractmethod
    def validate(self, step_id: str, outputs: List[str]) -> Tuple[bool, List[str]]:
        """
        验证步骤输出

        Returns:
            (是否通过, 错误列表)
        """
        pass
```

**示例**：

```python
class FileSizeValidator(Validator):
    def __init__(self, max_size_mb: int = 10):
        self.max_size = max_size_mb * 1024 * 1024

    def validate(self, step_id: str, outputs: List[str]) -> Tuple[bool, List[str]]:
        errors = []
        for output in outputs:
            if os.path.getsize(output) > self.max_size:
                errors.append(f"File too large: {output}")

        return len(errors) == 0, errors
```

### 13.2 自定义注入器

**接口**：

```python
class ContextInjector(ABC):
    @abstractmethod
    def inject(self, context: AgentContext, step_id: str) -> InjectionResult:
        pass

    @abstractmethod
    def get_current_context(self) -> Optional[AgentContext]:
        pass

    @abstractmethod
    def clear_context(self) -> bool:
        pass
```

### 13.3 自定义门禁类型

**扩展**：支持自定义门禁类型

```yaml
steps:
  - id: custom_step
    custom_gate:
      type: "external_approval"
      config:
        endpoint: "https://approval-system.example.com/api/approve"
        timeout: 3600
```

---

## 14. 安全设计

### 14.1 Token 安全

**签名机制**：HMAC-SHA256

```python
def _sign_token(self, token: StepToken) -> str:
    """签名 Token"""
    data = f"{token.token_id}:{token.run_id}:{token.step_id}:{token.expires_at}"
    signature = hmac.new(
        self._get_secret(),
        data.encode(),
        hashlib.sha256
    ).hexdigest()
    return signature
```

**密钥管理**：

- 密钥存储：`.workflow/.secret`
- 密钥生成：`secrets.token_bytes(32)`
- 密钥权限：仅 owner 可读写（Unix）

### 14.2 文件权限

**敏感文件**：

```
.workflow/.secret        # 600 (仅 owner)
.workflow/tokens/        # 700 (仅 owner)
.workflow/approvals/     # 755 (可读)
```

### 14.3 输入验证

**路径验证**：

```python
def _validate_path(path: str) -> bool:
    """验证路径安全性"""
    # 防止路径遍历
    if ".." in path or path.startswith("/"):
        return False

    # 防止命令注入
    if any(char in path for char in [';', '&', '|', '$']):
        return False

    return True
```

### 14.4 审计追踪

**完整记录**：

- 所有状态变更
- 所有 Token 签发
- 所有门禁审批
- 所有工具调用

**不可篡改**：

- 事件日志：append-only
- Token 签名：HMAC
- Approval artifact：hash 绑定

---

## 15. 性能考虑

### 15.1 文件 I/O

**优化策略**：

1. **批量写入**：事件日志批量刷盘
2. **延迟加载**：按需加载状态文件
3. **缓存**：内存缓存已加载的状态

**示例**：

```python
class StateMachine:
    def __init__(self, project_dir: str):
        self._state_cache = None  # 缓存

    def load(self) -> Dict:
        if self._state_cache is None:
            with open(self.state_path) as f:
                self._state_cache = yaml.safe_load(f)
        return self._state_cache

    def _save_state(self):
        # 更新缓存
        self._state["updated_at"] = datetime.now().isoformat()
        self._state_cache = self._state

        # 写入文件
        with open(self.state_path, 'w') as f:
            yaml.dump(self._state, f)
```

### 15.2 并发控制

**文件锁**：

```python
import fcntl

def _save_state_with_lock(self):
    """带文件锁的保存"""
    with open(self.state_path, 'w') as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        yaml.dump(self._state, f)
        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
```

### 15.3 内存优化

**事件流式处理**：

```python
def get_events(self, filters: Dict = None) -> Iterator[Event]:
    """流式读取事件"""
    with open(self.log_path, 'r') as f:
        for line in f:
            event = Event.from_dict(json.loads(line))

            # 应用过滤
            if self._matches_filters(event, filters):
                yield event
```

---

## 16. 技术选型

### 16.1 编程语言

**选择**：Python 3.10+

**原因**：
- 广泛的 AI 工具支持
- 丰富的生态系统
- 易于扩展和维护

### 16.2 数据格式

**YAML**：
- 配置文件（workflow.yaml, agent.yaml）
- 状态文件（state.yaml）

**JSON**：
- Token 存储
- Approval artifact
- Manifest

**JSONL**：
- 事件日志（events.jsonl）
- 追踪日志（traces.jsonl）

### 16.3 依赖库

**核心依赖**：

```toml
[tool.poetry.dependencies]
python = "^3.10"
pyyaml = "^6.0"
pydantic = "^2.0"

# 可选依赖
metagpt = {version = "^0.8.0", optional = true}
```

**开发依赖**：

```toml
[tool.poetry.dev-dependencies]
pytest = "^7.0"
pytest-cov = "^4.0"
black = "^23.0"
mypy = "^1.0"
```

### 16.4 存储系统

**文件系统**：

**优势**：
- 简单、可靠
- 易于备份
- 不需要额外服务

**目录结构**：

```
.workflow/
├── state.yaml           # 状态文件
├── events.jsonl         # 事件日志
├── traces/              # 追踪日志
│   └── traces.jsonl
├── tokens/              # Token 存储
│   └── TKN-XXX.json
├── approvals/           # 审批产物
│   └── gate_id.json
└── manifests/           # 产物清单
    └── step_id.manifest.json
```

---

## 附录

### A. 错误码

| 错误码 | 说明 |
|-------|------|
| `E001` | 工作流未初始化 |
| `E002` | 步骤不存在 |
| `E003` | 步骤状态错误 |
| `E004` | 依赖未完成 |
| `E005` | 门禁未通过 |
| `E006` | Token 无效 |
| `E007` | Token 过期 |
| `E008` | 权限不足 |
| `E009` | 产物验证失败 |
| `E010` | Agent 规范未找到 |

### B. 性能指标

| 指标 | 目标 |
|------|------|
| 步骤启动延迟 | < 100ms |
| 状态保存时间 | < 50ms |
| 事件写入延迟 | < 10ms |
| Token 验证时间 | < 5ms |
| 内存占用 | < 100MB |

### C. 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.0 | 2024-12-01 | 初始版本 |
| v1.1 | 2024-12-15 | 添加追踪系统 |
| v1.2 | 2025-01-01 | 添加 Agent 上下文 |
| v1.3 | 2025-01-10 | 添加测试流程扩展 |
| v1.4 | 2025-01-15 | 添加详细日志 |
| v1.5 | 2025-01-18 | 改进 Artifact Gate |
| v1.6 | 2025-01-22 | 添加 Workflow Generator |

---

**文档版本**: v1.6
**最后更新**: 2025-01-22
**维护者**: LEE 框架团队
