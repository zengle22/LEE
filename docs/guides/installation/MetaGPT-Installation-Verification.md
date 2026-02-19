# MetaGPT 安装验证指南

## 快速验证

### 1. 验证 PyPI 包是否存在

```bash
pip search metagpt
# 或
pip index versions metagpt
```

### 2. 安装并验证

```bash
# 创建测试环境
python -m venv venv-test
source venv-test/bin/activate  # Linux/Mac
# 或
venv-test\Scripts\activate  # Windows

# 安装 MetaGPT
pip install metagpt==0.8.2

# 验证安装
python -c "import metagpt; print(metagpt.__version__)"
```

### 3. 测试 LEE 适配层

```bash
# 在 LEE 项目根目录
pip install -e ".[metagpt]"

# 测试导入
python -c "from flowcore.engines.metagpt.protocol import LEERequest; print('✓ 适配层导入成功')"
```

---

## 完整测试流程

### 步骤 1: 清理环境（可选）

```bash
# 如果之前安装过旧版本
pip uninstall metagpt -y
```

### 步骤 2: 安装 LEE 框架

```bash
cd /path/to/LEE
pip install -e ".[metagpt]"
```

### 步骤 3: 验证依赖

```bash
# 检查已安装的包
pip list | grep metagpt

# 应该看到类似输出：
# metagpt               0.8.2
```

### 步骤 4: 测试 MetaGPT 初始化

```bash
# 初始化 MetaGPT 配置
metagpt --init-config

# 这会在 ~/.metagpt/config2.yaml 创建配置文件
```

### 步骤 5: 运行测试（如果有）

```bash
# 测试 MetaGPT 引擎
pytest tests/test_engines_metagpt.py -v

# 或运行示例
python examples/minimal_workflow/run.py
```

---

## 版本兼容性

### 已测试版本

| LEE 框架版本 | MetaGPT 版本 | 状态 |
|-------------|-------------|------|
| v0.1.0 | 0.8.2 | ✅ 推荐使用 |
| v0.1.0 | 0.8.0 - 0.8.1 | ✅ 兼容 |
| v0.1.0 | 0.7.x | ⚠️ 未测试 |
| v0.1.0 | 0.9.x | ❌ 待发布 |

### 升级建议

- **稳定生产环境**：使用 `metagpt==0.8.2`（固定版本）
- **开发环境**：使用 `metagpt>=0.8.0,<0.9.0`（允许小版本更新）
- **尝鲜功能**：使用 GitHub 开发版（风险自负）

---

## 常见问题

### Q1: pip install metagpt 失败？

**A**: 检查 Python 版本：
```bash
python --version  # 需要 >= 3.9
```

### Q2: 安装后导入失败？

**A**: 检查安装路径：
```bash
pip show metagpt
```

### Q3: PyPI 版本不是最新的？

**A**: PyPI 可能滞后于 GitHub，可以安装开发版：
```bash
pip install git+https://github.com/geekan/MetaGPT
```

### Q4: 如何查看可用版本？

**A**:
```bash
pip index versions metagpt
# 或访问
# https://pypi.org/project/metagpt/#history
```

---

## 参考资源

- **PyPI 页面**：https://pypi.org/project/metagpt/
- **GitHub 仓库**：https://github.com/geekan/MetaGPT
- **官方文档**：https://github.com/geekan/MetaGPT/blob/main/docs/README_CN.md

---

**最后更新**：2026-01-22
**验证版本**：MetaGPT 0.8.2
