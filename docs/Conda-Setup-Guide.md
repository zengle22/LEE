# Conda 环境搭建快速指南

## 概述

本指南说明如何使用 Conda + Python 3.10 搭建 LEE 框架的开发环境，解决 MetaGPT 的依赖问题。

## 前提条件

- 已安装 Conda 或 Miniconda
- Windows/Linux/macOS 系统

## 快速开始

### 1. 创建 Conda 环境

```bash
# 创建 Python 3.10 环境
conda create -n lee-env python=3.10 -y

# 验证环境
conda env list | grep lee-env
```

### 2. 激活环境（可选）

```bash
# Windows
conda activate lee-env

# Linux/macOS
conda activate lee-env
```

**或使用 `conda run`**（无需激活）：
```bash
conda run -n lee-env python --version
```

### 3. 安装 MetaGPT

```bash
# 安装最新稳定版
conda run -n lee-env pip install metagpt

# 或安装特定版本
conda run -n lee-env pip install metagpt==0.8.2
```

**预计时间**：3-5 分钟（取决于网络速度）

### 4. 验证安装

```bash
# 方式 1：检查 MetaGPT 版本
conda run -n lee-env python -c "import metagpt; print(metagpt.__version__)"

# 方式 2：运行验证脚本
conda run -n lee-env python tools/verify_env.py
```

### 5. 安装 LEE 框架

```bash
cd /path/to/LEE

# 安装完整版（包含 MetaGPT）
conda run -n lee-env pip install -e ".[metagpt]"

# 或仅安装核心功能
conda run -n lee-env pip install -e .
```

## 使用环境

### 方式 1：使用 conda run（推荐）

```bash
# 运行 Python 脚本
conda run -n lee-env python script.py

# 安装包
conda run -n lee-env pip install package-name

# 启动服务
conda run -n lee-env python -m flowcore.cli.main status
```

### 方式 2：激活环境

**首次使用需要初始化**：
```bash
# 初始化 conda（仅第一次）
conda init bash
source ~/.bashrc  # Linux/macOS
# 或重启终端
```

**激活环境**：
```bash
conda activate lee-env

# 使用环境
python script.py
pip install package-name
```

**退出环境**：
```bash
conda deactivate
```

## 环境管理

### 查看环境列表

```bash
conda env list
```

### 删除环境

```bash
conda deactivate  # 先退出环境
conda env remove -n lee-env -y
```

### 导出环境配置

```bash
# 导出当前环境的包列表
conda run -n lee-env pip freeze > requirements.txt

# 或导出完整的 conda 环境
conda env export > environment.yml
```

### 从配置重建环境

```bash
# 从 requirements.txt
conda create -n lee-env-new python=3.10 -y
conda activate lee-env-new
pip install -r requirements.txt

# 从 environment.yml
conda env create -f environment.yml
```

## 常见问题

### Q1: conda: command not found

**A**: 确保 Conda 已安装并添加到 PATH：
```bash
# Windows
# 检查: D:\soft\miniconda\Scripts 是否在 PATH 中

# Linux/macOS
# 重新打开终端，或 source ~/.bashrc
```

### Q2: ModuleNotFoundError: No module named 'metagpt'

**A**: MetaGPT 还在安装中，请等待：
```bash
# 检查安装状态
conda run -n lee-env pip show metagpt

# 如果显示 WARNING: Package(s) not found，说明还在安装
# 请等待 3-5 分钟后重试
```

### Q3: 安装速度慢

**A**: 使用国内镜像源：
```bash
# 配置 pip 镜像
conda run -n lee-env pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# 或配置 conda 镜像
conda config --add channels defaults
conda config --add channels conda-forge
```

### Q4: Windows 上如何激活环境

**A**: 使用 PowerShell 或 CMD：
```powershell
# PowerShell
conda activate lee-env

# CMD
conda activate lee-env
```

**注意**：首次使用需要运行 `conda init`：
```bash
# PowerShell
conda init powershell

# CMD
conda init cmd.exe
```

## 实际使用示例

### 示例 1：运行 LEE 工作流

```bash
cd /path/to/LEE/project

# 使用 conda run
conda run -n lee-env python -m flowcore.cli.main run workflows/my_workflow.yaml

# 或激活后运行
conda activate lee-env
python -m flowcore.cli.main run workflows/my_workflow.yaml
```

### 示例 2：开发模式安装

```bash
cd /path/to/LEE

# 创建环境
conda create -n lee-dev python=3.10 -y
conda activate lee-dev

# 安装开发依赖
pip install -e ".[dev]"
```

### 示例 3：在 IDE 中使用

**VS Code**：
1. 安装 Python 扩展
2. 选择解释器：`Conda env: lee-env`
3. 开始开发

**PyCharm**：
1. Settings → Project → Python Interpreter
2. Add Conda Environment
3. 选择 `lee-env`

## 验证清单

安装完成后，验证以下项目：

- [ ] `conda run -n lee-env python --version` 显示 3.10.x
- [ ] `conda run -n lee-env pip show metagpt` 显示版本信息
- [ ] `conda run -n lee-env python -c "import faiss; print(faiss.__version__)"` 显示 faiss 版本
- [ ] `conda run -n lee-env python tools/verify_env.py` 全部通过

## 相关文档

- **安装指南**：[Installation-Guide.md](Installation-Guide.md)
- **依赖管理**：[Dependency-Management.md](Dependency-Management.md)
- **验证脚本**：[tools/verify_env.py](../tools/verify_env.py)

---

**最后更新**：2026-01-22
**Conda 版本**：25.3.1
**Python 版本**：3.10.19
