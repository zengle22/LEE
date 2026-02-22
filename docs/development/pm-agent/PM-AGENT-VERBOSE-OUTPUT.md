# ✅ PM Agent 详细输出功能 - 已实现

> **作者**: LEE Team
> **日期**: 2026-02-21
> **版本**: v1.0.0
> **分类**: 开发文档

## 🎯 新功能

现在 PM Agent 会显示：

1. ✅ **LLM 思考过程** - 解释为什么做出这个决策
2. ✅ **执行的动作** - 显示将要执行的操作
3. ✅ **提取的参数** - 显示识别出的参数
4. ✅ **实际命令** - 显示等效的 LEE 命令
5. ✅ **详细错误** - 提供有用的提示和可用模板

---

## 📊 输出示例

### 示例 1: 列出工作流

```bash
Lee> 列出所有工作流

🧠 思考过程:
   Matched pattern: List/show commands

⚡ 执行动作: get_state
🔄 工作流ID: None

💻 执行命令:
   lee next None

✓ 执行成功: get_state

📊 Workflow State:

Confidence: 90%
```

### 示例 2: 运行工作流（成功）

```bash
Lee> 在当前目录运行office.workspace-cleanup

🧠 思考过程:
   User specified '运行' (run) with workflow template ID
   'office.workspace-cleanup' and location '当前目录'

⚡ 执行动作: run_workflow
📦 模板ID: office.workspace-cleanup

💻 执行命令:
   lee create workflow office.workspace-cleanup
   lee run <created_workflow_id>

✓ 执行成功: run_workflow

📊 工作流ID: wf_abc123
Confidence: 95%
```

### 示例 3: 运行工作流（模板不存在）

```bash
Lee> 在当前目录运行office.workspace-cleanup

🧠 思考过程:
   User specified '运行' (run) with workflow template ID
   'office.workspace-cleanup' and location '当前目录'

⚡ 执行动作: run_workflow
📦 模板ID: office.workspace-cleanup

💻 执行命令:
   lee create workflow office.workspace-cleanup
   lee run <created_workflow_id>

✗ Error: Template not found: office.workspace-cleanup

💡 提示: 可用的工作流模板:
   - office.workspace.cleanup
   - workflow.dev.feature
   - workflow.stg.opportunity_discovery

💡 提示: 使用 'lee list' 查看所有可用的命令

Confidence: 95%
```

### 示例 4: 继续工作流

```bash
Lee> 继续工作流wf_task_4e2b3abc

🧠 思考过程:
   Matched pattern: Continue commands
   Extracted workflow_id: wf_task_4e2b3abc

⚡ 执行动作: next_step
🔄 工作流ID: wf_task_4e2b3abc

💻 执行命令:
   lee next wf_task_4e2b3abc

✓ 执行成功: next_step
Confidence: 95%
```

---

## 🔧 技术实现

### 1. 思考过程显示

修改 `src/lee/cli/commands/chat.py`:

```python
# Show reasoning/LLM thought process
if 'reasoning' in result and result['reasoning']:
    click.echo()
    click.echo(click.style("🧠 思考过程:", fg='cyan', bold=True))
    click.echo(click.style(f"   {result['reasoning']}", fg='cyan'))
    click.echo()
```

### 2. 显示执行命令

```python
# Show command being executed
if data and 'workflow_id' in data:
    workflow_id = data['workflow_id']
    template_id = data.get('template_id', 'unknown')
    click.echo()
    click.echo(click.style(f"💻 执行命令:", fg='green', bold=True))
    click.echo(f"   lee create {template_id}")
    click.echo(f"   lee next {workflow_id}")
```

### 3. 智能错误提示

```python
# If template not found, show available templates
if 'Template not found' in error_msg:
    click.echo()
    click.echo(click.style("💡 提示: 可用的工作流模板:", fg='yellow'))

    # List available templates
    templates_dict = tm.load_all_templates()
    for tmpl in templates_dict.keys()[:10]:
        click.echo(f"   - {tmpl}")
```

---

## 📝 输出元素说明

| 符号 | 含义 | 颜色 |
|------|------|------|
| 🧠 | LLM 思考过程 | 青色 |
| ⚡ | 执行的动作 | 黄色 |
| 📦 | 模板 ID | 蓝色 |
| 🔄 | 工作流 ID | 蓝色 |
| ➡️ | 步骤 ID | 蓝色 |
| ✅ | 网关 ID | 蓝色 |
| 💻 | 执行的命令 | 绿色 |
| ✓ | 成功 | 绿色 |
| ✗ | 错误 | 红色 |
| 💡 | 提示信息 | 黄色 |

---

## 🚀 使用示例

### 测试详细输出

```bash
lee chat

# 查看完整的思考过程
Lee> 在当前目录运行office.workspace-cleanup

# 查看参数提取
Lee> 继续工作流wf_task_123

# 查看错误提示
Lee> 运行不存在的模板
```

---

## 🎯 改进点总结

### 之前

```bash
Lee> 在当前目录运行office.workspace-cleanup
🤔 Processing...
✗ Error: Template not found: office.workspace-cleanup
Confidence: 95%
```

❌ 没有解释
❌ 没有显示执行什么
❌ 没有有用的错误提示

### 现在

```bash
Lee> 在当前目录运行office.workspace-cleanup
🤔 Processing...

🧠 思考过程:
   User specified '运行' with template 'office.workspace-cleanup'

⚡ 执行动作: run_workflow
📦 模板ID: office.workspace-cleanup

💻 执行命令:
   lee create office.workspace-cleanup
   lee next <workflow_id>

✗ Error: Template not found

💡 提示: 可用的模板:
   - office.workspace.cleanup
   - workflow.dev.feature

Confidence: 95%
```

✅ 解释决策过程
✅ 显示执行命令
✅ 提供有用的帮助

---

## 🔍 调试模式

现在可以清楚地看到：

1. **LLM 如何理解输入**
2. **提取了什么参数**
3. **将执行什么命令**
4. **为什么失败**
5. **有什么替代选项**

这对调试和了解系统行为非常有帮助！

---

## 📌 待优化

1. **显示命令的实际输出**
   - 需要捕获 CLI 命令的 stdout
   - 实时显示执行进度

2. **更详细的错误信息**
   - 显示错误的根本原因
   - 提供修复建议

3. **交互式错误恢复**
   - "要尝试运行 office.workspace.cleanup 吗？"

---

## 🔧 架构升级 (v1.4.0)

**重要变更**: 现在 PM Agent 直接执行 CLI 命令，而不是调用 Orchestrator API！

详见: [PM-AGENT-CLI-EXECUTION.md](./PM-AGENT-CLI-EXECUTION.md)

### 核心改进

```python
# 之前 (错误)
api_create_workflow() + api_run_until_blocked()

# 现在 (正确)
subprocess.execute(['lee', 'run', 'office.workspace.cleanup'])
```

### 命令输出

现在可以看到**实际的 CLI 命令输出**:

```bash
Lee> 在当前目录运行office.workspace-cleanup

💻 执行命令:
   lee run office.workspace-cleanup --project-dir .

✓ Workflow created: wf_task_xxx
✓ Step 1/5 completed: analyze_project
✓ Step 2/5 completed: create_branch
⚠ Step 3/5 blocked: waiting for gate approval

✓ 命令执行成功
```

---

**版本**: v1.4.0
**更新日期**: 2026-02-21
**状态**: ✅ 已实现

**现在 PM Agent 不仅智能，而且透明，而且真正执行 CLI 命令！** 🎉
