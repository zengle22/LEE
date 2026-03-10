---
title: 依赖管理说明
author: LEE Team
date: 2026-01-29
version: 1.0
last_updated: 2026-02-19
---

# 依赖管理说明

## 概述

LEE 框架采用模块化依赖管理，核心功能不依赖任何 AI 框架，通过可选依赖的方式支持不同的执行引擎。

## 依赖结构

```
lee-framework (核心)
├── 基础依赖：PyYAML, JSONSchema
└── 可选依赖：
    ├── [legacy_executor] - Legacy Executor 引擎
    ├── [dev] - 开发工具
    └── [all] - 所有依赖
```

## Legacy Executor 引擎

### 版本策略

我们使用**固定主版本**的策略来管理 Legacy Executor 依赖：

```toml
[project.optional-dependencies]
legacy_executor = [
    "legacy_executor>=0.8.0,<0.9.0",  # 固定 0.8.x 版本
]
```

**原因**：
- ✅ 确保兼容性：避免破坏性更新导致适配层失效
- ✅ 安全可控：可以主动测试后再升级
- ✅ 回滚容易：如果新版本有问题，可以快速回退

### 当前版本

| 依赖 | 版本范围 | 说明 |
|------|---------|------|
| Legacy Executor | `>=0.8.0,<0.9.0` | 当前使用 0.8.x 版本 |

### 适配层位置

Legacy Executor 适配层代码位于：

```
flowcore/engines/legacy_executor/
├── __init__.py
├── protocol.py       # LEE 协议类型定义
├── adapter.py        # 核心适配器
└── scenarios.py      # 场景实现
```

**注意**：我们不包含 Legacy Executor 的源代码，而是通过 pip 安装官方包。

## 安装方式

### 用户安装

```bash
# 仅安装核心功能（不包含 Legacy Executor）
pip install lee-framework

# 安装核心 + Legacy Executor 引擎
pip install lee-framework[legacy_executor]
```

### 开发者安装

```bash
# 从源码安装（开发模式）
cd LEE
pip install -e .

# 安装开发依赖（包含 Legacy Executor + 测试工具）
pip install -e ".[dev]"
```

### 产品项目安装

在产品项目中（如 running-coach）：

```bash
cd running-coach
pip install -e ../LEE[legacy_executor]
```

## 版本升级

### 升级 Legacy Executor 版本

当需要升级 Legacy Executor 时（例如从 0.8.x 升级到 0.9.x）：

1. **在新分支中测试**

```bash
git checkout -b upgrade-legacy_executor-0.9
```

2. **更新 pyproject.toml**

```toml
legacy_executor = [
    "legacy_executor>=0.9.0,<1.0.0",  # 升级到 0.9.x
]
```

3. **安装并测试**

```bash
pip install -e ".[legacy_executor]"
pytest tests/test_engines_legacy_executor.py -v
```

4. **更新适配层**（如果需要）

如果 Legacy Executor 的 API 发生变化，相应更新：

```
flowcore/engines/metgpt/protocol.py
flowcore/engines/metgpt/adapter.py
```

5. **提交并发布**

```bash
git commit -am "升级: Legacy Executor 0.8.x -> 0.9.x"
git tag v0.2.0
```

### 升级检查清单

升级 Legacy Executor 版本前，请确认：

- [ ] 阅读上游 [Legacy Executor Release Notes](https://github.com/geekan/Legacy Executor/releases)
- [ ] 检查是否有 Breaking Changes
- [ ] 在测试环境中验证所有功能
- [ ] 更新本文件的版本说明
- [ ] 更新 CHANGELOG.md

## 安全更新

### 自动检查依赖漏洞

建议使用以下工具定期检查依赖安全：

```bash
# 使用 pip-audit 检查已知漏洞
pip install pip-audit
pip-audit

# 使用 safety 检查
pip install safety
safety check
```

### 发现漏洞时

如果 Legacy Executor 发现安全漏洞：

1. **检查上游是否已修复**
2. **临时方案**：在 `pyproject.toml` 中固定到安全版本
3. **官方修复后**：按照"版本升级"流程升级

## 依赖锁定（可选）

对于生产环境，建议使用依赖锁定文件：

### 生成 requirements.txt

```bash
pip freeze > requirements-lock.txt
```

### 使用 pip-tools

```bash
pip install pip-tools
pip-compile pyproject.toml -o requirements-lock.txt
pip-sync
```

## 常见问题

### Q: 为什么不把 Legacy Executor 源码放到仓库中？

A: 原因如下：
- ❌ 会大幅增加仓库体积（Legacy Executor 约 100MB+）
- ❌ 难以追踪上游更新
- ❌ 不符合 Python 生态最佳实践
- ✅ 通过 pip 安装更标准化
- ✅ 可以利用 PyPI 的缓存和镜像
- ✅ 减小仓库体积，加快克隆速度

### Q: 离线环境如何安装？

A: 使用 wheel 包：

```bash
# 在有网络的机器上下载
pip download -d ./packages lee-framework[legacy_executor]

# 在离线机器上安装
pip install --no-index --find-links=./packages lee-framework[legacy_executor]
```

### Q: 如何指定 Legacy Executor 的特定版本？

A: 在 `pyproject.toml` 中修改：

```toml
legacy_executor = [
    "legacy_executor==0.8.1",  # 精确版本
]
```

或创建 `requirements.txt`：

```txt
lee-framework[legacy_executor]
legacy_executor==0.8.1
```

## 相关文档

- [PyPI 依赖规范](https://peps.python.org/pep-0621/)
- [Legacy Executor 官方文档](https://github.com/geekan/Legacy Executor)
- [Pip 安装指南](https://pip.pypa.io/en/stable/user_guide/)

---

**维护者**：LEE 框架团队
**最后更新**：2026-01-22
