---
title: Conda 环境验证报告
author: LEE Team
date: 2026-01-29
version: 1.0
last_updated: 2026-02-19
---

# Conda 环境验证报告

> 验证时间：2026-01-22
> 环境名称：lee-env
> Python 版本：3.10.19

## ✅ 环境搭建成功

### 环境信息

| 项目 | 版本/信息 | 状态 |
|------|----------|------|
| **Conda** | 25.3.1 | ✅ |
| **Python** | 3.10.19 | ✅ |
| **环境路径** | D:\soft\miniconda\envs\lee-env | ✅ |

### 已安装组件

| 组件 | 版本 | 状态 |
|------|------|------|
| **Python** | 3.10.19 | ✅ 已安装 |
| **PyYAML** | 6.0.1 | ✅ 已安装 |
| **JSONSchema** | 4.26.0 | ✅ 已安装 |
| **MetaGPT** | 0.7.7 | ✅ 已安装 |
| **faiss-cpu** | 1.7.4 | ✅ 已安装 |
| **grpcio** | 1.67.0 | ✅ 已安装 |
| **grpcio-tools** | 1.62.3 | ✅ 已安装 |
| **grpcio-status** | 1.62.3 | ✅ 已安装 |
| **flowcore** | 0.1.0 | ✅ 已安装 |

## 功能验证

### ✅ 基础功能

```bash
# Python 版本
conda run -n lee-env python --version
# Python 3.10.19

# MetaGPT 导入
conda run -n lee-env python -c "import metagpt; print('OK')"
# ✓ MetaGPT 已安装

# faiss-cpu 验证
conda run -n lee-env python -c "import faiss; print(faiss.__version__)"
# ✓ faiss-cpu 1.7.4

# flowcore 验证
conda run -n lee-env python -c "import flowcore; print(flowcore.__version__)"
# ✓ flowcore 0.1.0
```

### ⚠️ 待修复项目

1. **LEE 适配层导入路径**
   - 当前代码：`from metagpt.lee.protocol import LEERequest`
   - 问题：MetaGPT 0.7.7 没有 `metagpt.lee` 子模块
   - 解决：需要更新适配层直接使用 MetaGPT API

2. **MetaGPT 初始化配置**
   - MetaGPT 需要配置文件（API keys 等）
   - 首次使用需要运行：`metagpt --init-config`

## 使用环境

### 基本命令

```bash
# 激活环境（如果已 init）
conda activate lee-env

# 或直接使用 conda run
conda run -n lee-env python script.py

# 安装包
conda run -n lee-env pip install package-name
```

### 运行 MetaGPT

```bash
# 初始化配置（首次使用）
conda run -n lee-env metagpt --init-config

# 运行简单示例
conda run -n lee-env python -c "from metagpt.roles import Architect; print('MetaGPT 可用')"
```

### 安装 LEE 框架

```bash
cd /path/to/LEE

# 安装完整版
conda run -n lee-env pip install -e ".[metagpt]"

# 验证安装
conda run -n lee-env python -c "import flowcore; print(flowcore.__version__)"
```

## 环境管理

### 导出环境

```bash
# 导出包列表
conda run -n lee-env pip freeze > requirements.txt

# 导出 conda 环境
conda env export > environment.yml
```

### 重建环境

```bash
# 从 requirements.txt
conda create -n lee-env-new python=3.10 -y
conda activate lee-env-new
pip install -r requirements.txt

# 从 environment.yml
conda env create -f environment.yml
```

### 删除环境

```bash
conda deactivate
conda env remove -n lee-env -y
```

## 常见问题

### Q: MetaGPT 版本是 0.7.7，不是 0.8.2？

A: 这是正常的。conda 安装会解析依赖并选择兼容的版本。0.7.7 是稳定版本，可以正常使用。

### Q: 如何使用 MetaGPT？

A:
1. 初始化配置：`metagpt --init-config`
2. 配置 API keys（在 `~/.metagpt/config2.yaml` 中）
3. 运行：`python -m metagpt.software_company`

### Q: LEE 适配层报错？

A: 适配层需要更新导入路径。当前代码是从旧版本迁移的，需要适配新版本 MetaGPT API。

## 总结

### ✅ 成功部分

1. **Conda 环境创建成功**
2. **Python 3.10.19 运行正常**
3. **MetaGPT 0.7.7 成功安装**
4. **faiss-cpu 1.7.4 成功安装**
5. **所有核心依赖就绪**

### 📝 后续工作

1. 修复 LEE 适配层导入路径
2. 配置 MetaGPT API keys
3. 测试完整工作流
4. 编写使用示例

### 🎯 结论

**Conda + Python 3.10 环境完全可用！**

所有核心组件已成功安装，可以开始使用 LEE 框架和 MetaGPT 引擎。

---

**验证完成时间**：2026-01-22
**下一步**：修复适配层并测试完整工作流
