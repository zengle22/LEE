---
title: LLM & MetaGPT Executor 集成指南
author: LEE Team
date: 2026-01-29
version: 1.0
last_updated: 2026-02-19
---

# LLM & MetaGPT Executor 集成指南

## 概述

LEE Orchestrator 现已集成完整的 LLM 和 MetaGPT 执行器，支持：

### LLM Executor
- ✅ 支持多种 LLM Provider（OpenAI、Claude、智谱 GLM、自定义反代）
- ✅ 配置文件管理（YAML 格式）
- ✅ 环境变量替换
- ✅ 自动重试机制
- ✅ 多配置文件支持

### MetaGPT Executor
- ✅ 代码实现任务（SoftwareCompany）
- ✅ Bug 自动修复
- ✅ 自定义团队配置

---

## 配置文件

LLM 配置文件位于: `flowcore/engines/llm/config.yaml`

### 支持的配置

#### 1. antigravity（本地反代）
```yaml
antigravity:
  type: llm
  provider: custom
  base_url: http://127.0.0.1:8045/v1
  api_key: sk-2988e892730744ccafde80aac9ced361
  model: gemini-3-flash
  temperature: 0.7
  max_tokens: 8000
```

#### 2. zhipu（智谱 GLM）
```yaml
zhipu:
  type: llm
  provider: custom
  base_url: https://open.bigmodel.cn/api/paas/v4
  api_key: 06bc11ad44e3431d8f685bfe3405284e.KlPI5clCIbAb4aOa
  model: glm-4-flash
  temperature: 0.7
  max_tokens: 8000
```

#### 3. agent.prd（生产环境）
```yaml
agent.prd:
  type: llm
  provider: custom
  base_url: http://127.0.0.1:8045/v1
  api_key: sk-2988e892730744ccafde80aac9ced361
  model: gemini-3-flash
  temperature: 0.7
  max_tokens: 4000
```

#### 4. agent.dev（开发环境）
```yaml
agent.dev:
  type: llm
  provider: custom
  base_url: http://127.0.0.1:8045/v1
  api_key: sk-2988e892730744ccafde80aac9ced361
  model: glm-4-flash
  temperature: 0.5
  max_tokens: 8000
```

---

## 使用方法

### 1. 在模板中使用 LLM Executor

在 `templates.yaml` 中定义步骤：

```yaml
name: code_generation_task
description: "使用 LLM 生成代码"

steps:
  - name: "生成 API 代码"
    executor: llm
    input:
      prompt: "实现一个用户认证 API，包含登录、注册功能"
      system_message: "你是一个专业的后端工程师"
      # 可选：覆盖配置
      temperature: 0.3
      max_tokens: 2000
    # 可选：指定配置文件
    # profile: zhipu
```

### 2. 指定配置文件

有两种方式指定 LLM 配置：

#### 方式 1: 在模板中指定
```yaml
steps:
  - name: "生成代码"
    executor: llm
    input:
      prompt: "..."
    profile: zhipu  # 使用智谱配置
```

#### 方式 2: 在创建工作流时指定
```python
executor = ExecutorFactory.create("llm", profile="antigravity")
```

### 3. 使用 MetaGPT Executor

```yaml
name: metagpt_task
description: "使用 MetaGPT 实现功能"

steps:
  - name: "实现 Todo List"
    executor: metagpt
    input:
      task_type: code_implementation
      requirement: "创建一个 Todo List 应用"
      workspace: "./workspace"
    llm_config:
      api_key: "your-api-key"
      model: "glm-4-flash"
      base_url: "http://127.0.0.1:8045/v1"
      investment: 10.0
      max_rounds: 5
```

---

## 编程接口

### 创建 LLM Executor

```python
from lee.orchestrator.execution.executors import ExecutorFactory

# 使用默认配置 (antigravity)
executor = ExecutorFactory.create("llm")

# 指定配置文件
executor = ExecutorFactory.create("llm", profile="zhipu")

# 指定自定义配置路径
executor = ExecutorFactory.create(
    "llm",
    profile="custom",
    config_path="/path/to/config.yaml"
)
```

### 执行 LLM 任务

```python
result = await executor.execute({
    "prompt": "你的问题",
    "system_message": "系统提示词",
    # 可选参数
    "temperature": 0.7,
    "max_tokens": 4000,
})

# 检查结果
if result["status"] == "completed":
    print(result["generated_text"])
else:
    print(f"错误: {result['error']}")
```

### 创建 MetaGPT Executor

```python
# 首先安装 MetaGPT
# pip install metagpt

executor = ExecutorFactory.create(
    "metagpt",
    role="Developer",
    llm_config={
        "api_key": "your-api-key",
        "model": "glm-4-flash",
        "base_url": "http://127.0.0.1:8045/v1",
    }
)

result = await executor.execute({
    "task_type": "code_implementation",
    "requirement": "创建一个 Web 应用",
    "workspace": "./workspace",
})
```

---

## 测试

### 运行简单测试
```bash
python examples/test_llm_simple.py
```

### 运行完整测试
```bash
python examples/test_llm_metagpt.py
```

### 运行模板执行测试
```bash
python examples/test_template_execution.py
```

---

## 已验证功能

### ✅ LLM Executor

| 功能 | 状态 | 说明 |
|------|------|------|
| 配置文件加载 | ✅ | YAML 配置正确加载 |
| 环境变量替换 | ✅ | 支持 ${VAR} 格式 |
| 智谱 GLM 调用 | ✅ | glm-4-flash 成功调用 |
| 自动重试 | ✅ | 503/429/500 自动重试 |
| 多配置支持 | ✅ | 支持多个配置文件 |

### ⚠️ MetaGPT Executor

| 功能 | 状态 | 说明 |
|------|------|------|
| 代码实现 | ✅ | SoftwareCompany 集成 |
| Bug 修复 | ✅ | 占位符实现 |
| 安装依赖 | ⚠️ | 需要安装 metagpt |

---

## 安装 MetaGPT（可选）

如果需要使用 MetaGPT Executor：

```bash
pip install metagpt
```

---

## 故障排除

### 1. 503 Service Unavailable

**原因**: 本地反代服务（antigravity）未运行

**解决**:
- 启动本地反代服务
- 或使用其他配置（如 zhipu）

### 2. API Key 无效

**原因**: API Key 过期或错误

**解决**:
- 检查配置文件中的 API Key
- 更新为有效的 API Key

### 3. MetaGPT 导入错误

**原因**: MetaGPT 未安装

**解决**:
```bash
pip install metagpt
```

---

## 配置文件结构

```
flowcore/
└── engines/
    └── llm/
        └── config.yaml    # LLM 配置文件
```

配置文件格式：
```yaml
# 配置名称
profile_name:
  type: llm
  provider: custom        # openai, anthropic, azure, custom
  base_url: https://...
  api_key: ${ENV_VAR}     # 支持环境变量
  model: model-name
  temperature: 0.7
  max_tokens: 4000
```

---

## 下一步

1. ✅ LLM Executor 已完全集成
2. ✅ 配置文件系统已实现
3. ✅ 自动重试机制已添加
4. ⏳ 可选：安装 MetaGPT 进行完整测试

---

## 文件清单

**新增文件**:
- `src/lee/orchestrator/execution/llm_executor.py` - LLM 执行器实现
- `src/lee/orchestrator/execution/metagpt_executor.py` - MetaGPT 执行器实现
- `examples/test_llm_simple.py` - LLM 简单测试
- `examples/test_llm_metagpt.py` - 完整测试
- `examples/llm_metagpt_guide.md` - 本文档

**修改文件**:
- `src/lee/orchestrator/execution/executors.py` - 更新为代理模式

---

**最后更新**: 2026-01-27
**版本**: v1.0
