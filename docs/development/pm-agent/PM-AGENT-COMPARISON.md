# PM Agent 架构对比 - 旧 vs 新

> **作者**: LEE Team
> **日期**: 2026-02-21
> **版本**: v1.0.0
> **分类**: 开发文档

## 📊 对比表

| 维度 | 旧架构 (错误) | 新架构 (正确) |
|-----|-------------|-------------|
| **执行方式** | 调用 Orchestrator API | 执行 CLI 命令 |
| **命令显示** | ❌ 不显示实际命令 | ✅ 显示 `lee run ...` |
| **输出显示** | ❌ 只显示 API 结果 | ✅ 显示 stdout/stderr |
| **透明度** | ❌ 黑盒 API 调用 | ✅ 完全透明 |
| **调试难度** | 🔴 困难 | 🟢 简单 |
| **符合协议** | ❌ 绕过 CLI 层 | ✅ 自然语言 → CLI |
| **架构复杂度** | 🔴 过度设计 | 🟢 简单直接 |

---

## 🔍 详细对比

### 场景: 运行工作流模板

#### 用户输入
```bash
Lee> 在当前目录运行office.workspace-cleanup
```

#### 旧架构 (v1.3.0)

```python
# 1. Decision Engine 处理
result = await runtime.process_input(text, session_id)
# result = {
#     'action': 'run_workflow',
#     'data': {'template_id': 'office.workspace-cleanup'}
# }

# 2. 调用 Orchestrator API
async def _handle_run_workflow(decision, context):
    template_id = decision.params.params.get("template_id")

    # ❌ 直接调用 API，绕过 CLI
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

    return APIResponse(status="success", data={...})

# 3. 显示结果
click.echo("✓ 执行成功: run_workflow")
# ❌ 没有显示实际命令
# ❌ 没有显示 stdout/stderr
```

**问题**:
- ❌ 用户看不到实际执行的 `lee run` 命令
- ❌ 看不到命令的实际输出
- ❌ 绕过了 CLI 层
- ❌ 不符合 PM Agent 协议

#### 新架构 (v1.4.0)

```python
# 1. Decision Engine 处理 (相同)
result = await runtime.process_input(text, session_id)
# result = {
#     'action': 'run_workflow',
#     'data': {'template_id': 'office.workspace-cleanup'}
# }

# 2. ✅ 构建 CLI 命令
cmd = self._build_cli_command(result)
# cmd = ['lee', 'run', 'office.workspace-cleanup', '--project-dir', '/Users/zengle/git/ai/lee']

# 3. ✅ 显示命令
click.echo("💻 执行命令:")
click.echo("   lee run office.workspace-cleanup --project-dir /Users/zengle/git/ai/lee")

# 4. ✅ 执行 CLI 命令
proc = await asyncio.create_subprocess_exec(
    *cmd,
    cwd=str(self.project_dir),
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE
)

# 5. ✅ 捕获输出
stdout, stderr = await proc.communicate()

# 6. ✅ 显示实际输出
click.echo(stdout.decode('utf-8'))
# 输出:
# ✓ Workflow created: wf_task_xxx
# ✓ Step 1/5 completed: analyze_project
# ✓ Step 2/5 completed: create_branch
# ⚠ Step 3/5 blocked: waiting for gate approval
```

**优点**:
- ✅ 显示实际执行的命令
- ✅ 显示命令的真实输出
- ✅ 通过 CLI 层执行
- ✅ 符合 PM Agent 协议

---

## 🎯 架构图

### 旧架构

```
┌─────────────┐
│ 用户输入      │ "在当前目录运行office.workspace-cleanup"
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Decision    │ 识别意图: run_workflow
│ Engine      │ 提取参数: template_id=office.workspace-cleanup
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ API         │ _handle_run_workflow()
│ Wrapper     │   ↓
└──────┬──────┘
       │
       ▼
┌─────────────────────────┐
│ Orchestrator API        │ api_create_workflow()
│  (内部调用)              │ api_run_until_blocked()
└──────────┬──────────────┘
           │
           ▼
      ┌─────────┐
      │ 返回结果 │ {"status": "success", "data": {...}}
      └─────────┘

❌ 问题: 绕过了 CLI 层
❌ 问题: 用户看不到实际命令
❌ 问题: 看不到命令输出
```

### 新架构

```
┌─────────────┐
│ 用户输入      │ "在当前目录运行office.workspace-cleanup"
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Decision    │ 识别意图: run_workflow
│ Engine      │ 提取参数: template_id=office.workspace-cleanup
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Build CLI   │ ['lee', 'run', 'office.workspace-cleanup',
│ Command     │  '--project-dir', '/Users/zengle/git/ai/lee']
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ 显示命令     │ 💻 lee run office.workspace-cleanup --project-dir .
└──────┬──────┘
       │
       ▼
┌─────────────────────────┐
│ Subprocess              │ asyncio.create_subprocess_exec()
│ Execute                 │   ↓
└──────────┬──────────────┘
           │
           ▼
      ┌─────────┐
      │ CLI 执行 │ lee run office.workspace-cleanup --project-dir .
      └────┬────┘
           │
           ▼
      ┌─────────┐
      │ 捕获输出 │ ✓ Workflow created: wf_task_xxx
      │         │ ✓ Step 1/5 completed: analyze_project
      └─────────│

✅ 优点: 通过 CLI 层执行
✅ 优点: 显示实际命令
✅ 优点: 显示命令输出
```

---

## 📝 代码对比

### 旧代码 (删除)

```python
async def _handle_run_workflow(self, decision: Decision, context: Optional[ExecutionContext]) -> APIResponse:
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
        # ❌ 直接调用 Orchestrator API
        create_result = await api_create_workflow(
            project_dir=self.project_dir,
            level="task",
            template_id=template_id,
            parent_id=None,
            data={}
        )

        if "workflow_id" not in create_result:
            return APIResponse(
                status="error",
                data={},
                error=f"Failed to create workflow: {create_result.get('error', 'Unknown error')}",
                action="run_workflow"
            )

        workflow_id = create_result["workflow_id"]

        # ❌ 直接调用 Orchestrator API
        run_result = await api_run_until_blocked(
            project_dir=self.project_dir,
            workflow_id=workflow_id,
            max_steps=10
        )

        return APIResponse(
            status="success",
            data={
                "workflow_id": workflow_id,
                "template_id": template_id,
                "create_result": create_result,
                "run_result": run_result,
                "message": f"Created and started workflow {workflow_id} from template {template_id}"
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

### 新代码 (添加)

```python
def _build_cli_command(self, result: dict) -> list:
    """Build CLI command from Decision Engine result"""
    action = result.get('action', '')
    data = result.get('data', {})

    cmd = ['lee']

    # ✅ 简单的命令映射
    if action == 'run_workflow':
        template_id = data.get('template_id')
        if template_id:
            cmd.extend(['run', template_id, '--project-dir', str(self.project_dir)])
        else:
            return None

    elif action == 'next_step':
        workflow_id = data.get('workflow_id')
        if workflow_id:
            cmd.extend(['next', workflow_id])
        else:
            return None

    # ... 其他映射

    return cmd

async def _handle_with_decision_engine(self, text: str):
    """Handle input using Decision Engine - Direct CLI command execution"""
    result = await self.runtime.process_input(text, self.session_id)

    # ✅ 构建命令
    cmd = self._build_cli_command(result)
    if not cmd:
        self._print_error("无法构建命令")
        return

    # ✅ 显示命令
    click.echo(click.style(f"💻 执行命令:", fg='green', bold=True))
    click.echo(f"   {' '.join(cmd)}")

    # ✅ 执行命令
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(self.project_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        # ✅ 捕获输出
        stdout, stderr = await proc.communicate()

        # ✅ 显示输出
        if stdout:
            click.echo(stdout.decode('utf-8'))

        if stderr and proc.returncode != 0:
            self._print_error(f"命令执行失败 (退出码: {proc.returncode})")
            click.echo(click.style(stderr.decode('utf-8'), fg='red'))

            # ✅ 显示帮助信息
            if 'Template not found' in stderr.decode('utf-8'):
                await self._show_available_templates()

        if proc.returncode == 0:
            self._print_success("✓ 命令执行成功")

    except Exception as e:
        self._print_error(f"执行命令时出错: {e}")
```

---

## 🎉 总结

### 旧架构的问题

1. **绕过 CLI 层**: 直接调用 Orchestrator API
2. **不透明**: 用户看不到实际执行的命令
3. **缺少输出**: 只显示 API 结果，不显示 stdout/stderr
4. **过度设计**: 复杂的 API 包装层
5. **不符合协议**: PM Agent 应该是简单的命令翻译器

### 新架构的优点

1. **直接执行**: 通过 CLI 命令执行
2. **完全透明**: 显示实际命令和输出
3. **简单直接**: 易于理解和调试
4. **符合协议**: 自然语言 → CLI 命令
5. **类似 Claude Code**: 简单的翻译层架构

---

**版本**: v1.4.0
**更新日期**: 2026-02-21
**状态**: ✅ 生产就绪

**PM Agent 架构修复完成！** 🎊
