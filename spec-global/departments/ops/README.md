# 运维部门 (ops)

> Operations Department

## 部门职责

负责部署、监控、故障响应和基础设施管理

### 主要职责

- 系统部署
- 监控配置
- 故障响应
- 基础设施管理
- 性能优化

## 目录结构

```
{dept_id}/
├── workflows/      # 部门工作流
├── gates/          # 部门门禁
├── agents/         # 部门专属 agent
├── skills/         # 部门技能
└── contracts/      # 部门交付物契约
```

## 工作流 (workflows)

| 工作流 | 说明 | 输入 | 输出 |
|--------|------|------|------|
| deployment.yaml | 部署工作流 | 发布包 | 部署完成 |
| monitoring_setup.yaml | 监控配置工作流 | 系统 | 监控系统 |
| incident_response.yaml | 故障响应工作流 | 故障报告 | 故障解决 |

## 门禁 (gates)

| 门禁 | 触发条件 | 检查项 |
|------|----------|--------|
| deployment_success_gate.yaml | 部署成功门禁 | 切换流量前 |
| uptime_sla_gate.yaml | 可用性 SLA 门禁 | 发布后 |

## Agent 列表

| Agent | 职责 | 说明 |
|-------|------|------|
| devops-engineer.yaml | DevOps 工程师 | 负责部署和运维 |
| sre.yaml | SRE | 负责系统可靠性 |

## 技能 (skills)

| 技能 | 说明 |
|------|------|
| infrastructure.yaml | 基础设施技能 |
| monitoring.yaml | 监控技能 |

## 契约 (contracts)

| 契约 | 说明 |
|------|------|
| deployment_plan_contract.yaml | 部署计划契约 |

## 跨部门协作

### 协作关系

| 协作部门 | 接口契约 | E2E 工作流 |
|----------|----------|------------|
| qa | qa-ops 发布就绪契约 | 测试到运维 E2E 工作流 |

---

**最后更新**：2026-01-22

**维护者**：LEE 框架团队
