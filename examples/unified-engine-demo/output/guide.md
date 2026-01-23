# Orchestrator 快速入门指南

## 简介

Orchestrator 是一个通用的 AI 工作流编排器。

## 核心特性

1. **强制执行规范**：让工作流规范从"建议"变成"协议"
2. **人类在环控制**：关键决策点强制人工审批
3. **完整审计追踪**：记录所有操作，可追溯、可回放
4. **跨平台支持**：Claude Code、Codex CLI、Gemini Code

## 快速开始

```bash
# 初始化工作流
python -m flowcore.orchestrator init . --workflow workflow.yaml

# 执行步骤
python -m flowcore.orchestrator run-engine . step1
```

## 架构

Orchestrator 采用分层架构：
- 编排层：管理工作流状态
- Engine 层：执行具体任务
- 存储层：文件系统
