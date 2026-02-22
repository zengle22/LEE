# Lee Chat 历史记录功能 - 快速参考

> **作者**: LEE Team
> **日期**: 2026-02-21
> **版本**: v1.0.0
> **分类**: 快速参考

## ⌨️ 快捷键

| 快捷键 | 功能 |
|--------|------|
| **↑ (上箭头)** | 查看上一条历史命令 |
| **↓ (下箭头)** | 查看下一条历史命令 |
| **Ctrl+C** | 中断当前输入 |
| **Ctrl+D** | 退出 lee chat |

---

## 📁 历史文件

**位置**: `.lee/chat_history.txt`

**格式**: 每行一个命令，格式为 `timestamp:command`

**示例**:
```
1771643078:在当前目录运行office.workspace-cleanup
1771643078:继续工作wf_task_123
1771643078:当前状态如何
```

---

## 🚀 快速开始

### 1. 启动 lee chat

```bash
$ lee chat

╔════════════════════════════════════════════════════════════╗
║           Lee Chat - PM Agent Interactive Interface         ║
╚════════════════════════════════════════════════════════════╝

快捷键:
  ↑/↓ 箭头键    - 翻阅历史命令
  Ctrl+C        - 中断当前输入
  Ctrl+D        - 退出
```

### 2. 输入命令

```bash
Lee> 在当前目录运行office.workspace-cleanup
# 执行...
```

### 3. 使用历史记录

```bash
# 按 ↑ 键
Lee> 在当前目录运行office.workspace-cleanup
# 命令自动填充，按回车执行
```

---

## 💡 使用技巧

### 技巧 1: 快速重试

```bash
Lee> 在当前目录运行office.workspace-cleanup
# 执行失败...

# 按 ↑ 键，修改后重试
Lee> 在当前目录运行office.workspace.cleanup  # 修正拼写
```

### 技巧 2: 批量操作

```bash
Lee> 继续工作流wf_task_001
# 按 ↑ → 修改 ID → 执行
Lee> 继续工作流wf_task_002
# 按 ↑ → 修改 ID → 执行
Lee> 继续工作流wf_task_003
```

### 技巧 3: 跨会话使用

```bash
# 第一次会话
$ lee chat
Lee> 运行 workflow.dev.feature
Lee> exit

# 几天后
$ lee chat
Lee> # 按 ↑ 键，历史命令仍然可用
```

---

## 🔧 管理历史

### 查看历史

```bash
$ cat .lee/chat_history.txt
1771643078:在当前目录运行office.workspace-cleanup
1771643078:继续工作流wf_task_123
```

### 清空历史

```bash
$ > .lee/chat_history.txt
```

### 编辑历史

```bash
$ vim .lee/chat_history.txt
# 或使用任何文本编辑器
```

---

## ⚠️ 注意事项

### 隐私保护

⚠️ **不要输入敏感信息**（密码、密钥、Token等）

历史文件以明文保存，包含所有输入的命令。

### 定期清理

如果历史文件过大，建议定期清理：

```bash
# 查看文件大小
$ ls -lh .lee/chat_history.txt

# 清空历史
$ > .lee/chat_history.txt
```

---

## 🎉 功能特性

✅ **自动保存** - 每次输入自动保存到历史文件
✅ **永久保存** - 跨会话保留，重启后仍然可用
✅ **快速翻阅** - 使用 ↑/↓ 键快速查找
✅ **可编辑** - 历史命令可以修改后重新执行

---

**版本**: v1.5.0
**状态**: ✅ 已实现

**Lee Chat 现在支持完整的命令历史记录功能！** 🎊
