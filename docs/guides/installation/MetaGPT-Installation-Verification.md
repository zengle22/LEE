---
title: Legacy Executor 安装验证指南
author: LEE Team
date: 2026-01-29
version: 1.0
last_updated: 2026-02-19
---

# Legacy Executor 安装验证指南

## 快速验证

### 1. 验证 PyPI 包是否存在

```bash
pip search legacy_executor
# 或
pip index versions legacy_executor
```

### 2. 安装并验证

```bash
# 创建测试环境
python -m venv venv-test
source venv-test/bin/activate  # Linux/Mac
# 或
venv-test\Scripts\activate  # Windows

# 安装 Legacy Executor
pip install legacy_executor==0.8.2

# 验证安装
python -c "import legacy_executor; print(legacy_executor.__version__)"
```

### 3. 测试 LEE 适配层

```bash
# 在 LEE 项目根目录
pip install -e ".[legacy_executor]"

# 测试导入
python -c "from flowcore.engines.legacy_executor.protocol import LEERequest; print('✓ 适配层导入成功')"
```

---

## 完整测试流程

### 步骤 1: 清理环境（可选）

```bash
# 如果之前安装过旧版本
pip uninstall legacy_executor -y
```

### 步骤 2: 安装 LEE 框架

```bash
cd /path/to/LEE
pip install -e ".[legacy_executor]"
```

### 步骤 3: 验证依赖

```bash
# 检查已安装的包
pip list | grep legacy_executor

# 应该看到类似输出：
# legacy_executor               0.8.2
```

### 步骤 4: 测试 Legacy Executor 初始化

```bash
# 初始化 Legacy Executor 配置
legacy_executor --init-config

# 这会在 ~/.legacy_executor/config2.yaml 创建配置文件
```

### 步骤 5: 运行测试（如果有）

```bash
# 测试 Legacy Executor 引擎
pytest tests/test_engines_legacy_executor.py -v

# 或运行示例
python examples/minimal_workflow/run.py
```

---

## 版本兼容性

### 已测试版本

| LEE 框架版本 | Legacy Executor 版本 | 状态 |
|-------------|-------------|------|
| v0.1.0 | 0.8.2 | ✅ 推荐使用 |
| v0.1.0 | 0.8.0 - 0.8.1 | ✅ 兼容 |
| v0.1.0 | 0.7.x | ⚠️ 未测试 |
| v0.1.0 | 0.9.x | ❌ 待发布 |

### 升级建议

- **稳定生产环境**：使用 `legacy_executor==0.8.2`（固定版本）
- **开发环境**：使用 `legacy_executor>=0.8.0,<0.9.0`（允许小版本更新）
- **尝鲜功能**：使用 GitHub 开发版（风险自负）

---

## 常见问题

### Q1: pip install legacy_executor 失败？

**A**: 检查 Python 版本：
```bash
python --version  # 需要 >= 3.9
```

### Q2: 安装后导入失败？

**A**: 检查安装路径：
```bash
pip show legacy_executor
```

### Q3: PyPI 版本不是最新的？

**A**: PyPI 可能滞后于 GitHub，可以安装开发版：
```bash
pip install git+https://github.com/geekan/Legacy Executor
```

### Q4: 如何查看可用版本？

**A**:
```bash
pip index versions legacy_executor
# 或访问
# https://pypi.org/project/legacy_executor/#history
```

---

## 参考资源

- **PyPI 页面**：https://pypi.org/project/legacy_executor/
- **GitHub 仓库**：https://github.com/geekan/Legacy Executor
- **官方文档**：https://github.com/geekan/Legacy Executor/blob/main/docs/README_CN.md

---

**最后更新**：2026-01-22
**验证版本**：Legacy Executor 0.8.2
