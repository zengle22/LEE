---
title: LEE Executor (基于 LangGraph) 架构设计 - MVP 版本
author: LEE Team
date: 2026-01-29
version: v3.1-MVP
last_updated: 2026-02-19
---

# LEE Executor (基于 LangGraph) 架构设计 - MVP 版本

> **版本:** v3.1-MVP
> **状态:** MVP 设计（精简版，聚焦可落地）
> **创建日期:** 2026-01-29
> **作者:** LEE Team
> **基于:** v3.1-design + 评审反馈修正

---

## 📋 文档说明

本文档是 `04-executor-langgraph-architecture.md` 的 **MVP 精简版本**，基于评审反馈进行了以下调整：

### ✅ 已修复的问题

1. **GraphState 类型设计** - 简化为纯 TypedDict，移除复杂继承
2. **时间类型统一** - 统一使用 `datetime`，不再混用 str
3. **删除伪异步** - 移除 `run_task_async`，避免未来坑点
4. **修复工具层 bug** - 补充缺失的 import，修正 SDK 调用
5. **简化 base helper** - 先让各个 graph 独立实现，稳定后再抽象
6. **添加安全边界** - 新增 workspace guard 和 safe_join

### ⏸️ 暂缓的功能

- [ ] 完整的重试策略（只在 Runner 外部做简单重试）
- [ ] 并行执行支持（先做单线程）
- [ ] Validator registry（先手动调用简单 validator）
- [ ] LLM 工具调用（call_llm_with_tools）
- [ ] 异步/分布式后端（只用 LangGraph 同步版本）
- [ ] LLM 成本统计（先只记 tokens_used）

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
│  - security: 安全边界                                              │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 📁 目录结构（MVP）

```
lee_runtime/
  executor/
    __init__.py                       # Executor 模块导出
    types.py                           # 核心数据类型（简化版）
    registry.py                        # task_type -> Graph Builder 注册表
    langgraph_runner.py                # 核心入口：run_task（仅同步）
    tools/
      __init__.py
      fs_tools.py                     # 文件系统工具
      shell_tools.py                  # Shell 命令工具
      llm_tools.py                    # LLM 调用工具（仅 Anthropic）
      security.py                     # [NEW] 安全边界工具
    graphs/
      __init__.py
      # 移除 base.py，先让每个 graph 独立实现
      impl_coding.py                   # l3.impl.coding 实现 Graph
      unit_test.py                     # l3.test.unit 测试 Graph
    tracing/
      __init__.py
      span_builder.py                  # Span 构建器（简化版）
    profiles/                           # LLM Profile 配置
      __init__.py
      loader.py                        # Profile 加载器
    tests/
      __init__.py
      test_graphs.py                   # Graph 单元测试
      test_integration.py              # 集成测试
```

---

## 📦 核心类型定义（修正版）

### `lee_runtime/executor/types.py`

```python
"""
LEE Executor 核心类型定义（MVP 版本）

定义 Orchestrator -> Executor 之间的统一数据契约。
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
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

    # [NEW] 安全边界
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
# Graph State 类型定义（修正版）
# ============================================

from typing import TypedDict, NotRequired  # Python 3.11+

class BaseState(TypedDict, total=False):
    """
    LangGraph State 的基础类型（TypedDict 版本）

    所有 Graph 的 State 都应该继承这些基础字段。

    注意：这是类型提示，运行时使用普通 dict 即可。
    """
    task: ExecutorTaskSpec               # 任务规格（入参）
    logs: List[str]                       # 执行日志
    errors: List[str]                     # 错误日志
    current_step: str                     # 当前步骤名
    retry_count: int                      # 重试次数
    started_at: datetime                  # [FIXED] 开始时间（datetime 类型）
    completed_at: NotRequired[datetime]   # 完成时间（可选）


# 具体 Graph 的 State 定义示例
class ImplCodingState(BaseState, total=False):
    """实现类任务 State"""
    inputs: Dict[str, str]               # 加载的输入内容
    prd: str                              # PRD 内容
    design: str                           # 设计文档内容
    contract: str                         # 实现契约内容
    impl_plan: str                        # 实现方案
    code_changes: Dict[str, str]         # 代码变更（文件路径 -> 内容）
    exec_result: ExecutionResult          # 最终执行结果


class UnitTestState(BaseState, total=False):
    """单元测试任务 State"""
    test_command: str                    # 测试命令
    test_config: Dict[str, Any]          # 测试配置
    test_report: str                     # 测试报告内容
    test_results: Dict[str, Any]         # 测试结果
    exec_result: ExecutionResult          # 最终执行结果
```

---

## 🏗️ 核心组件（修正版）

### 1. LangGraph Runner（同步版，移除伪异步）

#### `lee_runtime/executor/langgraph_runner.py`

```python
"""
LEE Executor - LangGraph Runner（MVP 版本）

基于 LangGraph 的统一执行入口（仅同步版本）。

核心职责：
1. 接收 ExecutorTaskSpec
2. 根据 task_type 获取对应的 Graph Builder
3. 构建 LangGraph 流程
4. 执行并返回 ExecutionResult
"""

from typing import Dict, Any
from datetime import datetime

from .types import (
    ExecutorTaskSpec,
    ExecutionResult,
    TaskStatus,
    BaseState,
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

        # 准备初始状态（使用普通 dict）
        initial_state: Dict[str, Any] = {
            "task": task,
            "logs": [f"Starting task: {task.task_id} (type: {task.task_type})"],
            "errors": [],
            "current_step": "start",
            "retry_count": 0,
            "started_at": started_at,  # [FIXED] 直接存 datetime 对象
        }

        # 执行 Graph
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
                started_at=started_at,
                completed_at=datetime.now(),
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
```

---

### 2. 安全边界工具（新增）

#### `lee_runtime/executor/tools/security.py`

```python
"""
安全边界工具

提供文件路径安全验证，防止路径穿越攻击。
"""

import os
import pathlib
from typing import List, Optional


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
) -> tuple[bool, Optional[str]]:
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

### 3. 文件系统工具（集成安全边界）

#### `lee_runtime/executor/tools/fs_tools.py`

```python
"""
文件系统工具（MVP 版本，集成安全边界）
"""

import pathlib
import hashlib
from typing import Dict, Any, Optional

from .security import safe_join, validate_write_operation


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
    # [NEW] 安全边界参数
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

### 4. Shell 工具（修复 bug）

#### `lee_runtime/executor/tools/shell_tools.py`

```python
"""
Shell 命令工具（MVP 版本，修复 bug）

提供安全的命令执行功能。
"""

import subprocess
import time  # [FIXED] 添加缺失的 import
import os    # [FIXED] 添加缺失的 import
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
    start_time = time.time()

    # [FIXED] 修正环境变量处理
    process_env = None
    if env is not None:
        process_env = {**os.environ, **env}
    else:
        process_env = os.environ.copy()

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
    if args:
        cmd = ["python", "-m", "pytest"] + args
    else:
        cmd = ["python", "-m", "pytest", test_path]

    cmd_str = " ".join(cmd)
    return run_shell(cmd_str, cwd=cwd, timeout=timeout, shell=False)
```

---

### 5. LLM 工具（修复 bug，仅支持 Anthropic）

#### `lee_runtime/executor/tools/llm_tools.py`

```python
"""
LLM 调用工具（MVP 版本，仅 Anthropic）

统一的 LLM 调用接口，MVP 阶段只支持 Anthropic。
"""

from typing import List, Dict, Any, Optional
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
    调用 LLM（MVP 版本，仅支持 Anthropic）

    Args:
        profile: LLM Profile 名称
        messages: 消息列表（内部格式）
        temperature: 温度（覆盖 profile）
        max_tokens: 最大 token（覆盖 profile）
        stream: 是否流式输出（MVP 阶段固定为 False）

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

    # 调用 Anthropic Messages API
    response = client.messages.create(**params)

    # 解析响应（Anthropic 格式）
    if hasattr(response, "usage"):
        usage = response.usage
        tokens_used = usage.output_tokens
    else:
        tokens_used = 0

    # Anthropic 响应格式：response.content[0].text
    if hasattr(response, "content") and len(response.content) > 0:
        content = response.content[0].text
    else:
        content = ""

    duration = time.time() - start_time

    return LLMResponse(
        content=content,
        model=profile_config.model,
        profile=profile,
        tokens_used=tokens_used,
        duration_seconds=duration,
        raw_response=response.model_dump() if hasattr(response, "model_dump") else None,
    )


# call_llm_with_tools 在 MVP 阶段不实现
```

---

## 📊 Graph 实现（简化版，独立实现）

### 1. `impl_coding.py` Graph（独立实现，不依赖 base helper）

#### `lee_runtime/executor/graphs/impl_coding.py`

```python
"""
实现类任务 Graph (l3.impl.coding)

MVP 版本：独立实现，不依赖 base helper。

处理代码实现任务：读取设计文档 -> LLM 生成代码 -> 安全写入文件。
"""

from typing import Dict, Any
from langgraph.graph import StateGraph, END

from ..types import (
    ExecutorTaskSpec,
    ExecutionResult,
    TaskStatus,
    ImplCodingState,
)
from ..tools import fs_tools, llm_tools


def build_impl_coding_graph(task: ExecutorTaskSpec) -> Any:
    """
    构建实现类任务 LangGraph

    Args:
        task: 任务规格

    Returns:
        编译后的 LangGraph
    """
    # 使用 ImplCodingState 作为状态类型
    graph = StateGraph(ImplCodingState)

    # 节点1: 加载输入
    def load_inputs(state: ImplCodingState) -> ImplCodingState:
        t = state["task"]
        logs = state.get("logs", []).copy()
        logs.append("[load_inputs] Loading inputs...")

        inputs = {}

        # 加载 PRD
        if "frozen_prd" in t.inputs:
            try:
                content = fs_tools.read_file(t.inputs["frozen_prd"])
                state["prd"] = content
                logs.append(f"  Loaded PRD from {t.inputs['frozen_prd']}")
            except Exception as e:
                logs.append(f"  Failed to load PRD: {e}")
                state["errors"].append(str(e))

        # 加载设计文档
        if "design_spec" in t.inputs:
            try:
                content = fs_tools.read_file(t.inputs["design_spec"])
                state["design"] = content
                logs.append(f"  Loaded design from {t.inputs['design_spec']}")
            except Exception as e:
                logs.append(f"  Failed to load design: {e}")
                state["errors"].append(str(e))

        # 加载实现契约
        if "impl_contract" in t.inputs:
            try:
                content = fs_tools.read_file(t.inputs["impl_contract"])
                state["contract"] = content
                logs.append(f"  Loaded contract from {t.inputs['impl_contract']}")
            except Exception as e:
                logs.append(f"  Failed to load contract: {e}")
                state["errors"].append(str(e))

        state["logs"] = logs
        state["inputs"] = inputs
        return state

    # 节点2: LLM 生成实现方案
    def llm_impl(state: ImplCodingState) -> ImplCodingState:
        t = state["task"]
        logs = state.get("logs", []).copy()
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
{state.get('contract', '(No Contract)')}
"""

        try:
            response = llm_tools.call_llm(
                profile=t.llm_profile or "default",
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
            logs.append(f"  Generated {len(code_changes)} file(s)")
            logs.append(f"  Tokens used: {response.tokens_used}")

        except Exception as e:
            logs.append(f"  LLM call failed: {e}")
            state["errors"].append(str(e))

        state["logs"] = logs
        return state

    # 节点3: 应用更改（带安全边界）
    def apply_changes(state: ImplCodingState) -> ImplCodingState:
        t = state["task"]
        logs = state.get("logs", []).copy()
        logs.append("[apply_changes] Applying code changes...")

        repo_root = t.inputs.get("repo_workspace", ".")
        workspace_root = t.workspace_root or repo_root
        allowed_patterns = t.allowed_write_patterns or []

        for rel_path, content in state.get("code_changes", {}).items():
            try:
                # 使用安全路径拼接
                from ..tools.security import safe_join
                abs_path = safe_join(repo_root, rel_path)
                if abs_path is None:
                    logs.append(f"  Security: Path traversal attempt: {rel_path}")
                    state["errors"].append(f"Path traversal: {rel_path}")
                    continue

                # 写入文件（带安全检查）
                fs_tools.write_file(
                    abs_path,
                    content,
                    workspace_root=workspace_root,
                    allowed_patterns=allowed_patterns,
                )
                logs.append(f"  Written: {abs_path}")

            except Exception as e:
                logs.append(f"  Failed to write {rel_path}: {e}")
                state["errors"].append(str(e))

        state["logs"] = logs
        return state

    # 节点4: 构建结果
    def build_result(state: ImplCodingState) -> ImplCodingState:
        t = state["task"]
        logs = state.get("logs", []).copy()

        # 收集 artifacts
        artifacts = {}
        for logical_name, real_path in t.outputs.items():
            from pathlib import Path
            if Path(real_path).exists():
                artifacts[logical_name] = real_path

        # 决定最终状态
        errors = state.get("errors", [])
        status = TaskStatus.SUCCESS if not errors else TaskStatus.FAILED
        message = "Implementation completed successfully" if not errors else f"Implementation failed with {len(errors)} error(s)"

        state["exec_result"] = ExecutionResult(
            task_id=t.task_id,
            status=status,
            message=message,
            artifacts=artifacts,
            logs=logs,
            error_details="\n".join(errors) if errors else None,
            metrics={
                "files_written": len(state.get("code_changes", {})),
                "error_count": len(errors),
            },
            completed_at=__import__("datetime").datetime.now(),
        )

        return state

    # 添加节点
    graph.add_node("load_inputs", load_inputs)
    graph.add_node("llm_impl", llm_impl)
    graph.add_node("apply_changes", apply_changes)
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

### 2. `unit_test.py` Graph（简单测试 Graph）

#### `lee_runtime/executor/graphs/unit_test.py`

```python
"""
单元测试任务 Graph (l3.test.unit)

MVP 版本：简单的测试执行 Graph。
"""

from typing import Dict, Any
from langgraph.graph import StateGraph, END

from ..types import (
    ExecutorTaskSpec,
    ExecutionResult,
    TaskStatus,
    UnitTestState,
)
from ..tools import shell_tools, fs_tools


def build_unit_test_graph(task: ExecutorTaskSpec) -> Any:
    """
    构建单元测试任务 LangGraph

    Args:
        task: 任务规格

    Returns:
        编译后的 LangGraph
    """
    graph = StateGraph(UnitTestState)

    # 节点1: 加载测试配置
    def load_config(state: UnitTestState) -> UnitTestState:
        t = state["task"]
        logs = state.get("logs", []).copy()
        logs.append("[load_config] Loading test configuration...")

        # 获取测试命令
        test_command = t.params.get("test_command", "pytest -q")
        state["test_command"] = test_command
        logs.append(f"  Test command: {test_command}")

        # 加载测试配置文件（如果有）
        if "test_config" in t.inputs:
            try:
                import yaml
                config_path = t.inputs["test_config"]
                with open(config_path) as f:
                    state["test_config"] = yaml.safe_load(f)
                logs.append(f"  Loaded config from {config_path}")
            except Exception as e:
                logs.append(f"  Failed to load config: {e}")

        state["logs"] = logs
        return state

    # 节点2: 执行测试
    def run_tests(state: UnitTestState) -> UnitTestState:
        t = state["task"]
        logs = state.get("logs", []).copy()
        logs.append("[run_tests] Running tests...")

        cwd = t.inputs.get("repo_workspace", ".")
        test_command = state["test_command"]

        try:
            result = shell_tools.run_shell(
                test_command,
                cwd=cwd,
                timeout=t.timeout_seconds,
            )

            state["test_results"] = {
                "exit_code": result.exit_code,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "duration": result.duration_seconds,
            }

            logs.append(f"  Exit code: {result.exit_code}")
            logs.append(f"  Duration: {result.duration_seconds:.2f}s")

            if result.exit_code == 0:
                logs.append("  Tests passed!")
            else:
                logs.append("  Tests failed!")
                state["errors"].append(f"Tests failed with exit code {result.exit_code}")

        except Exception as e:
            logs.append(f"  Test execution failed: {e}")
            state["errors"].append(str(e))

        state["logs"] = logs
        return state

    # 节点3: 生成测试报告
    def generate_report(state: UnitTestState) -> UnitTestState:
        t = state["task"]
        logs = state.get("logs", []).copy()
        logs.append("[generate_report] Generating test report...")

        # 生成 Markdown 报告
        test_results = state.get("test_results", {})
        report = f"# Test Report\n\n"
        report += f"**Exit Code:** {test_results.get('exit_code', 'N/A')}\n\n"
        report += f"**Duration:** {test_results.get('duration', 0):.2f}s\n\n"
        report += f"## Output\n\n```\n{test_results.get('stdout', '')}\n```\n\n"

        if test_results.get("stderr"):
            report += f"## Errors\n\n```\n{test_results['stderr']}\n```\n\n"

        state["test_report"] = report

        # 写入报告文件
        if "test_report_human" in t.outputs:
            report_path = t.outputs["test_report_human"]
            try:
                fs_tools.write_file(report_path, report)
                logs.append(f"  Written report to {report_path}")
            except Exception as e:
                logs.append(f"  Failed to write report: {e}")

        state["logs"] = logs
        return state

    # 节点4: 构建结果
    def build_result(state: UnitTestState) -> UnitTestState:
        t = state["task"]
        logs = state.get("logs", []).copy()

        errors = state.get("errors", [])
        status = TaskStatus.SUCCESS if not errors else TaskStatus.FAILED

        # 收集 artifacts
        artifacts = {}
        for logical_name, real_path in t.outputs.items():
            from pathlib import Path
            if Path(real_path).exists():
                artifacts[logical_name] = real_path

        state["exec_result"] = ExecutionResult(
            task_id=t.task_id,
            status=status,
            message="Tests completed successfully" if not errors else "Tests failed",
            artifacts=artifacts,
            logs=logs,
            error_details="\n".join(errors) if errors else None,
            metrics=state.get("test_results", {}),
            completed_at=__import__("datetime").datetime.now(),
        )

        return state

    # 添加节点
    graph.add_node("load_config", load_config)
    graph.add_node("run_tests", run_tests)
    graph.add_node("generate_report", generate_report)
    graph.add_node("build_result", build_result)

    # 连接图
    graph.set_entry_point("load_config")
    graph.add_edge("load_config", "run_tests")
    graph.add_edge("run_tests", "generate_report")
    graph.add_edge("generate_report", "build_result")
    graph.add_edge("build_result", END)

    return graph.compile()
```

---

## 📋 MVP 实现路线图

### Phase A：打通最小链路（无 LLM / 单一 graph）

**目标：** 验证 L2 → L3 → L4 调用链路能跑通

- [ ] 实现核心类型 (`types.py`)
  - [ ] `ExecutorTaskSpec`
  - [ ] `ExecutionResult`
  - [ ] `BaseState` / `UnitTestState` TypedDict
- [ ] 实现 LangGraph Runner (`langgraph_runner.py`)
  - [ ] `run_task` 同步版本
- [ ] 实现注册表 (`registry.py`)
  - [ ] 注册 `l3.test.unit`
- [ ] 实现工具层（最小集）
  - [ ] `shell_tools.py` (run_shell, run_pytest)
  - [ ] `fs_tools.py` (read_file, write_file)
  - [ ] `security.py` (safe_join, validate_write_operation)
- [ ] 实现 `unit_test.py` Graph
  - [ ] 加载配置 -> 执行测试 -> 生成报告 -> 构建结果
- [ ] 在 Orchestrator 中集成
  - [ ] 添加 `execute_step_with_executor` 函数
  - [ ] 挑一个 step（如 `p08_03_test`）改成用 executor 跑
- [ ] 测试：从 CLI 把单元测试执行跑通

---

### Phase B：接入 LLM + 实现 `l3.impl.coding`

**目标：** 验证 LLM 调用和代码生成流程

- [ ] 实现 `llm_tools.py`
  - [ ] `call_llm`（仅 Anthropic，不带 tools）
  - [ ] 实现 Profile 加载器 (`profiles/loader.py`)
- [ ] 实现 `impl_coding.py` Graph
  - [ ] 加载输入 -> LLM 生成 -> 应用更改 -> 构建结果
  - [ ] **只写一个固定路径的 demo.py**，不要一上来就允许多文件任意路径
- [ ] 测试：用 demo repo 跑几次，验证 PRD + Design → LLM → 写文件 → ExecutionResult

---

### Phase C：完善文件路径安全

**目标：** 确保所有文件操作都有安全边界

- [ ] 在 `ExecutorTaskSpec` 中增加 `workspace_root` 字段
- [ ] 在 `fs_tools.write_file` 中集成安全检查
- [ ] 在所有 Graph 中使用安全路径拼接
- [ ] 添加安全边界测试（路径穿越攻击场景）

---

### Phase D：[未来] 再说 code_review / acceptance_check

等 A/B/C 稳定后再做这两块，否则 executor 复杂度暴增。

---

## 🔗 与 Orchestrator 集成（修正版）

```python
"""
flowcore/orchestrator/engine_commands.py 中添加 Executor 调用
"""

from pathlib import Path
import yaml
from lee_runtime.executor.types import ExecutorTaskSpec, ExecutionResult, TaskStatus
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
    inputs = _resolve_inputs(project_dir, exec_ctx.get("inputs", {}))
    outputs = _resolve_outputs(project_dir, exec_ctx.get("outputs", {}))

    # 5. [NEW] 解析安全边界配置
    workspace_root = exec_ctx.get("workspace_root", project_dir)
    allowed_write_patterns = exec_ctx.get("allowed_write_patterns", [])

    # 6. 构造 ExecutorTaskSpec
    task = ExecutorTaskSpec(
        task_id=step_id,
        task_type=task_type,
        inputs=inputs,
        outputs=outputs,
        llm_profile=llm_profile,
        params=exec_ctx.get("params", {}),
        workspace_root=workspace_root,
        allowed_write_patterns=allowed_write_patterns,
    )

    # 7. 调用 Executor
    result = run_task(task)

    # 8. 处理结果
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
    """将 agent/skill 映射到 task_type（回退逻辑）"""
    # 简化映射规则
    mapping = {
        # 实现类
        ("implementation_executor", "impl"): "l3.impl.coding",
        ("tech_lead", "coding"): "l3.impl.coding",

        # 测试类
        ("test_engineer", "test"): "l3.test.unit",
        ("qa_engineer", "test"): "l3.test.unit",
    }

    # 尝试精确匹配
    if agent and skill:
        key = (agent, skill)
        if key in mapping:
            return mapping[key]

    # 尝试 skill 模糊匹配
    if skill:
        skill_lower = skill.lower()
        if "impl" in skill_lower or "coding" in skill_lower:
            return "l3.impl.coding"
        elif "test" in skill_lower or "unit" in skill_lower:
            return "l3.test.unit"

    # 默认
    return "l3.impl.coding"


def _resolve_inputs(project_dir: str, inputs_config: dict) -> dict:
    """解析输入配置为真实路径"""
    result = {}
    for logical_name, path_spec in inputs_config.items():
        # 简化处理：如果是绝对路径直接使用，否则拼接项目目录
        if Path(path_spec).is_absolute():
            result[logical_name] = path_spec
        else:
            result[logical_name] = str(Path(project_dir) / path_spec)
    return result


def _resolve_outputs(project_dir: str, outputs_config: dict) -> dict:
    """解析输出配置为真实路径"""
    return _resolve_inputs(project_dir, outputs_config)
```

---

## 📝 审查清单（MVP 版）

### 设计阶段（MVP）

- [x] GraphState 类型简化为 TypedDict
- [x] 时间类型统一为 datetime
- [x] 移除伪异步 run_task_async
- [x] 添加安全边界工具
- [x] 修复工具层 bug（import、SDK 调用）
- [x] 简化 base helper（让每个 graph 独立实现）

### Phase A 检查点

- [ ] 类型定义正确（ExecutorTaskSpec, ExecutionResult, BaseState）
- [ ] Runner 能正确调用 Graph Builder
- [ ] unit_test Graph 能执行 pytest 并生成报告
- [ ] Orchestrator 能成功调用 Executor

### Phase B 检查点

- [ ] llm_tools 能调用 Anthropic API
- [ ] impl_coding Graph 能生成代码并写入文件
- [ ] 生成的代码文件路径在安全边界内

### Phase C 检查点

- [ ] 所有文件操作都有安全边界检查
- [ ] 路径穿越攻击被正确拦截
- [ ] workspace_root 和 allowed_write_patterns 正确生效

---

## 🔗 相关文档

- [04-executor-langgraph-architecture.md](./04-executor-langgraph-architecture.md) - 完整版设计
- [01-功能与用法手册.md](./01-功能与用法手册.md)
- [02-软件架构文档.md](./02-软件架构文档.md)
- [03-缺陷与改进方向.md](./03-缺陷与改进方向.md)

---

## 📊 附录：workflow.yaml 示例（带安全边界）

```yaml
kind: workflow
id: workflow.dev.development_pipeline
name: 开发流水线
version: '1.0'

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
      # [NEW] 安全边界配置
      workspace_root: "@output"
      allowed_write_patterns:
        - "src/**/*.py"
        - "tests/**/*.py"
        - "*.md"
      params:
        llm_temperature: 0.3
    depends_on:
      - p08_03_design

  - id: p08_03_test
    name: 单元测试
    agent: qa_engineer
    execution_context:
      task_type: l3.test.unit
      inputs:
        repo_workspace: "@output"
      outputs:
        test_report_human: "@output/test_report.md"
      params:
        test_command: "pytest -q"
      # 测试步骤不需要写入权限
      workspace_root: "@output"
      allowed_write_patterns: []
    depends_on:
      - p08_03_impl
```

---

## 🎯 下一步行动

1. **评审 MVP 设计** - 确认 MVP 范围和实现优先级
2. **开始 Phase A 实现** - 打通最小链路
3. **Phase B 实现** - 接入 LLM 和代码生成
4. **Phase C 实现** - 完善安全边界
5. **迭代优化** - 根据 A/B/C 阶段反馈调整设计
