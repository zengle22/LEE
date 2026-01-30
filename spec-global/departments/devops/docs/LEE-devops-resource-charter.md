# LEE DevOps 资源管理宪法 v1.0

> **文档版本**: 1.0
> **创建日期**: 2026-01-30
> **状态**: 生效中

---

## 1. 目标

在 LEE 体系中，明确硬件资源（云服务器等）的权责边界，保证：
- 成本可控
- 安全边界清晰
- 部署流程可控、可回滚、可审计
- 未来能平滑升级至 Terraform / k8s / GitOps

---

## 2. 三层权力结构中的位置

| 层级 | 角色 | 职责 |
|------|------|------|
| **人类（Strategic authority）** | 资源拥有者 | 决定是否购买/释放资源；决定资源规模、成本上限、地域、网络边界 |
| **传统程序 / Orchestrator（Process authority）** | 流程调度者 | 选择使用哪些资源（通过 inventory / 标签）；调度部署流程（Ansible / 脚本） |
| **Agent（Cognitive execution）** | 代码生成者 | 生成/维护 Ansible Playbook / Inventory 模板 / IaC 文件；**不直接申请资源，不直接执行变更** |

---

## 3. DevOps 部门职责边界

### 3.1 DevOps 必须做的事

- **设计并维护**：
  - Ansible inventory 结构与命名规范
  - Ansible playbook / role（部署、回滚、巡检）
  - 环境标签规范（env / role / zone 等）
  - 资源使用规范（每台机器跑哪些服务）
- **确保**：
  - 所有部署流程脚本化、可重复
  - 有明确回滚方案
  - 有基础审计输出（部署日志、变更记录）

### 3.2 DevOps 明确不做的事

- 不直接创建 / 删除云服务器
- 不直接操作云账号 / 计费策略
- 不擅自变更服务器规格（CPU/内存/磁盘）
- 不负责云厂商选型与谈价
- 不绕过人类审批申请新增资源

> **核心原则**：DevOps 只"使用资源"，不"创造资源"。

---

## 4. 人类（资源拥有者）的职责

- **规划整体资源池**：
  - 选择云厂商 / 区域 / 专线等
  - 规划 dev / test / staging / prod 的独立资源
- **创建服务器**：
  - 基础系统安装（OS、基础安全加固）
  - 分配基本网络与安全组
- **与 DevOps 联合制定**：
  - 资源标签
  - 环境配额（每个 env 可用多少台、规格）

---

## 5. Workflow 与资源的关系

- workflow **只能选择已有资源**，不能申请新资源
- workflow 中引用资源的唯一方式是：
  - Ansible inventory 名称
  - 或资源标签（env, role 等）
- workflow 不得：
  - 自行决定创建云资源
  - 自行扩大资源规模
  - 直接操作云 API 申请新机器

---

## 6. 安全与成本控制原则

1. **硬件资源视为"慢变量"**
   - 由人类周期性评估（按月/季度）
   - 不由 workflow 动态调整

2. **部署视为"快变量"**
   - 由 DevOps + Orchestrator 负责
   - 可以频繁执行，变更可回滚

3. **任何能导致账单显著变化的操作，必须由人类执行或审批**

---

## 7. 未来演进预留

- 当满足以下条件时，可以考虑让 DevOps 通过 Terraform 管理资源：
  - 有稳定增长的用户需求
  - 有成熟的成本监控 & 报警
  - 有清晰的变更审批流程
- 即便引入 Terraform：
  - 资源变更仍需人类审批
  - Orchestrator 只触发既定 Terraform 计划，不直接写云 API

> 详细演进路线图参见：[LEE-devops-iac-roadmap.md](./LEE-devops-iac-roadmap.md)

---

## 8. 相关文档

| 文档 | 说明 |
|------|------|
| [resource-tags.yaml](../resource-tags.yaml) | 资源标签规范 |
| [LEE-devops-iac-roadmap.md](./LEE-devops-iac-roadmap.md) | IaC 演进路线图 |
| [devops-execution.contract.yaml](../contracts/devops-execution.contract.yaml) | DevOps 执行契约 |

---

**维护者**: LEE DevOps Team
**最后更新**: 2026-01-30
