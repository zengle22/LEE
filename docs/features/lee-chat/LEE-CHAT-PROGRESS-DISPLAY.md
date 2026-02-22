# LEE Chat 实时进度显示问题分析

> **作者**: LEE Team
> **日期**: 2026-02-21
> **版本**: v1.0.0
> **分类**: 问题分析

## 🎯 问题现象

用户输入:
```
Lee> 运行工作流workspace_cleanup
```

预期：
- ✅ 看到工作流创建的进度
- ✅ 看到每一步的执行状态
- ✅ 实时看到 Claude Code 的日志输出

实际：
- ❌ "没有任何输出"（但工作流在后台运行）
- ✅ Claude Code 日志显示正在执行
- ❌ 用户看不到进度

---

## 🔍 问题分析

### 当前架构（修复后）

```
用户输入 → PM Agent → Orchestrator API (直接调用)
                      ↓
              返回结果
                      ↓
              显示给用户
```

**问题**：
1. Orchestrator API 是**异步执行**的
2. `api_run_until_blocked()` 会：
   - 创建工作流
   - 执行多个步骤
   - 直到阻塞或完成
   - **然后才返回结果**

3. 在执行过程中：
   - 用户看不到任何输出
   - Claude Code 在后台运行
   - 但进度信息没有实时显示给用户

### 对比 Claude Code 的实现

**Claude Code** 如何显示进度？

Claude Code 会：
1. **流式输出工具调用** - 实时显示每个工具的执行
2. **显示中间结果** - 每个步骤完成后立即显示
3. **显示思考过程** - 实时显示 LLM 的推理

---

## ✅ 解决方案

### 方案 1: 使用 `lee watch` 命令（推荐）

**特点**：
- ✅ 实时监控工作流进度
- ✅ 显示每一步的执行状态
- ✅ 显示日志输出

**使用方法**：
```bash
# 在另一个终端
$ lee watch wf_task_xxx

# 或者在 lee chat 中
Lee> watch wf_task_xxx
```

### 方案 2: 增强进度显示（需开发）

在 `api_wrapper.py` 中添加**进度回调**：

```python
async def _handle_run_workflow(self, decision, context):
    # 创建工作流
    create_result = await api_create_workflow(...)

    workflow_id = create_result["workflow_id"]

    # ✅ 显示创建成功
    click.echo(f"✅ 工作流已创建: {workflow_id}")

    # ✅ 逐步执行并显示进度
    for step_num in range(10):  # 最多10步
        # 获取就绪步骤
        state = await api_get_state(project_dir, workflow_id)
        ready_steps = state.get('ready_steps', [])

        if not ready_steps:
            click.echo("⏸️ 工作流已阻塞或完成")
            break

        step = ready_steps[0]
        click.echo(f"🔄 执行步骤 {step_num+1}: {step['id']}")

        # 执行步骤
        result = await api_run_step(project_dir, workflow_id, step['id'])

        # ✅ 显示执行结果
        if result['status'] == 'success':
            click.echo(f"  ✅ {step['id']} 完成")
        elif result['status'] == 'blocked':
            click.echo(f"  🚫 {step['id']} 阻塞")
            break
```

### 方案 3: 集成 Claude Code 日志流（已有部分实现）

当前代码已经有 `_stream_claude_runtime_logs` 方法，但可能没有正确显示。

---

## 🎯 立即可用的解决方案

### 使用 `lee watch` 查看实时进度

```bash
# 终端 1: 启动监控
$ lee watch

# 终端 2: 运行工作流
$ lee run workspace_cleanup
```

### 或者，在 `lee chat` 中使用 watch

```
Lee> 运行工作流 workspace_cleanup
✅ 工作流已创建: wf_task_xxx

Lee> watch
# 实时显示进度
```

---

## 📊 当前状态总结

### ✅ 已修复
- P0: cmd 变量未定义
- P1: 数据库路径不一致
- 架构: 直接调用 Orchestrator API（正确）

### ❌ 当前问题
- **用户看不到实时进度**
- Orchestrator API 返回的是最终结果
- 执行过程中的进度没有实时显示

### 🎯 建议的改进

1. **短期**：使用 `lee watch` 查看进度
2. **中期**：增强 `api_wrapper` 添加进度回调
3. **长期**：实现完整的流式输出

---

## 🎉 结论

**问题原因**：
- 当前架构是**批量执行**（执行完才返回）
- 不是**流式执行**（实时显示进度）

**临时解决方案**：
- 使用 `lee watch` 命令查看实时进度
- 或查看 Claude Code 日志文件

**长期解决方案**：
- 需要重构为流式输出架构
- 显示每个步骤的执行状态
- 实时显示 Claude Code 的日志

---

**状态**: 分析完成，待实施改进
**日期**: 2026-02-21
