# Phase 目录结构规范 v1.0

## 目的

统一所有开发阶段(Phase)的目录结构，确保 Agent 产出物位置一致、可预测。

## 标准目录结构

```
project/{项目名}/dev/
└── phase{N}/                    # 阶段根目录
    ├── .workflow/               # 工作流状态 (内部)
    │   ├── state.yaml           # 工作流状态文件
    │   ├── tokens/              # 步骤令牌
    │   └── approvals/           # 审批记录
    │
    ├── openspec/                # OpenSpec 产出物 (唯一产出目录)
    │   ├── 00-init/             # 初始化
    │   │   ├── init.yaml        # 初始化配置
    │   │   └── context.yaml     # 项目上下文
    │   │
    │   ├── 01-requirements/     # 需求校准
    │   │   └── calibrated-requirements.md
    │   │
    │   ├── 02-contracts/        # 测试契约
    │   │   └── test-contracts.yaml
    │   │
    │   ├── 03-proposal/         # 实现提案
    │   │   ├── proposal.md      # 提案文档
    │   │   ├── tasks.md         # 任务分解
    │   │   └── ai-contracts/    # AI契约 (可选)
    │   │
    │   ├── 04-review/           # 代码审查
    │   │   └── review-report.md
    │   │
    │   ├── 05-retrospective/    # 回顾总结
    │   │   └── retrospective.md
    │   │
    │   ├── 06-knowledge/        # 知识沉淀
    │   │   ├── patterns/        # 设计模式
    │   │   ├── best-practices/  # 最佳实践
    │   │   └── pitfalls/        # 避坑指南
    │   │
    │   ├── 07-archive/          # 阶段归档
    │   │   └── archive.yaml
    │   │
    │   ├── 08-acceptance/       # 验收报告
    │   │   └── acceptance-report.yaml
    │   │
    │   └── backlog/             # 遗留任务
    │       └── tasks.md
    │
    └── design/                  # 设计文档 (可选)
        └── design.md
```

## 规则

### 1. 产出物唯一性

**所有 Agent 产出物必须放在 `openspec/` 目录下。**

❌ 禁止:
- `phase{N}/output/`
- `phase{N}/workflow/openspec/`
- `phase{N}/docs/`

✅ 正确:
- `phase{N}/openspec/`

### 2. 工作流状态隔离

`.workflow/` 目录只存放:
- 工作流状态 (`state.yaml`)
- 步骤令牌 (`tokens/`)
- 审批记录 (`approvals/`)

**不存放任何 Agent 产出物。**

### 3. 目录编号

使用两位数字前缀确保排序:
- `00-init/`
- `01-requirements/`
- `02-contracts/`
- ...

### 4. 文件命名

| 类型 | 命名规则 | 示例 |
|------|----------|------|
| 需求 | `calibrated-requirements.md` | - |
| 契约 | `{domain}-contracts.yaml` | `coach-contracts.yaml` |
| 提案 | `proposal.md` | - |
| 审查 | `review-report.md` | - |
| 回顾 | `retrospective.md` | - |
| 归档 | `archive.yaml` | - |
| 遗留 | `{category}-tasks.md` | `security-tasks.md` |

## Agent 输出路径模板

Agent 在输出文件时使用以下路径模板:

```yaml
# 路径变量
project_root: project/{项目名}
phase_root: ${project_root}/dev/phase{N}
openspec_root: ${phase_root}/openspec

# 步骤输出路径
p1_init: ${openspec_root}/00-init/
p2_requirements: ${openspec_root}/01-requirements/
p3_contracts: ${openspec_root}/02-contracts/
p4_proposal: ${openspec_root}/03-proposal/
p7_review: ${openspec_root}/04-review/
p8_retrospective: ${openspec_root}/05-retrospective/
p9_knowledge: ${openspec_root}/06-knowledge/
p10_archive: ${openspec_root}/07-archive/
backlog: ${openspec_root}/backlog/
```

## 迁移指南

对于已有的混乱结构，按以下步骤迁移:

1. 创建标准 `openspec/` 目录结构
2. 将 `workflow/openspec/*` 移动到 `openspec/`
3. 将 `output/*` 移动到 `openspec/06-knowledge/`
4. 删除空的 `workflow/openspec/` 和 `output/`
5. 更新 `state.yaml` 中的输出路径引用

## 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.0 | 2026-01-10 | 初始版本 |
