---
title: LEE Slash Commands 使用指南
author: LEE Team
date: 2026-01-29
version: 1.0
last_updated: 2026-02-19
---

# LEE Slash Commands 使用指南

## 概述

LEE 系统现在支持两种类型的可执行组件：

### 1. Function Tools (`.claude/tools/*.json`)

**用途**: AI 可以自动调用的函数工具

**特点**:
- 定义为 JSON 格式
- AI 根据上下文自动决定何时调用
- 用于程序化集成

**示例**:
- `gate_review` - Gate review function tool
- `gate_approval` - Gate approval function tool
- `pm_workflow` - PM workflow management tool

### 2. Slash Commands (`.claude/commands/*.md`)

**用途**: 用户可以直接输入的斜杠命令

**特点**:
- 定义为 Markdown 格式
- 用户主动触发执行
- 用于交互式操作

**示例**:
- `/gate-review` - Review and approve gates
- `/gate-approval` - Gate approval tools
- `/pm-workflow` - PM workflow management

## Slash Commands 使用

### `/gate-review` - Gate Review

审核和审批 LEE workflow 中的 human gates。

```bash
/gate-review
```

这将：
1. 列出所有待审批的 gates
2. 显示每个 gate 的关键决策内容
3. 显示上游分析结果摘要
4. 引导你提交审批决策

### `/gate-approval` - Gate Approval

Gate 审批工具的快捷方式。

```bash
/gate-approval
```

### `/pm-workflow` - PM Workflow

PM workflow 管理工具。

```bash
/pm-workflow
```

## 文件结构

```
LEE/
├── .claude/
│   ├── tools/                      # Function Tools (JSON)
│   │   ├── gate-review.json        # gate_review 函数工具
│   │   ├── gate-approval.json      # gate_approval 函数工具
│   │   └── pm-workflow.json       # pm_workflow 函数工具
│   └── commands/                   # Slash Commands (Markdown)
│       ├── gate-review.md          # /gate-review 斜杠命令
│       ├── gate-approval.md        # /gate-approval 斜杠命令
│       └── pm-workflow.md         # /pm-workflow 斜杠命令
├── flowcore/
│   └── api.py                      # Handler 实现
└── spec-global/
    └── cross/
        └── skills/
            └── gate-review/
                └── v1/
                    └── skill.yaml  # Skill 规范
```

## 区别总结

| 特性 | Function Tools | Slash Commands |
|------|---------------|----------------|
| 文件格式 | JSON | Markdown |
| 位置 | `.claude/tools/*.json` | `.claude/commands/*.md` |
| 调用方式 | AI 自动调用 | 用户输入 `/name` |
| 用途 | 程序化集成 | 交互式操作 |
| 示例 | `gate_review` tool | `/gate-review` command |

## 故障排除

### Slash command 不生效？

1. **检查文件位置**: 确保文件在 `.claude/commands/` 目录下
2. **检查文件名**: 文件名必须与命令名匹配（如 `gate-review.md` → `/gate-review`）
3. **重启 Claude Code**: 添加新命令后需要完全重启 Claude Code
4. **检查文件格式**: 确保是有效的 Markdown 文件

### Function tool 不工作？

1. **检查 handler 路径**: 确保 `handler: "flowcore.api:handler_name"` 正确
2. **检查 Python 导入**:
   ```python
   python -c "from flowcore.api import gate_review_handler; print('OK')"
   ```
3. **测试函数调用**:
   ```python
   from flowcore.api import gate_review_handler
   result = gate_review_handler(action='list', project_dir='.')
   print(result['markdown'])
   ```

## 相关文档

- [Gate Review Skill Guide](./GATE-REVIEW-SKILL-GUIDE.md) - gate_review 函数工具详细指南
- [Gate Review Troubleshooting](./GATE-REVIEW-TROUBLESHOOT.md) - 故障排除指南
- [PM Agent Protocol](./PM_AGENT_PROTOCOL.md) - PM Agent 协议说明
- [Gate Assistant Protocol](./GATE_ASSISTANT_PROTOCOL.md) - Gate Assistant 协议说明

## 参考资料

- [Claude Code Slash Commands Documentation](https://code.claude.com/docs/zh-CN/slash-commands)
- [Claude Code Skills Documentation](https://code.claude.com/docs/en/skills)
