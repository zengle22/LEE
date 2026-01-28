# DevOps 与 Orchestrator 集成指南

> **LEE Orchestrator v3.1 - DevOps 部门集成文档**
>
> 文档版本: 1.0
> 创建日期: 2026-01-29
> 状态: ✅ 已完成

---

## 📋 目录

- [一、集成概览](#一集成概览)
- [二、CLI 命令映射](#二cli-命令映射)
- [三、Human Gate 实现](#三human-gate-实现)
- [四、执行流程](#四执行流程)
- [五、实战示例](#五实战示例)

---

## 一、集成概览

### 1.1 集成架构

```
┌─────────────────────────────────────────────────────────────┐
│                    LEE Orchestrator v3.1                    │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐ │
│  │          L1: Product MVP Workflow                    │ │
│  │  ┌─────────────────────────────────────────────────┐  │ │
│  │  │ Step 4: Dev Implementation (L2)                │  │ │
│  │  │  ┌───────────────────────────────────────────┐  │  │ │
│  │  │  │ Step 4.5: Deploy to Test (L2 Sub-step)    │  │  │ │
│  │  │  │  ┌─────────────────────────────────────┐  │  │  │ │
│  │  │  │  │ Spawn L2: workflow.devops.deployment│  │  │  │ │
│  │  │  │  └─────────────────────────────────────┘  │  │  │ │
│  │  │  │                                           │  │  │ │
│  │  │  │  ➔ DevOps L2 Workflow:                   │  │  │ │
│  │  │  │     p1: Architecture (Agent)             │  │  │ │
│  │  │  │     p2: Infra Code (Agent)               │  │  │ │
│  │  │  │     p3: Env Config (Human Gate) ⏸️       │  │  │ │
│  │  │  │     p4: Deploy (Shell)                   │  │  │ │
│  │  │  │     p5: Verification (Agent + Gate) ⏸️   │  │  │ │
│  │  │  │     p6: Freeze (Agent + Gate) ⏸️        │  │  │ │
│  │  │  └───────────────────────────────────────────┘  │  │ │
│  │  └─────────────────────────────────────────────────┘  │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐ │
│  │              Human Gate System                        │ │
│  │  ┌─────────────────────────────────────────────────┐  │ │
│  │  │  Pending Gates Queue                            │  │ │
│  │  │  - gate_id: devops.p3_env_config                │  │ │
│  │  │    reviewers: [devops_lead]                     │  │ │
│  │  │    status: pending                              │  │ │
│  │  │  - gate_id: devops.p5_verification              │  │ │
│  │  │    reviewers: [devops_lead, qa_lead]            │  │ │
│  │  │    status: pending                              │  │ │
│  │  └─────────────────────────────────────────────────┘  │ │
│  └───────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 核心概念

| 概念 | 说明 | DevOps 实现 |
|------|------|------------|
| **Workflow Spawn** | L1 调用 L2 | Dev L2 spawn DevOps L2 |
| **Agent Execution** | LLM Agent 生成方案 | architect → implementation → verification |
| **Human Gate** | 人工审批点 | 配置注入、部署验收、版本冻结 |
| **Shell Runner** | 执行命令 | 部署脚本、回滚脚本 |
| **Freeze Package** | 部署产物 | release-manifest.yaml、freeze-report.md |

---

## 二、CLI 命令映射

### 2.1 命令结构

```bash
lee run devops <command> [options]
```

### 2.2 可用命令

#### 📋 `lee run devops init`

初始化 DevOps 基础设施方案。

```bash
lee run devops init --project <project_name>
```

**参数**:
- `--project`: 项目名称（必需）

**执行**:
- 调用 `agent.devops.architect`
- 生成 `infra-architecture.yaml`
- 生成 `env-matrix.yaml`
- 生成 `release-strategy.md`

**输出**:
```
project/<project_name>/devops/
├── infra-architecture.yaml
├── env-matrix.yaml
└── release-strategy.md
```

---

#### ⚙️ `lee run devops generate`

生成 DevOps 实施代码。

```bash
lee run devops generate --project <project_name>
```

**参数**:
- `--project`: 项目名称（必需）
- `--tool`: IaC 工具（可选，默认: docker-compose）

**执行**:
- 调用 `agent.devops.implementation`
- 生成 `infra/` 目录
- 生成 `cicd/` 目录
- 生成 `deploy/` 脚本
- 生成 `scripts/` 辅助脚本

**输出**:
```
project/<project_name>/devops/
├── infra/
│   ├── docker-compose.yml
│   ├── k8s/
│   └── terraform/
├── cicd/
│   └── github-actions/
├── deploy/
│   ├── deploy-dev-test.sh
│   └── rollback-dev-test.sh
└── scripts/
    ├── db-init/
    └── helpers/
```

---

#### 🔐 `lee run devops inject-config`

注入环境配置（人类填写真实凭证）。

```bash
lee run devops inject-config --project <project_name> --env <environment>
```

**参数**:
- `--project`: 项目名称（必需）
- `--env`: 环境（dev/test/staging/prod）

**执行**:
- 读取 `templates/env-config.template.yaml`
- 生成 `env/env-config.<env>.yaml`
- 提示人类填写敏感信息
- 生成 `.env.<env>` 文件

**输出**:
```
project/<project_name>/devops/env/
├── env-config.dev.yaml
├── env-config.test.yaml
├── .env.dev
└── .env.test
```

**注意**: 此命令只是生成模板，真实凭证必须由人类填写！

---

#### 🚀 `lee run devops deploy`

部署到指定环境。

```bash
lee run devops deploy --project <project_name> --env <environment>
```

**参数**:
- `--project`: 项目名称（必需）
- `--env`: 环境（dev/test）
- `--skip-approval`: 跳过审批（仅 dev/test，默认: false）

**执行流程**:

1. **检查前置条件**:
   ```bash
   cd project/<project_name>/devops
   ./deploy/deploy-dev-test.sh <env>
   ```

2. **记录审计日志**:
   ```yaml
   audit_log:
     timestamp: "2026-01-29T10:00:00Z"
     operator: "orchestrator"
     action: "deploy"
     environment: "<env>"
     command: "./deploy/deploy-dev-test.sh <env>"
   ```

3. **更新状态**:
   ```yaml
   deployment_status:
     environment: "<env>"
     status: "deploying"
     started_at: "2026-01-29T10:00:00Z"
   ```

4. **等待完成**:
   - 监控部署脚本输出
   - 检查健康状态
   - 记录部署结果

**输出**:
```
deployment_status:
  environment: "<env>"
  status: "success"
  completed_at: "2026-01-29T10:05:00Z"
  health_check: "passed"
```

---

#### 🔍 `lee run devops verify`

验证部署状态。

```bash
lee run devops verify --project <project_name> --env <environment>
```

**参数**:
- `--project`: 项目名称（必需）
- `--env`: 环境（必需）

**执行**:
- 调用 `agent.devops.verification`
- 运行 `deployment-checklist.md`
- 生成验证报告

**输出**:
```
project/<project_name>/devops/logs/
└── verification-<env>-20260129.md
```

---

#### ❄️ `lee run devops freeze`

冻结版本。

```bash
lee run devops freeze --project <project_name> --version <version>
```

**参数**:
- `--project`: 项目名称（必需）
- `--version`: 版本号（必需）
- `--message`: 冻结说明（可选）

**执行**:
- 调用 `agent.devops.verification`
- 生成 `release-manifest.yaml`
- 生成 `freeze-report.md`
- 生成 `audit-trail.yaml`

**输出**:
```
project/<project_name>/devops/release/
├── v1.0.0/
│   ├── release-manifest.yaml
│   ├── freeze-report.md
│   ├── audit-trail.yaml
│   └── release-bundle.tar.gz
```

---

#### 🔄 `lee run devops rollback`

回滚部署。

```bash
lee run devops rollback --project <project_name> --env <environment> [--version <version>]
```

**参数**:
- `--project`: 项目名称（必需）
- `--env`: 环境（必需）
- `--version`: 目标版本（可选）

**执行**:
- 确认回滚操作
- 执行 `rollback-<env>.sh`
- 验证回滚结果
- 生成回滚报告

**输出**:
```
project/<project_name>/devops/logs/
└── rollback-<env>-20260129.md
```

---

## 三、Human Gate 实现

### 3.1 Gate 触发机制

DevOps L2 Workflow 中的 Human Gate 点：

| 阶段 | Gate ID | 审批者 | 触发条件 |
|------|---------|--------|---------|
| p3 | `devops.p3_env_config` | devops_lead | Agent 完成架构设计后 |
| p5 | `devops.p5_verification` | devops_lead + qa_lead | 部署完成后 |
| p6 | `devops.p6_release_freeze` | devops_lead + tech_lead + product_owner | 验证通过后 |

### 3.2 Gate 数据结构

```yaml
human_gate:
  gate_id: "devops.p3_env_config"
  workflow_id: "workflow.devops.deployment"
  workflow_instance_id: "<instance_id>"
  step_id: "p3_env_config"

  status: "pending"  # pending | approved | rejected

  gate_info:
    name: "环境配置注入"
    description: "人类填写真实环境配置和凭证"
    priority: "high"

  reviewers:
    - role: "devops_lead"
      name: "<reviewer_name>"
      status: "pending"
      approved_at: null

  checklist:
    checklists:
      - ref: "checklists/devops-human-gate.checklist.yaml"
        items:
          - id: "env_scope"
            description: "环境范围确认"
            status: "pending"
            required: true
          - id: "credentials"
            description: "敏感凭证已填写"
            status: "pending"
            required: true
          - id: "rollback"
            description: "回滚脚本已准备"
            status: "pending"
            required: true

  inputs:
    - name: "env-config.dev.yaml"
      path: "env/env-config.dev.yaml"
      description: "开发环境配置文件"
      review_required: true
    - name: "env-config.test.yaml"
      path: "env/env-config.test.yaml"
      description: "测试环境配置文件"
      review_required: true

  outputs:
    - name: "env-config-approval"
      path: "contracts/env-config-approval/v1/approval.yaml"
      description: "环境配置审批记录"

  timeout:
    duration: "24h"
    action: "escalate"
    escalate_to: ["tech_lead"]

  created_at: "2026-01-29T10:00:00Z"
  updated_at: "2026-01-29T10:00:00Z"
```

### 3.3 Gate 审批流程

```
┌─────────────────────────────────────────────────────────────┐
│                    Human Gate Flow                          │
│                                                             │
│  1. Workflow 执行到 Gate 点                                 │
│     ➔ 状态转为 BLOCKED                                     │
│     ➔ 创建 Gate 实例                                       │
│                                                             │
│  2. 通知审批者                                              │
│     ➔ 发送通知到 devops_lead                               │
│     ➔ 显示 Checklist 和 Inputs                            │
│                                                             │
│  3. 审批者检查                                              │
│     ➔ 查看清单项目                                         │
│     ➔ 检查配置文件                                         │
│     ➔ 验证凭证格式                                         │
│                                                             │
│  4. 审批决策                                                │
│     ├─ Approved:                                           │
│     │  ➔ 填写审批意见                                      │
│     │  ➔ 状态转为 APPROVED                                 │
│     │  ➔ Workflow 继续                                    │
│     │                                                      │
│     └─ Rejected:                                           │
│        ➔ 填写拒绝原因                                      │
│        ➔ 状态转为 REJECTED                                 │
│        ➔ Workflow 终止或要求整改                          │
│                                                             │
│  5. 记录审计跟踪                                            │
│     ➔ 保存审批记录到 audit-trail.yaml                     │
└─────────────────────────────────────────────────────────────┘
```

### 3.4 Gate UI 示例

```bash
# 查看待审批的 Gates
lee gate list

# 输出：
# Pending Gates:
# ┌──────────────────────────────────────────────────────────┐
# │ Gate ID: devops.p3_env_config                            │
# │ Workflow: workflow.devops.deployment                     │
# │ Status: pending                                          │
# │ Reviewers: devops_lead                                   │
# │                                                           │
# │ Checklist:                                                │
# │   [ ] env_scope          - 环境范围确认                  │
# │   [ ] credentials        - 敏感凭证已填写                │
# │   [ ] rollback           - 回滚脚本已准备                │
# │                                                           │
# │ Inputs:                                                   │
# │   - env/env-config.dev.yaml                              │
# │   - env/env-config.test.yaml                             │
# │                                                           │
# │ Actions:                                                  │
# │   lee gate approve devops.p3_env_config                  │
# │   lee gate reject devops.p3_env_config --reason "..."    │
# └──────────────────────────────────────────────────────────┘

# 审批 Gate
lee gate approve devops.p3_env_config --comment "配置已验证，可以继续"

# 拒绝 Gate
lee gate reject devops.p3_env_config --reason "缺少回滚脚本，请补充"
```

---

## 四、执行流程

### 4.1 完整执行流程

```
┌─────────────────────────────────────────────────────────────┐
│               DevOps L2 执行流程                            │
└─────────────────────────────────────────────────────────────┘

Phase 1: p1_architecture (架构设计)
├─ Agent: agent.devops.architect
├─ Input:
│  ├─ 项目基本信息
│  └─ 部署需求
├─ Action:
│  └─ LLM 生成基础设施架构设计
├─ Output:
│  ├─ infra-architecture.yaml
│  ├─ env-matrix.yaml
│  └─ release-strategy.md
└─ ➔ 触发 Human Gate: devops_lead + tech_lead

Phase 2: p2_infra_code (实施代码生成)
├─ Agent: agent.devops.implementation
├─ Input:
│  ├─ infra-architecture.yaml
│  └─ env-matrix.yaml
├─ Action:
│  └─ LLM 生成 IaC 代码和脚本
├─ Output:
│  ├─ infra/docker-compose.yml
│  ├─ cicd/github-actions/
│  └─ deploy/deploy-dev-test.sh
└─ ➔ 继续下一步

Phase 3: p3_env_config (配置注入) ⏸️
├─ Kind: HUMAN_GATE
├─ Reviewers: devops_lead
├─ Checklist: devops-human-gate.checklist.yaml
├─ Action:
│  └─ 人类填写真实配置和凭证
├─ Output:
│  ├─ env/env-config.dev.yaml
│  ├─ env/env-config.test.yaml
│  └─ env/.env.dev, env/.env.test
└─ ➔ 等待审批后继续

Phase 4: p4_deploy_dev_test (部署到 dev/test)
├─ Kind: SHELL_RUNNER
├─ Command: ./deploy/deploy-dev-test.sh <env>
├─ Action:
│  ├─ 停止现有服务
│  ├─ 拉取最新镜像
│  ├─ 启动新服务
│  └─ 健康检查
├─ Output:
│  ├─ 部署日志
│  └─ 部署状态
└─ ➔ 继续下一步

Phase 5: p5_verification (环境验收) ⏸️
├─ Agent: agent.devops.verification
├─ Kind: AGENT + HUMAN_GATE
├─ Reviewers: devops_lead + qa_lead
├─ Action:
│  ├─ Agent 运行验证检查
│  ├─ 生成 deployment-checklist.md
│  └─ 人类审核验证结果
├─ Output:
│  ├─ deployment-checklist.md
│  └─ release-manifest.yaml (draft)
└─ ➔ 等待审批后继续

Phase 6: p6_release_freeze (版本冻结) ⏸️
├─ Agent: agent.devops.verification
├─ Kind: AGENT + HUMAN_GATE
├─ Reviewers: devops_lead + tech_lead + product_owner
├─ Action:
│  ├─ Agent 生成冻结报告
│  ├─ 生成审计跟踪
│  └─ 最终审批
├─ Output:
│  ├─ freeze-report.md
│  ├─ audit-trail.yaml
│  └─ release-manifest.yaml (final)
└─ ➔ Workflow 完成
```

### 4.2 错误处理流程

```
┌─────────────────────────────────────────────────────────────┐
│                    错误处理流程                              │
└─────────────────────────────────────────────────────────────┘

错误场景 1: Agent 执行失败
├─ 检测: Agent 返回错误或超时
├─ 状态: FAILED
├─ 处理:
│  ├─ 记录错误日志
│  ├─ 生成错误报告
│  └─ 通知人类介入
└─ 恢复: 修复问题后重新执行

错误场景 2: Human Gate 超时
├─ 检测: Gate 超过 timeout 时间
├─ 状态: TIMEOUT
├─ 处理:
│  ├─ 发送提醒通知
│  └─ 升级到 escalate_to 角色
└─ 恢复: 审批者处理后继续

错误场景 3: Shell 脚本执行失败
├─ 检测: 脚本返回非 0 退出码
├─ 状态: FAILED
├─ 处理:
│  ├─ 记录脚本输出
│  ├─ 检查回滚脚本
│  └─ 询问是否回滚
└─ 恢复: 执行回滚或人工修复

错误场景 4: 验证检查失败
├─ 检测: verification 返回失败
├─ 状态: BLOCKED
├─ 处理:
│  ├─ 记录失败原因
│  ├─ 生成整改建议
│  └─ 触发 Human Gate
└─ 恢复: 修复后重新验证
```

---

## 五、实战示例

### 5.1 完整部署流程

```bash
# ============================================================
# 场景：将新版本部署到 test 环境
# ============================================================

# 步骤 1: 初始化 DevOps 方案
lee run devops init --project my-app

# 输出：
# ✓ infra-architecture.yaml 生成完成
# ✓ env-matrix.yaml 生成完成
# ✓ release-strategy.md 生成完成

# 步骤 2: 生成实施代码
lee run devops generate --project my-app --tool docker-compose

# 输出：
# ✓ infra/docker-compose.yml 生成完成
# ✓ cicd/github-actions/ci-cd-github-actions.yaml 生成完成
# ✓ deploy/deploy-dev-test.sh 生成完成
# ✓ deploy/rollback-dev-test.sh 生成完成

# 步骤 3: 填写环境配置
lee run devops inject-config --project my-app --env dev
lee run devops inject-config --project my-app --env test

# 输出：
# ✓ env/env-config.dev.yaml 已生成
# ✓ env/env-config.test.yaml 已生成
# ⚠️  请手动填写敏感凭证（${VAR_NAME} 占位符）

# 人类编辑文件，填写真实凭证...
# vim project/my-app/devops/env/env-config.dev.yaml
# vim project/my-app/devops/env/env-config.test.yaml

# 步骤 4: 启动 DevOps Workflow
lee workflow start workflow.devops.deployment --project my-app

# 输出：
# ✓ Workflow 实例创建成功
#   Instance ID: wf-devops-20260129-001
#   Status: RUNNING

# 步骤 5: 等待到 p3 Human Gate
# Workflow 自动执行到 p3 停止，等待审批

# 查看待审批 Gates
lee gate list

# 输出：
# Pending Gates:
#   - devops.p3_env_config (reviewers: devops_lead)

# 审批 Gate
lee gate approve devops.p3_env_config \
  --comment "环境配置已验证，dev 和 test 配置正确"

# 输出：
# ✓ Gate 审批通过
# ✓ Workflow 继续执行

# 步骤 6: 等待部署完成
# Workflow 执行 p4: 部署到 dev/test

# 查看部署状态
lee run devops status --project my-app --env test

# 输出：
# Deployment Status:
#   Environment: test
#   Status: deploying
#   Progress: 60%
#   Services:
#     - app: running
#     - db: running
#     - redis: running

# 步骤 7: 验证部署
# Workflow 执行 p5: 验证

# 查看待审批 Gates
lee gate list

# 输出：
# Pending Gates:
#   - devops.p5_verification (reviewers: devops_lead, qa_lead)

# 审批 Gate
lee gate approve devops.p5_verification \
  --comment "部署验证通过，所有服务正常"

# 步骤 8: 版本冻结
# Workflow 执行 p6: 冻结版本

# 查看待审批 Gates
lee gate list

# 输出：
# Pending Gates:
#   - devops.p6_release_freeze (reviewers: devops_lead, tech_lead, product_owner)

# 最终审批
lee gate approve devops.p6_release_freeze \
  --comment "版本 1.0.0 冻结，可以发布"

# 输出：
# ✓ Gate 审批通过
# ✓ Workflow 完成
# ✓ 版本已冻结
#   Release: v1.0.0
#   Manifest: release/v1.0.0/release-manifest.yaml

# 完成！
```

### 5.2 回滚流程

```bash
# ============================================================
# 场景：部署失败需要回滚
# ============================================================

# 步骤 1: 检测部署失败
# 自动或手动发现部署失败

# 步骤 2: 查看部署状态
lee run devops status --project my-app --env test

# 输出：
# Deployment Status:
#   Environment: test
#   Status: failed
#   Error: Health check failed
#   Failed at: 2026-01-29T10:05:00Z

# 步骤 3: 执行回滚
lee run devops rollback --project my-app --env test --version 0.9.0

# 输出：
# ⚠️  即将回滚 test 环境到版本 0.9.0
# ⚠️  此操作将停止当前服务并恢复上一个版本
#
# 确认要继续吗? (yes/no): yes

# ✓ 停止当前服务
# ✓ 恢复版本 0.9.0
# ✓ 启动恢复的服务
# ✓ 服务恢复成功

# 步骤 4: 验证回滚
lee run devops verify --project my-app --env test

# 输出：
# ✓ Health check passed
# ✓ Services running: app, db, redis
# ✓ Version: 0.9.0

# 步骤 5: 查看回滚报告
cat project/my-app/devops/logs/rollback-test-20260129.md

# 输出：
# === 回滚报告 ===
# 环境: test
# 回滚时间: 2026-01-29T10:10:00Z
# 从版本: 1.0.0
# 到版本: 0.9.0
# 状态: success
#
# === 回滚原因 ===
# 健康检查失败，服务无法正常启动
```

---

## 六、最佳实践

### 6.1 安全建议

1. **凭证管理**
   - 使用密钥管理服务（AWS Secrets Manager、HashiCorp Vault）
   - 不要将凭证提交到版本控制
   - 定期轮换密钥和密码

2. **权限控制**
   - 为不同环境使用不同的凭证
   - 限制生产环境的访问权限
   - 启用 MFA（多因素认证）

3. **审计跟踪**
   - 记录所有配置变更
   - 记录所有部署操作
   - 定期审计日志

### 6.2 运维建议

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

**文档版本**: 1.0
**最后更新**: 2026-01-29
**维护者**: LEE Team
**状态**: ✅ 已完成
