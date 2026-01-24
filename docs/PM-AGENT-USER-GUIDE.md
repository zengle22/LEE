# PM Agent 使用指南

本文档详细介绍 LEE 系统中顶层 PM Agent 的使用方法和 Orchestrator 支持的执行器。

---

## 📖 目录

1. [PM Agent 概述](#pm-agent-概述)
2. [PM Agent 的职责](#pm-agent-的职责)
3. [PM Agent 使用方法](#pm-agent-使用方法)
4. [Orchestrator 支持的执行器](#orchestrator-支持的执行器)
5. [完整示例](#完整示例)

---

## PM Agent 概述

### 什么是 PM Agent？

PM Agent（Project Manager Agent）是 LEE 系统的顶层智能体，扮演项目总监的角色。它运行在 Claude Code 中，负责"看状态 + 做决策"，但不直接动手执行任务。

### 架构定位

```
┌─────────────────────────────────────────┐
│         Claude Code (用户界面)           │
│                                         │
│  ┌─────────────┐      ┌─────────────┐  │
│  │ PM Session  │      │Gate Session │  │
│  │  (PM Agent) │      │(Gate Agent) │  │
│  └──────┬──────┘      └──────┬──────┘  │
│         │                    │         │
└─────────┼────────────────────┼─────────┘
          │                    │
          ▼                    ▼
    ┌─────────────────────────────┐
    │      Orchestrator           │
    │  ┌─────────────────────┐    │
    │  │   State Machine     │    │
    │  │   Workflow Parser   │    │
    │  │   Engine Commands   │    │
    │  └─────────────────────┘    │
    └─────────────┬───────────────┘
                  │
      ┌───────────┼───────────┐
      ▼           ▼           ▼
   ┌─────┐   ┌─────┐   ┌─────┐
   │ LLM │   │Shell│   │ MCP │
   └─────┘   └─────┘   └─────┘
```

---

## PM Agent 的职责

### ✅ 你可以做的事情

1. **查看项目状态**
   - 哪些步骤已完成
   - 哪些步骤 ready（可执行）
   - 当前阻塞点在哪里

2. **阅读关键产物摘要**
   - 系统会自动提供产物的简要说明
   - 包括：路径、类型、摘要

3. **做出决策**
   - 决定下一步执行哪个步骤
   - 决定是否需要人工介入
   - 决定是否重试失败的步骤

4. **调用工具**
   - `orchestrator_get_state` - 获取状态
   - `orchestrator_run_step` - 执行特定步骤
   - `orchestrator_next` - 自动执行下一步

### ❌ 你不能做的事情

1. **不要直接修改项目文件**
   - 所有文件修改由 Orchestrator 处理
   - 你只负责决策

2. **不要直接执行 Shell 命令**
   - 不要运行 pytest/git/build 等命令
   - 这些由 Shell Executor 处理

3. **不要直接调用外部系统**
   - 不要直接调用 CI/K8s/Figma
   - 这些通过 MCP Executor 处理

4. **不要宣称步骤已完成**
   - 完成情况由系统执行结果决定
   - 你只负责"发起请求"和"解释结果"

---

## PM Agent 使用方法

### 1. 获取工作流状态

使用 `api_get_state()` 或 `pm_workflow_handler(action="get_state")`:

```python
from flowcore.api import api_get_state

state = api_get_state(".")

# 返回结果示例：
{
    "workflow_id": "stg-opportunity-discovery",
    "workflow_name": "商业机会发现工作流",
    "run_id": "run-20250123-001",
    "total_steps": 7,
    "completed_steps": 2,
    "failed_steps": 0,
    "ready_steps": ["analyze_user_signals", "analyze_industry_structure", "analyze_supply_competition"],
    "steps": [
        {
            "id": "search_signals",
            "name": "搜索采集",
            "kind": "agent",
            "status": "completed",
            "description": "采集市场搜索信号",
            "is_ready": False,
            "is_human_gate": False
        },
        {
            "id": "analyze_user_signals",
            "name": "用户信号分析",
            "kind": "agent",
            "status": "pending",
            "description": "分析谁在搜&为什么",
            "is_ready": True,
            "is_human_gate": False
        },
        # ... 更多步骤
    ],
    "human_gates": ["freeze_approval"],
    "project_dir": ".",
    "timestamp": "2025-01-23T10:30:00"
}
```

### 2. 列出就绪步骤

使用 `api_list_ready_steps()` 或 `pm_workflow_handler(action="list_ready_steps")`:

```python
from flowcore.api import api_list_ready_steps

ready_steps = api_list_ready_steps(".")

# 返回结果示例：
[
    {
        "id": "analyze_user_signals",
        "name": "用户信号分析",
        "kind": "agent",
        "description": "分析谁在搜&为什么",
        "dependencies": ["search_signals"]
    },
    {
        "id": "analyze_industry_structure",
        "name": "行业结构分析",
        "kind": "agent",
        "description": "分析行业所处阶段",
        "dependencies": ["search_signals"]
    },
    {
        "id": "analyze_supply_competition",
        "name": "供给竞争分析",
        "kind": "agent",
        "description": "分析现有方案解决得如何",
        "dependencies": ["search_signals"]
    }
]
```

### 3. 执行特定步骤

使用 `api_run_step()` 或 `pm_workflow_handler(action="run_step", step_id="...")`:

```python
from flowcore.api import api_run_step

result = api_run_step(".", "analyze_user_signals")

# 返回结果示例：
{
    "status": "completed",
    "step_id": "analyze_user_signals",
    "outputs": [
        ".workflow/steps/analyze_user_signals/user_hypothesis.json",
        ".workflow/steps/analyze_user_signals/analysis_report.md"
    ],
    "messages": [
        {
            "role": "system",
            "content": "分析用户搜索意图和痛点..."
        },
        {
            "role": "assistant",
            "content": "根据搜索信号分析，目标用户是..."
        }
    ],
    "duration_seconds": 45.2,
    "engine_type": "llm",
    "timestamp": "2025-01-23T10:31:00"
}
```

### 4. 自动执行下一步

使用 `api_next_step()` 或 `pm_workflow_handler(action="next_step")`:

```python
from flowcore.api import api_next_step

result = api_next_step(".")

# 系统会自动选择第一个就绪步骤执行
# 返回结果同 api_run_step
```

### 5. 典型工作循环

```python
from flowcore.api import api_get_state, api_list_ready_steps, api_run_step

# 1. 查看当前状态
state = api_get_state(".")
print(f"进度: {state['completed_steps']}/{state['total_steps']}")

# 2. 列出就绪步骤
ready_steps = api_list_ready_steps(".")
print(f"就绪步骤: {len(ready_steps)}")

# 3. 决策：执行哪个步骤？
if ready_steps:
    # 选择第一个就绪步骤
    step_id = ready_steps[0]['id']
    print(f"执行: {step_id}")

    # 4. 执行步骤
    result = api_run_step(".", step_id)

    # 5. 处理结果
    if result['status'] == 'completed':
        print(f"✅ 完成: {result['outputs']}")
    elif result['status'] == 'failed':
        print(f"❌ 失败: {result['error']}")
        # 决定是否重试或等待人工介入
```

---

## Orchestrator 支持的执行器

Orchestrator 目前支持 **4 种执行器**：

### 1. LLM Executor - 大模型执行器

**用途**: 直接调用大模型 API 进行推理和生成

**支持的 Provider**:
- OpenAI (GPT-4, GPT-3.5)
- Anthropic (Claude)
- Azure OpenAI
- 其他兼容 OpenAI API 的服务

**配置示例** (`agent.yaml`):

```yaml
kind: agent
id: agent.prd.prd_writer
version: 1.0

engine:
  type: llm
  provider: openai          # openai, anthropic, azure, custom
  model: gpt-4
  api_key: ${OPENAI_API_KEY}  # 或从环境变量读取
  base_url: https://api.openai.com/v1  # 可选
  temperature: 0.7
  max_tokens: 4000

system_prompt: |
  你是专业的 PRD 撰写专家...
```

**工作流程**:
1. 构建系统提示词和用户消息
2. 调用 LLM API
3. 保存响应到 `.workflow/steps/{step_id}/response.txt`
4. 返回执行结果

**使用场景**:
- 文档生成（PRD、技术方案）
- 代码生成
- 分析和推理任务
- 创意生成

---

### 2. Shell Executor - Shell 命令执行器

**用途**: 执行本地 Shell 命令和脚本

**支持的操作**:
- 运行测试（pytest, npm test）
- 构建项目（npm build, make, cargo build）
- 部署操作（kubectl, docker）
- 其他确定性操作

**配置示例** (`skill.yaml`):

```yaml
kind: skill
id: dev.run_tests
version: 1.0

engine:
  type: shell
  command: |
    cd {{ project_dir }} && \
    pytest --maxfail=1 -q \
      --junitxml=reports/unit_test_report.xml
  timeout: 300               # 超时时间（秒），默认 300
  shell: /bin/bash            # 可选，默认 /bin/sh
  working_dir: {{ project_dir }}
  env:                        # 额外的环境变量
    TEST_ENV: ci
```

**支持的变量替换**:
- `{{ project_dir }}` - 项目目录
- `{{ step_id }}` - 步骤 ID
- `{{ run_id }}` - 运行 ID
- `{{ENV_VAR}}` - 环境变量

**工作流程**:
1. 解析命令模板，替换变量
2. 创建子进程执行命令
3. 捕获 stdout 和 stderr
4. 保存输出到工作目录
5. 根据返回码判断成功/失败

**输出文件**:
- `.workflow/steps/{step_id}/stdout.txt`
- `.workflow/steps/{step_id}/stderr.txt`

**使用场景**:
- 单元测试、集成测试
- 代码质量检查（linting）
- 项目构建
- Docker/K8s 操作

---

### 3. MCP Executor - MCP 协议执行器

**用途**: 通过 MCP (Model Context Protocol) 调用远程服务

**支持的服务**:
- CI/CD 系统（Jenkins, GitLab CI）
- 容器编排（Kubernetes）
- 设计工具（Figma）
- 其他 HTTP API 服务

**配置示例** (`skill.yaml`):

```yaml
kind: skill
id: ci.deploy
version: 1.0

engine:
  type: mcp
  server_url: http://localhost:3000/mcp
  tool: deploy
  timeout: 600
  auth_token: ${MCP_AUTH_TOKEN}  # 可选
  arguments:
    environment: staging
    project: {{ project_dir }}
    branch: main
  context:
    - build_number
    - commit_sha
```

**工作流程**:
1. 构建参数（支持变量替换）
2. 发送 MCP 请求：`POST {server_url}/tools/{tool_name}`
3. 等待响应
4. 保存结果到 `.workflow/steps/{step_id}/result.json`

**使用场景**:
- CI/CD 部署
- K8s 资源管理
- Figma 设计导出
- 第三方服务集成

---

### 4. MetaGPT Executor - MetaGPT 多智能体执行器

**用途**: 调用 MetaGPT 框架进行多智能体协作

**注意**: MetaGPT 是可选依赖，如果未安装则不可用

**配置示例** (`agent.yaml`):

```yaml
kind: agent
id: dev.tech_architect
version: 1.0

engine:
  type: metagpt
  scenario: technical_design  # 场景名称
  role: architect             # 角色
  enable_human_interaction: false

system_prompt: |
  你是技术架构专家...
```

**支持的场景** (根据 MetaGPT 定义):
- 技术设计
- 代码生成
- 文档生成
- 等

**使用场景**:
- 复杂的多智能体协作任务
- 需要角色分工的场景
- MetaGPT 生态集成

---

## 执行器对比

| 特性 | LLM | Shell | MCP | MetaGPT |
|------|-----|-------|-----|---------|
| **用途** | 推理生成 | 命令执行 | 服务调用 | 多智能体 |
| **主要场景** | 文档/代码 | 测试/构建 | CI/CD/K8s | 复杂协作 |
| **输入** | Prompt | 命令 | 参数 | 场景+角色 |
| **输出** | 文本响应 | stdout/stderr | JSON结果 | 多agent输出 |
| **依赖** | LLM API | 本地环境 | MCP服务 | MetaGPT |
| **异步** | ✅ | ✅ | ✅ | ✅ |
| **超时控制** | ❌ | ✅ | ✅ | ✅ |

---

## 完整示例

### 示例 1: STG 商业机会发现工作流

```python
from flowcore.api import (
    api_get_state,
    api_list_ready_steps,
    api_run_step,
    api_next_step
)

# 项目目录
project_dir = "spec-global/departments/stg"

# 1. 查看初始状态
state = api_get_state(project_dir)
print(f"工作流: {state['workflow_name']}")
print(f"总步骤: {state['total_steps']}")

# 2. Layer 1: 执行搜索采集
print("\n▶ Layer 1: 搜索采集")
result = api_run_step(project_dir, "search_signals")
if result['status'] == 'completed':
    print(f"✅ 采集完成: {len(result['outputs'])} 个输出")

# 3. Layer 2: 并行执行三个分析步骤
print("\n▶ Layer 2: 分析层（并行）")
ready_steps = api_list_ready_steps(project_dir)
print(f"就绪步骤: {[s['id'] for s in ready_steps]}")

for step in ready_steps:
    result = api_run_step(project_dir, step['id'])
    print(f"  ✅ {step['name']} 完成")

# 4. Layer 3: 检查是否需要人工审批
print("\n▶ Layer 3: 冻结审批")
state = api_get_state(project_dir)
pending_gates = [s for s in state['steps'] if s['is_human_gate'] and s['status'] == 'pending_human']

if pending_gates:
    print(f"⏸️  需要人工审批: {pending_gates[0]['id']}")
    print("   请切换到 Gate Session 进行审批")
else:
    print("✅ 无需审批，继续执行")

# 5. Layer 4-5: 继续后续步骤
print("\n▶ Layer 4-5: 机会构建 & 产品交付")
result = api_next_step(project_dir)
while result['status'] == 'completed':
    print(f"  ✅ {result['step_id']} 完成")
    result = api_next_step(project_dir)

print("\n🎉 工作流执行完成！")
```

### 示例 2: 处理失败和重试

```python
from flowcore.api import api_run_step, api_get_state

# 执行一个可能失败的步骤
result = api_run_step(".", "run_unit_tests")

if result['status'] == 'failed':
    print(f"❌ 步骤失败: {result['error']}")

    # 分析失败原因
    error_details = result.get('error_details', {})
    print(f"错误类型: {error_details.get('exception_type')}")

    # 决策：是否重试？
    state = api_get_state(".")
    failed_steps = [s for s in state['steps'] if s['status'] == 'failed']

    if failed_steps:
        step_id = failed_steps[0]['id']

        # 检查是否可以重试
        retry_count = state.get('retry_count', {}).get(step_id, 0)

        if retry_count < 3:
            print(f"重试 {step_id} (第 {retry_count + 1} 次)")
            result = api_run_step(".", step_id)
        else:
            print(f"⚠️  已重试 {retry_count} 次，需要人工介入")
```

### 示例 3: 监控工作流进度

```python
from flowcore.api import api_get_state
import time

def monitor_workflow(project_dir: str, check_interval: int = 5):
    """监控工作流执行进度"""

    while True:
        state = api_get_state(project_dir)

        completed = state['completed_steps']
        total = state['total_steps']
        failed = state['failed_steps']

        print(f"进度: {completed}/{total} | 失败: {failed}")

        # 检查是否完成
        if completed == total:
            print("✅ 工作流完成！")
            break

        # 检查是否失败
        if failed > 0:
            print("❌ 有步骤失败，停止监控")
            break

        # 检查是否阻塞（等待人工）
        if not state['ready_steps']:
            print("⏸️  等待人工介入或无就绪步骤")
            break

        time.sleep(check_interval)

# 使用
monitor_workflow(".")
```

---

## 总结

### PM Agent 核心原则

1. **只决策，不执行**
   - 你负责"看状态 + 做决策"
   - Orchestrator 负责实际执行

2. **多用工具，少凭空想象**
   - 用 `api_get_state()` 查看真实状态
   - 不要假设系统状态

3. **清晰解释决策理由**
   - 每次决策都要说明原因
   - 便于人类理解和审计

### 执行器选择指南

- **LLM**: 需要推理、生成、分析
- **Shell**: 需要执行本地命令
- **MCP**: 需要调用远程服务
- **MetaGPT**: 需要多智能体协作

---

**文档版本**: v1.0
**最后更新**: 2025-01-23
