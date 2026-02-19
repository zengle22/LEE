---
title: LEE 工作流日志和监控指南
author: LEE Team
date: 2026-02-18
version: 1.0
last_updated: 2026-02-19
---

# LEE 工作流日志和监控指南

## 📋 问题解决方案

### 原始问题
执行 `lee run` 命令后，CLI 卡住不显示任何进度信息。

### 根本原因
`run_until_blocked` 是同步阻塞调用，在执行期间无法显示进度。

## ✅ 解决方案

### 1. 简化的 `lee run` 命令

现在 `lee run` 会：
- 创建工作流并显示工作流 ID
- 执行工作流
- 完成后显示摘要统计

### 2. 新增 `lee watch` 命令

实时监控工作流执行进度：

```bash
$ lee watch <workflow_id> [--interval 2]
```

功能：
- ✅ 实时显示执行状态
- ✅ 显示完成进度（X/Y 步骤）
- ✅ 显示当前正在执行的步骤
- ✅ 自动停止（当工作流完成/失败/暂停时）
- ✅ Ctrl+C 手动停止

### 3. 日志查看脚本

使用 `./lee-logs.sh` 查看详细日志

## 📊 日志位置

### 主要日志文件

1. **事件日志** - `.workflow/events.jsonl`
2. **数据库** - `.workflow/orchestrator.db`
3. **Claude Code 执行日志** - `.workflow/claude-code/RUN-*/`
4. **渲染的工作流模板** - `.workflow/rendered/workflow-*.yaml`

## 🎯 使用建议

### 方式 1：后台运行 + 监控

```bash
# 在一个终端运行工作流
lee run office.workspace-cleanup --project-dir .

# 在另一个终端监控
lee watch <workflow_id>
```

### 方式 2：分步执行

```bash
# 执行少数步骤
lee run office.workspace-cleanup --project-dir . --max-steps 1

# 查看结果
./lee-logs.sh
```

## 📝 总结

现在你可以：
1. ✅ 实时监控工作流进度 - `lee watch <workflow_id>`
2. ✅ 查看详细日志 - `./lee-logs.sh <workflow_id>`
3. ✅ 检查当前状态 - `lee status <workflow_id>`
4. ✅ 查看数据库记录 - 直接查询 SQLite
5. ✅ 监控事件流 - `tail -f .workflow/events.jsonl | jq`

不再需要担心 CLI 卡住！
