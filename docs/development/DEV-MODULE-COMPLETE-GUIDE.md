# LEE Dev 模块完整指南

**版本**: v1.0
**更新日期**: 2026-02-27
**适用范围**: Dev 部门所有功能模块

---

## 目录

1. [概述](#概述)
2. [核心理念](#核心理念)
3. [目录结构](#目录结构)
4. [Spec 定义系统](#spec-定义系统)
5. [工作流体系](#工作流体系)
6. [Contract 契约系统](#contract-契约系统)
7. [Agent 体系](#agent-体系)
8. [Skill 体系](#skill-体系)
9. [Python 脚本和工具](#python-脚本和工具)
10. [中间产物和制成品管理](#中间产物和制成品管理)
11. [输入输出契约](#输入输出契约)
12. [执行架构](#执行架构)

---

## 概述

Dev 模块是 LEE 框架中负责研发阶段的核心模块，遵循 **Phase 驱动、契约先行、持续反馈** 的原则。通过 OpenSpec 作为 Phase 级运行时工作空间实现规范驱动开发。

### 核心职责

- **特性开发**: L2/L3 分层工作流管理完整开发流程
- **契约管理**: API 契约设计与评审，Single Source of Truth
- **代码实现**: 前后端并行开发，基于冻结契约
- **质量保障**: 6 步 TDD 流程，自动化测试
- **制品管理**: 产出物全生命周期管理

---

## 核心理念

### 1. Phase 驱动

将大项目拆分为可管理的 Phase，每个 Phase 有独立的契约和闭环。

### 2. 契约先行 (Contract-First)

- Test Contract 先于实现，确保需求可验证
- API 契约冻结后，前后端并行开发
- 契约是唯一事实来源 (Single Source of Truth)

### 3. 复杂度路由

| 复杂度 | 执行策略 | 适用场景 |
|--------|----------|----------|
| **S** | 直接执行 | 简单任务、测试 |
| **M** | Spawn 单个 L3 | 中等复杂度功能 |
| **L** | PMA 拆分 → 多个 L3 | 大型复杂功能 |

### 4. 6 步 TDD

```
对齐需求 → 设计测试 → 实现 → 测试 → Review → 复盘
[必须] [必须] [必须] [必须] [必须] [可选]
```

---

## 目录结构

```
lee/
├── spec-global/departments/dev/          # Spec 定义目录
│   ├── workflows/                        # 工作流定义
│   │   ├── feature/v3/workflow.yaml      # L2 v3 工作流
│   │   ├── templates/                    # 工作流模板
│   │   │   ├── feature-l2-template.yaml  # L2 模板
│   │   │   ├── l3/task-l3-v3-template.yaml  # L3 v3 模板 (6步TDD)
│   │   │   ├── feature-contract-l3-template.yaml
│   │   │   ├── feature-fe-l3-template.yaml
│   │   │   ├── feature-be-l3-template.yaml
│   │   │   ├── feature-integration-l3-template.yaml
│   │   │   └── bug-fix-l3-template.yaml
│   │   ├── instances/                    # 工作流实例
│   │   │   ├── l2/                       # L2 实例
│   │   │   └── l3-v3/                    # L3 v3 实例
│   │   └── phase-openspec-flow/v1/       # Phase OpenFlow 子流程
│   ├── contracts/                        # 契约定义
│   │   ├── frozen-dev-package-contract/v1/schema.json
│   │   ├── phase-contract/v1/schema.json
│   │   ├── api-contract/v1/schema.json
│   │   ├── requirement-analysis-contract/v1/schema.json
│   │   ├── test-code-diff-contract/v1/schema.json
│   │   ├── bug-fix-plan-contract/v1/schema.json
│   │   └── ...
│   ├── agents/                           # Agent 定义
│   │   ├── contract-designer/v1/agent.yaml
│   │   ├── uniapp-frontend-engineer/v1/agent.yaml
│   │   ├── go-backend-engineer/v1/agent.yaml
│   │   ├── code-reviewer/v1/agent.yaml
│   │   ├── code-self-reviewer/v1/agent.yaml
│   │   ├── bug-*/v1/agent.yaml           # Bug 修复相关 Agent
│   │   └── ...
│   ├── skills/                           # Skill 定义
│   │   ├── git-checkout/v1/skill.yaml
│   │   ├── vitest-runner/v1/skill.yaml
│   │   ├── pytest-runner/v1/skill.yaml
│   │   ├── ruff-lint/v1/skill.yaml
│   │   └── file-read/v1/skill.yaml
│   ├── standards/                        # 开发标准
│   │   ├── frontend-testing/v1/
│   │   └── observability/v1/
│   └── AGENTS.md                         # Dev 部门宪法
│
├── src/lee/orchestrator/                 # 编排器核心代码
│   ├── execution/                        # 执行层
│   │   ├── artifacts/                    # 产出物管理
│   │   ├── runners/                      # 执行器
│   │   ├── validators/                   # 验证器
│   │   ├── orchestrator.py               # 主编排器
│   │   └── pm_agent/                     # PMA (Planning Agent)
│   └── core/                             # 核心组件
│
├── scripts/                              # Python 脚本
│   ├── spec_validate.py                  # Spec 验证脚本
│   ├── setup_env.py                      # 环境设置脚本
│   └── install_requirements.py           # 依赖安装脚本
│
└── runtime/departments/dev/              # 运行时目录
    └── workflows/README.md
```

---

## Spec 定义系统

### L2/L3 工作流模板

#### L2 特性开发模板 (`feature-l2-template.yaml`)

```yaml
kind: l2_workflow_template
version: "2.1"
id: template.dev.feature
name: Feature Development L2 Template

phases:
  - id: contract_design      # P1: 契约设计
    default_complexity: L
    spawns_l3: true

  - id: frontend_dev         # P2.1: 前端开发
    default_complexity: L
    spawns_l3: true

  - id: backend_dev          # P2.2: 后端开发
    default_complexity: L
    spawns_l3: true

  - id: integration          # P3: 集成测试
    default_complexity: S

  - id: smoke_test           # P4: 冒烟测试
    default_complexity: S
```

#### L3 任务开发模板 (`task-l3-v3-template.yaml`)

**6 步 TDD 流程:**

| 步骤 | 名称 | 类型 | 必填 | 说明 |
|------|------|------|------|------|
| 1 | `align_requirement` | Agent | ✅ | 分析 Feature Spec，明确功能点 |
| 2 | `design_tests` | Agent | ✅ | 设计测试用例（测试先行） |
| 3 | `implement` | Agent | ✅ | 编写实现代码 |
| 4 | `run_tests` | Skill | ✅ | 运行单元测试 |
| 5 | `code_review` | Agent | ✅ | 代码评审 |
| 6 | `retrospective` | Agent | ❌ | 任务复盘 |

### Phase OpenSpec Flow

每个 Phase 内部运行 OpenSpec 子流程：

```
Init → Calibration → Test Contract → Proposal → Implementation → Unit Test → Review → Retrospective → Archive
```

---

## 工作流体系

### L2 工作流 v3

**文件**: `spec-global/departments/dev/workflows/feature/v3/workflow.yaml`

#### 阶段定义

| 阶段 ID | 名称 | 默认 Complexity | 说明 |
|---------|------|-----------------|------|
| `p1_contract_design` | 契约设计 | M | API 契约设计与评审 |
| `p2_1_fe_development` | 前端开发 | M | 前端实现（spawn L3） |
| `p2_2_be_development` | 后端开发 | M | 后端实现 |
| `p3_integration` | 集成测试 | S | 前后端联调 |
| `p4_smoke` | 冒烟测试 | S | 端到端测试 |

#### 阶段依赖关系

```
p1_contract_design (完成)
         ↓
    ┌────┴────┐
    ↓         ↓
p2_1_fe    p2_2_be   ← 可并行
    └────┬────┘
         ↓
   p3_integration
         ↓
      p4_smoke
```

### L3 工作流 v3

**文件**: `spec-global/departments/dev/workflows/templates/l3/task-l3-v3-template.yaml`

#### 6 步 TDD 流程详细说明

1. **对齐需求 (`align_requirement`)**
   - 分析 Feature Spec
   - 产出需求分析文档
   - 明确输入/输出/边界条件
   - 列出验收标准

2. **设计测试 (`design_tests`)**
   - 根据需求分析设计测试用例
   - 覆盖正常路径、异常路径、边界条件
   - 测试基于接口定义，不依赖内部实现
   - 此阶段只写测试代码，不写业务实现

3. **实现 (`implement`)**
   - 根据测试用例编写实现代码
   - 参照测试用例理解接口契约
   - 编写最小化实现代码
   - 实现完成后所有测试应为绿色

4. **测试 (`run_tests`)**
   - 执行单元测试
   - 生成测试覆盖率报告
   - 确保所有测试通过

5. **Review (`code_review`)**
   - 代码自检与评审
   - 检查代码质量与规范
   - 检查测试覆盖率
   - 验证功能完整性

6. **复盘 (`retrospective`)**
   - 任务复盘与总结
   - 记录遇到的问题与解决方案
   - 提出改进建议

### 执行策略

| 级别 | 名称 | 执行策略 | L3 Spawning |
|------|------|----------|-------------|
| **S** | Simple | 直接执行阶段步骤 | 否 |
| **M** | Medium | Spawn 单个 L3 | 是 (1个) |
| **L** | Large | PMA 拆分 → 多个 L3 | 是 (2-5个) |

---

## Contract 契约系统

### 契约类型

#### 1. 研发冻结包契约 (Frozen Dev Package)

**文件**: `contracts/frozen-dev-package-contract/v1/schema.json`

L2 工作流的标准输入，包含完整的前置契约信息。

```json
{
  "contract_type": "frozen-dev-package",
  "metadata": {
    "package_id": "FPKG-20260224-001",
    "created_at": "2026-02-24T10:00:00Z",
    "total_confidence_score": 85
  },
  "package_content": {
    "prd_ref": "path/to/frozen-detailed-prd.yaml",
    "tech_ref": "path/to/frozen-technical-architecture.yaml",
    "ui_ref": "path/to/frozen-ui-prototype.yaml"
  },
  "scheduling_validation": {
    "q1_non_goals": "这个需求不做什么？",
    "q2_simplification": "哪些地方允许先简化/降级？",
    "q3_uncertainties": "技术上最不确定的1-2个点是什么？",
    "q4_ui_priority": "哪些UI必须现在定，哪些可以后补？",
    "q5_cut_sequence": "如果延期，最先砍哪一块？"
  }
}
```

#### 2. Phase 契约

**文件**: `contracts/phase-contract/v1/schema.json`

Phase 级研发契约，定义 OpenSpec 子流程与主流程的边界协议。

```json
{
  "phase_id": "auth",
  "phase_name": "Authentication",
  "status": "in_progress",
  "inputs": {
    "requirement_source": "path/to/requirement.md",
    "ui_source": "path/to/ui-prototype.yaml"
  },
  "outputs": {
    "deliverables": [
      { "type": "api", "path": "src/api/auth.ts" }
    ],
    "interfaces": [
      { "name": "LoginAPI", "type": "rest_api" }
    ]
  },
  "quality_gates": {
    "unit_test": { "coverage_threshold": 80 }
  }
}
```

#### 3. API 契约

**文件**: `contracts/api-contract/v1/schema.json`

API 接口契约定义。

#### 4. 需求分析契约

**文件**: `contracts/requirement-analysis-contract/v1/schema.json`

需求分析输出契约。

### 契约验证标准

#### 验证层次

1. **Level 1**: 工作流启动前 - 输入契约验证
2. **Level 2**: 步骤执行前 - 输入契约验证
3. **Level 3**: 步骤执行后 - 输出契约验证（含重试机制）

#### 处理策略

| 策略 | 行为 | 使用场景 |
|------|------|----------|
| `block` | 阻塞执行 | 关键输入契约验证失败 |
| `warn` | 仅警告 | 非关键输出验证失败 |
| `retry` | 自动重试 | 输出验证失败（L3 步骤） |

---

## Agent 体系

### Agent 定义规范

所有 Agent 遵循 YAML v1.0 规范，必须包含：

```yaml
kind: agent
version: 1.0

# Dev 部门宪法引用 (强制)
constitution:
  ref: ../../AGENTS.md
  version: "1.0"
  mandatory: true

id: agent.dev.<name>
name: <Agent Name>
description: >
  Agent 描述

# 契约定义
contracts:
  input_schema: ../../contracts/<input>/v1/schema.json
  output_schema: ../../contracts/<output>/v1/schema.json

# 角色定义
persona:
  role: "<角色>"
  style: "<风格>"

# 策略定义
policy:
  decision_rules: [...]
  quality_bar: {...}
  refusal: {...}

# 禁止行为
forbidden_behaviors: [...]

# 职责边界
responsibility:
  in_scope: [...]
  out_of_scope: [...]
```

### Dev 部门 Agent 列表

#### 核心开发 Agent

| Agent ID | 名称 | 职责 |
|----------|------|------|
| `agent.dev.contract_designer` | Contract Designer | 设计并维护 API 协议与 DTO 结构 |
| `agent.dev.uniapp_frontend_engineer` | UniApp Frontend Engineer | UniApp 前端实现（支持 TDD 任务路由） |
| `agent.dev.go_backend_engineer` | Go Backend Engineer | Go 后端实现 |
| `agent.dev.code_reviewer` | Code Reviewer | 代码评审 |
| `agent.dev.code_self_reviewer` | Code Self Reviewer | 代码自检与评审 |

#### Bug 修复 Agent

| Agent ID | 名称 | 职责 |
|----------|------|------|
| `agent.dev.bug_triage` | Bug Triage | Bug 分类和优先级评估 |
| `agent.dev.bug_reproducer` | Bug Reproducer | Bug 复现 |
| `agent.dev.bug_root_cause_analyst` | Root Cause Analyst | 根因分析 |
| `agent.dev.bug_fix_planner` | Fix Planner | 修复计划 |
| `agent.dev.bug_fix_implementer` | Fix Implementer | 修复实现 |
| `agent.dev.bug_fix_verifier` | Fix Verifier | 修复验证 |
| `agent.dev.bug_knowledge_curator` | Knowledge Curator | 知识沉淀 |
| `agent.dev.bug_technical_debt_recorder` | Technical Debt Recorder | 技术债务记录 |

#### 其他 Agent

| Agent ID | 名称 | 职责 |
|----------|------|------|
| `agent.dev.tech_architect` | Tech Architect | 技术架构设计 |
| `agent.dev.integration_planner` | Integration Planner | 集成计划 |
| `agent.dev.smoke_tester` | Smoke Tester | 冒烟测试 |
| `agent.dev.unit_test_runner` | Unit Test Runner | 单元测试执行 |
| `agent.dev.unit_test_writer` | Unit Test Writer | 单元测试编写 |
| `agent.dev.git_committer` | Git Committer | Git 提交 |
| `agent.dev.freeze_orchestrator` | Freeze Orchestrator | 冻结流程编排 |
| `agent.dev.code_completion_checker` | Code Completion Checker | 代码完成度检查 |

### Agent 宪法

**文件**: `spec-global/departments/dev/AGENTS.md`

Dev 部门宪法定义了所有 Agent 必须遵守的核心原则和规范。

---

## Skill 体系

### Skill 定义规范

```yaml
kind: skill
version: 1.0

id: skill.<category>.<name>
name: <Skill Name>
description: >
  Skill 描述

interface:
  inputs:
    type: object
    required: [...]
    properties: {...}
  outputs:
    type: object
    properties: {...}

runtime:
  type: cli
  command: "<command>"
  args_template: "<template>"
  exit_codes: {...}

constraints:
  - must_pass: "<condition>"
    on_fail: "<action>"
```

### Dev 部门 Skill 列表

| Skill ID | 名称 | 职责 |
|----------|------|------|
| `skill.git.checkout` | Git Checkout | 切换/创建目标分支 |
| `skill.test.vitest` | Vitest Runner | 运行 Vitest 前端单元测试 |
| `skill.test.pytest` | Pytest Runner | 运行 Python 单元测试 |
| `skill.lint.ruff` | Ruff Lint | Python 代码检查 |
| `skill.dev.file_read` | File Read | 读取文件内容 |

### Skill 三分法分类

- **tools**: 有 runtime 块，可执行
- **specs**: 有 spec 文件，无 runtime（参考用）
- **capabilities**: 可选能力，不强制

---

## Python 脚本和工具

### 核心脚本

#### 1. Spec 验证脚本 (`scripts/spec_validate.py`)

三分法 Spec 引用完整性验证器。

```bash
python scripts/spec_validate.py              # 检查所有
python scripts/spec_validate.py --strict     # 严格模式
```

校验规则:
- **E001**: workflow → agent 引用：对应 agent.yaml 必须存在
- **E002**: agent tools: → skill spec：必须有 spec 文件且 spec 有 runtime: 块
- **E003**: agent specs: → skill spec：必须有 spec 文件（runtime 可选）
- **W001**: agent capabilities: 中有 spec 文件的 skill → 建议移到 tools/specs

#### 2. 环境设置脚本 (`scripts/setup_env.py`)

加载 .env 文件并配置环境。

```bash
python scripts/setup_env.py
```

功能:
- 加载 .env 文件
- 设置 PYTHONPATH
- 验证环境配置

#### 3. 依赖安装脚本 (`scripts/install_requirements.py`)

安装所有必需的依赖。

```bash
python scripts/install_requirements.py
```

功能:
- 安装 Python 依赖（pyyaml, aiohttp, python-dotenv, openai）
- 安装 MCP Server（Node.js）
- 创建 .gitignore 文件

### 工具脚本

#### `/tools/` 目录

| 脚本 | 职责 |
|------|------|
| `create_department_readmes.py` | 创建部门说明 |
| `update_imports.py` | 更新导入 |
| `verify_env.py` | 验证环境 |

---

## 中间产物和制成品管理

### 产出物类型

| 类型 | 说明 | 类别示例 |
|------|------|----------|
| `CONTRACT` | 契约类 | frozen_prd, api_contract, test_plan, design_doc |
| `DOCUMENT` | 文档类 | readme, usage_guide, investigation_report |
| `CODE_REF` | 代码引用类 | implementation, config, script |
| `PATCH` | 补丁类 | feature_patch, bugfix_patch, refactor_patch |
| `TEST` | 测试类 | test_report, test_case, coverage_report |
| `HANDOVER` | 移交类 | to_qa, to_backend, to_frontend |
| `LOG` | 日志类 | execution_log, error_log, debug_log |
| `INTERMEDIATE` | 中间产物 | draft, temp, scratch |

### 产出物状态

| 状态 | 说明 |
|------|------|
| `DRAFT` | 草稿状态，可编辑 |
| `ACTIVE` | 活跃状态，正在使用 |
| `FROZEN` | 冻结状态，不可变 |
| `ARCHIVED` | 归档状态 |
| `DEPRECATED` | 废弃状态 |

### ArtifactManager

**文件**: `src/lee/orchestrator/execution/artifacts/manager.py`

核心功能:

1. **创建产出物 (`create`)**
   - 支持字符串、字节、文件路径
   - 自动生成 ART-xxxxx ID
   - 计算内容哈希
   - 文件大小限制 (100MB)

2. **Adopt 外部文件 (`adopt`)**
   - `copy_mode`: 复制文件内容到 .artifacts/
   - `reference_mode`: 仅保存 git 引用 (SHA + path)

3. **冻结产出物 (`freeze`)**
   - 移动到 frozen/ 目录
   - 状态变为 FROZEN

4. **获取内容 (`get_content`)**
   - copy_mode: 从文件读取
   - reference_mode: 从 git 获取

### ManifestManager

**文件**: `src/lee/orchestrator/execution/artifacts/manifest.py`

Run 级 Manifest 管理，每个 run 的权威产出物记录。

功能:
- 创建/获取/保存 manifest
- 添加产出物
- 更新状态
- 冻结 run
- 获取移交产出物
- 统计信息
- 清理旧 runs

### 目录结构

```
.artifacts/
├── active/                    # 活跃产出物
│   ├── <department>/          # 按部门组织
│   │   └── <run_id>/
│   │       ├── manifest.yaml
│   │       └── ART-xxxxx.*
│   └── <run_id>/
├── frozen/                    # 冻结产出物
│   └── <run_id>.yaml
├── archive/                   # 归档产出物
├── logs/                      # 日志文件
└── cache/                     # 缓存
```

---

## 输入输出契约

### L2 输入契约

```yaml
contracts:
  inputs:
    - frozen_dev_package:
        path: ../../contracts/frozen-dev-package-contract/v1/schema.json
        validation:
          enabled: true
          on_failure: block
          schema_validation:
            - field: contract_type
              required: true
              allowed_values: ["frozen-dev-package"]
            - field: package_content.prd_ref
              required: true
              check: file_exists
```

### L2 输出契约

```yaml
  outputs:
    - l2_outputs:
        path: ../../contracts/l2-outputs/v1/schema.json
        validation:
          enabled: true
          on_failure: warn
          required_artifacts:
            - output/api-contract.yaml
            - output/fe-l3-output.json
            - output/be-code-diff.patch
```

### L3 步骤输出验证（含重试）

```yaml
step_output_validation:
  implement:
    contract_ref: ../../contracts/code-diff/v1/schema.json
    on_failure: retry
    max_retries: 3
    retry_delay_seconds: 5
    required_fields:
      - files_changed
      - diff_summary
```

---

## 执行架构

### Orchestrator

**文件**: `src/lee/orchestrator/execution/orchestrator.py`

主编排器，负责工作流的执行调度。

核心功能:
- 工作流实例管理
- 阶段调度
- L3 子流程派发
- 事件发布订阅
- 错误处理和重试

### 执行器 (Runners)

**目录**: `src/lee/orchestrator/execution/runners/`

| 执行器 | 职责 |
|--------|------|
| `BaseRunner` | 执行器基类 |
| `LLMRunner` | LLM 调用执行器 |
| `ShellRunner` | Shell 命令执行器 |
| `GateRunner` | 质量门执行器 |
| `PatchApplyRunner` | 补丁应用执行器 |

### 验证器 (Validators)

**目录**: `src/lee/orchestrator/execution/validators/`

| 验证器 | 职责 |
|--------|------|
| `Validator` | 验证器基类 |
| `SchemaValidator` | JSON Schema 验证 |
| `FileValidator` | 文件验证 |

### 事件总线

**文件**: `src/lee/orchestrator/core/event_bus.py`

事件驱动架构，支持:

- `L3_SPAWNED`: L3 子流程派发事件
- `PHASE_COMPLETED`: 阶段完成事件
- `WORKFLOW_COMPLETED`: 工作流完成事件

---

## 附录

### 相关文档

- [L2/L3 v3 用户指南](../spec-global/departments/dev/workflows/L2_L3_v3_User_Guide.md)
- [契约验证标准](../spec-global/departments/dev/contracts/contract-validation-standard/v1/guide.md)
- [Dev 部门宪法](../spec-global/departments/dev/AGENTS.md)

### 更新日志

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.0 | 2026-02-27 | 初始版本，完整梳理 Dev 模块 |

---

**文档维护**: Dev Workflow Team
