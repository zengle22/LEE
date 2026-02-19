---
title: 🚀 LEE 快速启动指南
author: LEE Team
date: 2026-01-29
version: 1.0
last_updated: 2026-02-19
---

# 🚀 LEE 快速启动指南

## 环境已搭建完成！

所有依赖已安装，所有测试已通过。以下是快速使用指南。

---

## 📋 前置条件

- ✅ Python 3.8+
- ✅ Node.js 16+ (可选，用于 MCP Server)
- ✅ Antigravity 反代运行中 (http://127.0.0.1:8045/v1)
- ✅ 环境变量已配置 (.env 文件)

---

## 🎯 三种使用方式

### 1️⃣ 使用 PM Agent API

```python
from flowcore.api import api_get_state, api_run_step, api_next_step

# 获取工作流状态
state = api_get_state(".")
print(f"进度: {state['completed_steps']}/{state['total_steps']}")

# 执行下一步
result = api_next_step(".")
print(f"执行: {result['step_id']}")
```

### 2️⃣ 直接使用 LLM Executor

```python
from flowcore.engines.llm.executor import LLMExecutor
import asyncio

async def test():
    executor = LLMExecutor(".", {
        "engine": {
            "type": "llm",
            "provider": "custom",
            "base_url": "http://127.0.0.1:8045/v1",
            "api_key": "sk-2988e892730744ccafde80aac9ced361",
            "model": "gemini-3-flash"
        },
        "system_prompt": "你是有帮助的助手",
        "user_prompt": "介绍一下 Python"
    })

    result = await executor.execute(request)
    print(result.raw)

asyncio.run(test())
```

### 3️⃣ 调用 MCP 工具

```python
import aiohttp
import asyncio

async def call_mcp_tool():
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "http://localhost:3000/tools/run_tests",
            json={"arguments": {"project": ".", "test_type": "unit"}}
        ) as resp:
            result = await resp.json()
            print(result)

asyncio.run(call_mcp_tool())
```

---

## 🔧 启动服务

### MCP Server (必需)

```bash
# 方法 1: Python Mock Server (推荐用于测试)
python scripts/run_mock_mcp.py

# 方法 2: Node.js Server (生产环境)
cd mcp-server
npm install
npm start
```

### 确认服务运行

```bash
# 检查 MCP Server
curl http://localhost:3000/health

# 检查 Antigravity 反代
curl http://127.0.0.1:8045/v1/models
```

---

## 🧪 运行测试

### 完整测试套件

```bash
python scripts/test_all.py
```

### 单独测试

```bash
# LLM 测试
python scripts/test_llm.py

# MCP 测试
python scripts/test_mcp.py

# MetaGPT 测试
python scripts/test_metagpt.py

# PM Gate 集成测试
python examples/pm-gate-integration-demo/test_pm_gate_integration.py
```

---

## 📁 创建 Agent

### 1. 创建 Agent Spec

**文件**: `spec-global/departments/my_agent/v1/agent.yaml`

```yaml
kind: agent
id: agent.my.custom_agent
version: 1.0
name: 我的自定义 Agent
description: 使用本地 LLM 的自定义 Agent

engine:
  type: llm
  provider: custom
  base_url: http://127.0.0.1:8045/v1
  api_key: sk-2988e892730744ccafde80aac9ced361
  model: gemini-3-flash
  temperature: 0.7
  max_tokens: 4000

system_prompt: |
  你是一个专业的助手，专注于...
  你的任务是...

constraints:
  non_goals:
    - 不要做超出范围的事情
    - 不要编造信息

  hard_rules:
    - 必须基于事实回答
    - 遇到不确定的信息要说不知道

quality_bar:
  accuracy: "必须准确无误"
  completeness: "必须完整回答"
  clarity: "必须清晰易懂"
```

### 2. 运行 Agent

```python
from flowcore.orchestrator.pm_agent_tools import orchestrator_run_step

result = orchestrator_run_step(".", "my.custom_agent")
```

---

## 📁 创建 Skill

### 1. 创建 Shell Skill

**文件**: `spec-global/departments/my_skill/v1/skill.yaml`

```yaml
kind: skill
id: skill.my.run_tests
version: 1.0
name: 运行测试
description: 运行项目单元测试

engine:
  type: shell
  command: |
    cd {{ project_dir }} && \
    python -m pytest tests/ -v \
      --junitxml=reports/test-report.xml
  timeout: 300
  working_dir: {{ project_dir }}

inputs: []
outputs:
  - path: reports/test-report.xml
    description: JUnit 测试报告
```

### 2. 创建 MCP Skill

**文件**: `spec-global/departments/my_skill/v1/deploy_skill.yaml`

```yaml
kind: skill
id: skill.my.deploy
version: 1.0
name: 部署应用
description: 部署到指定环境

engine:
  type: mcp
  server_url: http://localhost:3000
  tool: deploy
  timeout: 600
  arguments:
    environment: staging
    project: {{ project_dir }}
    branch: main

inputs:
  - from_step: build
    path: dist/
    description: 构建产物

outputs:
  - path: deployment-report.json
    description: 部署报告
```

---

## 🎯 执行 Workflow

### 1. 初始化 Workflow

```bash
cd examples/stg-opportunity-discovery-demo
python -m flowcore.orchestrator.cli init
```

### 2. 运行步骤

```bash
# 方法 1: 使用 CLI
python -m flowcore.orchestrator.cli run search_signals

# 方法 2: 使用 Python API
from flowcore.api import api_run_step
result = api_run_step(".", "search_signals")

# 方法 3: 自动执行下一步
from flowcore.api import api_next_step
result = api_next_step(".")
```

---

## 📚 示例项目

### STG 商业机会发现

```bash
cd examples/stg-opportunity-discovery-demo
python test_workflow.py
```

### PM Gate 集成

```bash
cd examples/pm-gate-integration-demo
python test_pm_gate_integration.py
```

---

## 🔍 故障排查

### 问题 1: LLM 调用失败

```bash
# 检查 Antigravity 反代
curl http://127.0.0.1:8045/v1/models

# 检查环境变量
echo $OPENAI_BASE_URL
echo $OPENAI_API_KEY
```

### 问题 2: MCP Server 连接失败

```bash
# 检查 MCP Server
curl http://localhost:3000/health

# 重启 MCP Server
python scripts/run_mock_mcp.py
```

### 问题 3: 导入错误

```bash
# 设置 PYTHONPATH
export PYTHONPATH="./src:."
# 或
set PYTHONPATH=src;.

# Windows (CMD)
set PYTHONPATH=src;.

# Windows (PowerShell)
$env:PYTHONPATH="src;."
```

---

## 📖 文档索引

- **环境搭建**: `docs/LOCAL-ENVIRONMENT-SETUP-COMPLETE.md`
- **PM Agent 使用**: `docs/PM-AGENT-USER-GUIDE.md`
- **PM Agent 协议**: `docs/PM_AGENT_PROTOCOL.md`
- **Orchestrator 架构**: `docs/Orchestrator-Architecture.md`
- **API 参考**: `flowcore/api.py`

---

## 🎉 开始使用

环境已就绪，测试已通过。现在可以：

1. ✅ 创建自定义 Agent
2. ✅ 创建自定义 Skill
3. ✅ 运行 Workflow
4. ✅ 集成到你的项目

**祝使用愉快！** 🚀
