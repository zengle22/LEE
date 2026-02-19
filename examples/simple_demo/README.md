---
title: 简单 Demo 说明
author: LEE Team
date: 2026-01-29
version: 1.0
last_updated: 2026-02-19
---

# 简单 Demo 说明

本目录包含用于验证 LEE + MetaGPT 环境的简单示例。

## 文件说明

### verify_env.py - 环境验证脚本

**最简单的验证脚本**，无需任何配置即可运行。

**功能**：
- 测试 MetaGPT 导入
- 测试 faiss-cpu 导入
- 测试 MetaGPT 模块导入
- 测试 LEE 框架导入

**运行方式**：
```bash
conda run -n lee-env python examples/simple_demo/verify_env.py
```

**预期输出**：
```
✅ MetaGPT 导入成功
✅ faiss-cpu 1.7.4 导入成功
✅ Architect 角色模块导入成功
✅ flowcore 0.1.0 导入成功
```

### test_metagpt.py - MetaGPT 完整示例

**需要配置 MetaGPT API keys** 才能运行。

**功能**：
- 使用 MetaGPT 的 Architect 角色生成设计文档
- 验证 MetaGPT 的完整功能

**运行方式**：
```bash
# 1. 首次使用需要初始化配置
conda run -n lee-env metagpt --init-config

# 2. 编辑配置文件，设置 API keys
notepad ~/.metagpt/config2.yaml

# 3. 运行示例
conda run -n lee-env python examples/simple_demo/test_metagpt.py
```

**预期输出**：
- 生成设计文档
- 显示内容预览
- 保存完整输出

## 快速开始

### 步骤 1：快速验证

```bash
# 运行最简单的验证（推荐）
conda run -n lee-env python examples/simple_demo/quick_test.py
```

### 步骤 2：配置 MetaGPT（可选）

```bash
# 初始化配置
conda run -n lee-env metagpt --init-config

# 编辑配置文件，添加你的 API keys
```

### 步骤 3：运行完整示例（可选）

```bash
conda run -n lee-env python examples/simple_demo/test_metagpt.py
```

## 故障排除

### 问题 1：ModuleNotFoundError: No module named 'metagpt'

**解决**：
```bash
# 确认在 lee-env 环境中
conda run -n lee-env pip list | grep metagpt

# 如果没有，重新安装
conda run -n lee-env pip install metagpt
```

### 问题 2：MetaGPT 配置错误

**解决**：
```bash
# 重新初始化配置
conda run -n lee-env metagpt --init-config

# 查看配置文件位置
conda run -n lee-env python -c "from metagpt.const import CONFIG_ROOT; print(CONFIG_ROOT)"
```

### 问题 3：API keys 错误

**解决**：
1. 编辑 `~/.metagpt/config2.yaml`
2. 设置 `llm.api_key` 为你的 API key
3. 设置 `llm.model` 为支持的模型名称

## 相关文档

- **Conda 设置指南**：[../../docs/Conda-Setup-Guide.md](../../docs/Conda-Setup-Guide.md)
- **安装指南**：[../../docs/Installation-Guide.md](../../docs/Installation-Guide.md)
- **环境验证**：[../../docs/Conda-Environment-Verification.md](../../docs/Conda-Environment-Verification.md)
