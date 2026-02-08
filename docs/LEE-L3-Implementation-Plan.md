# LEE L3 工作流实施计划

> **版本**: v1.0
> **创建日期**: 2026-02-07
> **状态**: 待审批
> **范围**: 支撑最基础的 AI 工程研发自动化工作流

---

## 1. 背景与目标

### 1.1 北极星目标

> 用「**Spec + Orchestrator + 部门化工作流**」，把 **人类、传统程序、AI Agent** 三方接到一条最小可用的研发流水线上，人类只在关键 Gate 上拍板，其余都让自动化跑起来。

### 1.2 当前版本范围

- 只覆盖 **工程 L3 流程**（Dev / QA / DevOps）
- 产品、商业、架构层（L1 / L2）先以「人类 + 简单模板」为主
- 不追求「最聪明的 Agent」，只追求「**最小闭环** + **可持续演进**」

### 1.3 当前状态总结

| 组件 | 状态 | 说明 |
|------|------|------|
| Orchestrator 核心 | ✅ 完成 | v3.0，SQLite 状态管理，Gate 系统 |
| spec-global 结构 | ✅ 完成 | 7 部门组织，100+ agents，50+ contracts |
| bug-fix workflow | ✅ 完成 | 7 阶段，30+ 步骤 |
| Executor 层 | ✅ 完成 | LLM/MetaGPT/Shell |
| dev_feature_l3 | ❌ 缺失 | 核心开发工作流 |
| qa_regression_l3 | ❌ 缺失 | 核心测试工作流 |
| devops_deploy_l3 | ❌ 缺失 | 核心部署工作流 |
| `lee run` CLI | ❌ 缺失 | 简化命令入口 |
| Verifier 系统 | ❌ 缺失 | 硬性规则检查 |
| 资产层规范 | ⚠️ 不完整 | 缺 /evidence/, /env/ |

---

## 2. 实施阶段概览

```
┌──────────────────────────────────────────────────────────────────┐
│ Phase 1: 核心 L3 工作流 (优先级: P0)                               │
│   目标: Dev/QA/DevOps 三部门各有一条可跑通的最小工作流               │
│   预计产出: 3 个完整 workflow + 配套 agents/contracts               │
└──────────────────────────────────────────────────────────────────┘
                                  ↓
┌──────────────────────────────────────────────────────────────────┐
│ Phase 2: 统一 CLI 入口 (优先级: P1)                                │
│   目标: lee run <dept>.<workflow> 简化命令                         │
│   预计产出: lee CLI + 工作流注册表                                  │
└──────────────────────────────────────────────────────────────────┘
                                  ↓
┌──────────────────────────────────────────────────────────────────┐
│ Phase 3: 资产层规范化 (优先级: P1)                                  │
│   目标: /spec/ /evidence/ /env/ 目录规范                           │
│   预计产出: 目录规范文档 + 模板 + Evidence 收集机制                   │
└──────────────────────────────────────────────────────────────────┘
                                  ↓
┌──────────────────────────────────────────────────────────────────┐
│ Phase 4: Verifier 系统 (优先级: P2)                                │
│   目标: 硬性规则检查，违规直接中断                                   │
│   预计产出: Verifier 接口 + 内置 verifiers                          │
└──────────────────────────────────────────────────────────────────┘
                                  ↓
┌──────────────────────────────────────────────────────────────────┐
│ Phase 5: 跨部门串联 (优先级: P3, 下一版本)                          │
│   目标: Dev → QA → DevOps 一键 pipeline                            │
│   预计产出: Pipeline Spec + 自动触发机制                            │
└──────────────────────────────────────────────────────────────────┘
```

---

## 3. Phase 1: 核心 L3 工作流

### 3.1 目标

让 Dev/QA/DevOps 三个部门各有一条可跑通的最小工作流，实现「最小闭环」。

### 3.2 任务分解

#### 3.2.1 dev_feature_l3 (开发特性工作流)

**职责**: 从 Spec → 代码实现 → 自测通过 → 准备好给 QA

**输入**:
- `spec/dev/feature_x.yaml`（需求摘要、接口定义、验收标准）
- 目标分支（如 `feature/x`）

**工作流阶段**:

| 阶段 | 步骤 | 执行者 | 说明 |
|------|------|--------|------|
| s1_prepare | s1_1_pull_branch | Program | 拉取最新代码，切分支 |
| s1_prepare | s1_2_parse_spec | Agent | 解析 Feature Spec，提取实现要点 |
| s2_coding | s2_1_generate_code | Agent | Coding Agent 生成/修改代码 |
| s2_coding | s2_2_static_check | Program | 运行 lint / format |
| s2_coding | s2_3_unit_test | Program | 运行单元测试 |
| s3_review | s3_1_self_review | Agent | AI 自审代码质量 |
| s3_review | s3_2_generate_summary | Agent | 生成变更说明 |
| s4_gate | s4_1_dev_gate | Human | Dev Lead 审批 |

**输出**:
- 代码变更（uncommitted，等待审批后提交）
- 变更说明文档
- 单测报告

**需创建的文件**:

```
spec-global/departments/dev/workflows/feature/v1/
├── workflow.yaml
├── agents/
│   ├── feature-spec-parser/
│   │   └── v1/agent.yaml
│   ├── feature-coder/
│   │   └── v1/agent.yaml
│   └── code-self-reviewer/
│       └── v1/agent.yaml
├── contracts/
│   ├── feature-spec.schema.json
│   ├── code-diff.schema.json
│   └── change-summary.schema.json
└── gates/
    └── dev-feature-gate/
        └── v1/gate.yaml
```

---

#### 3.2.2 qa_regression_l3 (回归测试工作流)

**职责**: 执行回归测试，归纳问题，生成 Bug 草稿

**输入**:
- `spec/qa/release_x.yaml`（测试计划、用例列表）
- 测试环境信息

**工作流阶段**:

| 阶段 | 步骤 | 执行者 | 说明 |
|------|------|--------|------|
| s1_prepare | s1_1_deploy_test_env | Program | 部署到测试环境（调用 devops） |
| s1_prepare | s1_2_parse_test_plan | Agent | 解析测试计划 |
| s2_generate | s2_1_generate_scripts | Agent | 生成测试脚本（Playwright/API） |
| s3_execute | s3_1_run_tests | Program | 执行测试用例 |
| s3_execute | s3_2_collect_results | Program | 收集结果、日志、截图 |
| s4_analyze | s4_1_analyze_failures | Agent | 归类失败用例 |
| s4_analyze | s4_2_draft_bugs | Agent | 生成 Bug 草稿 |
| s5_gate | s5_1_qa_gate | Human | QA 认可，确认 Bug 列表 |

**输出**:
- 测试报告（通过率、失败列表）
- Bug 列表（JSON/Markdown）
- 测试日志/截图

**需创建的文件**:

```
spec-global/departments/qa/workflows/regression/v1/
├── workflow.yaml
├── agents/
│   ├── test-plan-parser/
│   │   └── v1/agent.yaml
│   ├── test-script-generator/
│   │   └── v1/agent.yaml
│   ├── failure-analyzer/
│   │   └── v1/agent.yaml
│   └── bug-drafter/
│       └── v1/agent.yaml
├── contracts/
│   ├── test-plan.schema.json
│   ├── test-result.schema.json
│   └── bug-draft.schema.json
└── gates/
    └── qa-regression-gate/
        └── v1/gate.yaml
```

---

#### 3.2.3 devops_deploy_l3 (部署工作流)

**职责**: 脚本化部署，健康检查，生成部署报告

**输入**:
- 目标环境（staging/production）
- 版本/commit

**工作流阶段**:

| 阶段 | 步骤 | 执行者 | 说明 |
|------|------|--------|------|
| s1_prepare | s1_1_validate_version | Program | 验证版本存在、CI 通过 |
| s1_prepare | s1_2_check_env | Program | 检查目标环境状态 |
| s2_deploy | s2_1_run_deploy_script | Program | 执行部署脚本 |
| s2_deploy | s2_2_health_check | Program | 健康检查 |
| s3_verify | s3_1_smoke_test | Program | 冒烟测试 |
| s3_verify | s3_2_generate_report | Agent | 生成部署报告 |
| s4_gate | s4_1_deploy_gate | Human | DevOps 确认（仅 production） |

**输出**:
- 部署报告
- 健康检查结果
- 回滚脚本（预生成）

**需创建的文件**:

```
spec-global/departments/devops/workflows/deploy/v1/
├── workflow.yaml
├── agents/
│   └── deploy-report-generator/
│       └── v1/agent.yaml
├── contracts/
│   ├── deploy-config.schema.json
│   ├── health-check-result.schema.json
│   └── deploy-report.schema.json
├── gates/
│   └── deploy-gate/
│       └── v1/gate.yaml
└── skills/
    ├── deploy-script.sh
    ├── health-check.sh
    └── rollback.sh
```

---

### 3.3 交付物清单

| 类别 | 数量 | 说明 |
|------|------|------|
| Workflow | 3 | dev_feature, qa_regression, devops_deploy |
| Agent | 10+ | 各工作流配套的 agents |
| Contract | 9+ | 输入输出 schema |
| Gate | 3 | 各工作流的人工审批 gate |
| Skill | 3+ | 部署相关脚本 |

---

## 4. Phase 2: 统一 CLI 入口

### 4.1 目标

实现 `lee run <dept>.<workflow>` 的简化命令，降低使用门槛。

### 4.2 任务分解

| 任务 ID | 任务名称 | 说明 |
|---------|---------|------|
| 2.1 | 创建 `lee` CLI 入口 | 新建 `src/lee/cli/main.py`，封装 orchestrator |
| 2.2 | 实现工作流注册表 | `config/workflow-registry.yaml` 映射简称到路径 |
| 2.3 | 支持 `--spec` 参数 | 指定项目级 spec 文件 |
| 2.4 | 支持 `--env` 参数 | 指定运行环境 |
| 2.5 | 添加 `lee status` 命令 | 查看当前工作流状态 |
| 2.6 | 添加 `lee approve` 命令 | 快捷审批 gate |

### 4.3 目标命令

```bash
# 运行开发特性工作流
lee run dev.feature --spec spec/dev/feature_plan_page.yaml

# 运行 QA 回归测试
lee run qa.regression --spec spec/qa/release_0_1.yaml

# 运行部署（指定环境和版本）
lee run devops.deploy --env staging --version HEAD

# 查看状态
lee status

# 审批 gate
lee approve <gate_id>
```

### 4.4 工作流注册表格式

```yaml
# config/workflow-registry.yaml
version: "1.0"

workflows:
  dev.feature:
    path: spec-global/departments/dev/workflows/feature/v1/workflow.yaml
    description: "开发特性工作流"
    required_params:
      - spec

  dev.bugfix:
    path: spec-global/departments/dev/workflows/bug-fix/v1/workflow.yaml
    description: "Bug 修复工作流"
    required_params:
      - spec

  qa.regression:
    path: spec-global/departments/qa/workflows/regression/v1/workflow.yaml
    description: "回归测试工作流"
    required_params:
      - spec

  devops.deploy:
    path: spec-global/departments/devops/workflows/deploy/v1/workflow.yaml
    description: "部署工作流"
    required_params:
      - env
      - version
```

### 4.5 交付物清单

| 类别 | 文件 | 说明 |
|------|------|------|
| CLI | `src/lee/cli/main.py` | 入口命令 |
| CLI | `src/lee/cli/commands/run.py` | run 子命令 |
| CLI | `src/lee/cli/commands/status.py` | status 子命令 |
| CLI | `src/lee/cli/commands/approve.py` | approve 子命令 |
| Config | `config/workflow-registry.yaml` | 工作流注册表 |
| Entry | `pyproject.toml` 更新 | 添加 `lee` 入口点 |

---

## 5. Phase 3: 资产层规范化

### 5.1 目标

在项目级建立 `/spec/` `/evidence/` `/env/` 目录规范，明确资产组织方式。

### 5.2 目录结构设计

```
/project-root/
├── spec/                           # 项目级 Spec（约束与意图）
│   ├── dev/                        # Dev 部门 Spec
│   │   ├── feature_xxx.yaml        # Feature Spec
│   │   └── bugfix_xxx.yaml         # Bug Fix Spec
│   ├── qa/                         # QA 部门 Spec
│   │   ├── release_0_1.yaml        # 测试计划
│   │   └── testcase_xxx.yaml       # 测试用例
│   └── devops/                     # DevOps 部门 Spec
│       ├── staging.yaml            # Staging 部署策略
│       └── production.yaml         # Production 部署策略
│
├── evidence/                       # 证据（执行产物）
│   ├── RUN-20260207-001/           # 按 run_id 组织
│   │   ├── manifest.yaml           # 执行清单
│   │   ├── test_report.json        # 测试报告
│   │   ├── git_diff.patch          # 代码变更
│   │   ├── deploy_log.txt          # 部署日志
│   │   └── screenshots/            # 截图
│   └── RUN-20260207-002/
│       └── ...
│
├── env/                            # 环境配置
│   ├── .devcontainer/              # 开发容器配置
│   ├── secrets.template.yaml       # Secrets 模板
│   ├── staging.env.template        # Staging 环境变量模板
│   └── production.env.template     # Production 环境变量模板
│
└── .workflow/                      # 运行时状态（保持现有）
    ├── orchestrator.db
    ├── state.yaml
    └── ...
```

### 5.3 任务分解

| 任务 ID | 任务名称 | 说明 |
|---------|---------|------|
| 3.1 | 编写目录规范文档 | `docs/Asset-Layer-Specification.md` |
| 3.2 | 创建项目级 spec 模板 | `templates/spec/` 目录 |
| 3.3 | 实现 Evidence 收集机制 | 修改 Orchestrator，step 完成后自动归档 |
| 3.4 | 创建 env 配置模板 | `templates/env/` 目录 |
| 3.5 | 添加 `lee init` 命令 | 初始化项目目录结构 |

### 5.4 Evidence 收集机制

```python
# 伪代码
class EvidenceCollector:
    def collect(self, run_id: str, step_id: str, outputs: List[str]):
        evidence_dir = f"evidence/{run_id}"
        os.makedirs(evidence_dir, exist_ok=True)

        for output in outputs:
            # 复制产物到 evidence 目录
            shutil.copy(output, evidence_dir)

        # 生成 manifest
        manifest = {
            "run_id": run_id,
            "step_id": step_id,
            "collected_at": datetime.now().isoformat(),
            "artifacts": outputs
        }
        with open(f"{evidence_dir}/manifest.yaml", "a") as f:
            yaml.dump(manifest, f)
```

### 5.5 交付物清单

| 类别 | 文件 | 说明 |
|------|------|------|
| 文档 | `docs/Asset-Layer-Specification.md` | 资产层规范 |
| 模板 | `templates/spec/dev/feature.yaml.template` | Feature Spec 模板 |
| 模板 | `templates/spec/qa/testplan.yaml.template` | 测试计划模板 |
| 模板 | `templates/env/devcontainer.json` | 开发容器模板 |
| 代码 | `src/lee/orchestrator/evidence_collector.py` | Evidence 收集器 |
| CLI | `src/lee/cli/commands/init.py` | init 命令 |

---

## 6. Phase 4: Verifier 系统

### 6.1 目标

实现硬性规则自动检查，违规直接中断（不进入 Human Gate）。

### 6.2 Verifier vs Validator 区别

| 维度 | Validator | Verifier |
|------|-----------|----------|
| 触发时机 | step 完成后 | step 完成后，Gate 之前 |
| 失败处理 | 进入 Gate 让人决定 | 直接 fail，不进 Gate |
| 用途 | 质量建议 | 硬性规则 |
| 示例 | 代码风格建议 | lint 必须通过、覆盖率 > 80% |

### 6.3 任务分解

| 任务 ID | 任务名称 | 说明 |
|---------|---------|------|
| 4.1 | 定义 Verifier 接口 | `src/lee/orchestrator/verifiers/base.py` |
| 4.2 | 实现 LintVerifier | 运行 ruff/eslint 检查 |
| 4.3 | 实现 CoverageVerifier | 检查测试覆盖率 |
| 4.4 | 实现 CommitFormatVerifier | 检查 commit message 格式 |
| 4.5 | 集成到 Orchestrator | step 完成后先过 Verifier |
| 4.6 | 更新 workflow schema | 支持 verifiers 字段 |

### 6.4 Verifier 接口设计

```python
# src/lee/orchestrator/verifiers/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

class VerifyStatus(Enum):
    PASSED = "passed"
    FAILED = "failed"

@dataclass
class VerifyResult:
    status: VerifyStatus
    verifier_id: str
    message: str
    details: dict = None

class BaseVerifier(ABC):
    @abstractmethod
    def verify(self, context: dict) -> VerifyResult:
        """执行验证，返回结果"""
        pass

    @property
    @abstractmethod
    def verifier_id(self) -> str:
        """Verifier 唯一标识"""
        pass
```

### 6.5 内置 Verifier

```yaml
# workflow.yaml 中的使用方式
steps:
  - id: s2_3_unit_test
    run: skill.test.pytest
    verifiers:
      - type: lint
        config:
          command: "ruff check ."
          fail_on_error: true

      - type: coverage
        config:
          min_coverage: 80
          fail_on_error: true

      - type: commit_format
        config:
          pattern: "^(feat|fix|docs|refactor|test|chore)\\(.*\\):.*"
```

### 6.6 执行流程

```
Step 完成
    ↓
运行 Verifiers (按顺序)
    ↓
┌─ 全部通过 ──→ 进入 Gate (如有) ──→ 等待审批
│
└─ 任一失败 ──→ Step 状态 = FAILED ──→ 工作流中断
```

### 6.7 交付物清单

| 类别 | 文件 | 说明 |
|------|------|------|
| 代码 | `src/lee/orchestrator/verifiers/base.py` | Verifier 基类 |
| 代码 | `src/lee/orchestrator/verifiers/lint.py` | Lint Verifier |
| 代码 | `src/lee/orchestrator/verifiers/coverage.py` | Coverage Verifier |
| 代码 | `src/lee/orchestrator/verifiers/commit_format.py` | Commit Format Verifier |
| 代码 | `src/lee/orchestrator/verifier_engine.py` | Verifier 执行引擎 |
| Schema | 更新 workflow schema | 支持 verifiers 字段 |

---

## 7. Phase 5: 跨部门串联（下一版本）

### 7.1 目标

实现 Dev → QA → DevOps 一键 pipeline。

### 7.2 设计思路

```yaml
# spec/pipelines/release.yaml
kind: pipeline
id: pipeline.release
version: "1.0"

stages:
  - id: dev
    workflow: dev.feature
    on_success: qa
    on_failure: stop

  - id: qa
    workflow: qa.regression
    on_success: devops
    on_failure: stop

  - id: devops
    workflow: devops.deploy
    config:
      env: staging
```

### 7.3 任务分解（预规划）

| 任务 ID | 任务名称 | 说明 |
|---------|---------|------|
| 5.1 | 定义 Pipeline Spec 格式 | 串联多个 workflow |
| 5.2 | 实现自动触发机制 | Gate 通过后触发下一 workflow |
| 5.3 | 添加 `lee run pipeline.xxx` | Pipeline 运行命令 |
| 5.4 | 实现跨 workflow 上下文传递 | 输出 → 输入 映射 |

---

## 8. 风险与缓解措施

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| Workflow 设计过于复杂 | 难以落地 | 从最小可用版开始，逐步迭代 |
| Agent 生成质量不稳定 | 需要频繁人工干预 | 增加 Verifier，明确验收标准 |
| 跨部门协作困难 | 流程割裂 | Phase 5 实现串联机制 |
| CLI 与现有 orchestrator 冲突 | 维护成本增加 | lee CLI 封装 orchestrator，不重复实现 |

---

## 9. 成功标准

### Phase 1 成功标准
- [ ] `dev_feature_l3` 能完整跑通一个简单 feature 开发流程
- [ ] `qa_regression_l3` 能执行测试并生成 Bug 草稿
- [ ] `devops_deploy_l3` 能部署到 staging 环境

### Phase 2 成功标准
- [ ] `lee run dev.feature --spec xxx` 命令可用
- [ ] `lee status` 能查看当前状态
- [ ] `lee approve` 能审批 gate

### Phase 3 成功标准
- [ ] 项目目录结构符合规范
- [ ] Evidence 自动收集到 `/evidence/` 目录
- [ ] `lee init` 能初始化项目

### Phase 4 成功标准
- [ ] Lint 失败时 step 直接中断
- [ ] Coverage 不达标时 step 直接中断
- [ ] Verifier 结果记录在 evidence 中

---

## 10. 审批确认

请审批以下事项：

- [ ] **Phase 1**: 同意创建 3 个核心 L3 工作流
- [ ] **Phase 2**: 同意创建 `lee` CLI 入口
- [ ] **Phase 3**: 同意资产层目录规范
- [ ] **Phase 4**: 同意 Verifier 系统设计
- [ ] **Phase 5**: 同意跨部门串联作为下一版本目标

**审批人**: ________________

**审批日期**: ________________

**审批意见**:

```
[ ] 全部同意，按计划执行
[ ] 部分同意，需要调整（请注明）
[ ] 需要进一步讨论
```

---

## 附录 A: 目录结构对比

### 目标架构

```
/project/
├── spec/
│   ├── dev/
│   ├── qa/
│   └── devops/
├── evidence/
├── env/
└── src/
```

### 当前架构

```
/lee/
├── spec-global/          # 框架级模板
│   └── departments/
├── src/lee/
│   ├── orchestrator/
│   └── runtime/
└── .workflow/            # 运行时状态
```

### 融合方案

```
/lee/                           # LEE 框架
├── spec-global/                # 框架级模板（不变）
├── src/lee/                    # 框架代码（不变）
├── config/                     # 框架配置
│   └── workflow-registry.yaml
└── templates/                  # 项目模板
    ├── spec/
    ├── env/
    └── evidence/

/project/                       # 使用 LEE 的项目
├── spec/                       # 项目级 Spec
├── evidence/                   # 项目级证据
├── env/                        # 项目级环境配置
├── src/                        # 项目代码
└── .workflow/                  # LEE 运行时状态
```

---

## 附录 B: 工作流模板示例

### dev_feature_l3 workflow.yaml 骨架

```yaml
kind: workflow
id: workflow.dev.feature_l3
version: "1.0"
name: "Feature Development L3"
description: "从 Feature Spec 到代码实现的完整开发流程"

entry_gate:
  ref: gate.dev.feature_entry
  description: "确认 Feature Spec 完整"

stages:
  - id: s1_prepare
    name: "准备阶段"
    steps:
      - id: s1_1_pull_branch
        name: "拉取分支"
        type: skill
        run: skill.git.checkout
        inputs:
          - branch: "{{params.branch}}"
        outputs:
          - path: "output/git-status.txt"

      - id: s1_2_parse_spec
        name: "解析 Feature Spec"
        type: agent
        run: agent.dev.feature_spec_parser
        dependencies: [s1_1_pull_branch]
        inputs:
          - spec: "{{params.spec}}"
        outputs:
          - path: "output/parsed-spec.yaml"

  - id: s2_coding
    name: "编码阶段"
    steps:
      - id: s2_1_generate_code
        name: "生成代码"
        type: agent
        run: agent.dev.feature_coder
        dependencies: [s1_2_parse_spec]
        inputs:
          - parsed_spec: "output/parsed-spec.yaml"
        outputs:
          - path: "output/code-diff.patch"

      - id: s2_2_static_check
        name: "静态检查"
        type: skill
        run: skill.lint.ruff
        dependencies: [s2_1_generate_code]
        verifiers:
          - type: lint
            config:
              command: "ruff check ."
              fail_on_error: true

      - id: s2_3_unit_test
        name: "单元测试"
        type: skill
        run: skill.test.pytest
        dependencies: [s2_2_static_check]
        verifiers:
          - type: coverage
            config:
              min_coverage: 80

  - id: s3_review
    name: "审查阶段"
    steps:
      - id: s3_1_self_review
        name: "AI 自审"
        type: agent
        run: agent.dev.code_self_reviewer
        dependencies: [s2_3_unit_test]
        outputs:
          - path: "output/review-report.md"

      - id: s3_2_generate_summary
        name: "生成变更说明"
        type: agent
        run: agent.dev.change_summarizer
        dependencies: [s3_1_self_review]
        outputs:
          - path: "output/change-summary.md"

  - id: s4_gate
    name: "审批阶段"
    steps:
      - id: s4_1_dev_gate
        name: "Dev Lead 审批"
        type: gate_decision
        dependencies: [s3_2_generate_summary]
        gate:
          ref: gate.dev.feature_gate
          context:
            requires:
              - "output/code-diff.patch"
              - "output/review-report.md"
              - "output/change-summary.md"

outputs:
  - id: code_changes
    source: "output/code-diff.patch"
  - id: change_summary
    source: "output/change-summary.md"
  - id: test_report
    source: "output/test-report.json"
```

---

**文档结束**
