# LLM 配置指南

> **作者**: LEE Team
> **日期**: 2026-02-20
> **版本**: v1.0.0
> **分类**: 配置指南

## 📍 配置文件位置

配置文件位于：`config/llm_config.yaml`

---

## 🔧 配置方法

### 方法 1: 使用环境变量（推荐）

创建或编辑项目根目录的 `.env` 文件：

```bash
# 在项目根目录创建 .env 文件
cat > .env << 'EOF'
# LLM 配置 - 选择一个 Provider 配置即可

# ============================================
# 选项 1: 使用 DeepSeek（推荐，性价比高）
# ============================================
export LLM_PROFILE=deepseek
# 或者直接设置环境变量
export LLM_API_KEY=sk-your-deepseek-api-key
export LLM_BASE_URL=https://api.deepseek.com
export LLM_MODEL=deepseek-chat

# ============================================
# 选项 2: 使用智谱 GLM
# ============================================
# export LLM_PROFILE=zhipu
# 配置文件中已有 API key，直接使用即可

# ============================================
# 选项 3: 使用 OpenAI
# ============================================
# export LLM_PROFILE=openai
export LLM_API_KEY=sk-your-openai-api-key
export LLM_BASE_URL=https://api.openai.com/v1
export LLM_MODEL=gpt-4o

# ============================================
# 选项 4: 使用 Anthropic Claude
# ============================================
# export LLM_PROFILE=anthropic
export ANTHROPIC_API_KEY=sk-ant-your-anthropic-api-key
export LLM_BASE_URL=https://api.anthropic.com/v1
export LLM_MODEL=claude-sonnet-4-5-20250514

# ============================================
# 选项 5: 使用本地 Ollama（无需 API key）
# ============================================
# export LLM_PROFILE=ollama
# 确保 Ollama 服务运行在 localhost:11434
# export OLLAMA_BASE_URL=http://localhost:11434
# export OLLAMA_MODEL=qwen2.5
EOF
```

然后加载环境变量：

```bash
# 加载 .env 文件
source .env

# 或者在每次运行前加载
source .env && lee chat
```

### 方法 2: 直接编辑配置文件

编辑 `config/llm_config.yaml` 文件，修改 `default` 配置：

```yaml
default:
  type: llm
  provider: openai
  base_url: https://api.deepseek.com  # 修改为你的 API 地址
  api_key: sk-your-api-key-here       # 修改为你的 API key
  model: deepseek-chat                # 修改为你的模型
  temperature: 0.7
  max_tokens: 4000
  timeout: 60
```

**注意**：配置文件中已经包含了一些预配置的 Provider：

| Provider | 说明 | API Key 状态 |
|----------|------|--------------|
| `zhipu` | 智谱 GLM | ✅ 已配置 |
| `deepseek` | DeepSeek 官方 | ✅ 已配置 |
| `huawei_deepseek` | 华为 DeepSeek | ✅ 已配置 |
| `minimax` | MiniMax | ✅ 已配置 |
| `ollama` | 本地 Ollama | ⚠️ 需要本地服务 |
| `openai` | OpenAI | ❌ 需要配置 |
| `anthropic` | Anthropic Claude | ❌ 需要配置 |

---

## 🚀 快速开始

### 选项 1: 使用已配置的 Provider（最快）

配置文件中已经包含了可用的 API keys，你可以直接使用：

```bash
# 使用智谱 GLM
export LLM_PROFILE=zhipu
lee chat

# 或使用 DeepSeek
export LLM_PROFILE=deepseek
lee chat

# 或使用华为 DeepSeek
export LLM_PROFILE=huawei_deepseek
lee chat
```

### 选项 2: 使用本地 Ollama（零成本）

如果你本地安装了 Ollama：

```bash
# 启动 Ollama 服务
ollama serve

# 使用 Ollama
export LLM_PROFILE=ollama
lee chat
```

### 选项 3: 使用你自己的 API Key

```bash
# 设置你的 API key
export LLM_API_KEY=sk-your-api-key-here
export LLM_BASE_URL=https://api.openai.com/v1
export LLM_MODEL=gpt-4o

# 启动 chat
lee chat
```

---

## ✅ 验证配置

运行以下命令验证配置是否正确：

```bash
# 检查配置是否加载
python -c "
from lee.orchestrator.execution.llm_executor import LLMExecutor
import os
os.environ['LLM_PROFILE'] = 'deepseek'
try:
    executor = LLMExecutor(profile='deepseek')
    print('✓ LLM Executor 初始化成功')
    print(f'  Provider: {executor.config.get(\"provider\")}')
    print(f'  Model: {executor.config.get(\"model\")}')
    print(f'  Base URL: {executor.config.get(\"base_url\")}')
except Exception as e:
    print(f'✗ 初始化失败: {e}')
"
```

---

## 🎯 推荐配置

### 开发/测试环境

```bash
# 使用本地 Ollama（免费、快速、无限制）
export LLM_PROFILE=ollama
lee chat
```

### 生产环境

```bash
# 使用 DeepSeek（性价比高）
export LLM_PROFILE=deepseek
lee chat
```

### 高级用户

```bash
# 使用 Anthropic Claude（质量最高）
export LLM_PROFILE=anthropic
export ANTHROPIC_API_KEY=sk-ant-your-key
lee chat
```

---

## 🔍 故障排查

### 问题 1: "LLM config 'default' missing api_key"

**原因**：未配置 API key

**解决**：
```bash
# 方法 1: 使用环境变量
export LLM_API_KEY=your-api-key

# 方法 2: 使用已配置的 profile
export LLM_PROFILE=zhipu
export LLM_PROFILE=deepseek
```

### 问题 2: "Connection refused"

**原因**：API 服务不可达或 base_url 配置错误

**解决**：
```bash
# 检查网络连接
curl https://api.deepseek.com

# 修改 base_url
export LLM_BASE_URL=https://api.deepseek.com
```

### 问题 3: "Authentication failed"

**原因**：API key 错误或过期

**解决**：
```bash
# 更新 API key
export LLM_API_KEY=your-new-api-key
```

---

## 📊 Provider 对比

| Provider | 优势 | 劣势 | 推荐场景 |
|----------|------|------|----------|
| **Ollama** | 免费、快速、本地 | 需要本地资源 | 开发测试 |
| **DeepSeek** | 性价比高、质量好 | 需要联网 | 生产环境 |
| **智谱 GLM** | 中文友好 | 速度一般 | 中文场景 |
| **OpenAI GPT** | 质量最高 | 价格高 | 高预算项目 |
| **Claude** | 理解能力强 | 价格较高 | 复杂任务 |

---

## 💡 最佳实践

1. **使用环境变量**：不要在配置文件中硬编码 API keys
2. **使用 .env 文件**：方便管理不同环境的配置
3. **选择合适的 Provider**：
   - 开发：Ollama
   - 测试：DeepSeek
   - 生产：DeepSeek 或 Claude
4. **监控用量**：定期检查 API 使用量，避免超支
5. **设置超时**：合理的超时时间（60-120秒）

---

## 📞 获取帮助

- 查看 `config/llm_config.yaml` 了解所有可用配置
- 运行 `python examples/pm_agent_demo.py` 验证功能
- 查看文档：`docs/features/pm-agent/`

---

**配置文件**: `config/llm_config.yaml`
**环境文件**: `.env` (项目根目录)
**文档**: `docs/features/pm-agent/LLM-SETUP-GUIDE.md`
