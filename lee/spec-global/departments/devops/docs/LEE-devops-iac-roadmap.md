# LEE DevOps 基础设施演进路线图 v1.0

> **文档版本**: 1.0
> **创建日期**: 2026-01-30
> **状态**: 生效中

---

## 目标

从 "人工创建云服务器 + Ansible 部署" 平滑演进到 "Terraform 管理资源 + Ansible / k8s 部署"，中间不引入过度复杂性。

---

## 阶段 0：当前状态（起点）

- 云服务器由人类在控制台手动创建
- 服务器 IP / 角色写入 Ansible inventory
- 部署通过：
  - docker-compose
  - Ansible playbook
  - Orchestrator program runner 调用 shell / ansible-playbook

**是否继续维持：是，这是当前最适合的状态。**

---

## 阶段 1：Ansible 治理与规范化（建议立即做）

**目标**：先把 Ansible 用规范、用扎实。

**动作**：
1. 建立统一的 inventory 目录结构与标签规范（env / role / zone）
2. 将所有部署操作脚本化（部署 / 回滚 / 巡检）
3. 为 dev / test / staging / prod 定义不同 playbook：
   - `deploy-dev.yml`
   - `deploy-test.yml`
   - `deploy-prod.yml`
4. 将部署入口统一为：
   - `deploy-dev.sh`
   - `deploy-test.sh`
   - `deploy-prod.sh`（带 human gate）

**完成标准**：
- [x] dev / test 部署完全可由一条命令触发
- [x] prod 部署需要人类审批 + 统一脚本
- [x] 任意一次部署都有对应的回滚方案

---

## 阶段 2：引入 Terraform 管理"部分资源"（基础版）

**前提条件**：
- 资源规模开始增大
- 新增 / 删除服务器的频率增加
- 对资源的可追溯 / 可审计要求提升

**策略**：
- 不是"一步上云"，而是"先让部分资源代码化"
- 优先 Terraform 化：
  - VPC / 子网 / 安全组
  - 公网 IP / 负载均衡
- 服务器本身可以先不 Terraform，只做网络层 IaC

**动作**：
1. 建立 `infra/terraform/network/` 目录
2. 定义各环境网络资源：
   - `dev_vpc` / `test_vpc` / `prod_vpc`
3. Orchestrator 只调用：
   - `terraform plan`（由人类审核）
   - `terraform apply`（带 strong human gate）

**完成标准**：
- [ ] 网络资源变更不再通过控制台点击完成，而是通过 Terraform 审核 + apply
- [ ] 所有 VPC / 子网 / 安全组有版本化记录

---

## 阶段 3：Terraform 管理服务器资源（中期）

**前提条件**：
- 需要频繁新增 / 缩减服务器
- 有成熟成本监控（账单 + 报警）
- 有固定 DevOps 负责人愿意背 IaC 责任

**动作**：
1. 为 dev / test 环境：
   - 用 Terraform 创建 VM / ECS / EC2 实例
   - Ansible 继续负责配置与部署
2. prod 资源：
   - 仍可由人类手动创建，等稳定后再 Terraform 化
3. 引入资源命名 + 标签体系：
   - `env=dev|test|prod`
   - `managed_by=terraform`
   - `system=<project-name>`

**完成标准**：
- [ ] 至少 dev / test 环境可以"一键重新创建"（网络 + 服务器）
- [ ] prod 的变更仍有严格的人类审批

---

## 阶段 4：考虑 k8s / GitOps（远期）

**只在出现以下场景时考虑**：
- 服务数量显著增加
- 自动伸缩需求强烈
- 希望多副本高可用 / 灰度发布 / 精细流量控制

**路线**：
1. Terraform 管理 k8s 集群（EKS / ACK / GKE 等）
2. Ansible 退居为少量非 k8s 资源管理
3. 部署方式从 ansible-playbook → GitOps（ArgoCD / Flux）

**注意**：
- 是否进入这一阶段，不是技术问题，而是**业务规模 + 人力成本**决策
- 现阶段不建议主动走到这一步

---

## 阶段对照表

| 阶段 | 资源管理 | 部署方式 | 适用场景 |
|------|---------|---------|---------|
| 0 | 人工控制台 | docker-compose / Ansible | 初创 / 小规模 |
| 1 | 人工 + inventory 规范 | Ansible playbook | 小规模 / 规范化 |
| 2 | Terraform (网络层) | Ansible playbook | 中等规模 / 审计需求 |
| 3 | Terraform (全量) | Ansible playbook | 较大规模 / 频繁变更 |
| 4 | Terraform + k8s | GitOps | 大规模 / 微服务 |

---

## 决策检查清单

在考虑升级到下一阶段前，请确认：

- [ ] 当前阶段的规范已完全落地
- [ ] 有明确的业务需求驱动升级
- [ ] 有足够的人力支撑新工具的维护
- [ ] 有成本监控和报警机制
- [ ] 有回滚到上一阶段的方案

---

## 相关文档

| 文档 | 说明 |
|------|------|
| [LEE-devops-resource-charter.md](./LEE-devops-resource-charter.md) | 资源管理宪法 |
| [resource-tags.yaml](../resource-tags.yaml) | 资源标签规范 |

---

**维护者**: LEE DevOps Team
**最后更新**: 2026-01-30
