# LEE 框架项目问题分析报告

**分析日期**: 2026-03-04  
**分析范围**: 项目架构、代码组织、功能实现、版本管理  
**重点关注**: 功能实现未集成、同类功能重复实现、版本混乱

---

## 一、核心架构问题

### 1.1 flowcore 包名存实亡（P0 - 严重）

**问题描述**:
```
README.md 声称:
├── flowcore/                    # 核心代码包
│   ├── orchestrator/             # 工作流编排器
│   ├── engines/                  # 执行引擎
│   ├── utils/                    # 工具模块
│   └── cli/                      # 命令行工具

实际代码结构:
src/flowcore/
├── __init__.py        # 仅有兼容性注释 "Compatibility package for legacy flowcore imports"
└── cli/
    ├── __init__.py    # 空文件
    └── main.py        # 仅 6 行代码，转发到 lee.cli.main

实际代码位置:
src/lee/
├── cli/                        # CLI 实现（完整）
├── orchestrator/               # 编排器实现（200+ 文件）
│   ├── api/
│   ├── core/                   # 核心功能（TemplateManager 等）
│   ├── execution/              # 执行层（另一个 TemplateManager！）
│   ├── storage/
│   └── ...
├── qa/                         # QA E2E 模块
└── runtime/                    # 运行时
```

**影响**:
- 文档与代码严重不符
- `pip install lee-framework` 后无法按文档示例使用
- 违反语义化版本约定 (v0.1.0 应包含承诺的功能)

---

## 二、同类功能重复实现

### 2.1 TemplateManager 双重实现（P0 - 严重）

**两个独立实现的 TemplateManager**:

| 文件 | 行数 | 版本 | 状态 |
|------|------|------|------|
| `src/lee/orchestrator/core/template_manager.py` | 115 | v1.0 (旧) | 基本废弃 |
| `src/lee/orchestrator/execution/template_manager.py` | 1000+ | v3.6 (新) | 活跃使用 |

**core/template_manager.py** (v1.0 - 简化版):
- 仅支持基本的 YAML 加载
- 使用 SimpleNamespace 包装模板
- 无 spec-global 格式支持
- 无 L2/L3 模板解析

**execution/template_manager.py** (v3.6 - 完整版):
- 支持 spec-global 格式 (kind: workflow)
- 支持 L2/L3 模板 (kind: l2_workflow_template, l3_workflow_template)
- 支持拓扑排序、依赖验证
- 集成 IRConverter、SpecGlobalParser
- 完整的缓存机制

**问题**:
- 两个类同名但功能差异巨大
- 容易产生混淆和错误导入
- 维护成本翻倍

### 2.2 Runner 类层次混乱（P1 - 重要）

**多个层次的 Runner 实现**:

```
src/lee/qa/runner/
├── base.py          # BaseRunner (抽象基类)
├── local.py         # LocalRunner (本地执行)
└── docker.py        # DockerRunner (容器执行)

src/lee/orchestrator/execution/runners/
├── base.py          # StepRunnerStrategy, StepRunnerBase
├── llm_runner.py    # LLMRunner, ClaudeCodeRunner
├── shell_runner.py  # SkillRunner, OrchestratorCLIRunner
├── gate_runner.py   # HumanGateRunner, ComplianceGateRunner
├── patch_apply_runner.py  # PatchApplyRunner
└── registry.py      # StepRunnerRegistry

src/lee/orchestrator/execution/
├── workflow_runner.py   # WorkflowRunner (Plan → Instance → Execute)
└── orchestrator.py      # Orchestrator (核心调度器)
```

**继承关系混乱**:
```python
# QA 模块
class BaseRunner(ABC): ...
class LocalRunner(BaseRunner): ...

# Orchestrator 模块  
class StepRunnerStrategy(ABC): ...
class StepRunnerBase(StepRunnerStrategy): ...
class LLMRunner(StepRunnerBase): ...

# 完全独立的两套体系，没有统一接口
```

### 2.3 技能定义分散两处（P1 - 重要）

**技能定义位置 1 - 项目内 (spec-global)**:
```
spec-global/departments/
├── dev/skills/           (6 skills)
├── devops/skills/        (6 skills)
├── media/skills/         (9 skills)
├── office/skills/        (5 skills)
├── qa/skills/            (6 skills)
└── ui/skills/            (1 skill)
```

**技能定义位置 2 - 全局配置 (~/.config/agents/skills)**:
```
lee-bug-fix/
lee-feature/
lee-feature-be/
lee-feature-contract/
lee-feature-fe/
lee-feature-integration/
lee-product-pipeline/
lee-product-to-dev-pipeline/
lee-test-plan-execution/
lee-test-set-production/
```

**问题**:
- 同一功能在不同位置重复定义
- spec-global 中的技能是 YAML 定义
- ~/.config 中的技能是 SKILL.md 文档
- 两者没有同步机制

### 2.4 Executor 多重实现（P1 - 重要）

**多种 Executor 实现**:
```
src/lee/orchestrator/execution/
├── executors.py           # ExecutorFactory (统一工厂)
├── llm_executor.py        # LLMExecutor
├── legacy_executor_executor.py    # Legacy ExecutorExecutor
├── mock_executor.py       # MockExecutor
├── langgraph_executor.py  # LangGraphExecutor
├── claude_code_executor.py # ClaudeCodeExecutor
└── codex_executor.py      # CodexExecutor
```

**问题**:
- 部分 Executor 未实现完成 (MockExecutor 混用代理模式)
- 没有统一的执行接口文档
- 选择逻辑复杂，依赖配置项 `executor.default_type`

---

## 三、版本混乱问题

### 3.1 Workflow 定义格式不统一（P0 - 严重）

**四种并存的工作流格式**:

1. **spec-global 格式** (推荐，但复杂):
```yaml
# spec-global/departments/*/workflows/*/v1/workflow.yaml
kind: workflow
version: 1.0
id: workflow.prd.product_pipeline
stages:
  - id: stage_1
    steps:
      - id: step_1
        run: agent.prd.xxx
```

2. **旧格式** (废弃中):
```yaml
# examples/templates.yaml
id: bug-fix
level: task
name: Bug Fix Workflow
steps:
  - id: analyze
    type: agent
```

3. **L2 模板格式**:
```yaml
# spec-global/departments/dev/workflows/templates/feature-l2-template.yaml
kind: l2_workflow_template
id: template.feature.l2
description: Feature L2 Template
phases:
  - id: contract
    name: Contract Design
```

4. **L3 模板格式**:
```yaml
# spec-global/departments/dev/workflows/templates/*-l3-template.yaml
kind: l3_workflow_template
id: template.feature.l3.contract
steps:
  - id: contract_design
    name: Contract Design
    run: agent.dev.contract_designer
```

**问题**:
- 同一项目需要支持 4 种格式
- 解析器代码复杂 (`template_manager.py` 的 `_parse_template_doc` 方法 200+ 行)
- 文档分散，用户不知该用哪种

### 3.2 模板版本管理混乱（P1 - 重要）

**同一模板多个版本并存**:
```
spec-global/departments/qa/workflows/templates/
├── test-plan-l2-template.yaml          # v1.0 (旧)
├── test-plan-l2-template-v2.1.yaml     # v2.1 (新)
├── test-set-l3-template.yaml           # v1.0 (旧)
├── test-set-l3-template-v1.1.yaml      # v1.1 (新)
└── test-set-production-l3-template.yaml
```

**问题**:
- 没有明确的版本淘汰机制
- 新旧版本同时维护
- 用户不知该引用哪个版本

### 3.3 代码版本标识不一致（P2 - 中等）

**版本号到处散落**:
```python
# src/lee/orchestrator/execution/orchestrator.py
"""LEE Orchestrator v3.1 - 核心调度器"""

# src/lee/orchestrator/execution/template_manager.py
"""LEE Orchestrator v3.0 - 模板管理器"""

# src/lee/orchestrator/storage/models.py
"""LEE Orchestrator v3.0 - 统一数据模型"""

# src/lee/orchestrator/execution/workflow_runner.py
"""Workflow Runner - Plan → Instance → Execute 流程控制器"""  # 无版本号
```

**问题**:
- 版本号不统一 (v3.0, v3.1 混用)
- 没有 CHANGELOG 记录各版本变更
- 用户无法确定使用的版本

---

## 四、功能未集成问题

### 4.1 flowcore 包未实现功能（P0 - 严重）

根据 README，flowcore 应该包含:
- ✅ `flowcore.cli.main` - 仅转发到 lee.cli.main
- ❌ `flowcore.orchestrator.runner` - 不存在
- ❌ `flowcore.orchestrator.state_machine` - 不存在
- ❌ `flowcore.engines.base` - 不存在
- ❌ `flowcore.engines.legacy_executor.adapter` - 不存在
- ❌ `flowcore.utils.logging` - 不存在
- ❌ `flowcore.utils.ids` - 不存在

### 4.2 Docker Runner 未完整实现（P1 - 重要）

```python
# src/lee/qa/runner/docker.py
class DockerRunner(BaseRunner):
    """Docker 测试运行器"""
    
    async def run(self, test_case: TestCase) -> TestResult:
        # TODO: 完整实现 Docker 执行逻辑
        raise NotImplementedError("Docker runner not fully implemented")
```

### 4.3 RuntimeValidator 未实现（P1 - 重要）

```python
# src/lee/orchestrator/execution/validators/
├── base.py              # ValidatorBase (有)
├── file_validator.py    # FileValidator (有)
└── schema_validator.py  # SchemaValidator (有)

# 缺少 RuntimeValidator
```

### 4.4 工作流迁移工具缺失（P1 - 重要）

README 声称提供:
```bash
lee migrate-workflow <template_id> --output spec-global/workflows/
```

实际:
```
# src/lee/orchestrator/tools/migrate_workflow.py 存在
# 但没有注册到 CLI 命令
```

---

## 五、配置管理混乱

### 5.1 多配置文件并存

```
项目根目录/
├── .env                    # 环境变量
├── .env.example           # 环境变量示例
├── config/                # 配置目录
│   └── workspace.template.yaml
├── .lee/                  # LEE 项目配置
│   └── config.yaml        # 运行时配置
└── spec-global/           # 全局规范
    └── _metadata.yaml     # 元数据配置
```

**问题**:
- 没有统一配置加载顺序文档
- 配置项分散，难以查找
- 优先级不明确

### 5.2 模板路径解析逻辑复杂

```python
# src/lee/orchestrator/api/__init__.py
template_dir = Path(normalized_project_dir) / "lee" / "spec-global"
if not template_dir.exists():
    parent_lee = Path(normalized_project_dir).parent / "lee" / "spec-global"
    # ... 多层 fallback
```

---

## 六、建议整改方案

### 阶段一：架构统一（2周）

1. **统一 flowcore 包**:
   - 删除空的 flowcore/ 目录，或将其重定向到 lee/
   - 更新 README 文档，移除不存在的导入示例

2. **合并 TemplateManager**:
   - 删除 `core/template_manager.py`
   - 保留 `execution/template_manager.py`
   - 更新所有导入引用

3. **统一 Runner 体系**:
   - 将 QA Runner 统一到 orchestrator/runners/
   - 定义统一的 RunnerInterface

### 阶段二：版本规范（1周）

1. **统一版本标识**:
   - 在 `__init__.py` 中定义单一版本号
   - 移除各文件中的分散版本注释

2. **规范工作流格式**:
   - 制定迁移计划，逐步淘汰旧格式
   - 完善 spec-global 格式文档

3. **模板版本管理**:
   - 建立版本淘汰机制
   - 在模板中明确标注版本状态 (stable/deprecated/obsolete)

### 阶段三：功能补全（2周）

1. **实现缺失功能**:
   - 完成 DockerRunner
   - 实现 RuntimeValidator
   - 注册 migrate-workflow CLI 命令

2. **集成技能定义**:
   - 统一技能定义位置
   - 建立技能文档自动生成机制

### 阶段四：文档更新（1周）

1. 重写 README.md，确保与代码一致
2. 创建架构决策记录 (ADR)
3. 编写贡献者指南

---

## 七、问题优先级汇总

| 优先级 | 问题 | 影响 | 整改建议 |
|--------|------|------|----------|
| P0 | flowcore 包缺失 | 无法按文档使用 | 删除或重定向 |
| P0 | TemplateManager 双重实现 | 维护困难，易混淆 | 合并为一个 |
| P0 | Workflow 格式不统一 | 解析复杂，用户困惑 | 统一为 spec-global |
| P1 | Runner 类层次混乱 | 扩展困难 | 统一接口 |
| P1 | 技能定义分散 | 同步困难 | 统一位置 |
| P1 | Docker Runner 未完成 | CI/CD 集成受阻 | 完成实现 |
| P1 | 迁移工具未注册 | 向后兼容性差 | 注册 CLI |
| P2 | 版本标识不一致 | 难以追踪 | 统一版本管理 |
| P2 | 配置管理混乱 | 使用困难 | 统一配置加载 |

---

## 八、结论

LEE 框架的核心功能已经实现，但存在严重的架构组织和版本管理问题：

1. **文档与代码严重不符** - flowcore 包名存实亡
2. **功能重复实现** - TemplateManager、Runner 等多处重复
3. **版本管理混乱** - 4 种 workflow 格式并存，无淘汰机制
4. **功能未集成** - 多个功能实现但未完整接入系统

建议优先解决 P0 级别问题，确保框架可用性，再逐步完善 P1/P2 级别问题。
