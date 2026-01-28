# LEE 框架

> **通用 AI 工作流编排系统**

LEE 框架是一个通用的 AI 工作流编排系统，用于管理和执行复杂的 AI Agent 工作流。它提供了标准化的接口、规范和工具，帮助开发者构建可维护、可扩展的 AI 应用。

## 项目定位

```
┌─────────────────────────────────────────────────────────────────┐
│                        架构关系                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   LEE/ (本项目 - 框架仓库)                                       │
│   ├── flowcore/        # 框架核心代码                           │
│   ├── spec-global/      # 全局规范模板（按部门组织）             │
│   ├── config/           # 配置模板                              │
│   ├── docs/             # 框架文档                              │
│   └── changelogs/       # 变更日志                              │
│          ↑                                                     │
│          │ git submodule / pip 依赖                             │
│          │                                                     │
│   running-coach/ (产品项目)                                      │
│   ├── LEE/             # → 引用本框架                          │
│   ├── project/         # 产品专属内容                          │
│   └── runtime/         # 运行时                                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 核心特性

- **工作流编排**：DAG 调度、状态管理、事件溯源
- **多引擎支持**：MetaGPT、单 Agent、Python/CLI
- **人工门禁**：工作流中的审批节点
- **规范管理**：全局规范模板 + 产品专属规范
- **部门化组织**：按 PM/Dev/QA/DevOps 部门组织规范
- **Verifier System**：AI 产物质量验证系统
- **可扩展**：标准化的接口，易于扩展新引擎

## 目录结构

```
LEE/
├── flowcore/                    # 核心代码包
│   ├── orchestrator/             # 工作流编排器
│   ├── engines/                  # 执行引擎
│   │   └── metagpt/              # MetaGPT 适配层
│   ├── utils/                    # 工具模块
│   └── cli/                      # 命令行工具
├── spec-global/                  # 全局规范模板（按部门组织）
│   ├── core/                     # 平台级基础规范
│   ├── departments/              # 按部门组织（pm/dev/qa/devops）
│   │   ├── dev/                  # 开发部门
│   │   ├── prd/                  # 产品部门
│   │   ├── qa/                   # 质量保证部门
│   │   ├── ui/                   # UI/UX 设计部门
│   │   ├── stg/                  # 策略部门
│   │   ├── devops/               # DevOps 部门（含 Verifier System）
│   │   └── office/               # 办公室
│   └── cross/                    # 跨部门流程和接口
├── config/                       # 配置模板
├── docs/                         # 框架文档
├── changelogs/                   # 变更日志
├── examples/                     # 使用示例
└── tools/                        # 工具脚本
```

## 快速开始

### 作为 Git Submodule（推荐）

在产品项目中引用 LEE 框架：

```bash
cd running-coach
git submodule add https://github.com/your-org/LEE.git LEE
git submodule update --init --recursive
```

### 创建产品项目

1. **复制 workspace 配置**：

```bash
cd running-coach/project
cp ../LEE/config/workspace.template.yaml workspace.yaml
```

2. **根据实际情况修改 workspace.yaml**：

```yaml
spec:
  global_root: "../LEE/spec-global"  # 指向 LEE 框架
  project_root: "./spec"             # 产品专属规范

repos:
  backend:
    path: "./repos/dev/backend"
    type: "git"

runtime:
  root: "../runtime"
```

3. **运行工作流**：

```bash
cd running-coach/project
python ../LEE/flowcore/cli/main.py run workflows/my_workflow.yaml
```

### 作为 pip 依赖

```bash
pip install lee-framework
```

```python
from flowcore.orchestrator.runner import run_workflow
from flowcore.engines.metagpt.adapter import run_lee_unit
```

## 使用 LEE CLI

```bash
# 查看状态
python -m flowcore.cli.main status

# 运行工作流
python -m flowcore.cli.main run workflows/my_workflow.yaml

# 审批门禁
python -m flowcore.cli.main approve gate_id --approver "张三"

# 查看日志
python -m flowcore.cli.main log
```

## 文档

### 框架级文档

- [框架总览](docs/LEE-Overview.md)
- [接口规范](docs/LEE-Interface-Spec.md)
- [Workflow 编写指南](docs/Workflow-Spec-Guide.md)
- [编排器指南](docs/Orchestrator-Guide.md)
- [Workspace 配置](docs/Workspace-Config.md)
- [Spec 组织结构](docs/Spec-Organization.md)
- [工作流汇总](spec-global/WORKFLOWS.md) - 所有工作流概览

### Spec-Global 文档

- [Spec-Global 迁移报告](spec-global/README.md)
- [工作流汇总](spec-global/WORKFLOWS.md)
- [DevOps 部门文档](spec-global/departments/devops/README.md)
- [Verifier System 快速开始](spec-global/departments/devops/docs/verifier-quickstart.md)

### 模块级文档

- [Orchestrator 模块](flowcore/orchestrator/README.md)
- [Engines 系统](flowcore/engines/README.md)
- [MetaGPT 集成](flowcore/engines/metagpt/README.md)

### 变更日志

- [变更日志总览](changelogs/README.md)
- [v0.1.0](changelogs/v0.1.0.md)

## 示例

查看 `examples/` 目录获取更多示例：

- `minimal_workflow/` - 最小工作流示例
- `code_implementation/` - 代码实现示例
- `bug_fix/` - Bug 修复示例

## 核心代码包：flowcore

**flowcore** 是 LEE 框架的核心代码包，包含：

- **orchestrator/**：工作流编排器
- **engines/**：执行引擎（MetaGPT、单 Agent 等）
- **utils/**：工具模块
- **cli/**：命令行工具

### Import 示例

```python
# 核心模块
from flowcore.orchestrator.runner import run_workflow
from flowcore.orchestrator.state_machine import StateMachine

# 引擎
from flowcore.engines.base import LEERequest, LEEResult
from flowcore.engines.metagpt.adapter import run_lee_unit

# 工具
from flowcore.utils.logging import setup_logger
from flowcore.utils.ids import generate_run_id
```

## Spec 全局规范：按部门组织

`spec-global/` 按三层结构组织：

1. **core/**：平台级基础规范（不归任何部门）
2. **departments/**：按部门垂直切分（pm/dev/qa/ops）
3. **cross/**：跨部门流程和接口

详见 [Spec 组织结构说明](docs/Spec-Organization.md)。

## 安装

### 基础安装

```bash
# 克隆仓库
git clone https://github.com/your-org/LEE.git
cd LEE

# 安装基础包
pip install -e .
```

### 安装 MetaGPT 引擎

```bash
# 安装包含 MetaGPT 引擎的完整版本
pip install -e ".[metagpt]"

# 或者安装所有可选依赖
pip install -e ".[all]"
```

### 开发环境安装

```bash
# 安装开发依赖（包含 MetaGPT 和测试工具）
pip install -e ".[dev]"
```

## 开发

### 代码规范

### 运行测试

```bash
pytest tests/
```

### 代码规范

```bash
# 检查
flake8 flowcore/

# 格式化
black flowcore/
```

## 变更日志

查看 [changelogs/](changelogs/) 了解各版本的详细变更。

## 贡献

欢迎贡献！请查看 [CONTRIBUTING.md](CONTRIBUTING.md) 了解详情。

## 许可证

[MIT License](LICENSE)

## 联系方式

- Issues: https://github.com/your-org/LEE/issues
- Discussions: https://github.com/your-org/LEE/discussions
