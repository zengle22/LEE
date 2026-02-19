---
title: Orchestrator 统一 Engine 接口 - 实施方案总结
author: LEE Team
date: 2026-01-29
version: 1.0
last_updated: 2026-02-19
---

# Orchestrator 统一 Engine 接口 - 实施方案总结

**版本**: v1.0
**更新日期**: 2025-01-22
**状态**: 已实现

---

## 📋 方案概述

按照您的建议，我们已经实现了 Orchestrator 的统一 Engine 接口，让 Orchestrator 更"纯"、Engine 更统一。

### 核心改进

1. ✅ **Orchestrator 职责更清晰**：只负责编排，不关心具体 Engine 实现
2. ✅ **统一的执行协议**：定义了 `StepExecutionRequest/Result` 标准接口
3. ✅ **Engine 注册机制**：支持可插拔的 Engine 架构
4. ✅ **LLMExecutor 作为默认引擎**：直接调用大模型 API
5. ✅ **MetaGPTExecutor 符合统一接口**：可插拔的"重型引擎"

---

## 🏗️ 架构设计

### 整体架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Orchestrator 统一 Engine 架构                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    Orchestrator (编排层)                      │   │
│  │                                                              │   │
│  │  职责：                                                       │   │
│  │  - 管理工作流状态                                            │   │
│  │  - 加载 Agent 规范                                           │   │
│  │  - 构建执行上下文                                            │   │
│  │  - 调用 Engine 执行                                          │   │
│  │  - 验证产物                                                  │   │
│  │  - 更新状态                                                  │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                              │                                     │                    │
│                              ▼                                     │                    │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │               统一执行协议 (protocol.py)                     │   │
│  │                                                              │   │
│  │  - StepExecutionRequest (输入)                              │   │
│  │  - StepExecutionResult (输出)                                │   │
│  │  - ArtifactReference (产物引用)                              │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                              │                                     │                    │
│                              ▼                                     │                    │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                 EngineRegistry (注册中心)                     │   │
│  │                                                              │   │
│  │  - 管理 Engine 注册                                           │   │
│  │  - 创建 Executor 实例                                          │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                              │                                     │                    │
│                ┌───────────────┴─────────────┐                       │
│                ▼                               ▼                       │
│  ┌─────────────────────┐         ┌─────────────────────┐           │
│  │   LLMExecutor        │         │ MetaGPTExecutor     │           │
│  │   (默认引擎)         │         │ (可选引擎)          │           │
│  └─────────────────────┘         └─────────────────────┘           │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 📁 文件结构

```
flowcore/
├── engines/
│   ├── protocol.py              # 统一执行协议（新增）
│   ├── base.py                  # BaseExecutor + EngineRegistry（新增）
│   ├── llm/
│   │   ├── executor.py          # LLM Executor（新增）
│   │   └── __init__.py          # LLM Engine 模块（新增）
│   └── metagpt/
│       ├── executor_v2.py        # MetaGPT Executor v2（新增）
│       └── __init__.py          # 更新（同时支持新旧接口）
└── orchestrator/
    └── engine_commands.py       # 新的 CLI 命令（新增）

examples/unified-engine-demo/    # 完整示例
├── workflow.yaml               # 工作流定义
├── agents/
│   ├── writer/agent.yaml       # Writer Agent
│   └── reviewer/agent.yaml    # Reviewer Agent
├── run_demo.py                # 端到端 Demo
└── README.md                  # 使用说明
```

---

## 🔧 核心组件

### 1. 统一执行协议 (protocol.py)

定义了 Orchestrator 与 Engine 之间的标准接口：

```python
@dataclass
class StepExecutionRequest:
    """执行请求"""
    project_dir: str
    step_id: str
    run_id: str
    agent_spec: Dict[str, Any]
    context: Dict[str, Any]
    ...

@dataclass
class StepExecutionResult:
    """执行结果"""
    status: Literal["completed", "failed", "skipped", "timeout"]
    outputs: List[ArtifactReference]
    messages: List[Dict[str, Any]]
    error: Optional[str]
    ...
```

### 2. Engine Registry (base.py)

管理所有可用的 Engine：

```python
class EngineRegistry:
    """Engine 注册表"""

    @classmethod
    def register(cls, engine_type: str):
        """装饰器：注册 Engine"""
        ...

    @classmethod
    def create(cls, agent_spec: Dict, project_dir: str):
        """创建 Executor 实例"""
        ...
```

### 3. LLMExecutor (engines/llm/executor.py)

直接调用大模型 API 的默认引擎：

**支持的 Provider**：
- OpenAI (GPT-4, GPT-3.5)
- Anthropic (Claude)
- Azure OpenAI
- 任何兼容 OpenAI API 的服务

**配置示例**：
```yaml
engine:
  type: llm
  provider: openai
  model: gpt-4
  api_key: ${OPENAI_API_KEY}
```

### 4. MetaGPTExecutor (engines/metagpt/executor_v2.py)

使用 MetaGPT 框架的"重型引擎"：

**特性**：
- 支持多角色协作
- 支持工具调用
- 支持多轮对话

**配置示例**：
```yaml
engine:
  type: metagpt
  role: Developer
  config:
    llm:
      model: gpt-4
      api_key: ${OPENAI_API_KEY}
```

---

## 🚀 使用方式

### 方式 1: 使用新命令（推荐）

```bash
# 初始化工作流
python -m flowcore.orchestrator init . --workflow workflow.yaml

# 使用统一 Engine 接口执行步骤
python -m flowcore.orchestrator run-engine . step1_write_doc

# 或自动选择下一个步骤
python -m flowcore.orchestrator run-engine .
```

### 方式 2: 在代码中使用

```python
from flowcore.engines.protocol import StepExecutionRequest
from flowcore.engines.base import EngineRegistry

# 1. 构建请求
request = StepExecutionRequest(
    project_dir="./project",
    step_id="step1",
    run_id="RUN-001",
    agent_spec=agent_spec,
    context=context
)

# 2. 创建 Executor
executor = EngineRegistry.create(agent_spec, "./project")

# 3. 执行
result = await executor.execute(request)
```

---

## 📖 完整示例

### 示例位置

```
examples/unified-engine-demo/
├── workflow.yaml               # 工作流定义
├── agents/
│   ├── writer/agent.yaml       # Writer Agent
│   └── reviewer/agent.yaml    # Reviewer Agent
├── run_demo.py                # 端到端 Demo
└── README.md                  # 使用说明
```

### 运行 Demo

```bash
# 1. 设置环境变量
export OPENAI_API_KEY="sk-..."

# 2. 运行 Demo
cd examples/unified-engine-demo
python run_demo.py
```

---

## 🔄 与旧架构的对比

### 旧架构（需要外部 AI 工具）

```
Orchestrator ──► 注入上下文 ──► [Claude Code] ──► 调用大模型 ──► 生成产物
     ↑                                                           │
     └────────────────────── 验证产物 ◄───────────────────────────┘
```

**问题**：
- 依赖外部 AI 工具（Claude Code）
- 无法完全自动化执行
- 难以集成到 CI/CD

### 新架构（统一 Engine 接口）

```
Orchestrator ──► EngineRegistry ──► [LLMExecutor/MetaGPTExecutor] ──► 调用大模型
     │                                                              │
     │                                                              │
     └──────────────────────────────── 验证产物 ◄─────────────────────┘
```

**优势**：
- ✅ 完全自动化执行
- ✅ 不依赖外部 AI 工具
- ✅ 易于集成到 CI/CD
- ✅ Engine 可插拔

---

## 🎯 设计原则

### 1. Orchestrator 职责单一

**只负责**：
- 管理工作流状态
- 构建执行上下文
- 调用 Engine
- 验证产物

**不负责**：
- 知道具体的 Engine 实现
- 理解 MetaGPT 或 OpenAI 的概念
- 管理大模型 API 调用

### 2. Engine 接口统一

所有 Engine 实现相同的接口：

```python
class BaseExecutor(ABC):
    @abstractmethod
    async def execute(self, request: StepExecutionRequest) -> StepExecutionResult:
        ...
```

### 3. 可插拔架构

通过注册机制支持新 Engine：

```python
@EngineRegistry.register("custom")
def create_custom_executor(agent_spec, project_dir):
    return CustomExecutor(project_dir, agent_spec)
```

---

## 🛠️ 扩展指南

### 添加自定义 Engine

#### 步骤 1: 创建 Executor 类

```python
# flowcore/engines/custom/executor.py

from flowcore.engines.base import AbstractExecutor
from flowcore.engines.protocol import StepExecutionRequest, StepExecutionResult

class CustomExecutor(AbstractExecutor):
    async def execute(self, request: StepExecutionRequest) -> StepExecutionResult:
        # 实现执行逻辑
        ...
        return StepExecutionResult(status="completed", ...)
```

#### 步骤 2: 注册到 EngineRegistry

```python
# flowcore/engines/custom/__init__.py

from .executor import CustomExecutor
from flowcore.engines.base import EngineRegistry

def create_executor(agent_spec, project_dir):
    return CustomExecutor(project_dir, agent_spec)

EngineRegistry.register("custom")(create_executor)
```

#### 步骤 3: 在 Agent 规范中使用

```yaml
# agents/myagent/agent.yaml
kind: agent
id: myagent
name: My Agent

engine:
  type: custom  # 使用自定义引擎
  custom_config:
    ...
```

---

## 📋 后续工作

### 短期（已完成）

- [x] 设计统一执行协议
- [x] 实现 EngineRegistry
- [x] 实现 LLMExecutor
- [x] 改写 MetaGPTExecutor
- [x] 创建完整示例
- [x] 创建端到端 Demo

### 中期（待实现）

- [ ] 更新主 CLI 集成 run-engine 命令
- [ ] 完善错误处理和日志
- [ ] 添加更多 Engine（Python、Shell）
- [ ] 性能优化和测试

### 长期（未来规划）

- [ ] 支持流式输出（实时显示 LLM 响应）
- [ ] 支持 Tool Calling（函数调用）
- [ ] 支持多模态输入输出
- [ ] Web UI 界面

---

## 🎉 总结

通过这次改进，我们实现了：

1. **更清晰的边界**：Orchestrator 不关心具体 Engine 实现
2. **统一的接口**：所有 Engine 实现相同协议
3. **可插拔架构**：轻松添加新的 Engine
4. **开箱即用**：LLMExecutor 作为默认引擎
5. **向后兼容**：保留旧的 MetaGPT Adapter

现在 Orchestrator 可以：
- ✅ 完全独立运行（不需要 Claude Code）
- ✅ 直接调用大模型（OpenAI、Claude 等）
- ✅ 可选集成 MetaGPT（更强大的功能）
- ✅ 支持自定义 Engine（灵活扩展）

---

**文档版本**: v1.0
**最后更新**: 2025-01-22
**维护者**: LEE 框架团队
