# LEE Chat 架构修复方案 - 详细步骤

> **作者**: LEE Team
> **日期**: 2026-02-21
> **版本**: v1.0.0
> **分类**: 修复方案

## 🎯 目标

让 `lee chat` 直接调用 Orchestrator API，而不是通过 subprocess 调用 `lee` CLI 命令。

---

## 📋 当前问题

### 问题 1: `api_wrapper.py` 只返回参数

```python
# src/lee/orchestrator/execution/pm_agent/api_wrapper.py

async def _handle_run_workflow(self, decision, context):
    # ❌ 当前: 只返回参数
    return APIResponse(
        status="success",
        data={"template_id": template_id},
        action="run_workflow"
    )
```

### 问题 2: `chat.py` 使用 subprocess

```python
# src/lee/cli/commands/chat.py

async def _handle_with_decision_engine(self, text: str):
    result = await self.runtime.process_input(text, self.session_id)

    cmd = self._build_cli_command(result)

    # ❌ 当前: 使用 subprocess 执行 CLI 命令
    proc = await asyncio.create_subprocess_exec(*cmd, ...)
    await proc.wait()  # 阻塞！用户无法继续输入
```

---

## ✅ 正确的架构

### 步骤 1: 恢复 `api_wrapper.py` 中的 Orchestrator API 调用

```python
# src/lee/orchestrator/execution/pm_agent/api_wrapper.py

async def _handle_run_workflow(
    self,
    decision: Decision,
    context: Optional[ExecutionContext]
) -> APIResponse:
    """Handle run_workflow action - creates and runs a workflow"""
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

    try:
        # ✅ 导入 Orchestrator API
        from lee.orchestrator.api import (
            api_create_workflow,
            api_run_until_blocked,
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

        # ✅ 返回完整结果
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

    except Exception as e:
        logger.error(f"Failed to run workflow: {e}")
        return APIResponse(
            status="error",
            data={},
            error=str(e),
            action="run_workflow"
        )
```

### 步骤 2: 简化 `chat.py` - 移除 subprocess，只显示结果

```python
# src/lee/cli/commands/chat.py

async def _handle_with_decision_engine(self, text: str):
    """Handle input using Decision Engine - Direct Orchestrator API calls"""
    click.echo(HTML("<pm>🤔 Processing...</pm>"))

    # ✅ process_input 内部已经调用了 Orchestrator API
    result = await self.runtime.process_input(text, self.session_id)

    # Show reasoning
    if 'reasoning' in result and result['reasoning']:
        click.echo()
        click.echo(click.style("🧠 思考过程:", fg='cyan', bold=True))
        click.echo(click.style(f"   {result['reasoning']}", fg='cyan'))
        click.echo()

    # Show action
    if 'action' in result:
        action = result['action']
        click.echo(click.style(f"⚡ 执行动作: {action}", fg='yellow'))

    # Show parameters
    data = result.get('data', {})
    if data:
        if 'template_id' in data:
            click.echo(click.style(f"📦 模板ID: {data['template_id']}", fg='blue'))
        if 'workflow_id' in data:
            click.echo(click.style(f"🔄 工作流ID: {data['workflow_id']}", fg='blue'))
        if 'step_id' in data:
            click.echo(click.style(f"➡️  步骤ID: {data['step_id']}", fg='blue'))
        if 'gate_id' in data:
            click.echo(click.style(f"✅ 网关ID: {data['gate_id']}", fg='blue'))

    click.echo()

    # ✅ 显示结果
    if result['status'] == 'success':
        self._print_success(f"✓ 执行成功: {result.get('action', 'unknown')}")
        self._display_result_data(result.get('data', {}))
    elif result['status'] == 'denied':
        self._print_warning(f"⚠ Permission denied: {result.get('error', 'Unknown reason')}")
    elif result['status'] == 'error':
        error_msg = result.get('error', 'Unknown error')
        self._print_error(f"✗ Error: {error_msg}")

        # Show template hints if template not found
        if 'Template not found' in error_msg or 'template' in error_msg.lower():
            await self._show_available_templates()

    # Show confidence
    if 'confidence' in result:
        confidence = result['confidence']
        confidence_str = f"{confidence:.0%}" if confidence > 0 else "N/A"
        click.echo()
        click.echo(click.style(f"Confidence: {confidence_str}", fg='blue'))

    # ✅ 立即返回，用户可以继续输入
```

### 步骤 3: 删除 `chat.py` 中不需要的方法

删除以下方法（不再需要）:
- `_build_cli_command()` - 不再构建 CLI 命令
- `_stream_subprocess_output()` - 不再使用 subprocess
- `_snapshot_claude_log_offsets()` - Claude 日志相关（可选保留）
- `_iter_claude_log_files()` - Claude 日志相关（可选保留）
- `_stream_claude_runtime_logs()` - Claude 日志相关（可选保留）

### 步骤 4: 增强 `_display_result_data()` 方法

```python
def _display_result_data(self, data: dict):
    """Display result data in user-friendly format"""
    if not data:
        return

    # Display workflow creation result
    if 'workflow_id' in data and 'template_id' in data:
        workflow_id = data['workflow_id']
        template_id = data['template_id']
        click.echo(f"\n✅ 工作流已创建:")
        click.echo(f"   ID: {workflow_id}")
        click.echo(f"   模板: {template_id}")

    # Display run result
    if 'run_result' in data:
        run_result = data['run_result']
        click.echo(f"\n📊 执行结果:")
        click.echo(f"   总步骤: {run_result.get('total_steps', 0)}")
        click.echo(f"   已完成: {run_result.get('completed_steps', 0)}")

        blocked_at = run_result.get('blocked_at')
        if blocked_at:
            click.echo(f"   阻塞于: {blocked_at}")

    # Display state information
    if 'state' in data:
        state = data['state']
        click.echo(f"\n📊 工作流状态:")
        if 'workflow_id' in state:
            click.echo(f"  工作流: {state['workflow_id']}")
        if 'status' in state:
            click.echo(f"  状态: {state['status']}")
        if 'ready_steps' in state and state['ready_steps']:
            click.echo(f"  就绪步骤: {', '.join([s['id'] for s in state['ready_steps']])}")

    # Display workflows list
    if 'workflows' in data:
        workflows = data['workflows']
        click.echo(f"\n📋 工作流列表 ({data.get('total', len(workflows))}):")
        for wf in workflows[:10]:
            click.echo(f"  - {wf['id']}: {wf['status']}")
        if len(workflows) > 10:
            click.echo(f"  ... 还有 {len(workflows) - 10} 个")
```

---

## 📝 修改文件清单

### 必须修改的文件

1. **`src/lee/orchestrator/execution/pm_agent/api_wrapper.py`**
   - ✅ 恢复 `_handle_run_workflow()` 中的 Orchestrator API 调用
   - ✅ 确保其他 handler 方法也正确调用 API

2. **`src/lee/cli/commands/chat.py`**
   - ✅ 简化 `_handle_with_decision_engine()`
   - ✅ 删除 subprocess 相关代码
   - ✅ 删除 `_build_cli_command()` 等方法
   - ✅ 增强 `_display_result_data()`

### 可选保留的代码

- Claude 日志流式输出相关代码（如果需要实时显示 Claude 日志）
- 历史记录功能（FileHistory）

---

## 🎯 测试验证

### 测试 1: 非阻塞验证

```bash
$ lee chat

Lee> 在当前目录运行office.workspace-cleanup
🤔 Processing...
✅ 工作流已创建
✓ 执行成功: run_workflow

# ✅ 立即返回，可以继续输入
Lee> 当前状态如何
🤔 Processing...
...
```

### 测试 2: 功能验证

```bash
Lee> 继续工作流wf_task_4e2b3abc
✅ 继续执行成功
Lee> 批准 gate_s5_2_review_commits
✅ 批准成功
```

---

## 🎉 预期效果

### 修复前

```bash
Lee> 在当前目录运行office.workspace-cleanup
🤔 Processing...
# ❌ 阻塞，等待 subprocess 完成
# ❌ 用户无法继续输入
```

### 修复后

```bash
Lee> 在当前目录运行office.workspace-cleanup
🤔 Processing...
✅ 工作流已创建: wf_task_xxx
✓ 执行成功

# ✅ 立即返回
Lee> 当前状态如何  # 可以继续输入
...
```

---

## 📌 关键点

1. **统一 API 层**: `lee cli` 和 `lee chat` 都调用 `orchestrator/api`
2. **非阻塞**: `lee chat` 必须立即返回，不能阻塞
3. **职责分离**:
   - `api_wrapper.py` - 调用 Orchestrator API
   - `chat.py` - 只负责显示结果
4. **代码复用**: Orchestrator API 被所有客户端共享

---

**版本**: v1.6.0
**状态**: 待实施
