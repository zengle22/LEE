# DevOps Demo 快速开始

## 📖 演示说明

本演示展示 DevOps L2 Workflow 的完整执行过程，模拟真实的项目部署场景。

**演示场景**:
- 项目: task-manager (任务管理系统)
- 版本: 1.0.0
- 目标环境: dev + test
- 部署方式: Docker Compose

## 🚀 快速开始

### 方式 1: 交互式演示（推荐）

```bash
# 进入 demo 目录
cd spec-global/departments/devops/demo

# 运行交互式演示（需要 bash 环境）
chmod +x demo-runner.sh
./demo-runner.sh
```

**交互式菜单**:
- 按 `1-6` 查看各个阶段的详细信息
- 按 `7` 查看完整执行日志
- 按 `8` 查看执行统计
- 按 `9` 查看项目结构
- 按 `0` 退出

### 方式 2: 查看文档

```bash
# 查看演示说明
cat README.md

# 查看执行日志
cat execution-log.md

# 查看各个阶段输出
ls -la 01-architecture/
ls -la 02-implementation/
ls -la 03-env-config/
ls -la 04-deployment/
ls -la 05-verification/
ls -la 06-release-freeze/
```

### 方式 3: 按阶段探索

```bash
# Phase 1: 查看架构设计
cat 01-architecture/infra-architecture.yaml
cat 01-architecture/env-matrix.yaml
cat 01-architecture/gate-approval.yaml

# Phase 2: 查看实施代码
cat 02-implementation/docker-compose.yml
cat 02-implementation/deploy/deploy-dev-test.sh

# Phase 3: 查看环境配置
cat 03-env-config/env-config.dev.yaml
cat 03-env-config/env-config.test.yaml

# Phase 4: 查看部署日志
cat 04-deployment/deployment-dev.log
cat 04-deployment/deployment-test.log
cat 04-deployment/service-status.yaml

# Phase 5: 查看验证结果
cat 05-verification/deployment-checklist.md
cat 05-verification/release-manifest.yaml

# Phase 6: 查看冻结报告
cat 06-release-freeze/freeze-report.md
cat 06-release-freeze/audit-trail.yaml
```

## 📂 文件结构

```
demo/
├── README.md                    # 演示说明（本文档）
├── QUICKSTART.md               # 快速开始（本文档）
├── execution-log.md            # 完整执行日志
├── demo-runner.sh              # 交互式演示脚本
│
├── 00-inputs/                  # 输入文件
│   ├── project-spec.json       # 项目规格
│   └── deployment-requirements.md  # 部署需求
│
├── 01-architecture/            # Phase 1 输出
│   ├── infra-architecture.yaml # 基础设施架构
│   ├── env-matrix.yaml         # 环境矩阵
│   └── gate-approval.yaml      # Gate 审批记录
│
├── 02-implementation/          # Phase 2 输出
│   ├── docker-compose.yml      # Docker Compose 配置
│   ├── deploy/
│   │   ├── deploy-dev-test.sh  # 部署脚本
│   │   └── rollback-dev-test.sh # 回滚脚本
│   └── cicd/
│       └── github-actions.yaml # CI/CD 配置
│
├── 03-env-config/              # Phase 3 输出
│   ├── env-config.dev.yaml     # Dev 环境配置
│   ├── env-config.test.yaml    # Test 环境配置
│   └── gate-approval.yaml      # Gate 审批记录
│
├── 04-deployment/              # Phase 4 输出
│   ├── deployment-dev.log      # Dev 部署日志
│   ├── deployment-test.log     # Test 部署日志
│   └── service-status.yaml     # 服务状态
│
├── 05-verification/            # Phase 5 输出
│   ├── deployment-checklist.md # 部署验收清单
│   ├── release-manifest.yaml   # 发布清单
│   └── gate-approval.yaml      # Gate 审批记录
│
└── 06-release-freeze/          # Phase 6 输出
    ├── freeze-report.md        # 冻结报告
    ├── audit-trail.yaml        # 审计跟踪
    └── gate-approval.yaml      # Gate 审批记录
```

## 🎯 学习路径

### 初学者路径

1. **了解整体流程** (5 分钟)
   - 阅读 `README.md`
   - 查看 `execution-log.md` 的摘要部分

2. **查看输入输出** (10 分钟)
   - 查看 `00-inputs/` 了解项目需求
   - 查看各阶段输出文件

3. **理解 Agent 执行** (15 分钟)
   - Phase 1: 架构设计
   - Phase 2: 代码生成
   - Phase 5: 验证和冻结

4. **理解 Human Gate** (10 分钟)
   - Phase 3: 配置注入
   - Phase 5: 验收审批
   - Phase 6: 最终审批

### 进阶路径

1. **深入架构设计** (20 分钟)
   - 详细阅读 `infra-architecture.yaml`
   - 理解服务拓扑和网络架构
   - 查看架构决策记录（ADR）

2. **分析实施代码** (30 分钟)
   - 阅读 `docker-compose.yml`
   - 分析部署脚本逻辑
   - 查看 CI/CD Pipeline 配置

3. **追踪审批流程** (15 分钟)
   - 查看各阶段的 `gate-approval.yaml`
   - 理解审批清单
   - 分析审批意见

### 专家路径

1. **完整审计跟踪** (30 分钟)
   - 阅读 `audit-trail.yaml`
   - 追踪每个阶段的执行时间
   - 分析决策和审批理由

2. **代码质量分析** (45 分钟)
   - 检查生成的代码质量
   - 分析安全性配置
   - 评估可维护性

3. **流程优化建议** (30 分钟)
   - 识别潜在瓶颈
   - 提出优化建议
   - 设计改进方案

## 📊 关键数据

| 指标 | 值 |
|------|-----|
| **总执行时间** | 88 分钟 |
| **Agent 执行** | 48 分钟 (55%) |
| **Human Gate** | 40 分钟 (45%) |
| **输出文件** | 20 个 |
| **代码行数** | ~1,670 行 |
| **审批通过率** | 100% |

## 🎓 核心概念

### 1. 三 Agent 模型

- **Architect Agent**: 架构设计与方案
- **Implementation Agent**: 代码生成与实现
- **Verification Agent**: 验证与版本冻结

### 2. Human Gate 机制

- **Phase 1 后**: 架构设计审批
- **Phase 3**: 配置注入（必须人类）
- **Phase 5 后**: 部署验收
- **Phase 6 后**: 版本冻结

### 3. 自动化程度

- **完全自动化**: Phase 2, Phase 4
- **半自动化**: Phase 1, Phase 5, Phase 6
- **人工操作**: Phase 3

## 💡 使用建议

1. **首次浏览**: 使用交互式演示，整体了解流程
2. **深入学习**: 按阶段查看详细文件
3. **实际应用**: 参考示例文件，应用到实际项目
4. **团队培训**: 使用 demo 作为培训材料

## 🔗 相关资源

- **DevOps 部门规范**: `../README.md`
- **Orchestrator 集成**: `../docs/orchestrator-integration.md`
- **实战示例**: `../examples/`
- **Workflow 定义**: `../workflows/devops-deployment/v1/workflow.yaml`

## ❓ 常见问题

**Q: 这个 demo 可以直接运行吗？**
A: 这是一个静态演示，展示了执行过程和结果。如果要在实际环境中运行，需要使用 `examples/` 目录中的文件。

**Q: 如何修改 demo 内容？**
A: 可以编辑各个阶段的输出文件，但建议保持原始结构以便理解。

**Q: demo 中的占位符是什么意思？**
A: `${VARIABLE_NAME}` 格式的占位符表示需要由人类填写的敏感信息，AI 不会生成真实密钥。

**Q: 如何在实际项目中使用？**
A: 参考 `examples/` 目录中的实战文件，复制并修改占位符即可。

---

**Demo 版本**: 1.0
**创建日期**: 2026-01-29
**维护者**: LEE Team
