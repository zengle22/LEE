---
title: V2 架构端到端示例
author: LEE Team
date: 2026-01-29
version: 1.0
last_updated: 2026-02-19
---

# V2 架构端到端示例

这是一个完整的示例项目，展示如何使用 LEE v2.0 架构来：
1. 使用 LLM Agent 生成代码
2. 使用 Shell Skill 运行测试

## 架构说明

本项目使用新的 v2.0 架构：
- **PM Agent**: 决策下一步执行哪个步骤
- **Orchestrator**: 管理工作流状态和调度
- **Engine/Executor**: 实际执行工作（LLMExecutor / ShellSkillExecutor）

## 快速开始

### 1. 设置环境变量

```bash
export OPENAI_API_KEY="sk-..."
```

### 2. 运行 Demo

```bash
# 方式 1: 使用 Python 脚本
python run_demo.py

# 方式 2: 使用 Orchestrator CLI
python -m flowcore.orchestrator init . --workflow ai-spec/workflows/demo/workflow.yaml
python -m flowcore.orchestrator run-engine . generate_code
python -m flowcore.orchestrator run-engine . run_unit_tests
```

## 项目结构

```
v2-demo/
├── ai-spec/
│   ├── workflows/
│   │   └── demo/
│   │       └── workflow.yaml      # 工作流定义
│   ├── agents/
│   │   └── developer/
│   │       └── agent.yaml         # Developer Agent 规范
│   └── skills/
│       └── ci.run_tests.yaml      # 测试 Skill 规范
├── src/
│   └── demo.py                    # 生成的代码（LLM 生成）
├── tests/
│   └── test_demo.py               # 测试文件
├── reports/
│   └── unit_test_report.xml       # 测试报告
└── run_demo.py                    # 运行脚本
```

## 工作流步骤

### Step 1: generate_code
- **类型**: Agent (LLM)
- **任务**: 生成一个 `add(a, b)` 函数
- **输出**: `src/demo.py`

### Step 2: run_unit_tests
- **类型**: Skill (Shell)
- **依赖**: generate_code
- **任务**: 运行 pytest
- **输出**: `reports/unit_test_report.xml`

## 预期输出

```
========================================
  V2 Architecture Demo
========================================

Workflow: demo_flow
Step 1: generate_code
  Engine: llm
  Status: completed
  Output: src/demo.py

Step 2: run_unit_tests
  Engine: shell
  Status: completed
  Output: reports/unit_test_report.xml

✅ All steps completed successfully!
```

## 扩展

你可以基于此示例创建更复杂的工作流：
- 添加多个 Agent 步骤
- 添加多个 Skill 步骤
- 使用不同的 Engine（MCP, MetaGPT）
- 添加门禁和人工审批

## 相关文档

- [新架构文档](../../docs/architecture.md)
- [PM Agent 协议](../../docs/PM_AGENT_PROTOCOL.md)
- [迁移指南](../../docs/ARCHITECTURE-MIGRATION-GUIDE.md)
