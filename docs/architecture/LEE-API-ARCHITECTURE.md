# LEE Orchestrator API 架构整理方案

> **作者**: LEE Team
> **日期**: 2026-02-21
> **版本**: v1.0.0
> **分类**: 架构文档

## 📋 当前架构分析

### ✅ 已存在的统一 API 层

**文件**: `src/lee/orchestrator/api/__init__.py`

已经提供了完整的 Orchestrator API：

```python
# 核心异步 API 函数
- api_get_state()           # 获取工作流状态
- api_list_ready_steps()    # 列出就绪步骤
- api_run_step()            # 执行指定步骤
- api_next_step()           # 自动执行下一步
- api_create_workflow()     # 创建工作流
- api_run_until_blocked()   # 执行直到阻塞
- api_approve_gate()        # 批准门禁
- api_reject_gate()         # 拒绝门禁
- api_pause_workflow()      # 暂停工作流
- api_resume_workflow()     # 恢复工作流

# 统一处理器
- pm_workflow_handler()      # 统一入口（异步）
- pm_workflow()              # 统一入口（同步）
```

---

## 🎯 正确的架构

```
┌─────────────────────────────────────────────────────────────┐
│                      用户界面层                              │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐          ┌──────────────┐                │
│  │  lee CLI     │          │  lee chat    │                │
│  │  (一次性)     │          │  (交互式)     │                │
│  └──────┬───────┘          └──────┬───────┘                │
│         │                          │                          │
└─────────┼──────────────────────────┼──────────────────────────
          │                          │
          │                          │
┌─────────┼──────────────────────────┼──────────────────────────┐
│         │        统一 API 层        │                          │
├─────────┼──────────────────────────┼──────────────────────────┤
│         │                          │                          │
│  ┌──────▼───────┐          ┌──────▼───────┐                │
│  │ pm_workflow()│          │PM Agent      │                │
│  │ (同步)       │          │Runtime       │                │
│  └──────┬───────┘          └──────┬───────┘                │
│         │                          │                          │
│         └──────────┬───────────────┘                          │
│                    │                                         │
│         ┌──────────▼───────────────┐                        │
│         │  pm_workflow_handler()   │                        │
│         │  (统一异步处理器)         │                        │
│         └──────────┬───────────────┘                        │
│                    │                                         │
└────────────────────┼─────────────────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────────────────┐
│                  Orchestrator 核心                           │
├──────────────────────────────────────────────────────────────┤
│  - api_get_state()                                           │
│  - api_run_step() / api_next_step()                         │
│  - api_create_workflow() / api_run_until_blocked()           │
│  - api_approve_gate() / api_reject_gate()                   │
└──────────────────────────────────────────────────────────────┘
```

---

## 🔧 修复方案

### 问题 1: `api_wrapper.py` 当前实现错误

**当前实现** (错误):
```python
# src/lee/orchestrator/execution/pm_agent/api_wrapper.py

async def _handle_run_workflow(self, decision, context):
    # ❌ 只返回参数，不执行 API
    return APIResponse(
        status="success",
        data={"template_id": template_id},
        action="run_workflow"
    )
```

**应该改为** (正确):
```python
# src/lee/orchestrator/execution/pm_agent/api_wrapper.py

from lee.orchestrator.api import (
    api_create_workflow,
    api_run_until_blocked,
)

async def _handle_run_workflow(self, decision, context):
    template_id = decision.params.params.get("template_id")
    if not template_id:
        template_id = decision.params.workflow_ref

    if not template_id:
        return APIResponse(
            status="error",
            data={},
            error="template_id is required to run workflow",
            action="run_workflow"
        )

    # ✅ 直接调用 Orchestrator API
    create_result = await api_create_workflow(
        project_dir=self.project_dir,
        level="task",
        template_id=template_id,
        parent_id=None,
        data={}
    )

    workflow_id = create_result["workflow_id"]

    run_result = await api_run_until_blocked(
        project_dir=self.project_dir,
        workflow_id=workflow_id,
        max_steps=10
    )

    # ✅ 返回完整结果，不阻塞
    return APIResponse(
        status="success",
        data={
            "workflow_id": workflow_id,
            "template_id": template_id,
            "create_result": create_result,
            "run_result": run_result,
            "message": f"Created and started workflow {workflow_id}"
        },
        action="run_workflow"
    )
```

### 问题 2: `chat.py` 使用 subprocess 是错误的

**当前实现** (错误):
```python
# src/lee/cli/commands/chat.py

async def _handle_with_decision_engine(self, text: str):
    result = await self.runtime.process_input(text, self.session_id)

    cmd = self._build_cli_command(result)

    # ❌ 使用 subprocess 执行 CLI 命令
    proc = await asyncio.create_subprocess_exec(*cmd, ...)
    await proc.wait()  # 阻塞！
```

**应该改为** (正确):
```python
# src/lee/cli/commands/chat.py

async def _handle_with_decision_engine(self, text: str):
    # ✅ process_input 已经调用了 Orchestrator API
    result = await self.runtime.process_input(text, self.session_id)

    # ✅ 只需要格式化和显示结果
    if result['status'] == 'success':
        self._display_result(result['data'])
    else:
        self._display_error(result['error'])

    # ✅ 立即返回，用户可以继续输入
```

---

## 📊 修复清单

### 需要修改的文件

#### 1. `src/lee/orchestrator/execution/pm_agent/api_wrapper.py`

**需要修改的方法**:
- `_handle_run_workflow()` - 恢复 API 调用
- `_handle_create_workflow()` - 确保正确调用 API
- `_handle_next_step()` - 确保正确调用 API
- `_handle_run_step()` - 确保正确调用 API
- `_handle_approve_gate()` - 确保正确调用 API
- `_handle_reject_gate()` - 确保正确调用 API

#### 2. `src/lee/cli/commands/chat.py`

**需要删除的代码**:
- `_build_cli_command()` - 不再需要
- `_stream_subprocess_output()` - 不再需要
- subprocess 相关的所有代码

**需要修改的方法**:
- `_handle_with_decision_engine()` - 简化为只显示结果
- `_display_result_data()` - 增强，显示更丰富的信息

---

## 🎯 最终架构

### `lee chat` 交互流程

```python
用户输入: "在当前目录运行office.workspace-cleanup"

1. chat.py 接收输入
   ↓
2. runtime.process_input()
   ↓
3. decision_engine 处理
   ├→ intent_classifier: run_workflow
   ├→ param_mapper: template_id=office.workspace-cleanup
   ↓
4. api_wrapper._handle_run_workflow()
   ├→ api_create_workflow()  # ✅ 直接调用 API
   ├→ api_run_until_blocked() # ✅ 直接调用 API
   ↓
5. 返回结果到 chat.py
   ↓
6. chat.py 格式化显示
   ↓
7. ✅ 立即返回，用户可以继续输入
```

### `lee cli` 命令流程

```python
命令: lee run office.workspace-cleanup

1. cli/commands/run.py 解析参数
   ↓
2. 调用 pm_workflow_handler()
   ├→ api_create_workflow()
   ├→ api_run_until_blocked()
   ↓
3. 格式化输出
```

---

## ✅ 优点

1. **统一接口** - `lee cli` 和 `lee chat` 使用相同的 API
2. **非阻塞** - `lee chat` 可以立即返回，用户可以继续输入
3. **无进程锁问题** - 在同一进程中执行
4. **代码复用** - Orchestrator API 被所有客户端共享
5. **性能更好** - 无进程启动开销

---

## 📝 实现步骤

1. **恢复 API 调用** - 修改 `api_wrapper.py`
2. **移除 subprocess** - 修改 `chat.py`
3. **测试验证** - 确保 `lee chat` 非阻塞
4. **更新文档** - 记录正确的架构

---

## 🎉 总结

**Orchestrator API 已经存在且设计良好！**

只需要：
1. ✅ 让 `api_wrapper.py` 调用 Orchestrator API
2. ✅ 让 `chat.py` 只负责显示结果
3. ✅ 移除 subprocess 调用

**核心原则**:
- `lee cli` → Orchestrator API (一次性)
- `lee chat` → Orchestrator API (交互式)
- 两者共享同一套 API 层
