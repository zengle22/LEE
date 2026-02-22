# LEE 项目修改计划

> **作者**: LEE Team
> **日期**: 2026-02-21
> **版本**: v1.0.0
> **分类**: 架构文档

**状态**: 待执行

---

## 📊 架构分析总结

### ✅ 当前架构优点

1. **Orchestrator API 层完善** (`src/lee/orchestrator/api/__init__.py`)
   - ✅ 提供 10+ 个 API 函数
   - ✅ 统一入口 `pm_workflow_handler`
   - ✅ 同步包装器 `pm_workflow`
   - ✅ 全局 Orchestrator 缓存

2. **PM Agent 架构清晰** (`src/lee/orchestrator/execution/pm_agent/`)
   - ✅ Decision Engine → Intent Classifier → Param Mapper
   - ✅ API Wrapper 统一接口
   - ✅ 正确调用 Orchestrator API

3. **CLI 命令正确实现**
   - ✅ 所有命令都通过 `pm_workflow()` 调用
   - ✅ 统一的错误处理

### ❌ 发现的问题

#### P0 - 严重问题（阻塞）

**文件**: `src/lee/cli/commands/chat.py`
**行号**: 209
**问题**: `cmd` 变量未定义

```python
# 第 209 行
proc = await asyncio.create_subprocess_exec(
    *cmd,  # ❌ NameError: name 'cmd' is not defined
    ...
)
```

**影响**: 所有需要执行动作的命令都会失败

#### P1 - 高优先级（功能问题）

**问题 1**: 数据库路径不一致
- **chat.py**: `.lee/lee.db` ❌
- **Orchestrator API**: `.workflow/orchestrator.db` ✅

**影响**: 状态不一致

**问题 2**: subprocess 设计问题
- 循环依赖: `lee chat` → subprocess → `lee run` → `pm_workflow`
- 性能开销
- 复杂性增加

---

## 🎯 修改计划

### 阶段 1: 紧急修复 (P0)

**目标**: 修复 `cmd` 变量未定义的阻塞问题

**文件**: `src/lee/cli/commands/chat.py`

**修改位置**: 第 202 行之后

```python
async def _handle_with_decision_engine(self, text: str):
    """Handle input using Decision Engine - Direct CLI command execution"""
    click.echo(HTML("<pm>🤔 Processing...</pm>"))

    # Process input end-to-end
    result = await self.runtime.process_input(text, self.session_id)

    # Show reasoning/LLM thought process
    if 'reasoning' in result and result['reasoning']:
        click.echo()
        click.echo(click.style("🧠 思考过程:", fg='cyan', bold=True))
        click.echo(click.style(f"   {result['reasoning']}", fg='cyan'))
        click.echo()

    # ⬇️ 添加这段代码
    # Build CLI command from decision
    cmd = self._build_cli_command(result)
    if not cmd:
        self._print_error("无法识别的命令")
        return
    # ⬆️ 添加结束

    # Show what action will be taken
    if 'action' in result:
        action = result['action']
        click.echo(click.style(f"⚡ 执行动作: {action}", fg='yellow'))
    ...
```

**验证**:
```bash
# 修复前
$ lee chat
Lee> 在当前目录运行office.workspace-cleanup
NameError: name 'cmd' is not defined

# 修复后
$ lee chat
Lee> 在当前目录运行office.workspace-cleanup
🤔 Processing...
✅ 正常执行
```

---

### 阶段 2: 架构优化 (P1)

**目标**: 修复数据库路径不一致问题

**问题**: `chat.py` 使用独立的 `.lee/lee.db`，应该使用 `.workflow/orchestrator.db`

**修改方案**:

#### 选项 A: 删除独立 store（推荐）

```python
# src/lee/cli/commands/chat.py

class LeeChatREPL:
    def __init__(self, project_dir: str, enable_llm: bool = True):
        self.project_dir = Path(project_dir).resolve()

        # ❌ 删除这两行
        # self.db_path = self.project_dir / ".lee" / "lee.db"
        # self.store = SQLiteWorkflowStore(str(self.db_path))

        # ✅ 直接使用 Orchestrator API（通过 runtime）
        # 无需独立的 store

        # Initialize Orchestrator
        self.orchestrator = Orchestrator(...)  # 保持不变
```

#### 选项 B: 修改数据库路径（不推荐）

如果要保留独立 store，需要修改路径：
```python
self.db_path = self.project_dir / ".workflow" / "orchestrator.db"
```

**推荐**: 使用选项 A，删除独立 store

---

### 阶段 3: 架构重构 (P2, 可选)

**目标**: 移除 subprocess，改为直接调用 Orchestrator API

**当前问题**:
- subprocess 有性能开销
- 环境变量传递复杂
- 循环依赖风险

**重构方案**:

#### 步骤 1: 简化 `_handle_with_decision_engine`

```python
async def _handle_with_decision_engine(self, text: str):
    """Handle input using Decision Engine - Direct Orchestrator API calls"""
    click.echo(HTML("<pm>🤔 Processing...</pm>"))

    # process_input 已经调用了 Orchestrator API
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

    # ✅ 直接显示结果（已经通过 API 获取）
    if result['status'] == 'success':
        self._print_success(f"✓ 执行成功: {result.get('action', 'unknown')}")
        self._display_result_data(result.get('data', {}))
    elif result['status'] == 'error':
        error_msg = result.get('error', 'Unknown error')
        self._print_error(f"✗ Error: {error_msg}")

        # Show template hints if needed
        if 'Template not found' in error_msg:
            await self._show_available_templates()

    # Show confidence
    if 'confidence' in result:
        confidence = result['confidence']
        confidence_str = f"{confidence:.0%}" if confidence > 0 else "N/A"
        click.echo()
        click.echo(click.style(f"Confidence: {confidence_str}", fg='blue'))

    # ✅ 立即返回，用户可以继续输入
```

#### 步骤 2: 删除不需要的代码

删除以下方法（如果不再需要）:
- `_build_cli_command()` - 不再构建 CLI 命令
- `_stream_subprocess_output()` - 不再使用 subprocess
- subprocess 相关的所有代码

**注意**: 如果需要保留 Claude 日志流式输出功能，可以保留相关方法。

---

## 📋 详细修改清单

### 必须修改 (P0 + P1)

| 序号 | 文件 | 行号 | 操作 | 优先级 |
|------|------|------|------|--------|
| 1 | `src/lee/cli/commands/chat.py` | 202 后添加 | 添加 `cmd = self._build_cli_command(result)` | P0 |
| 2 | `src/lee/cli/commands/chat.py` | 37-38 | 删除独立 store 或修改路径 | P1 |

### 可选修改 (P2)

| 序号 | 文件 | 操作 | 优先级 |
|------|------|------|--------|
| 3 | `src/lee/cli/commands/chat.py` | 重构 `_handle_with_decision_engine` | P2 |
| 4 | `src/lee/cli/commands/chat.py` | 删除 `_build_cli_command` 等方法 | P2 |

---

## 🔧 执行步骤

### 第 1 步: 紧急修复 P0

```bash
# 1. 备份文件
cp src/lee/cli/commands/chat.py src/lee/cli/commands/chat.py.backup

# 2. 修改文件
# 在第 202 行之后添加：
#     cmd = self._build_cli_command(result)
#     if not cmd:
#         self._print_error("无法识别的命令")
#         return

# 3. 测试
 lee chat
 Lee> 在当前目录运行office.workspace-cleanup
```

### 第 2 步: 修复数据库路径 P1

```bash
# 1. 修改 chat.py
# 删除或注释第 37-38 行：
#     # self.db_path = self.project_dir / ".lee" / "lee.db"
#     # self.store = SQLiteWorkflowStore(str(self.db_path))

# 2. 确保所有状态查询通过 Orchestrator API

# 3. 测试
 lee chat
 Lee> 当前状态
```

### 第 3 步: 架构重构 P2（可选）

```bash
# 1. 重构 _handle_with_decision_engine
# 2. 删除 subprocess 相关代码
# 3. 测试验证
```

---

## ✅ 验证标准

### P0 验证

```bash
$ lee chat
Lee> 在当前目录运行office.workspace-cleanup
✅ 不应该出现 NameError
✅ 应该正常执行
```

### P1 验证

```bash
$ lee chat
Lee> 当前状态
✅ 应该显示正确的工作流状态
✅ 状态应该与 lee status 一致
```

### P2 验证

```bash
$ lee chat
Lee> 在当前目录运行office.workspace-cleanup
✅ 执行后立即返回，可以继续输入
Lee> 当前状态
✅ 无阻塞，可以连续输入多个命令
```

---

## 📌 注意事项

1. **备份优先**: 修改前务必备份
2. **逐步测试**: 每个阶段完成后都要测试
3. **保持兼容**: 确保 `lee cli` 命令仍然正常工作
4. **文档更新**: 修改后更新相关文档

---

## 🎯 总结

### 短期目标（必须完成）

1. ✅ 修复 `cmd` 变量未定义 (P0)
2. ✅ 修复数据库路径不一致 (P1)

### 长期目标（可选）

3. ⭕ 架构重构，移除 subprocess (P2)

### 预期效果

修复后 `lee chat` 应该：
- ✅ 不再出现 `NameError`
- ✅ 状态查询与 `lee status` 一致
- ✅ 用户可以连续输入多个命令
- ✅ 执行命令后立即返回，无阻塞

---

**制定日期**: 2026-02-21
**制定人**: Claude
**版本**: v1.0
