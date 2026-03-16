# LEE Framework 工作流汇总

> **版本**: 1.0
> **更新日期**: 2026-01-29
> **状态**: ✅ 反映所有部门的工作流

---

## 概述

LEE Framework 包含多个层级的工作流，覆盖从产品决策到部署验收的完整软件开发生命周期。

### 工作流层级

| 层级 | 说明 | 数量 | 目录 |
|------|------|------|------|
| **L1** | 项目级/产品级主流程 | 2 | `cross/workflows/project/` |
| **L2** | 部门级专业流程 | 6 | `departments/{dept}/workflows/` |
| **L3** | 任务级子流程 | 2 | `departments/{dept}/workflows/` 或 `cross/workflows/task/` |

---

## L1 工作流（项目级）

### 1. Product Pipeline（产品决策流水线）

**ID**: `workflow.cross.product_pipeline`
**路径**: `cross/workflows/project/product-pipeline/v1/workflow.yaml`
**部门**: 跨部门（PRD 主导）

**阶段**: 4 个
- `value_definition` - 价值定义
- `problem_definition` - 问题定义
- `solution_design` - 方案设计
- `delivery_planning` - 交付规划

**Human Gates**: 4 个

**用途**: Stage 2 产品设计阶段的完整决策流程

---

### 2. Product MVP（产品最小可行产品）

**ID**: `workflow.cross.product_mvp`
**路径**: `cross/workflows/project/product-mvp/v1/workflow.yaml`
**部门**: 跨部门

**用途**: L1 产品级 MVP 创建流程

---

## L2 工作流（部门级）

### Dev 部门

#### 1. Feature Delivery L2（研发主流程）

**ID**: `template.dev.feature_delivery_l2`
**路径**: `departments/dev/workflows/templates/feature-delivery-l2-template.yaml`
**版本**: 3.0

**阶段**: 7 个
- `tech_design`
- `contract_design`
- `backend_dev`
- `frontend_dev`
- `integration`
- `evidence_pack`
- `smoke_gate`

**Gates**: `gate.dev.contract_freeze_gate`, `gate.dev.smoke_gate`

**用途**: Dev 部门当前 canonical Feature 主入口

**备注**: checked-in 文件为 template，运行时 instance 动态生成。

---

#### 2. Bugfix Delivery L2（缺陷修复主流程）

**ID**: `template.dev.bugfix_delivery_l2`
**路径**: `departments/dev/workflows/templates/bugfix-delivery-l2-template.yaml`
**版本**: 3.0

**阶段**: 7 个
- `triage`
- `root_cause`
- `fix_design`
- `fix_implementation`
- `verification`
- `evidence_pack`
- `merge_or_reject`

**用途**: Dev 部门当前 canonical Bugfix 主入口

**备注**: checked-in 文件为 template，运行时 instance 动态生成。

---

### QA 部门

#### 2. Testing Pipeline（测试流水线）

**ID**: `workflow.qa.testing_pipeline`
**路径**: `departments/qa/workflows/templates/test-plan-l2-template.yaml`

**用途**: QA 部门的测试流程模板

**备注**: checked-in 文件为 template，运行时 instance 动态生成。

---

#### 3. Test Main Pipeline（主测试流程）

**ID**: `workflow.qa.test_main_pipeline`
**路径**: `departments/qa/workflows/templates/test-plan-l2-template.yaml`
**版本**: 2.0

**用途**: QA 部门的主测试流程（legacy alias）

**状态**: Deprecated compatibility alias

---

### UI 部门

#### 4. UI Design Pipeline（UI 设计流水线）

**ID**: `workflow.ui.ui_design_pipeline`
**路径**: `departments/ui/workflows/ui-design-pipeline/v1/workflow.yaml`

**用途**: UI/UX 设计流程

---

### Product 部门

#### 5. Product Main Pipeline（产品主编排流程）

**ID**: `workflow.product.product_main_pipeline`
**路径**: `departments/product/workflows/templates/product-main-pipeline/v1/workflow.yaml`

**用途**: Product 部门新的 SSOT 主编排流程，串联 `SRC -> EPIC -> FEAT -> Delivery Prep -> Requirement Chain Validation`

---

#### 6. SRC to EPIC（源需求到 EPIC）

**ID**: `workflow.product.task.src_to_epic`
**路径**: `departments/product/workflows/templates/src-to-epic/v1/workflow.yaml`

**用途**: 将市场机会/原始需求收敛为 EPIC 并进行人类冻结

---

#### 7. EPIC to FEAT（EPIC 到 FEAT）

**ID**: `workflow.product.task.epic_to_feat`
**路径**: `departments/product/workflows/templates/epic-to-feat/v1/workflow.yaml`

**用途**: 将冻结后的 EPIC 拆解为可独立验收的 FEAT 并进行人类冻结

---

#### 8. FEAT to Delivery Prep（FEAT 到研发准备）

**ID**: `workflow.product.task.feat_to_delivery_prep`
**路径**: `departments/product/workflows/templates/feat-to-delivery-prep/v1/workflow.yaml`

**用途**: 基于冻结后的 FEAT 生成 UI / TECH / TASK 准备包

#### 9. Requirement Chain Validation（需求链一致性验证）

**ID**: `workflow.product.task.requirement_chain_validation`
**路径**: `departments/product/workflows/templates/requirement-chain-validation/v1/workflow.yaml`

**用途**: 在最终 handoff 前运行 requirement chain test，验证正式 SSOT 主链质量

---

#### Deprecated: PRD Workflows

- `workflow.prd.product_pipeline`
- `workflow.prd.product_to_dev_pipeline`

以上旧流程保留兼容窗口，但不再作为推荐入口。

---

### STG 部门

#### 10. Opportunity Discovery（商业机会发现）

**ID**: `workflow.stg.opportunity_discovery`
**路径**: `departments/stg/workflows/opportunity_discovery/v1/workflow.yaml`
**版本**: 1.1

**阶段**: 7 个
- Step 1: 市场信号采集
- Step 2: 信号验证
- Step 3: 商业洞察
- Step 4: 假设生成
- Step 5: 机会构建
- Step 6: 机会验证
- Step 7: 商业机会冻结（Human Gate）

**Human Gates**: 1 个（机会冻结）

**用途**: 商业机会从发现到冻结的完整流程

**v1.1 更新**: 从 handoff 模型改为 freeze 模型，增加机会冻结审批

---

### DevOps 部门（新增）

#### 11. DevOps Deployment（DevOps 部署工作流）

**ID**: `workflow.devops.deployment`
**路径**: `departments/devops/workflows/devops-deployment/v1/workflow.yaml`
**版本**: 1.1

**阶段**: 6 个
- `p1_architecture`: 环境与发布架构设计
- `p2_infra_code`: 基础设施与 CI/CD 实现
- `p3_env_config`: 人类注入环境配置与凭证
- `p4_deploy_dev_test`: 部署到 dev/test
- `p5_verification`: 环境与发布包验收
- `p6_release_freeze`: 版本冻结

**Human Gates**: 3 个（配置注入、验收、冻结）

**核心特性**:
- **Verifier System**: Phase 1 和 Phase 2 自动验证
- **三 Agent 模型**: Architect → Implementation → Verification
- **安全边界**: AI 生成模板，人类注入凭证

**用途**: 从架构设计到部署验收的完整 DevOps 流程

**v1.1 更新**: 集成 Verifier System，增加自动验证机制

---

## L3 工作流（任务级）

### Dev 部门

#### 0. Feature Contract Design L3（契约设计子流程）

**ID**: `template.dev.feature_contract_l3`
**路径**: `departments/dev/workflows/templates/feature-contract-l3-template.yaml`
**版本**: 2.0

**步骤**: 5 个
- `api_contract_design`
- `data_contract_design`
- `event_contract_design`
- `contract_self_review`
- `contract_freeze`

**Gate**: `gate.dev.contract_freeze_gate`

**用途**: Dev 部门 `contract_design` 阶段的唯一现役 L3，实现 TECH 到冻结契约的结构收口。

**备注**: Backend / Frontend 下游只允许消费 `contract_freeze_ref`。

---

#### 0.1. Feature Backend Development L3（后端开发子流程）

**ID**: `template.dev.feature_be_l3`
**路径**: `departments/dev/workflows/templates/feature-be-l3-template.yaml`
**版本**: 2.0

**步骤**: 5 个
- `write_ut`
- `implement_backend`
- `refactor_backend`
- `coverage_gate`
- `publish_backend`

**用途**: Dev 部门 `backend_dev` 阶段的唯一现役 L3，实现后端 UTDD、覆盖率门禁和 handoff 发布。

**状态**: Canonical

**备注**: 旧的 DTO/Handler 分段叙事不再作为推荐入口。

---

#### 0.2. Feature Frontend Development L3（前端开发子流程）

**ID**: `template.dev.feature_fe_l3`
**路径**: `departments/dev/workflows/templates/feature-fe-l3-template.yaml`
**版本**: 2.0

**步骤**: 5 个
- `write_ut`
- `implement_ui`
- `refactor_ui`
- `coverage_gate`
- `publish_frontend`

**用途**: Dev 部门 `frontend_dev` 阶段的唯一现役 L3，实现前端 UTDD、覆盖率门禁和 Evidence handoff。

**状态**: Canonical

**备注**: 旧的 Type Generation / UI Implementation / Self-Check 叙事不再作为推荐入口。

---

#### 1. Phase OpenSpec Flow（Phase 内 OpenSpec 子流程）

**ID**: `workflow.dev.phase_openspec_flow`
**路径**: `departments/dev/workflows/phase-openspec-flow/v1/workflow.yaml`
**版本**: 1.7

**步骤**: 13 个
- `p1`: OpenSpec 初始化
- `p2`: 需求校准
- `p3`: 测试契约生成
- `p4`: OpenSpec 变更提案
- `p5`: 代码实现
- `p6`: 单元测试
- `p7`: Code Review（条件门禁）
- `p8`: Phase 复盘
- `p9`: 知识沉淀
- `p10`: OpenSpec 归档
- `p11`: Phase 验收（强制门禁）
- `p12`: 知识合并
- `p13`: Phase 交接

**Human Gates**: 3 个

**用途**: 历史参考流程

**状态**: Deprecated，不再作为 Dev 部门新任务入口

**迁移**: 参见 `departments/dev/docs/deprecated-path-migration-guide.md`

---

#### 2. Bugfix Delivery（代码修复流程）

**ID**: `template.dev.bug_fix_l3`
**路径**: `departments/dev/workflows/templates/bug-fix-l3-template.yaml`

**用途**: 当前保留的缺陷修复模板

**状态**: Deprecated，新的缺陷修复任务统一收口到 `template.dev.bugfix_delivery_l2`

**迁移**: 参见 `departments/dev/docs/deprecated-path-migration-guide.md`

---

## 工作流关系图

```
┌─────────────────────────────────────────────────────────────────┐
│                        L1 - Project 级                          │
│                                                                  │
│  Product Pipeline ─────┐                                         │
│  Product MVP ───────────┤                                         │
│                        └──→ 调用 L2 工作流                          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                        L2 - Department 级                       │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  Dev:        │  │  QA:         │  │  DevOps:     │          │
│  │  Development │  │  Testing     │  │  Deployment  │          │
│  │  Pipeline    │  │  Pipeline    │  │              │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                 │                 │                     │
│         └────────────────┴─────────────────┘                     │
│                          ↓                                       │
│                  调用 L3 工作流                                  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                        L3 - Task 级                             │
│                                                                  │
│  Phase OpenSpec Flow ──→ 最小执行单元                           │
│  Dev Retest ────────────→ 代码修复                               │
└─────────────────────────────────────────────────────────────────┘
```

---

## Verifier System 集成

**DevOps Deployment Workflow** 是首个集成 **Verifier System** 的工作流。

### 验证流程

```
Agent 生成产物
    ↓
Verifier 检查产物
    ├─ 程序型检查: 文件、格式、结构
    └─ AI 型检查: 语义、质量、合理性
    ↓
    ↓
通过? → 进入下一阶段
    ↓
失败? → 重试 / 人工审查 / 中止
```

### 验证契约

| 契约 ID | 描述 | 检查项 |
|---------|------|--------|
| `devops.phase1.architecture.v1` | Phase 1 架构设计验证 | 7 项（4 error, 3 warning） |
| `devops.phase2.cicd.v1` | Phase 2 CI/CD 实现验证 | 8 项（5 error, 3 warning） |

---

## Human Gates 汇总

### 按部门统计

| 部门 | Human Gates 数量 | 主要审批点 |
|------|------------------|-----------|
| **Dev** | 4 | 项目初始化、计划审批、集成审查、验收 |
| **QA** | 4 | E2E、退出冒烟、提交 |
| **STG** | 1 | 商业机会冻结 |
| **DevOps** | 3 | 配置注入、验收、版本冻结 |
| **PRD** | - | - |
| **UI** | - | - |
| **Office** | 1 | Phase 验收 |

### Gate 类型

| 类型 | 说明 | 数量 |
|------|------|------|
| **Approval** | 需要审批才能继续 | 大多数 |
| **Review** | 审查但不一定阻断 | 部分 |
| **Decision** | 决策类 Gate | 少数 |

---

## 快速参考

### 运行工作流

```bash
# 运行 L2 工作流
python -m flowcore.cli.main run spec-global/departments/dev/workflows/development-pipeline/v1/workflow.yaml

# 运行 DevOps 工作流
python -m flowcore.cli.main run spec-global/departments/devops/workflows/devops-deployment/v1/workflow.yaml

# 运行 L3 工作流
python -m flowcore.cli.main run spec-global/departments/dev/workflows/phase-openspec-flow/v1/workflow.yaml
```

### 审批 Gate

```bash
# 审批指定 Gate
python -m flowcore.cli.main approve <gate_id> --approver "张三" --comments "通过"

# 查看待审批 Gates
python -m flowcore.cli.main list-gates
```

### 查看工作流状态

```bash
# 查看所有工作流
python -m flowcore.cli.main list-workflows

# 查看工作流详情
python -m flowcore.cli.main show <workflow_id>
```

---

## 元数据注册

所有工作流在 `spec-global/_metadata.yaml` 中注册，包含：

- **workflow_registry**: 工作流注册表
- **agent_registry**: Agent 注册表
- **gate_registry**: Gate 注册表
- **contract_registry**: 契约注册表

详见 [元数据文件](../_metadata.yaml)。

---

## 相关文档

- [Spec-Global README](README.md)
- [DevOps 部门文档](departments/devops/README.md)
- [Verifier System 快速开始](departments/devops/docs/verifier-quickstart.md)
- [Verifier System 集成指南](departments/devops/docs/verifier-system-integration.md)

---

**维护者**: LEE Team
**最后更新**: 2026-01-29
