---
title: LEE Orchestrator v3.0 - Skeleton Progress
author: LEE Team
date: 2026-01-29
version: 1.0
last_updated: 2026-02-19
---

# LEE Orchestrator v3.0 - Skeleton Progress

> **Date**: 2026-01-27
> **Status**: ✅ Skeleton Completed
> **Next**: Stage 1 Implementation

---

## ✅ Completed Files

### 1. Storage Layer

**`src/lee/orchestrator/storage/models_v3.py`**
- Unified data model for L1/L2/L3 workflows
- Enums: `WorkflowLevel`, `WorkflowStatus`, `TaskExecutionStatus`
- Dataclasses: `WorkflowInstance`, `TaskExecution`, `Template`, `Step`
- State classes: `WorkflowState`, `StepResult`, `ExecutionSummary`
- ✅ All dataclass field ordering issues fixed
- ✅ All tests passing

**`src/lee/orchestrator/storage/sqlite_store_v3.py`**
- Unified SQLite storage layer
- Single `workflow_instances` table for all levels
- CRUD operations for workflows, executions, templates
- Parent-child relationship support via `parent_id`
- Indexes on `parent_id`, `status`, `level`
- ✅ All tests passing

**`tests/test_storage_v3.py`**
- Comprehensive test suite
- Tests: CRUD, three-layer hierarchy, status updates
- ✅ All 3 test suites passing (100%)

### 2. Execution Layer

**`src/lee/orchestrator/execution/orchestrator_v3.py`**
- Core Orchestrator skeleton (interface definitions)
- Classes:
  - `TemplateManager`: Template loading and caching
  - `WorkflowStateMachine`: State transitions
  - `WorkflowExecutor`: Step execution
  - `Orchestrator`: Core scheduler with 8 responsibilities
  - `ExecutorFactory`: Executor creation
  - `BaseExecutor`: Abstract base class
- Status: Skeleton only, TODO markers for implementation

**`src/lee/orchestrator/execution/state_machine_v3.py`**
- State machine implementation (skeleton)
- `StateTransition`: State transition rules
- `IStateMachine`: State machine interface
- `WorkflowStateMachine`: Full state machine logic
- `GateStateMachine`: Human gate support
- Status: Skeleton only, TODO markers for implementation

**`src/lee/orchestrator/execution/template_manager_v3.py`**
- Template manager implementation (skeleton)
- `TemplateManager`: Load/parse/manage YAML templates
- `TemplateBuilder`: Programmatic template creation
- `BuiltinTemplates`: Common template definitions
- Status: Skeleton only, TODO markers for implementation

---

## 📊 Test Results

```
============================================================
  🚀 LEE Orchestrator v3.0 - 统一存储层测试
============================================================

测试 1: 工作流 CRUD 操作
✅ 创建 L1 Project
✅ 创建 L2 Department
✅ 创建 L3 Task
✅ 读取 L1 Project
✅ 查询子工作流
✅ 更新工作流状态
✅ 更新工作流数据
✅ 获取所有实例: 3 个
✅ 按层级过滤: Project=1, Dept=1, Task=1

测试 2: 任务执行记录
✅ 创建执行记录
✅ 完成工作流
✅ 查询执行记录: 1 条

测试 3: 三层嵌套关系
✅ L1 有 2 个子部门
✅ L2_001 有 2 个子任务

📊 层级结构:
🎯 L1_001 (project) ▶️
  🏢 L2_001 (department) ▶️
    📋 L3_001 (task) ▶️
    📋 L3_002 (task) ⏳
  🏢 L2_002 (department) ⏳

============================================================
  ✅ 所有测试通过！
============================================================
```

---

## 🎯 Next Steps

### Stage 1: Data Model Unification (1-2 days)

**Task 1.1**: Merge models.py
- [ ] Copy `models_v3.py` to `models.py`
- [ ] Remove old models
- [ ] Update imports across codebase

**Task 1.2**: Merge sqlite_store.py
- [ ] Copy `sqlite_store_v3.py` to `sqlite_store.py`
- [ ] Remove old store
- [ ] Update imports

**Task 1.3**: Create migration script
- [ ] Script to migrate old data to new schema
- [ ] Test migration with existing workflows

### Stage 2: Executor Unification (1 day)

**Task 2.1**: Keep new executors
- [ ] Verify `llm_executor.py` works
- [ ] Verify `metagpt_executor.py` works
- [ ] Verify `executors.py` proxy pattern

**Task 2.2**: Remove old executors
- [ ] Remove `flowcore/engines/` directory
- [ ] Update imports

### Stage 3: State Machine Implementation (2-3 days)

**Task 3.1**: Implement WorkflowStateMachine
- [ ] Implement `get_current_state()`
- [ ] Implement `can_start_step()`
- [ ] Implement `start_step()`
- [ ] Implement `complete_step()`
- [ ] Implement `fail_step()`
- [ ] Implement `pause_workflow()`
- [ ] Implement `resume_workflow()`
- [ ] Implement `get_ready_steps()`

**Task 3.2**: Implement TemplateManager
- [ ] Implement `load_yaml_template()`
- [ ] Implement `get_template()`
- [ ] Implement `get_steps()`
- [ ] Implement `get_departments()`
- [ ] Implement `get_tasks()`
- [ ] Implement `validate_template()`

**Task 3.3**: Write tests
- [ ] Test state transitions
- [ ] Test template loading
- [ ] Test ready steps calculation

### Stage 4: Orchestrator Core (3-5 days)

**Task 4.1**: Implement Orchestrator
- [ ] Implement `create_workflow()`
- [ ] Implement `spawn_workflow()`
- [ ] Implement `get_state()`
- [ ] Implement `run_step()`
- [ ] Implement `run_until_blocked()`
- [ ] Implement `pause()` and `resume()`

**Task 4.2**: Integration
- [ ] Connect StateMachine
- [ ] Connect TemplateManager
- [ ] Connect ExecutorFactory

**Task 4.3**: Testing
- [ ] End-to-end workflow test
- [ ] L1→L2→L3 nesting test
- [ ] Human gate test

---

## 📁 File Structure

```
src/lee/orchestrator/
├── storage/
│   ├── models_v3.py          ✅ Unified data model
│   └── sqlite_store_v3.py    ✅ Unified storage
├── execution/
│   ├── orchestrator_v3.py    ✅ Core skeleton
│   ├── state_machine_v3.py   ✅ State machine skeleton
│   ├── template_manager_v3.py ✅ Template manager skeleton
│   ├── executors.py          ✅ Existing (keep)
│   ├── llm_executor.py       ✅ Existing (keep)
│   └── metagpt_executor.py   ✅ Existing (keep)
tests/
└── test_storage_v3.py        ✅ All tests passing
docs/architecture/
├── LEE_Orchestrator_v3_Architecture.md
├── LEE_Orchestrator_v3_Diagrams.md
├── LEE_Orchestrator_v3_Implementation_Plan.md
└── README.md
```

---

## 🎓 Design Principles Verified

✅ **Unified Three-Layer Model**
- Single `WorkflowInstance` model for L1/L2/L3
- Distinguished by `level` and `parent_id` fields
- Single `workflow_instances` table

✅ **SQLite as Single Source of Truth**
- All state stored in SQLite
- No in-memory state
- Transaction support

✅ **Clear Power Boundaries**
- Orchestrator > Executor > Tool
- Orchestrator doesn't think, only decides
- Executor doesn't access DB

✅ **Template-Driven Execution**
- YAML-based workflow definitions
- Step dependencies
- Support for agent/skill/human_gate/marker

---

## 🚀 Quick Start

### Run Tests

```bash
python tests/test_storage_v3.py
```

### Create a Workflow (Example)

```python
from lee.orchestrator.storage.models_v3 import *
from lee.orchestrator.storage.sqlite_store_v3 import SQLiteStore

# Initialize store
store = SQLiteStore(":memory:")
await store.connect()

# Create L1 Project
project = WorkflowInstance(
    id="proj_001",
    level=WorkflowLevel.PROJECT,
    template_id="simple_project",
    status=WorkflowStatus.PENDING,
    data={"project_name": "My Project"},
)
await store.create_workflow(project)

# Create L2 Department
dept = WorkflowInstance(
    id="dept_001",
    level=WorkflowLevel.DEPARTMENT,
    parent_id="proj_001",
    template_id="dept_qa",
    status=WorkflowStatus.PENDING,
    data={"dept_name": "QA"},
)
await store.create_workflow(dept)

# Query children
children = await store.get_children("proj_001")
print(f"Found {len(children)} departments")
```

---

**Status**: ✅ Skeleton complete, ready for Stage 1 implementation
**Estimated time to MVP**: 7-10 days
