# DevOps 部门

> **LEE Orchestrator v3.1 - DevOps 部门规范**
>
> 文档版本: 1.0
> 创建日期: 2026-01-29
> 状态: ✅ 已完成

---

## 📋 目录

- [一、部门概述](#一部门概述)
- [二、核心职责](#二核心职责)
- [三、组织结构](#三组织结构)
- [四、工作流程](#四工作流程)
- [五、文件清单](#五文件清单)
- [六、快速开始](#六快速开始)

---

## 一、部门概述

### 1.1 部门定位

DevOps 部门在 LEE 体系中负责**基础设施与运维自动化**。

**核心定位**：
- AI 只负责生成方案和代码
- 真实凭证由人类注入
- 生产环境必须经过 Human Gate 审批
- 每个变更都有回滚方案

### 1.2 设计原则

| 原则 | 说明 |
|------|------|
| **AI 不生成密钥** | AI 只输出占位符，真实凭证由人类注入 |
| **生产需人工审批** | staging 和 prod 环境需要 Human Gate 审批 |
| **完整审计跟踪** | 所有操作必须记录审计日志 |
| **强制回滚方案** | 每个部署必须有对应的回滚方案 |

### 1.3 一句话原则

> **DevOps Agent 只写「代码 + 配置模板 + 执行计划」，
> 真实凭证永远由人类注入。**

---

## 二、核心职责

### 2.1 AI 可以做什么

✅ **环境基础设施声明式搭建**
- dev / test / staging / prod
- docker-compose / k8s / terraform

✅ **应用部署与发布**
- 编写部署脚本
- 生成 CI/CD pipeline
- 版本冻结包生成

✅ **基础设施代码化**
- IaC（Terraform / Helm / Compose）
- 配置模板
- 部署和回滚脚本

✅ **可追溯执行**
- 审计日志记录
- 变更历史追踪
- 发布清单生成

### 2.2 AI 明确不做

❌ **不创建账号**
❌ **不生成 token / 密钥**
❌ **不修改生产配置**
❌ **不做业务级数据操作**
❌ **不绕过 human gate**

---

## 三、组织结构

### 3.1 三大 Agent

#### 1️⃣ devops-architect-agent（架构与方案）

**职责**：
- 环境拓扑设计
- 技术选型（k8s / docker-compose / cloud service）
- 发布策略设计（蓝绿 / 滚动 / canary）
- 数据库 / 中间件架构声明

**输出**：
- `infra-architecture.yaml` - 基础设施架构设计
- `env-matrix.yaml` - 环境配置矩阵
- `release-strategy.md` - 发布策略文档

#### 2️⃣ devops-implementation-agent（代码执行者）

**职责**：
- 编写 IaC（Terraform / Helm / Compose）
- 编写 CI/CD pipeline
- 编写 deploy / rollback 脚本
- 生成 release bundle

**输出**：
- `infra/` - IaC 代码目录
- `cicd/` - CI/CD 配置目录
- `deploy/` - 部署脚本目录
- `scripts/` - 辅助脚本目录
- `release/` - 发布包目录

#### 3️⃣ devops-verification-agent（校验与冻结）

**职责**：
- 校验环境完整性
- 校验 release 包
- 生成可审计报告
- 冻结版本

**输出**：
- `deployment-checklist.md` - 部署验收清单
- `release-manifest.yaml` - 发布清单
- `freeze-report.md` - 冻结报告
- `audit-trail.yaml` - 审计跟踪记录

### 3.2 部门目录结构

```
spec-global/departments/devops/
├── contracts/
│   └── devops-execution.contract.yaml     # 执行契约（权限边界）
├── agents/
│   ├── devops-architect.agent.yaml         # 架构师 Agent
│   ├── devops-implementation.agent.yaml    # 实施工程师 Agent
│   └── devops-verification.agent.yaml      # 验收工程师 Agent
├── workflows/
│   └── devops-deployment/
│       └── v1/
│           └── workflow.yaml               # 部署工作流（L2）
├── checklists/
│   ├── devops-human-gate.checklist.yaml    # 人工门控检查清单
│   └── devops-release-freeze.checklist.yaml # 发布冻结检查清单
├── templates/
│   ├── env-config.template.yaml          # 环境配置模板
│   ├── release-version.template.yaml       # 发布版本模板
│   ├── deploy-plan.template.md            # 部署计划模板
│   └── rollback-plan.template.md          # 回滚计划模板
└── README.md                                # 本文档
```

---

## 四、工作流程

### 4.1 L2 工作流：DevOps 部署

**ID**: `workflow.devops.deployment`
**路径**: `departments/devops/workflows/devops-deployment/v1/workflow.yaml`
**Level**: `department` (L2)
**Owner**: `devops`

#### 6 个阶段

```
Phase 1: p1_architecture (架构设计)
├── Agent: devops-architect-agent
├── 输出: infra-architecture.yaml, env-matrix.yaml, release-strategy.md
└── Human Gate: devops_lead + tech_lead

Phase 2: p2_infra_code (实施代码生成)
├── Agent: devops-implementation-agent
└── 输出: infra/, cicd/, deploy/, scripts/, release/

Phase 3: p3_env_config (配置注入)
├── 人类填写真实配置
├── 输入: env-config.dev.yaml, env-config.test.yaml, ...
└── Human Gate: devops_lead

Phase 4: p4_deploy_dev_test (部署到 dev/test)
├── Runner: shell
├── 执行: ./deploy/deploy-dev-test.sh dev/test
└── 无需 Human Gate

Phase 5: p5_verification (环境验收)
├── Agent: devops-verification-agent
├── 输出: deployment-checklist.md, release-manifest.yaml
└── Human Gate: devops_lead + qa_lead

Phase 6: p6_release_freeze (版本冻结)
├── Agent: devops-verification-agent
├── 输出: freeze-report.md, audit-trail.yaml
└── Human Gate: devops_lead + tech_lead + product_owner
```

#### 时间估算

| 阶段 | 预计时间 |
|------|----------|
| p1_architecture | 1 小时 |
| p2_infra_code | 2 小时 |
| p3_env_config | 24 小时（人类填写） |
| p4_deploy_dev_test | 20 分钟 |
| p5_verification | 30 分钟 |
| p6_release_freeze | 1 小时 |
| **总计** | **~1.5 个工作日** |

### 4.2 与 L1 的关系

DevOps 部门的 L2 工作流可以被 L1 产品 MVP 工作流调用：

```
L1: Product MVP Workflow
  ├─ Step 4: Dev (研发实现)
  │   └─ spawn L2: workflow.dev.development_pipeline
  │       └─ spawn L2: workflow.devops.deployment
  │
  └─ Step 6: Release (发布批准)
      └─ L1 Human Gate 最终批准
```

---

## 五、文件清单

### 5.1 Contract（契约）

| 文件 | 说明 |
|------|------|
| `devops-execution.contract.yaml` | DevOps 执行契约，定义 AI 权限边界 |

### 5.2 Agents（代理）

| 文件 | 角色 | 能力 |
|------|------|------|
| `devops-architect.agent.yaml` | 架构师 | 环境拓扑设计、发布策略设计 |
| `devops-implementation.agent.yaml` | 实施工程师 | IaC 代码生成、CI/CD 定义 |
| `devops-verification.agent.yaml` | 验收工程师 | 部署验证、版本冻结 |

### 5.3 Workflows（工作流）

| 文件 | 层级 | 说明 |
|------|------|------|
| `workflow.devops.deployment` | L2 | DevOps 部署主流程（6 个阶段） |

### 5.4 Checklists（检查清单）

| 文件 | 适用场景 |
|------|----------|
| `devops-human-gate.checklist.yaml` | 所有 Human Gate 审批点 |
| `devops-release-freeze.checklist.yaml` | 版本冻结最终审批 |

### 5.5 Templates（模板）

| 文件 | 用途 |
|------|------|
| `env-config.template.yaml` | 生成各环境配置文件 |
| `release-version.template.yaml` | 生成发布版本信息 |
| `deploy-plan.template.md` | 生成部署计划 |
| `rollback-plan.template.md` | 生成回滚计划 |

---

## 六、快速开始

### 6.1 使用 DevOps 工作流

```bash
# 1. 初始化 DevOps 基础设施方案
lee run devops init --project <project_name>

# 2. 人类填写配置
# 编辑 devops/env/env-config.dev.yaml
# 编辑 devops/env/env-config.test.yaml

# 3. 部署到 dev/test
lee run devops deploy --project <project_name> --env dev
lee run devops deploy --project <project_name> --env test

# 4. 冻结版本
lee run devops freeze --project <project_name> --version 1.0.0
```

### 6.2 项目内使用

在每个项目下创建 `devops/` 目录：

```
project/<project_name>/
└── devops/
    ├── env/               # 环境配置（人类填写）
    ├── infra/             # IaC 代码（AI 生成）
    ├── cicd/              # CI/CD 配置（AI 生成）
    ├── deploy/            # 部署脚本（AI 生成）
    ├── scripts/           # 辅助脚本（AI 生成）
    ├── release/           # 发布包
    ├── logs/              # 部署日志
    └── spec-link/         # 指向 spec-global/devops（软链接）
```

---

## 七、安全与合规

### 7.1 权限边界

- ✅ AI 可以生成代码和配置模板
- ✅ AI 可以生成占位符（`${PLACEHOLDER}`）
- ❌ AI 不能生成真实密钥或凭证
- ❌ AI 不能直接修改生产环境配置

### 7.2 审计要求

所有部署操作必须记录：
- 操作时间戳
- 操作者（人类或 Agent）
- 目标环境
- 执行的命令
- 操作结果

### 7.3 回滚策略

每个部署必须有对应的回滚方案：
- 回滚脚本已准备
- 回滚步骤已文档化
- 回滚时间已估算
- 数据备份已确认

---

## 八、跨部门协作

### 8.1 协作关系

| 协作部门 | 接口契约 | 说明 |
|----------|----------|------|
| Dev | 开发完成交付包 | Dev → DevOps 部署流水线 |
| QA | 部署后验证 | DevOps → QA 验收确认 |
| Product | 发布审批 | DevOps → Product 最终批准 |

### 8.2 交接产物

| 产物 | 来源 | 消费者 |
|------|------|--------|
| `test_submission_freeze_package.yaml` | Dev | DevOps |
| `deliverable_release.yaml` | QA | DevOps |
| `product_mvp_release.yaml` | L1 Gate | Production |

---

## 九、旧版文件（已废弃）

以下文件为旧版本，已被新版替代：

- `workflows/deployment.yaml` → 被 `workflows/devops-deployment/v1/workflow.yaml` 替代
- `agents/devops-engineer.yaml` → 被三大新 Agent 替代
- `agents/sre.yaml` → 职责合并到新 Agent 中

---

## 十、实战示例与文档

### 10.1 示例文件

我们提供了完整的实战示例，可以直接使用：

**Docker Compose 示例** (`examples/docker-compose.yml`)
- 包含应用、数据库、Redis、Nginx
- 支持健康检查和依赖管理
- 环境变量占位符模式

**环境配置示例** (`examples/env-config.*.yaml`)
- `env-config.dev.yaml` - 开发环境配置
- `env-config.test.yaml` - 测试环境配置
- 包含所有必需和可选配置项
- 敏感信息占位符说明

**部署脚本** (`examples/deploy-dev-test.sh`)
- 完整的部署流程
- 前置检查、备份、验证
- 错误处理和回滚机制

**回滚脚本** (`examples/rollback-dev-test.sh`)
- 快速回滚到上一个版本
- 状态记录和恢复验证
- 回滚报告生成

**CI/CD Pipeline** (`examples/ci-cd-github-actions.yaml`)
- GitHub Actions 完整配置
- 包含构建、测试、安全扫描、部署
- 多环境支持和人工审批

### 10.2 集成文档

**与 Orchestrator 集成指南** (`docs/orchestrator-integration.md`)
- CLI 命令映射
- Human Gate 实现细节
- 执行流程说明
- 完整实战示例

包含以下核心内容：

1. **集成架构图**
   - L1/L2 Workflow 调用关系
   - Human Gate 交互流程

2. **CLI 命令参考**
   - `lee run devops init` - 初始化方案
   - `lee run devops generate` - 生成代码
   - `lee run devops inject-config` - 注入配置
   - `lee run devops deploy` - 部署
   - `lee run devops verify` - 验证
   - `lee run devops freeze` - 冻结
   - `lee run devops rollback` - 回滚

3. **Human Gate 实现**
   - Gate 触发机制
   - Gate 数据结构
   - 审批流程
   - Gate UI 示例

4. **实战流程**
   - 完整部署流程示例
   - 回滚流程示例
   - 错误处理流程

### 10.3 使用示例

#### 示例 1: 创建新项目的 DevOps 配置

```bash
# 1. 创建项目目录
mkdir -p project/my-app/devops
cd project/my-app/devops

# 2. 复制示例文件
cp -r spec-global/departments/devops/examples/* .
cp -r spec-global/departments/devops/templates/* .

# 3. 修改 docker-compose.yml 中的占位符
# 编辑文件，将 ${APP_NAME} 替换为实际项目名

# 4. 填写环境配置
# 编辑 env-config.dev.yaml 和 env-config.test.yaml
# 填写真实的数据库连接、密钥等信息

# 5. 部署到 dev 环境
chmod +x deploy/deploy-dev-test.sh
./deploy/deploy-dev-test.sh dev
```

#### 示例 2: 在 L1 Workflow 中调用 DevOps L2

```yaml
# L1 Product MVP Workflow 中的 Dev 部分步骤
steps:
  # ... 其他步骤 ...

  # Step 4: Dev 实现
  - id: dev_implementation
    kind: workflow_spawn
    workflow: workflow.dev.development_pipeline
    level: department
    outputs:
      - path: contracts/test_submission_freeze_package/v1/freeze.yaml

    # Dev 完成后自动触发 DevOps 部署
    post_steps:
      - id: devops_deployment
        kind: workflow_spawn
        workflow: workflow.devops.deployment
        level: department
        inputs:
          - from_step: dev_implementation
            contract: contracts/test_submission_freeze_package/v1/freeze.yaml
        outputs:
          - path: contracts/deployment_freeze/v1/freeze.yaml
```

### 10.4 最佳实践

#### 安全实践
1. **凭证管理**
   - 使用密钥管理服务（AWS Secrets Manager、HashiCorp Vault）
   - 不要将凭证提交到版本控制
   - 定期轮换密钥

2. **环境隔离**
   - 为不同环境使用不同的凭证
   - 限制生产环境的访问权限
   - 启用 MFA（多因素认证）

3. **审计跟踪**
   - 记录所有配置变更
   - 记录所有部署操作
   - 定期审计日志

#### 运维实践
1. **渐进式部署**
   - 先部署到 dev
   - 再部署到 test
   - 最后到 staging/prod

2. **自动化测试**
   - 部署前运行自动化测试
   - 部署后运行烟雾测试
   - 定期运行性能测试

3. **监控告警**
   - 配置健康检查
   - 设置监控指标
   - 配置告警通知

4. **回滚准备**
   - 始终准备回滚脚本
   - 定期测试回滚流程
   - 记录回滚时间

---

**文档版本**: 1.1
**最后更新**: 2026-01-29
**维护者**: LEE Team
**状态**: ✅ 已完成
