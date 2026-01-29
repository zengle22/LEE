# LEE Executor (基于 LangGraph) 架构设计

> **版本:** v3.1-design
> **状态:** 设计评审
> **创建日期:** 2026-01-29
> **作者:** LEE Team

---

## 📋 文档概述

本文档定义了基于 LangGraph 的 LEE Executor 架构设计。Executor 是 LEE Orchestrator 的执行层（L3），负责根据 Orchestrator（L2）下发的任务规格，选择合适的 LangGraph 流程模板并执行任务。

### 设计目标

1. **解耦关注点**：Orchestrator 专注于流程编排，Executor 专注于任务执行
2. **可扩展性**：通过注册表机制，轻松添加新的 task_type 和对应的流程模板
3. **可观测性**：基于 Execution Trace 契约，记录完整的执行日志
4. **可测试性**：每个 Graph 模板可以独立测试

---

## 🎯 核心概念

### 三层架构

```
┌─────────────────────────────────────────────────────────────────┐
│  L2: Orchestrator (编排层)                                        │
│  - 读取 workflow.yaml                                            │
│  - 解析步骤依赖                                                   │
│  - 选择 task_type                                                │
│  - 调用 Executor.run_task(task_spec)                            │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│  L3: Executor (执行层) - 本文档设计重点                             │
│  - 接收 ExecutorTaskSpec                                            │
│  - 根据 task_type 选择 Graph Builder                                 │
│  - 构建 LangGraph 流程                                              │
│  - 执行并返回 ExecutionResult                                    │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│  L4: Tools (工具层)                                                │
│  - fs_tools: 文件读写                                              │
│  - shell_tools: 命令执行                                           │
│  - llm_tools: LLM 调用                                            │
│  - validator_tools: 验证器                                          │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 📁 目录结构

```
lee_runtime/
  executor/
    __init__.py                       # Executor 模块导出
    types.py                           # 核心数据类型
    registry.py                        # task_type -> Graph Builder 注册表
    langgraph_runner.py                # 核心入口：run_task 函数
    tools/
      __init__.py
      fs_tools.py                     # 文件系统工具
      shell_tools.py                  # Shell 命令工具
      llm_tools.py                    # LLM 调用工具
      validator_tools.py              # 验证器工具
    graphs/
      __init__.py
      base.py                           # Graph 基类和工具函数
      impl_coding.py                   # l3.impl.coding 实现 Graph
      unit_test.py                     # l3.test.unit 测试 Graph
      code_review.py                    # l3.review.code 代码审查 Graph
      acceptance_check.py               # l3.acceptance 验收 Graph
      # 未来可扩展：
      # ui_design.py
      # bug_fix.py
    tracing/
      __init__.py
      span_builder.py                  # Span 构建器（对接 Execution Trace）
    profiles/                           # LLM Profile 配置
      __init__.py
      loader.py                        # Profile 加载器
    tests/
      __init__.py
      test_graphs.py                   # Graph 单元测试
      test_integration.py              # 集成测试
```

---

## 📦 核心类型定义

### `lee_runtime/executor/types.py`

```python
"""
LEE Executor 核心类型定义

定义 Orchestrator -> Executor 之间的统一数据契约。
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Union
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


class TaskBackend(str, Enum):
    """执行后端"""
    LANGGRAPH = "langgraph"
    # 未来可扩展：
    # CELERY = "celery"
    # ARGO = "argo"
    # PREFECT = "prefect"


@dataclass
class ExecutorTaskSpec:
    """
    Executor 任务规格

    Orchestrator 填写此规格并传递给 Executor.run_task()
    """
    # 基础标识
    task_id: str                           # 任务唯一标识
    task_type: str                         # 任务类型，映射到 Graph Builder
    backend: TaskBackend = TaskBackend.LANGGRAPH  # 执行后端

    # 输入输出映射（逻辑名 -> 真实路径）
    inputs: Dict[str, str] = field(default_factory=dict)
    outputs: Dict[str, str] = field(default_factory=dict)

    # 执行参数
    params: Dict[str, Any] = field(default_factory=dict)

    # LLM 配置
    llm_profile: Optional[str] = None         # LLM Profile 名称
    llm_temperature: Optional[float] = None    # LLM 温度
    llm_max_tokens: Optional[int] = None       # LLM 最大 token

    # 约束配置
    timeout_seconds: int = 3600              # 超时时间
    max_retries: int = 3                     # 最大重试次数

    # 上下文信息
    context: Dict[str, Any] = field(default_factory=dict)

    # 追踪信息
    trace_id: Optional[str] = None             # 关联 Execution Trace
    parent_span_id: Optional[str] = None       # 父 Span ID


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

    # 时间戳
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # 自由扩展字段
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolCallResult:
    """工具调用结果"""
    tool_name: str
    success: bool
    output: Any
    error: Optional[str] = None
    duration_seconds: float = 0.0


@dataclass
class LLMCallResult:
    """LLM 调用结果"""
    profile: str
    model: str
    success: bool
    response: str
    tokens_used: int = 0
    cost_usd: float = 0.0
    duration_seconds: float = 0.0
    error: Optional[str] = None


# ============================================
# 扩展类型：Graph 状态
# ============================================

class GraphState(Dict):
    """
    LangGraph State 的基础类型

    所有 Graph 的 State 都应该继承这些基础字段。
    """
    task: ExecutorTaskSpec               # 任务规格（入参）
    logs: List[str]                        # 执行日志
    errors: List[str]                      # 错误日志
    current_step: str                       # 当前步骤名
    retry_count: int = 0                    # 重试次数
    started_at: str                          # 开始时间
    completed_at: Optional[str] = None        # 完成时间


@dataclass
class GraphConfig:
    """
    Graph 配置项

    定义 Graph 的全局配置，如超时、重试策略等。
    """
    timeout_seconds: int = 3600
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    enable_tracing: bool = True
    enable_logging: bool = True
```

---

## 🏗️ 架构组件

### 1. 统一入口：LangGraph Runner

#### `lee_runtime/executor/langgraph_runner.py`

```python
"""
LEE Executor - LangGraph Runner

基于 LangGraph 的统一执行入口。

核心职责：
1. 接收 ExecutorTaskSpec
2. 根据 task_type 获取对应的 Graph Builder
3. 构建 LangGraph 流程
4. 执行并返回 ExecutionResult
"""

from typing import Optional, Dict, Any, Callable
from datetime import datetime

from .types import (
    ExecutorTaskSpec,
    ExecutionResult,
    TaskStatus,
    TaskBackend,
    GraphState,
)
from .registry import get_graph_builder, get_validator
from .tracing.span_builder import SpanBuilder


def run_task(task: ExecutorTaskSpec) -> ExecutionResult:
    """
    执行 Executor 任务（统一入口）

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
    )

    try:
        # 获取 Graph Builder
        builder = get_graph_builder(task.task_type)
        if builder is None:
            return ExecutionResult(
                task_id=task.task_id,
                status=TaskStatus.FAILED,
                message=f"Unknown task_type: {task.task_type}",
                started_at=started_at,
                completed_at=datetime.now(),
            )

        # 构建 LangGraph
        graph = builder(task)

        # 准备初始状态
        initial_state: GraphState = {
            "task": task,
            "logs": [f"Starting task: {task.task_id} (type: {task.task_type})"],
            "errors": [],
            "current_step": "start",
            "retry_count": 0,
            "started_at": started_at.isoformat(),
        }

        # 执行 Graph
        # 注意：这里假设 graph.invoke() 返回更新后的 state
        final_state = graph.invoke(initial_state)

        # 提取执行结果
        exec_result: ExecutionResult = final_state.get("exec_result")
        if exec_result is None:
            # Graph 没有返回 exec_result，构造一个默认的
            exec_result = ExecutionResult(
                task_id=task.task_id,
                status=TaskStatus.SUCCESS,
                message="Task completed (no explicit result)",
                logs=final_state.get("logs", []),
            )

        # 更新时间戳
        exec_result.started_at = started_at
        if exec_result.completed_at is None:
            exec_result.completed_at = datetime.now()

        # 记录 Span
        span_builder.complete(
            status=exec_result.status.value,
            message=exec_result.message,
            metrics=exec_result.metrics,
        )

        return exec_result

    except Exception as e:
        # 记录异常
        import traceback
        error_details = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"

        span_builder.complete(
            status=TaskStatus.FAILED.value,
            message=f"Executor exception: {e}",
            extra={"error_details": error_details},
        )

        return ExecutionResult(
            task_id=task.task_id,
            status=TaskStatus.FAILED,
            message=f"Executor exception: {e}",
            logs=[error_details],
            error_details=error_details,
            started_at=started_at,
            completed_at=datetime.now(),
        )


def run_task_async(task: ExecutorTaskSpec) -> ExecutionResult:
    """
    异步执行任务（未来扩展）

    Args:
        task: 任务规格

    Returns:
        执行结果
    """
    # TODO: 实现异步执行
    import asyncio
    return asyncio.run(run_task(task))
```

---

### 2. 注册表机制

#### `lee_runtime/executor/registry.py`

```python
"""
LEE Executor - Graph Builder 注册表

维护 task_type -> Graph Builder 的映射关系。
"""

from typing import Callable, Dict, Optional, List
from .types import ExecutorTaskSpec

# Graph Builder 类型签名
GraphBuilder = Callable[[ExecutorTaskSpec], Any]  # Any 实际上是 CompiledGraph


# ============================================
# 内置 Graph Builders
# ============================================

from .graphs.impl_coding import build_impl_coding_graph
from .graphs.unit_test import build_unit_test_graph
from .graphs.code_review import build_code_review_graph
from .graphs.acceptance_check import build_acceptance_check_graph


# 注册表
_GRAPH_BUILDERS: Dict[str, GraphBuilder] = {
    # 实现类任务
    "l3.impl.coding": build_impl_coding_graph,
    "l3.impl.quick_fix": build_impl_coding_graph,  # 复用

    # 测试类任务
    "l3.test.unit": build_unit_test_graph,
    "l3.test.integration": build_unit_test_graph,  # 复用
    "l3.test.e2e": build_unit_test_graph,  # 复用

    # 审查类任务
    "l3.review.code": build_code_review_graph,
    "l3.review.requirement": build_code_review_graph,  # 复用

    # 验收类任务
    "l3.acceptance.check": build_acceptance_check_graph,
    "l3.gate.check": build_acceptance_check_graph,  # 复用
}


def get_graph_builder(task_type: str) -> Optional[GraphBuilder]:
    """
    获取 Graph Builder

    Args:
        task_type: 任务类型（如 "l3.impl.coding"）

    Returns:
        Graph Builder 函数，如果不存在返回 None
    """
    return _GRAPH_BUILDERS.get(task_type)


def list_graph_builders() -> List[str]:
    """
    列出所有已注册的 Graph Builder

    Returns:
        task_type 列表
    """
    return list(_GRAPH_BUILDERS.keys())


def register_graph_builder(
    task_type: str,
    builder: GraphBuilder,
    override: bool = False,
) -> None:
    """
    注册 Graph Builder

    Args:
        task_type: 任务类型
        builder: Graph Builder 函数
        override: 是否覆盖已存在的 builder
    """
    if task_type in _GRAPH_BUILDERS and not override:
        raise ValueError(f"task_type '{task_type}' already registered")

    _GRAPH_BUILDERS[task_type] = builder


def unregister_graph_builder(task_type: str) -> None:
    """
    注销 Graph Builder

    Args:
        task_type: 任务类型
    """
    if task_type in _GRAPH_BUILDERS:
        del _GRAPH_BUILDERS[task_type]


# ============================================
# Validator 注册表（类似机制）
# ============================================

_VALIDATORS: Dict[str, Callable] = {}


def get_validator(validator_type: str) -> Optional[Callable]:
    """获取验证器"""
    return _VALIDATORS.get(validator_type)


def register_validator(
    validator_type: str,
    validator: Callable,
) -> None:
    """注册验证器"""
    _VALIDATORS[validator_type] = validator
```

---

### 3. 工具层设计

#### `lee_runtime/executor/tools/fs_tools.py`

```python
"""
文件系统工具

提供安全的文件读写操作。
"""

import pathlib
import hashlib
from typing import Dict, Any, Optional


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
) -> None:
    """
    写入文件内容

    Args:
        path: 文件路径
        content: 文件内容
        encoding: 文件编码
        create_parents: 是否自动创建父目录

    Raises:
        IOError: 写入失败
    """
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


def list_files(
    directory: str,
    pattern: str = "*",
    recursive: bool = False,
) -> List[str]:
    """
    列出目录下的文件

    Args:
        directory: 目录路径
        pattern: 文件匹配模式
        recursive: 是否递归

    Returns:
        文件路径列表
    """
    p = pathlib.Path(directory)

    if recursive:
        files = list(p.rglob(pattern))
    else:
        files = list(p.glob(pattern))

    return [str(f) for f in files if f.is_file()]


def file_exists(path: str) -> bool:
    """检查文件是否存在"""
    return pathlib.Path(path).exists()


def get_file_size(path: str) -> int:
    """获取文件大小（字节）"""
    return pathlib.Path(path).stat().st_size
```

#### `lee_runtime/executor/tools/shell_tools.py`

```python
"""
Shell 命令工具

提供安全的命令执行功能。
"""

import subprocess
import shlex
from dataclasses import dataclass
from typing import List, Optional, Dict, Any


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
        env: 环境变量
        shell: 是否使用 shell

    Returns:
        执行结果

    Raises:
        subprocess.TimeoutExpired: 命令超时
        subprocess.CalledProcessError: 命令执行错误
    """
    import time
    start_time = time.time()

    # 准备环境变量
    process_env = None
    if env is not None:
        process_env = {**env, "PATH": os.environ.get("PATH", "")}

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
            stdout=stdout,
            stderr=stderr,
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
    cmd = ["python", "-m", "pytest"]
    if args:
        cmd.extend(args)
    elif test_path:
        cmd.append(test_path)

    cmd_str = " ".join(cmd)
    return run_shell(cmd_str, cwd=cwd, timeout=timeout)


def run_playwright(
    test_path: str = ".",
    cwd: Optional[str] = None,
    timeout: int = 600,
) -> ShellResult:
    """
    执行 Playwright 测试

    Args:
        test_path: 测试目录
        cwd: 工作目录
        timeout: 超时

    Returns:
        执行结果
    """
    cmd = f"npx playwright test {test_path}"
    return run_shell(cmd, cwd=cwd, timeout=timeout)
```

#### `lee_runtime/executor/tools/llm_tools.py`

```python
"""
LLM 调用工具

统一的 LLM 调用接口，支持多种 Profile。
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from ..profiles.loader import load_profile, get_client


@dataclass
class LLMResponse:
    """LLM 响应"""
    content: str
    model: str
    profile: str
    tokens_used: int = 0
    cost_usd: float = 0.0
    duration_seconds: float = 0.0
    raw_response: Optional[Dict] = None


def call_llm(
    profile: str,
    messages: List[Dict[str, str]],
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    stream: bool = False,
) -> LLMResponse:
    """
    调用 LLM

    Args:
        profile: LLM Profile 名称
        messages: 消息列表
        temperature: 温度（覆盖 profile）
        max_tokens: 最大 token（覆盖 profile）
        stream: 是否流式输出

    Returns:
        LLM 响应

    Raises:
    ValueError: Profile 不存在
    Exception: LLM 调用失败
    """
    import time
    start_time = time.time()

    # 加载 Profile
    profile_config = load_profile(profile)

    # 获取 Client
    client = get_client(profile_config)

    # 准备参数
    params = {
        "messages": messages,
        "stream": stream,
    }

    if temperature is not None:
        params["temperature"] = temperature
    elif profile_config.temperature is not None:
        params["temperature"] = profile_config.temperature

    if max_tokens is not None:
        params["max_tokens"] = max_tokens
    elif profile_config.max_tokens is not None:
        params["max_tokens"] = profile_config.max_tokens

    # 调用 LLM
    if profile_config.provider == "anthropic":
        response = client.messages.create(**params)
    elif profile_config.provider == "openai":
        response = client.chat.completions.create(**params)
    else:
        raise ValueError(f"Unsupported provider: {profile_config.provider}")

    # 解析响应
    if hasattr(response, "usage"):
        usage = response.usage
        tokens_used = usage.output_tokens
    else:
        tokens_used = 0

    # 构造响应
    content = response.content[0].text if hasattr(response, "content") else ""

    # 计算成本
    cost_usd = 0.0
    if hasattr(response, "usage"):
        # TODO: 根据实际 token 计算成本
        pass

    duration = time.time() - start_time

    return LLMResponse(
        content=content,
        model=profile_config.model,
        profile=profile,
        tokens_used=tokens_used,
        cost_usd=cost_usd,
        duration_seconds=duration,
        raw_response=response.model_dump() if hasattr(response, "model_dump") else None,
    )


def call_llm_with_tools(
    profile: str,
    messages: List[Dict[str, str]],
    tools: List[Dict[str, Any]],
    temperature: Optional[float] = None,
) -> LLMResponse:
    """
    调用带工具的 LLM

    Args:
        profile: LLM Profile 名称
        messages: 消息列表
        tools: 工具列表
        temperature: 温度

    Returns:
        LLM 响应
    """
    # TODO: 实现工具调用逻辑
    raise NotImplementedError("call_llm_with_tools not implemented yet")
```

#### `lee_runtime/executor/tools/validator_tools.py`

```python
"""
验证器工具

提供各种验证功能。
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass
import json
import yaml


@dataclass
class ValidationResult:
    """验证结果"""
    passed: bool
    validator: str
    errors: List[str] = None
    warnings: List[str] = None
    details: Dict[str, Any] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []


def validate_file_exists(
    path: str,
    required: bool = True,
) -> ValidationResult:
    """
    验证文件是否存在

    Args:
        path: 文件路径
        required: 是否必需

    Returns:
        验证结果
    """
    from pathlib import Path

    p = Path(path)
    exists = p.exists()

    if required and not exists:
        return ValidationResult(
            passed=False,
            validator="file_exists",
            errors=[f"Required file not found: {path}"],
        )

    if not required and not exists:
        return ValidationResult(
            passed=True,
            validator="file_exists",
            warnings=[f"Optional file not found: {path}"],
        )

    return ValidationResult(
        passed=True,
        validator="file_exists",
    )


def validate_schema(
    data: Any,
    schema_path: str,
) -> ValidationResult:
    """
    根据 Schema 验证数据

    Args:
        data: 待验证数据
        schema_path: Schema 文件路径

    Returns:
        验证结果
    """
    from pathlib import Path
    import jsonschema

    schema = yaml.safe_load(Path(schema_path))

    try:
        jsonschema.validate(instance=data, schema=schema)
        return ValidationResult(
            passed=True,
            validator="schema",
        )
    except jsonschema.ValidationError as e:
        return ValidationResult(
            passed=False,
            validator="schema",
            errors=[str(e)],
        )


def validate_contract(
    contract_path: str,
    artifacts: Dict[str, str],
) -> ValidationResult:
    """
    验证契约产物

    Args:
        contract_path: 契约文件路径
        artifacts: 产物映射（逻辑名 -> 真实路径）

    Returns:
        验证结果
    """
    contract = yaml.safe_load(Path(contract_path))

    errors = []
    warnings = []

    # 验证 required_outputs
    required_outputs = contract.get("required_outputs", {})
    for logical_name, artifact_path in artifacts.items():
        if logical_name in required_outputs:
            if not Path(artifact_path).exists():
                errors.append(f"Required artifact not found: {logical_name} at {artifact_path}")

    # 验证 forbidden_behaviors
    forbidden = contract.get("forbidden_behaviors", [])
    # TODO: 实现验证逻辑

    return ValidationResult(
        passed=len(errors) == 0,
        validator="contract",
        errors=errors,
        warnings=warnings,
    )
```

---

### 4. Graph 基础组件

#### `lee_runtime/executor/graphs/base.py`

```python
"""
Graph 基础组件和工具函数

提供构建 LangGraph 的通用工具。
"""

from typing import Dict, Any, List, Callable, Any
from langgraph.graph import StateGraph, END
from langgraph.checkpoint import MemorySaver

from ..types import (
    GraphState,
    ExecutionResult,
    ExecutorTaskSpec,
    TaskStatus,
)
from ..tools import fs_tools, shell_tools, llm_tools


def create_base_graph(state_type: type, config: Dict = None) -> StateGraph:
    """
    创建基础 Graph

    Args:
        state_type: State 类型（TypedDict）
        config: 配置项

    Returns:
        StateGraph 实例
    """
    return StateGraph(state_type)


def add_load_inputs_node(graph: StateGraph, name: str = "load_inputs"):
    """
    添加加载输入节点

    通用的输入加载逻辑。
    """
    def load_inputs(state: GraphState) -> GraphState:
        t = state["task"]
        logs = state.get("logs", [])
        logs.append(f"[{name}] Loading inputs...")

        inputs = {}
        for logical_name, real_path in t.inputs.items():
            try:
                content = fs_tools.read_file(real_path)
                inputs[logical_name] = content
                logs.append(f"  Loaded: {logical_name} <- {real_path}")
            except Exception as e:
                logs.append(f"  Failed to load {logical_name}: {e}")
                state["errors"].append(str(e))

        state["inputs"] = inputs
        state["logs"] = logs
        return state

    graph.add_node(name, load_inputs)
    return graph


def add_llm_node(
    graph: StateGraph,
    name: str,
    system_prompt_template: str,
    user_prompt_template: str,
    output_key: str = "llm_output",
):
    """
    添加 LLM 调用节点

    Args:
        graph: StateGraph 实例
        name: 节点名称
        system_prompt_template: 系统提示词模板
        user_prompt_template: 用户提示词模板
        output_key: 输出在 state 中的键名
    """
    def llm_call(state: GraphState) -> GraphState:
        t = state["task"]
        logs = state.get("logs", [])
        logs.append(f"[{name}] Calling LLM...")

        # 准备消息
        system_prompt = system_prompt_template.format(**state)
        user_prompt = user_prompt_template.format(**state)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        # 调用 LLM
        response = llm_tools.call_llm(
            profile=t.llm_profile or "default",
            messages=messages,
            temperature=t.llm_temperature,
            max_tokens=t.llm_max_tokens,
        )

        state[output_key] = response.content
        state["logs"].append(f"  LLM response: {len(response.content)} chars")
        state["logs"].append(f"  Tokens used: {response.tokens_used}")
        state["logs"].append(f"  Cost: ${response.cost_usd:.4f}")

        return state

    graph.add_node(name, llm_call)
    return graph


def add_apply_changes_node(
    graph: StateGraph,
    name: str = "apply_changes",
    changes_key: str = "code_changes",
    notes_key: str = "impl_notes",
):
    """
    添加应用更改节点

    Args:
        graph: StateGraph 实例
        name: 节点名称
        changes_key: state 中存储 code changes 的键名
        notes_key: state 中存储 notes 的键名
    """
    def apply_changes(state: GraphState) -> GraphState:
        t = state["task"]
        logs = state.get("logs", [])
        logs.append(f"[{name}] Applying changes...")

        changes = state.get(changes_key, {})

        # 应用文件更改
        repo_root = t.inputs.get("repo_workspace", ".")
        for rel_path, content in changes.items():
            abs_path = f"{repo_root.rstrip('/')}/{rel_path.lstrip('/')}"
            fs_tools.write_file(abs_path, content)
            logs.append(f"  Written: {abs_path}")

        # 写入 notes
        notes_path = t.outputs.get(notes_key)
        if notes_path and notes_key in state:
            fs_tools.write_file(notes_path, state[notes_key])
            logs.append(f"  Written notes: {notes_path}")

        # 写入摘要
        summary_path = t.outputs.get("change_summary")
        if summary_path:
            summary = "本次任务改动了以下文件：\n"
            summary += "\n".join(f"- {p}" for p in changes.keys())
            fs_tools.write_file(summary_path, summary)
            logs.append(f"  Written summary: {summary_path}")

        state["logs"] = logs
        return state

    graph.add_node(name, apply_changes)
    return graph


def add_build_result_node(
    graph: StateGraph,
    name: str = "build_result",
) -> StateGraph:
    """
    添加构建结果节点

    这个节点负责构造 ExecutionResult。
    """
    def build_result(state: GraphState) -> GraphState:
        t = state["task"]
        logs = state.get("logs", [])

        # 收集 artifacts
        artifacts = {}
        for logical_name, real_path in t.outputs.items():
            if Path(real_path).exists():
                artifacts[logical_name] = real_path

        # 构造 ExecutionResult
        state["exec_result"] = ExecutionResult(
            task_id=t.task_id,
            status=TaskStatus.SUCCESS,
            message=f"{t.task_type} completed successfully",
            artifacts=artifacts,
            logs=logs,
            metrics={
                "duration_seconds": 0,  # TODO: 计算实际耗时
                "retry_count": state.get("retry_count", 0),
            },
            started_at=t.inputs.get("started_at"),  # 可能由上游传入
            completed_at=datetime.now().isoformat(),
        )

        return state

    graph.add_node(name, build_result)
    return graph


def compile_graph(
    graph: StateGraph,
    entry_point: str = "load_inputs",
    end_node: str = "build_result",
) -> Any:
    """
    编译 Graph

    Args:
        graph: StateGraph 实例
        entry_point: 入口节点名称
        end_node: 结束节点名称

    Returns:
        编译后的 Graph
    """
    # 设置入口点
    graph.set_entry_point(entry_point)

    # 连接结束节点
    graph.add_edge(end_node, END)

    return graph.compile()
```

---

### 5. 具体 Graph 实现

#### `lee_runtime/executor/graphs/impl_coding.py`

```python
"""
实现类任务 Graph (l3.impl.coding)

处理代码实现任务：读取设计文档 -> LLM 生成代码 -> 写入文件。
"""

from typing import TypedDict, Any
from langgraph.graph import StateGraph, END

from ..types import ExecutorTaskSpec, ExecutionResult, GraphState
from ..graphs.base import (
    create_base_graph,
    add_load_inputs_node,
    add_llm_node,
    add_apply_changes_node,
    add_build_result_node,
)
from ..tools import fs_tools, llm_tools


class ImplCodingState(GraphState, total=False):
    """实现类任务 State"""
    task: ExecutorTaskSpec
    inputs: Dict[str, str] = {}
    prd: str = ""
    design: str = ""
    contract: str = ""
    impl_plan: str = ""
    code_changes: Dict[str, str] = {}
    logs: List[str] = []
    errors: List[str] = []
    exec_result: ExecutionResult = None


def build_impl_coding_graph(task: ExecutorTaskSpec):
    """
    构建实现类任务 LangGraph

    Args:
        task: 任务规格

    Returns:
        编译后的 LangGraph
    """
    graph = StateGraph(ImplCodingState)

    # 节点1: 加载输入
    def load_inputs(state: ImplCodingState) -> ImplCodingState:
        t = state["task"]
        logs = state.get("logs", [])
        logs.append("[load_inputs] Loading inputs...")

        # 加载 PRD
        if "frozen_prd" in t.inputs:
            state["prd"] = fs_tools.read_file(t.inputs["frozen_prd"])
            logs.append(f"  Loaded PRD from {t.inputs['frozen_prd']}")

        # 加载设计文档
        if "design_spec" in t.inputs:
            state["design"] = fs_tools.read_file(t.inputs["design_spec"])
            logs.append(f"  Loaded design from {t.inputs['design_spec']}")

        # 加载实现契约
        if "impl_contract" in t.inputs:
            state["contract"] = fs_tools.read_file(t.inputs["impl_contract"])
            logs.append(f"  Loaded contract from {t.inputs['impl_contract']}")

        state["logs"] = logs
        return state

    graph.add_node("load_inputs", load_inputs)

    # 节点2: LLM 生成实现方案
    def llm_impl(state: ImplCodingState) -> ImplCodingState:
        t = state["task"]
        logs = state.get("logs", [])
        logs.append("[llm_impl] Calling LLM for implementation...")

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
{state.get('contract', '(No Contract)'}
"""

        response = llm_tools.call_llm(
            profile=t.llm_profile or "claudebot",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=t.llm_temperature,
        )

        # 解析 FILE 标记
        code_changes = {}
        current_path = None
        current_lines = []

        for line in response.content.splitlines():
            if line.startswith("===FILE:") and line.endswith("==="):
                if current_path is not None:
                    code_changes[current_path] = "\n".join(current_lines).strip()
                current_path = line[len("===FILE:"):-len("===")].strip()
                current_lines = []
            elif current_path is not None:
                current_lines.append(line)

        if current_path is not None:
            code_changes[current_path] = "\n".join(current_lines).strip("\n")

        state["code_changes"] = code_changes
        state["impl_plan"] = response.content[:500] + "..." if len(response.content) > 500 else response.content
        state["logs"].append(f"  Generated {len(code_changes)} file(s)")
        state["logs"] = logs
        return state

    graph.add_node("llm_impl", llm_impl)

    # 节点3: 应用更改
    def apply_changes(state: ImplCodingState) -> ImplCodingState:
        t = state["task"]
        logs = state.get("logs", [])
        logs.append("[apply_changes] Applying code changes...")

        repo_root = t.inputs.get("repo_workspace", ".")

        for rel_path, content in state.get("code_changes", {}).items():
            abs_path = f"{repo_root.rstrip('/')}/{rel_path.lstrip('/')}"
            fs_tools.write_file(abs_path, content)
            logs.append(f"  Written: {abs_path}")

        state["logs"] = logs
        return state

    graph.add_node("apply_changes", apply_changes)

    # 节点4: 构建结果
    def build_result(state: ImplCodingState) -> ImplCodingState:
        t = state["task"]
        logs = state.get("logs", [])

        # 收集 artifacts
        artifacts = {}
        for logical_name, real_path in t.outputs.items():
            if Path(real_path).exists():
                artifacts[logical_name] = real_path

        state["exec_result"] = ExecutionResult(
            task_id=t.task_id,
            status=TaskStatus.SUCCESS,
            message="Implementation completed successfully",
            artifacts=artifacts,
            logs=logs,
            metrics={"files_written": len(state.get("code_changes", {}))},
        )

        return state

    graph.add_node("build_result", build_result)

    # 连接图
    graph.set_entry_point("load_inputs")
    graph.add_edge("load_inputs", "llm_impl")
    graph.add_edge("llm_impl", "apply_changes")
    graph.add_edge("apply_changes", "build_result")
    graph.add_edge("build_result", END)

    return graph.compile()
```

---

### 6. 与 Orchestrator 集成方案

#### 集成点设计

```python
"""
flowcore/orchestrator/engine_commands.py 中添加 Executor 调用
"""

from lee_runtime.executor.types import ExecutorTaskSpec, ExecutionResult
from lee_runtime.executor.langgraph_runner import run_task


def execute_step_with_executor(
    project_dir: str,
    step_id: str,
    llm_profile: str = "claudebot",
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
    workflow = yaml.safe_load(workflow_path)

    # 2. 查找步骤定义
    step = None
    for s in workflow.get("steps", []):
        if s.get("id") == step_id:
            step = s
            break

    if step is None:
        print(f"Error: Step not found: {step_id}")
        return False

    # 3. 构造 ExecutorTaskSpec
    # 步骤的 agent/skill 映射到 task_type
    task_type = _map_to_task_type(step.get("agent", ""), step.get("skill", ""))

    task = ExecutorTaskSpec(
        task_id=step_id,
        task_type=task_type,
        inputs=_resolve_inputs(project_dir, step.get("inputs", {})),
        outputs=_resolve_outputs(project_dir, step.get("outputs", {})),
        llm_profile=llm_profile,
    )

    # 4. 调用 Executor
    result = run_task(task)

    # 5. 处理结果
    if result.status == TaskStatus.SUCCESS:
        print(f"✅ Step {step_id} completed: {result.message}")
        for artifact_name, artifact_path in result.artifacts.items():
            print(f"   📄 {artifact_name}: {artifact_path}")
    else:
        print(f"❌ Step {step_id} failed: {result.message}")
        if result.error_details:
            print(f"   Error: {result.error_details}")

    return result.status == TaskStatus.SUCCESS


def _map_to_task_type(agent: str, skill: str) -> str:
    """
    将 agent/skill 映射到 task_type

    Args:
        agent: Agent ID
        skill: Skill ID

    Returns:
        task_type
    """
    # 简化映射规则
    mapping = {
        # 实现类
        ("implementation_executor", "impl"): "l3.impl.coding",
        ("tech_lead", "coding"): "l3.impl.coding",
        ("frontend_engineer", "impl"): "l3.impl.coding",
        ("backend_engineer", "impl"): "l3.impl.coding",

        # 测试类
        ("test_engineer", "test"): "l3.test.unit",
        ("qa_engineer", "test"): "l3.test.unit",
        ("test_executor", "test"): "l3.test.unit",

        # 审查类
        ("code_reviewer", "review"): "l3.review.code",
        ("implementation_reviewer", "review"): "l3.review.code",
    }

    # 尝试 skill 映射
    if skill:
        skill_lower = skill.lower()
        if "impl" in skill_lower or "coding" in skill_lower:
            return "l3.impl.coding"
        elif "test" in skill_lower or "unit" in skill_lower:
            return "l3.test.unit"
        elif "review" in skill_lower or "code" in skill_lower:
            return "l3.review.code"

    # 尝试 agent 映射
    if agent:
        agent_lower = agent.lower()
        if "impl" in agent_lower or "executor" in agent_lower:
            return "l3.impl.coding"
        elif "test" in agent_lower or "qa" in agent_lower:
            return "l3.test.unit"
        elif "review" in agent_lower:
            return "l3.review.code"

    # 默认
    return "l3.impl.coding"


def _resolve_inputs(project_dir: str, inputs_config: Dict) -> Dict[str, str]:
    """解析输入配置为真实路径"""
    # TODO: 实现路径解析逻辑
    return inputs_config


def _resolve_outputs(project_dir: str, outputs_config: Dict) -> Dict[str, str]:
    """解析输出配置为真实路径"""
    # TODO: 实现路径解析逻辑
    return outputs_config
```

---

## 🔄 执行流程图

```
┌──────────────────────────────────────────────────────────────────┐
│  Orchestrator (L2)                                         │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │ EngineCommands.execute_step_with_executor()                       │ │
│  │                                                         │ │
│  │ 1. 加载 workflow.yaml                                       │ │
│  │ 2. 找到步骤定义                                             │ │
│  │ 3. 映射 agent/skill -> task_type                             │ │
│  │ 4. 解析 inputs/outputs 为真实路径                               │ │
│  │ 5. 调用 Executor.run_task(task_spec)                          │ │
│  │                                                         │ │
│  └──────────────────────────────────────────────────────────────┘ │
└──────────────────────────────┬─────────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│  Executor (L3) - langgraph_runner.py                              │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │ run_task(task_spec)                                           │ │
│  │                                                         │ │
│  │ 1. get_graph_builder(task_type)                               │ │
│  │ 2. builder(task) -> CompiledGraph                          │ │
│  │ 3. graph.invoke(initial_state)                                 │ │
│  │ 4. extract exec_result from state                               │ │
│  │                                                         │ │
│  │ ┌──────────────────────────────────────────────────────┐ │ │
│  │ │ CompiledGraph (LangGraph)                              │ │ │ │
│  │ │                                                         │ │ │ │
│  │ │  Node: load_inputs                                   │ │ │ │ │
│  │ │   - fs_tools.read_file                              │ │ │ │ │
│  │ │      ↓                                                │ │ │ │ │
│  │ │ Node: llm_impl                                       │ │ │ │ │
│  │ │   - llm_tools.call_llm()                              │ │ │ │ │
│  │ │      ↓                                                │ │ │ │ │
│  │ │ Node: apply_changes                                 │ │ │ │ │
│  │ │   - fs_tools.write_file()                              │ │ │ │ │
│  │ │      ↓                                                │ │ │ │ │
│  │ │ Node: build_result                                  │ │ │ │ │ │
│  │ │   - construct ExecutionResult                            │ │ │ │ │ │
│  │ │      ↓                                                │ │ │ │ │
│  │ │  END                                                 │ │ │ │ │
│  │ └──────────────────────────────────────────────────────┘ │ │ │ │
│  │                                                         │ │ │ │
│  │  Span Builder (Execution Trace)                        │ │ │ │ │
│  │  - 记录 Span/Artifact                                   │ │ │ │ │ │
│  │ └──────────────────────────────────────────────────────┘ │ │ │ │
│  └──────────────────────────────────────────────────────────────┘ │ │ │
│                                                           │ │ │ │
│  ┌──────────────────────────────────────────────────────┐ │ │ │ │
│  │ Tool Layer (L4)                                          │ │ │ │ │
│  │ - fs_tools: read_file, write_file, compute_hash        │ │ │ │ │ │
│  │ - shell_tools: run_shell, run_pytest, run_playwright    │ │ │ │ │ │
│  │ - llm_tools: call_llm, call_llm_with_tools          │ │ │ │ │ │
│  │ - validator_tools: validate_file_exists, validate_schema  │ │ │ │ │ │
│  └──────────────────────────────────────────────────────┘ │ │ │ │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🧪 测试策略

### 单元测试

#### `lee_runtime/executor/tests/test_graphs.py`

```python
import pytest
from pathlib import Path
from lee_runtime.executor.types import ExecutorTaskSpec, TaskStatus
from lee_runtime.executor.langgraph_runner import run_task
from lee_runtime.executor.graphs.impl_coding import build_impl_coding_graph


def test_impl_graph_builder():
    """测试 Graph Builder 可以正常构建"""
    task = ExecutorTaskSpec(
        task_id="test_impl",
        task_type="l3.impl.coding",
        inputs={
            "frozen_prd": "/path/to/prd.md",
            "design_spec": "/path/to/design.md",
            "impl_contract": "/path/to/contract.md",
            "repo_workspace": "/path/to/repo",
        },
        outputs={
            "impl_notes": "/path/to/notes.md",
            "change_summary": "/path/to/summary.md",
        },
    )

    graph = build_impl_coding_graph(task)
    assert graph is not None


def test_executor_with_mock_inputs(tmp_path):
    """测试 Executor 执行流程（使用 mock 输入）"""
    # 创建临时测试文件
    prd_path = tmp_path / "prd.md"
    prd_path.write_text("# PRD Content")

    task = ExecutorTaskSpec(
        task_id="test_impl",
        task_type="l3.impl.coding",
        inputs={
            "frozen_prd": str(prd_path),
            "repo_workspace": str(tmp_path),
        },
        outputs={
            "impl_notes": str(tmp_path / "notes.md"),
        },
        llm_profile="claudebot",
    )

    # 这里会调用真实的 LLM，实际使用时需要 mock
    # result = run_task(task)

    # TODO: 添加 mock 支持
```

---

## 📋 实现路线图

### Phase 1: 核心框架 (当前任务)

- [x] 设计文档评审
- [ ] 创建目录结构
- [ ] 实现核心类型 (`types.py`)
- [ ] 实现 LangGraph Runner (`langgraph_runner.py`)
- [ ] 实现注册表 (`registry.py`)
- [ ] 实现 Graph 基础组件 (`graphs/base.py`)

### Phase 2: 工具层

- [ ] 实现 `fs_tools.py`
- [ ] 实现 `shell_tools.py`
- [ ] 实现 `llm_tools.py`
- [ ] 实现 `validator_tools.py`
- [ ] 实现 LLM Profile 加载器 (`profiles/loader.py`)

### Phase 3: Graph 模板

- [ ] 实现 `impl_coding.py`
- [ ] 实现 `unit_test.py`
- [ ] 实现 `code_review.py`
- [ ] 实现 `acceptance_check.py`

### Phase 4: 追踪与观测

- [ ] 实现 Span Builder (`tracing/span_builder.py`)
- [ ] 集成 Execution Trace
- [ ] 实现日志聚合

### Phase 5: Orchestrator 集成

- [ ] 修改 `engine_commands.py`
- [ ] 添加 `execute_step_with_executor()` 函数
- [ ] 添加 task_type 映射逻辑
- [ ] 添加路径解析逻辑

### Phase 6: 测试

- [ ] 单元测试
- [ ] 集成测试
- [ ] 端到端测试

---

## 🤔 设计问题

### 1. task_type 命名规范

**问题**: 如何设计 task_type 命名体系？

**建议**:
```
l3.{category}.{action}.{detail}

例如:
- l3.impl.coding         # 实现代码
- l3.test.unit         # 单元测试
- l3.review.code        # 代码审查
- l3.acceptance.check   # 验收检查
- l3.gate.check        # 门禁检查
```

### 2. 输入输出映射

**问题**: Orchestrator 中如何定义 inputs/outputs？

**建议**: 在 workflow.yaml 的步骤中增加 `execution_context` 字段：

```yaml
steps:
  - id: p08_03_impl
    name: 实现需求
    agent: implementation_executor
    execution_context:
      task_type: l3.impl.coding
      inputs:
        frozen_prd: "@openspec/contracts/requirement-freeze/v1/freeze.yaml"
        design_spec: "@openspec/designs/p08_03/design.md"
        impl_contract: "@openspec/contracts/implementation-contract/v1/contract.yaml"
        repo_workspace: "@output"
      outputs:
        impl_notes: "@output/impl_notes.md"
        change_summary: "@output/change_summary.md"
```

### 3. 错误处理策略

**问题**: Graph 执行失败时如何处理？

**建议**:
1. 在每个节点捕获异常，存入 `state["errors"]`
2. 在 `build_result` 节点检查 `state["errors"]`，决定最终 status
3. 如果有错误，添加 `error_details` 到 `ExecutionResult`
4. 关键错误记录到 Execution Trace

### 4. 重试机制

**问题**: 如何实现重试？

**建议**:
1. 在 Graph 层面添加重试边条件判断
2. 在 LangGraph Router 中捕获特定异常类型（如超时、临时网络错误）
3. 使用 LangGraph 的条件边功能实现智能重试
4. 记录重试次数到 `metrics.retry_count`

### 5. 并行执行

**问题**: 如何支持并行任务？

**建议**:
1. 设计 `l3.test.parallel` task_type
2. Graph 中使用 `Send` 节点并行调用多个测试
3. 使用 `join` 等待所有分支完成
4. 汇总所有分支的结果

---

## 📝 审查清单

### 设计阶段

- [ ] 核心类型定义是否合理？
- [ ] LangGraph State 设计是否完整？
- [ ] 工具层接口是否满足需求？
- [ ] 注册表机制是否灵活？
- [ ] 与现有 Orchestrator 集成方案是否可行？

### 实现阶段

- [ ] 所有组件是否按设计实现？
- [ ] 类型注解是否完整？
- [ ] 错误处理是否健壮？
- [ ] 日志记录是否充分？
- [ ] 测试覆盖率是否足够？

### 集成阶段

- [ ] Orchestrator 调用 Executor 是否无侵入？
- [ ] 现有 workflow.yaml 是否兼容？
- [ ] 性能开销是否可接受？
- [ ] 可观测性是否满足要求？
- [ ] 调试体验是否良好？

---

## 🔗 相关文档

- [01-功能与用法手册.md](./01-功能与用法手册.md)
- [02-软件架构文档.md](./02-软件架构文档.md)
- [03-缺陷与改进方向.md](./03-缺陷与改进方向.md)
- [spec-global/core/contracts/execution-trace/v1/contract.yaml](../spec-global/core/contracts/execution-trace/v1/contract.yaml)
- [workflow.yaml](../workflow.yaml)

---

## 📊 附录：完整示例

### A. workflow.yaml 示例

```yaml
kind: workflow
id: workflow.dev.development_pipeline
name: 开发流水线
version: '1.0'

steps:
  - id: p08_03_design
    name: 设计方案
    agent: tech_architect
    outputs:
      - path: "@openspec/designs/p08_03/design.md"
        required: true

  - id: p08_03_impl
    name: 实现需求
    agent: implementation_executor
    execution_context:
      task_type: l3.impl.coding
      inputs:
        frozen_prd: "@openspec/contracts/requirement-freeze/v1/freeze.yaml"
        design_spec: "@openspec/designs/p08_03/design.md"
        impl_contract: "@openspec/contracts/implementation-contract/v1/contract.yaml"
        repo_workspace: "@output"
      outputs:
        impl_notes: "@output/impl_notes.md"
        change_summary: "@output/change_summary.md"
    depends_on:
      - p08_03_design

  - id: p08_03_test
    name: 单元测试
    agent: qa_engineer
    execution_context:
      task_type: l3.test.unit
      inputs:
        repo_workspace: "@output"
      test_command: "pytest -q"
      test_config: "@output/tests/config.yaml"
      outputs:
        test_report_human: "@output/test_report.md"
        raw_logs: "@output/test_raw.log"
    depends_on:
      - p08_03_impl

  - id: p08_03_review
    name: 代码审查
    agent: code_reviewer
    execution_context:
      task_type: l3.review.code
      inputs:
        repo_workspace: "@output"
        review_criteria: "@openspec/review_criteria.yaml"
      outputs:
        review_report: "@output/review_report.md"
    depends_on:
      - p08_03_impl
```

### B. 完整的执行流程

```
Orchestrator (L2)                    │
  ├── EngineCommands                   │
  ├── step_id: p08_03_impl              │
  ├── agent: implementation_executor    │
  └── execution_context defined         │
                                        │
                                        ▼
Executor (L3)                          │
  ├── run_task(task_spec)              │
  │   ├── task_type: l3.impl.coding    │
  │   ├── inputs resolved              │
  │   └── outputs resolved             │
                                        │
                                        ▼
LangGraph                             │
  ├── load_inputs (fs_tools)         │
  ├── llm_impl (llm_tools)          │
  ├── apply_changes (fs_tools)       │
  └── build_result                  │
                                        │
                                        ▼
ExecutionResult                         │
  ├── status: success                 │
  ├── artifacts: impl_notes, ...      │
  └── logs: [...]                      │
```

---

## 🎯 下一步行动

1. **评审此设计** - 请 review 上面的设计，指出问题和改进建议
2. **确认实现优先级** - 确认哪些功能需要优先实现
3. **开始实现** - 按路线图逐步实现
4. **迭代优化** - 根据实际使用反馈调整设计
