---
title: LEE 框架打包部署指南
version: 0.2.0
date: 2026-03-05
---

# LEE 框架打包部署指南

> 本指南介绍如何将 LEE 框架打包为 Python 包，并在目标项目（workspace）中正确使用。

## 背景

版本号规则见 [LEE 版本号规则](/E:/ai/LEE/docs/guides/technical/LEE-VERSIONING.md)。

### 问题陈述

LEE 是一个 AI 驱动的研发框架，用于生成和驱动其他目标项目的开发。传统方式将 LEE 代码与目标项目混在一起，导致：

1. **`lee/` 目录常被误当成"项目根目录"**（如 `.gitignore` 歧义）
2. **升级/回滚不清晰**（版本号无法体现）
3. **CI/本地一致性差**

### 解决方案

将 LEE 打包成 Python 包发布到 PyPI，目标工程只保留：

- `lee` 命令（入口）
- `.lee/` 锚点文件 + 运行态目录

---

## 架构概览

### 目录结构对比

**传统方式（混在一起）**：
```
project/
├── lee/           # LEE 框架代码
├── LEE/           # spec-global 子模块
├── .lee/          # 项目配置
├── .workflow/     # 运行态
└── src/           # 目标项目源码
```

**打包后（分离部署）**：
```
project/
├── .lee/          # 项目配置 + 锚点
│   ├── config.yaml    # 运行配置
│   └── lee.lock       # 锁定信息
├── .workflow/     # 运行态
└── src/           # 目标项目源码

# LEE 包（pip 安装）
lee-framework/
├── lee/
│   ├── cli/
│   ├── orchestrator/
│   └── data/
│       └── spec-global/   # 所有规范模板（内置）
└── config/
    └── llm_config.yaml
```

---

## 快速开始

### 1. 安装 LEE 框架

```bash
# 从 PyPI 安装（推荐）
pip install lee-framework

# 或从源码安装
pip install -e .
```

### 2. 初始化目标项目

```bash
# 创建项目目录
mkdir my-project
cd my-project

# 初始化 LEE
lee init
```

这将创建以下文件：

```
.lee/
├── config.yaml    # 运行配置
└── lee.lock       # 版本锁定
```

### 3. 使用 LEE 命令

```bash
# 查看帮助
lee --help

# 诊断配置
lee doctor

# 运行工作流
lee run <dept>.<workflow>
```

---

## 配置文件详解

### .lee/config.yaml

```yaml
# .lee/config.yaml
spec_root: builtin  # builtin / ./my-spec / /absolute/path
executor:
  default_type: claude_code
```

| 配置项 | 说明 | 可选值 |
|--------|------|--------|
| `spec_root` | 规范模板根目录 | `builtin`（默认包内）、`./my-spec`（项目内）、`/absolute/path`（绝对路径） |
| `executor.default_type` | 默认执行器 | `claude_code`、`llm`、`legacy_executor` 等 |

### .lee/lee.lock

```json
{
  "schema_version": 1,
  "lee_version": "0.2.0",
  "lee_install": "pypi",
  "mode": "prod",
  "initialized_at": "2026-03-05T10:00:00Z"
}
```

| 字段 | 说明 |
|------|------|
| `lee_version` | LEE 框架版本 |
| `lee_install` | 安装方式：`pypi`、`editable`、`wheel` |
| `mode` | 运行模式：`prod`（生产）、`dev`（开发） |
| `lee_src` | 开发模式下的源码路径 |

---

## 高级配置

### Spec 覆盖优先级

LEE 支持多层级的 Spec 配置，优先级从高到低：

1. **CLI 参数**：`lee --spec-root=./my-spec run ...`
2. **环境变量**：`LEE_SPEC_ROOT=./my-spec lee run ...`
3. **配置文件**：`.lee/config.yaml` 中的 `spec_root`
4. **版本锁定**：`.lee/lee.lock` 中的 `mode` 和 `lee_src`
5. **内置默认**：包内的 `spec-global`

### 开发模式（LEE 研发 LEE）

如果你正在开发 LEE 框架本身，可以使用开发模式：

```bash
# 方式1：通过 lee.lock 配置
echo '{"mode": "dev", "lee_src": "/path/to/LEE"}' > .lee/lee.lock

# 方式2：通过环境变量
LEE_DEV_MODE=1 LEE_SRC=/path/to/LEE lee run ...
```

开发模式下：
- 相对路径以 `lee_src` 为基准
- 未指定 `spec_root` 时默认使用 `<lee_src>/spec-global`

---

## CLI 命令

### lee init

初始化项目目录结构：

```bash
lee init [OPTIONS]

Options:
  --project-dir PATH  项目目录
  --no-discover      禁用自动发现仓库
  --depth N          仓库发现深度
  --force            强制重新初始化
```

### lee doctor

诊断 LEE 配置和环境：

```bash
lee doctor [OPTIONS]

Options:
  --project-dir PATH   项目目录
  --self-check         执行安装后自检
  --spec-root PATH     指定 spec-root
```

**输出示例**：

```
✓ Workspace: /path/to/project
✓ .lee directory exists
✓ Config loaded
  spec_root: builtin (default)
  demo_mode: False
✓ Lock file loaded
  lee_version: 0.2.0
  mode: prod
  lee_install: pypi
✓ Spec Resolve:
  source: builtin
  kind: builtin
  value: builtin
```

### lee run

运行工作流：

```bash
lee run <dept>.<workflow> [OPTIONS]

Options:
  --project-dir PATH   项目目录
  --spec-root PATH     覆盖 spec-root
```

---

## CI 集成

### 基础 CI 配置

```yaml
# .github/workflows/lee.yml
name: LEE Workflow

on: [push, pull_request]

jobs:
  run:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install LEE
        run: pip install lee-framework

      - name: Initialize
        run: lee init

      - name: Run Workflow
        run: lee run dev.example-workflow
```

### 锁定版本

使用 `requirements-lee.txt` 锁定 LEE 版本：

```
# requirements-lee.txt
lee-framework==0.2.0
```

```yaml
# .github/workflows/lee.yml
- name: Install locked version
  run: pip install -r requirements-lee.txt
```

---

## 故障排查

### 常见问题

**Q: `lee` 命令找不到**

```bash
# 检查安装
pip show lee-framework

# 重新安装
pip install --force-reinstall lee-framework
```

**Q: `.lee` 目录未找到**

```bash
# 初始化项目
lee init

# 或指定项目目录
lee --project-dir /path/to/project doctor
```

**Q: Spec 文件未找到**

```bash
# 诊断配置
lee doctor

# 检查 spec_root 配置
cat .lee/config.yaml

# 使用 CLI 覆盖
lee --spec-root=./my-spec run <workflow>
```

### 自检

```bash
lee doctor --self-check
```

检查项：
- ✓ Workspace 发现
- ✓ Config 加载
- ✓ Lock 文件
- ✓ Spec 解析
- ✓ 内置 Spec 可访问性
- ✓ 抽样检查 workflows/skills/agents

---

## 技术细节

### 包内资源访问

LEE 使用 `importlib.resources` 访问包内资源：

```python
from lee.data_path import (
    get_builtin_spec_traversable,
    with_builtin_spec_root,
    resolve_spec,
    SpecResolveInput,
)

# 获取 Traversable（不落盘，适合读 YAML）
t = get_builtin_spec_traversable()

# 获取真实 Path（用于 glob 等操作）
with_builtin_spec_root(lambda p: print(p))

# 解析 Spec 路径
result = resolve_spec(SpecResolveInput(
    workspace_root=Path.cwd(),
    config_spec_root="builtin",
))
result.with_path(lambda p: ...)
```

### 路径解析算法

```
1. 确定 path_base：
   - mode=dev 且 lee_src 存在 → lee_src
   - 否则 → workspace_root

2. 按优先级解析：
   - CLI --spec-root → 相对于 path_base
   - ENV LEE_SPEC_ROOT → 相对于 path_base
   - config.spec_root → 相对于 path_base

3. builtin 语义：
   - 空字符串 / "builtin" / "@builtin" → 使用包内默认
```

---

## 更新日志

| 版本 | 日期 | 说明 |
|------|------|------|
| 0.2.0 | 2026-03-05 | 初始版本：打包部署支持 |

---

## 相关文档

- [LEE 框架总览](../README.md)
- [LEE CLI 命令参考](./CLI-Commands.md)
- [工作流编写指南](./Workflow-Spec-Guide.md)
- [Orchestrator 指南](./Orchestrator-Guide.md)
