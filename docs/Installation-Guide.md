# LEE 框架安装指南

## 系统要求

### Python 版本

| 组件 | Python 版本 | 说明 |
|------|------------|------|
| **LEE 核心功能** | Python 3.8+ | 推荐使用 3.10 或 3.11 |
| **MetaGPT 引擎** | Python 3.9-3.10 | ⚠️ **不支持 3.11+**（faiss-cpu 依赖限制） |

### 推荐环境

**开发环境**：
- Python 3.10.13（推荐）
- Conda/Miniconda（推荐用于依赖管理）
- Git

**生产环境**：
- Docker 容器（Python 3.10）
- 虚拟环境（venv/conda）

---

## 安装方式

### 方式 1：仅安装核心功能（推荐用于测试）

```bash
# 克隆仓库
git clone https://github.com/your-org/LEE.git
cd LEE

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows

# 安装核心功能
pip install -e .

# 验证安装
python -c "import flowcore; print(flowcore.__version__)"
```

### 方式 2：使用 Conda 安装（推荐用于 MetaGPT）

#### Windows/Linux/Mac

```bash
# 创建 Conda 环境（Python 3.10）
conda create -n lee-env python=3.10 -y
conda activate lee-env

# 进入 LEE 项目目录
cd /path/to/LEE

# 安装包含 MetaGPT 的完整版本
pip install -e ".[metagpt]"

# 验证安装
python -c "import metagpt; print(metagpt.__version__)"
python -c "from flowcore.engines.metagpt.adapter import run_lee_unit; print('✓ MetaGPT 适配层正常')"
```

### 方式 3：Docker 安装（推荐用于生产）

#### Dockerfile

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# 复制项目文件
COPY . /app/LEE

# 安装 LEE 框架
WORKDIR /app/LEE
RUN pip install -e ".[metagpt]"

# 验证安装
RUN python -c "import flowcore; print(flowcore.__version__)" && \
    python -c "import metagpt; print(metagpt.__version__)"

CMD ["/bin/bash"]
```

#### 构建和运行

```bash
# 构建镜像
docker build -t lee-framework:0.1.0 .

# 运行容器
docker run -it lee-framework:0.1.0 bash

# 在容器中测试
python -c "from flowcore.orchestrator.state_machine import StateMachine; print('✓ 正常')"
```

---

## 依赖问题解决方案

### 问题：faiss-cpu 版本冲突

**症状**：
```
ERROR: No matching distribution found for faiss-cpu==1.7.4
```

**原因**：
- MetaGPT 依赖 `faiss-cpu==1.7.4`
- 该版本不支持 Python 3.11+ 和某些平台

**解决方案**：

#### 选项 1：使用 Python 3.10（推荐）

```bash
# 使用 Conda
conda create -n lee-env python=3.10 -y
conda activate lee-env

# 使用 pyenv（Linux/Mac）
pyenv install 3.10.13
pyenv local 3.10.13
```

#### 选项 2：使用 Docker

```bash
docker pull python:3.10-slim
docker run -it -v $(pwd):/app python:3.10-slim bash
```

#### 选项 3：仅安装核心功能（跳过 MetaGPT）

```bash
# 不包含 [metagpt]
pip install -e .
```

---

## 安装验证

### 核心功能验证

```bash
# 1. 检查版本
python -c "import flowcore; print('LEE 版本:', flowcore.__version__)"

# 2. 测试核心模块
python -c "from flowcore.orchestrator.state_machine import StateMachine; print('✓ orchestrator 正常')"
python -c "from flowcore.utils.template_resolver import TemplateResolver; print('✓ utils 正常')"

# 3. 测试 CLI
python -m flowcore.cli.main --help
```

### MetaGPT 引擎验证（如果已安装）

```bash
# 1. 检查 MetaGPT 版本
python -c "import metagpt; print('MetaGPT 版本:', metagpt.__version__)"

# 2. 测试适配层
python -c "from flowcore.engines.metagpt.protocol import LEERequest; print('✓ 协议层正常')"
python -c "from flowcore.engines.metagpt.adapter import run_lee_unit; print('✓ 适配器正常')"

# 3. 初始化配置
metagpt --init-config
```

---

## 常见问题

### Q1: Windows 上安装失败怎么办？

**A**: 使用 Conda：

```bash
# 安装 Miniconda
# https://docs.conda.io/en/latest/miniconda.html

# 创建环境
conda create -n lee python=3.10 -y
conda activate lee
```

### Q2: 如何同时使用多个 Python 版本？

**A**: 使用 pyenv（Linux/Mac）或 Conda：

```bash
# Conda
conda create -n lee-py310 python=3.10 -y
conda create -n lee-py39 python=3.9 -y

# 切换环境
conda activate lee-py310
```

### Q3: MetaGPT 可以不安装吗？

**A**: 可以！LEE 框架的核心功能不依赖 MetaGPT：

```bash
# 只安装核心
pip install -e .

# 核心功能包括：
# - orchestrator: 工作流编排
# - utils: 工具模块
# - cli: 命令行工具
# - 单 Agent 引擎（计划中）
# - Python/CLI 执行引擎（计划中）
```

### Q4: 如何离线安装？

**A**: 使用 wheel 包：

```bash
# 在有网络的机器上
pip download -d ./packages lee-framework[metagpt]

# 在离线机器上
pip install --no-index --find-links=./packages lee-framework[metagpt]
```

---

## 开发环境搭建

### 完整开发环境（推荐）

```bash
# 1. 创建 Conda 环境
conda create -n lee-dev python=3.10 -y
conda activate lee-dev

# 2. 安装开发依赖
cd LEE
pip install -e ".[dev]"

# 3. 验证安装
pytest tests/ -v

# 4. 初始化 MetaGPT 配置
metagpt --init-config
```

### 最小开发环境

```bash
# 1. 创建虚拟环境
python -m venv venv
source venv/bin/activate

# 2. 安装核心
pip install -e .

# 3. 安装开发工具
pip install pytest black flake8 mypy
```

---

## 卸载

```bash
# 卸载 LEE 框架
pip uninstall lee-framework -y

# 删除虚拟环境
rm -rf venv
# 或
conda deactivate
conda env remove -n lee-env
```

---

## 相关文档

- **依赖管理**：[Dependency-Management.md](Dependency-Management.md)
- **MetaGPT 验证**：[MetaGPT-Installation-Verification.md](MetaGPT-Installation-Verification.md)
- **快速开始**：[GETTING_STARTED.md](../GETTING_STARTED.md)

---

**最后更新**：2026-01-22
**测试状态**：
- ✅ Python 3.10 + Conda：完全支持
- ⚠️ Python 3.11+：核心功能支持，MetaGPT 引擎不支持
- ⚠️ Python 3.13：核心功能支持，MetaGPT 引擎不支持
