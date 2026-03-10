# LEE 框架 - 项目上下文

## 项目概述

**LEE** (通用 AI 工作流编排系统) 是一个用于管理和执行复杂 AI Agent 工作流的 Python 框架。它提供了标准化的接口、规范和工具，帮助开发者构建可维护、可扩展的 AI 应用。

### 核心特性

- **工作流编排**: DAG 调度、状态管理、事件溯源
- **多引擎支持**: 单 Agent、Python/CLI
- **人工门禁**: 工作流中的审批节点
- **规范管理**: 全局规范模板 + 产品专属规范
- **部门化组织**: 按 PM/Dev/QA/DevOps 部门组织规范
- **Verifier System**: AI 产物质量验证系统
- **QA E2E 测试模块**: 从 YAML 测试用例到可执行代码的完整闭环

### 技术栈

- **语言**: Python 3.8+
- **核心依赖**: PyYAML, jsonschema, aiosqlite, jinja2, click
- **测试框架**: pytest
- **代码质量**: black, flake8, mypy

---

## 项目结构

```
LEE/
├── src/                           # 核心代码目录
│   ├── flowcore/                  # 框架核心包
│   │   ├── orchestrator/          # 工作流编排器
│   │   ├── engines/               # 执行引擎
│   │   ├── utils/                 # 工具模块
│   │   └── cli/                   # 命令行工具
│   ├── lee/                       # LEE 应用层
│   │   ├── orchestrator/          # 应用级编排器
│   │   │   └── core/              # Instance 生成器等
│   │   └── qa/                    # QA E2E 测试模块
│   ├── config/                    # 配置加载器
│   ├── components/                # 组件库
│   ├── services/                  # 服务层
│   ├── types/                     # 类型定义
│   └── utils/                     # 通用工具
├── spec-global/                   # 全局规范模板（按部门组织）
│   ├── core/                      # 平台级基础规范
│   ├── departments/               # 按部门组织
│   │   ├── dev/                   # 开发部门
│   │   ├── prd/                   # 产品部门
│   │   ├── qa/                    # 质量保证部门
│   │   ├── ui/                    # UI/UX 设计部门
│   │   ├── stg/                   # 策略部门
│   │   ├── devops/                # DevOps 部门
│   │   └── office/                # 办公室
│   └── cross/                     # 跨部门流程和接口
├── config/                        # 配置模板
│   ├── defaults.yaml
│   ├── llm_config.yaml
│   ├── workflow-registry.yaml
│   └── workspace.template.yaml
├── tests/                         # 测试目录
│   ├── unit/                      # 单元测试
│   ├── integration/               # 集成测试
│   ├── e2e/                       # 端到端测试
│   ├── orchestrator/              # 编排器测试
│   ├── pm_agent/                  # PM Agent 测试
│   └── qa/                        # QA 模块测试
├── docs/                          # 文档目录
│   ├── architecture/              # 架构文档
│   ├── guides/                    # 使用指南
│   ├── qa/                        # QA 模块文档
│   └── technical-debt.md          # 技术债务清单
├── examples/                      # 使用示例
├── changelogs/                    # 变更日志
├── lee-logs.sh                    # 日志脚本
├── conftest.py                    # pytest 配置
├── pytest.ini                     # pytest 配置
├── pyproject.toml                 # 项目配置
└── .env.example                   # 环境变量模板
```

---

## 构建和运行

### 安装

```bash
# 基础安装
pip install -e .

# 完整安装（含可选依赖）
pip install -e ".[all]"

# 开发环境安装（含测试工具）
pip install -e ".[dev]"
```

### 配置

复制环境变量模板并根据实际情况修改：

```bash
cp .env.example .env
# 编辑 .env 文件，配置 LLM API 等信息
```

### 测试

```bash
# 运行所有测试
pytest tests/

# 运行特定目录测试
pytest tests/unit/
pytest tests/integration/
pytest tests/qa/

# 查看覆盖率
pytest --cov=src tests/
```

### CLI 使用

```bash
# 查看状态
lee status

# 运行工作流
lee run workflows/my_workflow.yaml

# 只生成 Plan
lee run workflows/my_workflow.yaml --plan-only

# 跳过 Plan，直接执行
lee run workflows/my_workflow.yaml --skip-plan

# 从指定 Instance 运行
lee run --instance instances/l2/my_instance.yaml

# 审批门禁
lee approve gate_id --approver "张三"

# 查看日志
lee log
```

### 代码质量检查

```bash
# 格式化代码（line-length: 100）
black src/

# 检查代码规范
flake8 src/

# 类型检查
mypy src/
```

---

## 开发约定

### 代码规范

- **Python 版本**: Python 3.8+
- **行长度**: 100 字符（Black 配置）
- **测试文件**: 命名为 `test_*.py`，放在 `tests/` 目录
- **类名**: 使用 PascalCase（如 `InstanceGenerator`）
- **函数名**: 使用 snake_case（如 `generate_instance`）
- **常量**: 使用 UPPER_SNAKE_CASE

### 测试实践

- 使用 pytest 作为测试框架
- 测试按层级组织：`unit/`, `integration/`, `e2e/`
- 每个模块应有对应的测试文件
- 测试覆盖率目标：> 70%
- 使用 conftest.py 共享测试配置和 fixture

### 工作流定义规范

- **唯一格式**: 所有新工作流必须使用 `spec-global` 格式
- **工作流文件**: 存放在 `spec-global/departments/{department}/workflows/{name}/v1/workflow.yaml`
- **格式标识**: 文件必须以 `kind: workflow` 开头
- **版本管理**: 使用 `version: 1.0` 标识格式版本

### 工作流执行流程

LEE 框架采用 **Plan → Instance → Execute** 统一流程：

1. **Plan Agent**: LLM 分析模板，生成执行计划
2. **Instance Generator**: 根据计划生成 Instance YAML 文件
3. **Review Gate**: 三种审批模式（simple/suggest/force）
4. **Orchestrator**: 从 Instance 文件加载并执行工作流

---

## 核心模块说明

### 1. Orchestrator (编排器)

- **位置**: `src/lee/orchestrator/`, `src/flowcore/orchestrator/`
- **职责**: 工作流调度、状态管理、事件溯源
- **核心类**:
  - `InstanceGenerator`: 根据 Plan 生成 Instance 文件
  - `PlanAgent`: LLM 分析模板生成执行计划
  - `WorkflowRunner`: 工作流执行引擎
  - `ReviewGate`: 审批门禁控制器

### 2. Engines (执行引擎)

- **位置**: `src/flowcore/engines/`
- **职责**: 执行不同类型的工作流节点
- **支持引擎**:
  - 单 Agent 引擎
  - Python/CLI 引擎

### 3. QA E2E 测试模块

- **位置**: `lee/qa/`
- **职责**: 从 YAML 测试用例生成可执行代码并执行
- **核心组件**:
  - `generator/`: 基于 LLM 的 Playwright 代码生成
  - `runner/`: 本地/Docker 测试执行器
  - `validator/`: 四层验证体系（结构/语法/语义/运行时）
  - `classifier/`: 错误分类器
  - `fixer/`: 自动修复器
- **测试状态**: 156 个测试用例，98.1% 通过率，76% 覆盖率

### 4. Config (配置系统)

- **位置**: `src/config/`, `config/`
- **职责**: 加载和管理项目配置
- **核心配置**:
  - `workspace.yaml`: 工作空间配置（从模板复制）
  - `llm_config.yaml`: LLM API 配置
  - `defaults.yaml`: 默认配置

---

## 技术债务

重要技术债务项详见 `docs/technical-debt.md`：

### QA E2E 模块（已完成核心功能）
- 高优先级：接入真实 LLM API、集成日志模块
- 中优先级：完善 Docker Runner、实现 RuntimeValidator
- 低优先级：多浏览器支持、并行测试、CI/CD 集成

### Artifact Management System
- 高优先级：`_get_git_info` 相对路径计算健壮性
- 中优先级：CLI 命令集成测试、性能基准测试

---

## 常见任务

### 创建新工作流

1. 在 `spec-global/departments/{department}/workflows/` 创建新目录
2. 创建 `v1/workflow.yaml` 文件，使用 `kind: workflow` 格式
3. 在 `spec-global/WORKFLOWS.md` 注册工作流

### 添加新 Agent

1. 在 `spec-global/departments/{department}/agents/` 创建目录
2. 编写 `implementation.yaml` 规范文件
3. 在 `src/lee/orchestrator/engines/` 实现执行逻辑

### 运行测试

```bash
# 单元测试
pytest tests/unit/

# 集成测试
pytest tests/integration/

# QA 模块测试
pytest tests/qa/

# E2E 测试
pytest tests/e2e/
```

### 查看日志

```bash
# 使用日志脚本
./lee-logs.sh

# 或直接查看 .workflow/logs/ 目录
```

---

## 相关资源

- **框架总览**: `docs/README.md`
- **变更日志**: `CHANGELOG.md`, `changelogs/`
- **技术债务**: `docs/technical-debt.md`
- **QA 模块文档**: `docs/qa/`
- **工作流汇总**: `spec-global/WORKFLOWS.md`
- **环境配置**: `.env.example`

---

## 版本信息

- **当前版本**: v0.2.0
- **最后更新**: 2026-02-26
- **Python 要求**: >= 3.8
- **许可**: MIT License

---

## 重要提示

1. **环境变量**: 使用 `.env` 文件配置 LLM API 和其他敏感信息，不要提交到 Git
2. **工作流格式**: 新工作流必须使用 `spec-global` 格式，旧的 `templates.yaml` 格式已废弃
3. **测试覆盖**: 修改核心功能时，必须确保测试通过且覆盖率达标
4. **执行器选择**: 默认使用 Claude Code，可通过配置切换
5. **技术债务**: 参见 `docs/technical-debt.md` 了解已知问题和改进计划
