# PM Agent LLM 配置优化指南

> **作者**: LEE Team
> **日期**: 2026-02-21
> **版本**: v1.0.0
> **分类**: 开发文档

## 📍 当前使用的模型

根据 `chat.py` 的自动检测逻辑，当前使用的模型优先级：

1. **deepseek** (DeepSeek-Chat) ← 当前使用
2. zhipu (智谱 GLM-5)
3. huawei_deepseek (华为 DeepSeek-R1)

### 当前配置详情

```yaml
deepseek:
  provider: deepseek
  model: deepseek-chat        # DeepSeek V3
  base_url: https://api.deepseek.com
  temperature: 0.1            # ← 温度太低！
  max_tokens: 8192
```

---

## 🤔 为什么感觉"弱智"？

### 问题 1: Temperature 太低

**当前**: `temperature: 0.1`

**问题**:
- Temperature 控制输出的随机性
- 0.1 太低，导致模型过于保守
- 回答机械、缺乏灵活性

**建议**: `temperature: 0.5 - 0.7`

### 问题 2: Max Tokens 限制

**当前**: `max_tokens: 8192`

**问题**:
- 对于复杂任务可能不够
- 限制了对上下文的理解

**建议**: `max_tokens: 16000`

### 问题 3: Prompt 简单

**当前 Prompt**:
```
You are an intent classifier for the LEE workflow system.
...
Keep reasoning brief and factual
```

**问题**:
- 没有提供足够的上下文
- 没有示例 (few-shot)
- 指令过于简单

---

## 🚀 优化方案

### 方案 1: 使用更好的模型（推荐）

```yaml
# 选项 A: GPT-4o（最强，但贵）
export LLM_API_KEY=your-openai-key
export LLM_BASE_URL=https://api.openai.com/v1
export LLM_MODEL=gpt-4o
lee chat

# 选项 B: Claude Sonnet 4.5（平衡）
export ANTHROPIC_API_KEY=your-anthropic-key
export LLM_BASE_URL=https://api.anthropic.com/v1
export LLM_MODEL=claude-sonnet-4-5-20250514
lee chat

# 选项 C: DeepSeek V3（性价比）
# 已配置，只需优化 temperature
```

### 方案 2: 优化当前 DeepSeek 配置

编辑 `config/llm_config.yaml`:

```yaml
deepseek:
  provider: deepseek
  base_url: https://api.deepseek.com
  api_key: sk-32763972ec7841aab1b45af0ca2c97d3
  model: deepseek-chat
  temperature: 0.6          # ← 提高到 0.6
  max_tokens: 16000         # ← 增加到 16k
  timeout: 300
```

### 方案 3: 使用环境变量覆盖（快速）

```bash
# 创建 .env 文件
cat > .env << EOF
# LLM 配置
LLM_PROFILE=deepseek
LLM_TEMPERATURE=0.6
LLM_MAX_TOKENS=16000

# 或使用其他模型
# LLM_PROFILE=openai
# LLM_API_KEY=sk-your-key
# LLM_MODEL=gpt-4o
EOF

# 加载环境变量
source .env
lee chat
```

---

## 📊 模型对比

| 模型 | 智能 | 速度 | 成本 | 推荐场景 |
|------|------|------|------|----------|
| **GPT-4o** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 💰💰💰 | 复杂任务 |
| **Claude Sonnet 4.5** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 💰💰 | 推荐！ |
| **DeepSeek V3** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 💰 | 性价比 |
| **智谱 GLM-5** | ⭐⭐⭐ | ⭐⭐⭐⭐ | 💰 | 中文场景 |
| **DeepSeek-R1** | ⭐⭐⭐⭐ | ⭐⭐ | 💰 | 推理任务 |

---

## 🔧 立即优化

### 快速修复（1分钟）

```bash
# 方法 1: 环境变量
export LLM_TEMPERATURE=0.6
export LLM_MAX_TOKENS=16000
lee chat

# 方法 2: 修改配置文件
# 编辑 config/llm_config.yaml
# 找到 deepseek 部分
# 修改 temperature: 0.6
# 修改 max_tokens: 16000
```

### 完整优化（5分钟）

```bash
# 1. 选择模型
# 选项 A: 使用 GPT-4o
export LLM_PROFILE=openai
export LLM_API_KEY=sk-...
export LLM_MODEL=gpt-4o

# 选项 B: 使用 Claude
export LLM_PROFILE=anthropic
export ANTHROPIC_API_KEY=sk-ant-...
export LLM_MODEL=claude-sonnet-4-5-20250514

# 选项 C: 优化 DeepSeek
export LLM_TEMPERATURE=0.6
export LLM_MAX_TOKENS=16000

# 2. 启动 Chat
lee chat

# 3. 测试
Lee> 帮我分析一下当前工作流的状态，并建议下一步应该做什么
```

---

## 💡 Prompt 优化建议

### 当前 Prompt（简单）

```
You are an intent classifier for the LEE workflow system.
...
Keep reasoning brief and factual
```

### 优化 Prompt（建议）

```
You are an intelligent assistant for the LEE workflow system.

Your role:
- Understand user intent from natural language
- Extract relevant parameters (workflow IDs, step IDs, etc.)
- Provide helpful suggestions when appropriate

Context:
- User is managing software development workflows
- Common tasks: run workflows, approve gates, check status
- Be concise but helpful

Available intents:
- query_status: Query workflow status
- execute_step: Run workflow steps
- approve_gate: Approve human gates
- reject_gate: Reject human gates
- list_workflows: List available workflows
- show_help: Show help information

Think step-by-step and provide reasoning.
```

---

## 🎯 推荐配置

### 开发环境（免费/快速）

```bash
# 使用 Ollama 本地模型
export LLM_PROFILE=ollama
export OLLAMA_MODEL=qwen2.5
lee chat
```

### 生产环境（性价比）

```bash
# 使用 DeepSeek（已优化）
export LLM_PROFILE=deepseek
export LLM_TEMPERATURE=0.6
export LLM_MAX_TOKENS=16000
lee chat
```

### 高级用户（最佳体验）

```bash
# 使用 Claude Sonnet 4.5
export LLM_PROFILE=anthropic
export ANTHROPIC_API_KEY=sk-ant-...
export LLM_MODEL=claude-sonnet-4-5-20250514
export LLM_TEMPERATURE=0.7
export LLM_MAX_TOKENS=8000
lee chat
```

---

## 🔍 检查当前配置

```bash
# 查看当前使用的模型
python << 'EOF'
from lee.orchestrator.execution.llm_executor import LLMExecutor
executor = LLMExecutor(profile="deepseek")
print(f"Provider: {executor.config.get('provider')}")
print(f"Model: {executor.config.get('model')}")
print(f"Temperature: {executor.config.get('temperature')}")
print(f"Max Tokens: {executor.config.get('max_tokens')}")
EOF
```

---

## 📝 总结

### 为什么"弱智"？

1. **Temperature 太低** (0.1) → 改为 0.6
2. **Max Tokens 限制** (8192) → 改为 16000
3. **Prompt 简单** → 可以优化（需修改代码）
4. **模型选择** → DeepSeek V3 不错，但需要调参

### 立即行动

```bash
# 最简单的优化
export LLM_TEMPERATURE=0.6
lee chat

# 或者使用更好的模型
export LLM_PROFILE=anthropic
export ANTHROPIC_API_KEY=your-key
lee chat
```

---

**配置文件**: `config/llm_config.yaml`
**环境文件**: `.env`
**文档**: `docs/features/pm-agent/LLM-SETUP-GUIDE.md`
