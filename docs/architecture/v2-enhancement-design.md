---
title: Orchestrator v2.0 Enhancement Design
author: LEE Team
date: 2026-01-29
version: 1.0
last_updated: 2026-02-19
---

# Orchestrator v2.0 Enhancement Design
# 支持Testing Workflow v2.0的技术设计

> **版本:** v2.0
> **创建日期:** 2026-01-15
> **目标:** 支持事件驱动、Bug子流程、多轮循环测试

---

## 📋 需求概述

Testing Workflow v2.0 引入了以下核心特性，需要Orchestrator支持：

1. **事件驱动架构** - 测试失败触发Bug子流程
2. **子流程Spawning** - 并行运行多个Bug契约工作流
3. **多轮循环控制** - 最多10轮测试循环
4. **外部等待** - 等待Bug修复完成
5. **模板变量扩展** - 支持 `{bug_id}`, `{round_num}` 等变量

---

## 🏗️ 当前Orchestrator架构

### 已有功能

从 `state_machine.py` 分析，已支持：

✅ **循环支持**
```python
@dataclass
class LoopContext:
    loop_id: str
    condition: str
    max_iterations: int
    current_iteration: int = 0
    body_steps: List[str]
```

✅ **外部等待**
```python
class StepState(Enum):
    WAITING_EXTERNAL = "waiting_external"

class StepStatus:
    waiting_for_event: Optional[str] = None
    wait_timeout: Optional[str] = None
```

✅ **门禁管理**
```python
@dataclass
class GateStatus:
    gate_id: str
    type: str  # human / auto
    status: str  # pending / approved / rejected
```

### 缺失功能

❌ **事件总线** - 发送和接收事件
❌ **子流程管理器** - Spawn和跟踪子工作流
❌ **Bug契约工作流** - 专门处理Bug生命周期
❌ **模板变量解析** - 动态替换 `{bug_id}` 等变量

---

## 🎯 设计方案

### Feature 1: 事件总线 (Event Bus)

**目的:** 主流程和Bug子流程通过事件通信

**设计:**

```python
# orchestrator/core/event_bus.py

from dataclasses import dataclass
from typing import Dict, List, Callable, Any
from datetime import datetime
from enum import Enum

class EventType(Enum):
    """事件类型"""
    TEST_FAILURE = "test_failure"
    BUG_CREATED = "bug_created"
    BUG_TRIAGED = "bug_triaged"
    BUG_FIXED = "bug_fixed"
    BUG_VERIFIED = "bug_verified"
    BUG_CLOSED = "bug_closed"
    BUG_BLOCKED_HUMAN = "bug_blocked_human"
    BUG_BLOCKED_PM = "bug_blocked_pm"

@dataclass
class Event:
    """事件对象"""
    type: EventType
    payload: Dict[str, Any]
    source_workflow: str
    timestamp: str
    event_id: str

class EventBus:
    """事件总线 - 单例模式"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._handlers = {}
            cls._instance._event_log = []
        return cls._instance

    def subscribe(self, event_type: EventType, handler: Callable):
        """订阅事件"""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def publish(self, event: Event):
        """发布事件"""
        self._event_log.append(event)

        if event.type in self._handlers:
            for handler in self._handlers[event.type]:
                handler(event)

    def get_events(self, event_type: Optional[EventType] = None) -> List[Event]:
        """获取事件历史"""
        if event_type is None:
            return self._event_log
        return [e for e in self._event_log if e.type == event_type]
```

**使用方式:**

```python
# 主流程: 发布test_failure事件
event_bus = EventBus()
event = Event(
    type=EventType.TEST_FAILURE,
    payload={
        "test_case_id": "F-BASE-002",
        "error_message": "...",
        "trace_id": "...",
        "round_id": "TSTR-0001"
    },
    source_workflow="test-main-pipeline",
    timestamp=datetime.now().isoformat(),
    event_id="evt-001"
)
event_bus.publish(event)

# Bug子流程管理器: 订阅test_failure事件
def handle_test_failure(event: Event):
    spawn_bug_workflow(event.payload)

event_bus.subscribe(EventType.TEST_FAILURE, handle_test_failure)
```

---

### Feature 2: 子流程管理器 (Subprocess Manager)

**目的:** 管理并行运行的Bug契约工作流

**设计:**

```python
# orchestrator/core/subprocess_manager.py

from dataclasses import dataclass
from typing import Dict, List, Optional
from pathlib import Path
import subprocess
import json

@dataclass
class SubprocessInstance:
    """子流程实例"""
    subprocess_id: str          # 子流程唯一ID
    workflow_type: str          # bug-sub-workflow
    entity_id: str              # BUG-2026-0001
    entity_path: Path           # bugs/BUG-2026-0001.contract.yaml
    parent_workflow: str        # test-main-pipeline
    status: str                 # running / completed / failed
    started_at: str
    completed_at: Optional[str] = None
    pid: Optional[int] = None   # 进程ID (如果后台运行)

class SubprocessManager:
    """子流程管理器 - 单例模式"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._subprocesses = {}  # Dict[subprocess_id, SubprocessInstance]
        return cls._instance

    def spawn(self,
              workflow_path: Path,
              entity_path: Path,
              parent_workflow: str,
              async_mode: bool = True) -> str:
        """启动子流程

        Args:
            workflow_path: 子工作流YAML路径
            entity_path: 实体契约文件路径 (如 bugs/BUG-XXX.yaml)
            parent_workflow: 父工作流ID
            async_mode: 是否异步执行

        Returns:
            subprocess_id: 子流程唯一ID
        """
        subprocess_id = f"sub-{datetime.now().strftime('%Y%m%d%H%M%S')}-{entity_path.stem}"

        instance = SubprocessInstance(
            subprocess_id=subprocess_id,
            workflow_type="bug-sub-workflow",
            entity_id=entity_path.stem,
            entity_path=entity_path,
            parent_workflow=parent_workflow,
            status="running",
            started_at=datetime.now().isoformat()
        )

        if async_mode:
            # 后台异步执行
            cmd = [
                "python", "-m", "orchestrator",
                "init", str(entity_path.parent),
                "--workflow", str(workflow_path),
                "--entity", str(entity_path)
            ]
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            instance.pid = proc.pid
        else:
            # 同步执行 (测试用)
            # 直接调用 orchestrator API
            pass

        self._subprocesses[subprocess_id] = instance
        return subprocess_id

    def get_status(self, subprocess_id: str) -> Optional[SubprocessInstance]:
        """获取子流程状态"""
        return self._subprocesses.get(subprocess_id)

    def list_by_parent(self, parent_workflow: str) -> List[SubprocessInstance]:
        """列出父工作流的所有子流程"""
        return [s for s in self._subprocesses.values()
                if s.parent_workflow == parent_workflow]

    def wait_for(self, subprocess_id: str, timeout: Optional[int] = None):
        """等待子流程完成"""
        instance = self._subprocesses.get(subprocess_id)
        if instance and instance.pid:
            # 等待进程结束
            import os
            import time
            start = time.time()
            while True:
                try:
                    os.kill(instance.pid, 0)  # 检查进程是否存在
                    if timeout and (time.time() - start) > timeout:
                        raise TimeoutError(f"Subprocess {subprocess_id} timeout")
                    time.sleep(1)
                except OSError:
                    # 进程已结束
                    instance.status = "completed"
                    instance.completed_at = datetime.now().isoformat()
                    break
```

**使用方式:**

```python
# 测试失败时，spawn Bug子流程
subprocess_mgr = SubprocessManager()

bug_workflow = Path("ai-spec/specs/org/testing/workflows/bug-sub-workflow/v1/workflow.yaml")
bug_contract = Path("bugs/BUG-2026-0001.contract.yaml")

subprocess_id = subprocess_mgr.spawn(
    workflow_path=bug_workflow,
    entity_path=bug_contract,
    parent_workflow="test-main-pipeline-run-001",
    async_mode=True
)

# 主流程继续执行，不等待Bug修复
# ...

# 在TRIAGE_SYNC点，检查所有Bug状态
all_bugs = subprocess_mgr.list_by_parent("test-main-pipeline-run-001")
for bug in all_bugs:
    status = subprocess_mgr.get_status(bug.subprocess_id)
    print(f"{bug.entity_id}: {status.status}")
```

---

### Feature 3: Bug契约工作流解析器

**目的:** 解析Bug契约的状态机，支持独立流转

**设计:**

在 `workflow_parser.py` 中扩展：

```python
# orchestrator/core/workflow_parser.py (扩展)

class BugWorkflowParser:
    """Bug契约工作流解析器"""

    @staticmethod
    def parse_bug_state_machine(workflow_yaml: dict) -> dict:
        """解析Bug状态机"""
        state_machine = workflow_yaml.get("state_machine", {})

        # 解析状态转换规则
        transitions = {}
        for state_name, state_transitions in state_machine.get("transitions", {}).items():
            transitions[state_name] = []
            for trans in state_transitions:
                transitions[state_name].append({
                    "to": trans["to"],
                    "trigger": trans["trigger"],
                    "condition": trans.get("condition"),
                    "required_fields": trans.get("required_fields", [])
                })

        return {
            "states": state_machine.get("states", []),
            "transitions": transitions
        }

    @staticmethod
    def validate_transition(bug_contract: dict,
                           from_state: str,
                           to_state: str,
                           transitions: dict) -> Tuple[bool, Optional[str]]:
        """验证状态转换是否合法

        Returns:
            (is_valid, error_message)
        """
        if from_state not in transitions:
            return False, f"Invalid from_state: {from_state}"

        valid_transitions = [t for t in transitions[from_state] if t["to"] == to_state]
        if not valid_transitions:
            return False, f"No valid transition from {from_state} to {to_state}"

        # 检查required_fields
        trans = valid_transitions[0]
        for field in trans.get("required_fields", []):
            if not get_nested_field(bug_contract, field):
                return False, f"Missing required field: {field}"

        return True, None
```

---

### Feature 4: 模板变量解析器

**目的:** 支持动态变量 `{bug_id}`, `{round_num}` 等

**设计:**

```python
# orchestrator/core/template_resolver.py

import re
from typing import Dict, Any

class TemplateResolver:
    """模板变量解析器"""

    def __init__(self, context: Dict[str, Any]):
        """初始化

        Args:
            context: 变量上下文，如 {"bug_id": "BUG-2026-0001", "round_num": 3}
        """
        self.context = context

    def resolve(self, template: str) -> str:
        """解析模板字符串

        Examples:
            resolve("bugs/{bug_id}.yaml") -> "bugs/BUG-2026-0001.yaml"
            resolve("round-{round_num}/report.md") -> "round-003/report.md"
        """
        pattern = r'\{(\w+)\}'

        def replacer(match):
            var_name = match.group(1)
            value = self.context.get(var_name)

            if value is None:
                raise ValueError(f"Template variable '{var_name}' not found in context")

            # 数字格式化 (如 round_num -> 003)
            if isinstance(value, int) and var_name.endswith("_num"):
                return f"{value:03d}"

            return str(value)

        return re.sub(pattern, replacer, template)

    def resolve_dict(self, template_dict: Dict) -> Dict:
        """递归解析字典中的所有模板字符串"""
        result = {}
        for key, value in template_dict.items():
            if isinstance(value, str):
                result[key] = self.resolve(value)
            elif isinstance(value, dict):
                result[key] = self.resolve_dict(value)
            elif isinstance(value, list):
                result[key] = [self.resolve(v) if isinstance(v, str) else v for v in value]
            else:
                result[key] = value
        return result
```

**使用方式:**

```python
# 在workflow执行时注入上下文
context = {
    "bug_id": "BUG-2026-0001",
    "round_num": 3,
    "version": "v1.1.0"
}

resolver = TemplateResolver(context)

# 解析输出路径
output_path = resolver.resolve("test-rounds/round-{round_num}/bugs/{bug_id}/debug-report.json")
# -> "test-rounds/round-003/bugs/BUG-2026-0001/debug-report.json"
```

---

### Feature 5: 循环控制增强

**目的:** 支持多轮测试循环 (最多10轮)

**现有基础:**
`LoopContext` 已存在，需要增强：

```python
# orchestrator/core/state_machine.py (增强)

class StateMachine:

    def evaluate_loop_condition(self, loop_ctx: LoopContext, workflow_state: Dict) -> bool:
        """评估循环条件

        支持的条件表达式:
        - "open_p0_count > 0"
        - "open_p1_count > p1_threshold"
        - "current_iteration < max_iterations"
        """
        # 从workflow_state中获取变量
        variables = {
            "open_p0_count": self._count_bugs(workflow_state, severity="P0", status_not_in=["closed"]),
            "open_p1_count": self._count_bugs(workflow_state, severity="P1", status_not_in=["verified", "closed"]),
            "p1_threshold": 3,
            "current_iteration": loop_ctx.current_iteration,
            "max_iterations": loop_ctx.max_iterations
        }

        # 安全的条件求值
        try:
            result = eval(loop_ctx.condition, {"__builtins__": {}}, variables)
            return bool(result)
        except Exception as e:
            raise ValueError(f"Invalid loop condition: {loop_ctx.condition}, error: {e}")

    def _count_bugs(self, workflow_state: Dict, severity: str, status_not_in: List[str]) -> int:
        """统计Bug数量"""
        bugs_dir = Path(workflow_state.get("working_dir")) / "bugs"
        count = 0

        if bugs_dir.exists():
            for bug_file in bugs_dir.glob("*.yaml"):
                with open(bug_file) as f:
                    bug = yaml.safe_load(f)
                    if bug.get("severity") == severity and bug.get("status") not in status_not_in:
                        count += 1

        return count
```

---

## 📝 实现计划

### Phase 1: 基础设施 (2天)

1. ✅ 创建 `event_bus.py`
2. ✅ 创建 `subprocess_manager.py`
3. ✅ 创建 `template_resolver.py`
4. ✅ 扩展 `workflow_parser.py` - 支持Bug状态机
5. ✅ 扩展 `state_machine.py` - 循环条件求值

### Phase 2: CLI集成 (1天)

```bash
# 新增命令
python -m orchestrator spawn-subprocess --workflow bug-sub-workflow.yaml --entity bugs/BUG-XXX.yaml
python -m orchestrator list-subprocesses --parent <parent_run_id>
python -m orchestrator event-log --type test_failure
```

### Phase 3: 测试验证 (1天)

1. 单元测试 - EventBus, SubprocessManager, TemplateResolver
2. 集成测试 - 完整Testing Workflow v2.0流程
3. 性能测试 - 100个并发Bug子流程

### Phase 4: 文档更新 (0.5天)

1. 更新 `orchestrator/README.md`
2. 添加使用示例
3. API文档

---

## 🔒 向后兼容性

**保证:**
- 现有workflow.yaml格式100%兼容
- 不破坏现有CLI命令
- 新功能通过可选字段启用

**新特性开关:**

```yaml
# workflow.yaml
features:
  event_driven: true        # 启用事件驱动
  subprocess_spawning: true # 启用子流程spawning
  template_variables: true  # 启用模板变量
```

---

## 📊 性能指标

**目标:**
- 事件发布延迟 < 10ms
- 子流程spawn时间 < 500ms
- 支持100+并发Bug子流程
- 模板解析性能 < 1ms

---

## 🚀 部署计划

1. **Dev环境验证** (1天)
2. **Staging环境测试** (1天)
3. **Production灰度发布** (逐步放量)

---

**总工期:** 5天
**风险:** 低 (基于现有架构扩展)
**优先级:** P0 (阻塞Testing Workflow v2.0)

---

**文档维护者:** orchestrator-team
**最后更新:** 2026-01-15
**状态:** 设计完成，待实施
