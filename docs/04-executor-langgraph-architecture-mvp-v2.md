---
title: LEE Executor (基于 LangGraph) 架构设计 - MVP 版本 v2
author: LEE Team
date: 2026-01-29
version: v3.1-MVP-v2
last_updated: 2026-02-19
---

# LEE Executor (基于 LangGraph) 架构设计 - MVP 版本 v2

> **版本:** v3.1-MVP-v2
> **状态:** MVP 设计（精简版，架构评审修正版）
> **创建日期:** 2026-01-29
> **作者:** LEE Team
> **基于:** v3.1-MVP + 架构评审反馈修正

---

## 📋 文档说明

本文档是 `04-executor-langgraph-architecture-mvp.md` 的 **架构评审修正版本**，基于评审反馈进行了以下调整：

### ✅ v2 修复的问题

1. **层级命名澄清** - 明确与 v3.1 L1/L2/L3 的关系
2. **BaseState 补全** - 添加 metrics、tokens_used 字段
3. **补充 registry.py** - 完整的 Graph Builder 注册表实现
4. **补充 profiles/loader.py** - LLM Profile 加载器实现
5. **添加条件边** - 实现错误快速失败机制
6. **迁移策略说明** - 与现有 v3.1 Executor 的关系
7. **SpanBuilder 实现** - 完整的追踪构建器
8. **Graph 状态修改** - 改为函数式风格，返回新 state

### ⏸️ 暂缓的功能（保持不变）

- [ ] 完整的重试策略（只在 Runner 外部做简单重试）
- [ ] 并行执行支持（先做单线程）
- [ ] Validator registry（先手动调用简单 validator）
- [ ] LLM 工具调用（call_llm_with_tools）
- [ ] 异步/分布式后端（只用 LangGraph 同步版本）
- [ ] LLM 成本统计（先只记 tokens_used）

---

## 🔗 与 v3.1 架构的关系

### 层级命名澄清

**重要**: 本文档的 Layer 命名与 v3.1 的 L1/L2/L3 Workflow 层级是**不同的概念**：

| 本文档（执行架构层） | v3.1（工作流层级） | 说明 |
|---------------------|-------------------|------|
| Layer-Orchestrator | Runtime Core | 编排调度层 |
| Layer-Executor | Executors Layer | 执行器层 |
| Layer-Tools | External World 接口 | 工具/外部系统层 |

```
v3.1 Workflow 层级:           本文档 执行架构层:
┌─────────────────┐           ┌─────────────────────┐
│ L1: Project     │           │ Layer-Orchestrator  │
├─────────────────┤           │ (读取 workflow.yaml │
│ L2: Department  │  ──使用──▶│  调度 task_type)    │
├─────────────────┤           ├─────────────────────┤
│ L3: Task        │           │ Layer-Executor      │
└─────────────────┘           │ (LangGraph 实现)    │
                              ├─────────────────────┤
                              │ Layer-Tools         │
                              │ (fs/shell/llm)      │
                              └─────────────────────┘
```

### 与现有 v3.1 Executor 的迁移策略

本 MVP 设计采用**渐进式替换**策略：

1. **Phase A/B (当前)**: 新的 LangGraph Executor 与现有 Executor **并存**
   - 现有 `LLMExecutor`, `ShellExecutor`, `MetaGPTExecutor` 继续工作
   - 新的 LangGraph Executor 处理特定 `task_type`
   - 通过 `execution_context.task_type` 字段路由

2. **Phase C 后**: 验证稳定后，逐步迁移
   - 将现有 Executor 的功能迁移到 LangGraph Graph
   - 保持 API 兼容性

3. **最终目标**: 完全替换现有 Executor，统一使用 LangGraph 架构
   - 所有执行逻辑通过 Graph 定义
   - 更好的可观测性和可测试性

---

## 🎯 核心概念

### 三层执行架构

```
┌─────────────────────────────────────────────────────────────────┐
│  Layer-Orchestrator (编排层)                                      │
│  - 读取 workflow.yaml                                            │
│  - 解析步骤依赖                                                   │
│  - 选择 task_type                                                │
│  - 调用 Executor.run_task(task_spec)                            │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  Layer-Executor (执行层) - 本文档设计重点                          │
│  - 接收 ExecutorTaskSpec                                         │
│  - 根据 task_type 选择 Graph Builder                              │
│  - 构建 LangGraph 流程                                           │
│  - 执行并返回 ExecutionResult                                    │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  Layer-Tools (工具层)                                            │
│  - fs_tools: 文件读写                                            │
│  - shell_tools: 命令执行                                         │
│  - llm_tools: LLM 调用                                          │
│  - security: 安全边界                                            │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📁 目录结构（MVP v2）

```
lee_runtime/
  executor/
    __init__.py                       # Executor 模块导出
    types.py                          # 核心数据类型（v2 修正版）
    registry.py                       # task_type -> Graph Builder 注册表 [补充实现]
    langgraph_runner.py               # 核心入口：run_task（仅同步）
    tools/
      __init__.py
      fs_tools.py                     # 文件系统工具
      shell_tools.py                  # Shell 命令工具
      llm_tools.py                    # LLM 调用工具（仅 Anthropic）
      security.py                     # 安全边界工具
    graphs/
      __init__.py
      common.py                       # [NEW] 公共条件边和辅助函数
      impl_coding.py                  # l3.impl.coding 实现 Graph（v2 修正版）
      unit_test.py                    # l3.test.unit 测试 Graph（v2 修正版）
    tracing/
      __init__.py
      span_builder.py                 # Span 构建器 [补充实现]
    profiles/
      __init__.py
      loader.py                       # Profile 加载器 [补充实现]
    tests/
      __init__.py
      test_graphs.py                  # Graph 单元测试
      test_integration.py             # 集成测试
```

---

## 📦 核心类型定义（v2 修正版）

### `lee_runtime/executor/types.py`

```python
"""
LEE Executor 核心类型定义（MVP v2 版本）

定义 Orchestrator -> Executor 之间的统一数据契约。

v2 修正:
- BaseState 添加 metrics、tokens_used 字段
- 添加字段默认值说明
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, TypedDict, NotRequired
from enum import Enum
from datetime import datetime


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


@dataclass
class ExecutorTaskSpec:
    """
    Executor 任务规格

    Orchestrator 填写此规格并传递给 Executor.run_task()
    """
    # 基础标识
    task_id: str                           # 任务唯一标识
    task_type: str                         # 任务类型，映射到 Graph Builder

    # 输入输出映射（逻辑名 -> 真实路径）
    inputs: Dict[str, str] = field(default_factory=dict)
    outputs: Dict[str, str] = field(default_factory=dict)

    # 执行参数
    params: Dict[str, Any] = field(default_factory=dict)

    # LLM 配置
    llm_profile: Optional[str] = None         # LLM Profile 名称
    llm_temperature: Optional[float] = None   # LLM 温度
    llm_max_tokens: Optional[int] = None      # LLM 最大 token

    # 约束配置
    timeout_seconds: int = 3600              # 超时时间
    max_retries: int = 3                     # 最大重试次数

    # 上下文信息
    context: Dict[str, Any] = field(default_factory=dict)

    # 追踪信息
    trace_id: Optional[str] = None             # 关联 Execution Trace
    parent_span_id: Optional[str] = None       # 父 Span ID

    # 安全边界
    workspace_root: Optional[str] = None       # 工作区根目录（用于安全边界）
    allowed_write_patterns: List[str] = field(default_factory=list)  # 允许写入的路径模式


@dataclass
class ExecutionResult:
    """
    Executor 执行结果

    Executor 返回给 Orchestrator 的统一出参
    """
    task_id: str
    status: TaskStatus
    message: str                            # 状态描述

    # 产物信息
    artifacts: Dict[str, str] = field(default_factory=dict)  # 逻辑输出名 -> 真实路径
    artifact_metadata: Dict[str, Any] = field(default_factory=dict)  # 产物元数据

    # 执行日志
    logs: List[str] = field(default_factory=list)        # 执行过程日志
    error_details: Optional[str] = None            # 错误详情（如果失败）

    # 度量信息
    metrics: Dict[str, Any] = field(default_factory=dict)
    duration_seconds: float = 0.0
    tokens_used: int = 0
    retry_count: int = 0

    # 时间戳（统一使用 datetime）
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # 自由扩展字段
    extra: Dict[str, Any] = field(default_factory=dict)


# ============================================
# Graph State 类型定义（v2 修正版）
# ============================================

class BaseState(TypedDict, total=False):
    """
    LangGraph State 的基础类型（TypedDict 版本）

    所有 Graph 的 State 都应该包含这些基础字段。

    注意：这是类型提示，运行时使用普通 dict 即可。

    v2 修正:
    - 添加 metrics 字段用于收集执行指标
    - 添加 tokens_used 字段统计 token 消耗
    - 添加 should_stop 字段用于条件边判断
    """
    task: ExecutorTaskSpec               # 任务规格（入参）
    logs: List[str]                      # 执行日志
    errors: List[str]                    # 错误日志
    current_step: str                    # 当前步骤名，初始为 "start"
    retry_count: int                     # 重试次数，初始为 0
    started_at: datetime                 # 开始时间（datetime 类型）
    completed_at: NotRequired[datetime]  # 完成时间（可选）
    # v2 新增
    metrics: Dict[str, Any]              # 执行过程中收集的指标
    tokens_used: int                     # 累计 token 消耗
    should_stop: bool                    # 是否应该停止执行（用于条件边）


# 具体 Graph 的 State 定义
class ImplCodingState(BaseState, total=False):
    """实现类任务 State"""
    inputs: Dict[str, str]               # 加载的输入内容
    prd: str                             # PRD 内容
    design: str                          # 设计文档内容
    contract: str                        # 实现契约内容
    impl_plan: str                       # 实现方案
    code_changes: Dict[str, str]         # 代码变更（文件路径 -> 内容）
    exec_result: ExecutionResult         # 最终执行结果


class UnitTestState(BaseState, total=False):
    """单元测试任务 State"""
    test_command: str                    # 测试命令
    test_config: Dict[str, Any]          # 测试配置
    test_report: str                     # 测试报告内容
    test_results: Dict[str, Any]         # 测试结果
    exec_result: ExecutionResult         # 最终执行结果
```

---

## 🏗️ 核心组件（v2 修正版）

### 1. Graph Builder 注册表（补充实现）

#### `lee_runtime/executor/registry.py`

```python
"""
LEE Executor - Graph Builder 注册表

管理 task_type 到 Graph Builder 的映射。
"""

from typing import Callable, Dict, Optional, Any
from .types import ExecutorTaskSpec

# Graph Builder 类型定义
# 接收 ExecutorTaskSpec，返回编译后的 LangGraph
GraphBuilder = Callable[[ExecutorTaskSpec], Any]

# 注册表存储
_GRAPH_BUILDERS: Dict[str, GraphBuilder] = {}


def register_graph(task_type: str, builder: GraphBuilder) -> None:
    """
    注册 Graph Builder

    Args:
        task_type: 任务类型（如 "l3.impl.coding"）
        builder: Graph 构建函数
    """
    _GRAPH_BUILDERS[task_type] = builder


def get_graph_builder(task_type: str) -> Optional[GraphBuilder]:
    """
    获取 Graph Builder

    Args:
        task_type: 任务类型

    Returns:
        对应的 Graph Builder，如果不存在则返回 None
    """
    return _GRAPH_BUILDERS.get(task_type)


def list_registered_types() -> list[str]:
    """列出所有已注册的 task_type"""
    return list(_GRAPH_BUILDERS.keys())


def _auto_register() -> None:
    """自动注册内置 Graph Builder"""
    from .graphs.impl_coding import build_impl_coding_graph
    from .graphs.unit_test import build_unit_test_graph

    register_graph("l3.impl.coding", build_impl_coding_graph)
    register_graph("l3.test.unit", build_unit_test_graph)


# 模块加载时自动注册
_auto_register()
```

---

### 2. LLM Profile 加载器（补充实现）

#### `lee_runtime/executor/profiles/__init__.py`

```python
"""LLM Profile 模块"""
from .loader import load_profile, get_client, LLMProfile

__all__ = ["load_profile", "get_client", "LLMProfile"]
```

#### `lee_runtime/executor/profiles/loader.py`

```python
"""
LEE Executor - LLM Profile 加载器

管理 LLM 配置和客户端实例。

MVP 版本：只支持 Anthropic，硬编码默认配置。
"""

from dataclasses import dataclass
from typing import Optional, Any
import os


@dataclass
class LLMProfile:
    """LLM Profile 配置"""
    name: str
    provider: str  # "anthropic" | "openai" (MVP 只支持 anthropic)
    model: str
    api_key: str
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    # 扩展配置
    base_url: Optional[str] = None
    timeout: int = 120


# 内置 Profile 定义
_BUILTIN_PROFILES: dict[str, dict] = {
    "default": {
        "provider": "anthropic",
        "model": "claude-sonnet-4-20250514",
        "temperature": 0.3,
        "max_tokens": 4096,
    },
    "claudebot": {
        "provider": "anthropic",
        "model": "claude-sonnet-4-20250514",
        "temperature": 0.3,
        "max_tokens": 4096,
    },
    "claude-opus": {
        "provider": "anthropic",
        "model": "claude-opus-4-20250514",
        "temperature": 0.2,
        "max_tokens": 8192,
    },
    "claude-haiku": {
        "provider": "anthropic",
        "model": "claude-haiku-4-20250514",
        "temperature": 0.5,
        "max_tokens": 2048,
    },
}


def load_profile(name: str) -> LLMProfile:
    """
    加载 LLM Profile

    Args:
        name: Profile 名称

    Returns:
        LLMProfile 实例

    Raises:
        ValueError: Profile 不存在
    """
    if name not in _BUILTIN_PROFILES:
        raise ValueError(
            f"Unknown profile: {name}. "
            f"Available: {list(_BUILTIN_PROFILES.keys())}"
        )

    config = _BUILTIN_PROFILES[name]

    # 获取 API Key
    api_key = ""
    if config["provider"] == "anthropic":
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY environment variable not set"
            )
    elif config["provider"] == "openai":
        api_key = os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY environment variable not set"
            )

    return LLMProfile(
        name=name,
        provider=config["provider"],
        model=config["model"],
        api_key=api_key,
        temperature=config.get("temperature"),
        max_tokens=config.get("max_tokens"),
        base_url=config.get("base_url"),
        timeout=config.get("timeout", 120),
    )


def get_client(profile: LLMProfile) -> Any:
    """
    获取 LLM Client

    Args:
        profile: LLM Profile

    Returns:
        LLM Client 实例

    Raises:
        ValueError: 不支持的 provider
    """
    if profile.provider == "anthropic":
        try:
            from anthropic import Anthropic
        except ImportError:
            raise ImportError(
                "anthropic package not installed. "
                "Run: pip install anthropic"
            )

        return Anthropic(
            api_key=profile.api_key,
            base_url=profile.base_url,
            timeout=profile.timeout,
        )

    elif profile.provider == "openai":
        raise ValueError(
            "OpenAI provider not supported in MVP version. "
            "Use Anthropic profiles."
        )

    else:
        raise ValueError(f"Unsupported provider: {profile.provider}")
```

---

### 3. Span Builder（补充实现）

#### `lee_runtime/executor/tracing/__init__.py`

```python
"""追踪模块"""
from .span_builder import SpanBuilder

__all__ = ["SpanBuilder"]
```

#### `lee_runtime/executor/tracing/span_builder.py`

```python
"""
LEE Executor - Span 构建器

用于记录执行过程的追踪信息。

MVP 版本：简化实现，只记录基本信息。
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class SpanBuilder:
    """
    Span 构建器

    用于构建和记录执行追踪信息。
    """
    task_id: str
    task_type: str
    trace_id: Optional[str] = None
    parent_span_id: Optional[str] = None
    span_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    started_at: datetime = field(default_factory=datetime.now)

    # 内部状态
    _events: List[Dict[str, Any]] = field(default_factory=list)
    _completed: bool = False

    def add_event(
        self,
        name: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        添加事件

        Args:
            name: 事件名称
            data: 事件数据
        """
        self._events.append({
            "name": name,
            "timestamp": datetime.now().isoformat(),
            "data": data or {},
        })

    def complete(
        self,
        status: str,
        message: str,
        metrics: Optional[Dict[str, Any]] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        完成 Span 记录

        Args:
            status: 最终状态
            message: 状态消息
            metrics: 执行指标
            extra: 额外数据

        Returns:
            完整的 Span 记录
        """
        if self._completed:
            logger.warning(f"Span {self.span_id} already completed")

        self._completed = True
        completed_at = datetime.now()
        duration = (completed_at - self.started_at).total_seconds()

        span_record = {
            "span_id": self.span_id,
            "trace_id": self.trace_id or self.span_id,
            "parent_span_id": self.parent_span_id,
            "task_id": self.task_id,
            "task_type": self.task_type,
            "status": status,
            "message": message,
            "started_at": self.started_at.isoformat(),
            "completed_at": completed_at.isoformat(),
            "duration_seconds": duration,
            "metrics": metrics or {},
            "events": self._events,
            "extra": extra or {},
        }

        # MVP: 只记录日志
        logger.info(
            f"Span completed: {self.task_type} [{status}] "
            f"duration={duration:.2f}s"
        )
        logger.debug(f"Span details: {json.dumps(span_record, default=str)}")

        return span_record

    def fail(
        self,
        error: Exception,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        记录失败

        Args:
            error: 异常对象
            extra: 额外数据

        Returns:
            完整的 Span 记录
        """
        import traceback

        error_details = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "traceback": traceback.format_exc(),
        }

        return self.complete(
            status="failed",
            message=f"{type(error).__name__}: {error}",
            extra={**(extra or {}), "error_details": error_details},
        )
```

---

### 4. LangGraph Runner（v2 修正版）

#### `lee_runtime/executor/langgraph_runner.py`

```python
"""
LEE Executor - LangGraph Runner（MVP v2 版本）

基于 LangGraph 的统一执行入口（仅同步版本）。

v2 修正:
- 使用完整的 SpanBuilder
- 初始状态添加 metrics 和 tokens_used
"""

from typing import Dict, Any
from datetime import datetime

from .types import (
    ExecutorTaskSpec,
    ExecutionResult,
    TaskStatus,
)
from .registry import get_graph_builder
from .tracing.span_builder import SpanBuilder


def run_task(task: ExecutorTaskSpec) -> ExecutionResult:
    """
    执行 Executor 任务（统一入口，同步版本）

    这是 Orchestrator 调用的唯一入口点。

    Args:
        task: 任务规格

    Returns:
        执行结果
    """
    started_at = datetime.now()

    # 创建 Span Builder（用于追踪）
    span_builder = SpanBuilder(
        task_id=task.task_id,
        task_type=task.task_type,
        trace_id=task.trace_id,
        parent_span_id=task.parent_span_id,
    )
    span_builder.add_event("task_started", {"task_type": task.task_type})

    try:
        # 获取 Graph Builder
        builder = get_graph_builder(task.task_type)
        if builder is None:
            span_builder.add_event("builder_not_found", {"task_type": task.task_type})
            result = ExecutionResult(
                task_id=task.task_id,
                status=TaskStatus.FAILED,
                message=f"Unknown task_type: {task.task_type}",
                started_at=started_at,
                completed_at=datetime.now(),
            )
            span_builder.complete(
                status=TaskStatus.FAILED.value,
                message=result.message,
            )
            return result

        span_builder.add_event("graph_building")

        # 构建 LangGraph
        graph = builder(task)

        # 准备初始状态（v2: 添加 metrics 和 tokens_used）
        initial_state: Dict[str, Any] = {
            "task": task,
            "logs": [f"Starting task: {task.task_id} (type: {task.task_type})"],
            "errors": [],
            "current_step": "start",
            "retry_count": 0,
            "started_at": started_at,
            "metrics": {},          # v2 新增
            "tokens_used": 0,       # v2 新增
            "should_stop": False,   # v2 新增
        }

        span_builder.add_event("graph_invoking")

        # 执行 Graph
        final_state = graph.invoke(initial_state)

        span_builder.add_event("graph_completed", {
            "has_errors": len(final_state.get("errors", [])) > 0,
        })

        # 提取执行结果
        exec_result: ExecutionResult = final_state.get("exec_result")
        if exec_result is None:
            # Graph 没有返回 exec_result，构造一个默认的
            has_errors = len(final_state.get("errors", [])) > 0
            exec_result = ExecutionResult(
                task_id=task.task_id,
                status=TaskStatus.FAILED if has_errors else TaskStatus.SUCCESS,
                message="Task completed with errors" if has_errors else "Task completed",
                logs=final_state.get("logs", []),
                error_details="\n".join(final_state.get("errors", [])) if has_errors else None,
                metrics=final_state.get("metrics", {}),
                tokens_used=final_state.get("tokens_used", 0),
                started_at=started_at,
                completed_at=datetime.now(),
            )

        # 更新时间戳
        exec_result.started_at = started_at
        if exec_result.completed_at is None:
            exec_result.completed_at = datetime.now()

        # 计算持续时间
        exec_result.duration_seconds = (
            exec_result.completed_at - exec_result.started_at
        ).total_seconds()

        # 记录 Span
        span_builder.complete(
            status=exec_result.status.value,
            message=exec_result.message,
            metrics={
                **exec_result.metrics,
                "tokens_used": exec_result.tokens_used,
                "duration_seconds": exec_result.duration_seconds,
            },
        )

        return exec_result

    except Exception as e:
        # 记录异常
        import traceback
        error_details = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"

        span_builder.fail(e)

        return ExecutionResult(
            task_id=task.task_id,
            status=TaskStatus.FAILED,
            message=f"Executor exception: {e}",
            logs=[error_details],
            error_details=error_details,
            started_at=started_at,
            completed_at=datetime.now(),
        )
```

---

### 5. 公共条件边和辅助函数（新增）

#### `lee_runtime/executor/graphs/common.py`

```python
"""
Graph 公共组件

提供通用的条件边函数和辅助函数。
"""

from typing import Any, Dict, Literal


def should_continue(state: Dict[str, Any]) -> Literal["continue", "stop"]:
    """
    通用条件边：判断是否应该继续执行

    检查条件（任一满足则停止）：
    1. errors 列表非空
    2. should_stop 标志为 True

    Args:
        state: 当前状态

    Returns:
        "continue" 继续执行下一个节点
        "stop" 跳转到 build_result 节点
    """
    # 检查是否有错误
    if state.get("errors"):
        return "stop"

    # 检查 should_stop 标志
    if state.get("should_stop", False):
        return "stop"

    return "continue"


def add_log(state: Dict[str, Any], message: str) -> list[str]:
    """
    添加日志（返回新的日志列表）

    Args:
        state: 当前状态
        message: 日志消息

    Returns:
        新的日志列表
    """
    logs = state.get("logs", []).copy()
    logs.append(message)
    return logs


def add_error(state: Dict[str, Any], error: str) -> list[str]:
    """
    添加错误（返回新的错误列表）

    Args:
        state: 当前状态
        error: 错误消息

    Returns:
        新的错误列表
    """
    errors = state.get("errors", []).copy()
    errors.append(error)
    return errors


def update_metrics(
    state: Dict[str, Any],
    updates: Dict[str, Any],
) -> Dict[str, Any]:
    """
    更新指标（返回新的指标字典）

    Args:
        state: 当前状态
        updates: 指标更新

    Returns:
        新的指标字典
    """
    metrics = state.get("metrics", {}).copy()
    metrics.update(updates)
    return metrics
```

---

### 6. 安全边界工具

#### `lee_runtime/executor/tools/security.py`

```python
"""
安全边界工具

提供文件路径安全验证，防止路径穿越攻击。
"""

import os
import pathlib
from typing import List, Optional, Tuple


def safe_join(root: str, rel_path: str) -> Optional[str]:
    """
    安全地拼接路径，防止路径穿越攻击

    Args:
        root: 根目录（绝对路径）
        rel_path: 相对路径

    Returns:
        拼接后的绝对路径，如果路径穿越则返回 None

    Example:
        >>> safe_join("/workspace", "src/main.py")
        '/workspace/src/main.py'
        >>> safe_join("/workspace", "../../../etc/passwd")
        None
    """
    try:
        root_path = pathlib.Path(root).resolve()
        joined_path = (root_path / rel_path).resolve()

        # 检查结果路径是否在 root 之下
        if str(joined_path).startswith(str(root_path)):
            return str(joined_path)
        else:
            return None
    except (ValueError, OSError):
        # 路径解析失败
        return None


def validate_path_allowed(
    path: str,
    workspace_root: str,
    allowed_patterns: List[str],
) -> bool:
    """
    验证路径是否在允许的范围内

    Args:
        path: 待验证的路径
        workspace_root: 工作区根目录
        allowed_patterns: 允许的路径模式列表（支持通配符）

    Returns:
        是否允许
    """
    from fnmatch import fnmatch

    # 首先检查是否在工作区内
    safe_path = safe_join(workspace_root, path)
    if safe_path is None:
        return False

    # 计算相对于工作区的路径
    rel_path = os.path.relpath(safe_path, workspace_root)

    # 检查是否匹配允许的模式
    for pattern in allowed_patterns:
        if fnmatch(rel_path, pattern):
            return True

    return False


def validate_write_operation(
    abs_path: str,
    workspace_root: str,
    allowed_patterns: List[str],
) -> Tuple[bool, Optional[str]]:
    """
    验证写入操作是否安全

    Args:
        abs_path: 绝对路径
        workspace_root: 工作区根目录
        allowed_patterns: 允许的路径模式列表

    Returns:
        (是否允许, 错误信息)
    """
    # 检查是否在工作区内
    root_path = pathlib.Path(workspace_root).resolve()
    path_obj = pathlib.Path(abs_path).resolve()

    if not str(path_obj).startswith(str(root_path)):
        return False, f"Path outside workspace: {abs_path}"

    # 计算相对路径
    try:
        rel_path = path_obj.relative_to(root_path)
    except ValueError:
        return False, f"Cannot compute relative path: {abs_path}"

    # 如果没有模式限制，只检查是否在工作区内
    if not allowed_patterns:
        return True, None

    # 检查是否匹配允许的模式
    from fnmatch import fnmatch
    rel_path_str = str(rel_path).replace("\\", "/")

    for pattern in allowed_patterns:
        if fnmatch(rel_path_str, pattern):
            return True, None

    return False, f"Path not in allowed patterns: {rel_path_str}"
```

---

### 7. 文件系统工具

#### `lee_runtime/executor/tools/fs_tools.py`

```python
"""
文件系统工具（MVP 版本，集成安全边界）
"""

import pathlib
import hashlib
from typing import Optional

from .security import validate_write_operation


def read_file(path: str, encoding: str = "utf-8") -> str:
    """
    读取文件内容

    Args:
        path: 文件路径
        encoding: 文件编码

    Returns:
        文件内容

    Raises:
        FileNotFoundError: 文件不存在
        IOError: 读取失败
    """
    p = pathlib.Path(path)
    return p.read_text(encoding=encoding)


def write_file(
    path: str,
    content: str,
    encoding: str = "utf-8",
    create_parents: bool = True,
    # 安全边界参数
    workspace_root: Optional[str] = None,
    allowed_patterns: Optional[list[str]] = None,
) -> None:
    """
    写入文件内容（带安全边界检查）

    Args:
        path: 文件路径
        content: 文件内容
        encoding: 文件编码
        create_parents: 是否自动创建父目录
        workspace_root: 工作区根目录（用于安全检查）
        allowed_patterns: 允许写入的路径模式

    Raises:
        ValueError: 路径穿越或不在允许范围内
        IOError: 写入失败
    """
    # 如果提供了安全边界参数，进行验证
    if workspace_root is not None:
        allowed = allowed_patterns or []
        is_safe, error_msg = validate_write_operation(
            path, workspace_root, allowed
        )
        if not is_safe:
            raise ValueError(f"Security violation: {error_msg}")

    p = pathlib.Path(path)
    if create_parents:
        p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding=encoding)


def compute_hash(path: str, algorithm: str = "sha256") -> str:
    """
    计算文件哈希

    Args:
        path: 文件路径
        algorithm: 哈希算法（sha256, md5）

    Returns:
        哈希值（十六进制字符串）
    """
    p = pathlib.Path(path)
    content = p.read_bytes()

    if algorithm == "sha256":
        return hashlib.sha256(content).hexdigest()
    elif algorithm == "md5":
        return hashlib.md5(content).hexdigest()
    else:
        raise ValueError(f"Unsupported hash algorithm: {algorithm}")


def file_exists(path: str) -> bool:
    """检查文件是否存在"""
    return pathlib.Path(path).exists()


def get_file_size(path: str) -> int:
    """获取文件大小（字节）"""
    return pathlib.Path(path).stat().st_size
```

---

### 8. Shell 工具

#### `lee_runtime/executor/tools/shell_tools.py`

```python
"""
Shell 命令工具（MVP 版本）

提供安全的命令执行功能。
"""

import subprocess
import time
import os
from dataclasses import dataclass
from typing import List, Optional, Dict


@dataclass
class ShellResult:
    """Shell 命令执行结果"""
    exit_code: int
    stdout: str
    stderr: str
    command: str
    duration_seconds: float = 0.0


def run_shell(
    command: str,
    cwd: Optional[str] = None,
    timeout: int = 600,
    env: Optional[Dict[str, str]] = None,
    shell: bool = True,
) -> ShellResult:
    """
    执行 Shell 命令

    Args:
        command: 命令字符串
        cwd: 工作目录
        timeout: 超时时间（秒）
        env: 环境变量（会与系统环境变量合并）
        shell: 是否使用 shell

    Returns:
        执行结果
    """
    start_time = time.time()

    # 合并环境变量
    process_env = os.environ.copy()
    if env is not None:
        process_env.update(env)

    try:
        proc = subprocess.Popen(
            command,
            cwd=cwd,
            shell=shell,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=process_env,
        )

        stdout, stderr = proc.communicate(timeout=timeout)
        exit_code = proc.returncode
        duration = time.time() - start_time

        return ShellResult(
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            command=command,
            duration_seconds=duration,
        )

    except subprocess.TimeoutExpired:
        proc.kill()
        stdout, stderr = proc.communicate()
        return ShellResult(
            exit_code=124,  # 124 是 timeout 的标准 exit code
            stdout=stdout or "",
            stderr=stderr or "",
            command=command,
            duration_seconds=time.time() - start_time,
        )


def run_pytest(
    test_path: str = ".",
    args: Optional[List[str]] = None,
    cwd: Optional[str] = None,
    timeout: int = 600,
) -> ShellResult:
    """
    执行 pytest

    Args:
        test_path: 测试目录
        args: 额外的 pytest 参数
        cwd: 工作目录
        timeout: 超时

    Returns:
        执行结果
    """
    cmd_parts = ["python", "-m", "pytest"]
    if args:
        cmd_parts.extend(args)
    else:
        cmd_parts.append(test_path)

    cmd_str = " ".join(cmd_parts)
    return run_shell(cmd_str, cwd=cwd, timeout=timeout, shell=True)
```

---

### 9. LLM 工具

#### `lee_runtime/executor/tools/llm_tools.py`

```python
"""
LLM 调用工具（MVP 版本，仅 Anthropic）

统一的 LLM 调用接口，MVP 阶段只支持 Anthropic。
"""

from typing import List, Dict, Optional
from dataclasses import dataclass
import time

from ..profiles.loader import load_profile, get_client


@dataclass
class LLMResponse:
    """LLM 响应"""
    content: str
    model: str
    profile: str
    tokens_used: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    duration_seconds: float = 0.0
    raw_response: Optional[Dict] = None


def call_llm(
    profile: str,
    messages: List[Dict[str, str]],
    system: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> LLMResponse:
    """
    调用 LLM（MVP 版本，仅支持 Anthropic）

    Args:
        profile: LLM Profile 名称
        messages: 消息列表（格式: [{"role": "user", "content": "..."}]）
        system: 系统提示（可选，Anthropic 格式）
        temperature: 温度（覆盖 profile）
        max_tokens: 最大 token（覆盖 profile）

    Returns:
        LLM 响应

    Raises:
        ValueError: Profile 不存在或不支持的 provider
        Exception: LLM 调用失败
    """
    start_time = time.time()

    # 加载 Profile
    profile_config = load_profile(profile)

    # MVP 阶段只支持 Anthropic
    if profile_config.provider != "anthropic":
        raise ValueError(
            f"MVP version only supports Anthropic, got: {profile_config.provider}"
        )

    # 获取 Client
    client = get_client(profile_config)

    # 准备参数（Anthropic Messages API 格式）
    # 过滤 system 消息，Anthropic 使用独立的 system 参数
    filtered_messages = []
    extracted_system = system
    for msg in messages:
        if msg.get("role") == "system":
            if extracted_system is None:
                extracted_system = msg.get("content", "")
        else:
            filtered_messages.append(msg)

    params = {
        "model": profile_config.model,
        "messages": filtered_messages,
        "max_tokens": max_tokens or profile_config.max_tokens or 4096,
    }

    if extracted_system:
        params["system"] = extracted_system

    if temperature is not None:
        params["temperature"] = temperature
    elif profile_config.temperature is not None:
        params["temperature"] = profile_config.temperature

    # 调用 Anthropic Messages API
    response = client.messages.create(**params)

    # 解析响应
    input_tokens = 0
    output_tokens = 0
    if hasattr(response, "usage"):
        usage = response.usage
        input_tokens = getattr(usage, "input_tokens", 0)
        output_tokens = getattr(usage, "output_tokens", 0)

    # Anthropic 响应格式：response.content[0].text
    content = ""
    if hasattr(response, "content") and len(response.content) > 0:
        content = response.content[0].text

    duration = time.time() - start_time

    return LLMResponse(
        content=content,
        model=profile_config.model,
        profile=profile,
        tokens_used=input_tokens + output_tokens,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        duration_seconds=duration,
        raw_response=response.model_dump() if hasattr(response, "model_dump") else None,
    )
```

---

## 📊 Graph 实现（v2 修正版）

### 1. `impl_coding.py` Graph

#### `lee_runtime/executor/graphs/impl_coding.py`

```python
"""
实现类任务 Graph (l3.impl.coding)

MVP v2 版本：
- 函数式风格，返回新 state
- 使用条件边实现错误快速失败
- 集成安全边界检查
"""

from typing import Dict, Any
from datetime import datetime
from pathlib import Path
from langgraph.graph import StateGraph, END

from ..types import (
    ExecutorTaskSpec,
    ExecutionResult,
    TaskStatus,
    ImplCodingState,
)
from ..tools import fs_tools, llm_tools
from ..tools.security import safe_join
from .common import should_continue, add_log, add_error, update_metrics


def build_impl_coding_graph(task: ExecutorTaskSpec) -> Any:
    """
    构建实现类任务 LangGraph

    Args:
        task: 任务规格

    Returns:
        编译后的 LangGraph
    """
    graph = StateGraph(ImplCodingState)

    # ============================================
    # 节点定义（v2: 函数式风格）
    # ============================================

    def load_inputs(state: ImplCodingState) -> ImplCodingState:
        """加载输入文件"""
        t = state["task"]
        logs = add_log(state, "[load_inputs] Loading inputs...")
        errors = state.get("errors", []).copy()
        metrics = state.get("metrics", {}).copy()

        prd = ""
        design = ""
        contract = ""

        # 加载 PRD
        if "frozen_prd" in t.inputs:
            try:
                prd = fs_tools.read_file(t.inputs["frozen_prd"])
                logs = [*logs, f"  Loaded PRD from {t.inputs['frozen_prd']}"]
            except Exception as e:
                logs = [*logs, f"  Failed to load PRD: {e}"]
                errors = [*errors, f"Failed to load PRD: {e}"]

        # 加载设计文档
        if "design_spec" in t.inputs:
            try:
                design = fs_tools.read_file(t.inputs["design_spec"])
                logs = [*logs, f"  Loaded design from {t.inputs['design_spec']}"]
            except Exception as e:
                logs = [*logs, f"  Failed to load design: {e}"]
                errors = [*errors, f"Failed to load design: {e}"]

        # 加载实现契约
        if "impl_contract" in t.inputs:
            try:
                contract = fs_tools.read_file(t.inputs["impl_contract"])
                logs = [*logs, f"  Loaded contract from {t.inputs['impl_contract']}"]
            except Exception as e:
                logs = [*logs, f"  Failed to load contract: {e}"]
                errors = [*errors, f"Failed to load contract: {e}"]

        metrics["inputs_loaded"] = sum([1 for x in [prd, design, contract] if x])

        # 返回新 state
        return {
            **state,
            "logs": logs,
            "errors": errors,
            "metrics": metrics,
            "prd": prd,
            "design": design,
            "contract": contract,
            "current_step": "load_inputs",
        }

    def llm_impl(state: ImplCodingState) -> ImplCodingState:
        """调用 LLM 生成实现"""
        t = state["task"]
        logs = add_log(state, "[llm_impl] Calling LLM for implementation...")
        errors = state.get("errors", []).copy()
        metrics = state.get("metrics", {}).copy()
        tokens_used = state.get("tokens_used", 0)

        system_prompt = (
            "你是一个严格遵守约束的资深工程师。\n"
            "请根据 PRD、设计和实现契约，生成完整的实现代码。\n\n"
            "输出格式要求：\n"
            "===FILE:path/to/file.ext===\n"
            "<file content>\n"
            "===END===\n\n"
            "只输出代码，不要包含其他解释。"
        )

        user_prompt = f"""
[PRD]
{state.get('prd', '(No PRD)')}

[DESIGN]
{state.get('design', '(No Design)')}

[IMPLEMENTATION CONTRACT]
{state.get('contract', '(No Contract)')}
"""

        code_changes = {}
        impl_plan = ""

        try:
            response = llm_tools.call_llm(
                profile=t.llm_profile or "default",
                messages=[{"role": "user", "content": user_prompt}],
                system=system_prompt,
                temperature=t.llm_temperature,
                max_tokens=t.llm_max_tokens,
            )

            tokens_used += response.tokens_used

            # 解析 FILE 标记
            current_path = None
            current_lines = []

            for line in response.content.splitlines():
                if line.startswith("===FILE:") and line.endswith("==="):
                    if current_path is not None:
                        code_changes[current_path] = "\n".join(current_lines).strip()
                    current_path = line[len("===FILE:"):-len("===")].strip()
                    current_lines = []
                elif line.startswith("===END==="):
                    if current_path is not None:
                        code_changes[current_path] = "\n".join(current_lines).strip()
                        current_path = None
                        current_lines = []
                elif current_path is not None:
                    current_lines.append(line)

            # 处理最后一个文件（如果没有 ===END===）
            if current_path is not None:
                code_changes[current_path] = "\n".join(current_lines).strip()

            impl_plan = response.content[:500] + "..." if len(response.content) > 500 else response.content
            logs = [*logs, f"  Generated {len(code_changes)} file(s)"]
            logs = [*logs, f"  Tokens used: {response.tokens_used}"]

            metrics["llm_tokens"] = response.tokens_used
            metrics["llm_duration"] = response.duration_seconds
            metrics["files_generated"] = len(code_changes)

        except Exception as e:
            logs = [*logs, f"  LLM call failed: {e}"]
            errors = [*errors, f"LLM call failed: {e}"]

        return {
            **state,
            "logs": logs,
            "errors": errors,
            "metrics": metrics,
            "tokens_used": tokens_used,
            "code_changes": code_changes,
            "impl_plan": impl_plan,
            "current_step": "llm_impl",
        }

    def apply_changes(state: ImplCodingState) -> ImplCodingState:
        """应用代码变更（带安全边界）"""
        t = state["task"]
        logs = add_log(state, "[apply_changes] Applying code changes...")
        errors = state.get("errors", []).copy()
        metrics = state.get("metrics", {}).copy()

        repo_root = t.inputs.get("repo_workspace", ".")
        workspace_root = t.workspace_root or repo_root
        allowed_patterns = t.allowed_write_patterns or []

        files_written = 0

        for rel_path, content in state.get("code_changes", {}).items():
            try:
                # 使用安全路径拼接
                abs_path = safe_join(repo_root, rel_path)
                if abs_path is None:
                    logs = [*logs, f"  Security: Path traversal attempt: {rel_path}"]
                    errors = [*errors, f"Path traversal: {rel_path}"]
                    continue

                # 写入文件（带安全检查）
                fs_tools.write_file(
                    abs_path,
                    content,
                    workspace_root=workspace_root,
                    allowed_patterns=allowed_patterns if allowed_patterns else None,
                )
                logs = [*logs, f"  Written: {abs_path}"]
                files_written += 1

            except Exception as e:
                logs = [*logs, f"  Failed to write {rel_path}: {e}"]
                errors = [*errors, f"Failed to write {rel_path}: {e}"]

        metrics["files_written"] = files_written

        return {
            **state,
            "logs": logs,
            "errors": errors,
            "metrics": metrics,
            "current_step": "apply_changes",
        }

    def build_result(state: ImplCodingState) -> ImplCodingState:
        """构建执行结果"""
        t = state["task"]
        logs = add_log(state, "[build_result] Building execution result...")

        # 收集 artifacts
        artifacts = {}
        for logical_name, real_path in t.outputs.items():
            if Path(real_path).exists():
                artifacts[logical_name] = real_path

        # 决定最终状态
        errors = state.get("errors", [])
        status = TaskStatus.SUCCESS if not errors else TaskStatus.FAILED
        message = (
            "Implementation completed successfully"
            if not errors
            else f"Implementation failed with {len(errors)} error(s)"
        )

        exec_result = ExecutionResult(
            task_id=t.task_id,
            status=status,
            message=message,
            artifacts=artifacts,
            logs=logs,
            error_details="\n".join(errors) if errors else None,
            metrics={
                **state.get("metrics", {}),
                "error_count": len(errors),
            },
            tokens_used=state.get("tokens_used", 0),
            completed_at=datetime.now(),
        )

        return {
            **state,
            "logs": logs,
            "exec_result": exec_result,
            "current_step": "build_result",
        }

    # ============================================
    # 添加节点
    # ============================================
    graph.add_node("load_inputs", load_inputs)
    graph.add_node("llm_impl", llm_impl)
    graph.add_node("apply_changes", apply_changes)
    graph.add_node("build_result", build_result)

    # ============================================
    # 连接图（v2: 使用条件边）
    # ============================================
    graph.set_entry_point("load_inputs")

    # load_inputs -> (条件) -> llm_impl 或 build_result
    graph.add_conditional_edges(
        "load_inputs",
        should_continue,
        {
            "continue": "llm_impl",
            "stop": "build_result",
        }
    )

    # llm_impl -> (条件) -> apply_changes 或 build_result
    graph.add_conditional_edges(
        "llm_impl",
        should_continue,
        {
            "continue": "apply_changes",
            "stop": "build_result",
        }
    )

    # apply_changes -> build_result
    graph.add_edge("apply_changes", "build_result")

    # build_result -> END
    graph.add_edge("build_result", END)

    return graph.compile()
```

---

### 2. `unit_test.py` Graph

#### `lee_runtime/executor/graphs/unit_test.py`

```python
"""
单元测试任务 Graph (l3.test.unit)

MVP v2 版本：
- 函数式风格，返回新 state
- 使用条件边实现错误快速失败
"""

from typing import Dict, Any
from datetime import datetime
from pathlib import Path
from langgraph.graph import StateGraph, END

from ..types import (
    ExecutorTaskSpec,
    ExecutionResult,
    TaskStatus,
    UnitTestState,
)
from ..tools import shell_tools, fs_tools
from .common import should_continue, add_log, add_error


def build_unit_test_graph(task: ExecutorTaskSpec) -> Any:
    """
    构建单元测试任务 LangGraph

    Args:
        task: 任务规格

    Returns:
        编译后的 LangGraph
    """
    graph = StateGraph(UnitTestState)

    # ============================================
    # 节点定义（v2: 函数式风格）
    # ============================================

    def load_config(state: UnitTestState) -> UnitTestState:
        """加载测试配置"""
        t = state["task"]
        logs = add_log(state, "[load_config] Loading test configuration...")
        errors = state.get("errors", []).copy()

        # 获取测试命令
        test_command = t.params.get("test_command", "pytest -q")
        logs = [*logs, f"  Test command: {test_command}"]

        # 加载测试配置文件（如果有）
        test_config = {}
        if "test_config" in t.inputs:
            try:
                import yaml
                config_path = t.inputs["test_config"]
                with open(config_path) as f:
                    test_config = yaml.safe_load(f) or {}
                logs = [*logs, f"  Loaded config from {config_path}"]
            except Exception as e:
                logs = [*logs, f"  Failed to load config: {e}"]
                # 配置加载失败不是致命错误

        return {
            **state,
            "logs": logs,
            "errors": errors,
            "test_command": test_command,
            "test_config": test_config,
            "current_step": "load_config",
        }

    def run_tests(state: UnitTestState) -> UnitTestState:
        """执行测试"""
        t = state["task"]
        logs = add_log(state, "[run_tests] Running tests...")
        errors = state.get("errors", []).copy()
        metrics = state.get("metrics", {}).copy()

        cwd = t.inputs.get("repo_workspace", ".")
        test_command = state["test_command"]

        test_results = {}

        try:
            result = shell_tools.run_shell(
                test_command,
                cwd=cwd,
                timeout=t.timeout_seconds,
            )

            test_results = {
                "exit_code": result.exit_code,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "duration": result.duration_seconds,
            }

            logs = [*logs, f"  Exit code: {result.exit_code}"]
            logs = [*logs, f"  Duration: {result.duration_seconds:.2f}s"]

            metrics["test_duration"] = result.duration_seconds
            metrics["test_exit_code"] = result.exit_code

            if result.exit_code == 0:
                logs = [*logs, "  Tests passed!"]
            else:
                logs = [*logs, "  Tests failed!"]
                errors = [*errors, f"Tests failed with exit code {result.exit_code}"]

        except Exception as e:
            logs = [*logs, f"  Test execution failed: {e}"]
            errors = [*errors, f"Test execution failed: {e}"]

        return {
            **state,
            "logs": logs,
            "errors": errors,
            "metrics": metrics,
            "test_results": test_results,
            "current_step": "run_tests",
        }

    def generate_report(state: UnitTestState) -> UnitTestState:
        """生成测试报告"""
        t = state["task"]
        logs = add_log(state, "[generate_report] Generating test report...")
        errors = state.get("errors", []).copy()

        # 生成 Markdown 报告
        test_results = state.get("test_results", {})
        exit_code = test_results.get("exit_code", "N/A")
        duration = test_results.get("duration", 0)
        stdout = test_results.get("stdout", "")
        stderr = test_results.get("stderr", "")

        report = f"""# Test Report

**Exit Code:** {exit_code}
**Duration:** {duration:.2f}s
**Status:** {"PASSED" if exit_code == 0 else "FAILED"}

## Output

```
{stdout}
```
"""

        if stderr:
            report += f"""
## Errors

```
{stderr}
```
"""

        # 写入报告文件
        if "test_report_human" in t.outputs:
            report_path = t.outputs["test_report_human"]
            try:
                fs_tools.write_file(report_path, report)
                logs = [*logs, f"  Written report to {report_path}"]
            except Exception as e:
                logs = [*logs, f"  Failed to write report: {e}"]
                errors = [*errors, f"Failed to write report: {e}"]

        return {
            **state,
            "logs": logs,
            "errors": errors,
            "test_report": report,
            "current_step": "generate_report",
        }

    def build_result(state: UnitTestState) -> UnitTestState:
        """构建执行结果"""
        t = state["task"]
        logs = add_log(state, "[build_result] Building execution result...")

        errors = state.get("errors", [])
        test_results = state.get("test_results", {})

        # 判断状态：测试 exit_code == 0 且无其他错误
        test_passed = test_results.get("exit_code") == 0
        has_other_errors = len([e for e in errors if "Tests failed" not in e]) > 0

        if test_passed and not has_other_errors:
            status = TaskStatus.SUCCESS
            message = "Tests completed successfully"
        else:
            status = TaskStatus.FAILED
            message = "Tests failed" if not test_passed else "Test execution had errors"

        # 收集 artifacts
        artifacts = {}
        for logical_name, real_path in t.outputs.items():
            if Path(real_path).exists():
                artifacts[logical_name] = real_path

        exec_result = ExecutionResult(
            task_id=t.task_id,
            status=status,
            message=message,
            artifacts=artifacts,
            logs=logs,
            error_details="\n".join(errors) if errors else None,
            metrics={
                **state.get("metrics", {}),
                **test_results,
            },
            completed_at=datetime.now(),
        )

        return {
            **state,
            "logs": logs,
            "exec_result": exec_result,
            "current_step": "build_result",
        }

    # ============================================
    # 添加节点
    # ============================================
    graph.add_node("load_config", load_config)
    graph.add_node("run_tests", run_tests)
    graph.add_node("generate_report", generate_report)
    graph.add_node("build_result", build_result)

    # ============================================
    # 连接图（v2: 使用条件边）
    # ============================================
    graph.set_entry_point("load_config")

    # load_config -> run_tests（配置加载失败不中断）
    graph.add_edge("load_config", "run_tests")

    # run_tests -> (条件) -> generate_report 或 build_result
    graph.add_conditional_edges(
        "run_tests",
        should_continue,
        {
            "continue": "generate_report",
            "stop": "build_result",
        }
    )

    # generate_report -> build_result
    graph.add_edge("generate_report", "build_result")

    # build_result -> END
    graph.add_edge("build_result", END)

    return graph.compile()
```

---

## 🔗 与 Orchestrator 集成（v2 修正版）

```python
"""
Orchestrator 集成示例

展示如何在 Orchestrator 中调用新的 LangGraph Executor。
"""

from pathlib import Path
import yaml
from lee_runtime.executor.types import ExecutorTaskSpec, TaskStatus
from lee_runtime.executor.langgraph_runner import run_task


def execute_step_with_executor(
    project_dir: str,
    step_id: str,
    llm_profile: str = "default",
) -> bool:
    """
    使用 Executor 执行步骤

    这是 Orchestrator 调用 Executor 的入口点。

    Args:
        project_dir: 项目目录
        step_id: 步骤 ID
        llm_profile: LLM Profile

    Returns:
        是否成功
    """
    # 1. 加载 workflow.yaml
    workflow_path = Path(project_dir) / "workflow.yaml"
    with open(workflow_path) as f:
        workflow = yaml.safe_load(f)

    # 2. 查找步骤定义
    step = None
    for s in workflow.get("steps", []):
        if s.get("id") == step_id:
            step = s
            break

    if step is None:
        print(f"Error: Step not found: {step_id}")
        return False

    # 3. 从 execution_context 获取 task_type
    exec_ctx = step.get("execution_context", {})
    task_type = exec_ctx.get("task_type")
    if not task_type:
        # 回退到映射逻辑
        task_type = _map_to_task_type(step.get("agent", ""), step.get("skill", ""))

    # 4. 解析 inputs/outputs
    inputs = _resolve_paths(project_dir, exec_ctx.get("inputs", {}))
    outputs = _resolve_paths(project_dir, exec_ctx.get("outputs", {}))

    # 5. 解析安全边界配置
    workspace_root = exec_ctx.get("workspace_root")
    if workspace_root:
        workspace_root = _resolve_path(project_dir, workspace_root)
    else:
        workspace_root = project_dir

    allowed_write_patterns = exec_ctx.get("allowed_write_patterns", [])

    # 6. 构造 ExecutorTaskSpec
    task = ExecutorTaskSpec(
        task_id=step_id,
        task_type=task_type,
        inputs=inputs,
        outputs=outputs,
        llm_profile=llm_profile,
        llm_temperature=exec_ctx.get("params", {}).get("llm_temperature"),
        llm_max_tokens=exec_ctx.get("params", {}).get("llm_max_tokens"),
        params=exec_ctx.get("params", {}),
        timeout_seconds=exec_ctx.get("timeout_seconds", 3600),
        workspace_root=workspace_root,
        allowed_write_patterns=allowed_write_patterns,
    )

    # 7. 调用 Executor
    print(f"Executing step: {step_id} (task_type: {task_type})")
    result = run_task(task)

    # 8. 处理结果
    if result.status == TaskStatus.SUCCESS:
        print(f"✅ Step {step_id} completed: {result.message}")
        print(f"   Duration: {result.duration_seconds:.2f}s")
        if result.tokens_used > 0:
            print(f"   Tokens used: {result.tokens_used}")
        for artifact_name, artifact_path in result.artifacts.items():
            print(f"   📄 {artifact_name}: {artifact_path}")
    else:
        print(f"❌ Step {step_id} failed: {result.message}")
        if result.error_details:
            print(f"   Error: {result.error_details[:200]}...")

    return result.status == TaskStatus.SUCCESS


def _map_to_task_type(agent: str, skill: str) -> str:
    """将 agent/skill 映射到 task_type（回退逻辑）"""
    mapping = {
        ("implementation_executor", "impl"): "l3.impl.coding",
        ("tech_lead", "coding"): "l3.impl.coding",
        ("test_engineer", "test"): "l3.test.unit",
        ("qa_engineer", "test"): "l3.test.unit",
    }

    if agent and skill:
        key = (agent, skill)
        if key in mapping:
            return mapping[key]

    if skill:
        skill_lower = skill.lower()
        if "impl" in skill_lower or "coding" in skill_lower:
            return "l3.impl.coding"
        elif "test" in skill_lower or "unit" in skill_lower:
            return "l3.test.unit"

    return "l3.impl.coding"


def _resolve_path(project_dir: str, path_spec: str) -> str:
    """解析单个路径"""
    if path_spec.startswith("@output"):
        return str(Path(project_dir) / "output" / path_spec[8:].lstrip("/"))
    elif path_spec.startswith("@openspec"):
        return str(Path(project_dir) / ".openspec" / path_spec[10:].lstrip("/"))
    elif Path(path_spec).is_absolute():
        return path_spec
    else:
        return str(Path(project_dir) / path_spec)


def _resolve_paths(project_dir: str, paths_config: dict) -> dict:
    """解析路径配置"""
    return {
        name: _resolve_path(project_dir, spec)
        for name, spec in paths_config.items()
    }
```

---

## 📋 MVP 实现路线图（保持不变）

### Phase A：打通最小链路（无 LLM / 单一 graph）

**目标：** 验证 Orchestrator → Executor → Tools 调用链路能跑通

- [ ] 实现核心类型 (`types.py`)
- [ ] 实现 LangGraph Runner (`langgraph_runner.py`)
- [ ] 实现注册表 (`registry.py`)
- [ ] 实现工具层最小集
- [ ] 实现 `unit_test.py` Graph
- [ ] 在 Orchestrator 中集成
- [ ] 测试：从 CLI 把单元测试执行跑通

### Phase B：接入 LLM + 实现 `l3.impl.coding`

**目标：** 验证 LLM 调用和代码生成流程

- [ ] 实现 `llm_tools.py`
- [ ] 实现 Profile 加载器 (`profiles/loader.py`)
- [ ] 实现 `impl_coding.py` Graph
- [ ] 测试：验证 PRD + Design → LLM → 写文件 → ExecutionResult

### Phase C：完善文件路径安全

**目标：** 确保所有文件操作都有安全边界

- [ ] 在所有 Graph 中使用安全路径拼接
- [ ] 添加安全边界测试（路径穿越攻击场景）

---

## 📝 审查清单（MVP v2）

### 设计阶段（已完成）

- [x] 层级命名澄清与 v3.1 的关系
- [x] BaseState 补全 metrics、tokens_used、should_stop 字段
- [x] 补充 registry.py 实现
- [x] 补充 profiles/loader.py 实现
- [x] 补充 SpanBuilder 实现
- [x] Graph 节点改为函数式风格
- [x] 添加条件边实现错误快速失败
- [x] 说明与现有 v3.1 Executor 的迁移策略

### Phase A 检查点

- [ ] 类型定义正确（ExecutorTaskSpec, ExecutionResult, BaseState）
- [ ] Runner 能正确调用 Graph Builder
- [ ] unit_test Graph 能执行 pytest 并生成报告
- [ ] Orchestrator 能成功调用 Executor
- [ ] 条件边正确处理错误场景

### Phase B 检查点

- [ ] llm_tools 能调用 Anthropic API
- [ ] Profile 加载器正确获取 API Key
- [ ] impl_coding Graph 能生成代码并写入文件
- [ ] 生成的代码文件路径在安全边界内

### Phase C 检查点

- [ ] 所有文件操作都有安全边界检查
- [ ] 路径穿越攻击被正确拦截
- [ ] workspace_root 和 allowed_write_patterns 正确生效

---

## 🔗 相关文档

- [04-executor-langgraph-architecture.md](./04-executor-langgraph-architecture.md) - 完整版设计
- [04-executor-langgraph-architecture-mvp.md](./04-executor-langgraph-architecture-mvp.md) - MVP v1 版本
- [LEE_Orchestrator_v3_Architecture.md](./architecture/LEE_Orchestrator_v3_Architecture.md) - v3.1 总体架构

---

**文档版本**: v3.1-MVP-v2
**最后更新**: 2026-01-29
**维护者**: LEE Team
**状态**: 架构评审通过
