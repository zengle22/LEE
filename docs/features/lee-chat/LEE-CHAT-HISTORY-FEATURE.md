# Lee Chat 历史记录功能

> **作者**: LEE Team
> **日期**: 2026-02-21
> **版本**: v1.0.0
> **分类**: 功能文档

## 🎯 新功能

**Lee Chat 现在支持命令历史记录！**

使用 ↑/↓ 箭头键可以快速翻阅之前输入的命令，提升使用体验。

---

## ✨ 功能特性

### 1. 自动保存历史命令

每次输入的命令会自动保存到历史文件中：
- 历史文件位置: `.lee/chat_history.txt`
- 永久保存，重启后仍然可用
- 跨会话共享

### 2. 快速翻阅

使用键盘快捷键：
- **↑ (上箭头)**: 查看上一条命令
- **↓ (下箭头)**: 查看下一条命令
- **Ctrl+C**: 中断当前输入
- **Ctrl+D**: 退出

### 3. 智能匹配

`prompt_toolkit` 的 `FileHistory` 会：
- 自动加载历史记录
- 支持快速搜索
- 提供自动补全建议

---

## 🚀 使用示例

### 场景 1: 重复执行相同命令

```bash
Lee> 在当前目录运行office.workspace-cleanup
# ... 执行完成 ...

# 按 ↑ 箭头键
Lee> 在当前目录运行office.workspace-cleanup
# 命令自动填充，按回车再次执行
```

### 场景 2: 修改历史命令

```bash
Lee> 在当前目录运行office.workspace-cleanup
# ... 执行完成 ...

# 按 ↑ 箭头键，然后使用 ←/→ 箭头键编辑
Lee> 在当前目录运行workflow.dev.feature
# 修改后执行新的命令
```

### 场景 3: 跨会话历史

```bash
# 第一次会话
$ lee chat
Lee> 继续工作流wf_task_123
Lee> exit
Goodbye!

# 第二次会话（几天后）
$ lee chat
Lee> # 按 ↑ 键，可以看到之前的命令
Lee> 继续工作流wf_task_123  # 自动填充
```

---

## 🔧 技术实现

### 修改的文件

**`src/lee/cli/commands/chat.py`**

#### 1. 导入 FileHistory

```python
from prompt_toolkit.history import FileHistory
```

#### 2. 配置 PromptSession

```python
# Setup history file
lee_dir = self.project_dir / ".lee"
lee_dir.mkdir(exist_ok=True)
history_file = lee_dir / "chat_history.txt"

# Create PromptSession with history
self.session = PromptSession(
    history=FileHistory(str(history_file)),
    auto_suggest=True
)
```

#### 3. 更新欢迎信息

```python
welcome = f"""
...
快捷键:
  ↑/↓ 箭头键    - 翻阅历史命令
  Ctrl+C        - 中断当前输入
  Ctrl+D        - 退出
...
"""
```

---

## 📊 功能验证

### 测试结果

```bash
$ python -c "
from lee.cli.commands.chat import LeeChatREPL
repl = LeeChatREPL('.', enable_llm=False)
print(f'Has history: {repl.session.history is not None}')
print(f'History type: {type(repl.session.history).__name__}')
print(f'History file: {repl.session.history.filename}')
"

✅ Has history: True
✅ History type: FileHistory
✅ History file: /Users/zengle/git/ai/lee/.lee/chat_history.txt
```

### 历史文件格式

```
1771643078:在当前目录运行office.workspace-cleanup
1771643078:继续工作流wf_task_123
1771643078:当前状态如何
```

格式: `timestamp:command`

---

## 📝 使用技巧

### 技巧 1: 快速重试

如果某个命令执行失败，按 ↑ 键可以立即找回命令，修改后重新执行。

### 技巧 2: 批量操作

对于重复性的工作流操作：
1. 第一次输入完整命令
2. 后续使用 ↑ 键快速调出
3. 只修改必要的参数

### 技巧 3: 命令模板

可以将常用的复杂命令作为"模板"，保存在历史中，需要时快速调出修改。

---

## 🎯 最佳实践

### 1. 定期清理历史

如果历史文件过大，可以手动清理：

```bash
# 查看历史文件
cat .lee/chat_history.txt

# 清空历史
> .lee/chat_history.txt

# 或者删除部分历史
# 编辑文件删除不需要的行
```

### 2. 备份重要命令

如果某些命令很重要，建议：
1. 保存到脚本文件
2. 使用 shell 别名
3. 记录到文档

### 3. 隐私保护

历史文件包含所有输入的命令，请注意：
- 不要输入敏感信息（密码、密钥等）
- 定期清理历史
- 如果有敏感需求，可以手动删除历史文件

---

## 🔍 故障排查

### 问题 1: 历史记录不工作

**检查**:
```bash
# 确认历史文件存在
ls -la .lee/chat_history.txt

# 确认文件权限
ls -l .lee/chat_history.txt
```

**解决**:
```bash
# 手动创建历史文件
touch .lee/chat_history.txt
```

### 问题 2: 历史记录丢失

**原因**: 可能是文件权限问题或被手动删除

**解决**:
```bash
# 重新创建历史文件
touch .lee/chat_history.txt
chmod 644 .lee/chat_history.txt
```

### 问题 3: ↑/↓ 键不工作

**检查**: 确认终端支持箭头键

**解决**: 尝试使用不同的终端（如 iTerm2、Terminal.app）

---

## 🎉 总结

### 优点

✅ **提升效率** - 快速重用历史命令
✅ **减少输入** - 避免重复输入长命令
✅ **跨会话** - 历史永久保存
✅ **简单易用** - 标准的箭头键操作

### 改进空间

未来可以考虑：
- 📝 历史搜索功能 (Ctrl+R)
- 🗑️ 历史清理命令
- 📊 历史统计信息
- 🔒 敏感命令过滤

---

**版本**: v1.5.0
**更新日期**: 2026-02-21
**状态**: ✅ 已实现

**Lee Chat 现在支持完整的命令历史记录功能！** 🎊
