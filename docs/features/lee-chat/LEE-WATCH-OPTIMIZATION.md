# LEE Watch 优化完成

> **作者**: LEE Team
> **日期**: 2026-02-21
> **版本**: v1.0.0
> **分类**: 优化文档

## 🎯 优化内容

**问题**: `lee watch` 必须提供 workflow_id 参数，否则报错
**解决方案**: 让 workflow_id 参数变为可选，不提供时显示列表供用户选择

---

## ✅ 修改内容

### 修改前

```bash
$ lee watch
Usage: lee watch [OPTIONS] WORKFLOW_ID
Try 'lee watch --help' for help.

Error: Missing argument 'WORKFLOW_ID'.
```

### 修改后

```bash
$ lee watch

══════════════════════════════════════════════════════════════════════════════
可监控的工作流:
══════════════════════════════════════════════════════════════════════════════
1. 🔄 wf_task_cca07918
   模板: office.workspace.cleanup
   状态: running

2. ⏸️ wf_task_4e2b3abc
   模板: workflow.dev.feature
   状态: paused

3. ⏳ wf_task_123456
   模板: workflow.test.qa
   状态: pending

0. 取消

请选择要监控的工作流: 1

监控工作流: wf_task_cca07918
数据库: /Users/zengle/git/ai/.workflow/orchestrator.db
============================================================
按 Ctrl+C 停止监控
```

---

## 📋 新功能

### 1. 工作流列表显示

自动列出所有**活跃的工作流**（不包括 completed/failed）:
- 🔄 running - 运行中
- ⏸️ paused - 暂停
- ⏳ pending - 待执行
- 🚫 blocked - 阻塞

显示信息：
- 工作流 ID
- 模板 ID
- 当前状态

### 2. 交互式选择

```
请选择要监控的工作流: 1
```

- 输入数字选择工作流
- 输入 0 或 Ctrl+C 取消

### 3. 保留原有功能

```bash
# 直接指定工作流 ID
$ lee watch wf_task_cca07918

# 显示指定工作流的进度
```

---

## 🎯 使用场景

### 场景 1: 不知道工作流 ID

```bash
$ lee watch
# → 显示所有活跃工作流
# → 选择要监控的工作流
# → 开始监控
```

### 场景 2: 知道工作流 ID

```bash
$ lee watch wf_task_cca07918
# → 直接监控指定工作流
# → 跳过选择步骤
```

### 场景 3: 没有活跃工作流

```bash
$ lee watch
# → "没有活跃的工作流"
# → 退出
```

---

## 🔧 技术实现

### 修改的文件

**src/lee/cli/commands/watch.py**

**主要改动**:
1. `workflow_id` 参数改为可选 (`required=False`)
2. 添加 `_list_workflows()` 函数
3. 添加 `_select_workflow_to_watch()` 函数
4. 添加 `_watch_workflow()` 函数（原主逻辑）

### 关键代码

```python
@click.command()
@click.argument("workflow_id", required=False)  # ✅ 改为可选
@click.option("--project-dir", default=".", help="项目目录")
@click.option("--interval", default=2, help="刷新间隔（秒）")
def watch(workflow_id: Optional[str], project_dir: str, interval: int) -> None:
    """实时监控工作流执行进度"""
    # ...

    # 如果没有提供 workflow_id，显示列表并让用户选择
    if not workflow_id:
        workflow_id = _select_workflow_to_watch(db_path)
        if not workflow_id:
            click.echo("已取消监控")
            return

    # 监控指定工作流
    _watch_workflow(db_path, workflow_id, interval)
```

---

## ✅ 验证

### 语法检查
```bash
$ python -m py_compile src/lee/cli/commands/watch.py
✅ 无语法错误
```

### 功能测试

```bash
# 测试 1: 不带参数运行
$ lee watch
# → 应该显示工作流列表

# 测试 2: 带 workflow_id 运行
$ lee watch wf_task_123
# → 应该直接监控该工作流

# 测试 3: 没有活跃工作流
$ lee watch
# → 应该显示"没有活跃的工作流"
```

---

## 🎉 总结

### 优化前
- ❌ 必须提供 workflow_id
- ❌ 不提供直接报错
- ❌ 用户需要先 `lee status` 查找 ID

### 优化后
- ✅ workflow_id 可选参数
- ✅ 不提供时显示列表供选择
- ✅ 显示工作流状态和模板信息
- ✅ 更友好的用户体验

---

**状态**: ✅ 已完成
**日期**: 2026-02-21
**版本**: v1.1

**LEE Watch 已优化，可以更方便地监控工作流进度！** 🎊
