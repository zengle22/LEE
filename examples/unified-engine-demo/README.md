---
title: Orchestrator 统一 Engine 接口 - 完整示例
author: LEE Team
date: 2026-01-29
version: 1.0
last_updated: 2026-02-19
---

# Orchestrator 统一 Engine 接口 - 完整示例

本示例展示如何使用统一的 Engine 接口执行工作流。

## 目录结构

```
examples/unified-engine-demo/
├── workflow.yaml           # 工作流定义
├── agents/
│   ├── writer/
│   │   └── agent.yaml     # Writer Agent 规范
│   └── reviewer/
│       └── agent.yaml     # Reviewer Agent 规范
└── README.md              # 本文件
```

## 工作流定义 (workflow.yaml)

```yaml
id: unified-engine-demo
name: 统一 Engine 接口演示
version: "1.0"

description: |
  演示如何使用 Orchestrator 的统一 Engine 接口
  执行工作流，支持多种执行引擎（LLM、MetaGPT 等）

steps:
  # 示例 1: 使用 LLM Engine（直接调用 OpenAI API）
  - id: step1_write_doc
    name: 编写文档
    description: |
      使用 LLM Engine 生成一个简单的 Markdown 文档。
      这是默认的引擎，直接调用 OpenAI GPT-4 API。
    run: agent:writer
    engine:
      type: llm
      provider: openai
      model: gpt-4
      api_key: ${OPENAI_API_KEY}  # 从环境变量读取
      temperature: 0.7
    system_prompt: |
      你是一个专业的技术文档编写者。
      你的任务是生成清晰、准确的技术文档。
    inputs:
      - description: "无需输入"
    outputs:
      - path: output/guide.md
        required: true
        description: "生成的 Markdown 文档"

  # 示例 2: 使用 MetaGPT Engine（如果已安装）
  - id: step2_review_doc
    name: 审查文档
    description: |
      使用 MetaGPT Engine 审查文档质量。
      需要安装 MetaGPT: pip install metagpt
    run: agent:reviewer
    depends_on: [step1_write_doc]
    engine:
      type: metagpt
      role: DocumentationReviewer
      config:
        llm:
          model: gpt-4
          api_key: ${OPENAI_API_KEY}
    inputs:
      - source: step1_write_doc
        path: output/guide.md
        description: "需要审查的文档"
    outputs:
      - path: output/review.md
        required: true
        description: "审查报告"

  # 示例 3: 也可以用 LLM Engine 做审查（更简单）
  - id: step2_simple_review
    name: 简单审查
    description: 使用 LLM Engine 进行简单的文档审查
    run: agent:reviewer
    depends_on: [step1_write_doc]
    engine:
      type: llm
      provider: openai
      model: gpt-4
    system_prompt: |
      你是一个文档审查专家。
      你的任务是审查技术文档的质量，
      检查内容的准确性、完整性和可读性。
    inputs:
      - source: step1_write_doc
        path: output/guide.md
    outputs:
      - path: output/review.md
        required: true
```

## Agent 规范示例

### Writer Agent (agents/writer/agent.yaml)

```yaml
kind: agent
id: writer
name: 文档编写者
version: "1.0.0"

description: |
  使用 LLM 编写技术文档的 Agent

engine:
  type: llm
  provider: openai
  model: gpt-4
  api_key: ${OPENAI_API_KEY}
  temperature: 0.7
  max_tokens: 4000

system_prompt: |
  你是一个专业的技术文档编写者。

  你的职责：
  - 生成清晰、准确的技术文档
  - 使用 Markdown 格式
  - 包含代码示例和使用说明
  - 确保内容的准确性和完整性

  写作风格：
  - 结构清晰，层次分明
  - 语言简洁，避免冗余
  - 提供实用的示例

instructions:
  - "文档必须包含：简介、安装指南、使用示例、API 参考"
  - "使用标准 Markdown 格式"
  - "代码示例使用语法高亮"
  - "添加必要的注释和说明"

quality_bar:
  - "文档结构完整"
  - "代码示例可运行"
  - "无拼写和语法错误"

forbidden_behaviors:
  - id: "skip_examples"
    name: "跳过代码示例"
    description: "不允许缺少代码示例"

responsibility:
  input_schema:
    type: object
    properties:
      topic:
        type: string
        description: "文档主题"
  output_schema:
    type: object
    required:
      - markdown_document
    properties:
      markdown_document:
        type: string
        description: "生成的 Markdown 文档"
```

### Reviewer Agent (agents/reviewer/agent.yaml)

```yaml
kind: agent
id: reviewer
name: 文档审查者
version: "1.0.0"

description: |
  审查技术文档质量的 Agent

engine:
  type: llm
  provider: openai
  model: gpt-4
  api_key: ${OPENAI_API_KEY}
  temperature: 0.3  # 较低的温度，更客观

system_prompt: |
  你是一个经验丰富的技术文档审查专家。

  你的职责：
  - 审查文档的准确性和完整性
  - 检查代码示例的正确性
  - 评估文档的可读性和结构
  - 提供改进建议

  审查维度：
  1. 内容准确性
  2. 结构完整性
  3. 代码质量
  4. 语言表达
  5. 排版格式

instructions:
  - "提供具体的审查意见"
  - "指出需要改进的地方"
  - "如果文档质量很高，也要肯定优点"

quality_bar:
  - "审查意见具体、可操作"
  - "覆盖所有审查维度"
  - "提供改进建议"

forbidden_behaviors:
  - id: "vague_feedback"
    name: "模糊的反馈"
    description: "不允许给出模糊不清的审查意见"
```

## 快速开始（两种方式）

### 方式 1: Mock 测试（推荐，无需 API Key）

```bash
cd examples/unified-engine-demo

# 运行 Mock 测试（不需要真实 API Key）
python test_mock.py
```

**预期输出**：
```
============================================================
  Orchestrator 统一 Engine 接口 - Mock 测试
============================================================

ℹ️  使用 Mock LLM Executor，不需要真实的 API Key
ℹ️  1. 检查环境...
✅ 工作流初始化完成
ℹ️  2. 执行步骤 1: 编写文档 (Mock)...
✅ 步骤 1 完成
ℹ️  3. 执行步骤 2: 审查文档 (Mock)...
✅ 步骤 2 完成
✅ Mock 测试成功！
```

### 方式 2: 真实 LLM API（需要 API Key）

```bash
# 1. 设置 OpenAI API Key
export OPENAI_API_KEY="sk-..."

# 2. 运行真实 Demo
python run_demo.py
```

## 与旧方式的对比

### 旧方式（需要外部 AI 工具）

```bash
# 1. Orchestrator 注入上下文
python -m flowcore.orchestrator start . step1

# 2. 用户在 Claude Code 中手动执行任务
# 3. 用户手动完成步骤
python -m flowcore.orchestrator complete . step1 --outputs output/guide.md
```

### 新方式（统一 Engine 接口）

```bash
# 一键完成：Orchestrator 自动调用 Engine 执行
python -m flowcore.orchestrator run-engine . step1
```

## 优势

1. **更简单**：不需要外部 AI 工具，一行命令完成执行
2. **更可靠**：Engine 接口统一，易于切换不同引擎
3. **更可控**：完全自动化执行，可集成到 CI/CD
4. **更灵活**：支持多种 Engine（LLM、MetaGPT、自定义）

## 扩展：自定义 Engine

如果需要添加自定义 Engine，请参考：

- `flowcore/engines/base.py` - Executor 基类
- `flowcore/engines/llm/executor.py` - LLM Executor 示例
- `flowcore/engines/metagpt/executor_v2.py` - MetaGPT Executor 示例

实现步骤：

1. 继承 `AbstractExecutor`
2. 实现 `execute` 方法
3. 注册到 `EngineRegistry`
4. 在 agent.yaml 中配置

## 故障排除

### 问题 1: Engine not found

```
❌ Unknown engine type: 'xxx'
```

**解决**：
- 检查 engine.type 是否正确
- 确认 Engine 模块已正确导入
- 查看已注册的 Engine：`EngineRegistry.list_engines()`

### 问题 2: API key not found

```
❌ API key not found
```

**解决**：
- 设置环境变量：`export OPENAI_API_KEY="sk-..."`
- 或在 agent.yaml 中配置 `engine.api_key`

### 问题 3: MetaGPT not installed

```
❌ MetaGPT is not installed
```

**解决**：
```bash
pip install metagpt
```

## 下一步

- 查看 `docs/Orchestrator-Complete-Guide.md` 了解更多
- 查看 `docs/Orchestrator-Architecture.md` 了解架构
- 查看 `examples/` 目录中的更多示例
