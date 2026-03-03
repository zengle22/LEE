# QA-DevOps 接口契约文档

本文档定义了 DevOps 模块提供给 QA 模块的接口及其输入输出契约。

## 版本信息

- **版本**: v1.0
- **更新日期**: 2026-02-27
- **维护模块**: DevOps, QA

## 目录

- [调用链路概览](#调用链路概览)
- [接口清单](#接口清单)
  - [接口 #1: agent.qa.env_provisioner](#接口-1-agentqaenv_provisioner)
  - [接口 #2: skill.devops.deploy_test_env](#接口-2-skilldevopsdeploy_test_env)
  - [接口 #3: skill.devops.health_check](#接口-3-skilldevopshealth_check)
  - [接口 #4: skill.devops.deploy](#接口-4-skilldevopsdeploy)
  - [接口 #5: skill.env.check_tools](#接口-5-skillenvcheck_tools)

---

## 调用链路概览

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     QA → DevOps 接口调用链路                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Test Plan Execution Workflow (L2)                                      │
│    │                                                                     │
│    ├── Phase 2: 环境准备                                                │
│    │     └── agent.qa.env_provisioner                                   │
│    │            │                                                        │
│    │            ├── skill.devops.deploy_test_env  (部署测试环境)        │
│    │            ├── skill.devops.health_check     (健康检查)            │
│    │            └── skill.devops.deploy           (Docker部署)          │
│    │                                                                      │
│    └── Phase 3: 环境探测                                                │
│          └── skill.env.check_tools  (CLI: lee check-env qa-e2e)         │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 接口清单

### 接口 #1: agent.qa.env_provisioner

**Agent ID**: `agent.qa.env_provisioner`

**用途**: Phase 2 环境准备 - 部署测试环境并执行健康检查

**依赖的 DevOps 技能**:
- `skill.devops.deploy_test_env` - 部署测试环境
- `skill.devops.health_check` - 健康检查
- `skill.devops.deploy` - Docker 部署
- `skill.devops.check_env` - 环境检查

#### 输入契约

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `test_run` | object | 是 | Test Run 对象 |
| `build_version` | string | 是 | 构建版本 (如: v1.2.3) |
| `build_commit` | string | 是 | 构建 commit hash |
| `environment` | string | 是 | 环境名称 (dev/test/staging) |

#### 输出契约

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `environment_info` | object | 是 | 环境信息对象 |
| `environment_info.status` | string | 是 | 环境健康状态: `healthy` 或 `unhealthy` |
| `environment_info.url` | string | 是 | 环境访问 URL |
| `environment_info.env` | string | 是 | 环境名称 |
| `environment_info.version` | string | 否 | 部署的版本 |
| `environment_info.services` | object | 否 | 各服务状态 |
| `environment_info.health_check_result` | object | 否 | 健康检查详细结果 |
| `env_health` | object | 是 | 环境健康报告（详细） |

#### 门控检查

```yaml
gate:
  check: "environment_info.status == 'healthy'"
  on_pass: trigger "env_provisioned"
  on_fail: action "fail_phase"
```

---

### 接口 #2: skill.devops.deploy_test_env

**Skill ID**: `skill.devops.deploy_test_env`

**用途**: 部署测试环境

#### 输入契约

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `env` | string | 是 | - | 环境名称 (dev/test/staging) |
| `version` | string | 是 | - | 部署版本 |
| `compose_file` | string | 否 | docker-compose.test.yml | Docker Compose 文件路径 |

#### 输出契约

| 字段 | 类型 | 说明 |
|------|------|------|
| `ok` | boolean | 操作是否成功 |
| `status` | string | 部署状态: `deployed` 或 `failed` |
| `env` | string | 环境名称 |
| `version` | string | 部署的版本 |
| `type` | string | 环境类型 |
| `url` | string | 环境访问 URL |
| `port` | integer | 服务端口 |

#### 输出示例

```json
{
  "ok": true,
  "status": "deployed",
  "env": "test",
  "version": "v1.2.3",
  "type": "test",
  "url": "test.test.local",
  "port": 8080
}
```

---

### 接口 #3: skill.devops.health_check

**Skill ID**: `skill.devops.health_check`

**用途**: 健康检查，带重试逻辑

#### 输入契约

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `env` | string | 是 | - | 环境名称 |
| `url` | string | 是 | - | 健康检查端点 URL |
| `retries` | integer | 否 | 5 | 重试次数 |
| `interval` | integer | 否 | 3 | 重试间隔（秒） |

#### 输出契约

| 字段 | 类型 | 说明 |
|------|------|------|
| `ok` | boolean | 操作是否成功 |
| `status` | string | 健康状态: `healthy` 或 `unhealthy` |
| `env` | string | 环境名称 |
| `url` | string | 检查的 URL |
| `http_code` | integer | HTTP 状态码 |
| `attempt` | integer | 成功时的尝试次数 |
| `attempts` | integer | 失败时的总尝试次数 |
| `result_path` | string | 结果文件路径 |

#### 输出示例

成功:
```json
{
  "ok": true,
  "status": "healthy",
  "env": "test",
  "url": "http://test.test.local/health",
  "http_code": 200,
  "attempt": 1,
  "result_path": "health-check-results/test/health-20250227123456.json"
}
```

失败:
```json
{
  "ok": false,
  "status": "unhealthy",
  "env": "test",
  "url": "http://test.test.local/health",
  "http_code": 000,
  "attempts": 5,
  "result_path": "health-check-results/test/health-20250227123456.json"
}
```

---

### 接口 #4: skill.devops.deploy

**Skill ID**: `skill.devops.deploy`

**用途**: 通用 Docker 部署

#### 输入契约

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `env` | string | 是 | - | 环境名称 |
| `version` | string | 是 | - | 部署版本 |
| `compose_file` | string | 否 | docker-compose.yml | Docker Compose 文件路径 |

#### 输出契约

| 字段 | 类型 | 说明 |
|------|------|------|
| `ok` | boolean | 操作是否成功 |
| `env` | string | 环境名称 |
| `version` | string | 部署的版本 |
| `log` | string | 部署日志文件路径 |

---

### 接口 #5: skill.env.check_tools

**Skill ID**: `skill.env.check_tools`

**用途**: Phase 3 环境探测 - 检查测试工具和环境

**执行方式**: CLI (`lee check-env qa-e2e`)

#### 输入契约

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `require_docker` | boolean | 否 | true | 是否要求 Docker 存在 |
| `require_image` | string | 否 | e2e-runner:latest | 要求的 Docker 镜像名 |
| `base_url` | string | 否 | - | 可选：对被测应用 URL 做可达性探测 |

#### 输出契约

| 字段 | 类型 | 说明 |
|------|------|------|
| `ok` | boolean | 所有检查是否通过 |
| `checks` | array | 检查项列表 |
| `checks[].name` | string | 检查项名称 |
| `checks[].ok` | boolean | 是否通过 |
| `checks[].message` | string | 失败时的说明信息 |

#### 输出示例

```json
{
  "ok": true,
  "checks": [
    {"name": "docker_exists", "ok": true},
    {"name": "playwright_exists", "ok": true},
    {"name": "service_reachable", "ok": true}
  ]
}
```

#### 门控检查

```yaml
gate:
  check: "env_check_result.all_passed == true"
```

---

## 接口汇总表

| 接口 | 类型 | Phase | 输入关键字段 | 输出关键字段 | 门控条件 |
|------|------|-------|-------------|-------------|---------|
| `agent.qa.env_provisioner` | Agent | Phase 2 | `environment`, `build_version` | `status` | `status == 'healthy'` |
| `skill.devops.deploy_test_env` | Skill | Phase 2 | `env`, `version` | `url`, `port`, `status` | - |
| `skill.devops.health_check` | Skill | Phase 2 | `env`, `url` | `status` | - |
| `skill.devops.deploy` | Skill | Phase 2 | `env`, `version` | `ok`, `log` | - |
| `skill.env.check_tools` | Skill | Phase 3 | `base_url` | `all_passed` | `all_passed == true` |

---

## 文件索引

| 组件 | 文件路径 |
|------|---------|
| Env Provisioner Agent | `spec-global/departments/qa/agents/env-provisioner/v1/agent.yaml` |
| Deploy Test Env Skill | `spec-global/departments/devops/skills/deploy-test-env/v1/skill.yaml` |
| Health Check Skill | `spec-global/departments/devops/skills/health-check/v1/skill.yaml` |
| Deploy Skill | `spec-global/departments/devops/skills/deploy/v1/skill.yaml` |
| Check Tools Skill | `spec-global/departments/qa/skills/env-check-tools/v1/skill.yaml` |
| QA Test Plan Workflow | `spec-global/departments/qa/workflows/test-plan-execution/v2/workflow.yaml` |

---

## 变更历史

| 版本 | 日期 | 变更内容 |
|------|------|---------|
| v1.0 | 2026-02-27 | 初始版本，定义 QA-DevOps 集成接口契约 |
