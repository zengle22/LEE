# Running Coach - 发布策略

> Phase 1 输出 by agent.devops.architect
> 创建时间: 2026-01-30

---

## 1. 发布流程

```
dev → test → staging → prod
 │      │       │        │
 │      │       │        └── Human Gate (3人审批)
 │      │       └── Human Gate (2人审批)
 │      └── 自动
 └── 自动
```

## 2. 环境部署策略

| 环境 | 策略 | Human Gate | 审批人 |
|------|------|-----------|--------|
| dev | 自动部署 | 否 | - |
| test | 自动部署 | 否 | - |
| staging | 手动触发 | 是 | devops_lead, tech_lead |
| prod | 手动触发 | 是 | devops_lead, tech_lead, product_owner |

## 3. 部署方式

### 3.1 Docker Compose 部署（dev/test）

```bash
# 使用 Ansible 执行部署
ansible-playbook -i inventory/dev/hosts.ini playbooks/deploy.yml

# 或直接使用部署脚本
./deploy/deploy-dev.sh
```

### 3.2 资源绑定（v1.2 新增）

**关键约束**：
- 部署必须通过 Ansible inventory 引用服务器
- 禁止硬编码 IP 地址
- 禁止 Agent 创建云资源

```yaml
# workflow 中的 resource_binding
resource_binding:
  type: ansible_inventory
  inventories:
    dev: ./00-inventory/dev
    test: ./00-inventory/test
```

## 4. 回滚方案

### 4.1 快速回滚

```bash
# 使用回滚脚本
./deploy/rollback.sh dev

# 或使用 Ansible
ansible-playbook -i inventory/dev/hosts.ini playbooks/rollback.yml
```

### 4.2 回滚步骤

1. 停止当前服务
2. 恢复上一版本镜像
3. 启动服务
4. 健康检查
5. 验证功能

### 4.3 回滚时间目标

| 环境 | 目标 RTO |
|------|---------|
| dev | < 5 分钟 |
| test | < 5 分钟 |
| staging | < 10 分钟 |
| prod | < 15 分钟 |

## 5. 健康检查

```yaml
health_check:
  path: /health
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 60s
```

## 6. 监控与告警

- Prometheus 指标: `/metrics`
- 日志级别: 按环境配置
- 告警阈值:
  - API 响应时间 > 1s
  - 错误率 > 1%
  - 内存使用 > 80%

---

**文档版本**: 1.0.0
**创建者**: agent.devops.architect
