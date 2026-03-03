# DevOps 部署工作流 v1.2 Demo

> **演示 resource_binding 资源绑定机制**
>
> Demo 版本: 1.2
> 创建日期: 2026-01-30

---

## 核心变化：资源绑定机制

v1.2 新增了 `resource_binding`，确保部署 **只能通过 Ansible inventory 触达机器**：

```yaml
resource_binding:
  type: ansible_inventory
  contract_ref: contract.devops.execution
  inventories:
    dev:     project/running-coach/devops/ansible/inventory/dev
    test:    project/running-coach/devops/ansible/inventory/test
    staging: project/running-coach/devops/ansible/inventory/staging
    prod:    project/running-coach/devops/ansible/inventory/prod
```

**关键约束**：
- `NO_RESOURCE_PROVISIONING` - AI 禁止创建/删除云资源
- `MUST_USE_INVENTORY` - 必须通过 inventory 引用服务器
- 硬件资源由人类管理（`resource_policy.hardware_resources.managed_by: human`）

---

## 演示场景

| 项目 | 说明 |
|------|------|
| **项目名称** | running-coach (AI跑步教练) |
| **目标环境** | dev + test |
| **部署方式** | Docker Compose + Ansible |
| **版本** | 1.0.0 |

---

## Demo 目录结构

```
v1.2-resource-binding/
├── 00-inventory/                    # ★ v1.2 核心：Inventory 结构
│   ├── dev/
│   │   ├── hosts.ini                # Dev 主机列表
│   │   └── group_vars.yml           # Dev 环境变量
│   ├── test/
│   │   ├── hosts.ini
│   │   └── group_vars.yml
│   └── resource-binding.yaml        # 资源绑定声明
├── 01-architecture/                 # Phase 1 输出
│   ├── infra-architecture.yaml
│   ├── env-matrix.yaml
│   ├── release-strategy.md
│   └── gate-approval.yaml
├── 02-implementation/               # Phase 2 输出
│   ├── docker-compose.yml
│   ├── deploy/
│   │   ├── deploy-dev.sh
│   │   ├── deploy-test.sh
│   │   └── rollback.sh
│   └── ansible/
│       └── playbooks/
│           ├── deploy.yml
│           └── rollback.yml
├── 03-env-config/                   # Phase 3 输出
│   ├── env-config.dev.yaml
│   ├── env-config.test.yaml
│   └── gate-approval.yaml
├── 04-deployment/                   # Phase 4 输出
│   ├── deploy-dev.log
│   ├── deploy-test.log
│   └── inventory-usage.yaml         # ★ 显示使用了哪些 inventory
├── 05-verification/                 # Phase 5 输出
│   ├── deployment-checklist.md
│   ├── release-manifest.yaml
│   └── gate-approval.yaml
├── 06-release-freeze/               # Phase 6 输出
│   ├── freeze-report.md
│   ├── audit-trail.yaml
│   └── gate-approval.yaml
├── demo-runner.sh                   # 交互式演示脚本
└── README.md                        # 本文档
```

---

## 快速开始

```bash
# 进入 demo 目录
cd spec-global/departments/devops/demo/v1.2-resource-binding

# 运行交互式演示
./demo-runner.sh

# 或直接查看各阶段产物
cat 00-inventory/resource-binding.yaml
cat 04-deployment/inventory-usage.yaml
```

---

## 6 个 Phase 执行流程

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    DevOps Deployment Workflow v1.2                          │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    resource_binding (v1.2 新增)                      │   │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐                │   │
│  │  │inventory│  │inventory│  │inventory│  │inventory│                │   │
│  │  │   dev   │  │  test   │  │ staging │  │  prod   │                │   │
│  │  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘                │   │
│  └───────┼────────────┼────────────┼────────────┼─────────────────────┘   │
│          │            │            │            │                          │
│          ▼            ▼            ▼            ▼                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Phase 1          Phase 2          Phase 3          Phase 4                │
│  ┌────────┐       ┌────────┐       ┌────────┐       ┌────────┐            │
│  │Architect│──────▶│Implement│──────▶│ Human  │──────▶│ Deploy │            │
│  │  Agent  │       │  Agent  │       │  Gate  │       │dev/test│            │
│  └────────┘       └────────┘       └────────┘       └────┬───┘            │
│       │                                                   │                 │
│       ▼                                        uses_inventory               │
│  [H.Gate]                                      ├── dev ◀──┘                 │
│                                                └── test                     │
│                                                                             │
│  Phase 5          Phase 6                                                  │
│  ┌────────┐       ┌────────┐                                               │
│  │Verify  │──────▶│ Freeze │──────▶ ✅ 完成                                │
│  │ Agent  │       │ Agent  │                                               │
│  └────────┘       └────────┘                                               │
│       │                │                                                    │
│       ▼                ▼                                                    │
│  [H.Gate]         [H.Gate]                                                 │
│                   (最终审批)                                                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 关键文件说明

### 1. resource-binding.yaml (v1.2 核心)

```yaml
# 资源绑定声明 - 部署只能通过这些 inventory 触达机器
resource_binding:
  type: ansible_inventory
  contract_ref: contract.devops.execution

  # 绑定的 inventory 路径
  inventories:
    dev: ./00-inventory/dev
    test: ./00-inventory/test

  # 约束规则
  constraints:
    - NO_RESOURCE_PROVISIONING   # 禁止创建云资源
    - MUST_USE_INVENTORY         # 必须通过 inventory 引用

  # 人类管理硬件
  hardware_managed_by: human
```

### 2. inventory 结构

```ini
# 00-inventory/dev/hosts.ini
[dev-api]
dev-api-1 ansible_host=10.0.1.10 env=dev role=api zone=cn-south-1

[dev-db]
dev-db-1 ansible_host=10.0.1.11 env=dev role=db zone=cn-south-1

[dev:children]
dev-api
dev-db
```

### 3. inventory-usage.yaml (Phase 4 输出)

```yaml
# 记录部署实际使用了哪些 inventory
deployment:
  phase: p4_deploy_dev_test
  uses_inventory:
    - dev
    - test

  dev_deployment:
    inventory_path: ./00-inventory/dev
    hosts_deployed:
      - dev-api-1 (10.0.1.10)
      - dev-db-1 (10.0.1.11)
    status: success

  test_deployment:
    inventory_path: ./00-inventory/test
    hosts_deployed:
      - test-api-1 (10.0.2.10)
      - test-db-1 (10.0.2.11)
    status: success
```

---

## 与 v1.1 的差异

| 特性 | v1.1 | v1.2 |
|------|------|------|
| 资源绑定 | 无 | `resource_binding` 声明 |
| inventory 约束 | 隐式 | `uses_inventory` 显式声明 |
| 资源创建 | 未明确禁止 | `NO_RESOURCE_PROVISIONING` |
| 服务器引用 | 可硬编码 IP | 必须用 inventory |
| contract 版本 | 1.0.0 | 1.1.0 |

---

## 参考文档

- [资源管理宪法](../../docs/LEE-devops-resource-charter.md)
- [IaC 演进路线图](../../docs/LEE-devops-iac-roadmap.md)
- [资源标签规范](../../resource-tags.yaml)
- [执行契约 v1.1.0](../../contracts/devops-execution.contract.yaml)
- [工作流 v1.2](../../workflows/devops-deployment/v1/workflow.yaml)

---

**Demo 版本**: 1.2
**创建日期**: 2026-01-30
**维护者**: LEE DevOps Team
