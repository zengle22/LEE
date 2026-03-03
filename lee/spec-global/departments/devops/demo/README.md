# DevOps 主流程 Demo

> **LEE Orchestrator v3.1 - DevOps 部门主流程演示**
>
> Demo 版本: 1.0
> 创建日期: 2026-01-29

---

## 📋 Demo 概述

本演示展示 DevOps L2 Workflow 的完整执行过程，从架构设计到版本冻结的 6 个阶段。

### 演示场景

**项目**: `task-manager` (任务管理系统)
**目标环境**: dev + test
**部署方式**: Docker Compose
**版本**: 1.0.0

---

## 🎯 执行流程概览

```
┌─────────────────────────────────────────────────────────────┐
│              DevOps L2 Workflow 执行流程                      │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Phase 1: p1_architecture (架构设计)                         │
│ ├─ Agent: agent.devops.architect                            │
│ ├─ 输入: project-spec.json                                  │
│ ├─ 输出: infra-architecture.yaml, env-matrix.yaml          │
│ └─ ⏸️  Human Gate: devops_lead + tech_lead                 │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ Phase 2: p2_infra_code (实施代码生成)                       │
│ ├─ Agent: agent.devops.implementation                       │
│ ├─ 输入: infra-architecture.yaml, env-matrix.yaml          │
│ ├─ 输出: docker-compose.yml, deploy/, cicd/               │
│ └─ ➔  继续执行（无需审批）                                  │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ Phase 3: p3_env_config (配置注入) ⏸️                         │
│ ├─ Kind: HUMAN_GATE                                         │
│ ├─ Reviewers: devops_lead                                   │
│ ├─ 输入: env-config.dev.yaml, env-config.test.yaml         │
│ └─ ➔  等待人类填写配置并审批                                │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ Phase 4: p4_deploy_dev_test (部署到 dev/test)               │
│ ├─ Runner: shell                                            │
│ ├─ 命令: ./deploy/deploy-dev-test.sh dev                   │
│ ├─ 输出: 部署日志、服务状态                                  │
│ └─ ➔  继续执行（自动部署）                                  │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ Phase 5: p5_verification (环境验收) ⏸️                       │
│ ├─ Agent: agent.devops.verification                         │
│ ├─ Reviewers: devops_lead + qa_lead                         │
│ ├─ 输出: deployment-checklist.md, release-manifest.yaml    │
│ └─ ➔  等待验证审批                                          │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ Phase 6: p6_release_freeze (版本冻结) ⏸️                     │
│ ├─ Agent: agent.devops.verification                         │
│ ├─ Reviewers: devops_lead + tech_lead + product_owner      │
│ ├─ 输出: freeze-report.md, audit-trail.yaml                │
│ └─ ➔  等待最终审批                                          │
└─────────────────────────────────────────────────────────────┘
                              ↓
                     ✅ Workflow 完成
```

---

## 📁 Demo 目录结构

```
spec-global/departments/devops/demo/
├── 00-inputs/                    # 输入文件
│   ├── project-spec.json         # 项目规格
│   └── deployment-requirements.md # 部署需求
├── 01-architecture/              # Phase 1 输出
│   ├── infra-architecture.yaml   # 基础设施架构
│   ├── env-matrix.yaml           # 环境矩阵
│   └── gate-approval.yaml        # Gate 审批记录
├── 02-implementation/            # Phase 2 输出
│   ├── docker-compose.yml        # Docker Compose 配置
│   ├── deploy/
│   │   ├── deploy-dev-test.sh    # 部署脚本
│   │   └── rollback-dev-test.sh  # 回滚脚本
│   └── cicd/
│       └── github-actions.yaml   # CI/CD 配置
├── 03-env-config/                # Phase 3 输出
│   ├── env-config.dev.yaml       # Dev 环境配置
│   ├── env-config.test.yaml      # Test 环境配置
│   └── gate-approval.yaml        # Gate 审批记录
├── 04-deployment/                # Phase 4 输出
│   ├── deployment-dev.log        # Dev 部署日志
│   ├── deployment-test.log       # Test 部署日志
│   └── service-status.yaml       # 服务状态
├── 05-verification/              # Phase 5 输出
│   ├── deployment-checklist.md   # 部署验收清单
│   ├── release-manifest.yaml     # 发布清单
│   └── gate-approval.yaml        # Gate 审批记录
├── 06-release-freeze/            # Phase 6 输出
│   ├── freeze-report.md          # 冻结报告
│   ├── audit-trail.yaml          # 审计跟踪
│   └── gate-approval.yaml        # Gate 审批记录
├── execution-log.md              # 完整执行日志
└── README.md                     # 本文档
```

---

## 🚀 执行演示

### 方式 1: 查看完整日志

```bash
# 查看完整的执行日志
cat execution-log.md
```

### 方式 2: 按阶段查看

```bash
# Phase 1: 查看架构设计
cat 01-architecture/infra-architecture.yaml

# Phase 2: 查看实施代码
cat 02-implementation/docker-compose.yml

# Phase 3: 查看环境配置
cat 03-env-config/env-config.dev.yaml

# Phase 4: 查看部署结果
cat 04-deployment/deployment-dev.log

# Phase 5: 查看验证结果
cat 05-verification/deployment-checklist.md

# Phase 6: 查看冻结报告
cat 06-release-freeze/freeze-report.md
```

### 方式 3: 交互式演示

```bash
# 启动交互式演示
cd spec-global/departments/devops/demo
./demo-runner.sh
```

---

## 📊 阶段详情

### Phase 1: p1_architecture (架构设计)

**执行时间**: 2026-01-29 10:00:00 - 10:05:00 (5分钟)

**Agent 执行**:
```yaml
agent: agent.devops.architect
input:
  project_name: "task-manager"
  project_type: "web-application"
  deployment_target: ["dev", "test"]
  tech_stack:
    backend: "go"
    frontend: "react"
    database: "postgresql"
    cache: "redis"
```

**AI 生成的输出**:
- ✅ `infra-architecture.yaml` - 基础设施架构设计
- ✅ `env-matrix.yaml` - 环境配置矩阵
- ✅ `release-strategy.md` - 发布策略文档

**Human Gate 审批**:
```yaml
gate_id: "devops.p1_architecture"
reviewers:
  - role: "devops_lead"
    status: "approved"
    comment: "架构设计合理，环境隔离清晰"
    approved_at: "2026-01-29T10:06:00Z"
  - role: "tech_lead"
    status: "approved"
    comment: "技术选型符合项目需求"
    approved_at: "2026-01-29T10:07:00Z"
```

---

### Phase 2: p2_infra_code (实施代码生成)

**执行时间**: 2026-01-29 10:07:00 - 10:20:00 (13分钟)

**Agent 执行**:
```yaml
agent: agent.devops.implementation
input:
  infra_architecture: "01-architecture/infra-architecture.yaml"
  env_matrix: "01-architecture/env-matrix.yaml"
tools:
  iac: "docker-compose"
  cicd: "github-actions"
```

**AI 生成的输出**:
- ✅ `docker-compose.yml` - Docker Compose 配置（4个服务）
- ✅ `deploy/deploy-dev-test.sh` - 部署脚本（200+ 行）
- ✅ `deploy/rollback-dev-test.sh` - 回滚脚本
- ✅ `cicd/github-actions.yaml` - CI/CD Pipeline

**代码统计**:
- Docker Compose: 180 行
- 部署脚本: 220 行
- 回滚脚本: 150 行
- CI/CD 配置: 350 行
- **总计**: ~900 行代码和配置

---

### Phase 3: p3_env_config (配置注入) ⏸️

**执行时间**: 2026-01-29 10:20:00 - 10:45:00 (25分钟，人类填写)

**Human Gate 触发**:
```yaml
gate_id: "devops.p3_env_config"
status: "pending"
reviewers:
  - role: "devops_lead"
checklist:
  - env_scope: "环境范围确认"
    status: "pending"
  - credentials: "敏感凭证已填写"
    status: "pending"
  - rollback: "回滚脚本已准备"
    status: "completed"
```

**人类操作**:
1. ✅ 检查环境配置模板
2. ✅ 填写 dev 环境配置（数据库、Redis、API密钥）
3. ✅ 填写 test 环境配置
4. ✅ 验证配置格式
5. ✅ 提交审批

**审批记录**:
```yaml
gate_id: "devops.p3_env_config"
reviewer: "devops_lead"
status: "approved"
comment: |
  环境配置已验证：
  - Dev 环境：配置正确，凭证已填写
  - Test 环境：配置正确，测试数据准备完成
  - 回滚脚本：已准备就绪
approved_at: "2026-01-29T10:45:00Z"
```

---

### Phase 4: p4_deploy_dev_test (部署到 dev/test)

**执行时间**: 2026-01-29 10:45:00 - 11:00:00 (15分钟)

**Shell Runner 执行**:
```bash
# 部署到 dev 环境
./deploy/deploy-dev-test.sh dev

# 输出：
[INFO] 开始部署到 dev 环境...
[INFO] 前置检查通过
[INFO] 备份当前部署
[INFO] 加载环境配置
[INFO] 停止现有服务
[INFO] 拉取最新镜像
[INFO] 启动服务
[INFO] 等待服务健康...
[INFO] ✅ 所有服务健康检查通过
[INFO] ✅ 部署到 dev 环境成功
```

**部署结果**:
```yaml
environment: "dev"
status: "success"
services:
  - name: "app"
    status: "running"
    health: "healthy"
    image: "task-manager:1.0.0"
  - name: "db"
    status: "running"
    health: "healthy"
    version: "postgresql:15"
  - name: "redis"
    status: "running"
    health: "healthy"
    version: "redis:7"
  - name: "nginx"
    status: "running"
    health: "healthy"
```

**Test 环境部署**:
```bash
# 部署到 test 环境
./deploy/deploy-dev-test.sh test

# 输出类似，部署成功
```

---

### Phase 5: p5_verification (环境验收) ⏸️

**执行时间**: 2026-01-29 11:00:00 - 11:15:00 (15分钟)

**Agent 执行**:
```yaml
agent: agent.devops.verification
input:
  deployment_status: "04-deployment/service-status.yaml"
  environment: ["dev", "test"]
verification_checks:
  - services_running: "检查服务运行状态"
  - health_checks: "健康检查通过"
  - database_accessible: "数据库可访问"
  - api_responsive: "API 响应正常"
  - logs_collected: "日志正常收集"
```

**AI 生成的输出**:
- ✅ `deployment-checklist.md` - 部署验收清单（15项检查）
- ✅ `release-manifest.yaml` - 发布清单（draft）

**验收结果**:
```yaml
verification_summary:
  total_checks: 15
  passed: 15
  failed: 0
  warning: 0
  status: "passed"
details:
  dev_environment:
    status: "passed"
    checks_passed: 8
  test_environment:
    status: "passed"
    checks_passed: 7
```

**Human Gate 审批**:
```yaml
gate_id: "devops.p5_verification"
reviewers:
  - role: "devops_lead"
    status: "approved"
    comment: "Dev 环境验收通过，服务运行正常"
  - role: "qa_lead"
    status: "approved"
    comment: "Test 环境验收通过，可以进行自动化测试"
```

---

### Phase 6: p6_release_freeze (版本冻结) ⏸️

**执行时间**: 2026-01-29 11:15:00 - 11:30:00 (15分钟)

**Agent 执行**:
```yaml
agent: agent.devops.verification
input:
  verification_result: "05-verification/deployment-checklist.md"
  release_manifest: "05-verification/release-manifest.yaml"
  version: "1.0.0"
freeze_actions:
  - generate_freeze_report: "生成冻结报告"
  - generate_audit_trail: "生成审计跟踪"
  - create_release_bundle: "创建发布包"
  - tag_version: "打版本标签"
```

**AI 生成的输出**:
- ✅ `freeze-report.md` - 冻结报告
- ✅ `audit-trail.yaml` - 完整审计跟踪
- ✅ `release-bundle-v1.0.0.tar.gz` - 发布包

**审计跟踪**:
```yaml
audit_trail:
  version: "1.0.0"
  frozen_at: "2026-01-29T11:30:00Z"
  frozen_by: "devops_lead + tech_lead + product_owner"
  workflow_id: "workflow.devops.deployment"
  execution_id: "exec-devops-20260129-001"
  phases:
    - phase: "p1_architecture"
      agent: "agent.devops.architect"
      completed_at: "2026-01-29T10:05:00Z"
      approved_by: ["devops_lead", "tech_lead"]
    - phase: "p2_infra_code"
      agent: "agent.devops.implementation"
      completed_at: "2026-01-29T10:20:00Z"
    - phase: "p3_env_config"
      human_gate: true
      approved_by: "devops_lead"
      completed_at: "2026-01-29T10:45:00Z"
    - phase: "p4_deploy_dev_test"
      runner: "shell"
      completed_at: "2026-01-29T11:00:00Z"
    - phase: "p5_verification"
      agent: "agent.devops.verification"
      approved_by: ["devops_lead", "qa_lead"]
      completed_at: "2026-01-29T11:15:00Z"
    - phase: "p6_release_freeze"
      agent: "agent.devops.verification"
      approved_by: ["devops_lead", "tech_lead", "product_owner"]
      completed_at: "2026-01-29T11:30:00Z"
  artifacts:
    - infra_architecture: "01-architecture/infra-architecture.yaml"
    - docker_compose: "02-implementation/docker-compose.yml"
    - deploy_scripts: "02-implementation/deploy/"
    - cicd_pipeline: "02-implementation/cicd/"
    - env_configs: "03-env-config/"
    - release_bundle: "release-bundle-v1.0.0.tar.gz"
```

**最终审批**:
```yaml
gate_id: "devops.p6_release_freeze"
reviewers:
  - role: "devops_lead"
    status: "approved"
    comment: "版本 1.0.0 冻结，部署验收通过"
  - role: "tech_lead"
    status: "approved"
    comment: "技术实现符合规范，可以发布"
  - role: "product_owner"
    status: "approved"
    comment: "功能完整，批准发布 v1.0.0"
```

---

## 📈 执行统计

### 时间统计

| 阶段 | 执行时间 | Agent/Human | 输出文件数 |
|------|----------|-------------|-----------|
| p1_architecture | 5 分钟 | Agent | 3 |
| p2_infra_code | 13 分钟 | Agent | 6 |
| p3_env_config | 25 分钟 | Human | 3 |
| p4_deploy_dev_test | 15 分钟 | Shell | 3 |
| p5_verification | 15 分钟 | Agent + Human | 2 |
| p6_release_freeze | 15 分钟 | Agent + Human | 3 |
| **总计** | **~88 分钟** | - | **20** |

### 输出统计

| 类型 | 数量 | 总大小 |
|------|------|--------|
| YAML 配置 | 8 | ~50 KB |
| Shell 脚本 | 2 | ~15 KB |
| Markdown 文档 | 7 | ~25 KB |
| 日志文件 | 3 | ~10 KB |
| **总计** | **20** | **~100 KB** |

### 代码统计

| 语言 | 文件数 | 行数 |
|------|--------|------|
| YAML | 10 | 850 |
| Shell | 2 | 370 |
| Markdown | 8 | 450 |
| **总计** | **20** | **1,670** |

---

## 🎓 关键学习点

### 1. Agent 执行模式

**Architect Agent** (Phase 1):
- 输入：项目规格
- 输出：架构设计文档
- 特点：高层设计，无需详细实现

**Implementation Agent** (Phase 2):
- 输入：架构设计
- 输出：可执行代码和配置
- 特点：生成完整可用的 IaC 代码

**Verification Agent** (Phase 5, 6):
- 输入：部署状态
- 输出：验收报告和冻结包
- 特点：自动化验证 + 人工审批

### 2. Human Gate 机制

**触发点**:
- Phase 1 后：架构设计审批
- Phase 3：配置注入（必须人类填写）
- Phase 5 后：部署验收
- Phase 6 后：版本冻结

**审批流程**:
1. Workflow 遇到 Gate，状态转为 BLOCKED
2. 创建 Gate 实例，通知审批者
3. 审批者检查清单和输入
4. 审批决策（Approved/Rejected）
5. Workflow 继续（Approved）或终止（Rejected）

### 3. Shell Runner 执行

**Phase 4 部署**:
- 直接执行 shell 脚本
- 无需 Agent 参与
- 自动化程度高
- 错误处理完善

### 4. 冻结包机制

**冻结内容**:
- 架构设计文档
- IaC 代码
- 部署脚本
- 环境配置
- CI/CD Pipeline
- 验收报告
- 审计跟踪

**用途**:
- 版本回溯
- 审计合规
- 知识沉淀
- 跨环境复用

---

## 🔍 深入分析

### 成功要素

1. **清晰的职责分工**
   - Architect 负责设计
   - Implementation 负责编码
   - Verification 负责验收

2. **合理的审批点**
   - 架构设计：防止方向错误
   - 配置注入：确保凭证安全
   - 部署验收：保证质量
   - 版本冻结：最终把关

3. **完整的审计跟踪**
   - 每个阶段都有时间戳
   - 每个审批都有记录
   - 每个输出都可追溯

4. **可回滚设计**
   - 每个部署都有回滚脚本
   - 配置都有备份
   - 审计记录完整

### 潜在风险

1. **Human Gate 延误**
   - 配置注入需要人类填写
   - 审批可能需要等待
   - 缓解：设置超时和升级机制

2. **环境一致性**
   - Dev/Test/Prod 配置差异
   - 缓解：使用配置模板和验证

3. **回滚复杂度**
   - 数据库迁移回滚困难
   - 缓解：准备数据回滚脚本

---

## 📖 延伸阅读

1. **DevOps 部门规范**: `../README.md`
2. **Orchestrator 集成**: `../docs/orchestrator-integration.md`
3. **实战示例**: `../examples/`
4. **Workflow 定义**: `../workflows/devops-deployment/v1/workflow.yaml`

---

**Demo 版本**: 1.0
**创建日期**: 2026-01-29
**维护者**: LEE Team
**状态**: ✅ 可用于演示和培训
